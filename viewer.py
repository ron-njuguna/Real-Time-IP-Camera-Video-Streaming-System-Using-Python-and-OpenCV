import sys
import time

import cv2
import numpy as np

from camera import CameraError, check_reachable, mask_url, open_capture, parse_source
from config import ConfigError, load_config
from processing import (FpsEstimator, draw_overlay, draw_status, resize_to_width,
                        timestamped_path)
from recorder import Recorder, RecorderError

WINDOW = "IP Camera Viewer"
ESC = 27
CONTROLS = "Controls: Esc = quit | S = screenshot | R = start/stop recording"


class QuitRequested(Exception):
    """Raised when Esc is pressed while we are busy reconnecting."""


def connect(source):
    """Check reachability, open the stream and confirm a frame can be read."""
    content_type = check_reachable(source)
    cap = open_capture(source)
    ok, _ = cap.read()
    if not ok:
        cap.release()
        raise CameraError("The camera answered but sent no video frames.")
    return cap, content_type


def wait_with_status(seconds, message):
    """Show a status screen while waiting, staying responsive. True if Esc pressed."""
    screen = np.zeros((360, 640, 3), np.uint8)
    cv2.putText(screen, message, (30, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                (0, 200, 255), 2, cv2.LINE_AA)
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        cv2.imshow(WINDOW, screen)
        if cv2.waitKey(100) & 0xFF == ESC:
            return True
    return False


def reconnect(source, cfg):
    """Limited reconnect attempts with exponential back-off (1s, 2s, 4s, 8s, 8s)."""
    for attempt in range(1, cfg.max_reconnects + 1):
        delay = min(cfg.reconnect_delay * 2 ** (attempt - 1), cfg.reconnect_max_delay)
        print(f"Connection lost - reconnect attempt {attempt}/{cfg.max_reconnects} in {delay:.0f}s ...")
        if wait_with_status(delay, f"Reconnecting ({attempt}/{cfg.max_reconnects})..."):
            raise QuitRequested
        try:
            cap, _ = connect(source)
            print("Reconnected.")
            return cap
        except CameraError as exc:
            print(f"  attempt {attempt} failed: {exc}")
    raise CameraError(f"Could not reconnect after {cfg.max_reconnects} attempts. Giving up.")


def run(cfg):
    """Main loop. Returns a process exit code (0 = normal, 1 = error)."""
    recorder = Recorder()
    cap = None
    fps = FpsEstimator()
    toast, toast_until = "", 0.0
    failed_reads = 0
    exit_code = 0
    try:
        source = parse_source(cfg.camera_url)
        print(f"Connecting to {mask_url(cfg.camera_url)} ...")
        cap, content_type = connect(source)
        print(f"Connected (stream type: {content_type or 'n/a'}).")
        print(CONTROLS)
        cv2.namedWindow(WINDOW)

        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                failed_reads += 1
                if failed_reads < cfg.max_failed_reads:
                    if cv2.waitKey(20) & 0xFF == ESC:
                        raise QuitRequested
                    continue
                print("Lost the video stream.")
                cap.release()
                cap = None
                cap = reconnect(source, cfg)
                failed_reads = 0
                fps.reset()
                continue
            failed_reads = 0

            src_h, src_w = frame.shape[:2]
            shown = resize_to_width(frame, cfg.display_width)
            draw_overlay(shown, cfg.camera_name, fps.tick(), (src_w, src_h))

            if recorder.is_recording:
                try:
                    recorder.write(shown)
                except cv2.error:
                    path = recorder.stop()
                    print(f"Recording stopped after a write error; saved {path}")
                    toast, toast_until = "Recording error - stopped", time.monotonic() + 3

            display = shown.copy()  # status text is drawn on a copy so it is not recorded
            now = time.monotonic()
            draw_status(display,
                        recorder.elapsed() if recorder.is_recording else None,
                        toast if now < toast_until else "")
            cv2.imshow(WINDOW, display)

            key = cv2.waitKey(1) & 0xFF
            if key == ESC:
                print("Esc pressed - shutting down.")
                break
            if key in (ord("s"), ord("S")):
                path = timestamped_path(cfg.screenshots_dir, "screenshot", "jpg")
                if cv2.imwrite(str(path), shown):
                    print(f"Screenshot saved: {path}")
                    toast, toast_until = f"Saved {path.name}", now + 2
                else:
                    toast, toast_until = "Screenshot failed", now + 2
            elif key in (ord("r"), ord("R")):
                if recorder.is_recording:
                    path = recorder.stop()
                    print(f"Recording saved: {path}")
                    toast, toast_until = f"Recording saved: {path.name}", now + 3
                else:
                    try:
                        rate = min(30.0, max(5.0, fps.fps)) if fps.fps else 20.0
                        path = recorder.start((shown.shape[1], shown.shape[0]), rate,
                                              cfg.recordings_dir)
                        print(f"Recording started: {path}")
                    except RecorderError as exc:
                        print(f"Error: {exc}")
                        toast, toast_until = "Cannot start recording", now + 3
    except QuitRequested:
        print("Esc pressed - shutting down.")
    except KeyboardInterrupt:
        print("\nCtrl+C - shutting down.")
    except CameraError as exc:
        print(f"Error: {exc}")
        exit_code = 1
    except Exception as exc:  # last resort: explain, do not dump a traceback
        print(f"Unexpected error ({type(exc).__name__}): {exc}")
        exit_code = 1
    finally:
        # Runs on every way out: Esc, Ctrl+C, errors.
        try:
            saved = recorder.stop()
            if saved:
                print(f"Recording finished and saved: {saved}")
        except Exception:
            pass
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()
        print("Camera released. Goodbye.")
    return exit_code


def main():
    try:
        cfg = load_config()
    except ConfigError as exc:
        print(f"Configuration error: {exc}")
        return 2
    return run(cfg)


if __name__ == "__main__":
    sys.exit(main())
