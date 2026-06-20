# Physics Simulation & Creature Evolution Editor
### Overview & Feature Reference Manual

This interactive CAD and neuroevolution workspace allows you to design custom dynamic creatures, set up physical constraints (hinges, motors, springs), and train them using Genetic Algorithms to walk or run on a simulated obstacle course.

---

## 🎮 Workspace Navigation & Interaction

### 1. Advanced Viewport Navigation (Panning & Zoom)
* **Universal Panning:** Drag the workspace in any direction using:
  * `Spacebar + Left Mouse Button (LMB)`
  * `Right Mouse Button (RMB)`
  * `Middle Mouse Button (MMB)`
* **Directional Dragging:** Uses natural "pull" vector mapping so the workspace moves precisely under your cursor.
* **Camera Zoom:** Scroll the mouse wheel up/down to zoom in/out relative to the screen center.

### 2. Grid & Snapping Controls
* **Toggle Grid (`G` Key):** Instantly toggles the background grid overlay.
* **Coordinate Snapping:** When the grid is visible, all shape creation, shape positioning, and joint dragging actions automatically snap to the nearest grid intersection (`20px`).
* **Fluid Manipulation:** Hiding the grid automatically disables snapping, allowing for complete pixel-perfect freedom.

---

## 🛠️ Design & Creation Tools

### 1. Shape Placement (Place Mode)
* **Geometry Choices:** Circle, Rectangle, and custom Polygon shapes.
* **Custom Polygons:** Click in sequence to define arbitrary vertices, then click near the starting point to seal the shape. The center of mass is automatically calculated to prevent weight imbalances.
* **Live Ghost Preview:** Displays a semi-transparent preview of the shape under the cursor before you place it.

### 2. Hinge & Spring Connections (Joint Mode)
* **Precision Twin-Anchor Click:**
  * **First Click (`body_a`):** Locks the starting anchor position to the exact coordinate you clicked.
  * **Second Click (`body_b`):** Connects the joint.
* **Rubberband Preview:** A dynamic line and joint icon are drawn between your first click and the cursor to preview placement.
* **Tolerance Handling:** Missed clicks in empty space are safely ignored, preserving your first body selection.
* **Hinge Joints:** Motorized rotary hinges with custom torque limits, rate controls, and rotational limits.
* **Spring Joints:** Flexible Damped Springs with editable stiffness, damping, and rest length.

### 3. Drag-and-Drop Editing (Select Mode)
* **Body Repositioning:** Left-click and drag any body. All connected joints dynamically follow the body.
* **Live Joint Re-Alignment:** Moving a body automatically re-aligns all connected hinge/spring anchors, eliminating joint tension and preventing physical explosions.
* **Direct Anchor Dragging:** Click on a Hinge joint pivot or Spring endpoints and drag them to adjust coordinates.
* **Undo & Redo (`Ctrl+Z` / `Ctrl+Y`):** Fully integrated command history stack that tracks all moves, additions, deletions, and property modifications.

---

## 🎛️ Properties Panel

Click on any body or joint in **Select Mode** to configure its parameters in real-time in the sidebar:

### For Bodies
| Parameter | Description |
| :--- | :--- |
| **Name** | Custom identifier for the body part. |
| **Mass** | Weight of the body (affects gravity pull, torque limits, and moment of inertia). |
| **Friction & Elasticity** | Surface friction and bounciness. |
| **Radius / Width / Height** | Live sliders to adjust dimensions. **Pymunk shapes are rebuilt dynamically on-the-fly.** |

### For Joints
| Parameter | Description |
| :--- | :--- |
| **Name** | Custom identifier for the joint. |
| **Min & Max Angle** | Hard rotational bounds for hinge movement. |
| **Max Torque** | Maximum force the neural motor can exert. |
| **Stiffness & Damping** | Spring constants (for Spring Joints only). |

---

## ⚡ Physics Engine & Stability

* **Pymunk 6.x Solver:** Uses a sub-stepped integrator (`8 steps per frame`) to guarantee stability.
* **Low-Level Self-Collision Ignoring:** All creature parts are assigned to a unified collision group (`group=1`). This disables body-on-body physical overlaps, preventing clip-explosions and allowing legs and joints to rotate past each other smoothly.
* **Ground Traction:** All parts and feet collide normally with the static ground (`y = 0.0`), allowing for realistic locomotion.

---

## 🧠 Creature Neuroevolution

### 1. The Neural Brain
* Each creature is controlled by a Multi-Layer Perceptron (MLP) neural network.
* **Inputs (14):** Torso angle/velocity, limb angles/velocities, joint limits, and foot-to-ground contact sensors.
* **Outputs (3):** Direct motor rates applied to each active hinge joint.

### 2. Genetic Algorithm (GA) Training
* Launch the **Neural Training** runner to evolve a creature to walk.
* Displays a real-time progress screen showing the best creature of each generation walking along an endless ground track.
* Automatically saves checkpoints so you can reload and export successful brain templates.
