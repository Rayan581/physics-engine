import pygame
from config import *
from classes.body import RectBody, CircleBody, PolygonBody
from classes.drawing import DrawingTool
from classes.toolbox import Toolbox


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)

        # Window is wider than the canvas to accommodate the toolbox
        self.screen = pygame.display.set_mode((TOOLBOX_WIDTH + WIDTH, HEIGHT))
        self.clock  = pygame.time.Clock()
        self.running = True

        self.bodies: list = []
        self.drawing = DrawingTool()

        # Sub-surface for the drawable canvas (right of toolbox)
        # All body and preview drawing goes here so coordinates stay
        # canvas-relative — no manual offset arithmetic needed.
        self.canvas: pygame.Surface = self.screen.subsurface(
            pygame.Rect(TOOLBOX_WIDTH, 0, WIDTH, HEIGHT))

        self.toolbox = Toolbox(0, 0, TOOLBOX_WIDTH, HEIGHT)
        self.toolbox.init_fonts()

    # ── Main loop ──────────────────────────────────────────────────────────────

    def run(self):
        while self.running:
            self.handle_events()
            self.canvas.fill(Colors.BLACK)
            self.update()
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _canvas_mouse(self) -> tuple[int, int]:
        """Mouse position relative to the canvas origin."""
        mx, my = pygame.mouse.get_pos()
        return (mx - TOOLBOX_WIDTH, my)

    # ── Events ─────────────────────────────────────────────────────────────────

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                self._handle_key(event.key)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self._handle_click(event.pos)

    def _handle_click(self, pos: tuple[int, int]):
        if self.toolbox.contains(pos):
            # Toolbox click — toggle tool selection
            tool = self.toolbox.get_tool_at(pos)
            if tool:
                new = None if self.drawing.mode == tool else tool
                self.drawing.set_mode(new)
        else:
            # Canvas click — pass canvas-relative coords to drawing tool
            canvas_pos = (pos[0] - TOOLBOX_WIDTH, pos[1])
            self.drawing.handle_click(canvas_pos, self._add_body)

    def _handle_key(self, key: int):
        if key == pygame.K_ESCAPE:
            if self.drawing.mode:
                self.drawing.cancel()
            else:
                self.running = False

        elif key == pygame.K_r:
            new = None if self.drawing.mode == 'rect' else 'rect'
            self.drawing.set_mode(new)

        elif key == pygame.K_c:
            new = None if self.drawing.mode == 'circle' else 'circle'
            self.drawing.set_mode(new)

        elif key == pygame.K_p:
            new = None if self.drawing.mode == 'polygon' else 'polygon'
            self.drawing.set_mode(new)

    def _add_body(self, body):
        self.bodies.append(body)

    # ── Update / Draw ─────────────────────────────────────────────────────────

    def update(self):
        pass

    def draw(self):
        # Bodies and ghost preview go to the canvas sub-surface
        for body in self.bodies:
            body.draw(self.canvas)

        self.drawing.draw_preview(self.canvas, self._canvas_mouse())

        # Toolbox drawn on the full screen (left strip)
        self.toolbox.draw(self.screen, self.drawing.mode, pygame.mouse.get_pos())
