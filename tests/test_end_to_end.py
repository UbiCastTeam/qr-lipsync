#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2017, Florent Thiery
from unittest import TestCase
from qrlipsync.analyze import QrLipsyncAnalyzer
import logging
import sys
import os
import subprocess
import shutil
import json

PROJECTPATH = os.path.abspath(__file__).split('tests')[0]


class Options():
    qrcode_name = 'CAM1'
    duration = 30
    disable_audio = False


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
    def setUp(self):
        os.mkdir('tmptest')
        os.chdir('tmptest')

    def tearDown(self):
        os.chdir('../')
        shutil.rmtree('tmptest')

    def run_cmd(self, cmd):
        status, output = subprocess.getstatusoutput('PYTHONPATH=%s %s/bin/%s' % (PROJECTPATH, PROJECTPATH, cmd))
        if status != 0:
            print(output)
        return status, output

    def test_generate_and_analyze_pcm(self):
        self.assertTrue(self.run_cmd('qr-lipsync-generate.py')[0] == 0)
        self.assertTrue(self.run_cmd('qr-lipsync-detect.py -s cam1-qrcode-blue-30.qt')[0] == 0)
        self.assertTrue(self.run_cmd('qr-lipsync-analyze.py cam1-qrcode-blue-30_data.txt')[0] == 0)
        with open('cam1-qrcode-blue-30_data.report.json', 'r') as f:
            r = json.load(f)

        self.assertTrue(r['duplicated_frames'] == 0)
        self.assertTrue(r['dropped_frames'] == 0)
        self.assertTrue(r['total_frames'] == 900)
        self.assertTrue(r['avg_real_framerate'] == 30)
        self.assertTrue(r['median_av_delay_ms'] == 0)
        self.assertTrue(r['video_duration'] == 30.0)
        self.assertTrue(r['audio_duration'] == 30.0)
        self.assertTrue(r['matching_missing'] == 0)

    def test_generate_and_analyze_aac(self):
        self.assertTrue(self.run_cmd('qr-lipsync-generate.py -f mp4')[0] == 0)
        self.assertTrue(self.run_cmd('qr-lipsync-detect.py -s cam1-qrcode-blue-30.mp4')[0] == 0)
        self.assertTrue(self.run_cmd('qr-lipsync-analyze.py cam1-qrcode-blue-30_data.txt')[0] == 0)
        with open('cam1-qrcode-blue-30_data.report.json', 'r') as f:
            r = json.load(f)

        self.assertTrue(r['duplicated_frames'] == 0)
        self.assertTrue(r['dropped_frames'] == 0)
        self.assertTrue(r['total_frames'] == 900)
        self.assertTrue(r['avg_real_framerate'] == 30)
        self.assertTrue(abs(r['median_av_delay_ms']) < 10)
        self.assertTrue(r['video_duration'] == 30.0)
        self.assertTrue(int(r['audio_duration']) == 30)
        self.assertTrue(r['matching_missing'] == 0)

    def test_generate_and_analyze_webm_vp8(self):
        self.assertTrue(self.run_cmd('qr-lipsync-generate.py -f webm+vp8')[0] == 0)
        self.assertTrue(self.run_cmd('qr-lipsync-detect.py -s cam1-qrcode-blue-30-vp8.webm')[0] == 0)
        self.assertTrue(self.run_cmd('qr-lipsync-analyze.py cam1-qrcode-blue-30-vp8_data.txt')[0] == 0)
        with open('cam1-qrcode-blue-30-vp8_data.report.json', 'r') as f:
            r = json.load(f)

        self.assertEqual(r['duplicated_frames'], 0)
        self.assertEqual(r['dropped_frames'], 0)
        self.assertEqual(r['total_frames'], 900)
        self.assertEqual(r['avg_real_framerate'], 29.97)
        self.assertLess(abs(r['median_av_delay_ms']), 10)
        self.assertEqual(r['video_duration'], 29.999)
        self.assertEqual(int(r['audio_duration']), 30)
        self.assertEqual(r['matching_missing'], 0)

    def test_generate_and_analyze_webm_vp9(self):
        self.assertTrue(self.run_cmd('qr-lipsync-generate.py -f webm+vp9')[0] == 0)
        self.assertTrue(self.run_cmd('qr-lipsync-detect.py -s cam1-qrcode-blue-30-vp9.webm')[0] == 0)
        self.assertTrue(self.run_cmd('qr-lipsync-analyze.py cam1-qrcode-blue-30-vp9_data.txt')[0] == 0)
        with open('cam1-qrcode-blue-30-vp9_data.report.json', 'r') as f:
            r = json.load(f)

        self.assertEqual(r['duplicated_frames'], 0)
        self.assertEqual(r['dropped_frames'], 0)
        self.assertEqual(r['total_frames'], 900)
        self.assertEqual(r['avg_real_framerate'], 29.97)
        self.assertLess(abs(r['median_av_delay_ms']), 10)
        self.assertEqual(r['video_duration'], 29.999)
        self.assertEqual(int(r['audio_duration']), 30)
        self.assertEqual(r['matching_missing'], 0)

    def test_generate_and_analyze_noaudio(self):
        self.assertTrue(self.run_cmd('qr-lipsync-generate.py -a')[0] == 0)
        self.assertTrue(self.run_cmd('qr-lipsync-detect.py -s cam1-qrcode-blue-30.qt')[0] == 0)
        self.assertTrue(self.run_cmd('qr-lipsync-analyze.py cam1-qrcode-blue-30_data.txt')[0] == 0)
        with open('cam1-qrcode-blue-30_data.report.json', 'r') as f:
            r = json.load(f)

        self.assertTrue(r['duplicated_frames'] == 0)
        self.assertTrue(r['dropped_frames'] == 0)
        self.assertTrue(r['total_frames'] == 900)
        self.assertTrue(r['avg_real_framerate'] == 30)
        self.assertTrue(r['video_duration'] == 30.0)
        self.assertTrue(r['audio_duration'] == 0)
        self.assertTrue(r['matching_missing'] == 0)
