import pygame
from config import *
from classes.body import Body
from classes.drawing import DrawingTool
from classes.toolbox import Toolbox
from classes.context_menu import ContextMenu
from classes.physics import detect_all, resolve, positional_correction, boundary_collide


# Simulation states
STOPPED = 'stopped'
PLAYING = 'playing'
PAUSED  = 'paused'


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((TOOLBOX_WIDTH + WIDTH, HEIGHT))
        self.clock  = pygame.time.Clock()
        self.running = True

        self.bodies: list[Body] = []
        self.sim_state = STOPPED

        self.drawing = DrawingTool()
        self.toolbox = Toolbox(0, 0, TOOLBOX_WIDTH, HEIGHT)
        self.toolbox.init_fonts()

        self.ctx_menu = ContextMenu()
        self.ctx_menu.init_fonts()

        # Canvas sub-surface — bodies use canvas-relative coordinates
        self.canvas: pygame.Surface = self.screen.subsurface(
            pygame.Rect(TOOLBOX_WIDTH, 0, WIDTH, HEIGHT))

    # ── Main loop ───────────────────────────────────────────────────────────────

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.033)
            self.handle_events()
            if self.sim_state == PLAYING:
                self._physics_step(dt)
            self.canvas.fill(Colors.BLACK)
            self._draw()
            pygame.display.flip()
        pygame.quit()

    # ── Physics ─────────────────────────────────────────────────────────────────

    def _physics_step(self, dt: float):
        sub = dt / PHYSICS_SUBSTEPS
        for _ in range(PHYSICS_SUBSTEPS):
            for body in self.bodies:
                body.integrate(sub)
            for m in detect_all(self.bodies):
                resolve(m)
                positional_correction(m)
            for body in self.bodies:
                boundary_collide(body, WIDTH, HEIGHT)

    # ── Simulation control ──────────────────────────────────────────────────────

    def _play(self):
        if self.sim_state == STOPPED:
            self.drawing.cancel()
        self.sim_state = PLAYING
        self.ctx_menu.close()

    def _pause(self):
        if self.sim_state == PLAYING:
            self.sim_state = PAUSED

    def _stop(self):
        self.sim_state = STOPPED
        for body in self.bodies:
            body.reset()
        self.ctx_menu.close()

    def _sim_action(self, action: str):
        if action == PLAYING:
            self._play()
        elif action == PAUSED:
            self._pause()
        elif action == STOPPED:
            self._stop()

    # ── Events ─────────────────────────────────────────────────────────────────

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._handle_key(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos)

    def _handle_key(self, key: int):
        if key == pygame.K_ESCAPE:
            if self.ctx_menu.is_open:
                self.ctx_menu.close()
            elif self.drawing.mode:
                self.drawing.cancel()
            else:
                self.running = False
        elif key == pygame.K_r and self.sim_state == STOPPED:
            self.drawing.set_mode(None if self.drawing.mode == 'rect'    else 'rect')
        elif key == pygame.K_c and self.sim_state == STOPPED:
            self.drawing.set_mode(None if self.drawing.mode == 'circle'  else 'circle')
        elif key == pygame.K_p and self.sim_state == STOPPED:
            self.drawing.set_mode(None if self.drawing.mode == 'polygon' else 'polygon')
        elif key == pygame.K_SPACE:
            if   self.sim_state == STOPPED: self._play()
            elif self.sim_state == PLAYING: self._pause()
            elif self.sim_state == PAUSED:  self._play()
        elif key == pygame.K_s:
            self._stop()

    def _handle_click(self, pos):
        # ── Toolbox ───────────────────────────────────────────────────────────
        if self.toolbox.contains(pos):
            action = self.toolbox.get_sim_action_at(pos)
            if action:
                self._sim_action(action)
                return
            tool = self.toolbox.get_tool_at(pos)
            if tool and self.sim_state == STOPPED:
                self.drawing.set_mode(None if self.drawing.mode == tool else tool)
            return

        # ── Context menu ──────────────────────────────────────────────────────
        if self.ctx_menu.is_open and self.ctx_menu.contains(pos):
            self.ctx_menu.handle_click(pos)
            return

        # ── Canvas click ──────────────────────────────────────────────────────
        canvas_pos = (pos[0] - TOOLBOX_WIDTH, pos[1])

        # Close menu if clicking outside it
        if self.ctx_menu.is_open:
            self.ctx_menu.close()
            return

        if self.sim_state == PLAYING:
            return  # ignore canvas clicks during simulation

        if self.sim_state in (STOPPED, PAUSED):
            # Try to select a body first
            for body in reversed(self.bodies):
                if body.hit_test(*canvas_pos):
                    self.ctx_menu.open(body, *pos)
                    self.drawing.cancel()
                    return
            # Otherwise pass to drawing tool (only in STOPPED)
            if self.sim_state == STOPPED:
                self.drawing.handle_click(canvas_pos, self.bodies.append)

    # ── Draw ────────────────────────────────────────────────────────────────────

    def _draw(self):
        for body in self.bodies:
            body.draw(self.canvas)

        # Ghost preview only while stopped
        if self.sim_state == STOPPED:
            mx, my = pygame.mouse.get_pos()
            self.drawing.draw_preview(self.canvas, (mx - TOOLBOX_WIDTH, my))

        mouse = pygame.mouse.get_pos()
        self.toolbox.draw(self.screen, self.drawing.mode, self.sim_state, mouse)
        self.ctx_menu.draw(self.screen, mouse)
