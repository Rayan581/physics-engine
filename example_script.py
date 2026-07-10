import math
import pygame

class SceneScript:
    """
    Example script demonstrating how to control objects in the physics engine.
    This script will continuously push a box named "target_box" upwards,
    creating a bouncing effect.
    """
    def __init__(self, game):
        self.game = game
        self.box = None
        
    def setup(self):
        """Called once when the script is loaded or the scene starts."""
        print("Example Script Initialized!")
        # Find the target box by name
        for b in self.game.bodies:
            if getattr(b, 'name', '') == 'target_box':
                self.box = b
                break
                
        if self.box:
            print("Found 'target_box'! It will start bouncing automatically.")
        else:
            print("Could not find 'target_box'. Create a box and name it 'target_box'.")
            
    def update(self, dt):
        """
        Called every physics step (including during AI training).
        `dt` is the time step (e.g. 1/60.0).
        """
        if not self.box:
            return
            
        # Example: if the box falls below y=200, apply an upward velocity impulse
        if self.box.y > 200:
            self.box.vy = -600  # bounce upwards
            
    def draw(self, canvas, camera):
        """
        Called every frame. Useful for custom HUDs or visual effects.
        """
        if not self.box:
            return
            
        # Draw a custom tracking circle around the box
        # Convert world coordinates to screen coordinates
        screen_x, screen_y = camera.w2s(self.box.x, self.box.y)
        pygame.draw.circle(canvas, (255, 100, 100), (int(screen_x), int(screen_y)), 30, 2)
        
    def on_event(self, event):
        """
        Called on every Pygame event.
        """
        # Example: click to instantly stop the box
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.box:
                self.box.vx = 0
                self.box.vy = 0
