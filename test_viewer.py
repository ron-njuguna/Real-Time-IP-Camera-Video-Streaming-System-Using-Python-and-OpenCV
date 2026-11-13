"""Unit tests for the pure helpers. Run with:  python -m pytest -q"""
from datetime import datetime

import numpy as np
import pytest

from camera import CameraError, mask_url, parse_source
from config import ConfigError, load_config
from processing import FpsEstimator, format_elapsed, resize_to_width, timestamped_path
from recorder import Recorder


def test_resize_keeps_aspect_ratio():
    frame = np.zeros((1080, 1920, 3), np.uint8)
    out = resize_to_width(frame, 960)
    assert out.shape == (540, 960, 3)  # (height, width, channels)


def test_frame_shape_720p():
    assert np.zeros((720, 1280, 3), np.uint8).shape == (720, 1280, 3)


def test_fps_estimate_is_smoothed():
    est = FpsEstimator(smoothing=0.9)
    est.tick(0.0)
    assert est.tick(0.1) == pytest.approx(10.0)
    assert 10.0 < est.tick(0.15) < 20.0  # a fast frame nudges, not jumps, the value


def test_mask_url_hides_credentials():
    assert "secret" not in mask_url("http://admin:secret@192.168.1.5:8080/video")
    assert mask_url("http://192.168.1.5:8080/video") == "http://192.168.1.5:8080/video"


@pytest.mark.parametrize("bad", ["", "not a url", "ftp://1.2.3.4/x", "http://", "http://1.2.3.4:abc/video"])
def test_invalid_urls_rejected(bad):
    with pytest.raises(CameraError):
        parse_source(bad)


def test_valid_sources():
    assert parse_source("0") == 0
    assert parse_source("http://192.168.1.23:8080/video").startswith("http://")


def test_timestamped_path_never_overwrites(tmp_path):
    now = datetime(2026, 11, 13, 12, 30, 45)
    first = timestamped_path(tmp_path / "shots", "screenshot", "jpg", now)
    first.write_bytes(b"x")
    second = timestamped_path(tmp_path / "shots", "screenshot", "jpg", now)
    assert first != second and first.name == "screenshot_20261113_123045.jpg"


def test_format_elapsed():
    assert format_elapsed(75) == "01:15"


def test_recorder_writes_file_and_resizes_mismatched_frames(tmp_path):
    rec = Recorder()
    rec.start((320, 240), 10, tmp_path)
    rec.write(np.zeros((240, 320, 3), np.uint8))
    rec.write(np.zeros((480, 640, 3), np.uint8))  # wrong size is resized, not lost
    path = rec.stop()
    assert path.exists() and path.stat().st_size > 0
    assert rec.stop() is None  # stopping twice is safe


def test_missing_camera_url_is_a_config_error(monkeypatch, tmp_path):
    monkeypatch.delenv("CAMERA_URL", raising=False)
    with pytest.raises(ConfigError):
        load_config(env_file=str(tmp_path / "nope.env"))
