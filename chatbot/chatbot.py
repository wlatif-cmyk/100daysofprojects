"""
Interactive Chatbot using ChatterBot
A simple chatbot that learns from conversations and can be trained with custom responses.
"""

from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer, ListTrainer
import sys

def create_chatbot():
    """Create and configure the chatbot"""
    print("🤖 Creating your chatbot...")
    
    # Create a new chatbot instance
    chatbot = ChatBot(
        'rizzsimulatorbot',
        storage_adapter='chatterbot.storage.SQLStorageAdapter',
        database_uri='sqlite:///database.sqlite3',
        logic_adapters=[
            {
                'import_path': 'chatterbot.logic.BestMatch',
                'default_response': 'I am still learning. Could you teach me by rephrasing that?',
                'maximum_similarity_threshold': 0.90
            }
        ]
    )
    
    return chatbot

def train_chatbot(chatbot):
    """Train the chatbot with corpus data and custom responses"""
    print("📚 Training the chatbot... This may take a moment.")
    
    # Train with English corpus
    corpus_trainer = ChatterBotCorpusTrainer(chatbot)
    corpus_trainer.train(
        "chatterbot.corpus.english.greetings",
        "chatterbot.corpus.english.conversations"
    )
    
    # Train with custom responses
    list_trainer = ListTrainer(chatbot)
    
    # Custom conversation sets
    custom_conversations = [
        "How are you?",
        "I'm doing great, thanks for asking! How about you?",
        "What's your name?",
        "I'm rizzsimulatorbot, your AI companion!",
        "Tell me a joke",
        "Why did the Python programmer not respond? Because they were stuck in a loop!",
        "What can you do?",
        "I can chat with you, learn from our conversations, and try to be helpful!",
        "Do you like Python?",
        "Absolutely! Python is the language I run on, so it's pretty important to me!",
        "What's the meaning of life?",
        "42! Just kidding... I think it's to learn, grow, and help others.",
        "Tell me something interesting",
        "Did you know that honey never spoils? Archaeologists have found 3000-year-old honey in Egyptian tombs that's still edible!",
        "Goodbye",
        "Goodbye! It was nice chatting with you. Come back soon!",
        "See you later",
        "See you later! Have a wonderful day!",
    ]
    
    list_trainer.train(custom_conversations)
    
    print(" Training complete!\n")

def chat_loop(chatbot):
    """Main chat loop for interacting with the bot"""
    print("="*60)
    print("rizzsimulatorbot is ready to chat!")
    print("="*60)
    print("Tips:")
    print("  - Type your messages and press Enter to chat")
    print("  - Type 'quit', 'exit', or 'bye' to end the conversation")
    print("  - The bot learns from your conversations!")
    print("="*60)
    print()
    
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("rizzsimulatorbot: Goodbye! Thanks for chatting with me! 👋")
                break
            
            # Skip empty inputs
            if not user_input:
                continue
            
            # Get bot response
            response = chatbot.get_response(user_input)
            print(f"rizzsimulatorbot: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\nrizzsimulatorbot: Goodbye! Thanks for chatting! 👋")
            break
        except Exception as e:
            print(f"rizzsimulatorbot: Oops! I encountered an error: {e}")
            print("Let's keep chatting!\n")

def main():
    """Main function to run the chatbot"""
    print("\n" + "="*60)
    print("         WELCOME TO rizzsimulatorbot")
    print("="*60 + "\n")
    
    # Create the chatbot
    chatbot = create_chatbot()
    
    # Train the chatbot
    train_chatbot(chatbot)
    
    # Start chatting
    chat_loop(chatbot)
    
    print("\nThank you for using rizzsimulatorbot!")

if __name__ == "__main__":
    main()