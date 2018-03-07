#!/usr/bin/env python
# -*- coding: utf-8 -*-
import signal
import sys
import time

import logging
logger = logging.getLogger('qrcode_generator')

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
GObject.threads_init()
Gst.init(None)

import easyevent
from gstmanager import PipelineManager


class QrLipsyncGenerator(easyevent.User):
    '''
        Generate video with qrcode incrusted using gstreamer
        and each seconde, there is an audio beep at different frequency
    '''
    def __init__(self, settings, mainloop):
        easyevent.User.__init__(self)
        signal.signal(signal.SIGINT, self._signal_handler)
        self.register_event("eos")
        self.settings = settings
        self.mainloop = mainloop
        self.samplesperbuffer = settings.get('samplesperbuffer')
        self.duration = (settings.get('duration') - 1) * Gst.SECOND
        self.delay_audio_freq_change = settings.get('delay_audio_freq_change') * Gst.SECOND
        self.freq_array = settings.get('freq_array')
        self.output_file = settings.get('output_file')

        self.start_time = None
        self.end_time = None
        self.id_prob_audio_src = None
        self.audio_src_pad = None
        self.current_audio_timestamp = 0
        self.increment = 0

        self.pipeline_str = self._get_pipeline_string()
        logger.info(self.pipeline_str)
        self.pipeline = PipelineManager(self.pipeline_str)

    def _signal_handler(self, signal, frame):
        logger.info('You pressed Ctrl+C!')
        sys.exit(0)

    def _get_pipeline_string(self):
        s = self.settings
        # Black background
        color = s.get("background", "black")
        video_src = "videotestsrc pattern=%s" % color
        video_caps = "video/x-raw, format=(string)I420, width=(int)%s, height=(int)%s, framerate=(fraction)%s/1" % (s.get('width', 320), s.get('height', 240), s.get('framerate', 30))
        audio_src = self._get_audio_src()
        audio_caps = self._get_audio_caps()
        qroverlay = self._get_qroverlay(self.freq_array)
        textoverlay = self._get_textoverlay()
        video_converter = "videoconvert"
        video_encoder = "x264enc pass=5 quantizer=21"
        self.increment += 1
        muxer = "qtmux name=mux"
        sink = "filesink location=%s" % self.output_file
        pipeline = '%s ! %s ! %s ! %s ! %s ! %s ! %s ! %s %s ! %s ! mux. ' % (video_src, video_caps, qroverlay, textoverlay, video_converter, video_encoder, muxer, sink, audio_src, audio_caps)
        return pipeline

    def _get_textoverlay(self):
        if self.settings.get('enable_textoverlay', True):
            return 'timeoverlay text=%s halignment=center valignment=bottom font-desc="Arial 30"' % self.settings.get('qrname')
        return ""

    def _get_qroverlay(self, data_array):
        s = self.settings
        extra_data_array = ",".join([str(i) for i in data_array])
        plugin_name = s.get('qrname', 'myqroverlay')
        x_position = 50
        y_position = 20
        error_correction = 3
        span_buffer = 1
        interval_buffers = 30
        pixel_size = s.get('qr_pix_size', 2)
        data_name = s.get('extra_data_name', 'tickfreq')
        qroverlay = 'qroverlay x=%s y=%s name=%s qrcode-error-correction=%s extra-data-span-buffers=%s extra-data-interval-buffers=%s extra-data-name=%s extra-data-array="%s" pixel-size=%s' % (x_position, y_position, plugin_name, error_correction, span_buffer, interval_buffers, data_name, extra_data_array, pixel_size)
        return qroverlay

    def _get_audio_src(self):
        audio_src = "audiotestsrc wave=8 freq=%s samplesperbuffer=%s name=audio_src" % (self.freq_array[self.increment], self.samplesperbuffer)
        return audio_src

    def _get_audio_caps(self):
        channel = 1
        rate = 48000
        format_audio = "S16LE"
        caps = 'capsfilter caps="audio/x-raw\,\ format\=\(string\)%s\,\ layout\=\(string\)interleaved\,\ rate\=\(int\)%s\,\ channels\=\(int\)%s"' % (format_audio, rate, channel)
        return caps

    def on_audio_src_buffer(self, pad, info, data):
        buf = info.get_buffer()
        self.current_audio_timestamp = buf.pts
        self.update_audiotestsrc_freq()
        return True

    def update_audiotestsrc_freq(self):
        if self.current_audio_timestamp >= self.duration * Gst.NSECOND:
            self.disconnect_probes()
            self.pipeline.send_eos()
        if self.current_audio_timestamp % self.delay_audio_freq_change == 0:
            self.set_audiotestsrc_freq(self.freq_array[self.increment])
            self.increment += 1
            if self.increment == len(self.freq_array):
                self.increment = 0

    def set_audiotestsrc_freq(self, freq):
        audio_src = self.pipeline.pipeline.get_by_name("audio_src")
        logger.info("Change audiotestsrc frequency to %s Hz" % freq)
        audio_src.set_property('freq', freq)

    def disconnect_probes(self):
        logger.debug('Disconnecting probes')
        if self.audio_src_pad:
            self.audio_src_pad.remove_probe(self.id_prob_audio_src)

    def start(self):
        self.start_time = time.time()
        audio_src_elt = self.pipeline.pipeline.get_by_name("audio_src")
        self.audio_src_pad = audio_src_elt.get_static_pad('src')
        self.id_prob_audio_src = self.audio_src_pad.add_probe(Gst.PadProbeType.BUFFER, self.on_audio_src_buffer, None)
        self.pipeline.run()

    def evt_eos(self, event):
        self.end_time = time.time()
        self.unregister_event("eos")
        self.pipeline.stop()
        render_duration = self.end_time - self.start_time
        fps = self.settings['framerate']*self.settings['duration']/render_duration
        logger.info("Rendering of %s took %.2fs (%i fps)" % (self.output_file, render_duration, fps))
        GObject.idle_add(self.mainloop.quit)

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        stream=sys.stderr
    )

    # Name that will identify the qrcode
    qrname = "cam4"

    settings = {
        "output_file": "%s-qrcode.qt" % qrname,
        "samplesperbuffer": 48000,
        "duration": 60,
        "delay_audio_freq_change": 1,
        "qrname": qrname,
        "width": 640,
        "height": 360,
        "framerate": 30,
        "qr_pix_size": 4,
        "extra_data_name": "tickfreq",
        "freq_array": (240, 480, 720, 960, 1200, 1440, 1680, 1920, 2160, 2400, 2640, 2880, 3120, 3360, 3600, 3840, 4080, 4320, 4560, 4800, 5040, 5280, 5520, 5760, 6000, 6240, 6480, 6720, 6960, 7200, 7440, 7680, 7920, 8160, 8400, 8640, 8880, 9120, 9360, 9600, 9840, 10080),
        "background": "checkers-1",
        "enable_textoverlay": True,
    }

    ml = GObject.MainLoop()
    qr_gen = QrLipsyncGenerator(settings, ml)
    GObject.idle_add(qr_gen.start)
    ml.run()
