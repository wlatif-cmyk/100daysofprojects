import turtle
import random

class InteractiveArtGame:
    """Interactive hypnotic art drawing game - draw with your cursor"""
    
    def __init__(self):
        # Setup screen
        self.screen = turtle.Screen()
        self.screen.setup(1000, 800)
        self.screen.bgcolor("black")
        self.screen.title("Hypnotic Art Drawing Game")
        
        # Main drawing turtle
        self.t = turtle.Turtle()
        self.t.speed(0)
        self.t.hideturtle()
        self.t.pensize(2)
        
        # UI turtle for text
        self.ui = turtle.Turtle()
        self.ui.hideturtle()
        self.ui.speed(0)
        self.ui.penup()
        
        # Drawing state
        self.drawing_mode = "spiral"
        self.is_drawing = False
        self.last_pos = (0, 0)
        self.hue = 0
        
        # 3 simple modes
        self.modes = ["spiral", "mandala", "trail"]
        self.mode_index = 0
        
        # Setup UI and bindings
        self.draw_ui()
        self.setup_bindings()
        
    def hsv_to_rgb(self, h, s=1, v=1):
        """Convert HSV to RGB for smooth rainbow colors"""
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c
        
        if h < 60:
            r, g, b = c, x, 0
        elif h < 120:
            r, g, b = x, c, 0
        elif h < 180:
            r, g, b = 0, c, x
        elif h < 240:
            r, g, b = 0, x, c
        elif h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        
        return (r + m, g + m, b + m)
    
    def get_color(self):
        """Get the next rainbow color"""
        color = self.hsv_to_rgb(self.hue)
        self.hue = (self.hue + 5) % 360
        return color
    
    def draw_ui(self):
        """Draw simple UI text"""
        self.ui.clear()
        self.ui.color("white")
        
        # Title
        self.ui.goto(0, 350)
        self.ui.write("HYPNOTIC ART DRAWING", align="center", 
                     font=("Arial", 18, "bold"))
        
        # Current mode
        self.ui.goto(0, 320)
        self.ui.write(f"Mode: {self.drawing_mode.upper()}", align="center", 
                     font=("Arial", 14, "normal"))
        
        # Instructions
        self.ui.goto(0, -360)
        self.ui.write("Click and Drag to Draw  |  SPACE: Change Mode  |  C: Clear  |  S: Save", 
                     align="center", font=("Arial", 11, "normal"))
    
    def setup_bindings(self):
        """Setup mouse and keyboard controls"""
        self.screen.onscreenclick(self.on_click)
        self.screen.onkey(self.next_mode, "space")
        self.screen.onkey(self.clear_canvas, "c")
        self.screen.onkey(self.save_art, "s")
        self.screen.listen()
    
    def on_click(self, x, y):
        """Handle mouse clicks and dragging"""
        # Ignore clicks on UI area
        if y > 300:
            return
        
        self.is_drawing = True
        self.last_pos = (x, y)
        self.draw_at_position(x, y)
        
        # Track dragging
        self.screen.ontimer(lambda: self.track_drag(x, y), 10)
    
    def track_drag(self, x, y):
        """Track mouse dragging for continuous drawing"""
        if self.is_drawing:
            try:
                mx = self.screen.getcanvas().winfo_pointerx() - self.screen.getcanvas().winfo_rootx()
                my = self.screen.getcanvas().winfo_pointery() - self.screen.getcanvas().winfo_rooty()
                
                # Convert to turtle coordinates
                canvas_width = self.screen.window_width()
                canvas_height = self.screen.window_height()
                tx = (mx - canvas_width / 2) * (self.screen.window_width() / canvas_width)
                ty = (canvas_height / 2 - my) * (self.screen.window_height() / canvas_height)
                
                # Draw if moved enough
                if abs(tx - self.last_pos[0]) > 5 or abs(ty - self.last_pos[1]) > 5:
                    self.draw_at_position(tx, ty)
                    self.last_pos = (tx, ty)
                
                self.screen.ontimer(lambda: self.track_drag(tx, ty), 10)
            except:
                self.is_drawing = False
    
    def draw_at_position(self, x, y):
        """Draw pattern at cursor position"""
        if self.drawing_mode == "spiral":
            self.draw_spiral(x, y)
        elif self.drawing_mode == "mandala":
            self.draw_mandala(x, y)
        elif self.drawing_mode == "trail":
            self.draw_trail(x, y)
    
    def draw_spiral(self, x, y):
        """Draw a spiral pattern"""
        self.t.penup()
        self.t.goto(x, y)
        self.t.pendown()
        self.t.pencolor(self.get_color())
        
        for i in range(20):
            self.t.forward(i * 0.5)
            self.t.left(20)
    
    def draw_mandala(self, x, y):
        """Draw a mandala pattern"""
        self.t.penup()
        self.t.goto(x, y)
        self.t.pencolor(self.get_color())
        
        segments = 8
        for i in range(segments):
            self.t.penup()
            self.t.goto(x, y)
            self.t.setheading(360 / segments * i)
            self.t.pendown()
            self.t.circle(20, 60)
            self.t.left(120)
            self.t.circle(20, 60)
    
    def draw_trail(self, x, y):
        """Draw a smooth continuous trail"""
        self.t.pencolor(self.get_color())
        self.t.pensize(3)
        
        if abs(x - self.last_pos[0]) < 100 and abs(y - self.last_pos[1]) < 100:
            self.t.penup()
            self.t.goto(self.last_pos[0], self.last_pos[1])
            self.t.pendown()
            self.t.goto(x, y)
        else:
            self.t.penup()
            self.t.goto(x, y)
    
    def next_mode(self):
        """Switch to next drawing mode"""
        self.mode_index = (self.mode_index + 1) % len(self.modes)
        self.drawing_mode = self.modes[self.mode_index]
        self.draw_ui()
        print(f"Switched to: {self.drawing_mode.upper()}")
    
    def clear_canvas(self):
        """Clear the drawing"""
        self.t.clear()
        self.hue = 0
        print("Canvas cleared")
    
    def save_art(self):
        """Save your artwork"""
        filename = f"art_{random.randint(1000, 9999)}.eps"
        self.screen.getcanvas().postscript(file=filename)
        print(f"Art saved as {filename}")
    
    def run(self):
        """Start the game"""
        print("\nHYPNOTIC ART DRAWING GAME")
        print("=" * 40)
        print("CONTROLS:")
        print("  Click and drag to draw")
        print("  SPACE - Change mode")
        print("  C - Clear canvas")
        print("  S - Save artwork")
        print("=" * 40)
        print("Start drawing!\n")
        
        self.screen.mainloop()


# Run the game
if __name__ == "__main__":
    game = InteractiveArtGame()
    game.run()