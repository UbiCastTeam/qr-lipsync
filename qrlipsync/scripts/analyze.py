#!/usr/bin/env python
import logging
import argparse
import os
import signal
import sys
from qrlipsync.analyze import QrLipsyncAnalyzer

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Process QrCode and spectrum data file generated with qr-lipsync-detect"
    )

    parser.add_argument("input_file", help="filename of raw QrCode and spectrum data")

    parser.add_argument(
        "-q",
        "--qrcode-name",
        help="name of qrcode pattern to look after",
        default="CAM1",
    )

    parser.add_argument(
        "-c",
        "--custom-data-name",
        help="name of custom data embedded in qrcode to extract",
        default="TICKFREQ",
    )

    parser.add_argument(
        "-v",
        "--verbosity",
        help="increase output verbosity",
        action="store_true"
    )

    parser.add_argument(
        "--desync-threshold-frames",
        help="tolerated desync (in frames); beyond this, qr-lipsync will exit with a non 0 exit status",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--expected-beep-duration",
        help="Duration in ms of a beep (if 0, will consider 1 video frame duration based on the framerate of the video)",
        type=float,
        default=0,
    )

    parser.add_argument(
        "-n",
        "--no-report-files",
        help="do not write report files",
        action="store_true"
    )

    options = parser.parse_args(sys.argv[1:])

    logging.basicConfig(
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        level=logging.DEBUG if options.verbosity else logging.INFO,
        stream=sys.stderr,
    )

    signal.signal(signal.SIGINT, sys.exit)

    input_file = options.input_file
    exit_code = 0
    if os.path.isfile(input_file):
        a = QrLipsyncAnalyzer(input_file, options)
        if a.start():
            exit_code = a.show_summary_and_exit()
    else:
        logger.error("File %s not found" % options.input_file)
        exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
