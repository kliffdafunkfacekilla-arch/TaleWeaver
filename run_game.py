import sys
import os

# Add src directory to path so imports work correctly
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

try:
    import main_game
    if __name__ == "__main__":
        main_game.main()
except ImportError as e:
    print(f"Error: Could not find game source files. {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
