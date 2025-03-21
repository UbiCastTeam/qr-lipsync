#!/usr/bin/env python
import signal
import sys
import time
import logging

import gi

gi.require_version("Gst", "1.0")  # noqa
from gi.repository import GObject, Gst # noqa

Gst.init(None)

logger = logging.getLogger("qrcode_generator")


class QrLipsyncGenerator:
    """
        Generate video with qrcode incrusted using gstreamer
        and each seconde, there is an audio beep at different frequency
    """

    def __init__(self, settings, mainloop):
        signal.signal(signal.SIGINT, self._signal_handler)
        self.settings = settings
        self.mainloop = mainloop
        # self.duration = (settings.get('duration') - 1) * Gst.SECOND
        self.delay_audio_freq_change = (
            settings.get("delay_audio_freq_change") * Gst.SECOND
        )
        self.freq_array = settings.get("freq_array")
        self.output_file = settings.get("output_file")

        self.start_time = None
        self.end_time = None
        self.id_prob_audio_src = None
        self.audio_src_pad = None
        self.increment = 0

        self.pipeline_str = self._get_pipeline_string()
        logger.info(self.pipeline_str)
        try:
            self.pipeline = Gst.parse_launch(self.pipeline_str)
        except Exception as e:
            logger.error("Failed to start pipeline (%s), exiting with error" % e)
            sys.exit(1)

    def _signal_handler(self, signal, frame):
        logger.info("You pressed Ctrl+C!")
        sys.exit(0)

    def get_tick_periods(self, freq):
        # we target a 1 frame duration tick
        framerate = self.settings["framerate"]
        target_tick_dur = 1 / framerate
        sine_dur = 1 / freq
        tick_periods = int(target_tick_dur / sine_dur)
        return tick_periods

    def _get_pipeline_string(self):
        s = self.settings
        # Black background
        video_src = "videotestsrc pattern=%s num-buffers=%s" % (
            s["background"],
            s["framerate"] * s["duration"],
        )
        video_caps = (
            "video/x-raw, format=(string)I420, width=(int)%s, height=(int)%s, framerate=(fraction)%s/1"
            % (s.get("width", 320), s.get("height", 240), s.get("framerate", 30))
        )
        # the ticks duration is samplesperbuffer-long, so we need 1s long samples
        audio_src = (
            "audiotestsrc wave=ticks freq=%s samplesperbuffer=%s name=audio_src num-buffers=%s sine-periods-per-tick=%s"
            % (
                self.freq_array[self.increment],
                s["samplerate"],
                s["duration"],
                self.get_tick_periods(self.freq_array[self.increment]),
            )
        )
        audio_caps = (
            'capsfilter caps="audio/x-raw, format=(string)S16LE, layout=(string)interleaved, rate=(int)%s, channels=(int)1"'
            % s["samplerate"]
        )
        qroverlay = self._get_qroverlay(self.freq_array)
        textoverlay = self._get_textoverlay()
        video_converter = "videoconvert"
        video_encoder = s["vcodec"]
        self.increment += 1
        muxer = "%s name=mux" % s["muxer"]
        sink = "filesink location=%s" % self.output_file
        pipeline = " ! ".join(
            [
                video_src,
                video_caps,
                qroverlay,
                textoverlay,
                video_converter,
                video_encoder,
                muxer,
                sink,
            ]
        )
        if not s["disable_audio"]:
            pipeline += " " + " ! ".join([audio_src, audio_caps, s["acodec"], "mux."])
        return pipeline

    def _get_textoverlay(self):
        if self.settings.get("enable_textoverlay", True):
            return (
                'timeoverlay text=%s halignment=center valignment=bottom font-desc="Arial 30"'
                % self.settings.get("qrname")
            )
        return ""

    def _get_qroverlay(self, data_array):
        s = self.settings
        extra_data_array = ",".join([str(i) for i in data_array])
        plugin_name = s.get("qrname", "myqroverlay")
        x_position = 50
        y_position = 20
        error_correction = 3
        span_buffer = 1
        interval_buffers = self.settings["framerate"]
        qrcode_size_percent = s.get("qrcode_size_percent", 50)
        if not self.settings["disable_audio"]:
            data_name = s.get("extra_data_name", "tickfreq")
            qroverlay = f'debugqroverlay x={x_position} y={y_position} name={plugin_name} qrcode-error-correction={error_correction} extra-data-span-buffers={span_buffer} extra-data-interval-buffers={interval_buffers} extra-data-name={data_name} extra-data-array="{extra_data_array}" size={qrcode_size_percent}'
        else:
            qroverlay = f'debugqroverlay x={x_position} y={y_position} name={plugin_name} qrcode-error-correction={error_correction} extra-data-span-buffers={span_buffer} size={qrcode_size_percent}'

        return qroverlay

    def on_audio_src_buffer(self, pad, info, data):
        buf = info.get_buffer()
        if buf.pts % self.delay_audio_freq_change == 0:
            freq = self.freq_array[self.increment]
            audio_src = self.pipeline.get_by_name("audio_src")
            audio_src.set_property("freq", freq)
            tick_periods = self.get_tick_periods(freq)
            audio_src.set_property("sine-periods-per-tick", tick_periods)
            logger.info(
                "[timestamp: %s] Change audiotestsrc frequency to %s Hz, periods: %s"
                % (buf.pts, freq, tick_periods)
            )
            self.increment += 1
            if self.increment == len(self.freq_array):
                self.increment = 0
        return True

    def disconnect_probes(self):
        logger.debug("Disconnecting probes")
        if self.audio_src_pad:
            self.audio_src_pad.remove_probe(self.id_prob_audio_src)

    def start(self):
        self.start_time = time.time()
        if not self.settings["disable_audio"]:
            audio_src_elt = self.pipeline.get_by_name("audio_src")
            self.audio_src_pad = audio_src_elt.get_static_pad("src")
            self.id_prob_audio_src = self.audio_src_pad.add_probe(
                Gst.PadProbeType.BUFFER, self.on_audio_src_buffer, None
            )
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::eos", self._on_eos)
        logger.info("starting pipeline")
        self.pipeline.set_state(Gst.State.PLAYING)

    def _on_eos(self, bus, message):
        self.end_time = time.time()
        self.pipeline.set_state(Gst.State.NULL)
        render_duration = self.end_time - self.start_time
        fps = self.settings["framerate"] * self.settings["duration"] / render_duration
        logger.info(
            "Rendering of %s took %.2fs (%i fps)"
            % (self.output_file, render_duration, fps)
        )
        GObject.idle_add(self.mainloop.quit)
