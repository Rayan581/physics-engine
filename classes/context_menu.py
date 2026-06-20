import pygame
from config import *


class ContextMenu:
    """Floating panel shown when clicking a body in stopped/paused state."""

    W  = 165
    H  = 105
    PAD = 10

    def __init__(self):
        self._body   = None
        self._rect   = None
        self._font_t = None   # title font
        self._font   = None   # body font

    def init_fonts(self):
        self._font_t = pygame.font.SysFont("segoeui", 13, bold=True)
        self._font   = pygame.font.SysFont("segoeui", 12)

    # ── state ───────────────────────────────────────────────────────────────────

    @property
    def is_open(self):
        return self._body is not None

    def open(self, body, screen_x: int, screen_y: int):
        self._body = body
        mx = screen_x + 12
        my = screen_y - 12
        # flip if off-screen
        total_w = TOOLBOX_WIDTH + WIDTH
        if mx + self.W > total_w:
            mx = screen_x - self.W - 12
        my = max(4, min(my, HEIGHT - self.H - 4))
        self._rect = pygame.Rect(mx, my, self.W, self.H)

    def close(self):
        self._body = None
        self._rect = None

    def contains(self, pos) -> bool:
        return bool(self._rect and self._rect.collidepoint(pos))

    # ── interaction ─────────────────────────────────────────────────────────────

    def handle_click(self, pos):
        if not self._body or not self._rect:
            return
        if self._fixed_btn().collidepoint(pos):
            self._body.fixed = not self._body.fixed
        if self._res_minus().collidepoint(pos):
            self._body.restitution = max(0.0, round(self._body.restitution - 0.1, 1))
        if self._res_plus().collidepoint(pos):
            self._body.restitution = min(1.0, round(self._body.restitution + 0.1, 1))

    # ── button rects (screen-space) ─────────────────────────────────────────────

    def _fixed_btn(self):
        return pygame.Rect(self._rect.x + self.PAD, self._rect.y + 38, 18, 18)

    def _res_minus(self):
        return pygame.Rect(self._rect.x + 100, self._rect.y + 72, 22, 18)

    def _res_plus(self):
        return pygame.Rect(self._rect.x + 136, self._rect.y + 72, 22, 18)

    # ── draw ────────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, mouse_pos):
        if not self._body or not self._rect:
            return
        r = self._rect
        pygame.draw.rect(surface, CM_BG, r, border_radius=8)
        pygame.draw.rect(surface, CM_BORDER, r, 1, border_radius=8)

        # Title
        name = type(self._body).__name__.replace("Body", "")
        surface.blit(self._font_t.render(name, True, CM_TITLE_COLOR),
                     (r.x + self.PAD, r.y + self.PAD))

        # Separator
        pygame.draw.line(surface, CM_BORDER,
                         (r.x+6, r.y+30), (r.right-6, r.y+30))

        # Fixed toggle
        btn = self._fixed_btn()
        hov = btn.collidepoint(mouse_pos)
        bg  = CM_BTN_ACTIVE if self._body.fixed else (CM_BTN_HOVER if hov else CM_BTN_BG)
        pygame.draw.rect(surface, bg, btn, border_radius=3)
        pygame.draw.rect(surface, CM_BORDER, btn, 1, border_radius=3)
        if self._body.fixed:
            pygame.draw.lines(surface, CM_ACCENT, False,
                              [(btn.x+3, btn.centery), (btn.x+7, btn.bottom-3),
                               (btn.right-3, btn.y+4)], 2)
        surface.blit(self._font.render("Fixed", True, CM_TEXT_COLOR),
                     (r.x + self.PAD + 24, r.y + 39))

        # Restitution
        surface.blit(self._font.render(
            f"Bounce: {self._body.restitution:.1f}", True, CM_TEXT_COLOR),
            (r.x + self.PAD, r.y + 73))
        for btn_r, label in [(self._res_minus(), "\u2212"), (self._res_plus(), "+")]:
            hov = btn_r.collidepoint(mouse_pos)
            pygame.draw.rect(surface, CM_BTN_HOVER if hov else CM_BTN_BG,
                             btn_r, border_radius=3)
            pygame.draw.rect(surface, CM_BORDER, btn_r, 1, border_radius=3)
            ls = self._font.render(label, True, CM_ACCENT)
            surface.blit(ls, ls.get_rect(center=btn_r.center))
