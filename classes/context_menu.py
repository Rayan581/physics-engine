import pygame
import math
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
        
        self._text_text = ""
        self._text_edit = False
        
        self._r_text = ""
        self._g_text = ""
        self._b_text = ""
        self._r_edit = False
        self._g_edit = False
        self._b_edit = False
        
        self._presets = [(255, 255, 255)] * 10
        self._load_presets()
        
        self._speed_text = ""
        self._speed_edit = False
        self._torque_text = ""
        self._torque_edit = False
        self._min_text = ""
        self._min_edit = False
        self._max_text = ""
        self._max_edit = False

    def init_fonts(self):
        self._font_t = pygame.font.SysFont("segoeui", 13, bold=True)
        self._font   = pygame.font.SysFont("segoeui", 12)

    def _load_presets(self):
        import json, os
        if os.path.exists('colors.json'):
            try:
                with open('colors.json', 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) == 10:
                        self._presets = [tuple(c) for c in data]
            except Exception:
                pass

    def _save_presets(self):
        import json
        try:
            with open('colors.json', 'w') as f:
                json.dump(self._presets, f)
        except Exception:
            pass

    # ── state ───────────────────────────────────────────────────────────────────

    @property
    def is_open(self):
        return self._body is not None
        
    @property
    def is_motor(self):
        return self._body and type(self._body).__name__ == "MotorJoint"

    def open(self, body, screen_x: int, screen_y: int):
        self._body = body
        mx = screen_x + 12
        my = screen_y - 12
        # flip if off-screen
        total_w = TOOLBOX_WIDTH + WIDTH
        if mx + self.W > total_w:
            mx = screen_x - self.W - 12
        my = max(4, min(my, HEIGHT - self.H - 4))
        if type(body).__name__ == "MotorJoint":
            self.H = 208
            self._speed_text = f"{math.degrees(body.motor_speed):.0f}"
            self._torque_text = f"{body.motor_torque:.0f}"
            self._min_text = f"{math.degrees(body.min_angle):.0f}"
            self._max_text = f"{math.degrees(body.max_angle):.0f}"
        else:
            self.H = 310 if type(body).__name__ == "TextBody" else 260
            self._mass_text = f"{body.mass:.1f}"
            self._layer_text = ", ".join(sorted(body.layers))
            self._r_text = f"{body.color[0]}"
            self._g_text = f"{body.color[1]}"
            self._b_text = f"{body.color[2]}"
            if type(body).__name__ == "TextBody":
                self._text_text = body.text
            
        self._rect = pygame.Rect(mx, my, self.W, self.H)
        self._mass_edit = False
        self._layer_edit = False
        self._text_edit = False
        self._r_edit = False
        self._g_edit = False
        self._b_edit = False
        self._speed_edit = False
        self._torque_edit = False

    def close(self):
        self._apply_mass()
        self._apply_layer()
        self._apply_color()
        self._apply_motor()
        self._apply_text()
        self._body = None
        self._rect = None
        self._mass_edit = False
        self._layer_edit = False
        self._text_edit = False
        self._r_edit = False
        self._g_edit = False
        self._b_edit = False
        self._speed_edit = False
        self._torque_edit = False
        self._min_edit = False
        self._max_edit = False

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
        if not self._body or self.is_motor or not self._layer_edit: return
        layers = {l.strip() for l in self._layer_text.split(',') if l.strip()}
        if not layers: layers = {"Default"}
        self._body.layers = layers
        self._layer_text = ", ".join(sorted(layers))
        self._layer_edit = False
        
    def _apply_color(self):
        if not self._body or self.is_motor: return
        if not (self._r_edit or self._g_edit or self._b_edit): return
        
        r, g, b = self._body.color
        if self._r_edit:
            try: r = max(0, min(255, int(self._r_text)))
            except ValueError: pass
        if self._g_edit:
            try: g = max(0, min(255, int(self._g_text)))
            except ValueError: pass
        if self._b_edit:
            try: b = max(0, min(255, int(self._b_text)))
            except ValueError: pass
            
        self._body.color = (r, g, b)
        self._r_text = f"{r}"
        self._g_text = f"{g}"
        self._b_text = f"{b}"
        self._r_edit = False
        self._g_edit = False
        self._b_edit = False

    def _apply_text(self):
        if not self._body or not self._text_edit or type(self._body).__name__ != "TextBody": return
        self._body.update_text(self._text_text)
        self._text_edit = False
        
    def _apply_motor(self):
        if not self._body or not self.is_motor: return
        import math
        if self._speed_edit:
            try:
                val = float(self._speed_text)
                self._body.motor_speed = math.radians(val)
            except ValueError:
                pass
            self._speed_text = f"{math.degrees(self._body.motor_speed):.0f}"
            self._speed_edit = False
        if self._torque_edit:
            try:
                val = float(self._torque_text)
                self._body.motor_torque = max(0.0, val)
            except ValueError:
                pass
            self._torque_text = f"{self._body.motor_torque:.0f}"
            self._torque_edit = False
        if self._min_edit:
            try:
                val = float(self._min_text)
                self._body.min_angle = math.radians(val)
            except ValueError:
                pass
            self._min_text = f"{math.degrees(self._body.min_angle):.0f}"
            self._min_edit = False
        if self._max_edit:
            try:
                val = float(self._max_text)
                self._body.max_angle = math.radians(val)
            except ValueError:
                pass
            self._max_text = f"{math.degrees(self._body.max_angle):.0f}"
            self._max_edit = False

    def handle_key(self, ev) -> bool:
        if self._mass_edit or self._speed_edit or self._torque_edit or self._min_edit or self._max_edit or self._r_edit or self._g_edit or self._b_edit:
            target_text = self._mass_text if self._mass_edit else \
                          self._speed_text if self._speed_edit else \
                          self._torque_text if self._torque_edit else \
                          self._min_text if self._min_edit else \
                          self._max_text if self._max_edit else \
                          self._r_text if self._r_edit else \
                          self._g_text if self._g_edit else \
                          self._b_text
            
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                if self._mass_edit: self._apply_mass()
                elif self._r_edit or self._g_edit or self._b_edit: self._apply_color()
                else: self._apply_motor()
            elif ev.key == pygame.K_BACKSPACE:
                target_text = target_text[:-1]
            elif ev.unicode in "0123456789.-":
                if ev.unicode == '.' and '.' in target_text: pass
                elif ev.unicode == '-' and '-' in target_text: pass
                else: target_text += ev.unicode
                
            if self._mass_edit: self._mass_text = target_text
            elif self._speed_edit: self._speed_text = target_text
            elif self._torque_edit: self._torque_text = target_text
            elif self._min_edit: self._min_text = target_text
            elif self._max_edit: self._max_text = target_text
            elif self._r_edit: self._r_text = target_text
            elif self._g_edit: self._g_text = target_text
            elif self._b_edit: self._b_text = target_text
            return True
        elif self._layer_edit:
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                self._apply_layer()
            elif ev.key == pygame.K_BACKSPACE:
                self._layer_text = self._layer_text[:-1]
            elif ev.unicode and ev.unicode.isprintable():
                self._layer_text += ev.unicode
            return True
        elif self._text_edit:
            if ev.key == pygame.K_ESCAPE:
                self._apply_text()
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._text_text += '\n'
            elif ev.key == pygame.K_BACKSPACE:
                self._text_text = self._text_text[:-1]
            elif ev.unicode and ev.unicode.isprintable():
                self._text_text += ev.unicode
            return True
        return False

    def handle_click(self, pos, button=1):
        if not self._body or not self._rect:
            return
            
        if button == 3:
            if not self.is_motor:
                for i, r in enumerate(self._preset_boxes()):
                    if r.collidepoint(pos):
                        self._apply_color()
                        self._presets[i] = self._body.color
                        self._save_presets()
            return

        if self.is_motor:
            if self._speed_box().collidepoint(pos):
                self._apply_motor()
                self._speed_edit = True
                return
            if self._torque_box().collidepoint(pos):
                self._apply_motor()
                self._torque_edit = True
                return
            if self._min_box().collidepoint(pos):
                self._apply_motor()
                self._min_edit = True
                return
            if self._max_box().collidepoint(pos):
                self._apply_motor()
                self._max_edit = True
                return
            self._apply_motor()
            
            if self._fixed_btn().collidepoint(pos):
                self._body.motor_enabled = not self._body.motor_enabled
            if self._limits_btn().collidepoint(pos):
                self._body.limits_enabled = not self._body.limits_enabled
            return
        
        if self._mass_box().collidepoint(pos):
            self._apply_layer()
            self._apply_color()
            self._mass_edit = True
            return
            
        if self._layer_box().collidepoint(pos):
            self._apply_mass()
            self._apply_color()
            self._layer_edit = True
            return
            
        if self._r_box().collidepoint(pos):
            self._apply_mass()
            self._apply_layer()
            self._apply_color()
            self._r_edit = True
            return
        if self._g_box().collidepoint(pos):
            self._apply_mass()
            self._apply_layer()
            self._apply_color()
            self._g_edit = True
            return
        if self._b_box().collidepoint(pos):
            self._apply_mass()
            self._apply_layer()
            self._apply_color()
            self._b_edit = True
            return

        if self._text_box() and self._text_box().collidepoint(pos):
            self._apply_mass()
            self._apply_layer()
            self._apply_color()
            self._text_edit = True
            return

        # If clicked elsewhere in menu, apply edit
        self._apply_mass()
        self._apply_layer()
        self._apply_color()
        self._apply_text()

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
            
        for i, r in enumerate(self._preset_boxes()):
            if r.collidepoint(pos):
                self._body.color = self._presets[i]
                self._r_text = f"{self._presets[i][0]}"
                self._g_text = f"{self._presets[i][1]}"
                self._b_text = f"{self._presets[i][2]}"

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
        
    def _r_box(self):
        return pygame.Rect(self._rect.x + 48, self._rect.y + 174, 30, 18)
        
    def _g_box(self):
        return pygame.Rect(self._rect.x + 83, self._rect.y + 174, 30, 18)
        
    def _b_box(self):
        return pygame.Rect(self._rect.x + 118, self._rect.y + 174, 30, 18)
        
    def _preset_boxes(self):
        boxes = []
        for i in range(10):
            row = i // 5
            col = i % 5
            boxes.append(pygame.Rect(self._rect.x + self.PAD + col * 30, self._rect.y + 208 + row * 22, 22, 18))
        return boxes

    def _speed_box(self):
        return pygame.Rect(self._rect.x + 52, self._rect.y + 72, 48, 18)

    def _torque_box(self):
        return pygame.Rect(self._rect.x + 52, self._rect.y + 106, 48, 18)

    def _limits_btn(self):
        return pygame.Rect(self._rect.x + self.PAD, self._rect.y + 140, 18, 18)

    def _min_box(self):
        return pygame.Rect(self._rect.x + 36, self._rect.y + 174, 44, 18)

    def _max_box(self):
        return pygame.Rect(self._rect.x + 110, self._rect.y + 174, 44, 18)

    def _text_box(self):
        if type(self._body).__name__ == "TextBody":
            return pygame.Rect(self._rect.x + self.PAD, self._rect.y + 252, self.W - self.PAD*2, 44)
        return None

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

        if self.is_motor:
            self._draw_motor(surface, mouse_pos)
        else:
            self._draw_body(surface, mouse_pos)

    def _draw_body(self, surface: pygame.Surface, mouse_pos):
        r = self._rect
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

        # Color Label
        surface.blit(self._font.render("Color:", True, CM_TEXT_COLOR),
                     (r.x + self.PAD, r.y + 175))

        # R Box
        rbox = self._r_box()
        pygame.draw.rect(surface, Colors.WHITE if self._r_edit else CM_BTN_BG, rbox, border_radius=2)
        pygame.draw.rect(surface, CM_ACCENT if self._r_edit else CM_BORDER, rbox, 1, border_radius=2)
        disp_text = self._r_text if self._r_edit else f"{self._body.color[0]}"
        if self._r_edit and pygame.time.get_ticks() % 1000 < 500: disp_text += "|"
        ts = self._font.render(disp_text, True, Colors.BLACK if self._r_edit else CM_TEXT_COLOR)
        surface.blit(ts, (rbox.x + 3, rbox.y + 1), area=pygame.Rect(0, 0, rbox.width-6, rbox.height))

        # G Box
        gbox = self._g_box()
        pygame.draw.rect(surface, Colors.WHITE if self._g_edit else CM_BTN_BG, gbox, border_radius=2)
        pygame.draw.rect(surface, CM_ACCENT if self._g_edit else CM_BORDER, gbox, 1, border_radius=2)
        disp_text = self._g_text if self._g_edit else f"{self._body.color[1]}"
        if self._g_edit and pygame.time.get_ticks() % 1000 < 500: disp_text += "|"
        ts = self._font.render(disp_text, True, Colors.BLACK if self._g_edit else CM_TEXT_COLOR)
        surface.blit(ts, (gbox.x + 3, gbox.y + 1), area=pygame.Rect(0, 0, gbox.width-6, gbox.height))

        # B Box
        bbox = self._b_box()
        pygame.draw.rect(surface, Colors.WHITE if self._b_edit else CM_BTN_BG, bbox, border_radius=2)
        pygame.draw.rect(surface, CM_ACCENT if self._b_edit else CM_BORDER, bbox, 1, border_radius=2)
        disp_text = self._b_text if self._b_edit else f"{self._body.color[2]}"
        if self._b_edit and pygame.time.get_ticks() % 1000 < 500: disp_text += "|"
        ts = self._font.render(disp_text, True, Colors.BLACK if self._b_edit else CM_TEXT_COLOR)
        surface.blit(ts, (bbox.x + 3, bbox.y + 1), area=pygame.Rect(0, 0, bbox.width-6, bbox.height))

        # Presets
        y = 208
        boxes = self._preset_boxes()
        for i, r_box in enumerate(boxes):
            c = self._presets[i]
            pygame.draw.rect(surface, c, r_box, border_radius=2)
            pygame.draw.rect(surface, CM_BORDER, r_box, 1, border_radius=2)

        # Text input box
        if type(self._body).__name__ == "TextBody":
            surface.blit(self._font.render("Text:", True, CM_TEXT_COLOR),
                         (r.x + self.PAD, r.y + 236))
            t_box = self._text_box()
            pygame.draw.rect(surface, Colors.WHITE if self._text_edit else CM_BTN_BG, t_box, border_radius=2)
            pygame.draw.rect(surface, CM_ACCENT if self._text_edit else CM_BORDER, t_box, 1, border_radius=2)
            
            disp_text = self._text_text if self._text_edit else self._body.text
            if self._text_edit and pygame.time.get_ticks() % 1000 < 500: disp_text += "|"
            
            # Simple multiline render for textbox
            lines = disp_text.split('\n')
            ty = t_box.y + 2
            for line in lines:
                ts = self._font.render(line, True, Colors.BLACK if self._text_edit else CM_TEXT_COLOR)
                surface.blit(ts, (t_box.x + 3, ty), area=pygame.Rect(0, 0, t_box.width-6, ts.get_height()))
                ty += ts.get_height()

    def _draw_motor(self, surface: pygame.Surface, mouse_pos):
        import math
        r = self._rect
        
        # Motor Enabled Toggle
        btn = self._fixed_btn()
        hov = btn.collidepoint(mouse_pos)
        bg  = CM_BTN_ACTIVE if self._body.motor_enabled else (CM_BTN_HOVER if hov else CM_BTN_BG)
        pygame.draw.rect(surface, bg, btn, border_radius=3)
        pygame.draw.rect(surface, CM_BORDER, btn, 1, border_radius=3)
        if self._body.motor_enabled:
            pygame.draw.lines(surface, CM_ACCENT, False,
                              [(btn.x+3, btn.centery), (btn.x+7, btn.bottom-3),
                               (btn.right-3, btn.y+4)], 2)
        surface.blit(self._font.render("Motor On", True, CM_TEXT_COLOR),
                     (r.x + self.PAD + 24, r.y + 39))

        # Motor Speed
        surface.blit(self._font.render("Speed:", True, CM_TEXT_COLOR),
                     (r.x + self.PAD, r.y + 73))
                     
        sbox = self._speed_box()
        pygame.draw.rect(surface, Colors.WHITE if self._speed_edit else CM_BTN_BG, sbox, border_radius=2)
        pygame.draw.rect(surface, CM_ACCENT if self._speed_edit else CM_BORDER, sbox, 1, border_radius=2)
        
        disp_text = self._speed_text if self._speed_edit else f"{math.degrees(self._body.motor_speed):.0f}"
        if self._speed_edit and pygame.time.get_ticks() % 1000 < 500: disp_text += "|"
        ts = self._font.render(disp_text, True, Colors.BLACK if self._speed_edit else CM_TEXT_COLOR)
        surface.blit(ts, (sbox.x + 3, sbox.y + 1), area=pygame.Rect(0, 0, sbox.width-6, sbox.height))

        # Motor Torque
        surface.blit(self._font.render("Torque:", True, CM_TEXT_COLOR),
                     (r.x + self.PAD, r.y + 107))
                     
        tbox = self._torque_box()
        pygame.draw.rect(surface, Colors.WHITE if self._torque_edit else CM_BTN_BG, tbox, border_radius=2)
        pygame.draw.rect(surface, CM_ACCENT if self._torque_edit else CM_BORDER, tbox, 1, border_radius=2)
        
        disp_text = self._torque_text if self._torque_edit else f"{self._body.motor_torque:.0f}"
        if self._torque_edit and pygame.time.get_ticks() % 1000 < 500: disp_text += "|"
        ts = self._font.render(disp_text, True, Colors.BLACK if self._torque_edit else CM_TEXT_COLOR)
        surface.blit(ts, (tbox.x + 3, tbox.y + 1), area=pygame.Rect(0, 0, tbox.width-6, tbox.height))

        # Limits Enabled Toggle
        lbtn = self._limits_btn()
        hov = lbtn.collidepoint(mouse_pos)
        bg  = CM_BTN_ACTIVE if self._body.limits_enabled else (CM_BTN_HOVER if hov else CM_BTN_BG)
        pygame.draw.rect(surface, bg, lbtn, border_radius=3)
        pygame.draw.rect(surface, CM_BORDER, lbtn, 1, border_radius=3)
        if self._body.limits_enabled:
            pygame.draw.lines(surface, CM_ACCENT, False,
                              [(lbtn.x+3, lbtn.centery), (lbtn.x+7, lbtn.bottom-3),
                               (lbtn.right-3, lbtn.y+4)], 2)
        surface.blit(self._font.render("Use Limits", True, CM_TEXT_COLOR),
                     (r.x + self.PAD + 24, r.y + 141))

        # Min Angle
        surface.blit(self._font.render("Min:", True, CM_TEXT_COLOR),
                     (r.x + self.PAD, r.y + 175))
                     
        minb = self._min_box()
        pygame.draw.rect(surface, Colors.WHITE if self._min_edit else CM_BTN_BG, minb, border_radius=2)
        pygame.draw.rect(surface, CM_ACCENT if self._min_edit else CM_BORDER, minb, 1, border_radius=2)
        
        disp_text = self._min_text if self._min_edit else f"{math.degrees(self._body.min_angle):.0f}"
        if self._min_edit and pygame.time.get_ticks() % 1000 < 500: disp_text += "|"
        ts = self._font.render(disp_text, True, Colors.BLACK if self._min_edit else CM_TEXT_COLOR)
        surface.blit(ts, (minb.x + 3, minb.y + 1), area=pygame.Rect(0, 0, minb.width-6, minb.height))

        # Max Angle
        surface.blit(self._font.render("Max:", True, CM_TEXT_COLOR),
                     (r.x + 84, r.y + 175))
                     
        maxb = self._max_box()
        pygame.draw.rect(surface, Colors.WHITE if self._max_edit else CM_BTN_BG, maxb, border_radius=2)
        pygame.draw.rect(surface, CM_ACCENT if self._max_edit else CM_BORDER, maxb, 1, border_radius=2)
        
        disp_text = self._max_text if self._max_edit else f"{math.degrees(self._body.max_angle):.0f}"
        if self._max_edit and pygame.time.get_ticks() % 1000 < 500: disp_text += "|"
        ts = self._font.render(disp_text, True, Colors.BLACK if self._max_edit else CM_TEXT_COLOR)
        surface.blit(ts, (maxb.x + 3, maxb.y + 1), area=pygame.Rect(0, 0, maxb.width-6, maxb.height))
