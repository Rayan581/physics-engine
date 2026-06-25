from typing import Tuple, List, Any

class BaseTrainer:
    """
    Base class for AI Training Plugins.
    Custom training scripts should inherit from this class.
    """
    
    config_path: str = "config-feedforward"
    max_steps: int = 600  # Default 10 seconds at 60 FPS
    
    def setup(self, bodies: list, joints: list) -> bool:
        """
        Called once before training or playback begins.
        Identify your robot's bodies and joints here.
        Return True if successful, False if the required objects are missing.
        """
        return True
        
    def get_observation(self) -> List[float]:
        """
        Return the current state of the simulation as a list of floats.
        Must match the number of inputs in your NEAT config.
        """
        raise NotImplementedError
        
    def apply_action(self, action: List[float]):
        """
        Apply the neural network output (action) to the motors/bodies.
        """
        raise NotImplementedError
        
    def get_camera_target(self) -> Tuple[float, float] | None:
        """
        Optional: Return the (x, y) coordinates the camera should follow during training/playback.
        Return None if the camera should not follow anything.
        """
        return None
        
    def check_status(self) -> Tuple[bool, float]:
        """
        Return (is_done, current_fitness).
        is_done should be True if the robot falls over, reaches the goal, or the simulation should end early.
        current_fitness is the continuous reward score.
        """
        raise NotImplementedError
