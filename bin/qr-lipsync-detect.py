#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

import sys
import logging
from gi.repository import GLib

logger = logging.getLogger('timing_analyzer_bin')

from qrlipsync.detect import QrLipsyncDetector

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='Generate videos suitable for measuring lipsync with qrcodes',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('input_file', help='filename of video to analyze')
    parser.add_argument('-a', '--area', help='area in x1:y1:x2:y2 format (in percent) to look qrcodes for; example: 0:30:30:80; reference is top left corner')
    parser.add_argument('-s', '--skip-results', help='do not display results right after analysis', action="store_true")
    parser.add_argument('-d', '--downscale-width', help='downscale picture to this width to speed up qrcode lookup, 0 to disable', default=300, type=int)
    parser.add_argument('-p', '--preview', help='display a live preview of the analyzed area', action="store_true")
    parser.add_argument('-v', '--verbosity', help='increase output verbosity', action="store_true")
    options = parser.parse_args()
    verbosity = getattr(logging, "DEBUG" if options.verbosity else "INFO")

    logging.basicConfig(
        level=verbosity,
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        stream=sys.stderr
    )

    media_file = options.input_file
    mainloop = GLib.MainLoop()
    if os.path.isfile(media_file):
        dirname = os.path.dirname(media_file)
        media_prefix = os.path.splitext(os.path.basename(media_file))[0]
        result_file = os.path.join(dirname, "%s_data.txt" % (media_prefix))
        d = QrLipsyncDetector(media_file, result_file, options, mainloop)
        GLib.idle_add(d.start)
        try:
            mainloop.run()
        except KeyboardInterrupt:
            logger.info('Ctrl+C hit, stopping')
            d.exit()
    else:
        logger.error("File %s not found" % media_file)
