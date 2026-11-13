import argparse
import time

import cv2
import numpy as np
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ARGS = None
START = time.monotonic()


def make_frame(t, w=1280, h=720):
    img = np.full((h, w, 3), (45, 35, 25), np.uint8)
    x = int((np.sin(t) * 0.4 + 0.5) * w)
    cv2.circle(img, (x, h // 2), 50, (0, 200, 255), -1)
    cv2.putText(img, "MOCK CAMERA", (40, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    cv2.putText(img, f"t = {t:6.1f}s", (40, 160), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)
    return img


def in_outage():
    if ARGS.outage_after is None:
        return False
    elapsed = time.monotonic() - START
    return ARGS.outage_after <= elapsed < ARGS.outage_after + ARGS.outage_for


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if in_outage():
            self.send_error(503, "Simulated outage")
            return
        if self.path != "/video":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Mock camera. Stream is at /video\n")
            return
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        try:
            while not in_outage():
                ok, jpg = cv2.imencode(".jpg", make_frame(time.monotonic() - START))
                self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n"
                                 + f"Content-Length: {len(jpg)}\r\n\r\n".encode()
                                 + jpg.tobytes() + b"\r\n")
                time.sleep(1.0 / ARGS.fps)
        except (BrokenPipeError, ConnectionResetError):
            pass


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--fps", type=float, default=15)
    p.add_argument("--outage-after", type=float, default=None, help="seconds until a simulated outage")
    p.add_argument("--outage-for", type=float, default=10, help="outage length in seconds")
    ARGS = p.parse_args()
    print(f"Mock camera at http://127.0.0.1:{ARGS.port}/video  (Ctrl+C to stop)")
    try:
        ThreadingHTTPServer(("127.0.0.1", ARGS.port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
