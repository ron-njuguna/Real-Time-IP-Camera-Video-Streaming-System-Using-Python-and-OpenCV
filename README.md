# IP Camera Viewer

**Features**
- Live video in a window, every frame resized to a fixed width (aspect ratio kept)
- Overlay: date/time, camera name, frame resolution, estimated FPS
- `S` saves a timestamped screenshot to `screenshots/` (with on-screen confirmation)
- `R` starts/stops a timestamped recording in `recordings/` (red REC + elapsed time while recording)
- Clear messages (no tracebacks) for an invalid URL, an unavailable camera, a dropped connection (limited automatic reconnects) and failed frame reads
- Clean shutdown on Esc, Ctrl+C or error: recording finished, camera released, windows closed


## Controls

| Key | Action |
|-----|--------|
| `Esc` | Quit |
| `S` | Save a screenshot |
| `R` | Start / stop recording |
| `Ctrl+C` (terminal) | Quit safely |

## Setup

Requires Python 3.10+.

```bash
git clone https://github.com/ron-njuguna/Real-Time-IP-Camera-Video-Streaming-System-Using-Python-and-OpenCV.git
cd Real-Time-IP-Camera-Video-Streaming-System-Using-Python-and-OpenCV
python -m venv venv
# Windows:  venv\Scripts\activate
# macOS/Linux:  source venv/bin/activate
pip install -r requirements.txt
```

## Configure the camera URL (never commit it)

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

Edit `.env` and set `CAMERA_URL` to the stream URL provided by your camera app.
Keep this value private and do not commit your `.env` file. For a laptop webcam,
set `CAMERA_URL=0`.

```
CAMERA_URL=
CAMERA_NAME=Camera 1
```

Enter your private stream URL as the value of `CAMERA_URL` in your local `.env` file.
`.env` is listed in `.gitignore`. You can also set `CAMERA_URL` as a normal environment variable instead (it takes priority over `.env`).

Optional settings: `DISPLAY_WIDTH` (default 960), `MAX_RECONNECTS` (5), `RECONNECT_DELAY` (1 second, doubles each try up to 8), `MAX_FAILED_READS` (5).

### Camera options
- **Android:** use an IP camera app and enter the stream URL it displays into `.env`.
- **iPhone:** use an app that serves an MJPEG-over-HTTP stream and enter the URL it displays into `.env`.
- **No phone?** Run the built-in test camera (below).

## Run

```bash
python viewer.py
```

### Try it without a camera
In one terminal, run `python mock_camera.py`. Set `CAMERA_URL` in `.env` to the local stream URL printed by the mock camera, then run `python viewer.py` in another terminal.
To demo the reconnect logic: `python mock_camera.py --outage-after 15 --outage-for 10`.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

## Files

| File | Purpose |
|------|---------|
| `viewer.py` | Main loop, key handling, reconnect logic, safe shutdown |
| `config.py` | Reads settings from environment / `.env` |
| `camera.py` | URL validation, Requests reachability check, `cv2.VideoCapture` opening, credential masking |
| `processing.py` | Resize, FPS estimate, overlays, timestamped file names |
| `recorder.py` | `cv2.VideoWriter` recording wrapper |
| `mock_camera.py` | Local fake MJPEG camera for testing |
| `test_viewer.py` | Unit tests |
| `.env.example` | Template for your private `.env` |
