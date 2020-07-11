#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2017, Florent Thiery
from unittest import TestCase
from qrlipsync.analyze import QrLipsyncAnalyzer
import logging
import sys
import os

os.environ["QRLIPSYNC_MIN_ACCEL_SAMPLES"] = "1"


class Options():
    no_report_files = True
    qrcode_name = 'CAM1'
    custom_data_name = 'TICKFREQ'
    desync_threshold_frames = 0


def setUpModule():
    level = 'ERROR'
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        stream=sys.stderr
    )


def analyze_file(input_file):
    options = Options()
    q = QrLipsyncAnalyzer(input_file, options)
    q.start()
    results = q.get_results_dict()
    exit_code = q.get_exit_code(results)
    return results, exit_code


class AnalyzeTest(TestCase):

    def test_normal(self):
        input_file = 'tests/normal_data.txt'
        results, exit_code = analyze_file(input_file)
        self.assertIs(results['duplicated_frames'], 0)
        self.assertIs(results['dropped_frames'], 0)
        self.assertIs(results['median_av_delay_ms'], 0)
        self.assertIs(results['matching_missing'], 0)
        self.assertIs(results['av_delay_accel'], 0)
        self.assertIs(results['median_av_delay_frames'], 0)
        self.assertIs(exit_code, 0)

    def test_dropped(self):
        input_file = 'tests/dropped_data.txt'
        results, exit_code = analyze_file(input_file)
        self.assertIs(results['duplicated_frames'], 0)
        self.assertIs(results['matching_missing'], 0)
        self.assertIs(results['dropped_frames'], 1)
        self.assertIs(results['av_delay_accel'], 0)
        self.assertIs(results['median_av_delay_frames'], 0)
        self.assertIs(exit_code, 0)

    def test_duplicated(self):
        input_file = 'tests/duplicated_data.txt'
        results, exit_code = analyze_file(input_file)
        self.assertIs(results['duplicated_frames'], 1)
        self.assertIs(results['dropped_frames'], 1)
        self.assertIs(results['matching_missing'], 0)
        self.assertIs(results['av_delay_accel'], 0)
        self.assertIs(results['median_av_delay_frames'], 0)
        self.assertIs(exit_code, 0)

    def test_latency_bigger_than_one_frame(self):
        input_file = 'tests/latency_bigger_than_one_frame_data.txt'
        results, exit_code = analyze_file(input_file)
        self.assertIs(results['duplicated_frames'], 0)
        self.assertIs(results['dropped_frames'], 0)
        self.assertIs(results['matching_missing'], 0)
        self.assertIs(results['av_delay_accel'], 0)
        self.assertTrue(int(results['median_av_delay_ms']) == 50)
        self.assertIs(results['median_av_delay_frames'], 1)
        self.assertIs(exit_code, 1)

    def test_drift(self):
        input_file = 'tests/drift_data.txt'
        results, exit_code = analyze_file(input_file)
        self.assertIs(results['duplicated_frames'], 0)
        self.assertIs(results['dropped_frames'], 0)
        self.assertTrue(results['median_av_delay_ms'] != 0)
        self.assertIs(results['matching_missing'], 0)
        self.assertTrue(results['av_delay_accel'] > 0)
        self.assertIs(exit_code, 1)

    def test_nobeeps(self):
        input_file = 'tests/nobeep_data.txt'
        results, exit_code = analyze_file(input_file)
        self.assertIs(results['duplicated_frames'], 0)
        self.assertIs(results['dropped_frames'], 0)
        self.assertTrue(results['median_av_delay_ms'] != 0)
        self.assertIs(results['matching_missing'], 30)
        self.assertTrue(results['av_delay_accel'] == "could not measure")
        self.assertIs(exit_code, 0)
