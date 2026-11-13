"""Per-frame processing: resizing, FPS estimate, overlays and file naming."""
import time
from datetime import datetime
from pathlib import Path

import cv2

FONT = cv2.FONT_HERSHEY_SIMPLEX


def resize_to_width(frame, width):
    """Resize to a fixed width, keeping the aspect ratio (always returns a new array)."""
    h, w = frame.shape[:2]
    new_h = max(1, round(h * width / w))
    return cv2.resize(frame, (width, new_h), interpolation=cv2.INTER_AREA)


class FpsEstimator:
    """FPS from the time between frames, smoothed with an exponential average.

    The raw 1/dt value jumps around because network frames arrive unevenly;
    averaging it makes the on-screen number readable.
    """

    def __init__(self, smoothing=0.9):
        self.smoothing = smoothing
        self.fps = 0.0
        self._last = None

    def tick(self, now=None):
        now = time.perf_counter() if now is None else now
        if self._last is not None and now > self._last:
            instant = 1.0 / (now - self._last)
            self.fps = instant if self.fps == 0 else (
                self.smoothing * self.fps + (1 - self.smoothing) * instant)
        self._last = now
        return self.fps

    def reset(self):
        self.fps, self._last = 0.0, None


def put_text(frame, text, org, color=(255, 255, 255), scale=0.6, thickness=1):
    """Text with a dark outline so it stays readable on any background."""
    cv2.putText(frame, text, org, FONT, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(frame, text, org, FONT, scale, color, thickness, cv2.LINE_AA)


def draw_overlay(frame, camera_name, fps, source_size, now=None):
    """Timestamp, camera name, resolution of the shown frame and FPS."""
    now = now or datetime.now()
    h, w = frame.shape[:2]
    put_text(frame, now.strftime("%Y-%m-%d %H:%M:%S"), (10, 24))
    put_text(frame, camera_name, (10, 48), color=(0, 255, 255))
    put_text(frame, f"{w}x{h} (source {source_size[0]}x{source_size[1]})  {fps:4.1f} FPS",
             (10, h - 12))


def format_elapsed(seconds):
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def draw_status(frame, recording_seconds=None, toast=""):
    """Red REC indicator (top-right) and a short confirmation message (bottom)."""
    h, w = frame.shape[:2]
    if recording_seconds is not None:
        label = f"REC {format_elapsed(recording_seconds)}"
        cv2.circle(frame, (w - 120, 20), 8, (0, 0, 255), -1)
        put_text(frame, label, (w - 105, 26), color=(0, 0, 255), scale=0.6, thickness=2)
    if toast:
        put_text(frame, toast, (10, h - 40), color=(0, 255, 0), scale=0.6, thickness=2)


def timestamped_path(directory, prefix, ext, now=None):
    """e.g. screenshots/screenshot_20261113_123045.jpg ; never overwrites a file.

    The folder is created if missing. If the name already exists (two saves in
    the same second) a counter is added: ..._1, ..._2 and so on.
    """
    now = now or datetime.now()
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"{prefix}_{now:%Y%m%d_%H%M%S}"
    path = folder / f"{stem}.{ext}"
    counter = 1
    while path.exists():
        path = folder / f"{stem}_{counter}.{ext}"
        counter += 1
    return path
