#!/usr/bin/env python
import time
import logging
import os
import json
import statistics
import fractions
import numpy as np

logger = logging.getLogger("qr-lipsync-analyze")

SECOND = 1000000000
NAN = "could not measure"


class QrLipsyncAnalyzer:
    def __init__(self, input_file, options):
        self._input_file = input_file
        self.options = options

        self._fd_result_log = -1
        self._fd_graph = -1
        if not options.no_report_files:
            dirname = os.path.dirname(input_file)
            media_name = os.path.splitext(os.path.basename(input_file))[0]
            self._result_file = os.path.join(dirname, "%s.report.json" % media_name)
            self._result_log = os.path.join(dirname, "%s.report.txt" % media_name)
            self._result_graph_file = os.path.join(
                dirname, "%s.graph.txt" % (media_name)
            )

        self.expected_qrcode_name = options.qrcode_name
        self.custom_data_name = options.custom_data_name

        self.frame_duration_ms = 0
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
        self.audio_video_delays_tc = list()

    def start(self):
        result = 0
        logger.info("Reading file %s" % self._input_file)
        begin = time.time()

        with open(self._input_file, "r") as fd_input_file:
            if not self.options.no_report_files:
                self._fd_result_file = open(self._result_file, "w")
                self._fd_result_log = open(self._result_log, "w")
                self._fd_graph = open(self._result_graph_file, "w")
                self.write_graphfile("time\tdelay")
            try:
                fd_input_file.seek(0)
            except Exception as e:
                logger.error("Could not seek at the begining : %s" % e)
            result, line = self.read_and_parse_line(fd_input_file)
            while line and result == 0:
                if len(line) > 0:
                    self.parse_line(line)
                result, line = self.read_and_parse_line(fd_input_file)

        if result == 0:
            logger.info("Finished reading, took %is" % (time.time() - begin))
            self.check_av_sync()
            self.check_video_stats()
            result = self.check_qrcode_names()
        return result == 0

    def close_files(self):
        if not self.options.no_report_files:
            self._fd_result_file.close()
            self._fd_result_log.close()
            self._fd_graph.close()

    def get_qrcode_data(self, line):
        qrcode_name = line["NAME"]
        if qrcode_name not in self.qrcode_names:
            self.qrcode_names.append(qrcode_name)

        if qrcode_name == self.expected_qrcode_name:
            # timestamp in qrcode, converted to seconds
            decoded_timestamp = float(line["VIDEOTIMESTAMP"]) / SECOND
            # actual decoded buffer timestamp, converted to seconds
            current_timestamp = float(line["TIMESTAMP"]) / SECOND
            qrcode_frame_number = line["BUFFERCOUNT"]

            if (
                current_timestamp is None
                or qrcode_name is None
                or qrcode_frame_number is None
            ):
                logger.error(
                    "Skipping invalid line (timestamp, name or frame number missing)"
                )
                return

            qrcode = {
                "qrcode_timestamp": current_timestamp,
                "decoded_timestamp": decoded_timestamp,
                "qrcode_frame_number": qrcode_frame_number,
                "qrcode_name": qrcode_name,
                "qrcode_framerate": float(fractions.Fraction(line.get("FRAMERATE"))),
            }

            beep_freq = line.get(self.custom_data_name)
            if beep_freq is not None and len(beep_freq) > 0:
                qrcode["beep_freq"] = beep_freq
                if qrcode not in self.all_qrcodes_with_freq:
                    self.all_qrcodes_with_freq.append(qrcode)
            return qrcode

    def get_timecode_from_seconds(self, seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return "%i:%i:%.3f" % (hours, minutes, seconds)

    def check_qrcode_names(self):
        result = 0
        if self.expected_qrcode_name not in self.qrcode_names:
            logger.warning("No expected qrcode %s detected" % self.expected_qrcode_name)
            if self.qrcode_names:
                logger.info(
                    "Found unexpected qrcode names %s, you may want to run qr-lipsync-analyze.py with -q %s"
                    % (",".join(self.qrcode_names), self.qrcode_names[0])
                )
            logger.error("Exiting with error")
            result = 1
        return result

    def check_video_stats(self):
        logger.info("Checking video stats")
        # when capturing looped video samples, the frame count will reset to 1
        # this is expected behaviour but may be interpreted as backwards frames
        # we estimate that the sample is 30fps and is at least 10s long
        max_backwards_diff = -30 * 10
        start_timestamp = end_timestamp = None
        frame_duration = None

        qrcode_framerate = 0

        last_qrcode = None
        logger.info(f"Detected {len(self.all_qrcodes)} qrcodes and {len(self.all_audio_beeps)} beeps")
        for qrcode in self.all_qrcodes:
            if not self.frame_duration_ms:
                frame_duration = 1 / qrcode["qrcode_framerate"]
                self.frame_duration_ms = frame_duration * 1000
                logger.info(
                    "Detected original sample frame duration of %.1fms" % (self.frame_duration_ms)
                )

            timestamp = qrcode["decoded_timestamp"]
            if last_qrcode is not None:
                qrcode_frame_number = qrcode["qrcode_frame_number"]
                last_frame_nb = last_qrcode["qrcode_frame_number"]
                qrcode_frame_number_diff = qrcode_frame_number - last_frame_nb
                if qrcode_frame_number_diff == 1:
                    # normal behaviour
                    qrcode_framerate += 1
                elif qrcode_frame_number_diff > 1:
                    qrcode_framerate += 1
                    dropped_frames = qrcode_frame_number_diff - 1
                    self.dropped_frames_count += dropped_frames
                    logger.debug(
                        "%s dropped frame(s): %s > %s at %s"
                        % (
                            dropped_frames,
                            last_frame_nb,
                            qrcode_frame_number,
                            self.get_timecode_from_seconds(timestamp),
                        )
                    )
                elif qrcode_frame_number == last_frame_nb:
                    logger.debug(
                        "1 duplicated frame at  %s"
                        % self.get_timecode_from_seconds(timestamp)
                    )
                    self.duplicated_frames_count += 1
                elif qrcode_frame_number_diff < 0:
                    qrcode_framerate += 1
                    if qrcode_frame_number_diff > max_backwards_diff:
                        logger.warning(
                            "Backwards frame: %s > %s"
                            % (qrcode_frame_number, last_frame_nb)
                        )
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
        if len(self.all_qrcodes_with_freq) > 0:
            logger.info("Checking AV sync")
            # for each new qrcode found that contains frequency information
            for f in self.all_qrcodes_with_freq:
                qrcode_freq = int(f["beep_freq"])
                # actual buffer timestamp, not the one written in the qrcode
                qrcode_ts = f["decoded_timestamp"]
                audio_candidates = self.filter_audio_samples(
                    timestamp=qrcode_ts, width=5
                )
                ts = self.find_beep(audio_candidates, qrcode_freq)
                if ts:
                    # timestamps are in s
                    diff_ms = round((ts - qrcode_ts) * 1000)
                    logger.debug("Found beep at %ss, diff: %sms" % (ts, diff_ms))
                    self.write_graphfile("%s\t%s" % (ts, diff_ms))
                    self.audio_video_delays_ms.append(diff_ms)
                    self.audio_video_delays_tc.append(ts)
                    if abs(diff_ms) > abs(self.max_delay_ms):
                        self.max_delay_ms = diff_ms
                        self.max_delay_ts = ts
                else:
                    logger.warning(
                        "Did not find %s Hz beep at %s"
                        % (qrcode_freq, self.get_timecode_from_seconds(qrcode_ts))
                    )
                    self.missing_beeps_count += 1

    def filter_audio_samples(self, timestamp, width):
        # return audio buffers between timestamp - width and timestamp + width
        start = timestamp - width / 2
        end = timestamp + width / 2
        samples = [a for a in self.all_audio_beeps if start < a["timestamp"] < end]
        return samples

    def find_beep(self, audio_samples, frequency):
        threshold_hz = 50
        for i, item in enumerate(audio_samples):
            if abs(item["beep_freq"] - frequency) < threshold_hz:
                return audio_samples[i]["timestamp"]

    def parse_line(self, line):
        name = line.get("ELEMENTNAME")
        if name == "qrcode_detector":
            self.qrcode_frames_count += 1
            qrcode = self.get_qrcode_data(line)
            if qrcode:
                self.all_qrcodes.append(qrcode)
        elif name == "spectrum":
            audio_data = {}
            audio_data["timestamp"] = float(line["TIMESTAMP"]) / SECOND
            audio_data["peak_value"] = line["PEAK"]
            audio_data["beep_freq"] = line["FREQ"]
            self.all_audio_beeps.append(audio_data)
        else:
            if line.get("AUDIODURATION"):
                self.audio_duration_s = round(float(line["AUDIODURATION"]) / SECOND, 3)
            if line.get("VIDEODURATION"):
                self.video_duration_s = round(float(line["VIDEODURATION"]) / SECOND, 3)

    def read_and_parse_line(self, fd_input_file):
        result = 0
        json_line = None
        try:
            line = fd_input_file.readline()
            if line:
                try:
                    return result, json.loads(line)
                except Exception as e:
                    print("Failed to parse line %s : %s" % (repr(line), e))
        except UnicodeDecodeError:
            print("This file is not a text file, exiting")
            result = 1
        return result, json_line

    def write_line(self, line_content, dfile):
        if not self.options.no_report_files:
            if line_content is not None:
                line_content += "\n"
                dfile.write(line_content)
                dfile.flush()

    def write_logfile(self, line_content):
        logger.info(line_content)
        self.write_line(line_content, self._fd_result_log)

    def write_graphfile(self, line_content):
        self.write_line(line_content, self._fd_graph)

    def get_results_dict(self):
        avg_av_delay_ms = (
            self.get_mean(self.audio_video_delays_ms)
            if len(self.audio_video_delays_ms) > 0
            else NAN
        )
        avg_av_delay_frames = (
            self.get_ms_to_frames(avg_av_delay_ms) if avg_av_delay_ms != NAN else NAN
        )

        median_av_delay_ms = (
            self.get_median(self.audio_video_delays_ms, 0)
            if len(self.audio_video_delays_ms) > 0
            else NAN
        )
        median_av_delay_frames = (
            self.get_ms_to_frames(median_av_delay_ms)
            if median_av_delay_ms != NAN
            else NAN
        )

        results_dict = {
            "duplicated_frames": self.duplicated_frames_count,
            "duplicated_frames_percent": self.get_percent(
                self.duplicated_frames_count, self.qrcode_frames_count
            ),
            "dropped_frames": self.dropped_frames_count,
            "dropped_frames_percent": self.get_percent(
                self.dropped_frames_count, self.qrcode_frames_count
            ),
            "total_frames": self.qrcode_frames_count,
            "total_beeps": len(self.all_audio_beeps),
            "avg_real_framerate": self.get_mean(self.all_qrcode_framerates, 2),
            "median_av_delay_ms": median_av_delay_ms,
            "median_av_delay_frames": median_av_delay_frames,
            "avg_av_delay_ms": avg_av_delay_ms,
            "avg_av_delay_frames": avg_av_delay_frames,
            "av_delay_accel": self.get_accel(self.audio_video_delays_tc, self.audio_video_delays_ms),
            "max_delay_ms": self.max_delay_ms,
            "max_delay_ts": self.max_delay_ts,
            "video_duration": self.video_duration_s,
            "audio_duration": self.audio_duration_s,
            "matching_missing": self.missing_beeps_count,
        }
        return results_dict

    def get_exit_code(self, results):
        av_sync_metrics = [
            "median_av_delay_frames",
            "avg_av_delay_frames",
        ]
        for k in av_sync_metrics:
            if results.get(k) not in (None, NAN):
                if abs(results[k]) > self.options.desync_threshold_frames:
                    logger.error(f"AV sync metric {k} is over {self.options.desync_threshold_frames} ({results[k]}), exiting with error")
                    return 1
        if results.get("av_delay_accel", NAN) not in [0, NAN]:
            logger.error(f"Non-zero delay accel, audio or video is drifting by {results['av_delay_accel']} ms")
            return 1
        return 0

    def try_mean(self, list):
        result = 0
        if list:
            try:
                result = statistics.mean(list)
            except Exception as e:
                logger.error(f'statistics.mean failed: {e}')
                result = -1
        return result

    def get_mean(self, list, ndigits=2):
        return round(self.try_mean(list), ndigits)

    def get_median(self, list, ndigits=2):
        if ndigits != 0:
            return round(statistics.median(list), ndigits)
        else:
            return round(statistics.median(list))

    def get_percent(self, value, total, ndigits=1):
        return round(100 * value / total, ndigits)

    def get_ms_to_frames(self, value):
        return int(round(value / self.frame_duration_ms, 1))

    def get_accel(self, x_values, y_values):
        # we need enough samples so that +/- 1 frame is negligible
        num_samples = len(y_values)
        if num_samples:
            min_values = int(os.environ.get("QRLIPSYNC_MIN_ACCEL_SAMPLES", int(self.frame_duration_ms * 2)))
            if num_samples < min_values:
                logger.info(f"Got only {num_samples} samples, we need at least {min_values} samples to detect drifts")
                return 0
            else:
                order = 1
                result = np.polyfit(x_values, y_values, order)
                # we assume that beeps are every second, so this is a trend per second
                slope = result[-2]
                logger.debug("%.2f ms/s accel slope found" % slope)
                # ignore values below 1ms
            return int(slope)
        else:
            return NAN

    def show_summary_and_exit(self):
        results_dict = self.get_results_dict()
        self.write_logfile(
            "---------------------------- Global report --------------------------"
        )
        self.write_logfile(
            "Total duplicated frames : %s/%s (%s%%)"
            % (
                self.duplicated_frames_count,
                self.qrcode_frames_count,
                results_dict["duplicated_frames_percent"],
            )
        )
        self.write_logfile(
            "Total dropped frames : %s/%s (%s%%)"
            % (
                self.dropped_frames_count,
                self.qrcode_frames_count,
                results_dict["dropped_frames_percent"],
            )
        )
        self.write_logfile(
            "Average framerate (based on qrcode content) is %s"
            % results_dict["avg_real_framerate"]
        )
        if len(self.audio_video_delays_ms) > 0:
            median_value = results_dict["median_av_delay_ms"]
            median_value_frames = results_dict["median_av_delay_frames"]
            if int(round(median_value)) == 0:
                string_median_delay = "Delay between beep and qrcode is perfect (0)"
            else:
                string_median_delay = (
                    "Median delay between beep and qrcode : %d ms (%s frames)"
                    % (abs(median_value), abs(median_value_frames))
                )
                if median_value < 0:
                    string_median_delay += ", video is late"
                else:
                    string_median_delay += ", audio is late"
            string_median_delay += "; average: %sms (%.1f frames)" % (
                results_dict["avg_av_delay_ms"],
                results_dict["avg_av_delay_frames"],
            )
            if self.max_delay_ms:
                string_median_delay += ", max: %sms at %s" % (
                    self.max_delay_ms,
                    self.get_timecode_from_seconds(self.max_delay_ts),
                )
            self.write_logfile(string_median_delay)
            if results_dict["av_delay_accel"] not in [0, NAN]:
                self.write_logfile(
                    "Warning, %s ms/s drift detected" % results_dict["av_delay_accel"]
                )
        self.write_logfile(
            "Video duration is %ss (%s)"
            % (
                self.video_duration_s,
                self.get_timecode_from_seconds(self.video_duration_s),
            )
        )
        if self.audio_duration_s:
            self.write_logfile(
                "Audio duration is %ss (%s)"
                % (
                    self.audio_duration_s,
                    self.get_timecode_from_seconds(self.audio_duration_s),
                )
            )
            if len(self.all_qrcodes_with_freq) == 0:
                self.write_logfile("Found no qrcodes with freq, cannot measure lipsync")
            else:
                self.write_logfile(
                    "Missed %s beeps out of %s qrcodes (%i%%)"
                    % (
                        self.missing_beeps_count,
                        len(self.all_qrcodes_with_freq),
                        100
                        * self.missing_beeps_count
                        / len(self.all_qrcodes_with_freq),
                    )
                )
        else:
            self.write_logfile("No audio detected")
        self.write_logfile(
            "---------------------------------------------------------------------"
        )
        if not self.options.no_report_files:
            with open(self._result_file, "w") as f:
                json.dump(results_dict, f)
            logger.info("Wrote results as JSON into %s" % self._result_file)
        self.close_files()
        return self.get_exit_code(results_dict)
