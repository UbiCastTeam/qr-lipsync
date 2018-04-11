#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import argparse
import os
import re
import signal
import sys
import json
import statistics

logger = logging.getLogger('qr-lipsync-analyze')

SECOND = 1000000000


class QrLipsyncAnalyzer():

    def __init__(self, input_file, result_file, result_log, result_graph, qrcode_name, custom_data_name):
        self._input_file = input_file
        self._result_file = result_file
        self._result_log = result_log
        self._result_to_graph = result_graph
        self._fd_result_log = -1
        self._fd_graph = -1

        self.expected_qrcode_name = qrcode_name
        self.custom_data_name = custom_data_name

        self.qrcode_frames_count = 0
        self.dropped_frames_count = 0
        self.duplicated_frames_count = 0
        self.missing_beeps_count = 0

        self.video_duration_s = 0
        self.audio_duration_s = 0

        self.max_delay_ms = 0
        self.max_delay_ts = 0

        self.qrcode_names = list()
        self.all_audio_beeps = list()
        self.all_qrcodes = list()
        self.all_qrcodes_with_freq = list()
        self.all_qrcode_framerates = list()
        self.audio_video_delays_ms = list()

    def start(self):
        logger.info('Reading file %s' % self._input_file)

        with open(self._input_file, 'r') as fd_input_file:
            self._fd_result_file = open(self._result_file, 'w')
            self._fd_result_log = open(self._result_log, 'w')
            self._fd_graph = open(self._result_to_graph, 'w')
            self.write_graphfile("time\tdelay")
            try:
                fd_input_file.seek(0)
            except Exception as e:
                logger.error("Could not seek at the begining : %s" % e)
            line = self._read_andparse_line_in_file(fd_input_file)
            while (line):
                if len(line) > 0:
                    self.parse_line(line)
                line = self._read_andparse_line_in_file(fd_input_file)

        self.check_av_sync()
        self.check_video_stats()
        self.check_qrcode_names()
        self.show_summary()
        self.close_files()

    def close_files(self):
        self._fd_result_file.close()
        self._fd_result_log.close()
        self._fd_graph.close()

    def get_mean(self, list, ndigits=2):
        return round(statistics.mean(list), ndigits)

    def get_median(self, list, ndigits=2):
        return round(statistics.median(list), ndigits)

    # Complete report when parsing is over
    def show_summary(self):

        results_dict = {
            "duplicated_frames": self.duplicated_frames_count,
            "duplicated_frames_percent": round(100 * self.duplicated_frames_count / self.qrcode_frames_count, 1),
            "dropped_frames": self.dropped_frames_count,
            "dropped_frames_percent": round(100 * self.dropped_frames_count / self.qrcode_frames_count, 1),
            "total_frames": self.qrcode_frames_count,
            "avg_real_framerate": self.get_mean(self.all_qrcode_framerates, 2),
            "avg_av_delay_ms": self.get_mean(self.audio_video_delays_ms) if len(self.audio_video_delays_ms) > 0 else "could not measure",
            "median_av_delay_ms": self.get_median(self.audio_video_delays_ms) if len(self.audio_video_delays_ms) > 0 else "could not measure",
            "max_delay_ms": self.max_delay_ms,
            "max_delay_ts": self.max_delay_ts,
            "video_duration": self.video_duration_s,
            "audio_duration": self.audio_duration_s,
            "matching_missing": self.missing_beeps_count,
        }
        self.write_logfile("---------------------------- Global report --------------------------")
        self.write_logfile("Total duplicated frames : %s/%s (%s%%)" % (self.duplicated_frames_count, self.qrcode_frames_count, results_dict['duplicated_frames_percent']))
        self.write_logfile("Total dropped frames : %s/%s (%s%%)" % (self.dropped_frames_count, self.qrcode_frames_count, results_dict['dropped_frames_percent']))
        self.write_logfile("Avg real framerate (based on qrcode content) is %s" % results_dict['avg_real_framerate'])
        if len(self.audio_video_delays_ms) > 0:
            avg_value = results_dict['avg_av_delay_ms']
            if avg_value == 0:
                string_avg_delay = "Delay between beep and qrcode is perfect (0)"
            elif avg_value < 0:
                string_avg_delay = "Avg delay between beep and qrcode : %d ms, video is late" % abs(avg_value)
            else:
                string_avg_delay = "Avg delay between beep and qrcode : %d ms, audio is late" % abs(avg_value)
            string_avg_delay += " (median: %sms" % results_dict['median_av_delay_ms']
            if self.max_delay_ms:
                string_avg_delay += ", max: %sms at %ss)" % (self.max_delay_ms, round(self.max_delay_ts, 3))
            else:
                string_avg_delay += ")"
            self.write_logfile(string_avg_delay)
        self.write_logfile("Video duration is %ss" % (self.video_duration_s))
        if self.audio_duration_s:
            self.write_logfile("Audio duration is %ss" % (self.audio_duration_s))
            self.write_logfile("Missed %s beeps out of %s qrcodes" % (self.missing_beeps_count, len(self.all_qrcodes_with_freq)))
        else:
            self.write_logfile("No audio detected")
        self.write_logfile("---------------------------------------------------------------------")
        with open(self._result_file, "w") as f:
            json.dump(results_dict, f)
        logger.info('Wrote results as JSON into %s' % self._result_file)

    def get_qrcode_data(self, line):
        qrcode_name = line['NAME']
        if qrcode_name not in self.qrcode_names:
            self.qrcode_names.append(qrcode_name)

        if qrcode_name == self.expected_qrcode_name:
            # timestamp in qrcode, converted to seconds
            decoded_timestamp = float(line['VIDEOTIMESTAMP']) / SECOND
            # actual decoded buffer timestamp, converted to seconds
            current_timestamp = float(line['TIMESTAMP']) / SECOND
            qrcode_frame_number = line['BUFFERCOUNT']

            if current_timestamp is None or qrcode_name is None or qrcode_frame_number is None:
                logger.error("Skipping invalid line (timestamp, name or frame number missing)")
                return

            qrcode = {
                "qrcode_timestamp": current_timestamp,
                "decoded_timestamp": decoded_timestamp,
                "qrcode_frame_number": qrcode_frame_number,
                "qrcode_name": qrcode_name,
            }

            beep_freq = line.get(self.custom_data_name)
            if beep_freq is not None and len(beep_freq) > 0:
                qrcode["beep_freq"] = beep_freq
                if qrcode not in self.all_qrcodes_with_freq:
                    self.all_qrcodes_with_freq.append(qrcode)
            return qrcode

    def check_qrcode_names(self):
        if self.expected_qrcode_name not in self.qrcode_names:
            logger.warning('No expected qrcode %s detected' % self.expected_qrcode_name)
            if self.qrcode_names:
                logger.info('Found unexpected qrcode names %s, you may want to run qr-lipsync-analyze.py with -q %s' % (",".join(self.qrcode_names), self.qrcode_names[0]))
            logger.error('Exiting with error')
            sys.exit(1)

    def check_video_stats(self):
        logger.info('Checking video stats')
        # when capturing looped video samples, the frame count will reset to 1
        # this is expected behaviour but may be interpreted as backwards frames
        # we estimate that the sample is 30fps and is at least 10s long
        max_backwards_diff = -30 * 10
        start_timestamp = end_timestamp = None
        frame_duration = None
        qrcode_framerate = 0

        last_qrcode = None
        for qrcode in self.all_qrcodes:
            timestamp = qrcode['decoded_timestamp']
            if last_qrcode is not None:
                qrcode_frame_number = qrcode['qrcode_frame_number']
                last_frame_nb = last_qrcode['qrcode_frame_number']
                qrcode_frame_number_diff = qrcode_frame_number - last_frame_nb
                if qrcode_frame_number_diff == 1:
                    # normal behaviour
                    qrcode_framerate += 1
                    if frame_duration is None:
                        frame_duration = qrcode['qrcode_timestamp'] - last_qrcode['qrcode_timestamp']
                        logger.info('Detected frame duration of %.1fms' % (frame_duration * 1000))
                elif qrcode_frame_number_diff > 1:
                    qrcode_framerate += 1
                    dropped_frames = qrcode_frame_number_diff - 1
                    self.dropped_frames_count += dropped_frames
                    logger.warning("%s dropped frame(s): %s > %s at %.3fs" % (dropped_frames, last_frame_nb, qrcode_frame_number, timestamp))
                elif qrcode_frame_number == last_frame_nb:
                    logger.warning('1 duplicated frame at timestamp %.3fs' % timestamp)
                    self.duplicated_frames_count += 1
                elif qrcode_frame_number_diff < 0:
                    qrcode_framerate += 1
                    if qrcode_frame_number_diff > max_backwards_diff:
                        logger.warning('Backwards frame: %s > %s' % (qrcode_frame_number, last_frame_nb))
                    else:
                        # video is starting over
                        pass
            if frame_duration is not None:
                if start_timestamp is None:
                    start_timestamp = int(timestamp)
                    end_timestamp = start_timestamp + 1 - frame_duration
                elif timestamp >= end_timestamp:
                    self.all_qrcode_framerates.append(qrcode_framerate)
                    start_timestamp = end_timestamp = None
                    qrcode_framerate = 0
            last_qrcode = qrcode

    def check_av_sync(self):
        if len(self.all_qrcodes_with_freq) > 0 and len(self.all_audio_beeps) > 0:
            logger.info("Checking AV sync")
            # for each new qrcode found that contains frequency information
            for f in self.all_qrcodes_with_freq:
                qrcode_freq = int(f['beep_freq'])
                # actual buffer timestamp, not the one written in the qrcode
                qrcode_ts = f['decoded_timestamp']
                audio_candidates = self.filter_audio_samples(timestamp=qrcode_ts, width=5)
                ts = self.find_beep(audio_candidates, qrcode_freq)
                if ts:
                    # timestamps are in s
                    diff_ms = round((ts - qrcode_ts) * 1000)
                    logger.debug('Found beep at %ss, diff: %sms' % (ts, diff_ms))
                    self.write_graphfile("%s\t%s" %(ts, diff_ms))
                    self.audio_video_delays_ms.append(diff_ms)
                    if abs(diff_ms) > abs(self.max_delay_ms):
                        self.max_delay_ms = diff_ms
                        self.max_delay_ts = ts
                else:
                    logger.info('Did not find beep of %s Hz at %.3fs' % (qrcode_freq, qrcode_ts))
                    self.missing_beeps_count += 1

    def filter_audio_samples(self, timestamp, width):
        # return audio buffers between timestamp - width and timestamp + width
        start = timestamp - width / 2
        end = timestamp + width / 2
        samples = [a for a in self.all_audio_beeps if start < a['timestamp'] < end]
        return samples

    def find_beep(self, audio_samples, frequency):
        threshold_hz = 50
        for i, item in enumerate(audio_samples):
            if abs(item['beep_freq'] - frequency) < threshold_hz:
                return audio_samples[i]['timestamp']

    def parse_line(self, line):
        name = line.get('ELEMENTNAME')
        if name == 'qroverlay':
            self.qrcode_frames_count += 1
            qrcode = self.get_qrcode_data(line)
            if qrcode:
                self.all_qrcodes.append(qrcode)
        elif name == 'spectrum':
            audio_data = {}
            audio_data["timestamp"] = float(line['TIMESTAMP']) / SECOND
            audio_data["peak_value"] = line['PEAK']
            audio_data["beep_freq"] = line['FREQ']
            self.all_audio_beeps.append(audio_data)
        else:
            if line.get('AUDIODURATION'):
                self.audio_duration_s = round(float(line['AUDIODURATION']) / SECOND, 3)
            if line.get('VIDEODURATION'):
                self.video_duration_s = round(float(line['VIDEODURATION']) / SECOND, 3)

    def _read_andparse_line_in_file(self, fd_input_file):
        line = fd_input_file.readline()
        if line:
            try:
                return json.loads(line)
            except Exception as e:
                print("Failed to parse line %s : %s" % (repr(line), e))

    def write_line(self, line_content, dfile):
        if line_content is not None:
            line_content += '\n'
            dfile.write(line_content)
            dfile.flush()

    def write_logfile(self, line_content):
        logger.info(line_content)
        self.write_line(line_content, self._fd_result_log)

    def write_graphfile(self, line_content):
        self.write_line(line_content, self._fd_graph)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process QrCode and spectrum data file generated with qr-lipsync-detect.py')
    parser.add_argument('input_file', help='filename of raw QrCode and spectrum data')
    parser.add_argument('-q', '--qrcode-name', help='name of qrcode pattern to look after', default='CAM1')
    parser.add_argument('-c', '--custom-data-name', help='name of custom data embedded in qrcode to extract', default='TICKFREQ')
    parser.add_argument('-v', '--verbosity', help='increase output verbosity', action="store_true")
    options = parser.parse_args(sys.argv[1:])

    level = "DEBUG" if options.verbosity else "INFO"
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        stream=sys.stderr
    )

    signal.signal(signal.SIGINT, sys.exit)

    input_file = options.input_file
    if os.path.isfile(input_file):
        dirname = os.path.dirname(input_file)
        media_name = os.path.splitext(os.path.basename(input_file))[0]
        media_name = media_name.replace("data", "report")
        result_file = os.path.join(dirname, "%s.json" % media_name)
        result_log = os.path.join(dirname, "%s.txt" % media_name)
        result_graph = os.path.join(dirname, "%s_graph.txt" % (media_name))
        a = QrLipsyncAnalyzer(input_file, result_file, result_log, result_graph, options.qrcode_name, options.custom_data_name)
        a.start()
    else:
        logger.error("File %s not found" % options.input_file)
        sys.exit(1)
