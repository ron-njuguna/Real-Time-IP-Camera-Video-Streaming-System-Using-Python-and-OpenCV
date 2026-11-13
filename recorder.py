"""Video recording with cv2.VideoWriter."""
import time

import cv2

from processing import timestamped_path


class RecorderError(Exception):
    """The recording could not be started or written."""


class Recorder:
    def __init__(self):
        self._writer = None
        self._size = None
        self._started = 0.0
        self.path = None

    @property
    def is_recording(self):
        return self._writer is not None

    def elapsed(self):
        return time.monotonic() - self._started if self.is_recording else 0.0

    def start(self, frame_size, fps, directory):
        """frame_size is (width, height) - VideoWriter silently drops other sizes."""
        path = timestamped_path(directory, "recording", "mp4")
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, frame_size)
        if not writer.isOpened():
            writer.release()
            raise RecorderError("Could not create the video file (codec not available?).")
        self._writer, self._size, self.path = writer, frame_size, path
        self._started = time.monotonic()
        return path

    def write(self, frame):
        h, w = frame.shape[:2]
        if (w, h) != self._size:
            frame = cv2.resize(frame, self._size)
        self._writer.write(frame)

    def stop(self):
        """Finish the file. Safe to call when not recording."""
        path = self.path if self.is_recording else None
        if self._writer is not None:
            self._writer.release()
        self._writer = None
        return path
