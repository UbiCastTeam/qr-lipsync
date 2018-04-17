#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2017, Florent Thiery

from setuptools import setup

setup(
    name='qrlipsync',
    version=1.0,
    description='Tool for checking A/V synchronization',
    url='https://github.com/UbiCastTeam/qr-lipsync',
    scripts=[
        'bin/qr-lipsync-analyze.py',
        'bin/qr-lipsync-detect.py',
        'bin/qr-lipsync-generate.py',
    ],
    setup_requires=[
        'setuptools >= 3.3',
    ],
    packages=['qrlipsync'],
    test_suite="tests"
)
