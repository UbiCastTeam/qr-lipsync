#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import argparse
import os
import re
import signal
import sys
import json
from fractions import Fraction

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
        self._total_frames = 0
        self._total_drop_frames = 0
        self._total_dupl_frames = 0
        self._offset_video = 0
        self._gap_frame = 0
        self._max_delay_audio_video = 0
        self._timestamp_max_delay = 0

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
        self._frames_with_freq = list()
        self._all_audio_buff = list()
        self._delay_audio_video = list()
        self._avg_real_framerate = list()
        self._avg_framerate = list()

    def _signal_handler(self, signal, frame):
        logger.info('You pressed Ctrl+C!')
        sys.exit(0)

    def start(self):
        logger.info('Analyzing data')
        fd_input_file = open(self._input_file, 'r')
        self._fd_result_file = open(self._result_file, 'w')
        self._fd_result_log = open(self._result_log, 'w')
        self._fd_graph = open(self._result_to_graph, 'w')
        self.write_graphfile("time\tdelay")
        self._init_offset_video(fd_input_file)
        try:
            fd_input_file.seek(0)
        except Exception as e:
            logger.error("Could not seek at the begining : %s" % e)
        line = self._read_andparse_line_in_file(fd_input_file)
        while (line):
            if len(line) > 0:
                self.parse_line(line)
            line = self._read_andparse_line_in_file(fd_input_file)
        self._clean_all_list()
        self.show_summary(fd_input_file)

    # Read line to get theorical framerate stored in Qrcode
    def _init_offset_video(self, fd_input_file):
        line = self._read_andparse_line_in_file(fd_input_file)
        while(line):
            if line.get('ELEMENTNAME') == 'qroverlay':
                self._offset_video = self._get_offset_tolerance(line)
                break
            line = self._read_andparse_line_in_file(fd_input_file)

    # Complete report when parsing is over
    def show_summary(self, fd_input_file):
        results_dict = {
            "duplicated_frames": self._total_dupl_frames,
            "duplicated_frames_percent": round(100 * self._total_dupl_frames / self._total_frames, 1),
            "dropped_frames": self._total_drop_frames,
            "dropped_frames_percent": round(100 * self._total_drop_frames / self._total_frames, 1),
            "total_frames": self._total_frames,
            "avg_framerate": round(sum(self._avg_framerate) / len(self._avg_framerate), 1),
            "avg_real_framerate": round(sum(self._avg_real_framerate) / len(self._avg_real_framerate), 1),
            "avg_av_delay_ms": int((sum(self._delay_audio_video) / len(self._delay_audio_video)) * 1000) if len(self._delay_audio_video) > 0 else "could not measure",
            "max_delay_ms": int(self._max_delay_audio_video * 1000) if self._max_delay_audio_video else "could not measure",
            "max_delay_ts": self._timestamp_max_delay,
            "video_duration": self._video_duration,
            "audio_duration": self._audio_duration
        }
        self.write_logfile("---------------------------- Global report --------------------------")
        self.write_logfile("Nb total duplicated frames : %s (%.2f%%)" % (self._total_dupl_frames, results_dict['duplicated_frames_percent']))
        self.write_logfile("Nb total dropped frame : %s (%.2f%%)" % (self._total_drop_frames, results_dict['dropped_frames_percent']))
        self.write_logfile("Avg framerate is %.3f" % results_dict['avg_framerate'])
        self.write_logfile("Avg real framerate is %.3f" % results_dict['avg_real_framerate'])
        if len(self._delay_audio_video) > 0:
            avg_value = results_dict['avg_av_delay_ms']
            if avg_value < 0:
                string_avg_delay = "Avg delay between beep and qrcode : %d ms, video is late" % abs(avg_value)
            else:
                string_avg_delay = "Avg delay between beep and qrcode : %d ms, audio is late" % abs(avg_value)
            self.write_logfile(string_avg_delay)
        if self._max_delay_audio_video:
            self.write_logfile("Max delay between beep and qrcode : %d ms at %.3f s" % (abs(self._max_delay_audio_video) * 1000, self._timestamp_max_delay))
        self.write_logfile("Video duration is %.3f sec" % (self._video_duration))
        self.write_logfile("Audio duration is %.3f sec" % (self._audio_duration))
        self.write_logfile("---------------------------------------------------------------------")
        fd_input_file.close()
        self._fd_result_log.close()
        self._fd_graph.close()
        with open(self._result_file, "w") as f:
            json.dump(results_dict, f)
        logger.info('Wrote results as JSON into %s' % self._result_file)

    # We tolerate delay audio/video lower than one frame duration
    def _get_offset_tolerance(self, line):
        framerate = float(Fraction(line.get('FRAMERATE')))
        self._ref_fps = int(framerate)
        self._avg_framerate.append(framerate)
        self._avg_real_framerate.append(framerate)
        return 1000.0 / framerate

    def _get_regex_result(self, regex, string):
        result_regex = re.search(regex, string)
        if not result_regex:
            # logger.warning("Could not parse regex : %s" % regex)
            return None
        return result_regex.group(1)

    # Parsing data contained in Qrcode
    def get_qrcode_data(self, line):
        data_in_one_frame = dict()
        qrcode_name = line['NAME']
        if qrcode_name not in self._qrcode_names:
            self._qrcode_names.append(qrcode_name)
        if qrcode_name == self._expected_qrcode_name:
            if qrcode_name not in self._found_qrcode_names:
                self._found_qrcode_names.append(qrcode_name)
            self._video_timestamp = float(line['VIDEOTIMESTAMP']) / 1000000000
            current_timestamp = float(line['TIMESTAMP']) / 1000000000
            frame_number = line['BUFFERCOUNT']
            if current_timestamp is None or qrcode_name is None or frame_number is None:
                logger.error("Invalid line (timestamp, name or frame number missing)")
            freq_audio = line.get(self._custom_data_name)
            data_in_one_frame["timestamp"] = current_timestamp
            data_in_one_frame["frame_number"] = frame_number
            data_in_one_frame["qrcode_name"] = qrcode_name
            if freq_audio is not None and len(freq_audio) > 0:
                data_in_one_frame["video_timestamp"] = self._video_timestamp
                data_in_one_frame["freq_audio"] = freq_audio
                self._frames_with_freq.append(data_in_one_frame)
        return data_in_one_frame

    # Compare frame number theorical with frame number contained in Qrcode
    def _check_frame_number(self, data_in_one_frame):
        if not self._got_first_frame_qrcode:
            # Initialized variables when first qr code is detected in the video
            self._frame_number = data_in_one_frame.get("frame_number")
            self._init_video_timestamp = self._video_timestamp
            frame_diff = 0
            self._got_first_frame_qrcode = True
            self._nb_frames_in_sec = 0
            self._real_fps = 0
        elif self._frame_number - data_in_one_frame.get("frame_number") > self._frame_number - self._ref_fps and self._frame_number - self._ref_fps > 0:
            # Case during video, qrcode number restart
            frame_diff = 0
            self._frame_number = data_in_one_frame.get("frame_number")
            self._nb_dupl_frame = 0
            self._nb_drop_frame = 0
            self._gap_frame = 0
            self._nb_frames_in_sec = 0
            self._init_video_timestamp = self._video_timestamp
            self._real_fps = 0
        else:
            frame_diff = data_in_one_frame.get("frame_number") - (self._frame_number + self._gap_frame)
            self._nb_frames_in_sec += 1
        if frame_diff != 0:
            # Check if we have dropped or duplicate framerate
            self._inconsistent_frame_number(frame_diff, data_in_one_frame)
        if (self._video_timestamp - self._init_video_timestamp + 0.01) * 1000 >= 1000:
            self._report_every_second()
        elif frame_diff >= 0:
            # Count nb frame if it is not a duplicate frame and less than one secondes is passed
            self._real_fps += 1
        self._frame_number += 1

    def _inconsistent_frame_number(self, frame_diff, data_in_one_frame):
        if frame_diff > 0:
            self._nb_drop_frame += 1
            self._total_drop_frames += 1
            warning = "At %.3f sec, frame dropped. Qrcode number is %s should be %s" % (self._video_timestamp, data_in_one_frame["frame_number"], self._frame_number + self._gap_frame)
            self._gap_frame += 1
        else:
            self._nb_dupl_frame += 1
            self._total_dupl_frames += 1
            warning = "At %.3f sec, frame duplicated. Qrcode number is %s should be %s" % (self._video_timestamp, data_in_one_frame["frame_number"], self._frame_number + self._gap_frame)
            self._gap_frame -= 1
        logger.debug("%s" % warning)
        self.write_line(warning, self._fd_result_log)

    def _report_every_second(self):
        framerate = 1000.0 / (float(self._video_timestamp - self._init_video_timestamp) / float((self._nb_frames_in_sec)) * 1000.0)
        self._avg_framerate.append(framerate)
        self._avg_real_framerate.append(self._real_fps)
        # logger.info("Framerate is %.3f, at %.3f sec, we have %s frames dropped and %s frames duplicate, real framerate is %.3f" % (framerate, self._video_timestamp, self._nb_drop_frame, self._nb_dupl_frame, self._real_fps))
        self._nb_dupl_frame = 0
        self._nb_drop_frame = 0
        self._nb_frames_in_sec = 0
        self._real_fps = 1
        self._init_video_timestamp = self._video_timestamp

    # Compare for each audio buffer containing freq if one Qrcode have a value close
    # In this case we calculate delay audio/video
    # return freq found with Qrcode corresponding
    def _get_corresponding_freq(self):
        for index_audio, audio_data in enumerate(self._all_audio_buff):
            audio_freq = float(audio_data['freq_audio'])
            audio_timestamp = audio_data['timestamp']
            for index_video, one_frame in enumerate(self._frames_with_freq):
                frame_freq_audio = float(one_frame['freq_audio'])
                if abs(audio_freq - frame_freq_audio) < self._offset_freq and audio_freq < frame_freq_audio:
                    diff_timestamp = audio_timestamp - one_frame.get("video_timestamp")
                    frame_number = self._frames_with_freq[index_video].get('frame_number')
                    if frame_number != self._qrcode_number:
                        if diff_timestamp < 1.0:
                            if abs(diff_timestamp) > abs(self._max_delay_audio_video):
                                self._max_delay_audio_video = diff_timestamp
                                self._timestamp_max_delay = one_frame.get("video_timestamp")
                            # if diff_timestamp * 1000.0 > self._offset_video:
                            string = "The frame %s has a delay of %.3f sec. Audio timestamp is %.3f sec, video timestamp is %.3f sec" % (frame_number, diff_timestamp, audio_timestamp, one_frame.get("video_timestamp"))
                            logger.debug("%s" % string)
                            self.write_line(string, self._fd_result_log)
                            self.write_line("%s\t%s" % (audio_timestamp, diff_timestamp), self._fd_graph)
                            self._frames_with_freq.pop(index_video)
                            self._all_audio_buff.pop(index_audio)
                            self._audio_timestamp = audio_timestamp
                            self._qrcode_number = int(frame_number)
                            self._delay_audio_video.append(diff_timestamp)
                            return float(one_frame.get("freq_audio", 0))
                    else:
                        logger.warning("The Qrcode %s has already been analyzed" % (frame_number))
                        self._frames_with_freq.pop(index_video)
                        return -1
        return -1

    def _clean_all_list(self):
        if not self._found_qrcode_names:
            logger.warning('No expected qrcode %s detected' % self._expected_qrcode_name)
            for q in self._qrcode_names:
                if q not in self._found_qrcode_names:
                    logger.warning('Found unexpected qrcode name %s, you may want to run qr-lipsync-analyze.py with -q %s' % (q, q))
            logger.error('Exiting with error')
            sys.exit(1)

        logger.info('Reached the end of the media, cleaning')
        self._frames_with_freq.reverse()
        for one_frame in self._frames_with_freq:
            video_timestamp = one_frame['timestamp']
            freq_in_frame = one_frame['freq_audio']
            string = "The frame number %s at %.3f with the frequency %sHz already found" % (one_frame.get('frame_number'), video_timestamp, freq_in_frame)
            logger.debug("%s" % string)
            self.write_line(string, self._fd_result_log)
        # self._all_audio_buff.reverse()
        for one_audio_buf in self._all_audio_buff:
            freq_audio = one_audio_buf['freq_audio']
            audio_timestamp = one_audio_buf['timestamp']
            string = "No corresponding qrcode found for audio beep (%d Hz) at %.3fs" % (freq_audio, audio_timestamp)
            logger.info("%s" % string)
            self.write_line(string, self._fd_result_log)

    # Check if we have Qrcode without beep corresponding
    # in this case we show a warning and delete it of the list
    def _orphan_qrcode(self, freq_analyzed):
        for index, one_frame in enumerate(self._frames_with_freq):
            freq_in_frame = one_frame['freq_audio']
            video_timestamp = one_frame['timestamp']
            if video_timestamp + 1.0 < self._audio_timestamp:
                if freq_analyzed == float(freq_in_frame):
                    string = "The frame number %s at %.3f with the frequency %sHz already found, that means the beep with qrcode was duplicated" % (one_frame.get('frame_number'), video_timestamp, freq_in_frame)
                else:
                    string = "The frame number %s at %.3f has no corresponding beep, this should be %sHz" % (one_frame.get('frame_number'), video_timestamp, freq_in_frame)
                logger.debug("%s" % string)

                self._frames_with_freq.pop(index)
            else:
                logger.debug("Probably the audio beep has not happened yet or the audio video delay is upper than 1 secondes")

    # Check if we have beep without Qrcode corresponding
    # in this case we show a warning and delete it of the list
    def _orphan_beep(self):
        for index, one_audio_buf in enumerate(self._all_audio_buff):
            freq_audio = one_audio_buf['freq_audio']
            audio_timestamp = one_audio_buf['timestamp']
            if audio_timestamp + 1.0 < self._video_timestamp:
                audio_timestamp = one_audio_buf['timestamp']
                string = "The audio beep at %s has no corresponding qrcode, this should be %sHz, frame number should be %s" % (one_audio_buf.get('timestamp'), freq_audio, int(round(audio_timestamp / int(self._offset_video))))
                logger.debug("%s" % string)
                self.write_line(string, self._fd_result_log)
                self._all_audio_buff.pop(index)
            else:
                logger.debug("Probably the qrcode has not happened yet or the audio video delay is upper than 1 secondes")

    def _check_av_synchro(self):
        freq_corresponding = self._get_corresponding_freq()
        if freq_corresponding > 0 and len(self._frames_with_freq) > 0:
            self._orphan_qrcode(freq_corresponding)
        if freq_corresponding > 0 and len(self._all_audio_buff) > 0:
            self._orphan_beep()

    def parse_line(self, line):
        name = line.get('ELEMENTNAME')
        if name == 'qroverlay':
            self._total_frames += 1
            data_in_one_frame = self.get_qrcode_data(line)
            if data_in_one_frame:
                self._check_frame_number(data_in_one_frame)
        elif name == 'spectrum':
            audio_data = {}
            audio_data["timestamp"] = float(line['TIMESTAMP']) / 1000000000
            audio_data["peak_value"] = line['PEAK']
            audio_data["freq_audio"] = line['FREQ']
            self._all_audio_buff.insert(0, audio_data)
        else:
            if line.get('AUDIODURATION'):
                self._audio_duration = float(line['AUDIODURATION']) / 1000000000.0
            if line.get('VIDEODURATION'):
                self._video_duration = float(line['VIDEODURATION']) / 1000000000.0

        if len(self._frames_with_freq) > 0 and len(self._all_audio_buff) > 0:
            self._check_av_synchro()

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
