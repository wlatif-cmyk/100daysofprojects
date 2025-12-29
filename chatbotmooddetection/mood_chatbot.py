from textblob import TextBlob
import random

class MoodChatbot:
    def __init__(self):
        self.name = "MoodBot"
        
    def analyze_mood(self, text):
        """Analyze the sentiment/mood of the text"""
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        # Classify mood based on polarity score
        if polarity > 0.3:
            return "happy"
        elif polarity < -0.3:
            return "sad"
        elif polarity < -0.1:
            return "angry"
        else:
            return "neutral"
    
    def get_response(self, mood, user_input):
        """Generate a response based on detected mood"""
        responses = {
            "happy": [
                "That's wonderful! I'm so glad you're feeling happy! 😊",
                "Your positivity is contagious! Tell me more!",
                "I love your energy! What's making you so cheerful?",
                "Awesome! It's great to hear such positive vibes!"
            ],
            "sad": [
                "I'm sorry you're feeling down. I'm here to listen if you want to talk.",
                "That sounds tough. Would you like to share what's bothering you?",
                "I hear you. Sometimes it helps to talk about it. I'm here for you.",
                "It's okay to feel sad sometimes. Want to tell me more about it?"
            ],
            "angry": [
                "I can sense you're upset. Take a deep breath. What's bothering you?",
                "I understand you're frustrated. Let's talk it through calmly.",
                "I'm here to help. What's making you angry?",
                "It sounds like something really got to you. Want to vent about it?"
            ],
            "neutral": [
                "I see. Tell me more about that.",
                "Interesting. How do you feel about it?",
                "Got it. What else is on your mind?",
                "I'm listening. What would you like to talk about?"
            ]
        }
        
        return random.choice(responses[mood])
    
    def chat(self):
        """Main chat loop"""
        print(f"\n{'='*60}")
        print(f"Hello! I'm {self.name}, a mood-detecting chatbot!")
        print("I can sense whether you're happy, sad, angry, or neutral.")
        print("Type 'quit' or 'exit' to end our conversation.")
        print(f"{'='*60}\n")
        
        while True:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print(f"\n{self.name}: Goodbye! Take care! 👋\n")
                break
            
            if not user_input:
                print(f"{self.name}: Please say something!\n")
                continue
            
            # Detect mood
            mood = self.analyze_mood(user_input)
            
            # Get appropriate response
            response = self.get_response(mood, user_input)
            
            # Show detected mood (optional - you can comment this out)
            print(f"[Detected mood: {mood.upper()}]")
            print(f"{self.name}: {response}\n")

if __name__ == "__main__":
    bot = MoodChatbot()
    bot.chat()