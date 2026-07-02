# Pygame Physics Engine

A custom-built, fully interactive 2D physics sandbox and Reinforcement Learning (RL) environment created in Python using `pygame-ce`.

This engine serves a dual purpose:
1. **Interactive Sandbox**: A robust 2D physics engine where users can build mechanisms, stack blocks, attach motors, and interact with objects in real-time.
2. **Reinforcement Learning Environment**: A Gymnasium-compatible API that hooks seamlessly into Stable Baselines 3, allowing AI agents to train on custom physics tasks.

## Features

### 🛠️ Physics Sandbox
- **Custom Rigid Body Dynamics**: Supports rectangles, circles, and arbitrary convex polygons.
- **Advanced Collision Engine**: Features SAT (Separating Axis Theorem) and optimized circle collisions, backed by impulse resolution (friction, restitution, and positional correction slop).
- **Interactive Tools**: Built-in HUD toolbox to draw objects directly into the world with a mouse click.
- **Constraints & Motors**: Connect bodies together with `MotorJoints` and configure angle limits or continuous rotation speeds.
- **Property Editor**: Right-click context menus to modify object mass, restitution, friction, or joint constraints on the fly.
- **Save & Load**: Fully serialize your scenes to `.json` files to share or train AI models on later.

### 🧠 Reinforcement Learning Integration
- **Gymnasium Compatible**: Wraps the physics simulation into a standard Gym environment.
- **Visual Callbacks**: View your agent's learning progress in real-time without disrupting the training process. The custom `RenderCallback` handles periodic visual rollouts.
- **State Machine Control**: The engine elegantly handles transitions between human `playing`, AI `training`, and `ai_playing` states, complete with dynamic Fast-Forward controls to accelerate physics calculations during training.

## Included Environments

### Pendulum Balancing (`pendulum_ppo.py`)
A classic control task reimagined for a continuous physics sandbox.
An agent is trained using PPO (Proximal Policy Optimization) to balance a rigid pendulum pole mounted on a cart. Instead of hardcoded physics constants, the agent directly interacts with the sandbox mechanics. It features dynamic boundary recognition by detecting `wall` objects within the scene, allowing the user to stretch or shrink the balancing track visually.

## Codebase Architecture

The project is structured to separate rendering/UI from core physics mathematics.

- `main.py`: The main entry point to start the application.
- `config.py`: Global constants, UI color themes (warm dark amber), physics constants (gravity = 500 px/s²), and collision slop settings.
- `classes/`
  - **`physics.py`**: The mathematical core. Handles SAT collision detection, depth calculations, and impulse application.
  - **`body.py`**: Classes defining rigid body shapes (`RectBody`, `CircleBody`, `PolygonBody`, `TextBody`).
  - **`joints.py`**: Implementation of positional and angular constraints (`MotorJoint`).
  - **`game.py`**: The orchestrator. Manages the Pygame event loop, rendering pipeline, and simulation state transitions.
  - **`toolbox.py` & `context_menu.py`**: The graphical user interface components.
  - **`drawing.py`**: Handles user input for the interactive shape and joint creation tools.
  - **`serialization.py`**: Logic for converting bodies and joints to/from JSON.
  - **`ai.py`**: Contains `BaseTrainer`, the base interface for writing custom Reinforcement Learning plugins.

## Installation & Requirements

Ensure you have Python 3.10+ installed.

1. Clone this repository.
2. Install the required dependencies:
   ```bash
   pip install pygame-ce numpy gymnasium stable-baselines3
   ```
   *(Note: `pygame-ce` is the Community Edition of Pygame, offering superior performance and modern features. You may install pygame instead of pygame-ce).* 

## Usage Instructions

### Running the Sandbox
Start the engine by running:
```bash
python main.py
```
- **Camera Controls**: Right-click and drag anywhere on the canvas to pan. Use the scroll wheel to zoom in and out.
- **Magnetic Cursor**: Press **`M`** while running to toggle a physics-accurate magnetic repelling field at your cursor. Hold **`SHIFT`** and scroll to dynamically adjust the radius. Great for pushing objects and testing AI stability!
- **Adding Objects**: Use the toolbar on the left to select a shape (Rect, Circle, Poly). Click (or click-and-drag) on the canvas to instantiate it.
- **Editing Objects**: Right-click on any physics body to open its context menu and edit properties like `fixed` (static), mass, or color.
- **Motor Joints**: Select the Motor tool and click where two bodies overlap to connect them.

### Running an AI Trainer
1. Build and save your physics scene (or load an existing one like `single_pendulum.json`).
2. Click **Load AI** from the left toolbar and select a trainer script (e.g., `pendulum_ppo.py`).
3. Click **Run AI** to begin training.
4. While training, you can press **`F`** to toggle Fast-Forward mode. Fast-Forward mode disables Pygame rendering to massively increase the steps-per-second throughput of the AI model.