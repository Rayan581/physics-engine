import pygame
import math
from config import Colors


# How many pixels from the first polygon point counts as "close enough" to seal
POLYGON_CLOSE_RADIUS = 20


class DrawingTool:
    """
    Manages the interactive shape-drawing state machine.

    Modes
    -----
    None      – no tool active (view/select mode)
    'rect'    – press R  – click corner A, then corner B
    'circle'  – press C  – click centre, then a point on circumference
    'polygon' – press P  – click vertices; click near first point to close
    """

    # Colour palette
    GHOST_COLOR   = (120, 200, 255, 160)   # semi-transparent preview fill
    OUTLINE_COLOR = (120, 200, 255)         # preview outline / guide lines
    POINT_COLOR   = (255, 220, 80)          # placed-vertex dots
    CLOSE_RING_COLOR = (80, 255, 140)       # ring shown near first poly point

    def __init__(self):
        self.mode: str | None = None        # current tool
        self._points: list[tuple[int, int]] = []  # clicks collected so far

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def set_mode(self, mode: str | None):
        """Switch tool and reset any in-progress drawing."""
        self.mode = mode
        self._points = []

    def cancel(self):
        """Escape / deselect: cancel current stroke without placing shape."""
        self._points = []
        self.mode = None

    def handle_click(self, pos: tuple[int, int], add_body_callback):
        """
        Process a left-click at *pos*.
        Calls add_body_callback(body) when a shape is fully defined.
        Returns True if a shape was completed.
        """
        if self.mode == 'rect':
            return self._handle_rect(pos, add_body_callback)
        elif self.mode == 'circle':
            return self._handle_circle(pos, add_body_callback)
        elif self.mode == 'polygon':
            return self._handle_polygon(pos, add_body_callback)
        return False

    def draw_preview(self, surface: pygame.Surface, mouse_pos: tuple[int, int]):
        """Render live ghost preview on *surface* using the current mouse position."""
        if self.mode == 'rect':
            self._draw_rect_preview(surface, mouse_pos)
        elif self.mode == 'circle':
            self._draw_circle_preview(surface, mouse_pos)
        elif self.mode == 'polygon':
            self._draw_polygon_preview(surface, mouse_pos)

    # ------------------------------------------------------------------
    # Rectangle
    # ------------------------------------------------------------------

    def _handle_rect(self, pos, cb):
        self._points.append(pos)
        if len(self._points) == 2:
            a, b = self._points
            x, y = min(a[0], b[0]), min(a[1], b[1])
            w, h = abs(b[0]-a[0]), abs(b[1]-a[1])
            if w > 1 and h > 1:
                from classes.body import RectBody
                cb(RectBody(x + w/2, y + h/2, w, h))  # centre-based
            self._points = []
            return True
        return False

    def _draw_rect_preview(self, surface, mouse):
        if not self._points:
            return
        a = self._points[0]
        x, y = min(a[0], mouse[0]), min(a[1], mouse[1])
        w, h = abs(mouse[0] - a[0]), abs(mouse[1] - a[1])
        if w < 1 or h < 1:
            return
        ghost = pygame.Surface((w, h), pygame.SRCALPHA)
        ghost.fill((*self.GHOST_COLOR[:3], 60))
        surface.blit(ghost, (x, y))
        pygame.draw.rect(surface, self.OUTLINE_COLOR, (x, y, w, h), 2)

    # ------------------------------------------------------------------
    # Circle
    # ------------------------------------------------------------------

    def _handle_circle(self, pos, cb):
        self._points.append(pos)
        if len(self._points) == 2:
            cx, cy = self._points[0]
            rx, ry = self._points[1]
            radius = int(math.hypot(rx - cx, ry - cy))
            if radius > 1:
                from classes.body import CircleBody
                cb(CircleBody(cx, cy, radius))
            self._points = []
            return True
        return False

    def _draw_circle_preview(self, surface, mouse):
        if not self._points:
            return
        centre = self._points[0]
        radius = int(math.hypot(mouse[0] - centre[0], mouse[1] - centre[1]))
        if radius < 1:
            return
        # ghost fill via a temporary surface to support alpha
        diam = radius * 2
        ghost = pygame.Surface((diam, diam), pygame.SRCALPHA)
        pygame.draw.circle(ghost, (*self.GHOST_COLOR[:3], 60),
                           (radius, radius), radius)
        surface.blit(ghost, (centre[0] - radius, centre[1] - radius))
        pygame.draw.circle(surface, self.OUTLINE_COLOR, centre, radius, 2)
        # radius guide line
        pygame.draw.line(surface, self.OUTLINE_COLOR, centre, mouse, 1)

    # ------------------------------------------------------------------
    # Polygon
    # ------------------------------------------------------------------

    def _near_first(self, pos) -> bool:
        """True if *pos* is within POLYGON_CLOSE_RADIUS of the first vertex."""
        if not self._points:
            return False
        dx = pos[0] - self._points[0][0]
        dy = pos[1] - self._points[0][1]
        return math.hypot(dx, dy) <= POLYGON_CLOSE_RADIUS

    def _handle_polygon(self, pos, cb):
        # Close the polygon when clicking near the first point (need ≥ 3 pts)
        if len(self._points) >= 3 and self._near_first(pos):
            from classes.body import PolygonBody
            cb(PolygonBody(list(self._points)))
            self._points = []
            return True
        self._points.append(pos)
        return False

    def _draw_polygon_preview(self, surface, mouse):
        all_pts = self._points + [mouse]

        # Draw edges so far
        if len(all_pts) >= 2:
            pygame.draw.lines(surface, self.OUTLINE_COLOR, False, all_pts, 2)

        # Ghost filled polygon (at least 3 real points + mouse)
        if len(all_pts) >= 3:
            ghost = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(ghost, (*self.GHOST_COLOR[:3], 40), all_pts)
            surface.blit(ghost, (0, 0))

        # Closing edge back to first point
        if len(self._points) >= 2:
            pygame.draw.line(surface, (*self.OUTLINE_COLOR, 100),
                             mouse, self._points[0], 1)

        # Highlight first point with a "close ring" so the user knows where
        # to click to seal the polygon
        if self._points:
            near = self._near_first(mouse)
            ring_col = (80, 255, 140) if near else (200, 200, 200)
            pygame.draw.circle(surface, ring_col, self._points[0],
                               POLYGON_CLOSE_RADIUS, 2)
