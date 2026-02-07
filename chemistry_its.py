import os
import sys
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import math
import random
import tkinter.font as tkFont
import json
import its_functions

import matplotlib
matplotlib.use("TkAgg")

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

def resource_path(relative_path):
    '''Get absolute path to resource (dev & pyinstaller)'''
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path) 


# ------------------------ DATA (fallback) ------------------------
LESSONS = [
    {"title": "Matter", "body": "Matter has mass and volume. Common states: solid, liquid, gas."},
    {"title": "Atoms & Molecules", "body": "Atoms: protons(+), neutrons(0) in the nucleus; electrons(-) around it."},
]

FALLBACK_QUESTIONS = [
    {
        "id": 0,
        "text": "Which of the following IS a state of matter?",
        "choices": ["Solid", "Light", "Sound", "Heat"],
        "answer_index": 0,
        "hint": "Think: solid / liquid / gas.",
        "explanation": "Classically: solid, liquid, gas.",
        "topic_id": 0,
    },
    {
        "id": 1,
        "text": "Where are protons located?",
        "choices": ["In the nucleus", "In the electron cloud", "Outside the atom", "Only in the valence shell"],
        "answer_index": 0,
        "hint": "Center of the atom.",
        "explanation": "Protons and neutrons are in the nucleus.",
        "topic_id": 0,
    },
]

# ------------------------ DESIGN CONSTANTS ------------------------
COLORS = {
    "bg": "#0B3C49",
    "accent": "#2BB3B1",
    "accent_dark": "#1D8A88",
    "white": "#FFFFFF",
    "muted": "#E0F2F1",
    "ok": "#6EE7B7",     # green
    "bad": "#F87171",    # red
}

TITLE_FONT = ("Helvetica", 26, "bold")
SUBTITLE_FONT = ("Helvetica", 20, "bold")
BODY_FONT = ("Helvetica", 15)
H1_FONT = ("Helvetica", 30, "bold")
H2_FONT = ("Helvetica", 20, "bold")

# ------------------------ BACKGROUND DECORATIONS ------------------------
def create_chemistry_background(parent):
    """Create a subtle chemistry-themed background with molecular patterns that scales with window."""
    # Create canvas that fills the entire parent
    canvas = tk.Canvas(parent, bg=COLORS["bg"], highlightthickness=0)
    canvas.place(x=0, y=0, relwidth=1, relheight=1)
    
    # Explicitly send canvas to the back
    try:
        canvas.lower()
    except:
        pass  # If lower() fails, canvas is already at bottom from place()
    
    def draw_pattern():
        """Draw the chemistry pattern - called on window resize."""
        canvas.delete("all")  # Clear previous drawings
        
        # Get current window size
        parent.update_idletasks()
        width = parent.winfo_width() or 1400
        height = parent.winfo_height() or 900
        
        # Ensure minimum size
        width = max(width, 1400)
        height = max(height, 900)
        
        # Subtle molecular network (very faint)
        import random
        random.seed(42)  # Consistent pattern
        
        # Draw hexagonal chemistry grid (like benzene rings)
        hex_color = "#0D4A5A"  # Slightly lighter than bg
        for x in range(-150, width + 150, 150):
            for y in range(-130, height + 130, 130):
                offset_x = 75 if (y // 130) % 2 else 0
                cx, cy = x + offset_x, y
                # Draw hexagon
                points = []
                for i in range(6):
                    angle = math.pi / 3 * i
                    px = cx + 30 * math.cos(angle)
                    py = cy + 30 * math.sin(angle)
                    points.extend([px, py])
                canvas.create_polygon(points, outline=hex_color, fill="", width=1)
        
        # Add subtle molecular dots at random positions
        dot_color = "#0E5566"
        num_dots = min(50, (width * height) // 30000)  # Scale dots with screen size
        for i in range(num_dots):
            x = random.randint(50, width - 50)
            y = random.randint(50, height - 50)
            canvas.create_oval(x-2, y-2, x+2, y+2, fill=dot_color, outline="")
        
        # Draw faint orbital rings in corners
        ring_color = "#0D4855"
        margin = 100
        positions = [
            (margin, margin), 
            (width-margin, margin), 
            (margin, height-margin), 
            (width-margin, height-margin)
        ]
        for cx, cy in positions:
            for r in [40, 60, 80]:
                canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline=ring_color, width=1)
            # Add nucleus dot
            canvas.create_oval(cx-4, cy-4, cx+4, cy+4, fill=ring_color, outline="")
    
    # Draw initial pattern
    parent.after(100, draw_pattern)
    
    # Redraw on window resize
    def on_resize(event):
        draw_pattern()
    
    canvas.bind("<Configure>", on_resize)
    
    return canvas

# ------------------------ DB HELPERS ------------------------
DB_PATH = resource_path("its_database.db")

def fetch_all_questions_from_db(db_path: str):
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        # Include image column too
        cur.execute("""
            SELECT question_id, question_text, answers, correct_answer, hint, explanation, lesson_id, image
            FROM questions
        """)
        return cur.fetchall()
    finally:
        conn.close()


def parse_questions(rows):
    parsed = []
    for r in rows:
        # Added image as last field
        q_id, q_text, answers_str, correct_ans, hint, explanation, lesson_id, image = r

        choices = json.loads(answers_str)
        if not choices:
            continue

        try:
            answer_index = choices.index(correct_ans.strip())
        except Exception:
            answer_index = 0

        parsed.append({
            "id": q_id,
            "text": q_text or "",
            "choices": choices,
            "answer_index": answer_index,
            "hint": hint or "",
            "explanation": explanation or "",
            "topic_id": lesson_id,
            "image": image or "",  
        })

    return parsed


def load_questions():
    if not os.path.exists(DB_PATH):
        return FALLBACK_QUESTIONS, "Database not found. Using built-in sample questions."
    try:
        rows = fetch_all_questions_from_db(DB_PATH)
        parsed = parse_questions(rows)
        if not parsed:
            return FALLBACK_QUESTIONS, "No usable questions in DB. Using built-in sample questions."
        return parsed, None
    except Exception as e:
        return FALLBACK_QUESTIONS, f"Error reading database: {e}. Using built-in sample questions."

def load_lessons():
    if not os.path.exists(DB_PATH):
        return LESSONS, "Database not found. Using fallback sample lessons."

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT lesson_name, content, image FROM lessons ORDER BY lesson_id ASC")
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return LESSONS, "No lessons found in DB. Using fallback sample lessons."

        parsed = [{"title": name, "body": content or "", "image": image or ""} for name, content, image in rows]
        return parsed, None

    except Exception as e:
        return LESSONS, f"Error reading lessons table: {e}. Using fallback sample lessons."

def create_users_table():
    """Ensure Users table exists (without recreating or overwriting anything)."""
    try:
        if not os.path.exists(DB_PATH):
            return False, f"Database not found at {DB_PATH}"

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Only creates table if missing, does NOT touch existing DB
        cur.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                UID INTEGER PRIMARY KEY AUTOINCREMENT,
                Username TEXT UNIQUE NOT NULL,
                Fname TEXT NOT NULL,
                Lname TEXT NOT NULL,
                Email TEXT UNIQUE NOT NULL,
                Password TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()
        return True, None
    except Exception as e:
        return False, f"Error creating Users table: {e}"


def insert_user(username, fname, lname, email, password):
    """Insert a new user into the Users table."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO Users (Username, Fname, Lname, Email, Password)
            VALUES (?, ?, ?, ?, ?)
        """, (username, fname, lname, email, password))
        conn.commit()
        user_id = cur.lastrowid
        conn.close()
        return True, user_id, None
    except sqlite3.IntegrityError as e:
        if "Username" in str(e):
            return False, None, "Username already exists."
        elif "Email" in str(e):
            return False, None, "Email already exists."
        else:
            return False, None, "User already exists."
    except Exception as e:
        return False, None, f"Error creating user: {e}"

def validate_login(username, password):
    """Validate user credentials and return user info if valid."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT UID, Username, Fname, Lname, Email
            FROM Users
            WHERE Username = ? AND Password = ?
        """, (username, password))
        row = cur.fetchone()
        conn.close()
        
        if row:
            return True, {
                "uid": row[0],
                "username": row[1],
                "name": f"{row[2]} {row[3]}",
                "fname": row[2],
                "lname": row[3],
                "email": row[4]
            }
        else:
            return False, None
    except Exception as e:
        return False, None
def create_progress_table():
    """Create UserProgress table if it doesn't exist."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS UserProgress (
                progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                selected_answer TEXT,
                is_correct INTEGER NOT NULL,
                used_hint INTEGER DEFAULT 0,
                mode TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES Users(UID),
                FOREIGN KEY (question_id) REFERENCES questions(question_id)
            )
        """)
        conn.commit()
        conn.close()
        return True, None
    except Exception as e:
        return False, f"Error creating UserProgress table: {e}"

def insert_progress(user_id, question_id, selected_answer, is_correct, used_hint, mode):
    """Insert a progress record for a user's question attempt."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO UserProgress (user_id, question_id, selected_answer, is_correct, used_hint, mode)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, question_id, selected_answer, int(is_correct), int(used_hint), mode))
        conn.commit()
        progress_id = cur.lastrowid
        conn.close()
        return True, progress_id, None
    except Exception as e:
        return False, None, f"Error inserting progress: {e}"

def get_user_progress(user_id, mode=None):
    """Retrieve progress records for a user, optionally filtered by mode."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        if mode:
            cur.execute("""
                SELECT progress_id, question_id, selected_answer, is_correct, used_hint, mode, timestamp
                FROM UserProgress
                WHERE user_id = ? AND mode = ?
                ORDER BY timestamp DESC
            """, (user_id, mode))
        else:
            cur.execute("""
                SELECT progress_id, question_id, selected_answer, is_correct, used_hint, mode, timestamp
                FROM UserProgress
                WHERE user_id = ?
                ORDER BY timestamp DESC
            """, (user_id,))
        rows = cur.fetchall()
        conn.close()
        return True, rows, None
    except Exception as e:
        return False, None, f"Error retrieving progress: {e}"
def get_user_progress_summary(user_id):
    """Get a summary of user's progress including total answered, correct, incorrect, and most frequent incorrect topic."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Get total questions answered, correct, and incorrect
        cur.execute("""
            SELECT 
                COUNT(*) as total_answered,
                SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as total_correct,
                SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) as total_incorrect
            FROM UserProgress
            WHERE user_id = ?
        """, (user_id,))
        stats_row = cur.fetchone()
        
        total_answered = stats_row[0] or 0
        total_correct = stats_row[1] or 0
        total_incorrect = stats_row[2] or 0
        
        # Get most frequent incorrect topic ID
        cur.execute("""
            SELECT q.lesson_id, COUNT(*) as incorrect_count
            FROM UserProgress up
            JOIN questions q ON up.question_id = q.question_id
            WHERE up.user_id = ? AND up.is_correct = 0
            GROUP BY q.lesson_id
            ORDER BY incorrect_count DESC
            LIMIT 1
        """, (user_id,))
        topic_row = cur.fetchone()
        
        most_incorrect_topic = topic_row[0] if topic_row else None
        most_incorrect_count = topic_row[1] if topic_row else 0
        
        conn.close()
        
        return True, {
            "total_answered": total_answered,
            "total_correct": total_correct,
            "total_incorrect": total_incorrect,
            "most_incorrect_topic_id": most_incorrect_topic,
            "most_incorrect_count": most_incorrect_count
        }, None
    except Exception as e:
        return False, None, f"Error getting progress summary: {e}"


# ------------------------ UI HELPERS ------------------------
def make_styles(root):
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(
        "Accent.TButton",
        font=("Helvetica", 16, "bold"),
        background=COLORS["accent"],
        foreground="white",
        padding=10,
        borderwidth=0,
        focusthickness=3,
    )
    style.map("Accent.TButton", background=[("active", COLORS["accent_dark"])])

    style.configure(
        "Outline.TButton",
        font=("Helvetica", 16, "bold"),
        background=COLORS["bg"],
        foreground=COLORS["accent"],
        relief="solid",
        bordercolor=COLORS["accent"],
        padding=10,
        borderwidth=2,
        focusthickness=3,
    )

    style.map("Outline.TButton", foreground=[("active", COLORS["accent_dark"])])

def make_modern_radio_style(root):
    style = ttk.Style(root)

    style.configure(
        "Modern.TRadiobutton",
        font=("Helvetica", 16, "bold"),
        background="#124E5E",
        foreground="white",
        padding=10
    )

    style.map(
        "Modern.TRadiobutton",
        background=[("active", COLORS["accent_dark"])],
        foreground=[("selected", COLORS["accent"])]
    )

    style.configure(
        "Modern.TCheckbutton",
        font=("Helvetica", 15, "bold"),
        background="#124E5E",
        foreground="white",
        padding=8
    )

    style.map(
        "Modern.TCheckbutton",
        background=[("active", COLORS["accent_dark"])],
        foreground=[("active", "white"), ("selected", COLORS["accent"])],
        indicatorcolor=[("selected", COLORS["accent"]), ("!selected", "white")]
    )


def H1(parent, text, fg=COLORS["white"], bg=COLORS["bg"]):
    return tk.Label(parent, text=text, font=H1_FONT, fg=fg, bg=bg)

def H2(parent, text, fg=COLORS["white"], bg=COLORS["bg"]):
    return tk.Label(parent, text=text, font=H2_FONT, fg=fg, bg=bg)

def BodyLabel(parent, text, fg=COLORS["muted"], bg=COLORS["bg"], justify="center"):
    return tk.Label(parent, text=text, font=BODY_FONT, fg=fg, bg=bg, justify=justify)


# ------------------------ REUSABLE PROGRESS BAR ------------------------
class ProgressBar(tk.Frame):
    def __init__(self, parent, width=400, height=18, bg="#E0E0E0"):
        super().__init__(parent, bg=bg)
        self.width = width
        self.height = height
        self.canvas = tk.Canvas(self, width=width, height=height, bg=bg, highlightthickness=0)
        self.canvas.pack()
        self.bar = self.canvas.create_rectangle(0, 0, 0, height, fill="#F87171", width=0)  # starts red

    def update_bar(self, fraction):
        """fraction = current progress (0.0 to 1.0)"""
        fraction = max(0, min(1, fraction))
        fill_width = self.width * fraction
        self.canvas.coords(self.bar, 0, 0, fill_width, self.height)

        # change color smoothly: red → yellow → green
        if fraction < 0.33:
            color = "#F87171"   # red
        elif fraction < 0.66:
            color = "#FACC15"   # yellow
        else:
            color = "#6EE7B7"   # green
        self.canvas.itemconfig(self.bar, fill=color)

# ------------------------ APP & SCREENS ------------------------
class NavBar(tk.Frame):
    """Clean top-bar navbar with text links."""
    def __init__(self, parent, app):
        super().__init__(parent, bg="#0B3C49")
        self.app = app
        self.links = {}
        self.current = None

        self.config(height=65, pady=10)

        # Left title
        tk.Label(
            self, text="0001 Chemistry ITS",
            font=("Helvetica", 18, "bold"),
            fg="white", bg="#0B3C49"
        ).pack(side="left", padx=20)

        # Right side links container
        link_frame = tk.Frame(self, bg="#0B3C49")
        link_frame.pack(side="right", padx=20)

        # Define link buttons
        items = [
            ("Menu", "menu"),
            ("Learn", "select_learn_area"),
            ("Practice", "practice_setup"),
            ("Evaluation", "evaluationSetup"),
            ("Progress", "progress"),
        ]

        for text, screen_name in items:
            lbl = tk.Label(
                link_frame,
                text=text,
                font=("Helvetica", 15, "bold"),
                fg="white",
                bg="#0B3C49",
            )
            lbl.pack(side="left", padx=15)
            lbl.bind("<Button-1>", lambda e, s=screen_name: app.switch_to(s))
            lbl.bind("<Enter>", lambda e, l=lbl: l.config(fg=COLORS["accent"]))
            lbl.bind("<Leave>", lambda e, l=lbl: self._reset_color(l))

            self.links[screen_name] = lbl

    def highlight(self, screen_name):
        """Highlight the active page."""
        self.current = screen_name
        for name, lbl in self.links.items():
            if name == screen_name:
                lbl.config(fg=COLORS["accent"], font=("Helvetica", 15, "bold", "underline"))
            else:
                lbl.config(fg="white", font=("Helvetica", 15, "bold"))

    def _reset_color(self, lbl):
        """When hovering out, restore correct colors."""
        for name, item in self.links.items():
            if item == lbl:
                if name == self.current:
                    item.config(fg=COLORS["accent"])
                else:
                    item.config(fg="white")
                return


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("0001 Inc. Chemistry ITS")
        try:
            self.attributes("-fullscreen", True)
        except tk.TclError:
            pass
        self.bind("<F11>", self._toggle_fullscreen)
        self.bind("<Escape>", self._exit_fullscreen)
        self._is_fullscreen = True

        self.configure(bg=COLORS["bg"])
        self.current_user = None
        self.practice_selection = None

        make_styles(self)
        make_modern_radio_style(self)

        self.navbar = NavBar(self, self)

        self.container = tk.Frame(self, bg=COLORS["bg"])
        self.container.pack(fill="both", expand=True)

        self.navbar.pack(fill="x", side="top", before=self.container)

        self.logo_imgtk = None
        try:
            img = Image.open(resource_path("logo.png")).convert("RGBA").resize((100, 110), Image.LANCZOS)
            self.logo_imgtk = ImageTk.PhotoImage(img)
        except Exception:
            self.logo_imgtk = None

        self.screens = {
            "landing": Landing(self.container, self),
            "auth": AuthChoice(self.container, self),
            "login": Login(self.container, self),
            "create": CreateAccountStub(self.container, self),
            "menu": MainMenu(self.container, self),
            "learn": Learn(self.container, self),
            "practice": Practice(self.container, self),
            "results": Results(self.container, self),

            "progress": Progress(self.container, self),
            "evaluationSetup": EvaluationSetup(self.container, self),
            "evaluation": Evaluation(self.container, self),
            "evaluationStub": EvaluationStub(self.container, self),

            "select_learn_area": SelectLearnArea(self.container, self),

            "practice_setup": PracticeSetup(self.container, self),
            "practice_topic_stub": PracticeTopicStub(self.container, self),
        }
        self.switch_to("landing")

        self.after(100, lambda: self.attributes("-fullscreen", True))

    def _toggle_fullscreen(self, _evt=None):
        self._is_fullscreen = not self._is_fullscreen
        try:
            self.attributes("-fullscreen", self._is_fullscreen)
        except tk.TclError:
            pass

    def _exit_fullscreen(self, _evt=None):
        self._is_fullscreen = False
        try:
            self.attributes("-fullscreen", False)
        except tk.TclError:
            pass

    def switch_to(self, name):
        # Prepare screens with dynamic content
        if name == "progress":
            if "progress" in self.screens:
                try:
                    self.screens["progress"].destroy()
                except Exception:
                    pass
            # create a fresh Progress with the current user
            self.screens["progress"] = Progress(self.container, self)
        # Prepare screens with dynamic content
        if name == "practice":
            pr = self.screens["practice"]
            pr.apply_selection_and_prepare()
            pr.reset()
        elif name == "evaluation":
            ev = self.screens["evaluation"]
            ev.apply_selection_and_prepare()
            ev.reset()

        if name in ("landing", "auth", "login", "create"):
            self.navbar.pack_forget()
        else:
            self.navbar.pack(fill="x", side="top", before=self.container)

        # Clear current screen
        for child in self.container.winfo_children():
            child.pack_forget()

        # Show new screen
        self.screens[name].pack(fill="both", expand=True)

        # Highlight correct navbar item
        if hasattr(self, "navbar"):
            self.navbar.highlight(name)
            

# ---------- Screens ----------
class Landing(tk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=COLORS["bg"])
        
        # Add subtle chemistry background
        create_chemistry_background(self)
        
        content = tk.Frame(self, bg=COLORS["bg"])
        content.place(relx=0.5, rely=0.5, anchor="center")

        if app.logo_imgtk:
            tk.Label(content, image=app.logo_imgtk, bg=COLORS["bg"]).pack(pady=(0, 10))
        else:
            tk.Label(content, text="[Logo Missing]", fg=COLORS["white"], bg=COLORS["bg"]).pack()

        tk.Label(content, text="0001 Inc.", font=TITLE_FONT, fg=COLORS["white"], bg=COLORS["bg"]).pack(pady=(5, 0))
        tk.Label(content, text="Chemistry Intelligent Tutoring System",
                 font=SUBTITLE_FONT, fg=COLORS["accent"], bg=COLORS["bg"]).pack(pady=(0, 12))
        BodyLabel(content, "Learn. Adapt. Master Chemistry.\nPersonalized lessons, feedback, and progress tracking."
                 ).pack(pady=(0, 25))

        btn_frame = tk.Frame(content, bg=COLORS["bg"])
        btn_frame.pack(pady=(10, 20))
        ttk.Button(btn_frame, text="Start", style="Accent.TButton",
                   width=20, command=lambda: app.switch_to("auth")).pack(pady=6)

        BodyLabel(content, "© 0001 Inc. 2025 — Chemistry ITS Prototype").pack(pady=(5, 0))

class AuthChoice(tk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=COLORS["bg"])
        
        # Add subtle chemistry background
        create_chemistry_background(self)
        
        content = tk.Frame(self, bg=COLORS["bg"])
        content.place(relx=0.5, rely=0.5, anchor="center")

        H1(content, "Get Started").pack(pady=(0, 8))
        BodyLabel(content, "Choose an option").pack(pady=6)

        btn_frame = tk.Frame(content, bg=COLORS["bg"])
        btn_frame.pack(pady=12)
        ttk.Button(btn_frame, text="Create Account", style="Accent.TButton",
                   width=20, command=lambda: app.switch_to("create")).pack(pady=6)
        ttk.Button(btn_frame, text="Log In", style="Outline.TButton",
                   width=20, command=lambda: app.switch_to("login")).pack(pady=6)

        ttk.Button(content, text="Back", style="Outline.TButton",
                   command=lambda: app.switch_to("landing")).pack(pady=6)

class Login(tk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=COLORS["bg"])
        
        # Add subtle chemistry background
        create_chemistry_background(self)
        
        content = tk.Frame(self, bg=COLORS["bg"])
        content.place(relx=0.5, rely=0.5, anchor="center")

        H1(content, "Login").pack(pady=8)
        BodyLabel(content, 'Enter your username and password').pack(pady=6)

        form = tk.Frame(content, bg=COLORS["bg"])
        form.pack(pady=8)
        tk.Label(form, text="Username", fg=COLORS["white"], bg=COLORS["bg"]).grid(row=0, column=0, sticky="e", padx=6, pady=6)
        tk.Label(form, text="Password", fg=COLORS["white"], bg=COLORS["bg"]).grid(row=1, column=0, sticky="e", padx=6, pady=6)

        self.username = ttk.Entry(form, width=30)
        self.username.grid(row=0, column=1)
        self.password = ttk.Entry(form, width=30, show="•")
        self.password.grid(row=1, column=1)

        self.msg = tk.Label(content, fg="#ff6961", bg=COLORS["bg"])
        self.msg.pack(pady=6)

        row = tk.Frame(content, bg=COLORS["bg"])
        row.pack(pady=6)
        ttk.Button(row, text="Login", style="Accent.TButton",
                   command=lambda: self._do_login(app)).grid(row=0, column=0, padx=6)
        ttk.Button(content, text="Back", style="Outline.TButton",
                   command=lambda: app.switch_to("auth")).pack(pady=6)

    def _do_login(self, app: App):
        u = self.username.get().strip()
        p = self.password.get().strip()
        if not u or not p:
            self.msg.config(text="Please enter both username and password.")
            return
        
        # Ensure Users table exists
        success, error = create_users_table()
        if not success:
            self.msg.config(text=f"Database error: {error}")
            return
        
        # Validate credentials
        valid, user_data = validate_login(u, p)
        if valid:
            app.current_user = user_data
            self.username.delete(0, "end")
            self.password.delete(0, "end")
            self.msg.config(text="")

            # Display progress summary in terminal
            self._display_progress_summary(user_data)
            
            app.switch_to("menu")

        else:
            self.msg.config(text='Invalid username or password.')

    def _display_progress_summary(self, user_data):
        """Display user's progress summary in the terminal."""
        user_id = user_data.get("uid")
        username = user_data.get("username")
        
        print(f"\n{'='*70}")
        print(f"LOGIN SUCCESS - Welcome back, {user_data.get('name')}!")
        print(f"{'='*70}")
        
        # Get progress summary
        success, summary, error = get_user_progress_summary(user_id)
        
        if not success:
            print(f"[PROGRESS] Unable to load progress summary: {error}")
            print(f"{'='*70}\n")
            return
        
        if summary["total_answered"] == 0:
            print(f"[PROGRESS] No questions answered yet. Start practicing to build your progress!")
            print(f"{'='*70}\n")
            return
        
        # Display summary
        total_answered = summary["total_answered"]
        total_correct = summary["total_correct"]
        total_incorrect = summary["total_incorrect"]
        accuracy = (total_correct / total_answered * 100) if total_answered > 0 else 0
        
        print(f"\n[PROGRESS SUMMARY]")
        print(f"  Total Questions Answered: {total_answered}")
        print(f"  Correct Answers: {total_correct} ({accuracy:.1f}%)")
        print(f"  Incorrect Answers: {total_incorrect}")
        
        if summary["most_incorrect_topic_id"] is not None:
            topic_id = summary["most_incorrect_topic_id"]
            incorrect_count = summary["most_incorrect_count"]
            print(f"\n[AREAS FOR IMPROVEMENT]")
            print(f"  Most Frequently Incorrect Topic ID: {topic_id}")
            print(f"  Incorrect Answers in This Topic: {incorrect_count}")
            print(f"  → Consider reviewing this topic for better performance!")
        
        print(f"\n{'='*70}\n")

class CreateAccountStub(tk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=COLORS["bg"])
        
        # Add subtle chemistry background
        create_chemistry_background(self)
        
        content = tk.Frame(self, bg=COLORS["bg"])
        content.place(relx=0.5, rely=0.5, anchor="center")
        
        H1(content, "Create Account").pack(pady=8)
        BodyLabel(content, "Fill in the form below to create your account.").pack(pady=6)

        form = tk.Frame(content, bg=COLORS["bg"])
        form.pack(pady=8)
        
        tk.Label(form, text="Username", fg=COLORS["white"], bg=COLORS["bg"]).grid(row=0, column=0, sticky="e", padx=6, pady=6)
        tk.Label(form, text="First Name", fg=COLORS["white"], bg=COLORS["bg"]).grid(row=1, column=0, sticky="e", padx=6, pady=6)
        tk.Label(form, text="Last Name", fg=COLORS["white"], bg=COLORS["bg"]).grid(row=2, column=0, sticky="e", padx=6, pady=6)
        tk.Label(form, text="Email", fg=COLORS["white"], bg=COLORS["bg"]).grid(row=3, column=0, sticky="e", padx=6, pady=6)
        tk.Label(form, text="Password", fg=COLORS["white"], bg=COLORS["bg"]).grid(row=4, column=0, sticky="e", padx=6, pady=6)
        tk.Label(form, text="Confirm Password", fg=COLORS["white"], bg=COLORS["bg"]).grid(row=5, column=0, sticky="e", padx=6, pady=6)

        self.username = ttk.Entry(form, width=30)
        self.username.grid(row=0, column=1)
        self.fname = ttk.Entry(form, width=30)
        self.fname.grid(row=1, column=1)
        self.lname = ttk.Entry(form, width=30)
        self.lname.grid(row=2, column=1)
        self.email = ttk.Entry(form, width=30)
        self.email.grid(row=3, column=1)
        self.password = ttk.Entry(form, width=30, show="•")
        self.password.grid(row=4, column=1)
        self.confirm_password = ttk.Entry(form, width=30, show="•")
        self.confirm_password.grid(row=5, column=1)

        self.msg = tk.Label(content, fg="#ff6961", bg=COLORS["bg"])
        self.msg.pack(pady=6)

        btn_frame = tk.Frame(content, bg=COLORS["bg"])
        btn_frame.pack(pady=6)
        ttk.Button(btn_frame, text="Create Account", style="Accent.TButton",
                   command=lambda: self._create_account(app)).grid(row=0, column=0, padx=6)
        ttk.Button(content, text="Back", style="Outline.TButton",
                   command=lambda: app.switch_to("auth")).pack(pady=8)

    def _create_account(self, app: App):
        username = self.username.get().strip()
        fname = self.fname.get().strip()
        lname = self.lname.get().strip()
        email = self.email.get().strip()
        password = self.password.get().strip()
        confirm_password = self.confirm_password.get().strip()

        # Validation
        if not all([username, fname, lname, email, password, confirm_password]):
            self.msg.config(text="All fields are required.")
            return

        if password != confirm_password:
            self.msg.config(text="Passwords do not match.")
            return

        if len(password) < 4:
            self.msg.config(text="Password must be at least 4 characters.")
            return

        if "@" not in email or "." not in email:
            self.msg.config(text="Please enter a valid email address.")
            return

        # Ensure table exists
        success, error = create_users_table()
        if not success:
            self.msg.config(text=f"Database error: {error}")
            return

        # Insert user
        success, user_id, error = insert_user(username, fname, lname, email, password)
        if success:
            messagebox.showinfo("Success", f"Account created successfully! Please log in.")
            # Clear form
            self.username.delete(0, "end")
            self.fname.delete(0, "end")
            self.lname.delete(0, "end")
            self.email.delete(0, "end")
            self.password.delete(0, "end")
            self.confirm_password.delete(0, "end")
            self.msg.config(text="")
            app.switch_to("login")
        else:
            self.msg.config(text=error)
            
class MainMenu(tk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=COLORS["bg"])
        
        # Add subtle chemistry background
        create_chemistry_background(self)
        
        content = tk.Frame(self, bg=COLORS["bg"])
        content.place(relx=0.5, rely=0.5, anchor="center")

        H1(content, "Main Menu").pack(pady=8)
        self.greet = tk.Label(content, text="", font=H2_FONT, fg=COLORS["muted"], bg=COLORS["bg"])
        self.greet.pack(pady=4)

        grid = tk.Frame(content, bg=COLORS["bg"])
        grid.pack(pady=12)
        ttk.Button(grid, text="Learn", width=22, style="Accent.TButton",
                   command=lambda: app.switch_to("select_learn_area")).grid(row=0, column=0, padx=8, pady=8)
        ttk.Button(grid, text="Practice", width=22, style="Accent.TButton",
           command=lambda: app.switch_to("practice_setup")).grid(row=0, column=1, padx=8, pady=8)
        ttk.Button(grid, text="View Progress", width=22, style="Accent.TButton",
                   command=lambda: app.switch_to("progress")).grid(row=1, column=0, padx=8, pady=8)
        
        ttk.Button(grid, text="Evaluation", width=22, style="Accent.TButton",
                   command=lambda: app.switch_to("evaluationSetup")).grid(row=1, column=1, padx=8, pady=8)
        
        ttk.Button(grid, text="Logout", width=22, style="Outline.TButton",
                   command=lambda: self.logout(app)).grid(row=3, column=0, padx=8, pady=8)

        self.bind("<<Show>>", lambda e: self._refresh(app))

    def pack(self, *a, **kw):
        super().pack(*a, **kw)
        self.event_generate("<<Show>>", when="tail")

    def _refresh(self, app: App):
        name = app.current_user["name"] if app.current_user else "Guest"
        self.greet.config(text=f"Welcome, {name}! Choose an activity.")
    
    def logout(self, app: App):
        app.current_user = None
        # app.navbar.pack_forget() 
        app.switch_to("login")


class SelectLearnArea(tk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        
        # Add subtle chemistry background
        create_chemistry_background(self)

        content = tk.Frame(self, bg=COLORS["bg"])
        content.place(relx=0.5, rely=0.5, anchor="center")

        H1(content, "Select Area of Learning").pack(pady=(0, 12))

        all_lessons, warn = load_lessons()
        if warn:
            messagebox.showwarning("Notice", warn)

        # Group lessons by topic name (strip (a), (b), etc.)
        grouped_topics = {}
        for i, lesson in enumerate(all_lessons):
            base_name = lesson["title"].split("(")[0].strip()
            if base_name not in grouped_topics:
                grouped_topics[base_name] = []
            grouped_topics[base_name].append(i)

        self.topics = list(grouped_topics.keys())
        self.topic_index_map = grouped_topics

        self.selected_topic = tk.StringVar(value="")
        topic_frame = tk.Frame(content, bg=COLORS["bg"])
        topic_frame.pack(pady=10)

        # --- Improved modern topic buttons ---
        for i, topic in enumerate(self.topics, start=1):
            pretty_name = topic.replace("PeriodicTable", "Periodic Table").strip()
            display_name = f"Topic {i}: {pretty_name}"

            # Create a frame to act as a "card" container
            card = tk.Frame(topic_frame, bg="#124E5E", highlightbackground=COLORS["accent"], highlightthickness=2)
            card.pack(fill="x", padx=20, pady=6)

            # Create the actual radio button inside the card
            btn = ttk.Radiobutton(
                card,
                text=display_name,
                value=topic,
                variable=self.selected_topic,
                style="Modern.TRadiobutton"
            )
            btn.pack(fill="x", padx=20, pady=10)


        btn_frame = tk.Frame(content, bg=COLORS["bg"])
        btn_frame.pack(pady=20)

        ttk.Button(
            btn_frame,
            text="← Back",
            style="Outline.TButton",
            command=lambda: app.switch_to("menu")
        ).grid(row=0, column=0, padx=10)

        ttk.Button(
            btn_frame,
            text="Start Learning!",
            style="Accent.TButton",
            command=self.start_learning
        ).grid(row=0, column=1, padx=10)

        self.all_lessons = all_lessons

    def start_learning(self):
        topic = self.selected_topic.get()
        if not topic:
            messagebox.showwarning("Notice", "Please select a topic to continue.")
            return

        lesson_indices = self.topic_index_map[topic]

        learn_screen: Learn = self.app.screens["learn"]
        learn_screen.lessons = [self.all_lessons[i] for i in lesson_indices]
        learn_screen.index = 0
        learn_screen.render()
        self.app.switch_to("learn")


class Learn(tk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        
        # Add subtle chemistry background
        create_chemistry_background(self)

        content = tk.Frame(self, bg=COLORS["bg"])
        content.place(relx=0.5, rely=0.5, anchor="center")

        H1(content, "Learn").pack(pady=6)

        self.lessons, warn = load_lessons()
        if warn:
            messagebox.showwarning("Notice", warn)
        self.index = 0

        self.title = tk.Label(content, text="", font=H2_FONT, fg=COLORS["white"], bg=COLORS["bg"])
        self.title.pack(pady=4)
        self.lesson_image = tk.Label(content, bg=COLORS["bg"])
        self.lesson_image.pack(pady=4)


        self.body = tk.Label(
            content,
            text="",
            font=BODY_FONT,
            fg=COLORS["white"],
            bg=COLORS["bg"],
            wraplength=600,
            justify="left"
        )

        self.body.pack(fill="both", expand=True, padx=4, pady=8)

        # Function to reset lesson index after returning to main menu and switch
        def reset_and_switch():
            self.index = 0
            self.render()
            app.switch_to("menu")

        # --- Subtopic buttons (a,b,c,...) ---
        self.subtopic_frame = tk.Frame(content, bg=COLORS["bg"])
        self.subtopic_frame.pack(pady=(4, 10))

        # Progress bar for lessons
        self.progress_bar = ProgressBar(content)
        self.progress_bar.pack(pady=(4, 6))
        self.progress_label = BodyLabel(content, "", fg=COLORS["white"])
        self.progress_label.pack(pady=(0, 10))

        # Navigation frame and buttons
        self.nav = tk.Frame(content, bg=COLORS["bg"])
        self.nav.pack(pady=8)

        self.btn_next = ttk.Button(self.nav, text="Next", style="Accent.TButton", command=self.next_lesson)
        self.btn_next.grid(row=0, column=0, padx=6)

        self.btn_menu = ttk.Button(self.nav, text="Return to Menu", style="Outline.TButton",
                                   command=reset_and_switch)
        self.btn_menu.grid(row=0, column=1, padx=6)

        self.render() 

    # ------------------------ Subtopic Buttons ------------------------
    def render_subtopic_buttons(self):
        # Clear existing buttons
        for widget in self.subtopic_frame.winfo_children():
            widget.destroy()

        if not self.lessons:
            return

        current_title = self.lessons[self.index]['title']
        base_name = current_title.split('(')[0].strip()

        # Find all related subtopics (like Matter(a), Matter(b), etc.)
        related = [(i, l) for i, l in enumerate(self.lessons)
                   if l['title'].startswith(base_name)]

        # If only one subtopic, skip showing buttons
        if len(related) <= 1:
            return

        for i, l in related:
            # extract (a), (b), etc.
            label = ""
            if '(' in l['title']:
                label = l['title'].split('(')[-1].replace(')', '')
            else:
                label = str(i + 1)

            btn = ttk.Button(
                self.subtopic_frame,
                text=label,
                style="Outline.TButton",
                width=4,
                command=lambda idx=i: self.go_to_subtopic(idx)
            )
            btn.pack(side="left", padx=4)

            # Disable button for current subtopic
            if i == self.index:
                btn.state(["disabled"])

    def go_to_subtopic(self, idx):
        self.index = idx
        self.render()

    # ------------------------ Main Rendering ------------------------
    def render(self):
        """Display current lesson content or an end-of-topic message."""
        # When all lessons in this topic are finished:
        if self.index >= len(self.lessons):
            select_screen: SelectLearnArea = self.app.screens["select_learn_area"]
            topics = select_screen.topics

            # Find current topic name
            current_topic = None
            for t, idxs in select_screen.topic_index_map.items():
                if self.lessons and select_screen.all_lessons.index(self.lessons[0]) in idxs:
                    current_topic = t
                    break

            cur_idx = topics.index(current_topic) if current_topic else -1
            next_topic = topics[cur_idx + 1] if cur_idx != -1 and cur_idx + 1 < len(topics) else None

            msg_lines = [f"Great job completing {current_topic}!"]
            if next_topic:
                msg_lines.append(f"Next up: {next_topic}.")
            else:
                msg_lines.append("You've completed all available topics!")

            msg_lines.append("You can now move on to the next topic or return to the main menu.")
            end_message = "\n\n".join(msg_lines)

            self.title.config(text=f"{current_topic} Complete!")
            self.body.config(text=end_message)


            for w in self.nav.winfo_children():
                w.destroy()

            if next_topic:
                ttk.Button(
                    self.nav, text=f"Next Topic →", style="Accent.TButton",
                    command=lambda: self.goto_next_topic(next_topic)
                ).grid(row=0, column=0, padx=6)
            ttk.Button(
                self.nav, text="Return to Menu", style="Outline.TButton",
                command=lambda: self.app.switch_to("menu")
            ).grid(row=0, column=1, padx=6)
            return

        # Otherwise, show current lesson normally
        lesson = self.lessons[self.index]
        self.title.config(text=f"{self.index+1}. {lesson['title']}")
        self.body.config(text=lesson["body"])
        # --- Render lesson image if available ---
        img_path = lesson.get("image", "").strip()
        if img_path:
            full_path = resource_path(os.path.join("cutouts", img_path))
            if os.path.exists(full_path):
                try:
                    img = Image.open(full_path).resize((900, 450), Image.LANCZOS)
                    self.lesson_imgtk = ImageTk.PhotoImage(img)
                    self.lesson_image.config(image=self.lesson_imgtk)
                except Exception:
                    self.lesson_image.config(image="", text="[Error loading image]", fg="white")
            else:
                self.lesson_image.config(image="", text="[Image not found]", fg="white")
        else:
            self.lesson_image.config(image="", text="")



        for w in self.nav.winfo_children():
            w.destroy()
        self.btn_next = ttk.Button(self.nav, text="Next", style="Accent.TButton", command=self.next_lesson)
        self.btn_next.grid(row=0, column=0, padx=6)
        self.btn_menu = ttk.Button(self.nav, text="Return to Menu", style="Outline.TButton",
                                   command=lambda: self.app.switch_to("menu"))
        self.btn_menu.grid(row=0, column=1, padx=6)

        # Refresh subtopic buttons
        self.render_subtopic_buttons()
        # --- Update progress bar based on subtopic completion ---
        current_title = self.lessons[self.index]['title']
        base_name = current_title.split('(')[0].strip()
        related = [l for l in self.lessons if l['title'].startswith(base_name)]

        if related:
            current_pos = [l['title'] for l in related].index(self.lessons[self.index]['title'])
            fraction = (current_pos + 1) / len(related)
            self.progress_bar.update_bar(fraction)
            self.progress_label.config(text=f"{int(fraction * 100)}% of {base_name} completed")
        else:
            # Single-topic lesson
            self.progress_bar.update_bar(1)
            self.progress_label.config(text=f"100% of {base_name} completed")


    def next_lesson(self):
        self.index += 1
        self.render()

    def goto_next_topic(self, next_topic):
        select_screen: SelectLearnArea = self.app.screens["select_learn_area"]
        lesson_indices = select_screen.topic_index_map[next_topic]
        self.lessons = [select_screen.all_lessons[i] for i in lesson_indices]
        self.index = 0
        self.render()



class Practice(tk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app

        # --- Load questions and initialize state ---
        self.all_questions, warn = load_questions()
        if warn:
            messagebox.showwarning("Notice", warn)

        self.questions = []
        self.q_idx = 0
        self.choice = tk.IntVar(value=-1)
        self.state = []  # holds {"selected": int, "is_correct": bool, "feedback": str, "used_hint": bool, ...}

        content = tk.Frame(self, bg=COLORS["bg"])
        content.pack(fill="both", expand=True)
        
        # Add subtle chemistry background to the content frame
        bg_canvas = create_chemistry_background(content)

        # --- TOP NAVBAR ---
        top_nav = tk.Frame(content, bg=COLORS["bg"])
        top_nav.pack(fill="x", pady=(10, 0))
        top_nav.grid_columnconfigure(0, weight=1)
        top_nav.grid_columnconfigure(1, weight=1)

        self.btn_menu = ttk.Button(top_nav, text="← Back to Topics", style="Outline.TButton",
                                   command=lambda: self.app.switch_to("practice_setup"))
        self.btn_menu.grid(row=0, column=0, sticky="w", padx=20)

        self.btn_finish = ttk.Button(top_nav, text="End Practice", style="Accent.TButton",
                                     command=self.finish)
        self.btn_finish.grid(row=0, column=1, sticky="e", padx=20)

        # --- MAIN BODY ---
        body = tk.Frame(content, bg=COLORS["bg"])
        body.pack(expand=True)
        
        # Ensure all content widgets are above the background canvas
        top_nav.lift()
        body.lift()

        H1(body, "Practice Questions").pack(pady=6)

        self.progress_bar = ProgressBar(body)
        self.progress_bar.pack(pady=(4, 10))
        self.progress_label = BodyLabel(body, "", fg=COLORS["white"])
        self.progress_label.pack(pady=(0, 8))

        # --- Question text ---
        self.qtext = tk.Label(
            body,
            text="",
            fg=COLORS["white"],
            bg=COLORS["bg"],
            wraplength=820,
            font=("Helvetica", 18, "bold"),
            justify="center",
        )
        self.qtext.pack(pady=(10, 20))

        # --- Answer options ---
        self.opts = tk.Frame(body, bg=COLORS["bg"])
        self.opts.pack(pady=(0, 10))

        # --- Image BELOW answers ---
        self.qimage_label = tk.Label(body, bg=COLORS["bg"])
        self.qimage_label.pack(pady=(25, 0), anchor="center")


        controls_center = tk.Frame(body, bg=COLORS["bg"])
        controls_center.pack(pady=16)

        self.btn_hint = ttk.Button(controls_center, text="Hint", style="Outline.TButton", command=self.hint)
        self.btn_hint.pack(side="left", padx=8)
        self.btn_submit = ttk.Button(controls_center, text="Check Answer", style="Accent.TButton",
                                     command=self.check_answer)
        self.btn_submit.pack(side="left", padx=8)

        self.feedback = tk.Label(body, text="", fg=COLORS["muted"], bg=COLORS["bg"],
                                 wraplength=820, justify="left", font=("Helvetica", 16))
        self.feedback.pack(pady=(10, 0))

        # --- FOOTER NAVIGATION ---
        footer = tk.Frame(content, bg=COLORS["bg"])
        footer.pack(fill="x", pady=(0, 20))
        footer.grid_columnconfigure(0, weight=1)
        footer.grid_columnconfigure(1, weight=1)

        self.btn_prev = ttk.Button(footer, text="← Previous", style="Outline.TButton",
                                   command=self.prev_q)
        self.btn_prev.grid(row=0, column=0, sticky="w", padx=20)

        self.btn_next = ttk.Button(footer, text="Next →", style="Outline.TButton",
                                   command=self.next_q)
        self.btn_next.grid(row=0, column=1, sticky="e", padx=20)
        
        # Ensure footer is above background
        footer.lift()

    def apply_selection_and_prepare(self):
        selection = self.app.practice_selection
        if not selection:
            return

        lesson_ids = selection.get("lesson_ids", [])
        user = self.app.current_user

        # --- Load DB ---
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # --- Use IRT if user exists ---
        if user:
            q_ids = its_functions.get_adaptive_questions(
                cursor=cur,
                user_id=user["uid"],
                lesson_ids=lesson_ids,
                n_per_topic=5
            )
        else:
            q_ids = []

        # --- Map IDs → full question objects ---
        q_map = {q["id"]: q for q in self.all_questions}
        self.questions = [q_map[qid] for qid in q_ids if qid in q_map]

        # --- Fallback if nothing found ---
        if not self.questions:
            self.questions = [
                q for q in self.all_questions
                if q["topic_id"] in lesson_ids
            ]
            random.shuffle(self.questions)

        self.q_idx = 0
        self.state = []
        conn.close()


    def reset(self):
        """Reset progress and UI."""
        self.q_idx = 0
        self.choice.set(-1)
        self.feedback.config(text="", fg=COLORS["muted"])
        self.state = [{} for _ in self.questions]
        self.render()
    
    def _update_next_button_state(self):
        """Disable Next until the current question has been checked."""
        if not self.questions:
            self.btn_next.state(["disabled"])
            return

        # Last question: no "next" anyway
        if self.q_idx >= len(self.questions) - 1:
            self.btn_next.state(["disabled"])
            return

        saved = self.state[self.q_idx]
        # Treat "feedback" existing as "user clicked Check Answer"
        if "feedback" in saved:
            self.btn_next.state(["!disabled"])
        else:
            self.btn_next.state(["disabled"])

    # ---------- Render ----------
    def render(self):
        if not self.questions:
            self.qtext.config(text="No questions available.")
            for w in self.opts.winfo_children():
                w.destroy()
            for b in (self.btn_submit, self.btn_hint, self.btn_next, self.btn_prev):
                b.state(["disabled"])
            self.feedback.config(text="")
            return

        # Progress
        progress = (self.q_idx + 1) / len(self.questions)
        self.progress_bar.update_bar(progress)
        self.progress_label.config(text=f"Question {self.q_idx + 1} of {len(self.questions)}")

        q = self.questions[self.q_idx]
        self.qtext.config(text=q["text"])
        # --- Render image if available ---
        img_path = q.get("image", "").strip()

        if img_path:
            full_path = resource_path(os.path.join("cutouts", img_path))

            if os.path.exists(full_path):
                try:
                    img = Image.open(full_path).resize((90, 90), Image.LANCZOS)  # adjust size
                    self.qimgtk = ImageTk.PhotoImage(img)
                    self.qimage_label.config(image=self.qimgtk)
                except Exception:
                    self.qimage_label.config(image="", text="[Error loading image]", fg="white")
            else:
                self.qimage_label.config(image="", text="[Image not found]", fg="white")
        else:
            self.qimage_label.config(image="", text="")


        # Enable/disable navigation
        self.btn_prev.state(["!disabled"] if self.q_idx > 0 else ["disabled"])
        self._update_next_button_state()

        # Clear old options
        for w in self.opts.winfo_children():
            w.destroy()

        # Restore saved state
        saved = self.state[self.q_idx]
        selected_before = saved.get("selected", -1)
        self.choice.set(selected_before)

        # --- Create radio buttons with auto-save ---
        for i, c in enumerate(q["choices"]):
            rb = tk.Radiobutton(
                self.opts,
                text=c,
                variable=self.choice,
                value=i,
                fg=COLORS["white"],
                bg=COLORS["bg"],
                activebackground=COLORS["bg"],
                selectcolor=COLORS["bg"],
                anchor="w",
                justify="left",
                font=("Helvetica", 16),
                command=self._auto_save_selection  # auto-save when selected
            )
            rb.pack(anchor="w")

        # Restore feedback (if they had checked the answer)
        if "feedback" in saved:
            self.feedback.config(text=saved["feedback"], fg=saved.get("color", COLORS["muted"]))
        else:
            self.feedback.config(text="", fg=COLORS["muted"])

    def _auto_save_selection(self):
        """Auto-save selection immediately when user clicks a choice."""
        sel = self.choice.get()
        if sel == -1:
            return
        # Save current selection (no feedback yet)
        self.state[self.q_idx]["selected"] = sel
        self.state[self.q_idx].pop("feedback", None)
        self.state[self.q_idx].pop("color", None)
        self.feedback.config(text="", fg=COLORS["muted"])

    def check_answer(self):
        """Show feedback for current answer without locking question."""
        if self.choice.get() == -1:
            self.feedback.config(text="Please select an answer first.", fg=COLORS["bad"])
            return

        q = self.questions[self.q_idx]
        selected = self.choice.get()
        correct_idx = int(q["answer_index"])
        correct_choice = q["choices"][correct_idx]
        is_correct = selected == correct_idx

        detail = q.get("explanation", "").strip()
        if is_correct:
            msg = f"Correct! {detail}" if detail else "Correct!"
            color = COLORS["ok"]
        else:
            msg = f"Incorrect. Correct answer: {correct_choice}."
            if detail:
                msg += f"\n{detail}"
            color = COLORS["bad"]

        self.feedback.config(text=msg, fg=color)
        self.state[self.q_idx].update({
            "selected": selected,
            "is_correct": is_correct,
            "feedback": msg,
            "color": color,
        })
        self._update_next_button_state()

        # Save progress to database
        self._save_progress_to_db()
    
    def _save_progress_to_db(self):
        """Save the current question's progress to the database."""
        if not self.app.current_user:
            print("[TRACKING] No user logged in - skipping progress save")
            return
        
        saved = self.state[self.q_idx]
        if "is_correct" not in saved:
            return  # Not yet checked
        
        # Ensure progress table exists
        success, error = create_progress_table()
        if not success:
            print(f"[TRACKING ERROR] Could not create progress table: {error}")
            return
        
        q = self.questions[self.q_idx]
        user_id = self.app.current_user.get("uid")
        question_id = q.get("id")
        selected_answer = q["choices"][saved["selected"]] if saved.get("selected") is not None else None
        is_correct = saved.get("is_correct", False)
        used_hint = saved.get("used_hint", False)
        mode = "practice"

        print(f"\n{'='*60}")
        print(f"[TRACKING] Saving Practice Progress:")
        print(f"  User ID: {user_id} ({self.app.current_user.get('username')})")
        print(f"  Question ID: {question_id}")
        print(f"  Question: {q.get('text', '')[:50]}...")
        print(f"  Selected Answer: {selected_answer}")
        print(f"  Correct: {is_correct}")
        print(f"  Used Hint: {used_hint}")
        print(f"  Mode: {mode}")
        
        success, progress_id, error = insert_progress(
            user_id, question_id, selected_answer, is_correct, used_hint, mode
        )
        
        if success:
            print(f"  ✓ Progress saved successfully (Progress ID: {progress_id})")
        else:
            print(f"  ✗ Failed to save progress: {error}")
        print(f"{'='*60}\n")

    # ---------- Navigation ----------
    def next_q(self):
        """Go to next question."""
        if self.q_idx < len(self.questions) - 1:
            self.q_idx += 1
            self.render()

    def prev_q(self):
        """Go to previous question."""
        if self.q_idx > 0:
            self.q_idx -= 1
            self.render()

    # ---------- Hint ----------
    def hint(self):
        q = self.questions[self.q_idx]
        # Mark that user used hint for this question
        if "used_hint" not in self.state[self.q_idx]:
            self.state[self.q_idx]["used_hint"] = True
        messagebox.showinfo("Hint", q.get("hint", "No hint available."))

    # ---------- Finish ----------
    def finish(self):
        """Submit all answers and show results."""
        # Mark correctness for all answered questions
        for i, s in enumerate(self.state):
            if "selected" in s and "is_correct" not in s:
                q = self.questions[i]
                s["is_correct"] = (s["selected"] == int(q["answer_index"]))
        
        user = self.app.current_user
        if user:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()

            selector = its_functions.IRTQuestionSelector(cur)
            selector.train_model()

            theta = selector.estimate_student_ability(user["uid"])

            its_functions.save_student_ability(cur, user["uid"], theta)
            conn.commit()
            conn.close()

        results_screen = self.app.screens["results"]
        self.app.last_mode = "practice"
        self.app.last_practice_selection = getattr(self.app, "practice_selection", None)
        results_screen.set_results(self.questions, self.state)
        self.app.switch_to("results")


class Results(tk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        
        # Add subtle chemistry background
        create_chemistry_background(self)
        
        # Outer container for centering
        outer = tk.Frame(self, bg=COLORS["bg"])
        outer.place(relx=0.5, rely=0.5, anchor="center")
        
        # Dynamic title (Practice vs Evaluation)
        self.title_label = H1(outer, "")
        self.title_label.pack(pady=8)
        
        # Score display
        self.score_label = tk.Label(outer, text="", font=("Helvetica", 18, "bold"), 
                                    fg=COLORS["accent"], bg=COLORS["bg"])
        self.score_label.pack(pady=8)
        
        self.summary_label = tk.Label(outer, text="", font=("Helvetica", 14), 
                                      fg=COLORS["muted"], bg=COLORS["bg"])
        self.summary_label.pack(pady=4)
        
        # Scrollable area for answers
        scroll_frame = tk.Frame(outer, bg=COLORS["bg"])
        scroll_frame.pack(pady=12, fill="both", expand=True)
        
        canvas = tk.Canvas(scroll_frame, bg=COLORS["bg"], width=900, height=400, highlightthickness=0)
        scrollbar = tk.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview)
        
        self.scrollable_content = tk.Frame(canvas, bg=COLORS["bg"])
        self.scrollable_content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons
        btn_row = tk.Frame(outer, bg=COLORS["bg"])
        btn_row.pack(pady=12)
        ttk.Button(btn_row, text="Try Again", style="Accent.TButton",
                  command=self.retry).grid(row=0, column=0, padx=6)
        ttk.Button(btn_row, text="Back to Menu", style="Outline.TButton",
                  command=lambda: self.app.switch_to("menu")).grid(row=0, column=1, padx=6)

    def set_results(self, questions, state):
        mode = getattr(self.app, "last_mode", "practice")
        is_eval = (mode == "evaluation")

        self.title_label.config(text="Evaluation Results" if is_eval else "Practice Results")

        total_qs = len(questions)
        answered = [s for s in state if "selected" in s and s.get("selected") not in (-1, None)]
        correct_count = sum(1 for s in state if s.get("is_correct", False))

        denom = total_qs if is_eval else len(answered)
        score_pct = (correct_count / denom * 100) if denom else 0.0

        self.score_label.config(text=f"Score: {score_pct:.1f}%")
        self.summary_label.config(
            text=f"{correct_count} correct out of {denom} {'questions' if is_eval else 'answered'}"
        )

        # Clear existing results
        for widget in self.scrollable_content.winfo_children():
            widget.destroy()

        # Which questions to show
        if is_eval:
            indices_to_show = range(len(questions))              # show all, even unanswered
        else:
            indices_to_show = [i for i, s in enumerate(state)    # show only answered in Practice
                            if s.get("selected") not in (-1, None)]

        if not indices_to_show:
            tk.Label(self.scrollable_content, text="No questions were answered.",
                    font=("Helvetica", 13, "bold"),
                    fg=COLORS["muted"], bg=COLORS["bg"]).pack(pady=20)
            return

        # Render each row
        for i in indices_to_show:
            q = questions[i]
            s = state[i]
            selected = s.get("selected", None)
            has_answer = (selected is not None) and (selected != -1)
            is_correct = bool(s.get("is_correct", False)) if has_answer else False

            # Color: green if correct, muted if wrong, light gray if unanswered
            if not has_answer:
                bg_color = "#F5F5F5"  # unanswered
            else:
                bg_color = "#E6FFFA" if is_correct else COLORS["muted"]
            fg_title = "#000000"

            q_frame = tk.Frame(self.scrollable_content, bg=bg_color, relief="solid", borderwidth=1)
            q_frame.pack(fill="x", padx=10, pady=8)

            tk.Label(q_frame, text=f"Question {i+1}:", font=("Helvetica", 14, "bold"),
                    fg=fg_title, bg=bg_color, anchor="w").pack(anchor="w", padx=10, pady=(10, 2))
            tk.Label(q_frame, text=q["text"], font=("Helvetica", 14),
                    fg=fg_title, bg=bg_color, anchor="w",
                    wraplength=850, justify="left").pack(anchor="w", padx=10, pady=2)

            # Show user answer or "Not answered"
            if has_answer:
                your_choice = q["choices"][selected]
                tk.Label(q_frame, text=f"Your answer: {your_choice}",
                        font=("Helvetica", 14),
                        fg=COLORS["ok"] if is_correct else COLORS["bad"],
                        bg=bg_color, anchor="w").pack(anchor="w", padx=10, pady=2)
            else:
                tk.Label(q_frame, text="Your answer: Not answered",
                        font=("Helvetica", 14),
                        fg="#9E9E9E", bg=bg_color, anchor="w").pack(anchor="w", padx=10, pady=2)

            # Always show the correct answer
            correct_choice = q["choices"][int(q["answer_index"])]
            if (not has_answer) or (has_answer and not is_correct):
                tk.Label(q_frame, text=f"Correct answer: {correct_choice}",
                        font=("Helvetica", 14), fg=COLORS["ok"], bg=bg_color,
                        anchor="w").pack(anchor="w", padx=10, pady=2)

            # Optional explanation
            if q.get("explanation"):
                tk.Label(q_frame, text=f"Explanation: {q['explanation']}",
                        font=("Helvetica", 14, "italic"), fg="#424242",
                        bg=bg_color, anchor="w", wraplength=850,
                        justify="left").pack(anchor="w", padx=10, pady=(2, 10))

    def retry(self):
        mode = getattr(self.app, "last_mode", "practice")

        if mode == "evaluation":
            if getattr(self.app, "last_evaluation_selection", None):
                self.app.evaluation_selection = self.app.last_evaluation_selection
            ev = self.app.screens["evaluation"]
            ev.reset()
            self.app.switch_to("evaluation")
        else:
            if getattr(self.app, "last_practice_selection", None):
                self.app.practice_selection = self.app.last_practice_selection
            pr = self.app.screens["practice"]
            pr.reset()
            self.app.switch_to("practice")


class Progress(tk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app

        user = self.app.current_user
        user_id = user["uid"] if user else None

        # default values
        overall_pct = 0.0
        total_mastered = 0       # distinct questions correct at least once
        total_questions = 0

        practice_pct = 0.0
        evaluation_pct = 0.0

        topic_stats = []         # list of {lesson_name, topic_ids, total, correct, pct}
        coverage_stats = {
            "attempted": 0,
            "total_questions": 0,
            "coverage_pct": 0.0,
        }
        hint_stats = {
            "total": 0,
        }
        recent_stats = {
            "recent_total": 0,
            "recent_correct": 0,
            "recent_pct": 0.0,
        }

        weakest_topic_id = None
        strongest_topic_id = None

        # pull stats from DB using its_functions
        if user_id is not None:
            try:
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()

                ability_history = its_functions.get_ability_history(cur, user_id)

                if ability_history:
                    latest_theta = ability_history[-1][0]
                    ability_label = its_functions.theta_to_level(latest_theta)
                else:
                    latest_theta = 0.0
                    ability_label = "New Learner"

                # Overall mastery (based on distinct questions ever correct)
                total_questions = its_functions.overall_total_questions(cur)
                total_mastered = its_functions.overall_total_correct(cur, user_id)
                if total_questions > 0:
                    # overall_percent returns a fraction (0..1), convert to %
                    overall_pct = its_functions.overall_percent(cur, user_id) * 100.0

                # By mode (practice vs evaluation)
                practice_pct = its_functions.mode_correct_percent(cur, user_id, "practice")
                evaluation_pct = its_functions.mode_correct_percent(cur, user_id, "evaluation")

                # Per-topic stats, coverage, and hints
                topic_stats = []
                hints_total = 0
                cov_total = 0
                cov_seen = 0

                for topic_name, lesson_ids in TOPICS.items():
                    agg_total = 0
                    agg_correct = 0
                    agg_seen = 0
                    agg_hints = 0
                    agg_eval_attempts = 0

                    for topic_id in lesson_ids:
                        # how many questions exist in this lesson/topic
                        t_total = its_functions.topic_total_questions(cur, topic_id)
                        # how many of them user has ever got correct at least once
                        t_correct = its_functions.topic_total_correct(cur, user_id, topic_id)
                        # seen% and convert back to a count
                        t_seen_pct = its_functions.topic_seen_percent(cur, user_id, topic_id)  # 0..100
                        t_seen = round(t_total * (t_seen_pct / 100.0))
                        # hints used in this topic
                        t_hints = its_functions.topic_hints_used(cur, user_id, topic_id)

                        # any evaluation attempts on this lesson_id?
                        cur.execute("""
                            SELECT COUNT(*)
                            FROM UserProgress up
                            JOIN questions q ON up.question_id = q.question_id
                            WHERE up.user_id = ? AND up.mode = 'evaluation' AND q.lesson_id = ?
                        """, (user_id, topic_id))
                        eval_count = cur.fetchone()[0] or 0

                        agg_total += t_total
                        agg_correct += t_correct
                        agg_seen += t_seen
                        agg_hints += t_hints
                        agg_eval_attempts += eval_count
                    # If user hasn't seen any questions in this topic → pct = None
                    if agg_total > 0 and agg_seen > 0:
                        pct = (agg_correct / agg_total) * 100.0
                    else:
                        pct = None

                    topic_stats.append({
                        "lesson_name": topic_name,
                        "topic_ids": list(lesson_ids),
                        "total": agg_total,
                        "correct": agg_correct,
                        "pct": pct,              # may be None
                        "seen": agg_seen,        # we need this later
                        "eval_attempts": agg_eval_attempts,
                        "has_eval": agg_eval_attempts > 0,
                    })

                    hints_total += agg_hints
                    cov_total += agg_total
                    cov_seen += agg_seen

                # Coverage across all topics
                if cov_total > 0:
                    cov_pct = (cov_seen / cov_total) * 100.0
                else:
                    cov_pct = 0.0

                coverage_stats = {
                    "attempted": cov_seen,
                    "total_questions": cov_total,
                    "coverage_pct": cov_pct,
                }

                hint_stats = {
                    "total": hints_total,
                }

                # Weakest / strongest topic
                if total_questions > 0:
                    try:
                            weakest_topic_id = its_functions.weak_topic(cur, user_id)
                            strongest_topic_id = its_functions.strong_topic(cur, user_id)
                    except Exception:
                        weakest_topic_id = None
                        strongest_topic_id = None
    
                    # Recent activity (last 20 "slots" using their helper)
                    recent_window = 20
                    recent_pct = its_functions.recent_correct_percent(cur, user_id, recent_window)  # 0..100
                    recent_correct = int(round(recent_pct * recent_window / 100.0))
                    recent_stats = {
                        "recent_total": recent_window,
                        "recent_correct": recent_correct,
                        "recent_pct": recent_pct,
                    }
            except Exception as e:
                print(f"[PROGRESS ERROR] Failed to load progress data: {e}")
                # Keep defaults if database query fails
                

        # Scrollable layout - transparent to show background
        canvas = tk.Canvas(self, bg=COLORS["bg"], highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=COLORS["bg"])
        
        # Add subtle chemistry background to the scrollable area
        create_chemistry_background(scroll_frame)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor="n", width=self.winfo_screenwidth())
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        outer = tk.Frame(scroll_frame, bg=COLORS["bg"])
        outer.pack(padx=80, pady=40, fill="both", expand=True)

        # Header
        H1(outer, "📊 Progress Overview").pack(pady=(0, 6))

        subtitle = "Your learning performance summary."
        if user is not None:
            subtitle = f"Progress for {user.get('name', user.get('username', 'Student'))}."
        BodyLabel(outer, subtitle, fg=COLORS["muted"]).pack(pady=(0, 18))

        if user_id is None:
            BodyLabel(
                outer,
                "No user is logged in. Log in to start tracking your progress.",
                fg=COLORS["muted"]
            ).pack(pady=20)
            return

        # Top Stats Row
        stats_row = tk.Frame(outer, bg=COLORS["bg"])
        stats_row.pack(fill="x", pady=(0, 30))

        # Card 1: Overall mastery
        card1 = tk.Frame(stats_row, bg="#1A3A4A", relief="flat", borderwidth=0)
        card1.pack(side="left", fill="both", expand=True, padx=8)

        card1_inner = tk.Frame(card1, bg="#1A3A4A")
        card1_inner.pack(padx=20, pady=15, fill="x")

        # Make this a bold section title
        tk.Label(
            card1_inner,
            text="Overall Score",
            font=("Helvetica", 15, "bold"),
            fg=COLORS["muted"], bg="#1A3A4A"
        ).pack(anchor="w")

        if total_questions > 0:
            tk.Label(
                card1_inner,
                text=f"{overall_pct:.1f}%",
                font=("Helvetica", 32, "bold"),
                fg="#6EE7B7", bg="#1A3A4A"
            ).pack(pady=(5, 0), anchor="w")
        else:
            tk.Label(
                card1_inner,
                text="No questions in database",
                font=("Helvetica", 18, "bold"),
                fg="#FACC15", bg="#1A3A4A"
            ).pack(pady=(5, 0), anchor="w")

        # Card 2: Practice vs Evaluation
        card2 = tk.Frame(stats_row, bg="#1A3A4A", relief="flat", borderwidth=0)
        card2.pack(side="left", fill="both", expand=True, padx=8)

        card2_inner = tk.Frame(card2, bg="#1A3A4A")
        card2_inner.pack(padx=20, pady=15, fill="x")

        tk.Label(
            card2_inner,
            text="By Mode",
            font=("Helvetica", 15, "bold"), 
            fg=COLORS["muted"], bg="#1A3A4A"
        ).pack(anchor="w")

        # Single-line style: "Practice: 37.5% accuracy"
        tk.Label(
            card2_inner,
            text=f"Practice: {practice_pct:.1f}% accuracy",
            font=("Helvetica", 14),
            fg="#6EE7B7", bg="#1A3A4A"
        ).pack(anchor="w", pady=(10, 4))

        tk.Label(
            card2_inner,
            text=f"Evaluation: {evaluation_pct:.1f}% accuracy",
            font=("Helvetica", 14),
            fg="#FB923C", bg="#1A3A4A"
        ).pack(anchor="w", pady=(2, 0))

        # Card 3: Coverage & Hints
        card3 = tk.Frame(stats_row, bg="#1A3A4A", relief="flat", borderwidth=0)
        card3.pack(side="left", fill="both", expand=True, padx=8)

        card3_inner = tk.Frame(card3, bg="#1A3A4A")
        card3_inner.pack(padx=20, pady=15, fill="x")

        tk.Label(
            card3_inner,
            text="Coverage & Hints",
            font=("Helvetica", 15, "bold"), 
            fg=COLORS["muted"], bg="#1A3A4A"
        ).pack(anchor="w")

        # "Seen X% of all questions"
        if coverage_stats["total_questions"] > 0:
            tk.Label(
                card3_inner,
                text=f"Seen {coverage_stats['coverage_pct']:.1f}% of all questions",
                font=("Helvetica", 14), 
                fg="#60A5FA", bg="#1A3A4A"
            ).pack(anchor="w", pady=(10, 4))
        else:
            tk.Label(
                card3_inner,
                text="Seen 0.0% of all questions",
                font=("Helvetica", 14),
                fg="#60A5FA", bg="#1A3A4A"
            ).pack(anchor="w", pady=(10, 4))

        # "Used _ hints"
        tk.Label(
            card3_inner,
            text=f"Used {hint_stats['total']} hint(s)",
            font=("Helvetica", 14),  
            fg="#FACC15", bg="#1A3A4A"
        ).pack(anchor="w", pady=(4, 0))


        # Topic Performance
        tk.Label(outer, text="📚 Topic Performance", font=("Helvetica", 20, "bold"),
                 fg="white", bg=COLORS["bg"]).pack(pady=(30, 20))
        if not topic_stats or all(ts["total"] == 0 for ts in topic_stats):
            BodyLabel(outer,
                      "No topic performance data yet. Answer some questions to see your strengths and weaknesses.",
                      fg=COLORS["muted"]).pack(pady=(0, 10))
        else:
            for ts in topic_stats:
                topic = ts["lesson_name"]
                pct = ts["pct"]      
                correct = ts["correct"]
                total = ts["total"]
                seen = ts["seen"]

                topic_container = tk.Frame(outer, bg="#124E5E", relief="flat")
                topic_container.pack(fill="x", pady=10, padx=10)

                topic_inner = tk.Frame(topic_container, bg="#124E5E")
                topic_inner.pack(padx=20, pady=15, fill="x")

                header_row = tk.Frame(topic_inner, bg="#124E5E")
                header_row.pack(fill="x", pady=(0, 8))

                tk.Label(header_row, text=topic, font=("Helvetica", 16, "bold"),
                         fg="white", bg="#124E5E", anchor="w").pack(side="left")

                if seen == 0 or pct is None:
                    display_pct = "N/A"
                    badge_color = "#9E9E9E"   # neutral grey
                    bar_width = 0.0
                else:
                    display_pct = f"{pct:.1f}%"
                    if pct >= 80:
                        badge_color = "#6EE7B7"
                    elif pct >= 50:
                        badge_color = "#FACC15"
                    else:
                        badge_color = "#F87171"
                    bar_width = pct / 100 if pct <= 100 else 1.0

                tk.Label(header_row, text=display_pct, font=("Helvetica", 14, "bold"),
                         fg=badge_color, bg="#124E5E", anchor="e").pack(side="right")

                bar_bg = tk.Frame(topic_inner, bg="#0B3C49", height=12)
                bar_bg.pack(fill="x")
                bar_bg.pack_propagate(False)

                bar_fg = tk.Frame(bar_bg, bg=badge_color)
                bar_fg.place(relx=0, rely=0, relheight=1, relwidth=bar_width)

        # Map topic_id -> name (for weak_topic/strong_topic ids)
        topic_id_to_name = {}
        for ts in topic_stats:
            for tid in ts.get("topic_ids", []):
                topic_id_to_name[tid] = ts["lesson_name"]
        
        # System-estimated weak/strong topic objects for UI
        system_weak = None
        system_strong = None

        # Very simple gate: only trust the model once they've seen some questions
        enough_data_for_model = coverage_stats["attempted"] >= 3 and total_questions > 0

        if enough_data_for_model:
            # System-estimated weakest topic (ITS weighting / hints / recency)
            if weakest_topic_id is not None and weakest_topic_id in topic_id_to_name:
                weak_name = topic_id_to_name[weakest_topic_id]
                system_weak = next(
                    (ts for ts in topic_stats if ts["lesson_name"] == weak_name),
                    None
                )

            # System-estimated strongest topic
            if strongest_topic_id is not None and strongest_topic_id in topic_id_to_name:
                strong_name = topic_id_to_name[strongest_topic_id]
                system_strong = next(
                    (ts for ts in topic_stats if ts["lesson_name"] == strong_name),
                    None
                )

        # -------- Ability (IRT θ) Graph --------
        ability_frame = tk.Frame(outer, bg="#1A2A3A")
        ability_frame.pack(fill="x", padx=20, pady=20)

        ability_inner = tk.Frame(ability_frame, bg="#1A2A3A")
        ability_inner.pack(padx=25, pady=20, fill="x")

        tk.Label(
            ability_inner,
            text="📈 Learning Ability (IRT)",
            font=("Helvetica", 18, "bold"),
            fg="#34D399",
            bg="#1A2A3A",
            anchor="w"
        ).pack(fill="x", pady=(0, 10))

        ability_history = its_functions.get_ability_history(cur, user_id)

        if ability_history:
            thetas = [row[0] for row in ability_history]
            labels = list(range(1, len(thetas) + 1))
            current_theta = thetas[-1]
            level = its_functions.ability_label(current_theta)
        else:
            thetas = [0.0]
            labels = [1]
            current_theta = 0.0
            level = "New Learner"

        tk.Label(
            ability_inner,
            text=f"Current Ability Level: {level}",
            font=("Helvetica", 14, "bold"),
            fg="#FBBF24",
            bg="#1A2A3A",
            anchor="w"
        ).pack(fill="x", pady=(0, 12))

        fig = Figure(figsize=(6.5, 2.8), dpi=100)
        ax = fig.add_subplot(111)

        ax.plot(labels, thetas, marker="o", linewidth=2)
        ax.axhline(0, linestyle="--", alpha=0.4)

        ax.set_title("Ability Progress Over Time", fontsize=12)
        ax.set_xlabel("Practice Sessions")
        ax.set_ylabel("Ability (θ)")

        ax.grid(alpha=0.3)

        # Color bands for levels
        ax.axhspan(-3, -1, color="#EF4444", alpha=0.08)
        ax.axhspan(-1, 0.5, color="#F59E0B", alpha=0.08)
        ax.axhspan(0.5, 1.5, color="#10B981", alpha=0.08)
        ax.axhspan(1.5, 3, color="#3B82F6", alpha=0.08)

        fig_canvas = FigureCanvasTkAgg(fig, master=ability_inner)
        fig_canvas.draw()
        fig_canvas.get_tk_widget().pack(fill="both", expand=True)

        # Personalized Insights 
        tk.Label(outer, text="💡 Personalized Insights", font=("Helvetica", 20, "bold"),
                 fg="white", bg=COLORS["bg"]).pack(pady=(40, 20))

        # Insight 1: Focus Areas
        insight1 = tk.Frame(outer, bg="#1A3A4A", relief="flat", borderwidth=0)
        insight1.pack(fill="x", pady=10, padx=20)

        insight1_inner = tk.Frame(insight1, bg="#1A3A4A")
        insight1_inner.pack(padx=25, pady=20, fill="x")

        tk.Label(insight1_inner, text="⚠️ Focus Areas", font=("Helvetica", 16, "bold"),
                 fg="#FACC15", bg="#1A3A4A", anchor="w").pack(fill="x", pady=(0, 12))

        if not topic_stats or all(ts["total"] == 0 for ts in topic_stats):
            txt = ("You haven't answered enough questions yet. "
                   "Once you do, we'll highlight where you need the most review.")
            tk.Label(
                insight1_inner,
                text=txt,
                font=("Helvetica", 13),
                fg="white", bg="#1A3A4A",
                wraplength=750,
                justify="left",
                anchor="w"
            ).pack(fill="x", pady=4)

        elif system_weak is not None:
            weak_name = system_weak["lesson_name"]
            weak_pct = system_weak.get("pct")

            if weak_pct is not None:
                msg = (
                    f"• System-detected weakest topic: {weak_name} "
                    f"({weak_pct:.1f}% accuracy so far). "
                    "Spend some time practicing this area."
                )
            else:
                msg = (
                    f"• System-detected weakest topic: {weak_name}. "
                    "We don't have enough data yet for a stable accuracy estimate, "
                    "but it appears to need attention."
                )

            tk.Label(
                insight1_inner,
                text=msg,
                font=("Helvetica", 13),
                fg="white", bg="#1A3A4A",
                anchor="w", wraplength=750, justify="left"
            ).pack(fill="x", pady=4)


        else:
            # We have some data, but not enough for the ITS model
            tk.Label(
                insight1_inner,
                text=(
                    "We don't have a clear weakest topic yet. "
                    "Keep answering questions and we'll highlight your main focus area here."
                ),
                font=("Helvetica", 13),
                fg="white", bg="#1A3A4A",
                anchor="w", wraplength=750, justify="left"
            ).pack(fill="x", pady=4)

        # Insight 2: Strengths
        insight2 = tk.Frame(outer, bg="#1A4A3A", relief="flat", borderwidth=0)
        insight2.pack(fill="x", pady=10, padx=20)

        insight2_inner = tk.Frame(insight2, bg="#1A4A3A")
        insight2_inner.pack(padx=25, pady=20, fill="x")

        tk.Label(insight2_inner, text="✅ Your Strengths", font=("Helvetica", 16, "bold"),
                 fg="#6EE7B7", bg="#1A4A3A", anchor="w").pack(fill="x", pady=(0, 12))

        if not topic_stats or all(ts["total"] == 0 for ts in topic_stats):
            tk.Label(
                insight2_inner,
                text="As you answer more questions, your strongest topics will be highlighted here.",
                font=("Helvetica", 13),
                fg="white", bg="#1A4A3A",
                anchor="w", wraplength=750, justify="left"
            ).pack(fill="x", pady=4)

        elif system_strong is not None:
            strong_name = system_strong["lesson_name"]
            strong_pct = system_strong.get("pct")

            if strong_pct is not None:
                msg = (
                    f"• System-detected strongest topic: {strong_name} "
                    f"({strong_pct:.1f}% accuracy so far). Great work!"
                )
            else:
                msg = (
                    f"• System-detected strongest topic: {strong_name}. "
                    "You're doing relatively better here, but we don't yet have enough "
                    "data for a precise accuracy value."
                )

            tk.Label(
                insight2_inner,
                text=msg,
                font=("Helvetica", 13),
                fg="white", bg="#1A4A3A",
                anchor="w", wraplength=750, justify="left"
            ).pack(fill="x", pady=4)


        else:
            tk.Label(
                insight2_inner,
                text=(
                    "We don't have a clear strongest topic yet. "
                    "Keep practicing and your top strength will appear here."
                ),
                font=("Helvetica", 13),
                fg="white", bg="#1A4A3A",
                anchor="w", wraplength=750, justify="left"
            ).pack(fill="x", pady=4)

        # Insight 3: Recommended Next Steps
        insight3 = tk.Frame(outer, bg="#2A2A4A", relief="flat", borderwidth=0)
        insight3.pack(fill="x", pady=10, padx=20)

        insight3_inner = tk.Frame(insight3, bg="#2A2A4A")
        insight3_inner.pack(padx=25, pady=20, fill="x")

        tk.Label(insight3_inner, text="🎯 Recommended Next Steps", font=("Helvetica", 16, "bold"),
                 fg="#A78BFA", bg="#2A2A4A", anchor="w").pack(fill="x", pady=(0, 12))

        # Step 1 – focus on the system-detected weakest topic, if we have one
        if system_weak is not None:
            weak_name = system_weak["lesson_name"]
            weak_pct = system_weak.get("pct")
            if weak_pct is not None:
                txt1 = (
                    f"1. Focus on '{weak_name}'. "
                    f"The system detects this as your weakest topic so far "
                    f"({weak_pct:.1f}% accuracy). "
                    "Do a short practice session here."
                )
            else:
                txt1 = (
                    f"1. Focus on '{weak_name}'. "
                    "The system detects this as your weakest topic so far, "
                    "but we don't yet have enough data for a precise accuracy value. "
                    "Do a short practice session here."
                )
        else:
            txt1 = (
                "1. Start a mixed practice session to help the system identify your weakest topic."
            )

        tk.Label(
            insight3_inner,
            text=txt1,
            font=("Helvetica", 13),
            fg="white", bg="#2A2A4A",
            anchor="w", wraplength=750, justify="left"
        ).pack(fill="x", pady=4)

        # Step 2 – strongest topic (only recommend evaluation if accuracy is high enough)
        if system_strong is not None:
            name = system_strong["lesson_name"]
            pct = system_strong.get("pct")
            has_eval = system_strong.get("has_eval", False)

            if pct is None:
                txt2 = (
                    f"2. '{name}' is currently your strongest topic relative to others, "
                    "but we don't yet have enough data to calculate a clear accuracy. "
                    "Keep practicing here to solidify your understanding, then try an evaluation."
                )
            else:
                if pct >= 70.0:
                    if has_eval:
                        txt2 = (
                            f"2. You've already taken an evaluation on '{name}' and "
                            f"you're doing well here ({pct:.1f}% so far). "
                            "You can retake the evaluation as a challenge or move on to other topics."
                        )
                    else:
                        txt2 = (
                            f"2. Try an evaluation on '{name}'. "
                            f"The system detects this as your strongest topic so far "
                            f"({pct:.1f}% accuracy)."
                        )
                else:
                    txt2 = (
                        f"2. '{name}' is currently your strongest topic, but your accuracy is "
                        f"only {pct:.1f}%. Do a bit more practice here before attempting an evaluation."
                    )
        else:
            txt2 = (
                "2. Once a topic starts to feel comfortable, try an evaluation "
                "to confirm your mastery."
            )

        tk.Label(
            insight3_inner,
            text=txt2,
            font=("Helvetica", 13),
            fg="white", bg="#2A2A4A",
            anchor="w", wraplength=750, justify="left"
        ).pack(fill="x", pady=4)
        # Step 3 – Recent performance
        if recent_stats["recent_total"] > 0:
            txt3 = (f"3. Your last {recent_stats['recent_total']} attempts window is at "
                    f"{recent_stats['recent_pct']:.1f}% accuracy. Keep going!")
        else:
            txt3 = ("3. Answer more questions so we can highlight how your recent performance "
                    "compares to your overall accuracy.")
        tk.Label(
            insight3_inner,
            text=txt3,
            font=("Helvetica", 13),
            fg="white", bg="#2A2A4A",
            anchor="w", wraplength=750, justify="left"
        ).pack(fill="x", pady=4)

        # Recent Activity
        insight5 = tk.Frame(outer, bg="#1A2A3A", relief="flat", borderwidth=0)
        insight5.pack(fill="x", pady=10, padx=20)

        insight5_inner = tk.Frame(insight5, bg="#1A2A3A")
        insight5_inner.pack(padx=25, pady=20, fill="x")

        tk.Label(insight5_inner, text="⏱️ Recent Activity", font=("Helvetica", 16, "bold"),
                 fg="#60A5FA", bg="#1A2A3A", anchor="w").pack(fill="x", pady=(0, 12))

        if recent_stats["recent_total"] > 0:
            tk.Label(
                insight5_inner,
                text=(
                    f"• Based on your last {recent_stats['recent_total']} questions: "
                    f"about {recent_stats['recent_correct']} correct "
                    f"({recent_stats['recent_pct']:.1f}% accuracy)."
                ),
                font=("Helvetica", 13),
                fg="white", bg="#1A2A3A",
                anchor="w", wraplength=750, justify="left"
            ).pack(fill="x", pady=4)
        else:
            tk.Label(
                insight5_inner,
                text="• No recent attempts yet. Start a practice session to see activity here.",
                font=("Helvetica", 13),
                fg="white", bg="#1A2A3A",
                anchor="w", wraplength=750, justify="left"
            ).pack(fill="x", pady=4)

        # Action Buttons
        btns = tk.Frame(outer, bg=COLORS["bg"])
        btns.pack(pady=40)

        ttk.Button(btns, text="Practice Weak Topics", style="Accent.TButton",
                   command=lambda: app.switch_to("practice_setup")).pack(side="left", padx=10)

        ttk.Button(btns, text="Take Evaluation", style="Accent.TButton",
                   command=lambda: app.switch_to("evaluationSetup")).pack(side="left", padx=10)

        ttk.Button(btns, text="Back to Menu", style="Outline.TButton",
                   command=lambda: app.switch_to("menu")).pack(side="left", padx=10)

        # Mousewheel scroll
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        conn.close()
        
        
class EvaluationSetup(tk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=COLORS["bg"])
        content = tk.Frame(self, bg=COLORS["bg"])
        content.place(relx=0.5, rely=0.5, anchor="center")

        H1(content, "Evaluation Setup").pack(pady=8)
        BodyLabel(content, "Please select a topic").pack(pady=6)

        grid = tk.Frame(content, bg=COLORS["bg"])
        grid.pack(pady=12)
        
        def submit(self):
            app.switch_to("evaluation")
                   
        #couldn't get the check buttons working properly but heres the frame work of one 
        #ttk.Checkbutton(grid, text="Matter", width=22, style="Accent.TButton",variable=Topic_Matter,
        #                command = processSelections("Matter")).grid(row=0, column=0, padx=8, pady=8)

        #currently just basic buttons that switch on selection - minimal functionality 

        ttk.Button(grid, text="Matter", width=22, style="Accent.TButton",
                   command=lambda: app.switch_to("evaluation")).grid(row=0, column=0, padx=8, pady=8)
        ttk.Button(grid, text="Atoms and Molecules", width=22, style="Outline.TButton",
                   command=lambda: app.switch_to("evaluation")).grid(row=0, column=1, padx=8, pady=8)
        ttk.Button(grid, text="Elements", width=22, style="Outline.TButton",
                   command=lambda: app.switch_to("evaluation")).grid(row=1, column=0, padx=8, pady=8)
        
        ttk.Button(grid, text="Electrons", width=22, style="Outline.TButton",
                   command=lambda: app.switch_to("evaluation")).grid(row=1, column=1, padx=8, pady=8)
        
        ttk.Button(grid, text="Periodic Table", width=22, style="Outline.TButton",
                   command=lambda: app.switch_to("evaluation")).grid(row=2, column=0, padx=8, pady=8)
        
        ttk.Button(content, text="Submit Topics", style="Outline.TButton",
                   command=lambda: submit(self)).pack(pady=8)

        ttk.Button(content, text="Back to Menu", style="Outline.TButton",
                   command=lambda: app.switch_to("menu")).pack(pady=8)
        
class EvaluationSetup(tk.Frame):
    """Multi-select topic screen for evaluation mode."""
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        self.topic_vars = {}
        
        # Add subtle chemistry background
        create_chemistry_background(self)

        content = tk.Frame(self, bg=COLORS["bg"])
        content.place(relx=0.5, rely=0.5, anchor="center")

        H1(content, "Select Evaluation Topics").pack(pady=(0, 12))
        BodyLabel(content, "Choose one or more topics to include in the evaluation.",
                  fg=COLORS["muted"]).pack(pady=(0, 12))

        self.topic_vars = {}
        topic_frame = tk.Frame(content, bg=COLORS["bg"])
        topic_frame.pack(pady=10)

        # Use multiple selection with modern card UI
        for i, topic in enumerate(TOPICS.keys(), start=1):
            display_name = f"Topic {i}: {topic}"
            card = tk.Frame(topic_frame, bg="#124E5E",
                            highlightbackground=COLORS["accent"], highlightthickness=2)
            card.pack(fill="x", padx=20, pady=6)

            var = tk.BooleanVar(value=False)
            self.topic_vars[topic] = var
            chk = ttk.Checkbutton(
                card,
                text=display_name,
                variable=var,
                style="Modern.TCheckbutton",
            )
            chk.pack(fill="x", padx=20, pady=10)

        # --- Bottom Buttons ---
        btn_frame = tk.Frame(content, bg=COLORS["bg"])
        btn_frame.pack(pady=20)

        ttk.Button(btn_frame, text="← Back", style="Outline.TButton",
                   command=lambda: app.switch_to("menu")).grid(row=0, column=0, padx=10)
        ttk.Button(btn_frame, text="Start Evaluation!", style="Accent.TButton",
                   command=self.start_evaluation).grid(row=0, column=1, padx=10)

    def start_evaluation(self):
        selected_topics = [t for t, v in self.topic_vars.items() if v.get()]
        if not selected_topics:
            messagebox.showwarning("Notice", "Please select at least one topic to continue.")
            return

        lesson_ids = set()
        for topic in selected_topics:
            lesson_ids |= TOPICS.get(topic, set())

        if not lesson_ids:
            messagebox.showinfo("Coming Soon", f"No evaluation questions yet for {', '.join(selected_topics)}.")
            return

        self.app.evaluation_selection = {"lesson_ids": lesson_ids}
        self.app.switch_to("evaluation")
        
class EvaluationSetup(tk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=COLORS["bg"])
        content = tk.Frame(self, bg=COLORS["bg"])
        content.place(relx=0.5, rely=0.5, anchor="center")

        H1(content, "Evaluation Setup").pack(pady=8)
        BodyLabel(content, "Please select a topic").pack(pady=6)

        grid = tk.Frame(content, bg=COLORS["bg"])
        grid.pack(pady=12)
        
        def submit(self):
            app.switch_to("evaluation")
                   
        #couldn't get the check buttons working properly but heres the frame work of one 
        #ttk.Checkbutton(grid, text="Matter", width=22, style="Accent.TButton",variable=Topic_Matter,
        #                command = processSelections("Matter")).grid(row=0, column=0, padx=8, pady=8)

        #currently just basic buttons that switch on selection - minimal functionality 

        ttk.Button(grid, text="Matter", width=22, style="Accent.TButton",
                   command=lambda: app.switch_to("evaluation")).grid(row=0, column=0, padx=8, pady=8)
        ttk.Button(grid, text="Atoms and Molecules", width=22, style="Outline.TButton",
                   command=lambda: app.switch_to("evaluation")).grid(row=0, column=1, padx=8, pady=8)
        ttk.Button(grid, text="Elements", width=22, style="Outline.TButton",
                   command=lambda: app.switch_to("evaluation")).grid(row=1, column=0, padx=8, pady=8)
        
        ttk.Button(grid, text="Electrons", width=22, style="Outline.TButton",
                   command=lambda: app.switch_to("evaluation")).grid(row=1, column=1, padx=8, pady=8)
        
        ttk.Button(grid, text="Periodic Table", width=22, style="Outline.TButton",
                   command=lambda: app.switch_to("evaluation")).grid(row=2, column=0, padx=8, pady=8)
        
        ttk.Button(content, text="Submit Topics", style="Outline.TButton",
                   command=lambda: submit(self)).pack(pady=8)

        ttk.Button(content, text="Back to Menu", style="Outline.TButton",
                   command=lambda: app.switch_to("menu")).pack(pady=8)
        
class EvaluationSetup(tk.Frame):
    """Multi-select topic screen for evaluation mode."""
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        self.topic_vars = {}
        
        # Add subtle chemistry background
        create_chemistry_background(self)

        content = tk.Frame(self, bg=COLORS["bg"])
        content.place(relx=0.5, rely=0.5, anchor="center")

        H1(content, "Select Evaluation Topics").pack(pady=(0, 12))
        BodyLabel(content, "Choose one or more topics to include in the evaluation.",
                  fg=COLORS["muted"]).pack(pady=(0, 12))

        self.topic_vars = {}
        topic_frame = tk.Frame(content, bg=COLORS["bg"])
        topic_frame.pack(pady=10)

        # Use multiple selection with modern card UI
        for i, topic in enumerate(TOPICS.keys(), start=1):
            display_name = f"Topic {i}: {topic}"
            card = tk.Frame(topic_frame, bg="#124E5E",
                            highlightbackground=COLORS["accent"], highlightthickness=2)
            card.pack(fill="x", padx=20, pady=6)

            var = tk.BooleanVar(value=False)
            self.topic_vars[topic] = var
            chk = ttk.Checkbutton(
                card,
                text=display_name,
                variable=var,
                style="Modern.TCheckbutton",
            )
            chk.pack(fill="x", padx=20, pady=10)

        # --- Bottom Buttons ---
        btn_frame = tk.Frame(content, bg=COLORS["bg"])
        btn_frame.pack(pady=20)

        ttk.Button(btn_frame, text="← Back", style="Outline.TButton",
                   command=lambda: app.switch_to("menu")).grid(row=0, column=0, padx=10)
        ttk.Button(btn_frame, text="Start Evaluation!", style="Accent.TButton",
                   command=self.start_evaluation).grid(row=0, column=1, padx=10)

    def start_evaluation(self):
        selected_topics = [t for t, v in self.topic_vars.items() if v.get()]
        if not selected_topics:
            messagebox.showwarning("Notice", "Please select at least one topic to continue.")
            return

        lesson_ids = set()
        for topic in selected_topics:
            lesson_ids |= TOPICS.get(topic, set())

        if not lesson_ids:
            messagebox.showinfo("Coming Soon", f"No evaluation questions yet for {', '.join(selected_topics)}.")
            return

        self.app.evaluation_selection = {"lesson_ids": lesson_ids}
        self.app.switch_to("evaluation")


class Evaluation(tk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app

        # --- Load questions and initialize state ---
        self.all_questions, warn = load_questions()
        if warn:
            messagebox.showwarning("Notice", warn)

        self.questions = []
        self.q_idx = 0
        self.choice = tk.IntVar(value=-1)
        self.state = []

        content = tk.Frame(self, bg=COLORS["bg"])
        content.pack(fill="both", expand=True)
        
        # Add subtle chemistry background to the content frame
        bg_canvas = create_chemistry_background(content)

        # --- TOP NAVBAR ---
        top_nav = tk.Frame(content, bg=COLORS["bg"])
        top_nav.pack(fill="x", pady=(10, 0))
        top_nav.grid_columnconfigure(0, weight=1)
        top_nav.grid_columnconfigure(1, weight=1)

        self.btn_menu = ttk.Button(top_nav, text="← Back to Topics", style="Outline.TButton",
                                   command=lambda: self.app.switch_to("evaluationSetup"))
        self.btn_menu.grid(row=0, column=0, sticky="w", padx=20)

        self.btn_finish = ttk.Button(top_nav, text="Finish & View Results", style="Accent.TButton",
                                     command=self.finish)
        self.btn_finish.grid(row=0, column=1, sticky="e", padx=20)

        # --- MAIN BODY ---
        body = tk.Frame(content, bg=COLORS["bg"])
        body.pack(expand=True)
        
        # Ensure all content widgets are above the background canvas
        top_nav.lift()
        body.lift()

        H1(body, "Evaluation").pack(pady=6)

        # Progress
        self.progress_bar = ProgressBar(body)
        self.progress_bar.pack(pady=(4, 10))
        self.progress_label = BodyLabel(body, "", fg=COLORS["white"])
        self.progress_label.pack(pady=(0, 8))

        # Question text
        self.qtext = tk.Label(body, text="", fg=COLORS["white"], bg=COLORS["bg"],
                              wraplength=820, font=("Helvetica", 18, "bold"))
        self.qtext.pack(pady=8)
        self.qimage_label = tk.Label(body, bg=COLORS["bg"])
        self.qimage_label.pack(pady=8)


        self.opts = tk.Frame(body, bg=COLORS["bg"])
        self.opts.pack(pady=6)

        # --- FOOTER NAVIGATION  ---
        footer = tk.Frame(content, bg=COLORS["bg"])
        footer.pack(fill="x", pady=(0, 20))
        footer.grid_columnconfigure(0, weight=1)
        footer.grid_columnconfigure(1, weight=1)

        self.btn_prev = ttk.Button(footer, text="← Previous", style="Outline.TButton",
                                   command=self.prev_q)
        self.btn_prev.grid(row=0, column=0, sticky="w", padx=20)

        self.btn_next = ttk.Button(footer, text="Next →", style="Outline.TButton",
                                   command=self.next_q)
        self.btn_next.grid(row=0, column=1, sticky="e", padx=20)
        
        # Ensure footer is above background
        footer.lift()

    def apply_selection_and_prepare(self):
        """Filter by selected topic and prepare for evaluation."""
        sel = getattr(self.app, "evaluation_selection", None)
        if not sel or not sel.get("lesson_ids"):
            messagebox.showinfo("Select Topic", "Please pick a topic first.")
            self.app.switch_to("evaluationSetup")
            return

        lesson_ids = {int(x) for x in sel["lesson_ids"]}
        filtered = [q for q in self.all_questions if int(q.get("topic_id", -9999)) in lesson_ids]

        if not filtered:
            messagebox.showinfo("No Questions", "No questions found for this topic.")
            self.app.switch_to("evaluationSetup")
            return

        random.shuffle(filtered)

        self.questions = filtered
        self.state = [{} for _ in self.questions]
        self.q_idx = 0
        self.choice.set(-1)
        self.render()

    def reset(self):
        self.q_idx = 0
        self.choice.set(-1)
        self.state = [{} for _ in self.questions]
        self.render()

    def render(self):
        if not self.questions:
            self.qtext.config(text="No questions available.")
            for w in self.opts.winfo_children():
                w.destroy()
            for b in (self.btn_next, self.btn_prev):
                b.state(["disabled"])
            return

        # Progress
        progress = (self.q_idx + 1) / len(self.questions)
        self.progress_bar.update_bar(progress)
        self.progress_label.config(text=f"Question {self.q_idx + 1} of {len(self.questions)}")

        q = self.questions[self.q_idx]
        self.qtext.config(text=q["text"])
        # --- Render image if available ---
        img_path = q.get("image", "").strip()

        if img_path:
            full_path = resource_path(os.path.join("cutouts", img_path))
            print("Looking for:", os.path.abspath(full_path))


            if os.path.exists(full_path):
                try:
                    img = Image.open(full_path).resize((90, 90), Image.LANCZOS)
                    self.qimgtk = ImageTk.PhotoImage(img)
                    self.qimage_label.config(image=self.qimgtk)
                    self.qimage_label.image = self.qimgtk  # keep a reference alive
                    self.qimage_label.config(text="")      # clear any text
                    print("Loaded:", os.path.exists(full_path))
                    print("Showing:", full_path)

                except Exception:
                    self.qimage_label.config(image="", text="[Error loading image]", fg="white")
            else:
                self.qimage_label.config(image="", text="[Image not found]", fg="white")
        else:
            self.qimage_label.config(image="", text="")


        self.btn_prev.state(["!disabled"] if self.q_idx > 0 else ["disabled"])
        self.btn_next.state(["!disabled"])

        # Clear old options
        for w in self.opts.winfo_children():
            w.destroy()

        saved = self.state[self.q_idx]
        selected_before = saved.get("selected", -1)
        self.choice.set(selected_before)

        for i, c in enumerate(q["choices"]):
            rb = tk.Radiobutton(
                self.opts,
                text=c,
                variable=self.choice,
                value=i,
                fg=COLORS["white"],
                bg=COLORS["bg"],
                activebackground=COLORS["bg"],
                selectcolor=COLORS["bg"],
                anchor="w",
                justify="left",
                font=("Helvetica", 16),
                command=self._auto_save_selection
            )
            rb.pack(anchor="w")

    def _auto_save_selection(self):
        """Auto-save selection immediately when user clicks a choice."""
        sel = self.choice.get()
        if sel == -1:
            return
        self.state[self.q_idx]["selected"] = sel

    def next_q(self):
        if self.q_idx < len(self.questions) - 1:
            self.q_idx += 1
            self.render()

    def prev_q(self):
        if self.q_idx > 0:
            self.q_idx -= 1
            self.render()

    def finish(self):
        # Mark correctness for all answered questions
        for i, s in enumerate(self.state):
            if "selected" in s:
                q = self.questions[i]
                s["is_correct"] = (s["selected"] == int(q["answer_index"]))
        
        # Save all progress to database
        self._save_all_progress_to_db()
        
        results_screen = self.app.screens["results"]
        self.app.last_mode = "evaluation"
        self.app.last_evaluation_selection = getattr(self.app, "evaluation_selection", None)
        results_screen.set_results(self.questions, self.state)
        self.app.switch_to("results")

    def _save_all_progress_to_db(self):
        """Save all answered questions' progress to the database."""
        if not self.app.current_user:
            print("[TRACKING] No user logged in - skipping progress save")
            return
        
        # Ensure progress table exists
        success, error = create_progress_table()
        if not success:
            print(f"[TRACKING ERROR] Could not create progress table: {error}")
            return
        
        user_id = self.app.current_user.get("uid")
        mode = "evaluation"
        
        print(f"\n{'='*60}")
        print(f"[TRACKING] Saving Evaluation Progress:")
        print(f"  User ID: {user_id} ({self.app.current_user.get('username')})")
        print(f"  Mode: {mode}")
        print(f"  Total Questions: {len(self.questions)}")
        print(f"{'='*60}")
        
        saved_count = 0
        skipped_count = 0
        
        for i, saved in enumerate(self.state):
            if "selected" not in saved:
                skipped_count += 1
                continue  # Skip unanswered questions
            
            q = self.questions[i]
            question_id = q.get("id")
            selected_answer = q["choices"][saved["selected"]] if saved.get("selected") is not None else None
            is_correct = saved.get("is_correct", False)
            used_hint = False  # Evaluation mode typically doesn't have hints
            
            print(f"\n  Question {i+1}/{len(self.questions)}:")
            print(f"    Question ID: {question_id}")
            print(f"    Text: {q.get('text', '')[:40]}...")
            print(f"    Selected: {selected_answer}")
            print(f"    Correct: {is_correct}")
            
            success, progress_id, error = insert_progress(
                user_id, question_id, selected_answer, is_correct, used_hint, mode
            )
            if success:
                print(f"    ✓ Saved (Progress ID: {progress_id})")
                saved_count += 1
            else:
                print(f"    ✗ Failed: {error}")
        
        print(f"\n{'='*60}")
        print(f"[TRACKING] Evaluation Complete:")
        print(f"  Saved: {saved_count} questions")
        print(f"  Skipped (unanswered): {skipped_count} questions")
        print(f"{'='*60}\n")



class EvaluationStub(tk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=COLORS["bg"])
        
        # Add subtle chemistry background
        create_chemistry_background(self)
        
        content = tk.Frame(self, bg=COLORS["bg"])
        content.place(relx=0.5, rely=0.5, anchor="center")
        H1(content, "Evaluation").pack(pady=8)
        BodyLabel(content, "Coming soon (UI stub only).").pack(pady=6)
        ttk.Button(content, text="Back to Menu", style="Outline.TButton",
                   command=lambda: app.switch_to("menu")).pack(pady=8)              
                   
TOPICS = {
    "Matter": {1},
    "Atoms & Molecules": {2},
    "Elements": {3},
    "Electrons": {4},
    "Periodic Table": {5},
}

class PracticeSetup(tk.Frame):
    """Multi-select topic screen for practice mode."""
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        self.topic_vars = {}
        
        # Add subtle chemistry background
        create_chemistry_background(self)

        content = tk.Frame(self, bg=COLORS["bg"])
        content.place(relx=0.5, rely=0.5, anchor="center")

        H1(content, "Select Topic(s) to Practice").pack(pady=(0, 12))
        BodyLabel(content, "Choose one or more topics to start practice.", fg=COLORS["muted"]).pack(pady=(0, 12))

        topic_frame = tk.Frame(content, bg=COLORS["bg"])
        topic_frame.pack(pady=10)

        # Use modern card design but allow multiple selection
        self.topic_vars = {}
        for i, topic in enumerate(TOPICS.keys(), start=1):
            display_name = f"Topic {i}: {topic}"
            card = tk.Frame(topic_frame, bg="#124E5E",
                            highlightbackground=COLORS["accent"], highlightthickness=2)
            card.pack(fill="x", padx=20, pady=6)

            var = tk.BooleanVar(value=False)
            self.topic_vars[topic] = var
            chk = ttk.Checkbutton(
                card,
                text=display_name,
                variable=var,
                style="Modern.TCheckbutton",
            )
            chk.pack(fill="x", padx=20, pady=10)

        # --- Bottom Buttons ---
        btn_frame = tk.Frame(content, bg=COLORS["bg"])
        btn_frame.pack(pady=20)

        ttk.Button(btn_frame, text="← Back", style="Outline.TButton",
                   command=lambda: app.switch_to("menu")).grid(row=0, column=0, padx=10)
        ttk.Button(btn_frame, text="Start Practice!", style="Accent.TButton",
                   command=self.start_practice).grid(row=0, column=1, padx=10)

    def start_practice(self):
        selected_topics = [t for t, v in self.topic_vars.items() if v.get()]
        if not selected_topics:
            messagebox.showwarning("Notice", "Please select at least one topic to continue.")
            return

        lesson_ids = set()
        for topic in selected_topics:
            lesson_ids |= TOPICS.get(topic, set())

        if not lesson_ids:
            self.app.screens["practice_topic_stub"].set_topic(", ".join(selected_topics))
            self.app.switch_to("practice_topic_stub")
            return

        self.app.practice_selection = {"lesson_ids": lesson_ids}
        self.app.switch_to("practice")



class PracticeTopicStub(tk.Frame):
    """Simple placeholder when a topic has no questions yet."""
    def __init__(self, parent, app: App):
        super().__init__(parent, bg=COLORS["bg"])
        self.app = app
        self.topic_name = ""
        
        # Add subtle chemistry background
        create_chemistry_background(self)

        content = tk.Frame(self, bg=COLORS["bg"])
        content.place(relx=0.5, rely=0.5, anchor="center")

        H1(content, "Practice (Coming Soon)").pack(pady=8)
        self.msg = BodyLabel(content, "", fg=COLORS["muted"])
        self.msg.pack(pady=(4, 12))

        ttk.Button(content, text="Back to Topics", style="Outline.TButton",
                   command=lambda: self.app.switch_to("practice_setup")).pack(pady=6)
        ttk.Button(content, text="Back to Menu", style="Outline.TButton",
                   command=lambda: self.app.switch_to("menu")).pack(pady=6)

    def set_topic(self, topic_name: str):
        self.topic_name = topic_name
        self.msg.config(text=f"(UI stub) '{topic_name}' has no questions yet.\nPlease pick another topic.")


# ------------------------ RUN ------------------------
if __name__ == "__main__":
    App().mainloop()
