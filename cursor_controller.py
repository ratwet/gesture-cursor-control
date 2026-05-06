# =============================================================================
# cursor_controller.py — Wayland Cursor Control via evdev UInput
# =============================================================================
# Creates a virtual mouse device using Linux uinput kernel module.
# Works natively on Wayland — no X11 or ydotool required.
#
# REQUIREMENT: /dev/uinput must be accessible (set up during project setup):
#   sudo chmod 666 /dev/uinput
#   (Made permanent via /etc/udev/rules.d/99-uinput.rules)
#
# What this module does:
#   1. Creates a virtual mouse device via evdev UInput
#   2. Auto-detects screen resolution
#   3. Converts normalised landmark coordinates → relative pixel movement
#   4. Fires left click, right click on demand
#
# Standalone test:
#   python3 cursor_controller.py
# =============================================================================

import time
import glob
import subprocess
import config

try:
    from evdev import UInput, ecodes as e
except ImportError:
    raise ImportError(
        "❌ evdev not installed.\n"
        "   Run: pip install evdev"
    )


class CursorController:
    """
    Controls the mouse cursor on Wayland using a virtual evdev input device.

    Methods
    -------
    move(norm_x, norm_y)  — move cursor to normalised position [0,1]
    left_click()          — fire a left mouse button click
    right_click()         — fire a right mouse button click
    close()               — release the virtual device cleanly
    """

    def __init__(self):
        # ── Detect screen resolution ──────────────────────────────────────────
        self.screen_w, self.screen_h = self._detect_resolution()
        print(f"✅ Screen resolution → {self.screen_w}×{self.screen_h}")

        # ── Create virtual mouse device via uinput ────────────────────────────
        capabilities = {
            e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL],
            e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT],
        }

        try:
            self._ui = UInput(capabilities, name="gesture-cursor-control")
        except PermissionError:
            raise PermissionError(
                "❌ Cannot write to /dev/uinput — permission denied.\n"
                "   Fix with:  sudo chmod 666 /dev/uinput\n"
                "   Make permanent: echo 'KERNEL==\"uinput\", MODE=\"0666\"' "
                "| sudo tee /etc/udev/rules.d/99-uinput.rules"
            )

        # ── Internal state ────────────────────────────────────────────────────
        # Previous landmark position — used to compute relative movement delta
        self._prev_x = None   # normalised [0.0–1.0]
        self._prev_y = None
        self._prev_scroll_y = None  # for scroll delta tracking

        # Warm-up: let the OS register the virtual device before sending events
        time.sleep(0.1)

        print(f"✅ Virtual mouse created → '{self._ui.name}'")


    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================

    def move(self, norm_x, norm_y):
        """
        Move the cursor to the given normalised position.

        Parameters
        ----------
        norm_x : float  normalised x from landmark [0.0–1.0]
        norm_y : float  normalised y from landmark [0.0–1.0]

        How it works:
          1. Apply screen margin (ignore outer 5% of camera frame)
          2. Convert normalised coords → screen pixels
          3. Compute delta from previous position
          4. Send REL_X / REL_Y events to virtual mouse
        """
        # Apply margin — clamp to inner (1 - 2*margin) of frame
        m  = config.SCREEN_MARGIN
        cx = (norm_x - m) / (1.0 - 2.0 * m)
        cy = (norm_y - m) / (1.0 - 2.0 * m)
        cx = max(0.0, min(1.0, cx))
        cy = max(0.0, min(1.0, cy))

        # Convert to absolute screen pixels
        abs_x = cx * self.screen_w
        abs_y = cy * self.screen_h

        # First frame — no previous position yet, just store and return
        if self._prev_x is None:
            self._prev_x = abs_x
            self._prev_y = abs_y
            return

        # Compute relative delta and apply sensitivity multiplier
        dx = int((abs_x - self._prev_x) * config.MOVE_SENSITIVITY)
        dy = int((abs_y - self._prev_y) * config.MOVE_SENSITIVITY)

        self._prev_x = abs_x
        self._prev_y = abs_y

        # Only send event if there's actual movement (skip zero deltas)
        if dx != 0 or dy != 0:
            self._ui.write(e.EV_REL, e.REL_X, dx)
            self._ui.write(e.EV_REL, e.REL_Y, dy)
            self._ui.syn()  # Flush — required after each event group


    def left_click(self):
        """Fire a left mouse button press + release."""
        self._ui.write(e.EV_KEY, e.BTN_LEFT, 1)  # Press
        self._ui.syn()
        time.sleep(0.01)                           # Short hold (10ms)
        self._ui.write(e.EV_KEY, e.BTN_LEFT, 0)  # Release
        self._ui.syn()


    def right_click(self):
        """Fire a right mouse button press + release."""
        self._ui.write(e.EV_KEY, e.BTN_RIGHT, 1)
        self._ui.syn()
        time.sleep(0.01)
        self._ui.write(e.EV_KEY, e.BTN_RIGHT, 0)
        self._ui.syn()


    def scroll(self, norm_y):
        """
        Scroll the page based on vertical hand movement.

        Parameters
        ----------
        norm_y : float  normalised Y of midpoint between index+middle tips

        How it works:
          - Tracks Y delta between frames (like move() does for cursor)
          - dy < 0 (hand moving UP)   → scroll UP   (positive REL_WHEEL)
          - dy > 0 (hand moving DOWN) → scroll DOWN  (negative REL_WHEEL)
          - Deadzone applied — tiny movements don't fire scroll events
          - Scale factor converts normalised delta → scroll ticks
        """
        if self._prev_scroll_y is None:
            self._prev_scroll_y = norm_y
            return

        dy = norm_y - self._prev_scroll_y
        self._prev_scroll_y = norm_y

        # Deadzone — ignore tiny jitter (< 0.008 normalised = ~8px at 1080p)
        if abs(dy) < 0.008:
            return

        # Convert to scroll ticks — negative dy = hand up = scroll up
        # Scale 30 gives ~3 ticks per visible hand movement — feels natural
        scroll_ticks = -int(dy * 30)

        if scroll_ticks != 0:
            self._ui.write(e.EV_REL, e.REL_WHEEL, scroll_ticks)
            self._ui.syn()


    def reset_scroll(self):
        """Clear scroll tracking — call when leaving SCROLL gesture."""
        self._prev_scroll_y = None


    def reset_position(self):
        """
        Clear the stored previous position.
        Call this when tracking resumes after a FIST (freeze) gesture
        so the cursor doesn't jump to catch up from old position.
        """
        self._prev_x = None
        self._prev_y = None


    def close(self):
        """Release the virtual input device cleanly."""
        self._ui.close()
        print("🛑 Virtual mouse released.")


    # =========================================================================
    # SCREEN RESOLUTION DETECTION
    # =========================================================================

    @staticmethod
    def _detect_resolution():
        """
        Auto-detect screen resolution using multiple fallback methods.

        Tries (in order):
          1. xrandr subprocess  (works on X11 and some Wayland compositors)
          2. /sys/class/drm/*/modes  (kernel DRM — Wayland reliable)
          3. Hardcoded default 1920×1080  (safe fallback for Dell Latitude 5420)
        """
        # Method 1 — xrandr
        try:
            out = subprocess.check_output(
                ['xrandr'], stderr=subprocess.DEVNULL
            ).decode()
            for line in out.splitlines():
                if '*' in line:
                    res = line.strip().split()[0]
                    w, h = res.split('x')
                    return int(w), int(h)
        except Exception:
            pass

        # Method 2 — /sys/class/drm kernel interface (Wayland-safe)
        try:
            for path in sorted(glob.glob('/sys/class/drm/*/modes')):
                with open(path) as f:
                    first_line = f.readline().strip()
                    if first_line and 'x' in first_line:
                        w, h = first_line.split('x')
                        return int(w), int(h)
        except Exception:
            pass

        # Method 3 — safe default (Dell Latitude 5420 native resolution)
        print("⚠️  Could not auto-detect resolution — defaulting to 1920×1080")
        print("   To override, set SCREEN_WIDTH / SCREEN_HEIGHT in config.py")
        return 1920, 1080


# =============================================================================
# STANDALONE TEST — python3 cursor_controller.py
# Moves cursor in a smooth diagonal then fires a left + right click.
# =============================================================================
if __name__ == "__main__":
    print("=" * 55)
    print("  PHASE 3 TEST — Cursor Controller")
    print("  Watch your cursor move diagonally across the screen.")
    print("  Then a left click + right click will fire.")
    print("=" * 55)

    ctrl = CursorController()

    print("\n🖱️  Moving cursor diagonally (top-left → centre)...")
    # Simulate landmark moving from (0.1, 0.1) to (0.5, 0.5) in small steps
    steps = 60
    for i in range(steps + 1):
        t    = i / steps
        nx   = 0.1 + t * 0.4   # 0.1 → 0.5
        ny   = 0.1 + t * 0.4
        ctrl.move(nx, ny)
        time.sleep(0.016)       # ~60fps

    print("✅ Cursor movement done")
    time.sleep(0.3)

    print("🖱️  Firing LEFT click...")
    ctrl.left_click()
    print("✅ Left click fired")
    time.sleep(0.5)

    print("🖱️  Firing RIGHT click...")
    ctrl.right_click()
    print("✅ Right click fired")

    ctrl.close()
    print("\n✅ Phase 3 test complete.")
    print("   Did your cursor move and clicks fire? → Ready for Phase 4!")
