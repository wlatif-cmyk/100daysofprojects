"""
Guess the Number Game with Tkinter GUI
A fun number guessing game with a graphical interface, difficulty levels, and score tracking.
"""

import tkinter as tk
from tkinter import messagebox
import random

class GuessTheNumberGame:
    def __init__(self, root):
        self.root = root
        self.root.title("🎮 Guess the Number Game")
        self.root.geometry("500x600")
        self.root.resizable(False, False)
        self.root.configure(bg="#2C3E50")
        
        # Game variables
        self.secret_number = 0
        self.attempts = 0
        self.max_attempts = 10
        self.min_range = 1
        self.max_range = 100
        self.best_score = float('inf')
        self.difficulty = "Medium"
        
        # Create UI
        self.create_widgets()
        self.start_new_game()
    
    def create_widgets(self):
        """Create all UI elements"""
        
        # Title
        title_label = tk.Label(
            self.root,
            text="🎯 GUESS THE NUMBER 🎯",
            font=("Arial", 24, "bold"),
            bg="#2C3E50",
            fg="#ECF0F1"
        )
        title_label.pack(pady=20)
        
        # Difficulty Frame
        difficulty_frame = tk.Frame(self.root, bg="#2C3E50")
        difficulty_frame.pack(pady=10)
        
        tk.Label(
            difficulty_frame,
            text="Difficulty:",
            font=("Arial", 12),
            bg="#2C3E50",
            fg="#ECF0F1"
        ).pack(side=tk.LEFT, padx=5)
        
        self.difficulty_var = tk.StringVar(value="Medium")
        difficulties = ["Easy", "Medium", "Hard", "Expert"]
        
        for diff in difficulties:
            tk.Radiobutton(
                difficulty_frame,
                text=diff,
                variable=self.difficulty_var,
                value=diff,
                font=("Arial", 10),
                bg="#2C3E50",
                fg="#ECF0F1",
                selectcolor="#34495E",
                command=self.change_difficulty
            ).pack(side=tk.LEFT, padx=5)
        
        # Info Frame
        info_frame = tk.Frame(self.root, bg="#34495E", relief=tk.RAISED, bd=3)
        info_frame.pack(pady=15, padx=40, fill=tk.X)
        
        self.range_label = tk.Label(
            info_frame,
            text=f"Range: {self.min_range} - {self.max_range}",
            font=("Arial", 14, "bold"),
            bg="#34495E",
            fg="#3498DB"
        )
        self.range_label.pack(pady=5)
        
        self.attempts_label = tk.Label(
            info_frame,
            text=f"Attempts Left: {self.max_attempts}",
            font=("Arial", 14),
            bg="#34495E",
            fg="#E74C3C"
        )
        self.attempts_label.pack(pady=5)
        
        self.best_score_label = tk.Label(
            info_frame,
            text="Best Score: --",
            font=("Arial", 12),
            bg="#34495E",
            fg="#2ECC71"
        )
        self.best_score_label.pack(pady=5)
        
        # Feedback Label
        self.feedback_label = tk.Label(
            self.root,
            text="Make your first guess!",
            font=("Arial", 16, "italic"),
            bg="#2C3E50",
            fg="#F39C12",
            wraplength=400
        )
        self.feedback_label.pack(pady=20)
        
        # Input Frame
        input_frame = tk.Frame(self.root, bg="#2C3E50")
        input_frame.pack(pady=10)
        
        tk.Label(
            input_frame,
            text="Your Guess:",
            font=("Arial", 14),
            bg="#2C3E50",
            fg="#ECF0F1"
        ).pack(side=tk.LEFT, padx=10)
        
        self.guess_entry = tk.Entry(
            input_frame,
            font=("Arial", 16),
            width=10,
            justify=tk.CENTER,
            relief=tk.SOLID,
            bd=2
        )
        self.guess_entry.pack(side=tk.LEFT, padx=10)
        self.guess_entry.bind('<Return>', lambda e: self.check_guess())
        
        # Buttons Frame
        buttons_frame = tk.Frame(self.root, bg="#2C3E50")
        buttons_frame.pack(pady=20)
        
        self.submit_button = tk.Button(
            buttons_frame,
            text="Submit Guess",
            font=("Arial", 14, "bold"),
            bg="#3498DB",
            fg="white",
            activebackground="#2980B9",
            activeforeground="white",
            width=15,
            height=2,
            cursor="hand2",
            command=self.check_guess
        )
        self.submit_button.pack(side=tk.LEFT, padx=10)
        
        self.new_game_button = tk.Button(
            buttons_frame,
            text="New Game",
            font=("Arial", 14, "bold"),
            bg="#2ECC71",
            fg="white",
            activebackground="#27AE60",
            activeforeground="white",
            width=15,
            height=2,
            cursor="hand2",
            command=self.start_new_game
        )
        self.new_game_button.pack(side=tk.LEFT, padx=10)
        
        # History Frame
        history_frame = tk.Frame(self.root, bg="#34495E", relief=tk.SUNKEN, bd=3)
        history_frame.pack(pady=15, padx=40, fill=tk.BOTH, expand=True)
        
        tk.Label(
            history_frame,
            text="📝 Guess History",
            font=("Arial", 12, "bold"),
            bg="#34495E",
            fg="#ECF0F1"
        ).pack(pady=5)
        
        self.history_listbox = tk.Listbox(
            history_frame,
            font=("Arial", 11),
            bg="#2C3E50",
            fg="#ECF0F1",
            selectbackground="#3498DB",
            height=6
        )
        self.history_listbox.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        
        # Focus on entry
        self.guess_entry.focus()
    
    def change_difficulty(self):
        """Change game difficulty"""
        self.difficulty = self.difficulty_var.get()
        
        difficulty_settings = {
            "Easy": (1, 50, 15),
            "Medium": (1, 100, 10),
            "Hard": (1, 200, 8),
            "Expert": (1, 500, 7)
        }
        
        self.min_range, self.max_range, self.max_attempts = difficulty_settings[self.difficulty]
        self.start_new_game()
    
    def start_new_game(self):
        """Start a new game"""
        self.secret_number = random.randint(self.min_range, self.max_range)
        self.attempts = 0
        
        # Update UI
        self.range_label.config(text=f"Range: {self.min_range} - {self.max_range}")
        self.attempts_label.config(text=f"Attempts Left: {self.max_attempts}")
        self.feedback_label.config(text="🎮 New game started! Make your guess!", fg="#F39C12")
        self.guess_entry.delete(0, tk.END)
        self.guess_entry.config(state=tk.NORMAL)
        self.submit_button.config(state=tk.NORMAL)
        self.history_listbox.delete(0, tk.END)
        self.guess_entry.focus()
    
    def check_guess(self):
        """Check the player's guess"""
        try:
            guess = int(self.guess_entry.get())
            
            # Validate range
            if guess < self.min_range or guess > self.max_range:
                self.feedback_label.config(
                    text=f"⚠️ Please enter a number between {self.min_range} and {self.max_range}!",
                    fg="#E74C3C"
                )
                return
            
            self.attempts += 1
            attempts_left = self.max_attempts - self.attempts
            self.attempts_label.config(text=f"Attempts Left: {attempts_left}")
            
            # Add to history
            self.history_listbox.insert(0, f"Attempt {self.attempts}: {guess}")
            
            # Check if correct
            if guess == self.secret_number:
                self.win_game()
            elif attempts_left == 0:
                self.lose_game()
            elif guess < self.secret_number:
                diff = self.secret_number - guess
                if diff <= 5:
                    hint = "🔥 Very close! Go HIGHER!"
                elif diff <= 15:
                    hint = "📈 Close! Too low, go higher!"
                else:
                    hint = "⬆️ Too low! Go much higher!"
                self.feedback_label.config(text=hint, fg="#3498DB")
            else:
                diff = guess - self.secret_number
                if diff <= 5:
                    hint = "🔥 Very close! Go LOWER!"
                elif diff <= 15:
                    hint = "📉 Close! Too high, go lower!"
                else:
                    hint = "⬇️ Too high! Go much lower!"
                self.feedback_label.config(text=hint, fg="#E67E22")
            
            self.guess_entry.delete(0, tk.END)
            
        except ValueError:
            self.feedback_label.config(
                text="❌ Please enter a valid number!",
                fg="#E74C3C"
            )
    
    def win_game(self):
        """Handle winning the game"""
        self.feedback_label.config(
            text=f"🎉 CONGRATULATIONS! You guessed it in {self.attempts} attempts!",
            fg="#2ECC71"
        )
        
        # Update best score
        if self.attempts < self.best_score:
            self.best_score = self.attempts
            self.best_score_label.config(text=f"Best Score: {self.best_score} attempts")
            messagebox.showinfo(
                "New Record! 🏆",
                f"Congratulations! You set a new best score of {self.best_score} attempts!"
            )
        else:
            messagebox.showinfo(
                "You Won! 🎉",
                f"Great job! You guessed the number in {self.attempts} attempts!\n\n"
                f"Your best score is {self.best_score} attempts."
            )
        
        self.guess_entry.config(state=tk.DISABLED)
        self.submit_button.config(state=tk.DISABLED)
    
    def lose_game(self):
        """Handle losing the game"""
        self.feedback_label.config(
            text=f"💔 Game Over! The number was {self.secret_number}",
            fg="#E74C3C"
        )
        messagebox.showinfo(
            "Game Over",
            f"Sorry! You've used all {self.max_attempts} attempts.\n\n"
            f"The secret number was: {self.secret_number}\n\n"
            f"Try again!"
        )
        self.guess_entry.config(state=tk.DISABLED)
        self.submit_button.config(state=tk.DISABLED)

def main():
    """Main function to run the game"""
    root = tk.Tk()
    game = GuessTheNumberGame(root)
    root.mainloop()

if __name__ == "__main__":
    main()