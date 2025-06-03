import tkinter as tk
from tkinter import Canvas, messagebox, Toplevel, Listbox, Scrollbar, simpledialog
import json
import os
from datetime import datetime
import random

SAVE_FILE = "fitness_tracker_save.json"

# Boss shapes and colors for each boss battle (every 10th level)
BOSS_SHAPES = [
    ("oval", "red"),
    ("rectangle", "purple"),
    ("triangle", "orange")
]

# Boss-specific taunts, victory, and defeat lines
BOSS_DIALOG = [
    {
        "taunt": "You dare challenge the Crimson Crusher? I'll flatten you!",
        "victory": "No! How could you defeat the mighty Crusher?",
        "defeat": "Pathetic! The Crusher reigns supreme!"
    },
    {
        "taunt": "Welcome to my domain, the Violet Vanquisher! Prepare for defeat.",
        "victory": "Impossible! The Vanquisher has been vanquished...",
        "defeat": "You never stood a chance against the Vanquisher!"
    },
    {
        "taunt": "The Tangerine Trickster is here! Let's see your best!",
        "victory": "What? Outsmarted by you? This can't be!",
        "defeat": "Ha! Outsmarted again. Try harder next time!"
    }
]

class FitnessTrackerMOBACharacter:
    def __init__(self, master, num_sessions=30):
        # Initialize main variables
        self.master = master
        self.num_sessions = num_sessions
        self.sessions = []
        self.current_position = 0
        self.character_name = None
        self.awaiting_boss = False  # True if next session is a boss battle
        self.current_boss_idx = 0  # Track which boss we're on

        self.master.title("MOBA Style Fitness Tracker with Character")

        # --- GUI Elements (no name entry here!) ---
        self.exercise_label = tk.Label(master, text="Enter Exercise Names (comma separated):")
        self.exercise_label.pack()
        self.exercise_entry = tk.Entry(master)
        self.exercise_entry.pack()

        self.weight_label = tk.Label(master, text="Enter Weights (comma separated, in kg):")
        self.weight_label.pack()
        self.weight_entry = tk.Entry(master)
        self.weight_entry.pack()

        self.reps_label = tk.Label(master, text="Enter Reps (comma separated):")
        self.reps_label.pack()
        self.reps_entry = tk.Entry(master)
        self.reps_entry.pack()

        self.notes_label = tk.Label(master, text="Enter Notes for this session:")
        self.notes_label.pack()
        self.notes_entry = tk.Entry(master)
        self.notes_entry.pack()

        self.add_button = tk.Button(master, text="Add Session", command=self.add_session)
        self.add_button.pack()

        self.view_button = tk.Button(master, text="View Previous Sessions", command=self.view_sessions)
        self.view_button.pack()

        self.progress_canvas = Canvas(master, width=600, height=120)
        self.progress_canvas.pack(pady=10)

        self.status_label = tk.Label(master, text="")
        self.status_label.pack()

        # Load saved data if available
        self.load_data()

        # Prompt for name if not saved
        if not self.character_name:
            self.character_name = simpledialog.askstring("Character Name", "Enter your character's name:")
            if not self.character_name:
                messagebox.showerror("Error", "Character name is required!")
                master.destroy()
                return
            self.save_data()

        self.draw_lane()

    def draw_lane(self):
        """Draw the lane bars first, then bosses, then character on top."""
        self.progress_canvas.delete("all")
        segment_width = self.progress_canvas.winfo_width() // self.num_sessions
        if segment_width == 0:
            segment_width = 20
        y0 = self.progress_canvas.winfo_height() // 3
        y1 = 2 * self.progress_canvas.winfo_height() // 3

        # 1. Draw all lane bars (including boss bars, all lightgray)
        for i in range(self.num_sessions):
            x0 = i * segment_width
            x1 = x0 + segment_width
            self.progress_canvas.create_rectangle(x0, y0, x1, y1, fill="lightgray", outline="black")

        # 2. Draw all boss shapes on top of the bars
        for i in range(self.num_sessions):
            if (i + 1) % 10 == 0:
                boss_idx = ((i + 1) // 10 - 1) % len(BOSS_SHAPES)
                shape, color = BOSS_SHAPES[boss_idx]
                x0 = i * segment_width
                x1 = x0 + segment_width
                cx = (x0 + x1) // 2
                cy = (y0 + y1) // 2
                if shape == "oval":
                    self.progress_canvas.create_oval(cx-10, cy-20, cx+10, cy+20, fill=color, outline="black")
                elif shape == "rectangle":
                    self.progress_canvas.create_rectangle(cx-12, cy-18, cx+12, cy+18, fill=color, outline="black")
                elif shape == "triangle":
                    self.progress_canvas.create_polygon(cx, cy-20, cx-15, cy+15, cx+15, cy+15, fill=color, outline="black")

        # 3. Draw character on top of everything
        if self.current_position < self.num_sessions:
            char_x = self.current_position * segment_width + segment_width // 2
        else:
            char_x = (self.num_sessions - 1) * segment_width + segment_width // 2
        char_y = self.progress_canvas.winfo_height() // 2
        radius = 15
        self.progress_canvas.create_oval(char_x - radius, char_y - radius, char_x + radius, char_y + radius, fill='blue')
        if self.character_name:
            self.progress_canvas.create_text(char_x, char_y - radius - 10, text=self.character_name, fill='black', font=('Arial', 10, 'bold'))

    def add_session(self):
        """Handle adding a new session, including boss logic and progress checks."""
        # Get exercises, weights, reps, and notes from input
        exercises = self.exercise_entry.get().strip()
        weights = self.weight_entry.get().strip()
        reps = self.reps_entry.get().strip()
        notes = self.notes_entry.get().strip()

        if not exercises or not weights or not reps:
            messagebox.showerror("Error", "Please enter exercises, weights, and reps.")
            return

        exercise_list = [e.strip() for e in exercises.split(",")]
        weight_list = [w.strip() for w in weights.split(",")]
        reps_list = [r.strip() for r in reps.split(",")]

        if len(exercise_list) != len(weight_list) or len(exercise_list) != len(reps_list):
            messagebox.showerror("Error", "Number of exercises, weights, and reps must match.")
            return

        try:
            weight_list = [float(w) for w in weight_list]
            reps_list = [int(r) for r in reps_list]
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for weights and reps.")
            return

        # Check progress for each exercise (improvement if weight or reps increased)
        progressed = False
        session_exercises = []
        for exercise, weight, reps in zip(exercise_list, weight_list, reps_list):
            last_weight = None
            last_reps = None
            for session in reversed(self.sessions):
                for ex in session.get('exercises', []):
                    if ex.get('name') == exercise:
                        last_weight = ex.get('weight')
                        last_reps = ex.get('reps')
                        break
                if last_weight is not None:
                    break

            # Progression logic: improvement if weight OR reps increased
            if last_weight is None or last_reps is None or weight > last_weight or reps > last_reps:
                progress = 'improvement'
                progressed = True
            elif weight < last_weight or reps < last_reps:
                progress = 'setback'
            else:
                progress = 'maintained'

            session_exercises.append({
                'name': exercise,
                'weight': weight,
                'reps': reps,
                'progress': progress
            })

        # --- Boss battle logic ---
        next_level = self.current_position + 1
        is_boss_level = (next_level % 10 == 0)
        boss_idx = ((next_level // 10 - 1) % len(BOSS_DIALOG)) if is_boss_level else self.current_boss_idx

        # If a boss battle is due, enforce it
        if self.awaiting_boss:
            if not progressed:
                defeat = BOSS_DIALOG[self.current_boss_idx]["defeat"]
                messagebox.showinfo("Boss Defeat", f"Boss defeated you! {defeat} You are sent back 2 levels. Try again!")
                self.status_label.config(
                    text=f"Boss defeated you! {defeat} You are sent back 2 levels. Try again!",
                    fg='red'
                )
                self.current_position = max(0, self.current_position - 2)
                self.awaiting_boss = False
                self.draw_lane()
                self.save_data()
                return
            else:
                victory = BOSS_DIALOG[self.current_boss_idx]["victory"]
                messagebox.showinfo("Boss Victory", f"You beat the boss! {victory}")
                self.status_label.config(
                    text=f"You beat the boss! {victory}",
                    fg='green'
                )
                self.awaiting_boss = False
                self.current_boss_idx = (self.current_boss_idx + 1) % len(BOSS_DIALOG)

        # If not awaiting boss, check if next level is a boss and set up the boss
        elif is_boss_level and self.current_position < self.num_sessions:
            taunt = BOSS_DIALOG[boss_idx]["taunt"]
            self.awaiting_boss = True
            self.current_boss_idx = boss_idx
            messagebox.showinfo("Boss Battle", f"Boss battle at level {next_level}!\n\n{taunt}")
            self.status_label.config(
                text=f"Boss battle at level {next_level}! {taunt}",
                fg='purple'
            )
            self.draw_lane()
            self.save_data()
            return

        # If not a boss level and no progress, do not advance
        elif not progressed:
            self.status_label.config(text="No progress in any exercise. Retry session.", fg='red')
            return

        # Prevent exceeding max sessions
        if self.current_position >= self.num_sessions:
            messagebox.showinfo("Info", "Maximum sessions reached.")
            return

        # Store the session data
        session_data = {
            'date': datetime.now().strftime("%Y-%m-%d"),
            'exercises': session_exercises,
            'notes': notes
        }

        self.sessions.append(session_data)
        self.current_position += 1

        # If next level is a boss, show taunt (for next submission)
        next_level = self.current_position + 1
        if (next_level % 10 == 0) and self.current_position < self.num_sessions:
            boss_idx = ((next_level // 10 - 1) % len(BOSS_DIALOG))
            taunt = BOSS_DIALOG[boss_idx]["taunt"]
            self.awaiting_boss = True
            self.current_boss_idx = boss_idx
            messagebox.showinfo("Boss Battle", f"Boss battle at level {next_level}!\n\n{taunt}")
            self.status_label.config(
                text=f"Boss battle at level {next_level}! {taunt}",
                fg='purple'
            )
        else:
            self.status_label.config(
                text=f"Leveled Up! {self.character_name} advanced on the lane!",
                fg='green'
            )

        self.draw_lane()
        self.save_data()

    def view_sessions(self):
        """Display a scrollable window with all previous sessions and their details."""
        if not self.sessions:
            messagebox.showinfo("Info", "No sessions recorded yet.")
            return

        window = Toplevel(self.master)
        window.title("Previous Sessions")
        window.geometry("800x400")

        listbox = Listbox(window, width=120, height=20)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = Scrollbar(window)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=listbox.yview)

        for i, session in enumerate(self.sessions, 1):
            date = session.get('date', 'Unknown')
            notes = session.get('notes', '')
            session_str = f"Session {i} - Date: {date} - Notes: {notes}"
            listbox.insert(tk.END, session_str)
            for ex in session.get('exercises', []):
                ex_str = (
                    f"    Exercise: {ex.get('name', 'Unknown')}, "
                    f"Weight: {ex.get('weight', 'Unknown')}kg, "
                    f"Reps: {ex.get('reps', 'Unknown')}, "
                    f"Progress: {ex.get('progress', 'Unknown')}"
                )
                listbox.insert(tk.END, ex_str)

    def save_data(self):
        """Save all tracker data to a JSON file."""
        data = {
            'character_name': self.character_name,
            'sessions': self.sessions,
            'current_position': self.current_position,
            'awaiting_boss': self.awaiting_boss,
            'current_boss_idx': self.current_boss_idx
        }
        try:
            with open(SAVE_FILE, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save data: {e}")

    def load_data(self):
        """Load tracker data from the JSON file, if it exists."""
        if not os.path.exists(SAVE_FILE):
            return
        try:
            with open(SAVE_FILE, 'r') as f:
                data = json.load(f)
            self.character_name = data.get('character_name', None)
            self.sessions = data.get('sessions', [])
            self.current_position = data.get('current_position', 0)
            self.awaiting_boss = data.get('awaiting_boss', False)
            self.current_boss_idx = data.get('current_boss_idx', 0)
        except Exception as e:
            messagebox.showwarning("Load Warning", f"Failed to load saved data: {e}")
            self.character_name = None
            self.sessions = []
            self.current_position = 0
            self.awaiting_boss = False
            self.current_boss_idx = 0

def main():
    # Start the Tkinter GUI application
    root = tk.Tk()
    app = FitnessTrackerMOBACharacter(root)
    root.mainloop()

if __name__ == '__main__':
    main()
