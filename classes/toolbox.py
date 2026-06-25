"""
classes/toolbox.py — Left-sidebar toolbox with shape tools and simulation controls.
Warm-dark amber theme.
"""
import math
import pygame
from config import *


# ── Shape-tool icon functions ────────────────────────────────────────────────────

def _icon_rect(surf, cx, cy, active):
    col = TB_ICON_ACTIVE if active else TB_ICON_COLOR
    pygame.draw.rect(surf, col, (cx-13, cy-8, 26, 17), 2, border_radius=3)

def _icon_circle(surf, cx, cy, active):
    col = TB_ICON_ACTIVE if active else TB_ICON_COLOR
    pygame.draw.circle(surf, col, (cx, cy), 12, 2)

def _icon_polygon(surf, cx, cy, active):
    col = TB_ICON_ACTIVE if active else TB_ICON_COLOR
    pts = [(cx + int(12*math.cos(math.radians(-90+i*72))),
            cy + int(12*math.sin(math.radians(-90+i*72)))) for i in range(5)]
    pygame.draw.polygon(surf, col, pts, 2)

def _icon_motor(surf, cx, cy, active):
    col = TB_ICON_ACTIVE if active else TB_ICON_COLOR
    pygame.draw.circle(surf, col, (cx, cy), 10, 2)
    pygame.draw.circle(surf, col, (cx, cy), 3)
    pygame.draw.line(surf, col, (cx, cy-10), (cx, cy+10), 2)
    pygame.draw.line(surf, col, (cx-10, cy), (cx+10, cy), 2)

def _icon_text(surf, cx, cy, active):
    col = TB_ICON_ACTIVE if active else TB_ICON_COLOR
    pygame.draw.line(surf, col, (cx - 9, cy - 10), (cx + 9, cy - 10), 3)
    pygame.draw.line(surf, col, (cx, cy - 10), (cx, cy + 10), 3)


# ── helpers ──────────────────────────────────────────────────────────────────────

def _draw_toggle(surface, rect, checked, hovered):
    """Draw a pill-shaped toggle switch."""
    r = rect
    track_col = TB_ACCENT if checked else TB_TOGGLE_TRACK_OFF
    track_border = TB_ACCENT if checked else TB_BTN_BORDER
    pygame.draw.rect(surface, track_col, r, border_radius=r.height//2)
    pygame.draw.rect(surface, track_border, r, 1, border_radius=r.height//2)
    # Knob
    knob_r = r.height // 2 - 2
    kx = r.right - knob_r - 3 if checked else r.x + knob_r + 3
    ky = r.centery
    knob_col = TB_TOGGLE_KNOB_ON if checked else TB_TOGGLE_KNOB_OFF
    pygame.draw.circle(surface, knob_col, (kx, ky), knob_r)


# ── ToolButton ───────────────────────────────────────────────────────────────────

class ToolButton:
    _LABEL = None
    _KEY   = None

    def __init__(self, name, label, icon_fn, key_hint, rect):
        self.tool_name = name
        self.label     = label
        self._icon_fn  = icon_fn
        self.key_hint  = key_hint
        self.rect      = rect

    @classmethod
    def init_fonts(cls):
        cls._LABEL = pygame.font.SysFont("segoeui", 11)
        cls._KEY   = pygame.font.SysFont("segoeui", 9)

    def draw(self, surface, active, hovered):
        r = self.rect
        bg = TB_BTN_ACTIVE_BG if active else (TB_BTN_HOVER_BG if hovered else TB_BTN_BG)
        pygame.draw.rect(surface, bg, r, border_radius=8)
        if active:
            pygame.draw.rect(surface, TB_ACCENT, r, 2, border_radius=8)
        elif hovered:
            pygame.draw.rect(surface, TB_BTN_BORDER, r, 1, border_radius=8)

        icon_y = r.y + r.height // 2 - 8
        self._icon_fn(surface, r.centerx, icon_y, active)

        if self._LABEL:
            col = TB_ICON_ACTIVE if active else TB_LABEL_COLOR
            lbl = self._LABEL.render(self.label, True, col)
            surface.blit(lbl, (r.centerx - lbl.get_width()//2, r.bottom - lbl.get_height() - 3))

        if self._KEY:
            col = TB_ACCENT if active else TB_KEY_COLOR
            ks  = self._KEY.render(self.key_hint, True, col)
            surface.blit(ks, (r.right - ks.get_width() - 3, r.y + 3))


# ── SimButton ────────────────────────────────────────────────────────────────────

class SimButton:
    """Pill-shaped play / pause / stop button."""
    _FONT = None

    def __init__(self, name, rect):
        self.name = name
        self.rect = rect

    @classmethod
    def init_fonts(cls):
        cls._FONT = pygame.font.SysFont("segoeui", 10, bold=True)

    def draw(self, surface, sim_state, hovered):
        r = self.rect
        is_active = (sim_state == self.name)
        if self.name == 'playing':
            accent = TB_PLAY_ACCENT
            accent_active = TB_PLAY_ACCENT_ACTIVE
        elif self.name == 'paused':
            accent = TB_PAUSE_ACCENT
            accent_active = TB_PAUSE_ACCENT_ACTIVE
        else:
            accent = TB_STOP_ACCENT
            accent_active = TB_STOP_ACCENT_ACTIVE

        col = accent_active if is_active else (accent if hovered else TB_BTN_BG)
        border = accent if (is_active or hovered) else TB_BTN_BORDER
        pygame.draw.rect(surface, col, r, border_radius=r.height//2)
        pygame.draw.rect(surface, border, r, 1, border_radius=r.height//2)

        cx, cy = r.centerx, r.centery
        ic = Colors.WHITE if is_active else TB_ICON_INACTIVE
        if self.name == 'playing':
            pts = [(cx-4, cy-5), (cx-4, cy+5), (cx+5, cy)]
            pygame.draw.polygon(surface, ic, pts)
        elif self.name == 'paused':
            pygame.draw.rect(surface, ic, (cx-5, cy-5, 4, 10))
            pygame.draw.rect(surface, ic, (cx+1, cy-5, 4, 10))
        elif self.name == 'stopped':
            pygame.draw.rect(surface, ic, (cx-4, cy-4, 9, 9))


# ── TextButton ───────────────────────────────────────────────────────────────────

class TextButton:
    def __init__(self, name, label, rect):
        self.name  = name
        self.label = label
        self.rect  = rect

    def draw(self, surface, hovered, font):
        r = self.rect
        bg     = TB_BTN_HOVER_BG if hovered else TB_BTN_BG
        border = TB_BTN_BORDER   if hovered else TB_BTN_BORDER_IDLE
        pygame.draw.rect(surface, bg, r, border_radius=6)
        pygame.draw.rect(surface, border, r, 1, border_radius=6)
        if font:
            col = TB_LABEL_COLOR if not hovered else TB_ACCENT_BRIGHT
            lbl = font.render(self.label, True, col)
            surface.blit(lbl, (r.centerx - lbl.get_width()//2,
                               r.centery - lbl.get_height()//2 + 1))


# ── Toggle Checkbox ───────────────────────────────────────────────────────────────

class Checkbox:
    def __init__(self, name, label, rect, checked=True):
        self.name    = name
        self.label   = label
        self.rect    = rect
        self.checked = checked

    def draw(self, surface, hovered, font):
        r = self.rect
        toggle_w, toggle_h = 30, 16
        toggle_rect = pygame.Rect(r.right - toggle_w, r.y + (r.height - toggle_h)//2,
                                  toggle_w, toggle_h)
        _draw_toggle(surface, toggle_rect, self.checked, hovered)
        if font:
            col = TB_LABEL_COLOR if not self.checked else TB_TITLE_COLOR
            lbl = font.render(self.label, True, col)
            surface.blit(lbl, (r.x, r.centery - lbl.get_height()//2 + 1))


# ── Toolbox ───────────────────────────────────────────────────────────────────────

class Toolbox:
    _HINTS = {
        'rect':    ["Click corner A,", "then corner B"],
        'circle':  ["Click center,",   "then radius pt"],
        'polygon': ["Click vertices,", "close near start"],
        'motor':   ["Click object", "to attach motor"],
        'text':    ["Click anywhere", "to spawn text"],
    }

    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self._tool_btns:   list[ToolButton] = []
        self._sim_btns:    list[SimButton]  = []
        self._action_btns: list[TextButton] = []
        self._checkboxes:  list[Checkbox]   = []
        self._title_font  = None
        self._hint_font   = None
        self._action_font = None
        self._build()

    def _build(self):
        pad  = 8
        side = self.rect.width - pad * 2
        tools = [
            ("rect",    "Rect",   _icon_rect,    "R"),
            ("circle",  "Circle", _icon_circle,  "C"),
            ("polygon", "Poly",   _icon_polygon, "P"),
            ("motor",   "Motor",  _icon_motor,   "M"),
            ("text",    "Text",   _icon_text,    "T"),
        ]
        # Tool buttons — 2-column grid to save vertical space
        col_w = (self.rect.width - pad * 2 - 4) // 2
        col_h = col_w
        y = self.rect.y + 44   # below amber header
        
        for i, (name, label, fn, key) in enumerate(tools):
            row = i // 2
            col = i % 2
            rx = self.rect.x + pad + col * (col_w + 4)
            ry = y + row * (col_h + 4)
            r = pygame.Rect(rx, ry, col_w, col_h)
            self._tool_btns.append(ToolButton(name, label, fn, key, r))
            
        y += ((len(tools) + 1) // 2) * (col_h + 4)

        # Sim buttons — pill row
        bw = (self.rect.width - pad * 2 - 4) // 3
        bh = 24
        y += 16
        for i, name in enumerate(['playing', 'paused', 'stopped']):
            rx = self.rect.x + pad + i * (bw + 2)
            self._sim_btns.append(SimButton(name, pygame.Rect(rx, y, bw, bh)))

        # Action buttons — 2-column grid for each menu type
        y += bh + 14
        bw2 = (self.rect.width - pad * 2 - 2) // 2
        bh2 = 24
        
        # Scene menu
        self._action_btns.append(TextButton('save',   'Save Scene',   pygame.Rect(self.rect.x + pad,          y, bw2, bh2)))
        self._action_btns.append(TextButton('load',   'Load Scene',   pygame.Rect(self.rect.x + pad + bw2 + 2, y, bw2, bh2)))

        y += bh2 + 4
        # Object menu
        self._action_btns.append(TextButton('export', 'Save Obj',     pygame.Rect(self.rect.x + pad,          y, bw2, bh2)))
        self._action_btns.append(TextButton('import', 'Load Obj',     pygame.Rect(self.rect.x + pad + bw2 + 2, y, bw2, bh2)))

        y += bh2 + 14
        # AI menu
        self._action_btns.append(TextButton('load_ai', 'Load AI',     pygame.Rect(self.rect.x + pad,          y, bw2, bh2)))
        self._action_btns.append(TextButton('run_ai',  'Run AI',      pygame.Rect(self.rect.x + pad + bw2 + 2, y, bw2, bh2)))

        y += bh2 + 14
        fw = self.rect.width - pad * 2
        self._checkboxes.append(Checkbox('show_com', 'Show CoM',
                                          pygame.Rect(self.rect.x + pad, y, fw, 20), True))
        y += 24
        self._checkboxes.append(Checkbox('viz_all', 'Viz All Agents',
                                          pygame.Rect(self.rect.x + pad, y, fw, 20), False))

    def init_fonts(self):
        ToolButton.init_fonts()
        SimButton.init_fonts()
        self._title_font  = pygame.font.SysFont("segoeui", 11, bold=True)
        self._hint_font   = pygame.font.SysFont("segoeui", 10)
        self._action_font = pygame.font.SysFont("segoeui", 11)

    # ── queries ──────────────────────────────────────────────────────────────────

    def contains(self, pos) -> bool:
        return self.rect.collidepoint(pos)

    def get_tool_at(self, pos) -> str | None:
        for b in self._tool_btns:
            if b.rect.collidepoint(pos):
                return b.tool_name
        return None

    def get_sim_action_at(self, pos) -> str | None:
        for b in self._sim_btns:
            if b.rect.collidepoint(pos):
                return b.name
        return None

    def get_action_at(self, pos) -> str | None:
        for b in self._action_btns:
            if b.rect.collidepoint(pos):
                return b.name
        return None

    def get_checkbox_at(self, pos) -> str | None:
        for cb in self._checkboxes:
            if cb.rect.collidepoint(pos):
                return cb.name
        return None

    # ── draw ─────────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface,
             active_tool: str | None, sim_state: str, mouse_pos):
        r = self.rect

        # Background + right border
        pygame.draw.rect(surface, TB_BG, r)
        pygame.draw.line(surface, TB_BORDER, (r.right - 1, r.top), (r.right - 1, r.bottom))

        # Amber header strip
        hdr = pygame.Rect(r.x, r.y, r.width, 34)
        pygame.draw.rect(surface, TB_HEADER_BG, hdr)
        pygame.draw.line(surface, TB_BORDER, (r.x, hdr.bottom), (r.right, hdr.bottom))
        if self._title_font:
            t = self._title_font.render("TOOLS", True, TB_TITLE_COLOR)
            surface.blit(t, (r.centerx - t.get_width()//2, hdr.centery - t.get_height()//2))

        # Tool buttons
        for b in self._tool_btns:
            b.draw(surface, b.tool_name == active_tool, b.rect.collidepoint(mouse_pos))

        # Separator
        def _sep(y):
            pygame.draw.line(surface, TB_SEP_COLOR, (r.x + 8, y), (r.right - 8, y))

        _sep(self._sim_btns[0].rect.y - 9)
        for b in self._sim_btns:
            b.draw(surface, sim_state, b.rect.collidepoint(mouse_pos))

        _sep(self._action_btns[0].rect.y - 9)
        for b in self._action_btns:
            b.draw(surface, b.rect.collidepoint(mouse_pos), self._action_font)

        _sep(self._checkboxes[0].rect.y - 6)
        for cb in self._checkboxes:
            cb.draw(surface, cb.rect.collidepoint(mouse_pos), self._action_font)

        # Hint
        if active_tool and sim_state == 'stopped' and self._hint_font:
            lines = self._HINTS.get(active_tool, [])
            lh = self._hint_font.get_height() + 2
            y  = r.bottom - len(lines) * lh - 10
            for line in lines:
                s = self._hint_font.render(line, True, TB_HINT_COLOR)
                surface.blit(s, (r.centerx - s.get_width()//2, y))
                y += lh
