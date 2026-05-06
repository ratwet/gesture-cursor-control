# =============================================================================
# main.py — Gesture Cursor Control  (Entry Point)
# =============================================================================
# Wires all modules together into one main loop:
#
#   HandDetector → GestureClassifier → Smoother → CursorController
#
# Gesture → Action mapping:
#   ☝️  POINT       → smooth landmark position → move cursor
#   🤏  LEFT_CLICK  → fire left mouse click
#   🤏  RIGHT_CLICK → fire right mouse click
#   ✊  FIST        → freeze cursor (nothing moves until fist released)
#   ·   NONE        → idle (cursor stays put)
#
# Controls:
#   Q / Ctrl+C → quit cleanly (always releases camera + virtual mouse)
#
# Run:
#   source ~/gesture_env/bin/activate
#   python3 main.py
# =============================================================================

import cv2
import time
import sys

import config
from hand_detector       import HandDetector
from gesture_classifier  import GestureClassifier
from smoother            import Smoother
from cursor_controller   import CursorController


# =============================================================================
# HUD HELPERS
# =============================================================================

def draw_hud(frame, gesture, fps, frozen, hand_found):
    """
    Draw the heads-up display overlay on the camera frame.

    Shows: FPS, current gesture label, FROZEN banner, control hints.
    """
    h, w = frame.shape[:2]

    # ── FPS (top-left) ────────────────────────────────────────────────────────
    cv2.putText(frame, f"FPS: {fps:.1f}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                0.75, config.HUD_YELLOW, 2)

    # ── Gesture label (top-centre) ────────────────────────────────────────────
    GESTURE_COLOURS = {
        "POINT"       : config.HUD_GREEN,
        "SCROLL"      : (0,   200, 255),   # Cyan-yellow
        "LEFT_CLICK"  : (0,   165, 255),   # Orange
        "RIGHT_CLICK" : (255, 100,  50),   # Blue-ish
        "FIST"        : config.HUD_RED,
        "NONE"        : (150, 150, 150),   # Grey
    }
    colour   = GESTURE_COLOURS.get(gesture, config.HUD_WHITE)
    lbl_w    = cv2.getTextSize(gesture, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)[0][0]
    cv2.putText(frame, gesture,
                ((w - lbl_w) // 2, 65),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, colour, 3)

    # ── FROZEN banner (centre screen) ─────────────────────────────────────────
    if frozen:
        # Semi-transparent dark bar
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h//2 - 45), (w, h//2 + 45),
                      (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

        banner      = "FROZEN  -  Open hand to resume"
        banner_w    = cv2.getTextSize(banner, cv2.FONT_HERSHEY_SIMPLEX,
                                       0.85, 2)[0][0]
        cv2.putText(frame, banner,
                    ((w - banner_w) // 2, h // 2 + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.85,
                    config.HUD_RED, 2)

    # ── No hand warning ───────────────────────────────────────────────────────
    if not hand_found:
        cv2.putText(frame, "Show hand to camera",
                    (10, h - 40), cv2.FONT_HERSHEY_SIMPLEX,
                    0.65, config.HUD_RED, 2)

    # ── Controls hint (bottom-left) ───────────────────────────────────────────
    cv2.putText(frame,
                "Q=quit | point=move | pinch=click | fist=freeze",
                (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX,
                0.5, config.HUD_WHITE, 1)


def draw_gesture_icon(frame, gesture):
    """
    Draw a small coloured indicator dot in the top-right corner
    as a quick at-a-glance status light.
    """
    COLOURS = {
        "POINT"       : config.HUD_GREEN,
        "SCROLL"      : (0,   200, 255),
        "LEFT_CLICK"  : (0,   165, 255),
        "RIGHT_CLICK" : (255, 100,  50),
        "FIST"        : config.HUD_RED,
        "NONE"        : (80,  80,  80),
    }
    h, w  = frame.shape[:2]
    colour = COLOURS.get(gesture, (80, 80, 80))
    cv2.circle(frame, (w - 25, 25), 14, colour, -1)
    cv2.circle(frame, (w - 25, 25), 14, (255, 255, 255), 1)  # White border


# =============================================================================
# MAIN LOOP
# =============================================================================

def main():
    print("=" * 60)
    print("  🖐️  Gesture Cursor Control  —  Starting up")
    print("=" * 60)

    # ── Initialise all modules ────────────────────────────────────────────────
    try:
        detector   = HandDetector()
        classifier = GestureClassifier()
        smoother   = Smoother()
        controller = CursorController()
    except Exception as ex:
        print(f"\n❌ Startup failed: {ex}")
        sys.exit(1)

    print("\n✅ All modules ready — starting gesture control!")
    print("   ☝️  Point              → move cursor")
    print("   ✌️  Index+middle up    → scroll up/down")
    print("   Pinch thumb+index    → left click")
    print("   Fist + thumb+middle  → right click")
    print("   ✊  Fist              → freeze cursor")
    print("   Q  / Ctrl+C          → quit\n")

    # ── State tracking ────────────────────────────────────────────────────────
    frozen        = False    # True when FIST gesture is active
    prev_gesture  = "NONE"   # Previous frame's gesture — for FIST transition
    prev_time     = time.time()

    # ── Main loop ─────────────────────────────────────────────────────────────
    try:
        while True:
            # ── 1. Capture frame + detect landmarks ───────────────────────────
            landmarks, frame, hand_found = detector.get_landmarks(draw=True)

            # ── 2. Classify gesture ───────────────────────────────────────────
            gesture = classifier.classify(landmarks)

            # ── 3. State machine — route gesture to action ────────────────────

            # FIST → enter freeze mode
            if gesture == "FIST":
                if not frozen:
                    frozen = True
                    print("✊ FROZEN")

            # Leaving FIST → reset smoother + controller (prevent cursor jump)
            elif prev_gesture == "FIST" and gesture != "FIST":
                frozen = False
                smoother.reset()
                controller.reset_position()
                controller.reset_scroll()
                print("Unfrozen — cursor reset")

            # Reset scroll tracker when leaving SCROLL gesture
            if prev_gesture == "SCROLL" and gesture != "SCROLL":
                controller.reset_scroll()

            # Normal gestures — only act when NOT frozen
            if not frozen and hand_found:

                if gesture == "POINT":
                    raw_x = landmarks[config.INDEX_TIP].x
                    raw_y = landmarks[config.INDEX_TIP].y
                    sx, sy = smoother.smooth(raw_x, raw_y)
                    controller.move(sx, sy)

                elif gesture == "SCROLL":
                    # Use midpoint between index + middle tips for stable Y
                    mid_y = (landmarks[config.INDEX_TIP].y +
                             landmarks[config.MID_TIP].y) / 2.0
                    controller.scroll(mid_y)

                elif gesture == "LEFT_CLICK":
                    controller.left_click()
                    print("Left click")

                elif gesture == "RIGHT_CLICK":
                    controller.right_click()
                    print("Right click")

                # NONE / FIST → idle

            prev_gesture = gesture

            # ── 4. HUD overlay ────────────────────────────────────────────────
            curr_time = time.time()
            fps       = 1.0 / max(curr_time - prev_time, 1e-6)
            prev_time = curr_time

            draw_hud(frame, gesture, fps, frozen, hand_found)
            draw_gesture_icon(frame, gesture)

            # ── 5. Display frame ──────────────────────────────────────────────
            if config.SHOW_WINDOW:
                cv2.imshow(config.WINDOW_NAME, frame)

            # ── 6. Exit on Q ──────────────────────────────────────────────────
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n👋 Q pressed — quitting...")
                break

    except KeyboardInterrupt:
        print("\n👋 Ctrl+C — quitting...")

    finally:
        # ── Always release resources, even on crash ───────────────────────────
        print("\n🧹 Cleaning up...")
        detector.release()
        controller.close()
        cv2.destroyAllWindows()
        print("✅ Clean exit. Bye!")


# =============================================================================
if __name__ == "__main__":
    main()
