# =============================================================================
# smoother.py — Cursor Position Smoother (Weighted Moving Average)
# =============================================================================
# Removes hand tremor jitter from raw MediaPipe landmark coordinates.
#
# Two mechanisms:
#   1. Weighted moving average  — recent frames count more than old ones
#   2. Velocity cap             — ignores sudden large jumps (accidental moves)
#
# Usage:
#   smoother = Smoother()
#   smooth_x, smooth_y = smoother.smooth(raw_x, raw_y)
#
# Tune behaviour in config.py:
#   SMOOTHING_FRAMES  — buffer size (higher = smoother but more lag)
# =============================================================================

import collections
import numpy as np
import config


# Maximum allowed position change per frame (normalised [0,1] units).
# Jumps larger than this are capped — prevents cursor flying when
# hand accidentally moves fast or MediaPipe briefly mislabels a landmark.
MAX_JUMP = 0.08


class Smoother:
    """
    Smooths a stream of (x, y) positions using a weighted moving average.

    The most recent position gets the highest weight — so the cursor
    still follows your hand closely while tremors are filtered out.

    Methods
    -------
    smooth(x, y) -> (float, float)
        Pass raw normalised position, get smoothed position back.

    reset()
        Clear buffer — call when tracking resumes after FIST freeze.
    """

    def __init__(self, buffer_size=None):
        size = buffer_size or config.SMOOTHING_FRAMES

        # Ring buffer — holds last N (x, y) positions
        self._buf = collections.deque(maxlen=size)

        # Weights: [1, 2, 3, ... N] — recent positions weighted higher
        # Normalised so they sum to 1.0
        raw_w        = np.arange(1, size + 1, dtype=float)
        self._weights = raw_w / raw_w.sum()

        # Previous smoothed position — used for velocity cap
        self._prev_x = None
        self._prev_y = None

        print(f"✅ Smoother ready → buffer={size} frames, "
              f"max_jump={MAX_JUMP}")


    def smooth(self, x, y):
        """
        Smooth a new raw position reading.

        Parameters
        ----------
        x : float  raw normalised x from landmark [0.0–1.0]
        y : float  raw normalised y from landmark [0.0–1.0]

        Returns
        -------
        (smooth_x, smooth_y) : tuple of float
            Smoothed position, still in normalised [0.0–1.0] space.
        """
        # ── Velocity cap ──────────────────────────────────────────────────────
        # On the very first call there's no previous — accept any position
        if self._prev_x is not None:
            dx   = x - self._prev_x
            dy   = y - self._prev_y
            dist = (dx * dx + dy * dy) ** 0.5

            if dist > MAX_JUMP:
                # Scale the delta back to MAX_JUMP magnitude
                scale = MAX_JUMP / dist
                x     = self._prev_x + dx * scale
                y     = self._prev_y + dy * scale

        # ── Add to buffer ─────────────────────────────────────────────────────
        self._buf.append((x, y))
        self._prev_x = x
        self._prev_y = y

        # ── Weighted average ──────────────────────────────────────────────────
        arr = np.array(self._buf)           # shape: (N, 2)

        # Slice weights to match current buffer length
        # (buffer may not be full yet in first few frames)
        w = self._weights[-len(arr):]
        w = w / w.sum()                     # re-normalise for partial buffer

        smooth_x = float(np.dot(arr[:, 0], w))
        smooth_y = float(np.dot(arr[:, 1], w))

        return smooth_x, smooth_y


    def reset(self):
        """
        Clear the position buffer and previous position.
        Call this whenever tracking resumes after a FIST freeze —
        prevents the cursor snapping from the old frozen position.
        """
        self._buf.clear()
        self._prev_x = None
        self._prev_y = None


# =============================================================================
# STANDALONE TEST — python3 smoother.py
# Compares raw vs smoothed positions with simulated noisy hand data.
# =============================================================================
if __name__ == "__main__":
    import time
    import random

    print("=" * 55)
    print("  PHASE 4 TEST — Smoother")
    print("  Comparing raw vs smoothed positions.")
    print("=" * 55)

    smoother = Smoother()

    # Simulate hand hovering around (0.5, 0.5) with random tremor noise
    base_x, base_y = 0.50, 0.50
    noise          = 0.015   # ±1.5% normalised = ~14–29px at 1080p — realistic tremor

    print(f"\n{'Frame':>5}  {'Raw X':>7}  {'Raw Y':>7}  "
          f"{'Smooth X':>9}  {'Smooth Y':>9}  {'Delta':>7}")
    print("-" * 58)

    prev_sx, prev_sy = base_x, base_y

    for i in range(20):
        # Slowly drift right + random tremor
        raw_x = base_x + (i * 0.005) + random.uniform(-noise, noise)
        raw_y = base_y + random.uniform(-noise, noise)

        sx, sy = smoother.smooth(raw_x, raw_y)

        # Delta from previous smooth position — shows how much cursor actually moves
        delta = ((sx - prev_sx)**2 + (sy - prev_sy)**2) ** 0.5
        prev_sx, prev_sy = sx, sy

        print(f"{i+1:>5}  {raw_x:>7.4f}  {raw_y:>7.4f}  "
              f"{sx:>9.4f}  {sy:>9.4f}  {delta:>7.5f}")
        time.sleep(0.025)  # ~40fps simulation

    print()
    print("=" * 55)
    print("  Notice: smooth values change gradually vs jittery raw.")
    print("  Tune SMOOTHING_FRAMES in config.py to adjust lag vs stability.")
    print("=" * 55)

    # Test velocity cap with a sudden jump
    print("\n🔍 Velocity cap test:")
    s2 = Smoother(buffer_size=3)
    s2.smooth(0.50, 0.50)   # seed
    before = (0.50, 0.50)
    after_raw    = (0.95, 0.95)  # huge sudden jump
    after_smooth = s2.smooth(*after_raw)
    print(f"  Raw jump:     ({after_raw[0]:.2f}, {after_raw[1]:.2f})")
    print(f"  After cap:    ({after_smooth[0]:.3f}, {after_smooth[1]:.3f})")
    print(f"  Cap working:  {after_smooth[0] < 0.70} ✅" )

    print("\n✅ Phase 4 test complete.")
    print("   Smooth output confirmed — ready for Phase 5: main.py!")
