import pygame
from config import *


class ContextMenu:
    """Floating panel shown when clicking a body in stopped/paused state."""

    W  = 165
    H  = 174
    PAD = 10

    def __init__(self):
        self._body   = None
        self._rect   = None
        self._font_t = None   # title font
        self._font   = None   # body font
        self._mass_text = ""
        self._mass_edit = False
        self._layer_text = ""
        self._layer_edit = False

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
        self._mass_text = f"{body.mass:.1f}"
        self._mass_edit = False
        self._layer_text = ", ".join(sorted(body.layers))
        self._layer_edit = False

    def close(self):
        self._apply_mass()
        self._apply_layer()
        self._body = None
        self._rect = None
        self._mass_edit = False
        self._layer_edit = False

    def contains(self, pos) -> bool:
        return bool(self._rect and self._rect.collidepoint(pos))

    # ── interaction ─────────────────────────────────────────────────────────────

    def _apply_mass(self):
        if not self._body or not self._mass_edit: return
        try:
            val = float(self._mass_text)
            self._body.mass = max(0.1, val)
        except ValueError:
            pass
        self._mass_text = f"{self._body.mass:.1f}"
        self._mass_edit = False

    def _apply_layer(self):
        if not self._body or not self._layer_edit: return
        layers = {l.strip() for l in self._layer_text.split(',') if l.strip()}
        if not layers: layers = {"Default"}
        self._body.layers = layers
        self._layer_text = ", ".join(sorted(layers))
        self._layer_edit = False

    def handle_key(self, ev) -> bool:
        if self._mass_edit:
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                self._apply_mass()
            elif ev.key == pygame.K_BACKSPACE:
                self._mass_text = self._mass_text[:-1]
            elif ev.unicode in "0123456789.":
                if ev.unicode == '.' and '.' in self._mass_text:
                    pass
                else:
                    self._mass_text += ev.unicode
            return True
        elif self._layer_edit:
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                self._apply_layer()
            elif ev.key == pygame.K_BACKSPACE:
                self._layer_text = self._layer_text[:-1]
            elif ev.unicode and ev.unicode.isprintable():
                self._layer_text += ev.unicode
            return True
        return False

    def handle_click(self, pos):
        if not self._body or not self._rect:
            return
        
        if self._mass_box().collidepoint(pos):
            self._apply_layer()
            self._mass_edit = True
            return
            
        if self._layer_box().collidepoint(pos):
            self._apply_mass()
            self._layer_edit = True
            return

        # If clicked elsewhere in menu, apply edit
        self._apply_mass()
        self._apply_layer()

        if self._fixed_btn().collidepoint(pos):
            self._body.fixed = not self._body.fixed
        if self._res_minus().collidepoint(pos):
            self._body.restitution = max(0.0, round(self._body.restitution - 0.1, 1))
        if self._res_plus().collidepoint(pos):
            self._body.restitution = min(1.0, round(self._body.restitution + 0.1, 1))
        if self._mass_minus().collidepoint(pos):
            self._body.mass = max(0.1, round(self._body.mass - 0.5, 1))
            self._mass_text = f"{self._body.mass:.1f}"
        if self._mass_plus().collidepoint(pos):
            self._body.mass = round(self._body.mass + 0.5, 1)
            self._mass_text = f"{self._body.mass:.1f}"

    # ── button rects (screen-space) ─────────────────────────────────────────────

    def _fixed_btn(self):
        return pygame.Rect(self._rect.x + self.PAD, self._rect.y + 38, 18, 18)

    def _res_minus(self):
        return pygame.Rect(self._rect.x + 100, self._rect.y + 72, 22, 18)

    def _res_plus(self):
        return pygame.Rect(self._rect.x + 136, self._rect.y + 72, 22, 18)

    def _mass_minus(self):
        return pygame.Rect(self._rect.x + 100, self._rect.y + 106, 22, 18)

    def _mass_plus(self):
        return pygame.Rect(self._rect.x + 136, self._rect.y + 106, 22, 18)

    def _mass_box(self):
        return pygame.Rect(self._rect.x + 48, self._rect.y + 106, 48, 18)

    def _layer_box(self):
        return pygame.Rect(self._rect.x + 48, self._rect.y + 140, 100, 18)

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

        # Mass Label
        surface.blit(self._font.render("Mass:", True, CM_TEXT_COLOR),
                     (r.x + self.PAD, r.y + 107))
        
        # Mass Text Box
        mbox = self._mass_box()
        pygame.draw.rect(surface, Colors.WHITE if self._mass_edit else CM_BTN_BG, mbox, border_radius=2)
        pygame.draw.rect(surface, CM_ACCENT if self._mass_edit else CM_BORDER, mbox, 1, border_radius=2)
        
        disp_text = self._mass_text if self._mass_edit else f"{self._body.mass:.1f}"
        if self._mass_edit and pygame.time.get_ticks() % 1000 < 500:
            disp_text += "|"
            
        ts = self._font.render(disp_text, True, Colors.BLACK if self._mass_edit else CM_TEXT_COLOR)
        # clip text if too long
        surface.blit(ts, (mbox.x + 3, mbox.y + 1), area=pygame.Rect(0, 0, mbox.width-6, mbox.height))

        # Mass +/- Buttons
        for btn_r, label in [(self._mass_minus(), "\u2212"), (self._mass_plus(), "+")]:
            hov = btn_r.collidepoint(mouse_pos)
            pygame.draw.rect(surface, CM_BTN_HOVER if hov else CM_BTN_BG,
                             btn_r, border_radius=3)
            pygame.draw.rect(surface, CM_BORDER, btn_r, 1, border_radius=3)
            ls = self._font.render(label, True, CM_ACCENT)
            surface.blit(ls, ls.get_rect(center=btn_r.center))

        # Layer Label
        surface.blit(self._font.render("Layer:", True, CM_TEXT_COLOR),
                     (r.x + self.PAD, r.y + 141))
        
        # Layer Text Box
        lbox = self._layer_box()
        pygame.draw.rect(surface, Colors.WHITE if self._layer_edit else CM_BTN_BG, lbox, border_radius=2)
        pygame.draw.rect(surface, CM_ACCENT if self._layer_edit else CM_BORDER, lbox, 1, border_radius=2)
        
        disp_text = self._layer_text if self._layer_edit else ", ".join(sorted(self._body.layers))
        if self._layer_edit and pygame.time.get_ticks() % 1000 < 500:
            disp_text += "|"
            
        ts = self._font.render(disp_text, True, Colors.BLACK if self._layer_edit else CM_TEXT_COLOR)
        surface.blit(ts, (lbox.x + 3, lbox.y + 1), area=pygame.Rect(0, 0, lbox.width-6, lbox.height))
