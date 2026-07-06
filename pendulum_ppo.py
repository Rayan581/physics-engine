import math
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3.common.callbacks import BaseCallback
import pygame
from config import CANVAS_BG
from classes.ai import BaseTrainer

MAX_STEPS = 500               # About 8 seconds at 60 FPS
MAX_ANGLE = math.radians(15)  # Fall angle limit

class PendulumPPOTrainer(BaseTrainer, gym.Env):
    is_sb3     = True
    algorithm  = "PPO"
    model_name = "pendulum_ppo"

    def __init__(self, game_instance=None):
        super().__init__()
        self.game = game_instance
        self.steps_trained = 0
        self._step_count = 0
        self.total_steps = 0
        self.target_total_steps = 100_000

        # Observations: [cart_x, cart_vx, rod_angle, rod_angular_velocity]
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(4,), dtype=np.float32
        )

        # Action: horizontal force on the cart
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(1,), dtype=np.float32
        )

        self._find_bodies()

    def _find_bodies(self):
        if not self.game:
            return
            
        self.cart = next((b for b in self.game.bodies if getattr(b, 'name', '') == "cart"), None)
        self.rod  = next((b for b in self.game.bodies if getattr(b, 'name', '') == "pendulum_rod"), None)
        
        if not all([self.cart, self.rod]):
            print("PendulumPPOTrainer: Missing 'cart' or 'pendulum_rod' bodies in the scene!")
        else:
            self.start_cart_x = self.cart.x

        # Find walls to determine limits dynamically
        walls = [b for b in self.game.bodies if getattr(b, 'name', '') == "wall"]
        if len(walls) >= 2:
            walls.sort(key=lambda w: w.x)
            # Add a small 15px margin to stop just before hitting the walls
            self.min_x = walls[0].x + 15.0
            self.max_x = walls[-1].x - 15.0
        else:
            # Fallback if walls are missing
            self.min_x = getattr(self, 'start_cart_x', 0) - 90.0
            self.max_x = getattr(self, 'start_cart_x', 0) + 90.0

    # ── BaseTrainer interface ────────────────────────────────────────────────────

    def setup(self, bodies, joints):
        return True

    def get_observation(self):
        return self._obs().tolist()

    def apply_action(self, action):
        self._apply(action)

    def get_camera_target(self):
        if self.cart:
            return (self.cart.x, self.cart.y)
        return None

    def check_status(self):
        done, reward = self._check()
        return done, reward

    # ── Gym interface ────────────────────────────────────────────────────────────

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        for b in self.game.bodies:
            b.reset()
            
        if self.cart:
            self.start_cart_x = self.cart.x
            # Add small random noise to velocities to make training robust. 
            # Directly modifying angles breaks positional constraints in the physics engine.
            self.rod.angular_velocity += np.random.uniform(-1.0, 1.0)
            self.cart.vx += np.random.uniform(-20, 20)
            
        self._step_count = 0
        return self._obs(), {}

    def step(self, action):
        self._step_count += 1
        self.steps_trained += 1
        self.total_steps += 1
        
        FPS = 60.0
        
        # --- Handle Pygame Events and UI during Training ---
        if self.game.sim_state == 'training':
            import time
            current_time = time.time()
            fast_forward = getattr(self.game, 'fast_forward', False)

            # In fast-forward: only pump events every 500ms — no rendering at all.
            # In normal mode: render at up to 60 Hz.
            ui_interval = 0.5 if fast_forward else (1.0 / 60.0)

            if current_time - getattr(self, '_last_ui_update', 0) > ui_interval:
                self._last_ui_update = current_time
                events = pygame.event.get()
                for ev in events:
                    if ev.type == pygame.QUIT:
                        self.game.running = False
                        raise Exception("Aborted")
                    elif ev.type == pygame.KEYDOWN:
                        if ev.key == pygame.K_ESCAPE:
                            raise Exception("Aborted")
                        elif ev.key == pygame.K_f:
                            self.game.fast_forward = not getattr(self.game, 'fast_forward', False)
                        elif ev.key == pygame.K_m:
                            self.game.magnetic_enabled = not getattr(self.game, 'magnetic_enabled', False)
                    elif ev.type == pygame.MOUSEBUTTONDOWN:
                        if ev.button == 1: self.game._lmb_down(ev.pos)
                        elif ev.button == 3: self.game._rmb_down(ev.pos)
                        elif ev.button == 4: self.game._scroll(ev.pos, 1.15)
                        elif ev.button == 5: self.game._scroll(ev.pos, 1/1.15)
                    elif ev.type == pygame.MOUSEBUTTONUP:
                        if ev.button == 1: self.game._lmb_up(ev.pos)
                        elif ev.button == 3: self.game._rmb_up(ev.pos)
                    elif ev.type == pygame.MOUSEMOTION:
                        self.game._motion(ev.pos)

                if not fast_forward:
                    self.game.canvas.fill(CANVAS_BG)
                    self.game._draw()
                    if self.cart:
                        self.game.camera.cam_x += (self.cart.x - self.game.camera.cam_x) * 5.0 * (1.0 / FPS)
                        self.game.camera.cam_y += (self.cart.y - self.game.camera.cam_y) * 5.0 * (1.0 / FPS)
                    self._draw_hud(0)
                    pygame.display.flip()

            if self.game.sim_state != 'training':
                raise Exception("Aborted")

        self._apply(action)
        self.game._physics_step(1.0 / FPS)

        obs          = self._obs()
        done, reward = self._check()
        truncated    = self._step_count >= MAX_STEPS

        return obs, reward, done, truncated, {}

    # ── Internals ────────────────────────────────────────────────────────────────

    def _obs(self):
        if not self.cart or not self.rod:
            return np.zeros(4, dtype=np.float32)
            
        center_x = (getattr(self, 'min_x', 0) + getattr(self, 'max_x', 0)) / 2.0
        max_dist = max((getattr(self, 'max_x', 1) - getattr(self, 'min_x', 0)) / 2.0, 1.0)
            
        return np.array([
            (self.cart.x - center_x) / max_dist,
            self.cart.vx / 200.0,
            self.rod.angle / MAX_ANGLE,
            self.rod.angular_velocity / 10.0,
        ], dtype=np.float32)

    def _apply(self, action):
        if self.cart:
            # Action is in [-1, 1]. Multiply to get a reasonable force for a mass of 1.0.
            # Increased force to give the agent more authority to catch the pendulum.
            self.cart.vx += float(action[0]) * 40.0

    def _check(self):
        if not self.cart or not self.rod:
            return True, 0.0
            
        angle = self.rod.angle

        fallen = abs(angle) > MAX_ANGLE
        out_of_bounds = self.cart.x < getattr(self, 'min_x', -90) or self.cart.x > getattr(self, 'max_x', 90)
        
        done = fallen or out_of_bounds
        
        center_x = (getattr(self, 'min_x', 0) + getattr(self, 'max_x', 0)) / 2.0
        max_dist = max((getattr(self, 'max_x', 1) - getattr(self, 'min_x', 0)) / 2.0, 1.0)
        dist_from_center = abs(self.cart.x - center_x)
        
        # Reward: +1 for surviving, with stronger penalties for instability
        angle_penalty = (abs(angle) / MAX_ANGLE) ** 2
        pos_penalty = (dist_from_center / max_dist) ** 2
        
        # Encourage the agent to keep the pole perfectly upright and in the center
        reward = 1.0 - angle_penalty - (0.2 * pos_penalty)
        
        return done, reward

    def _draw_hud(self, best_fitness):
        font = self.game.ctx_menu._font
        font_t = self.game.ctx_menu._font_t
        PAD, W, H = 12, 260, 132
        panel = pygame.Surface((W, H), pygame.SRCALPHA)
        panel.fill((20, 16, 12, 220))
        pygame.draw.rect(panel, (58, 44, 26, 200), (0, 0, W, H), 1)
        self.game.canvas.blit(panel, (PAD, PAD))

        x0, y0 = PAD + 8, PAD + 8
        title = font_t.render("PPO Pendulum Training", True, (255, 200, 100))
        self.game.canvas.blit(title, (x0, y0))

        y1 = y0 + 20
        prog_lbl = font.render(f"Ep Step: {self._step_count}/{MAX_STEPS}", True, (200,200,200))
        self.game.canvas.blit(prog_lbl, (x0, y1 + 13))

        y2 = y1 + 24
        total_lbl = font.render(f"Total:   {self.total_steps}/{self.target_total_steps}", True, (200,200,200))
        self.game.canvas.blit(total_lbl, (x0, y2 + 13))

        y3 = y2 + 48
        viz_on = not getattr(self.game, 'fast_forward', False)
        if viz_on:
            self.game.canvas.blit(font.render("VIZ ON   [F] toggle", True, (100,255,100)), (x0, y3))
        else:
            self.game.canvas.blit(font.render("VIZ OFF  [F] toggle", True, (255,100,100)), (x0, y3))
        self.game.canvas.blit(font.render("ESC: abort", True, (150,150,150)), (x0, y3 + 24))


class RenderCallback(BaseCallback):
    """
    Custom callback for rendering the agent every N steps.
    """
    def __init__(self, render_freq: int, verbose=0):
        super().__init__(verbose)
        self.render_freq = render_freq
        self.next_render_step = render_freq

    def _on_step(self) -> bool:
        if self.num_timesteps >= self.next_render_step:
            print(f"--- Reached {self.num_timesteps} steps, displaying a rollout ---")
            self._render_rollout()
            self.next_render_step += self.render_freq
        return True
        
    def _render_rollout(self):
        env = self.training_env.envs[0].env
        game = env.game
        
        # Save state
        old_sim_state = game.sim_state
        old_ff = getattr(game, 'fast_forward', False)
        
        # Force visualization on
        game.sim_state = 'ai_playing'
        game.fast_forward = False
        
        obs, _ = env.reset()
        done = False
        FPS = 60.0
        while not done:
            action, _ = self.model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
            
            # Manual render and event pump for the callback
            events = pygame.event.get()
            for ev in events:
                if ev.type == pygame.QUIT:
                    game.running = False
                    raise Exception("Aborted")
                elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    raise Exception("Aborted")
                elif ev.type == pygame.MOUSEBUTTONDOWN:
                    if ev.button == 1: game._lmb_down(ev.pos)
                    elif ev.button == 3: game._rmb_down(ev.pos)
                    elif ev.button == 4: game._scroll(ev.pos, 1.15)
                    elif ev.button == 5: game._scroll(ev.pos, 1/1.15)
                elif ev.type == pygame.MOUSEBUTTONUP:
                    if ev.button == 1: game._lmb_up(ev.pos)
                    elif ev.button == 3: game._rmb_up(ev.pos)
                elif ev.type == pygame.MOUSEMOTION:
                    game._motion(ev.pos)
                    
            game.canvas.fill(CANVAS_BG)
            game._draw()
            if env.cart:
                game.camera.cam_x += (env.cart.x - game.camera.cam_x) * 5.0 * (1.0 / FPS)
                game.camera.cam_y += (env.cart.y - game.camera.cam_y) * 5.0 * (1.0 / FPS)
                
            # Draw callback HUD
            font = game.ctx_menu._font
            game.canvas.blit(font.render("--- 10% PROGRESS DEMONSTRATION ---", True, (255, 200, 100)), (20, 20))
            pygame.display.flip()
            
            game.clock.tick(FPS) # Keep demonstration at correct framerate
            
        # Restore state
        game.sim_state = old_sim_state
        game.fast_forward = old_ff
        env.reset()
