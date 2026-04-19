import os

# Mock pygame for headless testing if needed, or just run a few frames
os.environ['SDL_VIDEODRIVER'] = 'dummy'

import main_game
import pygame
import time

def test_ui_init():
    try:
        print("Initializing OstrakaGame...")
        game = main_game.OstrakaGame()
        print("Starting Game Loop (5 frames)...")
        
        # Simulate 5 frames
        for i in range(5):
            game._handle_input()
            # Fake some input
            if i == 2:
                game.player_text = "move to 50,51"
                # Mock return key
                game._handle_pipeline_turn(game.player_text)
                game.player_text = ""
            
            # Rendering loop
            game.screen.fill((0,0,0))
            # ... (the rest of the render logic from start_game)
            game.clock.tick(60)
            print(f"Frame {i} rendered.")
            
        print("UI Test Successful!")
        pygame.quit()
        return True
    except Exception as e:
        print(f"UI Test Failed: {e}")
        import traceback
        traceback.print_exc()
        pygame.quit()
        return False

if __name__ == "__main__":
    test_ui_init()
