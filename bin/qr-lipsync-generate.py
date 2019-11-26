#!/usr/bin/env python
import sys
import argparse
import logging
from gi.repository import GLib
from qrlipsync.generate import QrLipsyncGenerator

logger = logging.getLogger("qrcode_generator")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Generate videos suitable for measuring lipsync with qrcodes",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-v", "--verbosity", help="increase output verbosity", action="store_true"
    )
    parser.add_argument(
        "--disable-audio",
        help="disable audio track",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--disable-audio-baseline",
        help="disable audio baseline",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--enable-textoverlay",
        help="enable text overlay (shows timecode)",
        action="store_true",
        default=True,
    )
    parser.add_argument(
        "--qrcode-name", help="name inserted into the qrcode pattern", default="cam1",
    )
    parser.add_argument(
        "-d",
        "--duration",
        help="duration of generated sample in seconds",
        type=int,
        default=30,
    )
    parser.add_argument("-r", "--framerate", help="framerate", type=int, default=30)
    parser.add_argument("-s", "--size", help="video size", type=str, default="640x360")
    parser.add_argument(
        "-f",
        "--format",
        help="video format: qt/h264/pcm (default) or mp4/h264/aac",
        choices=["mp4", "qt"],
        default="qt",
    )
    parser.add_argument(
        "-b",
        "--background",
        help="background color",
        choices=["snow", "black", "white", "red", "green", "blue", "smpte", "pinwheel"],
        default="blue",
    )

    options = parser.parse_args()

    verbosity = getattr(logging, "DEBUG" if options.verbosity else "INFO")
    logging.basicConfig(
        level=verbosity,
        format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
        stream=sys.stderr,
    )

    # Name that will identify the qrcode
    qrname = options.qrcode_name
    try:
        width, height = options.size.split("x")
    except ValueError:
        logger.error('Size must be in the following format: "640x360"')
        sys.exit(1)

    freq_array = [
        240,
        480,
        720,
        960,
        1200,
        1440,
        1680,
        1920,
        2160,
        2400,
        2640,
        2880,
        3120,
        3360,
        3600,
        3840,
        4080,
        4320,
        4560,
        4800,
        5040,
        5280,
        5520,
        5760,
        6000,
        6240,
        6480,
        6720,
        6960,
        7200,
        7440,
        7680,
        7920,
        8160,
        8400,
        8640,
        8880,
        9120,
        9360,
        9600,
        9840,
        10080,
    ]

    if not options.disable_audio_baseline:
        baseline_freq_array = [freq_array.pop(0)]
    else:
        baseline_freq_array = []

    settings = {
        "disable_audio": options.disable_audio,
        "samplerate": 48000,
        "duration": options.duration,
        "delay_audio_freq_change": 1,
        "qrname": qrname,
        "format": options.format,
        "width": width,
        "height": height,
        "framerate": options.framerate,
        "qr_pix_size": 4,
        "extra_data_name": "tickfreq",
        "freq_array": freq_array,
        "baseline_freq_array": baseline_freq_array,
        "background": options.background,
        "enable_textoverlay": True,
    }

    video_format = options.format
    if video_format == "qt":
        settings["muxer"] = "qtmux"
        bitrate = 20000 if options.background == "snow" else 1000
        settings["vcodec"] = (
            "x264enc pass=0 bitrate=%s tune=zerolatency ! video/x-h264, profile=main"
            % bitrate
        )
        settings["acodec"] = "identity"
        settings["fileext"] = ".qt"
        settings["output_file"] = "%s-qrcode-%s-%s.qt" % (
            qrname,
            options.background,
            options.framerate,
        )
    elif video_format == "mp4":
        settings["muxer"] = "mp4mux"
        bitrate = 20000 if options.background == "snow" else 1000
        settings["vcodec"] = (
            "x264enc pass=0 bitrate=%s tune=zerolatency ! video/x-h264, profile=main"
            % bitrate
        )
        settings["acodec"] = "fdkaacenc"
        settings["output_file"] = "%s-qrcode-%s-%s.mp4" % (
            qrname,
            options.background,
            options.framerate,
        )

    ml = GLib.MainLoop()
    qr_gen = QrLipsyncGenerator(settings, ml)
    GLib.idle_add(qr_gen.start)
    ml.run()
