"""
classes/toolbox.py — Left-sidebar toolbox with shape tools and simulation controls.
"""
import math
import pygame
from config import *


# ── Shape-tool icon functions ────────────────────────────────────────────────────

def _icon_rect(surf, cx, cy, active):
    col = TB_ICON_ACTIVE if active else TB_ICON_COLOR
    pygame.draw.rect(surf, col, (cx-12, cy-8, 24, 17), 2, border_radius=2)

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
    pygame.draw.line(surf, col, (cx - 8, cy - 10), (cx + 8, cy - 10), 3)
    pygame.draw.line(surf, col, (cx, cy - 10), (cx, cy + 10), 3)

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
        cls._KEY   = pygame.font.SysFont("segoeui", 10)

    def draw(self, surface, active, hovered):
        r = self.rect
        bg = TB_BTN_ACTIVE_BG if active else (TB_BTN_HOVER_BG if hovered else TB_BTN_BG)
        pygame.draw.rect(surface, bg, r, border_radius=7)
        if active:
            pygame.draw.rect(surface, TB_ACCENT, r, 2, border_radius=7)
        elif hovered:
            pygame.draw.rect(surface, TB_BTN_BORDER, r, 1, border_radius=7)
        self._icon_fn(surface, r.centerx, r.y + r.height//2 - 7, active)
        if self._LABEL:
            col  = TB_ICON_ACTIVE if active else TB_LABEL_COLOR
            lbl  = self._LABEL.render(self.label, True, col)
            surface.blit(lbl, (r.centerx - lbl.get_width()//2, r.bottom - lbl.get_height() - 4))
        if self._KEY:
            col = TB_ACCENT if active else TB_KEY_COLOR
            ks  = self._KEY.render(self.key_hint, True, col)
            surface.blit(ks, (r.right - ks.get_width() - 4, r.y + 4))


# ── SimButton ────────────────────────────────────────────────────────────────────

class SimButton:
    """Small play / pause / stop button."""
    _FONT = None

    def __init__(self, name, rect):
        self.name = name
        self.rect = rect

    @classmethod
    def init_fonts(cls):
        cls._FONT = pygame.font.SysFont("segoeui", 10)

    def draw(self, surface, sim_state, hovered):
        r = self.rect
        # Active if this button matches current sim state
        is_active = (sim_state == self.name)
        bg = TB_BTN_ACTIVE_BG if is_active else (TB_BTN_HOVER_BG if hovered else TB_BTN_BG)
        pygame.draw.rect(surface, bg, r, border_radius=5)
        if is_active:
            pygame.draw.rect(surface, TB_ACCENT, r, 1, border_radius=5)

        cx, cy = r.centerx, r.centery
        if self.name == 'playing':
            # Green triangle
            col = (80, 220, 100) if not is_active else (120, 255, 140)
            pts = [(cx-5, cy-6), (cx-5, cy+6), (cx+6, cy)]
            pygame.draw.polygon(surface, col, pts)
        elif self.name == 'paused':
            # Yellow double bar
            col = (240, 200, 60) if not is_active else (255, 230, 80)
            pygame.draw.rect(surface, col, (cx-5, cy-5, 4, 10))
            pygame.draw.rect(surface, col, (cx+1, cy-5, 4, 10))
        elif self.name == 'stopped':
            # Red square
            col = (220, 70, 70) if not is_active else (255, 100, 100)
            pygame.draw.rect(surface, col, (cx-5, cy-5, 10, 10))


# ── TextButton ───────────────────────────────────────────────────────────────────

class TextButton:
    def __init__(self, name, label, rect):
        self.name = name
        self.label = label
        self.rect = rect

    def draw(self, surface, hovered, font):
        r = self.rect
        bg = TB_BTN_HOVER_BG if hovered else TB_BTN_BG
        pygame.draw.rect(surface, bg, r, border_radius=5)
        if hovered:
            pygame.draw.rect(surface, TB_BTN_BORDER, r, 1, border_radius=5)
            
        if font:
            lbl = font.render(self.label, True, TB_LABEL_COLOR)
            surface.blit(lbl, (r.centerx - lbl.get_width()//2, r.centery - lbl.get_height()//2 + 1))


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
        self._tool_btns: list[ToolButton] = []
        self._sim_btns:  list[SimButton]  = []
        self._action_btns: list[TextButton] = []
        self._title_font = None
        self._hint_font  = None
        self._action_font = None
        self._build()

    def _build(self):
        pad  = 8
        side = self.rect.width - pad*2
        tools = [
            ("rect",    "Rect",   _icon_rect,    "R"),
            ("circle",  "Circle", _icon_circle,  "C"),
            ("polygon", "Poly",   _icon_polygon, "P"),
            ("motor",   "Motor",  _icon_motor,   "M"),
            ("text",    "Text",   _icon_text,    "T"),
        ]
        y = self.rect.y + 38
        for name, label, fn, key in tools:
            r = pygame.Rect(self.rect.x+pad, y, side, side)
            self._tool_btns.append(ToolButton(name, label, fn, key, r))
            y += side + 6

        # Sim buttons arranged horizontally
        bw = (self.rect.width - pad*2 - 4) // 3
        bh = 26
        y += 14   # gap after separator
        for i, name in enumerate(['playing', 'paused', 'stopped']):
            rx = self.rect.x + pad + i*(bw+2)
            self._sim_btns.append(SimButton(name, pygame.Rect(rx, y, bw, bh)))

        # Action buttons
        y += bh + 14
        bw2 = (self.rect.width - pad*2 - 2) // 2
        self._action_btns.append(TextButton('save', 'Save', pygame.Rect(self.rect.x + pad, y, bw2, bh)))
        self._action_btns.append(TextButton('load', 'Load', pygame.Rect(self.rect.x + pad + bw2 + 2, y, bw2, bh)))

        y += bh + 4
        self._action_btns.append(TextButton('export', 'Export', pygame.Rect(self.rect.x + pad, y, bw2, bh)))
        self._action_btns.append(TextButton('import', 'Import', pygame.Rect(self.rect.x + pad + bw2 + 2, y, bw2, bh)))

    def init_fonts(self):
        ToolButton.init_fonts()
        SimButton.init_fonts()
        self._title_font = pygame.font.SysFont("segoeui", 12, bold=True)
        self._hint_font  = pygame.font.SysFont("segoeui", 10)
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
        """Returns 'playing' | 'paused' | 'stopped' | None."""
        for b in self._sim_btns:
            if b.rect.collidepoint(pos):
                return b.name
        return None

    def get_action_at(self, pos) -> str | None:
        """Returns 'save' | 'load' | None."""
        for b in self._action_btns:
            if b.rect.collidepoint(pos):
                return b.name
        return None

    # ── draw ─────────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface,
             active_tool: str | None, sim_state: str, mouse_pos):
        r = self.rect
        pygame.draw.rect(surface, TB_BG, r)
        pygame.draw.line(surface, TB_BORDER, (r.right-1, r.top), (r.right-1, r.bottom))

        # Title
        if self._title_font:
            t = self._title_font.render("Tools", True, TB_TITLE_COLOR)
            surface.blit(t, (r.centerx - t.get_width()//2, r.y + 10))
        pygame.draw.line(surface, TB_BORDER, (r.x+6, r.y+28), (r.right-7, r.y+28))

        # Shape tool buttons
        for b in self._tool_btns:
            b.draw(surface, b.tool_name == active_tool, b.rect.collidepoint(mouse_pos))

        # Separator before sim controls
        sep_y = self._sim_btns[0].rect.y - 8
        pygame.draw.line(surface, TB_BORDER, (r.x+6, sep_y), (r.right-7, sep_y))

        # Sim control buttons
        for b in self._sim_btns:
            b.draw(surface, sim_state, b.rect.collidepoint(mouse_pos))

        # Separator before actions
        sep_y2 = self._action_btns[0].rect.y - 8
        pygame.draw.line(surface, TB_BORDER, (r.x+6, sep_y2), (r.right-7, sep_y2))

        # Action buttons
        for b in self._action_btns:
            b.draw(surface, b.rect.collidepoint(mouse_pos), self._action_font)

        # Usage hint at bottom
        if active_tool and sim_state == 'stopped' and self._hint_font:
            lines = self._HINTS.get(active_tool, [])
            lh = self._hint_font.get_height() + 2
            y  = r.bottom - len(lines)*lh - 8
            for line in lines:
                s = self._hint_font.render(line, True, TB_HINT_COLOR)
                surface.blit(s, (r.centerx - s.get_width()//2, y))
                y += lh
