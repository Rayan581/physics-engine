WIDTH  = 800
HEIGHT = 600
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
BODY_COLOR       = (200, 200, 220)
BODY_FIXED_COLOR = (110, 110, 140)

# ── Toolbox ─────────────────────────────────────────────────────────────────────
TOOLBOX_WIDTH      = 80
TB_BG              = (22,  22,  32)
TB_BORDER          = (42,  42,  60)
TB_BTN_BG          = (34,  34,  50)
TB_BTN_HOVER_BG    = (50,  52,  75)
TB_BTN_ACTIVE_BG   = (30,  65,  110)
TB_BTN_BORDER      = (55,  55,  78)
TB_ACCENT          = (100, 180, 255)
TB_ICON_COLOR      = (170, 170, 205)
TB_ICON_ACTIVE     = (140, 210, 255)
TB_KEY_COLOR       = (90,  90,  120)
TB_LABEL_COLOR     = (140, 140, 170)
TB_HINT_COLOR      = (100, 100, 135)
TB_TITLE_COLOR     = (120, 120, 155)

# ── Context menu ────────────────────────────────────────────────────────────────
CM_BG          = (28,  28,  42)
CM_BORDER      = (60,  60,  90)
CM_TITLE_COLOR = (180, 180, 210)
CM_TEXT_COLOR  = (150, 150, 185)
CM_BTN_BG      = (40,  40,  60)
CM_BTN_HOVER   = (60,  60,  90)
CM_BTN_ACTIVE  = (35,  85,  140)
CM_ACCENT      = (100, 180, 255)
