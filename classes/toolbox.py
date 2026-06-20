"""
classes/toolbox.py
==================
Paint-style left-sidebar toolbox.

Each tool is represented as a square button with:
  - A vector icon drawn with pygame primitives
  - A short label below the icon
  - A key-hint badge in the top-right corner
  - Hover glow and active-accent highlighting

All colours and the panel width come from config.py.
"""

import math
import pygame
from config import *


# ── Icon draw functions ────────────────────────────────────────────────────────

def _icon_rect(surface: pygame.Surface, cx: int, cy: int, active: bool):
    col = TB_ICON_ACTIVE if active else TB_ICON_COLOR
    w, h = 24, 17
    pygame.draw.rect(surface, col, (cx - w // 2, cy - h // 2, w, h), 2,
                     border_radius=2)


def _icon_circle(surface: pygame.Surface, cx: int, cy: int, active: bool):
    col = TB_ICON_ACTIVE if active else TB_ICON_COLOR
    pygame.draw.circle(surface, col, (cx, cy), 12, 2)


def _icon_polygon(surface: pygame.Surface, cx: int, cy: int, active: bool):
    col = TB_ICON_ACTIVE if active else TB_ICON_COLOR
    # Irregular pentagon (slightly more interesting than a regular one)
    r_outer = 12
    pts = []
    offsets = [0, 72, 144, 216, 288]   # regular pentagon angles
    for angle in offsets:
        rad = math.radians(angle - 90)
        pts.append((cx + int(r_outer * math.cos(rad)),
                    cy + int(r_outer * math.sin(rad))))
    pygame.draw.polygon(surface, col, pts, 2)


# ── ToolButton ─────────────────────────────────────────────────────────────────

class ToolButton:
    """A single square button inside the toolbox."""

    _LABEL_FONT: pygame.font.Font | None = None
    _KEY_FONT:   pygame.font.Font | None = None

    def __init__(self, tool_name: str, label: str,
                 icon_fn, key_hint: str, rect: pygame.Rect):
        self.tool_name = tool_name
        self.label     = label
        self._icon_fn  = icon_fn
        self.key_hint  = key_hint
        self.rect      = rect

    @classmethod
    def init_fonts(cls):
        cls._LABEL_FONT = pygame.font.SysFont("segoeui", 11)
        cls._KEY_FONT   = pygame.font.SysFont("segoeui", 10)

    def draw(self, surface: pygame.Surface, active: bool, hovered: bool):
        r = self.rect

        # ── Background ──────────────────────────────────────────────────────
        if active:
            bg = TB_BTN_ACTIVE_BG
        elif hovered:
            bg = TB_BTN_HOVER_BG
        else:
            bg = TB_BTN_BG
        pygame.draw.rect(surface, bg, r, border_radius=7)

        # ── Border ──────────────────────────────────────────────────────────
        if active:
            pygame.draw.rect(surface, TB_ACCENT, r, 2, border_radius=7)
        elif hovered:
            pygame.draw.rect(surface, TB_BTN_BORDER, r, 1, border_radius=7)

        # ── Icon (centred, shifted up a bit for the label) ──────────────────
        icon_cy = r.y + r.height // 2 - 7
        self._icon_fn(surface, r.centerx, icon_cy, active)

        # ── Label ────────────────────────────────────────────────────────────
        if self._LABEL_FONT:
            col  = TB_ICON_ACTIVE if active else TB_LABEL_COLOR
            surf = self._LABEL_FONT.render(self.label, True, col)
            surface.blit(surf, (r.centerx - surf.get_width() // 2,
                                r.bottom - surf.get_height() - 4))

        # ── Key hint (small badge, top-right) ────────────────────────────────
        if self._KEY_FONT:
            col  = TB_ACCENT if active else TB_KEY_COLOR
            surf = self._KEY_FONT.render(self.key_hint, True, col)
            surface.blit(surf, (r.right - surf.get_width() - 4, r.y + 4))


# ── Toolbox ───────────────────────────────────────────────────────────────────

class Toolbox:
    """
    Left-sidebar toolbox panel, similar to classic Paint.

    Usage
    -----
    - Call ``init_fonts()`` once after ``pygame.init()``.
    - Call ``draw(surface, active_tool, mouse_pos)`` every frame.
    - Call ``handle_click(pos)`` on MOUSEBUTTONDOWN events;
      returns the tool name to activate, ``None`` if no button was hit,
      or the *same* tool name if already active (caller should toggle).
    - Check ``contains(pos)`` to decide whether a click is for the toolbox
      or for the canvas.
    """

    # Usage hints shown at the bottom of the panel for the active tool
    _HINTS: dict[str, list[str]] = {
        'rect':    ["Click corner A,", "then corner B"],
        'circle':  ["Click center,",   "then radius pt"],
        'polygon': ["Click vertices,", "click near",    "start to close"],
    }

    def __init__(self, x: int, y: int, width: int, height: int):
        self.rect = pygame.Rect(x, y, width, height)
        self._buttons: list[ToolButton] = []
        self._title_font: pygame.font.Font | None = None
        self._hint_font:  pygame.font.Font | None = None
        self._build_buttons()

    # ── Setup ──────────────────────────────────────────────────────────────────

    def _build_buttons(self):
        pad      = 8
        btn_side = self.rect.width - pad * 2    # square button
        tools = [
            ("rect",    "Rect",   _icon_rect,    "R"),
            ("circle",  "Circle", _icon_circle,  "C"),
            ("polygon", "Poly",   _icon_polygon, "P"),
        ]
        y = self.rect.y + 38   # leave room below title
        for name, label, icon_fn, key in tools:
            r = pygame.Rect(self.rect.x + pad, y, btn_side, btn_side)
            self._buttons.append(ToolButton(name, label, icon_fn, key, r))
            y += btn_side + 6

    def init_fonts(self):
        ToolButton.init_fonts()
        self._title_font = pygame.font.SysFont("segoeui", 12, bold=True)
        self._hint_font  = pygame.font.SysFont("segoeui", 10)

    # ── Query ──────────────────────────────────────────────────────────────────

    def contains(self, pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)

    def get_tool_at(self, pos: tuple[int, int]) -> str | None:
        """Return the tool_name of the button under *pos*, or None."""
        for btn in self._buttons:
            if btn.rect.collidepoint(pos):
                return btn.tool_name
        return None

    # ── Draw ───────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface,
             active_tool: str | None, mouse_pos: tuple[int, int]):

        # Panel background
        pygame.draw.rect(surface, TB_BG, self.rect)

        # Right separator line
        pygame.draw.line(surface, TB_BORDER,
                         (self.rect.right - 1, self.rect.top),
                         (self.rect.right - 1, self.rect.bottom))

        # "Tools" title
        if self._title_font:
            t = self._title_font.render("Tools", True, TB_TITLE_COLOR)
            surface.blit(t, (self.rect.centerx - t.get_width() // 2,
                             self.rect.y + 10))

        # Thin line under title
        ty = self.rect.y + 28
        pygame.draw.line(surface, TB_BORDER,
                         (self.rect.x + 6, ty),
                         (self.rect.right - 7, ty))

        # Buttons
        for btn in self._buttons:
            btn.draw(surface,
                     active  = (btn.tool_name == active_tool),
                     hovered = btn.rect.collidepoint(mouse_pos))

        # Usage hint at bottom
        if active_tool and self._hint_font:
            lines = self._HINTS.get(active_tool, [])
            line_h = self._hint_font.get_height() + 2
            total  = len(lines) * line_h
            y = self.rect.bottom - total - 10
            for line in lines:
                s = self._hint_font.render(line, True, TB_HINT_COLOR)
                surface.blit(s, (self.rect.centerx - s.get_width() // 2, y))
                y += line_h
