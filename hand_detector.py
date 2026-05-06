# =============================================================================
# hand_detector.py — Hand Landmark Detection (MediaPipe Tasks API v0.10.13+)
# =============================================================================
# Uses the NEW MediaPipe Tasks API (mp.solutions was removed in 0.10.13+).
#
# REQUIRES: hand_landmarker.task model file in the same folder.
# Download it once with:
#   wget -O hand_landmarker.task \
#   https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
#
# What this module does:
#   1. Opens the webcam
#   2. Reads frames continuously
#   3. Detects hand landmarks using MediaPipe HandLandmarker (Tasks API)
#   4. Returns 21 landmark points per hand
#   5. Draws the hand skeleton on the frame
#
# Standalone test:
#   python3 hand_detector.py
# =============================================================================

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import time
import os
import sys
import config

# -----------------------------------------------------------------------------
# Hand skeleton connections (21 landmarks, MediaPipe topology)
# Used for manual drawing since mp.solutions.drawing_utils was removed
# -----------------------------------------------------------------------------
HAND_CONNECTIONS = [
    (0, 1),  (1, 2),  (2, 3),  (3, 4),    # Thumb
    (0, 5),  (5, 6),  (6, 7),  (7, 8),    # Index finger
    (5, 9),  (9, 10), (10, 11),(11, 12),   # Middle finger
    (9, 13), (13, 14),(14, 15),(15, 16),   # Ring finger
    (13,17), (17, 18),(18, 19),(19, 20),   # Pinky
    (0, 17),                               # Palm base
]


class HandDetector:
    """
    Detects hand landmarks using MediaPipe Tasks API (HandLandmarker).

    Attributes
    ----------
    cap        : cv2.VideoCapture  — webcam handle
    landmarker : HandLandmarker    — MediaPipe Tasks landmark detector
    start_time : float             — used for VIDEO mode timestamps
    """

    MODEL_FILENAME = "hand_landmarker.task"

    def __init__(self):
        # ── Locate model file ─────────────────────────────────────────────────
        model_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            self.MODEL_FILENAME
        )
        if not os.path.exists(model_path):
            print(f"\n❌ Model file not found: {model_path}")
            print("   Download it once with this command (run in ~/gesture_cursor/):\n")
            print("   wget -O hand_landmarker.task \\")
            print("   https://storage.googleapis.com/mediapipe-models/"
                  "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task\n")
            sys.exit(1)

        # ── Webcam setup ──────────────────────────────────────────────────────
        self.cap = cv2.VideoCapture(config.CAMERA_INDEX)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

        if not self.cap.isOpened():
            raise RuntimeError(
                f"❌ Cannot open camera index {config.CAMERA_INDEX}. "
                "Try CAMERA_INDEX = 2 in config.py"
            )

        # ── MediaPipe Tasks — HandLandmarker setup ────────────────────────────
        options = mp_vision.HandLandmarkerOptions(
            base_options = mp_python.BaseOptions(
                               model_asset_path=model_path),
            running_mode = mp_vision.RunningMode.VIDEO,
            num_hands    = config.MAX_HANDS,
            min_hand_detection_confidence = config.DETECTION_CONF,
            min_hand_presence_confidence  = config.TRACKING_CONF,
            min_tracking_confidence       = config.TRACKING_CONF,
        )
        self.landmarker = mp_vision.HandLandmarker.create_from_options(options)
        self.start_time = time.time()

        print(f"✅ Camera opened   → /dev/video{config.CAMERA_INDEX} "
              f"({config.FRAME_WIDTH}×{config.FRAME_HEIGHT})")
        print(f"✅ Model loaded    → {self.MODEL_FILENAME}")
        print(f"✅ MediaPipe ready → max_hands={config.MAX_HANDS}, "
              f"detection={config.DETECTION_CONF}, tracking={config.TRACKING_CONF}")


    def get_landmarks(self, draw=True):
        """
        Read one webcam frame and detect hand landmarks.

        Parameters
        ----------
        draw : bool
            Draw hand skeleton on the returned frame if True.

        Returns
        -------
        landmarks  : list of 21 NormalizedLandmark  (or None if no hand)
            landmarks[i].x  — normalised x position [0.0–1.0]
            landmarks[i].y  — normalised y position [0.0–1.0]
            landmarks[i].z  — relative depth

        frame      : np.ndarray BGR — annotated camera frame
        hand_found : bool           — True if a hand was detected
        """
        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("❌ Failed to read frame from camera.")

        # Mirror for natural feel
        if config.FLIP_CAMERA:
            frame = cv2.flip(frame, 1)

        # Convert BGR → RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Wrap in MediaPipe Image
        mp_image = mp.Image(
            image_format = mp.ImageFormat.SRGB,
            data         = rgb_frame
        )

        # VIDEO mode needs monotonically increasing timestamp in ms
        timestamp_ms = int((time.time() - self.start_time) * 1000)

        # Run detection
        result = self.landmarker.detect_for_video(mp_image, timestamp_ms)

        landmarks  = None
        hand_found = False

        if result.hand_landmarks:
            hand_found = True
            landmarks  = result.hand_landmarks[0]  # list of 21 NormalizedLandmark

            if draw:
                self._draw_landmarks(frame, landmarks)

        return landmarks, frame, hand_found


    def _draw_landmarks(self, frame, landmarks):
        """
        Draw 21 landmark dots + connections on frame.
        (Manual draw — mp.solutions.drawing_utils removed in 0.10.13+)
        """
        h, w = frame.shape[:2]

        # Normalised [0,1] → pixel coordinates
        pts = [
            (int(lm.x * w), int(lm.y * h))
            for lm in landmarks
        ]

        # Draw connections first so dots appear on top
        for (a, b) in HAND_CONNECTIONS:
            cv2.line(frame, pts[a], pts[b],
                     config.LANDMARK_LINE_COLOR, 2)

        # Draw landmark dots — fingertips get bigger dots
        for i, (px, py) in enumerate(pts):
            radius = 6 if i in (4, 8, 12, 16, 20) else 4
            cv2.circle(frame, (px, py), radius,
                       config.LANDMARK_DOT_COLOR, -1)

        # Cyan dot on index fingertip (landmark 8) = future cursor position
        cv2.circle(frame, pts[config.INDEX_TIP], 10, (0, 255, 255), -1)


    def release(self):
        """Release camera and MediaPipe resources cleanly."""
        self.cap.release()
        self.landmarker.close()
        print("🛑 Camera released.")


# =============================================================================
# STANDALONE TEST — python3 hand_detector.py
# =============================================================================
if __name__ == "__main__":
    print("=" * 55)
    print("  PHASE 1 TEST — Hand Detector (Tasks API)")
    print("  Show your hand to the camera.")
    print("  Press  Q  to quit.")
    print("=" * 55)

    detector  = HandDetector()
    prev_time = time.time()

    while True:
        landmarks, frame, hand_found = detector.get_landmarks(draw=True)

        # FPS
        curr_time = time.time()
        fps       = 1.0 / max(curr_time - prev_time, 1e-6)
        prev_time = curr_time

        h, w = frame.shape[:2]

        # FPS
        cv2.putText(frame, f"FPS: {fps:.1f}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, config.HUD_YELLOW, 2)

        if hand_found:
            cv2.putText(frame, "HAND DETECTED",
                        (10, 65), cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, config.HUD_GREEN, 2)

            tip   = landmarks[config.INDEX_TIP]
            thumb = landmarks[config.THUMB_TIP]

            cv2.putText(frame,
                        f"Index tip  x:{tip.x:.2f}  y:{tip.y:.2f}",
                        (10, 100), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, config.HUD_WHITE, 1)
            cv2.putText(frame,
                        f"Thumb tip  x:{thumb.x:.2f}  y:{thumb.y:.2f}",
                        (10, 125), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, config.HUD_WHITE, 1)

            # Pinch distance preview (useful when we test Phase 2)
            dx   = tip.x - thumb.x
            dy   = tip.y - thumb.y
            dist = (dx**2 + dy**2) ** 0.5
            colour = config.HUD_RED if dist < config.CLICK_THRESHOLD \
                     else config.HUD_WHITE
            cv2.putText(frame,
                        f"Pinch dist: {dist:.3f}  "
                        f"{'<< CLICK!' if dist < config.CLICK_THRESHOLD else ''}",
                        (10, 150), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, colour, 1)

        else:
            cv2.putText(frame, "No hand — show hand to camera",
                        (10, 65), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, config.HUD_RED, 2)

        cv2.putText(frame, "Q to quit",
                    (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, config.HUD_WHITE, 1)

        cv2.imshow(config.WINDOW_NAME, frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("👋 Quitting...")
            break

    detector.release()
    cv2.destroyAllWindows()
    print("✅ Phase 1 test complete.")
