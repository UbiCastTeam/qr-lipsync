import os
import sys

import pytest

from qrlipsync.scripts.analyze import main

os.environ["QRLIPSYNC_MIN_ACCEL_SAMPLES"] = "1"

DATA = os.path.join(os.path.dirname(__file__), "normal_data.txt")


def run_main(argv, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["qr-lipsync-analyze"] + argv)
    return main()


def test_failed_analysis_exits_nonzero(monkeypatch, caplog):
    # the expected qrcode name does not match the file content, so the
    # analyzer logs "Exiting with error" and start() returns False
    exit_code = run_main(["-n", "-q", "NOPE", DATA], monkeypatch)
    assert exit_code == 1


def test_successful_analysis_still_exits_zero(monkeypatch):
    exit_code = run_main(["-n", DATA], monkeypatch)
    assert exit_code == 0


def test_missing_file_still_exits_nonzero(monkeypatch):
    exit_code = run_main(["-n", "does-not-exist.txt"], monkeypatch)
    assert exit_code == 1
