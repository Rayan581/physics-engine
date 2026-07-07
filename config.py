WIDTH  = 1000
HEIGHT = 650
FPS    = 60
TITLE  = "Physics Engine"

# Beyond this distance from world origin in any direction, bodies are frozen
WORLD_KILL_LIMIT = 50_000   # pixels

# Colors
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

# -- Camera --
CAMERA_MIN_ZOOM = 0.1
CAMERA_MAX_ZOOM = 10.0

# ── Body Visuals ──
GHOST_COLOR_FILL     = (80, 180, 255, 40)
BODY_OUTLINE_COLOR   = (40, 30, 20)
COM_COLOR            = (220, 60, 60)

# ── Text Fonts ──
FONT_NAME            = "segoeui"
TEXT_BODY_FONT_SIZE  = 48

# ── Drawing Tools ──
POLYGON_CLOSE_RADIUS  = 20
DRAW_GHOST_COLOR      = (120, 200, 255)
DRAW_OUTLINE_COLOR    = (120, 200, 255)
DRAW_CLOSE_RING_NEAR  = (80, 255, 140)
DRAW_CLOSE_RING_FAR   = (160, 160, 160)
DRAW_MOTOR_PREVIEW    = (255, 150, 0)

# ── Joints ──
MOTOR_ENABLED_COLOR   = (255, 150, 0)
MOTOR_DISABLED_COLOR  = (100, 200, 255)
LIMIT_MIN_COLOR       = (255, 100, 100)
LIMIT_MAX_COLOR       = (100, 255, 100)

# ── Collision Resolution ──
POSITIONAL_CORRECTION_PERCENT = 0.8
POSITIONAL_CORRECTION_SLOP    = 0.1

# ── Extra Toolbox Colors ──
TB_TOGGLE_TRACK_OFF     = (50, 38, 24)
TB_TOGGLE_KNOB_ON       = (230, 200, 150)
TB_TOGGLE_KNOB_OFF      = (120, 95, 65)
TB_PLAY_ACCENT          = (82, 190, 100)
TB_PLAY_ACCENT_ACTIVE   = (110, 220, 130)
TB_PAUSE_ACCENT         = (200, 160, 50)
TB_PAUSE_ACCENT_ACTIVE  = (230, 190, 70)
TB_STOP_ACCENT          = (190, 75, 60)
TB_STOP_ACCENT_ACTIVE   = (220, 100, 85)
TB_BTN_BORDER_IDLE      = (40, 30, 18)
TB_ICON_INACTIVE        = (180, 160, 130)
CM_TEXTBOX_EDIT_BG = (40, 30, 18)

# ── Canvas & Grid ──
CANVAS_BG               = (18, 14, 10)
GRID_COLOR              = (32, 26, 18)

# ── Selection & Handles ──
SEL_COLOR               = (212, 140, 50)
BAND_COLOR              = (180, 110, 40)
SELECTED_HANDLE_COL     = (255, 255, 50)

# ── Training HUD ──
TRAINING_TITLE_COLOR    = (220, 180, 120)
TRAINING_BAR_BG         = (40, 30, 20)
TRAINING_BAR_FILL       = (212, 120, 42)
TRAINING_PROG_LBL       = (170, 140, 100)
TRAINING_FIT_LBL        = (240, 210, 160)
BADGE_PLAY_COL          = (50, 200, 100)
BADGE_PLAY_TEXT         = (220, 255, 220)
BADGE_FAST_COL_PULSE    = (180, 60, 60)
BADGE_FAST_COL          = (100, 30, 30)
BADGE_FAST_TEXT_PULSE   = (255, 200, 200)
BADGE_FAST_TEXT         = (180, 120, 120)
ESC_HINT_COL            = (100, 100, 130)

# ── Neural Network HUD ──
NN_TITLE_COL            = (220, 180, 120)
NN_BORDER_POS           = (120, 200, 100)
NN_BORDER_NEG           = (232, 180, 100)
NN_BORDER_NEUT          = (140, 110, 80)
NN_VAL_LBL              = (230, 230, 230)
