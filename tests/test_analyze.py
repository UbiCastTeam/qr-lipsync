#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2017, Florent Thiery
from unittest import TestCase
from qrlipsync.analyze import QrLipsyncAnalyzer
import logging
import sys


class Options():
    no_report_files = True
    qrcode_name = 'CAM1'
    custom_data_name = 'TICKFREQ'


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
    return q.get_results_dict()


class AnalyzeTest(TestCase):

    def test_normal(self):
        input_file = 'tests/normal_data.txt'
        r = analyze_file(input_file)
        self.assertIs(r['duplicated_frames'], 0)
        self.assertIs(r['dropped_frames'], 0)
        self.assertIs(r['median_av_delay_ms'], 0)
        self.assertIs(r['matching_missing'], 0)
        self.assertIs(r['av_delay_accel'], 0)

    def test_dropped(self):
        input_file = 'tests/dropped_data.txt'
        r = analyze_file(input_file)
        self.assertIs(r['duplicated_frames'], 0)
        self.assertIs(r['matching_missing'], 0)
        self.assertIs(r['dropped_frames'], 1)
        self.assertIs(r['av_delay_accel'], 0)

    def test_duplicated(self):
        input_file = 'tests/duplicated_data.txt'
        r = analyze_file(input_file)
        self.assertIs(r['duplicated_frames'], 1)
        self.assertIs(r['dropped_frames'], 1)
        self.assertIs(r['matching_missing'], 0)
        self.assertIs(r['av_delay_accel'], 0)

    def test_drift(self):
        input_file = 'tests/drift_data.txt'
        r = analyze_file(input_file)
        self.assertIs(r['duplicated_frames'], 0)
        self.assertIs(r['dropped_frames'], 0)
        self.assertIs(r['matching_missing'], 0)
        self.assertTrue(r['av_delay_accel'] > 0)
