# =============================================================================
# config.py — Central Configuration for Gesture Cursor Control
# =============================================================================
# ALL tunable parameters live here.
# Change values here to adjust behaviour — no need to dig into other files.
# =============================================================================

# -----------------------------------------------------------------------------
# CAMERA
# -----------------------------------------------------------------------------
CAMERA_INDEX   = 0      # /dev/video0 = main RGB webcam (Dell Latitude 5420)
                        # Fallback: try 2 if 0 doesn't work (/dev/video2)
FRAME_WIDTH    = 640    # Capture resolution width  (pixels)
FRAME_HEIGHT   = 480    # Capture resolution height (pixels)
FLIP_CAMERA    = True   # Mirror image horizontally — natural "mirror" feel

# -----------------------------------------------------------------------------
# MEDIAPIPE HAND DETECTION
# -----------------------------------------------------------------------------
MAX_HANDS         = 1   # Track only 1 hand — simpler + faster
DETECTION_CONF    = 0.7 # Min confidence to detect a hand (0.0–1.0)
TRACKING_CONF     = 0.6 # Min confidence to keep tracking (0.0–1.0)
                        # Lower = more responsive but more false positives

# -----------------------------------------------------------------------------
# GESTURE THRESHOLDS  (normalised 0.0–1.0 scale, NOT pixels)
# -----------------------------------------------------------------------------
LCLICK_THRESHOLD     = 0.05  # Left click  — thumb+index  (tight, natural pinch)
RCLICK_THRESHOLD     = 0.10  # Right click — thumb+middle (wider, across palm)
                              # R is larger because thumb travels further to reach middle
                              # Decrease → harder to click | Increase → easier

DOUBLE_CLICK_TIME    = 0.5   # Max seconds between 2 pinches = double click
CLICK_COOLDOWN       = 0.8   # Min seconds between any two clicks (debounce)

# -----------------------------------------------------------------------------
# CURSOR MOVEMENT
# -----------------------------------------------------------------------------
SMOOTHING_FRAMES  = 6    # Moving average buffer size
                         # Higher = smoother but more lag
                         # Lower  = more responsive but shakier

MOVE_SENSITIVITY  = 1.3  # Cursor speed multiplier
                         # 1.0 = 1:1 mapping, 1.5 = 50% faster

SCREEN_MARGIN     = 0.05 # Dead zone at frame edges (normalised 0.0–1.0)
                         # Prevents cursor getting stuck at screen edges
                         # 0.05 = ignore outer 5% of camera frame

# -----------------------------------------------------------------------------
# DISPLAY / HUD
# -----------------------------------------------------------------------------
SHOW_WINDOW  = True                     # Show camera feed with landmarks
WINDOW_NAME  = "Gesture Cursor Control" # OpenCV window title

# HUD text colours (BGR format — OpenCV uses BGR not RGB)
HUD_GREEN    = (0,   220,  0)    # Gesture label when active
HUD_WHITE    = (255, 255, 255)   # General info text
HUD_RED      = (0,   0,   220)   # Warning / frozen state
HUD_YELLOW   = (0,   220, 220)   # FPS counter

# Landmark drawing colours
LANDMARK_DOT_COLOR  = (0, 220, 0)      # Green dots on joints
LANDMARK_LINE_COLOR = (200, 200, 200)  # White-ish connections

# -----------------------------------------------------------------------------
# MEDIAPIPE LANDMARK INDICES  (for easy reference in classifier)
# -----------------------------------------------------------------------------
# Wrist
WRIST          = 0

# Thumb
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP   = 1, 2, 3, 4

# Index finger
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP  = 5, 6, 7, 8

# Middle finger
MID_MCP, MID_PIP, MID_DIP, MID_TIP         = 9, 10, 11, 12

# Ring finger
RING_MCP, RING_PIP, RING_DIP, RING_TIP     = 13, 14, 15, 16

# Pinky
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20
