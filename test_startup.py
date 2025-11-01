import sys
import os
import traceback

# Add the current directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("Testing voice typing startup...")
    from voice_typing import VoiceTypingApp
    print("Import successful")
    
    print("Creating app instance...")
    app = VoiceTypingApp()
    print("App created successfully")
    
    print("App should be running now. Check system tray for icon.")
    input("Press Enter to exit...")
    
except Exception as e:
    print(f"Error occurred: {e}")
    print("Full traceback:")
    traceback.print_exc()
    input("Press Enter to exit...")