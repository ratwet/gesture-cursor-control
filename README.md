# Gesture Cursor Control

> Control your mouse cursor with hand gestures using a webcam — real-time finger tracking with MediaPipe, OpenCV & Python. Wayland-native on Ubuntu. No mouse needed.

![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.35-orange?style=flat-square)
![OpenCV](https://img.shields.io/badge/OpenCV-4.13-green?style=flat-square&logo=opencv)
![Platform](https://img.shields.io/badge/Platform-Ubuntu%2024.04-purple?style=flat-square&logo=ubuntu)
</p>
<br/>
<img src="assets/asssetsimage.png" width="520" alt="Images" />
</div>

---

## Demo

```
☝️  Point index finger    →  Move cursor
🤏  Pinch thumb + index   →  Left click
🤏  Pinch thumb + middle  →  Right click
✌️  Peace sign + move     →  Scroll up / down
✊  Fist                  →  Freeze cursor
```

---

## Features

- **Real-time** — runs at ~40 FPS on a standard laptop CPU, no GPU needed
- **5 gestures** — move, left click, right click, scroll, freeze
- **Wayland native** — uses Linux `evdev + uinput` kernel module (works where PyAutoGUI fails)
- **Jitter-free** — weighted moving average smoother with velocity cap
- **Modular** — 6 clean Python files, each with a single responsibility
- **Zero training** — uses Google's pre-trained MediaPipe model, no dataset needed

---

## How It Works

```
📷 Webcam
    ↓  BGR frames (640×480)
OpenCV
    ↓  RGB frame
MediaPipe HandLandmarker
    ↓  21 normalised (x, y, z) landmarks
Gesture Classifier
    ↓  "POINT" / "LEFT_CLICK" / "RIGHT_CLICK" / "SCROLL" / "FIST"
Smoother (Weighted Moving Average)
    ↓  Jitter-free (x, y) position
Cursor Controller (evdev)
    ↓  Linux kernel input events
🖥️  Ubuntu Screen
```

---

## Project Structure

```
gesture-cursor-control/
│
├── config.py               # All settings & thresholds (edit this to tune)
├── hand_detector.py        # MediaPipe HandLandmarker wrapper
├── gesture_classifier.py   # Rule-based gesture detection
├── smoother.py             # Weighted moving average + velocity cap
├── cursor_controller.py    # evdev virtual mouse (Wayland compatible)
├── main.py                 # Entry point — wires all modules together
├── hand_landmarker.task    # MediaPipe model file (download separately)
└── requirements.txt        # Python dependencies
```

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Ubuntu 20.04 | Ubuntu 24.04 LTS |
| Display | X11 or Wayland | Wayland |
| Python | 3.10+ | 3.12 |
| Camera | 720p webcam | 1080p built-in |
| RAM | 4 GB | 8 GB |
| CPU | Dual-core 1.8 GHz | Intel i5 11th Gen+ |
| GPU | Not required | Not required |

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/gesture-cursor-control.git
cd gesture-cursor-control
```

### 2. Create virtual environment

```bash
python3 -m venv ~/gesture_env
source ~/gesture_env/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Download the MediaPipe model

```bash
wget -O hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
```

### 5. Set up uinput permissions (Wayland cursor control)

```bash
# Allow access to uinput device
sudo chmod 666 /dev/uinput

# Make it permanent across reboots
echo 'KERNEL=="uinput", MODE="0666"' | sudo tee /etc/udev/rules.d/99-uinput.rules
sudo udevadm control --reload-rules
```

---

## Usage

```bash
# Activate environment
source ~/gesture_env/bin/activate

# Run (uinput permission required each boot unless udev rule is set)
sudo chmod 666 /dev/uinput

# Start gesture control
python3 main.py
```

Press **`Q`** or **`Ctrl+C`** to quit cleanly.

---

## 🖐️ Gesture Guide

| Gesture | Hand Pose | Action |
|---------|-----------|--------|
| **POINT** | Index finger up, others curled | Move cursor |
| **LEFT CLICK** | Thumb touches index tip (pinch), middle curled | Left mouse click |
| **RIGHT CLICK** | Curl index in, thumb touches middle tip | Right mouse click |
| **SCROLL** | Peace sign ✌️ — move hand up or down | Scroll page |
| **FIST** | All fingers curled into palm | Freeze cursor |

> **Tip:** Run `python3 gesture_classifier.py` first to see gesture labels and debug values live before using `main.py`.

---

## Configuration

All tunable parameters live in **`config.py`**:

```python
# Cursor speed — increase if cursor moves too slowly
MOVE_SENSITIVITY  = 1.3

# Click sensitivity — decrease if clicks fire too easily
LCLICK_THRESHOLD  = 0.05   # Left click  (thumb ↔ index)
RCLICK_THRESHOLD  = 0.10   # Right click (thumb ↔ middle)

# Cooldown between clicks in seconds
CLICK_COOLDOWN    = 0.8

# Smoothing — increase for less jitter, decrease for faster response
SMOOTHING_FRAMES  = 6

# Camera device index
CAMERA_INDEX      = 0      # Try 2 if camera doesn't open
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `PermissionError: /dev/uinput` | Run `sudo chmod 666 /dev/uinput` |
| Camera won't open | Change `CAMERA_INDEX = 2` in `config.py` |
| `hand_landmarker.task not found` | Download the model file (see Installation step 4) |
| Right click not firing | Run `gesture_classifier.py`, watch `R-dist` — must drop below `R-thresh (0.10)` |
| Cursor too shaky | Increase `SMOOTHING_FRAMES` to 8–10 in `config.py` |
| Cursor too slow | Increase `MOVE_SENSITIVITY` to 1.5–2.0 in `config.py` |
| Accidental clicks while pointing | Increase `LCLICK_THRESHOLD` to 0.07 in `config.py` |

---

## Dependencies

```txt
opencv-python>=4.8.0
mediapipe>=0.10.13
numpy>=1.23.0
evdev>=1.6.0
```

Install all with:
```bash
pip install -r requirements.txt
```

> **Note:** MediaPipe 0.10.13+ (Python 3.12) uses the Tasks API. The old `mp.solutions.hands` API was removed. This project uses the new `HandLandmarker` API exclusively.

---

## Architecture Details

### MediaPipe Hand Landmarks
MediaPipe detects **21 3D landmark points** per hand. Key points used in this project:

```
Landmark #4  → Thumb tip      (click detection)
Landmark #8  → Index tip      (cursor position)
Landmark #12 → Middle tip     (right click + scroll)
Landmark #6  → Index PIP      (finger state — extended/curled)
```

### Wayland Compatibility
PyAutoGUI uses X11's XTEST extension — unavailable on Wayland. This project creates a **virtual mouse device** via the Linux kernel's `uinput` module using `evdev`:

```python
from evdev import UInput, ecodes as e
ui = UInput({
    e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL],
    e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT],
}, name="gesture-cursor-control")
```

This operates below the display server layer — fully compatible with all Wayland compositors.

### Smoothing Algorithm
Weighted moving average over the last 6 frames:
```
Weights: [1, 2, 3, 4, 5, 6]  →  recent frames count more
+ Velocity cap: max 0.08 normalised units per frame (blocks sudden jumps)
Result: ~60% jitter reduction vs raw landmarks
```

---

## Performance

| Metric | Value |
|--------|-------|
| Frame rate | ~40 FPS |
| End-to-end latency | < 25 ms |
| RAM usage | ~300 MB |
| CPU load | < 50% (one core) |
| Jitter reduction | ~60% |
| GPU required | No |

*Tested on Dell Latitude 5420 — Intel Core i5-1145G7, 8GB RAM, Ubuntu 24.04.*

---

## Acknowledgements

- [Google MediaPipe](https://ai.google.dev/edge/mediapipe) — Hand landmark detection model
- [OpenCV](https://opencv.org) — Computer vision framework
- [python-evdev](https://python-evdev.readthedocs.io) — Linux input device interface
- [NumPy](https://numpy.org) — Numerical computing
