WIDTH  = 1000
HEIGHT = 650
FPS    = 60
TITLE  = "Physics Engine"

# Beyond this distance from world origin in any direction, bodies are frozen
WORLD_KILL_LIMIT = 50_000   # pixels


class Colors:
    WHITE = (255, 255, 255)
    BLACK = (0,   0,   0)
    RED   = (255, 0,   0)
    GREEN = (0,   255, 0)
    BLUE  = (0,   0,   255)


# ── Physics ─────────────────────────────────────────────────────────────────────
GRAVITY               = 500.0  # px / s²
PHYSICS_SUBSTEPS      = 8      # sub-steps per frame (higher = stabler collisions)
DRAW_COLLISION_POINTS = False   # toggle visualization of collision contacts

# ── Body visuals ────────────────────────────────────────────────────────────────
BODY_COLOR       = (210, 195, 175)
BODY_FIXED_COLOR = (100,  90,  75)

# ── Warm-dark amber palette ──────────────────────────────────────────────────────
#   Inspired by the reference screenshots — charcoal base with amber accents.

# Toolbox
TOOLBOX_WIDTH      = 140
TB_BG              = (22,  18,  14)   # very dark warm brown
TB_BORDER          = (50,  40,  28)
TB_HEADER_BG       = (58,  36,  12)   # amber-brown header strip
TB_BTN_BG          = (34,  26,  18)
TB_BTN_HOVER_BG    = (55,  42,  26)
TB_BTN_ACTIVE_BG   = (90,  52,  16)   # warm amber active
TB_BTN_BORDER      = (70,  52,  30)
TB_ACCENT          = (212, 120,  42)  # amber
TB_ACCENT_BRIGHT   = (232, 148,  62)  # lighter amber on hover
TB_ICON_COLOR      = (160, 130, 100)
TB_ICON_ACTIVE     = (232, 180, 100)  # warm gold when active
TB_KEY_COLOR       = (90,   72,  50)
TB_LABEL_COLOR     = (180, 148, 110)
TB_HINT_COLOR      = (110,  88,  62)
TB_TITLE_COLOR     = (200, 160, 100)
TB_SEP_COLOR       = (48,   38,  24)

# Context menu
CM_BG          = (24,  20,  14)
CM_BORDER      = (58,  44,  26)
CM_HEADER_BG   = (52,  32,  10)
CM_TITLE_COLOR = (220, 175, 105)
CM_TEXT_COLOR  = (170, 138, 100)
CM_BTN_BG      = (38,  28,  18)
CM_BTN_HOVER   = (62,  46,  28)
CM_BTN_ACTIVE  = (88,  52,  16)
CM_ACCENT      = (212, 120,  42)
