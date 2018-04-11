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


class QrLipsyncAnalyzer():
    '''
        Open a text file containing JSON lines containing Qrcode and spectrum informations
        Compare frequency in spectrum and qrcode to compute audio/video delay
        Count Qrcode sequence number to check each second if video file has dropped/duplicate frames and compute framerate
        At the end, make a full report about the media
    '''
    def __init__(self, input_file, result_file, result_log, result_graph, qrcode_name, custom_data_name):
        signal.signal(signal.SIGINT, self._signal_handler)
        self._input_file = input_file
        self._result_file = result_file
        self._result_log = result_log
        self._result_to_graph = result_graph
        self._fd_result_log = -1
        self._fd_graph = -1

        self._ref_fps = 0
        self._real_fps = 0
        self._nb_dupl_frame = 0
        self._nb_drop_frame = 0
        self._nb_frames_in_sec = 0
        self.total_qrcode_frames = 0
        self._total_dropped_frames = 0
        self._total_dupl_frames = 0
        self._gap_frame = 0
        self._max_delay_audio_video = 0
        self._timestamp_max_delay = 0
        self._missing_beeps = 0

        self._got_first_frame_qrcode = False
        # 48000 hz / 1024 bands
        self._offset_freq = int(44100 / 512)

        self._video_duration = 0.0
        self._audio_duration = 0.0
        self._init_video_timestamp = 0
        self._video_timestamp = 0
        self._audio_timestamp = 0

        self._frame_number = 1
        self._qrcode_number = 0

        self._expected_qrcode_name = qrcode_name
        self._custom_data_name = custom_data_name
        self._qrcode_names = list()
        self._found_qrcode_names = list()
        self._all_audio_buff = list()
        self.all_qrcodes = list()
        self._qrcodes_with_freq = list()

        self._delay_audio_video_ms = list()
        self._avg_real_framerate = list()

    def _signal_handler(self, signal, frame):
        logger.info('You pressed Ctrl+C!')
        sys.exit(0)

    def start(self):
        logger.info('Reading file %s' % self._input_file)
        fd_input_file = open(self._input_file, 'r')
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

        if len(self._qrcodes_with_freq) > 0 and len(self._all_audio_buff) > 0:
            self.check_av_sync()
        self.check_video_stats()

        self._clean_all_list()
        self.show_summary(fd_input_file)

    def get_mean(self, list, ndigits=2):
        return round(statistics.mean(list), ndigits)

    def get_median(self, list, ndigits=2):
        return round(statistics.median(list), ndigits)

    # Complete report when parsing is over
    def show_summary(self, fd_input_file):
        results_dict = {
            "duplicated_frames": self._total_dupl_frames,
            "duplicated_frames_percent": round(100 * self._total_dupl_frames / self.total_qrcode_frames, 1),
            "dropped_frames": self._total_dropped_frames,
            "dropped_frames_percent": round(100 * self._total_dropped_frames / self.total_qrcode_frames, 1),
            "total_frames": self.total_qrcode_frames,
            "avg_real_framerate": self.get_mean(self._avg_real_framerate, 1),
            "avg_av_delay_ms": self.get_mean(self._delay_audio_video_ms) if len(self._delay_audio_video_ms) > 0 else "could not measure",
            "median_av_delay_ms": self.get_median(self._delay_audio_video_ms) if len(self._delay_audio_video_ms) > 0 else "could not measure",
            "max_delay_ms": self._max_delay_audio_video if self._max_delay_audio_video else "could not measure",
            "max_delay_ts": self._timestamp_max_delay,
            "video_duration": self._video_duration,
            "audio_duration": self._audio_duration,
            "matching_missing": self._missing_beeps,
        }
        self.write_logfile("---------------------------- Global report --------------------------")
        self.write_logfile("Total duplicated frames : %s/%s (%s%%)" % (self._total_dupl_frames, self.total_qrcode_frames, results_dict['duplicated_frames_percent']))
        self.write_logfile("Total dropped frames : %s/%s (%s%%)" % (self._total_dropped_frames, self.total_qrcode_frames, results_dict['dropped_frames_percent']))
        self.write_logfile("Avg real framerate (based on qrcode content) is %s" % results_dict['avg_real_framerate'])
        if len(self._delay_audio_video_ms) > 0:
            avg_value = results_dict['avg_av_delay_ms']
            if avg_value == 0:
                string_avg_delay = "Delay between beep and qrcode is perfect (0)"
            elif avg_value < 0:
                string_avg_delay = "Avg delay between beep and qrcode : %d ms, video is late" % abs(avg_value)
            else:
                string_avg_delay = "Avg delay between beep and qrcode : %d ms, audio is late" % abs(avg_value)
            string_avg_delay += " (median: %sms" % results_dict['median_av_delay_ms']
            if self._max_delay_audio_video:
                string_avg_delay += ", max: %sms at %ss)" % (round(self._max_delay_audio_video * 1000, 1), round(self._timestamp_max_delay, 3))
            else:
                string_avg_delay += ")"
            self.write_logfile(string_avg_delay)
        self.write_logfile("Video duration is %ss" % (self._video_duration))
        self.write_logfile("Audio duration is %ss" % (self._audio_duration))
        self.write_logfile("Missed %s beeps out of %s qrcodes" % (self._missing_beeps, len(self._qrcodes_with_freq)))
        self.write_logfile("---------------------------------------------------------------------")
        fd_input_file.close()
        self._fd_result_log.close()
        self._fd_graph.close()
        with open(self._result_file, "w") as f:
            json.dump(results_dict, f)
        logger.info('Wrote results as JSON into %s' % self._result_file)

    def _get_regex_result(self, regex, string):
        result_regex = re.search(regex, string)
        if not result_regex:
            # logger.warning("Could not parse regex : %s" % regex)
            return None
        return result_regex.group(1)

    # Parsing data contained in Qrcode
    def get_qrcode_data(self, line):
        qrcode_name = line['NAME']
        if qrcode_name not in self._qrcode_names:
            self._qrcode_names.append(qrcode_name)
        if qrcode_name == self._expected_qrcode_name:
            if qrcode_name not in self._found_qrcode_names:
                self._found_qrcode_names.append(qrcode_name)

            # timestamp in qrcode
            self._video_timestamp = decoded_timestamp = float(line['VIDEOTIMESTAMP']) / 1000000000
            # actual decoded buffer timestamp, in ns (gstreamer)
            current_timestamp = float(line['TIMESTAMP']) / 1000000000
            frame_number = line['BUFFERCOUNT']
            if current_timestamp is None or qrcode_name is None or frame_number is None:
                logger.error("Invalid line (timestamp, name or frame number missing)")
            freq_audio = line.get(self._custom_data_name)

            qrcode = {
                "timestamp": current_timestamp,  # timestamp in qrcode
                "frame_number": frame_number,
                "qrcode_name": qrcode_name,
                "decoded_timestamp": decoded_timestamp
            }

            if freq_audio is not None and len(freq_audio) > 0:
                qrcode["video_timestamp"] = self._video_timestamp
                qrcode["freq_audio"] = freq_audio
                if qrcode not in self._qrcodes_with_freq:
                    self._qrcodes_with_freq.append(qrcode)
        return qrcode

    def _clean_all_list(self):
        if not self._found_qrcode_names:
            logger.warning('No expected qrcode %s detected' % self._expected_qrcode_name)
            for q in self._qrcode_names:
                if q not in self._found_qrcode_names:
                    logger.warning('Found unexpected qrcode name %s, you may want to run qr-lipsync-analyze.py with -q %s' % (q, q))
            logger.error('Exiting with error')
            sys.exit(1)

        logger.info('Reached the end of the media, cleaning')
        self._qrcodes_with_freq.reverse()
        for one_frame in self._qrcodes_with_freq:
            video_timestamp = one_frame['timestamp']
            freq_in_frame = one_frame['freq_audio']
            string = "The frame number %s at %s with the frequency %sHz already found" % (one_frame.get('frame_number'), video_timestamp, freq_in_frame)
            logger.debug("%s" % string)
            self.write_line(string, self._fd_result_log)

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
                frame_number = qrcode['frame_number']
                last_frame_nb = last_qrcode['frame_number']
                frame_number_diff = frame_number - last_frame_nb
                if frame_number_diff == 1:
                    # normal behaviour
                    qrcode_framerate += 1
                    if frame_duration is None:
                        frame_duration = qrcode['timestamp'] - last_qrcode['timestamp']
                        logger.info('Detected frame duration of %.1fms' % (frame_duration * 1000))
                elif frame_number_diff > 1:
                    qrcode_framerate += 1
                    dropped_frames = frame_number_diff - 1
                    self._total_dropped_frames += dropped_frames
                    logger.warning("%s dropped frame(s): %s > %s at %.3fs" % (dropped_frames, last_frame_nb, frame_number, timestamp))
                elif frame_number == last_frame_nb:
                    logger.warning('1 duplicated frame at timestamp %.3fs' % timestamp)
                    self._total_dupl_frames += 1
                elif frame_number_diff < 0:
                    qrcode_framerate += 1
                    if frame_number_diff > max_backwards_diff:
                        logger.warning('Backwards frame: %s > %s' % (frame_number, last_frame_nb))
                    else:
                        # video is starting over
                        pass
            if frame_duration is not None:
                if start_timestamp is None:
                    start_timestamp = timestamp
                    end_timestamp = start_timestamp + 1 - frame_duration
                elif timestamp >= end_timestamp:
                    self._avg_real_framerate.append(qrcode_framerate)
                    start_timestamp = end_timestamp = None
                    qrcode_framerate = 0
            last_qrcode = qrcode

    def check_av_sync(self):
        logger.info("Checking AV sync")
        # for each new qrcode found that contains frequency information
        for f in self._qrcodes_with_freq:
            qrcode_freq = int(f['freq_audio'])
            # actual buffer timestamp, not the one written in the qrcode
            qrcode_ts = f['video_timestamp']
            audio_candidates = self.filter_audio_samples(timestamp=qrcode_ts, width=5)
            ts = self.find_beep(audio_candidates, qrcode_freq)
            if ts:
                # timestamps are in s
                diff_ms = round((ts - qrcode_ts) * 1000)
                logger.debug('Found beep at %ss, diff: %sms' % (ts, diff_ms))
                self._delay_audio_video_ms.append(diff_ms)
            else:
                logger.info('Did not find beep of %s Hz at %.3fs' % (qrcode_freq, qrcode_ts))
                self._missing_beeps += 1

    def filter_audio_samples(self, timestamp, width):
        # return audio buffers between timestamp - width and timestamp + width
        start = timestamp - width / 2
        end = timestamp + width / 2
        samples = [a for a in self._all_audio_buff if start < a['timestamp'] < end]
        return samples

    def find_beep(self, audio_samples, frequency):
        threshold_hz = 50
        for i, item in enumerate(audio_samples):
            if abs(item['freq_audio'] - frequency) < threshold_hz:
                return audio_samples[i]['timestamp']

    def parse_line(self, line):
        name = line.get('ELEMENTNAME')
        if name == 'qroverlay':
            self.total_qrcode_frames += 1
            qrcode = self.get_qrcode_data(line)
            self.all_qrcodes.append(qrcode)
        elif name == 'spectrum':
            audio_data = {}
            audio_data["timestamp"] = float(line['TIMESTAMP']) / 1000000000
            audio_data["peak_value"] = line['PEAK']
            audio_data["freq_audio"] = line['FREQ']
            self._all_audio_buff.append(audio_data)
        else:
            if line.get('AUDIODURATION'):
                self._audio_duration = round(float(line['AUDIODURATION']) / 1000000000.0, 3)
            if line.get('VIDEODURATION'):
                self._video_duration = round(float(line['VIDEODURATION']) / 1000000000.0, 3)

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
