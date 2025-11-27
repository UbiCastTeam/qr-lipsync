import os
import subprocess
import shutil
import json

import pytest


@pytest.fixture(autouse=True)
def tmp_work_dir():
    os.mkdir('tmptest')
    os.chdir('tmptest')
    yield
    os.chdir('../')
    shutil.rmtree('tmptest')


def run_cmd(cmd):
    p = subprocess.run(
        f'python3 ../qrlipsync/scripts/{cmd}'.split(' '),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60, text=True
    )
    if p.returncode != 0:
        print(p.stdout)
    return p.returncode, p.stdout


def test_generate_and_analyze_pcm():
    assert run_cmd('generate.py')[0] == 0
    assert run_cmd('detect.py -s cam1-qrcode-blue-30.qt')[0] == 0
    assert run_cmd('analyze.py cam1-qrcode-blue-30_data.txt')[0] == 0
    with open('cam1-qrcode-blue-30_data.report.json', 'r') as f:
        r = json.load(f)

    assert r['duplicated_frames'] == 0
    assert r['dropped_frames'] == 0
    assert r['total_frames'] == 900
    assert r['avg_real_framerate'] == 30
    assert r['median_av_delay_ms'] == 0
    assert r['video_duration'] == 30.0
    assert r['audio_duration'] == 30.0
    assert r['matching_missing'] == 0


def test_generate_and_analyze_aac():
    assert run_cmd('generate.py -f mp4')[0] == 0
    assert run_cmd('detect.py -s cam1-qrcode-blue-30.mp4')[0] == 0
    assert run_cmd('analyze.py cam1-qrcode-blue-30_data.txt')[0] == 0
    with open('cam1-qrcode-blue-30_data.report.json', 'r') as f:
        r = json.load(f)

    assert r['duplicated_frames'] == 0
    assert r['dropped_frames'] == 0
    assert r['total_frames'] == 900
    assert r['avg_real_framerate'] == 30
    assert abs(r['median_av_delay_ms']) < 10
    assert r['video_duration'] == 30.0
    assert int(r['audio_duration']) == 30
    assert r['matching_missing'] == 0


def test_generate_and_analyze_webm_vp8():
    assert run_cmd('generate.py -f webm+vp8')[0] == 0
    assert run_cmd('detect.py -s cam1-qrcode-blue-30-vp8.webm')[0] == 0
    assert run_cmd('analyze.py cam1-qrcode-blue-30-vp8_data.txt')[0] == 0
    with open('cam1-qrcode-blue-30-vp8_data.report.json', 'r') as f:
        r = json.load(f)

    r['duplicated_frames'] == 0
    r['dropped_frames'] == 0
    r['total_frames'] == 900
    r['avg_real_framerate'] == 29.97
    assert abs(r['median_av_delay_ms']) < 10
    r['video_duration'] == 30.0
    int(r['audio_duration']) == 30
    r['matching_missing'] == 0


def test_generate_and_analyze_webm_vp9():
    assert run_cmd('generate.py -f webm+vp9')[0] == 0
    assert run_cmd('detect.py -s cam1-qrcode-blue-30-vp9.webm')[0] == 0
    assert run_cmd('analyze.py cam1-qrcode-blue-30-vp9_data.txt')[0] == 0
    with open('cam1-qrcode-blue-30-vp9_data.report.json', 'r') as f:
        r = json.load(f)

    r['duplicated_frames'] == 0
    r['dropped_frames'] == 0
    r['total_frames'] == 900
    r['avg_real_framerate'] == 29.97
    assert abs(r['median_av_delay_ms']) < 10
    r['video_duration'] == 30.0
    int(r['audio_duration']) == 30
    r['matching_missing'] == 0


def test_generate_and_analyze_noaudio():
    assert run_cmd('generate.py -a')[0] == 0
    assert run_cmd('detect.py -s cam1-qrcode-blue-30.qt')[0] == 0
    assert run_cmd('analyze.py cam1-qrcode-blue-30_data.txt')[0] == 0
    with open('cam1-qrcode-blue-30_data.report.json', 'r') as f:
        r = json.load(f)

    assert r['duplicated_frames'] == 0
    assert r['dropped_frames'] == 0
    assert r['total_frames'] == 900
    assert r['avg_real_framerate'] == 30
    assert r['video_duration'] == 30.0
    assert r['audio_duration'] == 0
    assert r['matching_missing'] == 0
