import sqlite3
import random
import numpy as np

HISTORY_LENGTH = 5
WEIGHT_DECAY = 0.1
CORRECT_NO_HINT = 0
CORRECT_HINT = 1
WRONG_NO_HINT = 2
WRONG_HINT = 3
NOISE = 1

class IRTQuestionSelector:
    def __init__(self,cursor):
        self.cursor = cursor
        self.model = None
        self.student_abilities = {}
        self.question_difficulties = {}

    def get_adaptive_questions(cursor, user_id, lesson_id, n_per_topic=5):
        """
        Return IRT-selected questions per topic
        Falls back to random selection if insufficient data.
        """    
        selector = IRTQuestionSelector
        selector.train_model()

        all_selected = []

        for topic_id in lesson_id:
            try:
                qs = selector.select_optimal_questions(
                    user_id=user_id,
                    topic_id=topic_id,
                    n_questions=n_per_topic
                )
                all_selected.extend(qs)
            except Exception:
                # Fallback: Random
                cursor.execute("""
                    SELECT question_id
                    FROM questions
                    WHERE lesson_id = ?
                    ORDER BY RANDOM()
                    LIMIT ?
                """, (topic_id, n_per_topic))
                all_selected.extend(q[0] for q in cursor.fetchall())

        random.shuffle(all_selected)
        return all_selected

    def train_model(self):
        """Train IRT model on all historical data"""
        # Fetch all attempts
        self.cursor.execute("""
            SELECT user_id, question_id, is_correct
            FROM UserProgress
        """)
        rows = self.cursor.fetchall()

        if not rows:
            return
        
        # Organization
        user_correct = {}
        question_correct = {}

        for user_id, question_id, is_correct in rows: 
            user_correct.setdefault(user_id, []).append(is_correct)
            question_correct.setdefault(question_id, []).append(is_correct)

        # Estimate student abilities, theta
        for user_id, responses in user_correct.items():
            p = (sum(responses) + 0.5) / (len(responses) + 1 ) # Lapalce smoothing
            theta = np.log(p / (1 - p)) # logit
            self.student_abilities[user_id] = theta

        # Estimate question difficulties, b
        for question_id, responses in question_correct.items():
            p = (sum(responses) + 0.5) / (len(responses) + 1)
            b = -np.log(p / (1 - p)) # inverse difficulty
            self.question_difficulties[question_id] = b

    def estimate_student_ability(self, user_id):    
        """Get current ability estimate for student"""
        if user_id not in self.student_abilities:
            return 0.0 # neutral
        return self.student_abilities[user_id]
    
    def predict_success_probability(self, user_id, question_id):
        """Predict P(correct) for this student-question pair"""
        ability = self.estimate_student_ability(user_id)
        difficulty = self.question_difficulties[question_id]
        # IRT 2PL model: P(correct) = 1 / (1 + exp(-a*(theta - b)))
        return self._irt_probability(ability, difficulty)
    
    def select_optimal_questions(self, user_id, topic_id, n_questions):
        """Select questions at optimal difficulty (around 50% success rate)"""
        # Get all question in topic
        self.cursor.execute("""
            SELECT question_id
            FROM questions
            WHERE lesson_id = ?
        """, (topic_id,))
        question_ids = [q[0] for q in self.cursor.fetchall()]

        if not question_ids:
            return []

        # Rank by how close P(correct) is to 0.5
        theta = self.estimate_student_ability(user_id)
        scored = []

        for qid in question_ids:
            b = self.question_difficulties.get(qid, 0.0)
            p = self._irt_probability(theta, b)
            scored.append((abs(p - 0.5), qid))

        scored.sort(key=lambda x: x[0])

        # Return top n_questions
        return [qid for _, qid in scored[:n_questions]]
    
    """ HELPERS """
    def _sigmoid(self, x):
        return 1 / (1 + np.exp(-x))
    
    def _irt_probability(self, theta, b, a=1.0):
        return self._sigmoid(a * (theta - b))

def create_ability_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS StudentAbilityHistory (
            ability_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            theta REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )    
    """)

def save_student_ability(cursor, user_id, theta):
    create_ability_table(cursor)
    cursor.execute("""
        INSERT INTO StudentAbilityHistory (user_id, theta)
        VALUES (?, ?)
    """, (user_id, theta))

def get_ability_history (cursor, user_id, limit=20):
    # Ensure table exists before querying
    create_ability_table(cursor)
    
    cursor.execute("""
        SELECT theta, timestamp
        FROM StudentAbilityHistory
        WHERE user_id = ?
        ORDER BY timestamp ASC
        LIMIT ?
    """, (user_id, limit))
    return cursor.fetchall()

def theta_to_level(theta):
    if theta < -1.0:
        return "Beginner"
    elif theta < 0.5:
        return "Developing"
    elif theta < 1.5:
        return "Proficient"
    else:
        return "Advanced"


# Returns an integer value based on a question attempt
def attempt_value(is_correct, used_hint):
    if is_correct:
        if used_hint:
            return CORRECT_HINT
        return CORRECT_NO_HINT
    if used_hint:
        return WRONG_HINT
    return WRONG_NO_HINT

# Returns the current score for a specific question and user
# A question with no history will return the value of WRONG_HINT
def question_score(cursor, user_id, question_id):
    cursor.execute("""
        SELECT is_correct, used_hint
        FROM UserProgress
        WHERE user_id = ? AND question_id = ?
        ORDER BY progress_id DESC
        LIMIT ?
        """, (user_id, question_id, HISTORY_LENGTH,))
    result_history = cursor.fetchall()
    total_score = 0
    weight = 1
    for result in result_history:
        total_score += attempt_value(result[0], result[1]) * weight
        weight -= WEIGHT_DECAY
    length = len(result_history)
    difference = HISTORY_LENGTH - length
    if difference > 0:
        total_score += WRONG_HINT * difference * (1 - WEIGHT_DECAY * (2 * HISTORY_LENGTH - difference - 1) / 2)
    total_weights = HISTORY_LENGTH - (HISTORY_LENGTH * (HISTORY_LENGTH - 1) * WEIGHT_DECAY) / 2
    score = total_score / total_weights
    return score

# Returns the score for a topic, which is the average of all questions even if they have not been seen yet
def topic_score(cursor, user_id, topic_id):
    cursor.execute("""
        SELECT question_id
        FROM questions
        WHERE lesson_id = ?
        """, (topic_id,))
    question_ids = cursor.fetchall()
    if len(question_ids) == 0:
        return WRONG_HINT
    total_score = 0
    for question_id in question_ids:
        total_score += question_score(cursor, user_id, question_id[0])
    score = total_score / len(question_ids)
    return score

# Returns the lesson_id of the weakest topic
def weak_topic(cursor, user_id):
    cursor.execute("""
        SELECT DISTINCT lesson_id
        FROM questions
        """)
    topics = cursor.fetchall()
    scores = [(topic[0], topic_score(cursor, user_id, topic[0])) for topic in topics]
    weakest = max(scores, key=lambda x: x[1])[0]
    return weakest

# Returns the lesson_id of the strongest topic
def strong_topic(cursor, user_id):
    cursor.execute("""
        SELECT DISTINCT lesson_id
        FROM questions
        """)
    topics = cursor.fetchall()
    scores = [(topic[0], topic_score(cursor, user_id, topic[0])) for topic in topics]
    strongest = min(scores, key=lambda x: x[1])[0]
    return strongest

# Returns a list of question ids from a topic. Questions with worse scores are more likely to be selected
# Adjust the randomness value by adjust the NOISE value
def get_topic_questions(cursor, user_id, topic_id, number_of_questions):
    cursor.execute("""
        SELECT question_id
        FROM questions
        WHERE lesson_id = ?
        """, (topic_id,))
    question_ids = [id[0] for id in cursor.fetchall()]
    if number_of_questions > len(question_ids):
        print("More questions pulled than questions in the database")
        exit()
    elif number_of_questions == len(question_ids):
        return question_ids
    scores = [(question_id, question_score(cursor, user_id, question_id)) for question_id in question_ids]
    question_list = []
    for _ in range(number_of_questions):
        weights = [score + NOISE for (_, score) in scores]
        selected = random.choices(scores, weights=weights, k=1)[0]
        question_list.append(selected[0])
        scores.remove(selected)
    return question_list

# Returns the total number of hints used for a topic
def topic_hints_used(cursor, user_id, topic_id):
    cursor.execute("""
        SELECT UserProgress.question_id
        FROM UserProgress
        JOIN questions ON UserProgress.question_id = questions.question_id
        WHERE UserProgress.user_id = ? AND UserProgress.used_hint = 1 AND questions.lesson_id = ?
        """, (user_id, topic_id,))
    number_of_hints = len(cursor.fetchall())
    return number_of_hints

# Returns the percentage of questions seen for a topic
def topic_seen_percent(cursor, user_id, topic_id):
    cursor.execute("""
        SELECT COUNT(lesson_id)
        FROM questions
        WHERE lesson_id = ?
        """, (topic_id,))
    total_questions = cursor.fetchone()[0]
    if total_questions == 0:
        return 0
    cursor.execute("""
        SELECT COUNT(DISTINCT UserProgress.question_id)
        FROM UserProgress
        JOIN questions ON UserProgress.question_id = questions.question_id
        WHERE UserProgress.user_id = ? AND questions.lesson_id = ?
        """, (user_id, topic_id,))
    seen_questions = cursor.fetchone()[0]
    percent = seen_questions / total_questions * 100
    return percent
# Returns the total number of questions that a user has gotten correct at least once
def overall_total_correct(cursor, user_id):
    cursor.execute("""
        SELECT COUNT(DISTINCT UserProgress.question_id)
        FROM UserProgress
        JOIN questions ON UserProgress.question_id = questions.question_id
        WHERE UserProgress.user_id = ? AND is_correct = 1
        """, (user_id,))
    total_correct = cursor.fetchone()[0]
    return total_correct

# Returns the total number of questions
def overall_total_questions(cursor):
    cursor.execute("""
        SELECT COUNT(question_id)
        FROM questions
        """)
    total_questions = cursor.fetchone()[0]
    return total_questions

# Returns the percentage of questions the user has gotten correct at least once
def overall_percent(cursor, user_id):
    total_questions = overall_total_questions(cursor)
    if total_questions == 0:
        return 0
    total_correct = overall_total_correct(cursor, user_id)
    print(total_correct, total_questions)
    percent = total_correct / total_questions
    return percent

# Returns the total number of questions gotten correct at least once for a topic
def topic_total_correct(cursor, user_id, topic_id):
    cursor.execute("""
        SELECT COUNT(DISTINCT UserProgress.question_id)
        FROM UserProgress
        JOIN questions ON UserProgress.question_id = questions.question_id
        WHERE UserProgress.user_id = ? AND UserProgress.is_correct = 1 AND questions.lesson_id = ?
        """, (user_id, topic_id,))
    total_correct = cursor.fetchone()[0]
    return total_correct

# Returns the total numbers of questions in the topic
def topic_total_questions(cursor, topic_id):
    cursor.execute("""
        SELECT COUNT(lesson_id)
        FROM questions
        WHERE lesson_id = ?
        """, (topic_id,))
    total_questions = cursor.fetchone()[0]
    return total_questions

# Returns the total percentage of questions gotten correct at least once for a topic
def topic_correct_percent(cursor, user_id, topic_id):
    total_questions = topic_total_questions(cursor, topic_id)
    if total_questions == 0:
        return 0
    total_correct = topic_total_correct(cursor, topic_id)
    print(total_correct, total_questions)
    percent = total_correct / total_questions * 100
    return percent

# Returns the percentage of questions gotten correct for a mode
def mode_correct_percent(cursor, user_id, mode):
    cursor.execute("""
        SELECT COUNT(question_id)
        FROM UserProgress
        WHERE user_id = ? AND mode = ?
        """, (user_id, mode,))
    total_questions = cursor.fetchone()[0]
    if total_questions == 0:
        return 0
    cursor.execute("""
        SELECT COUNT(question_id)
        FROM UserProgress
        WHERE user_id = ? AND is_correct = 1 AND mode = ?
        """, (user_id, mode,))
    total_correct = cursor.fetchone()[0]
    percent = total_correct / total_questions * 100
    return percent

# Returns the percentage of questions gotten correct recently
def recent_correct_percent(cursor, user_id, history_length):
    if history_length == 0:
        return 0
    cursor.execute("""
        SELECT COUNT(progress_id)
        FROM (
            SELECT progress_id, is_correct
            FROM UserProgress
            WHERE user_id = ?
            ORDER BY progress_id DESC
            LIMIT ?
        ) AS recent
        WHERE is_correct = 1
        """, (user_id, history_length,))
    total_correct = cursor.fetchone()[0]
    percent = total_correct / history_length * 100
    return percent
