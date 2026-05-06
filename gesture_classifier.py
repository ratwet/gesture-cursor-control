# =============================================================================
# gesture_classifier.py — Gesture Classification from Hand Landmarks
# =============================================================================
# Gestures:
#   "POINT"       → Index up, others curled           → move cursor
#   "SCROLL"      → Index + Middle up, ring down      → scroll
#   "LEFT_CLICK"  → Thumb+Index pinch   (threshold 0.05) → left click
#   "RIGHT_CLICK" → Thumb+Middle pinch  (threshold 0.10) → right click
#   "FIST"        → All fingers curled                → freeze
#   "NONE"        → No clear gesture
# =============================================================================

import time
import math
import config


class GestureClassifier:

    def __init__(self):
        self._last_lclick_time = 0.0
        self._last_rclick_time = 0.0
        print("✅ GestureClassifier ready")


    def classify(self, landmarks):
        """
        Returns: "POINT"|"SCROLL"|"LEFT_CLICK"|"RIGHT_CLICK"|"FIST"|"NONE"
        Priority: FIST > LEFT_CLICK > RIGHT_CLICK > SCROLL > POINT > NONE
        """
        if landmarks is None:
            return "NONE"

        if self._is_fist(landmarks):       return "FIST"
        if self._is_left_click(landmarks): return "LEFT_CLICK"
        if self._is_right_click(landmarks):return "RIGHT_CLICK"
        if self._is_scrolling(landmarks):  return "SCROLL"
        if self._is_pointing(landmarks):   return "POINT"
        return "NONE"


    # =========================================================================
    # DETECTORS
    # =========================================================================

    def _is_pointing(self, lm):
        """Index up, middle + ring curled."""
        return (
            lm[config.INDEX_TIP].y < lm[config.INDEX_PIP].y and
            lm[config.MID_TIP].y   > lm[config.MID_PIP].y  and
            lm[config.RING_TIP].y  > lm[config.RING_PIP].y
        )


    def _is_scrolling(self, lm):
        """Peace sign ✌️ — index AND middle up, ring + pinky down."""
        return (
            lm[config.INDEX_TIP].y < lm[config.INDEX_PIP].y and
            lm[config.MID_TIP].y   < lm[config.MID_PIP].y  and
            lm[config.RING_TIP].y  > lm[config.RING_PIP].y and
            lm[config.PINKY_TIP].y > lm[config.PINKY_PIP].y
        )


    def _is_fist(self, lm):
        """All 4 fingertips below their PIP joints."""
        return (
            lm[config.INDEX_TIP].y > lm[config.INDEX_PIP].y and
            lm[config.MID_TIP].y   > lm[config.MID_PIP].y  and
            lm[config.RING_TIP].y  > lm[config.RING_PIP].y and
            lm[config.PINKY_TIP].y > lm[config.PINKY_PIP].y
        )


    def _is_left_click(self, lm):
        """
        LEFT CLICK — Easy, most frequent.
        Pinch thumb (#4) to index tip (#8). Threshold: LCLICK_THRESHOLD=0.05

        Guard: middle must be curled (not up) — blocks peace sign misfire.
        No index_curled check needed — pinch distance alone proves the bend.
        """
        if lm[config.MID_TIP].y < lm[config.MID_PIP].y:
            return False  # middle is up → peace sign or pointing, not a click

        dist = self._dist(lm, config.THUMB_TIP, config.INDEX_TIP)
        if dist < config.LCLICK_THRESHOLD:
            now = time.time()
            if now - self._last_lclick_time >= config.CLICK_COOLDOWN:
                self._last_lclick_time = now
                return True
        return False


    def _is_right_click(self, lm):
        """
        RIGHT CLICK — Deliberate, less frequent.
        Pinch thumb (#4) to middle tip (#12). Threshold: RCLICK_THRESHOLD=0.10

        WHY 0.10 not 0.05:
          Thumb travels further to reach middle than index — geometry means
          the natural pinch distance is ~0.09-0.11 not ~0.03-0.05.
          Using 0.05 meant it NEVER fired. 0.10 matches actual hand geometry.

        Guard logic — TWO conditions must hold:
          1. Index NOT pointing up (tip below PIP) — rules out pointing pose
          2. Thumb-to-index distance > LCLICK_THRESHOLD — not doing left click
        This ensures right click is a completely distinct pose.

        Gesture: relax fingers, curl index, bring thumb to middle fingertip.
        """
        # Guard 1: index must not be pointing up
        if lm[config.INDEX_TIP].y < lm[config.INDEX_PIP].y:
            return False

        # Guard 2: must NOT also be doing a left click pose
        l_dist = self._dist(lm, config.THUMB_TIP, config.INDEX_TIP)
        if l_dist < config.LCLICK_THRESHOLD:
            return False  # left click takes priority

        # Main check: thumb close to middle finger tip
        r_dist = self._dist(lm, config.THUMB_TIP, config.MID_TIP)
        if r_dist < config.RCLICK_THRESHOLD:
            now = time.time()
            if now - self._last_rclick_time >= config.CLICK_COOLDOWN:
                self._last_rclick_time = now
                return True
        return False


    # =========================================================================
    # HELPERS
    # =========================================================================

    @staticmethod
    def _dist(lm, a, b):
        dx = lm[a].x - lm[b].x
        dy = lm[a].y - lm[b].y
        return math.sqrt(dx * dx + dy * dy)


    def get_debug_info(self, lm):
        if lm is None:
            return {}
        return {
            "index_up"   : lm[config.INDEX_TIP].y < lm[config.INDEX_PIP].y,
            "middle_up"  : lm[config.MID_TIP].y   < lm[config.MID_PIP].y,
            "L-dist"     : round(self._dist(lm, config.THUMB_TIP, config.INDEX_TIP), 3),
            "R-dist"     : round(self._dist(lm, config.THUMB_TIP, config.MID_TIP),   3),
            "L-thresh"   : config.LCLICK_THRESHOLD,
            "R-thresh"   : config.RCLICK_THRESHOLD,
        }


# =============================================================================
# STANDALONE TEST — python3 gesture_classifier.py
# Watch R-dist live — it needs to drop below R-thresh (0.10) to right click
# =============================================================================
if __name__ == "__main__":
    import cv2
    from hand_detector import HandDetector

    print("=" * 58)
    print("  GESTURE TEST — watch debug panel on right side")
    print("  L-dist must drop below L-thresh → LEFT_CLICK")
    print("  R-dist must drop below R-thresh → RIGHT_CLICK")
    print("  RIGHT CLICK pose: curl index, bring thumb to middle")
    print("  Press Q to quit.")
    print("=" * 58)

    detector   = HandDetector()
    classifier = GestureClassifier()
    prev_time  = time.time()

    COLOURS = {
        "POINT"       : (0,   220,  0),
        "SCROLL"      : (0,   200, 255),
        "LEFT_CLICK"  : (0,   165, 255),
        "RIGHT_CLICK" : (255, 100,  50),
        "FIST"        : (0,   0,   220),
        "NONE"        : (150, 150, 150),
    }

    while True:
        landmarks, frame, hand_found = detector.get_landmarks(draw=True)
        curr_time = time.time()
        fps = 1.0 / max(curr_time - prev_time, 1e-6)
        prev_time = curr_time
        h, w = frame.shape[:2]

        cv2.putText(frame, f"FPS: {fps:.1f}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, config.HUD_YELLOW, 2)

        gesture = classifier.classify(landmarks)
        colour  = COLOURS.get(gesture, config.HUD_WHITE)
        lbl_w   = cv2.getTextSize(gesture, cv2.FONT_HERSHEY_SIMPLEX,
                                   1.3, 3)[0][0]
        cv2.putText(frame, gesture, ((w - lbl_w) // 2, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.3, colour, 3)

        if hand_found:
            dbg = classifier.get_debug_info(landmarks)

            # Colour L-dist red when below threshold
            ld_col = config.HUD_RED if dbg['L-dist'] < dbg['L-thresh'] \
                     else config.HUD_WHITE
            rd_col = config.HUD_RED if dbg['R-dist'] < dbg['R-thresh'] \
                     else config.HUD_WHITE

            panel = [
                (f"index_up  : {dbg['index_up']}",  config.HUD_WHITE),
                (f"middle_up : {dbg['middle_up']}", config.HUD_WHITE),
                (f"L-dist    : {dbg['L-dist']}",    ld_col),
                (f"L-thresh  : {dbg['L-thresh']}",  config.HUD_WHITE),
                (f"R-dist    : {dbg['R-dist']}",    rd_col),
                (f"R-thresh  : {dbg['R-thresh']}",  config.HUD_WHITE),
            ]
            for i, (line, col) in enumerate(panel):
                cv2.putText(frame, line, (w - 270, 30 + i * 26),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.52, col, 1)
        else:
            cv2.putText(frame, "No hand detected",
                        (10, 100), cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, config.HUD_RED, 2)

        cv2.putText(frame, "Q to quit",
                    (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, config.HUD_WHITE, 1)

        cv2.imshow(config.WINDOW_NAME, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    detector.release()
    cv2.destroyAllWindows()
