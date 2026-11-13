"""Camera helpers: URL validation, a reachability check and opening the stream."""
import re
from urllib.parse import urlparse

import cv2
import requests


class CameraError(Exception):
    """A camera problem that should be explained to the user (no traceback)."""


_CREDENTIALS = re.compile(r"(?<=//)[^/@\s]+@")


def mask_url(url):
    """Hide any user:password@ part so secrets never reach the screen or logs."""
    return _CREDENTIALS.sub("***:***@", str(url))


def parse_source(url):
    """Validate the configured source.

    Returns an int for a local webcam index ("0"), otherwise the URL string.
    Raises CameraError for an invalid URL.
    """
    url = url.strip()
    if url.isdigit():
        return int(url)
    parts = urlparse(url)
    if parts.scheme not in ("http", "https", "rtsp"):
        raise CameraError(
            "Invalid camera URL: it must start with http://, https:// or rtsp:// "
            f"(got '{mask_url(url)}')."
        )
    if not parts.hostname:
        raise CameraError("Invalid camera URL: no host / IP address found.")
    try:
        _ = parts.port
    except ValueError:
        raise CameraError("Invalid camera URL: the port must be a number (0-65535).")
    return url


def check_reachable(source, timeout=5.0):
    """Ask the camera for its headers over HTTP before handing the URL to OpenCV.

    Returns the Content-Type header (an MJPEG stream shows
    'multipart/x-mixed-replace'), or None when the check does not apply
    (webcam index or RTSP, which is not HTTP).
    """
    if not isinstance(source, str) or source.startswith("rtsp://"):
        return None
    try:
        response = requests.get(source, stream=True, timeout=timeout)
    except requests.exceptions.ConnectTimeout:
        raise CameraError(
            "The camera did not answer in time. Is it switched on, and are the "
            "computer and camera on the same Wi-Fi network?"
        )
    except requests.exceptions.ReadTimeout:
        raise CameraError("The camera accepted the connection but sent nothing.")
    except (requests.exceptions.InvalidURL, requests.exceptions.MissingSchema,
            requests.exceptions.InvalidSchema):
        raise CameraError("Invalid camera URL. Check the address in your .env file.")
    except requests.exceptions.ConnectionError:
        raise CameraError(
            "Camera unavailable: nothing is listening at that address/port. Check "
            "that the camera app's server is running, the IP address is current and "
            "the port number is right."
        )
    except requests.exceptions.RequestException as exc:
        raise CameraError(f"Network error while contacting the camera ({type(exc).__name__}).")
    try:
        if response.status_code in (401, 403):
            raise CameraError("The camera refused access: check the username/password in the URL.")
        if response.status_code >= 500:
            raise CameraError(
                f"The camera reported a server error (HTTP {response.status_code}). "
                "It may be restarting or overloaded."
            )
        if response.status_code >= 400:
            raise CameraError(
                f"The camera answered with HTTP status {response.status_code}. "
                "Check the path at the end of the URL (for example /video)."
            )
        return response.headers.get("Content-Type", "unknown")
    finally:
        response.close()


def open_capture(source, timeout_ms=5000):
    """Open the stream with OpenCV, with timeouts so a dead camera cannot hang us."""
    if isinstance(source, str):
        try:
            cap = cv2.VideoCapture(
                source, cv2.CAP_FFMPEG,
                [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms,
                 cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_ms],
            )
        except (TypeError, cv2.error):  # older OpenCV without the params overload
            cap = cv2.VideoCapture(source)
    else:
        cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        cap.release()
        raise CameraError("OpenCV could not open the video stream at that address.")
    return cap
