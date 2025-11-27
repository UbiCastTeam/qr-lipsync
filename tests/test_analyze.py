from qrlipsync.analyze import QrLipsyncAnalyzer
import os

os.environ["QRLIPSYNC_MIN_ACCEL_SAMPLES"] = "1"


class Options():
    no_report_files = True
    qrcode_name = 'CAM1'
    custom_data_name = 'TICKFREQ'
    desync_threshold_frames = 0


def analyze_file(input_file):
    options = Options()
    q = QrLipsyncAnalyzer(input_file, options)
    q.start()
    results = q.get_results_dict()
    exit_code = q.get_exit_code(results)
    return results, exit_code


def test_normal():
    input_file = 'tests/normal_data.txt'
    results, exit_code = analyze_file(input_file)
    assert results['duplicated_frames'] == 0
    assert results['dropped_frames'] == 0
    assert results['median_av_delay_ms'] == 0
    assert results['matching_missing'] == 0
    assert results['av_delay_accel'] == 0
    assert results['median_av_delay_frames'] == 0
    assert exit_code == 0


def test_dropped():
    input_file = 'tests/dropped_data.txt'
    results, exit_code = analyze_file(input_file)
    assert results['duplicated_frames'] == 0
    assert results['matching_missing'] == 0
    assert results['dropped_frames'] == 1
    assert results['av_delay_accel'] == 0
    assert results['median_av_delay_frames'] == 0
    assert exit_code == 0


def test_duplicated():
    input_file = 'tests/duplicated_data.txt'
    results, exit_code = analyze_file(input_file)
    assert results['duplicated_frames'] == 1
    assert results['dropped_frames'] == 1
    assert results['matching_missing'] == 0
    assert results['av_delay_accel'] == 0
    assert results['median_av_delay_frames'] == 0
    assert exit_code == 0


def test_latency_bigger_than_one_frame():
    input_file = 'tests/latency_bigger_than_one_frame_data.txt'
    results, exit_code = analyze_file(input_file)
    assert results['duplicated_frames'] == 0
    assert results['dropped_frames'] == 0
    assert results['matching_missing'] == 0
    assert results['av_delay_accel'] == 0
    assert int(results['median_av_delay_ms']) == 50
    assert results['median_av_delay_frames'] == 1
    assert exit_code == 1


def test_drift():
    input_file = 'tests/drift_data.txt'
    results, exit_code = analyze_file(input_file)
    assert results['duplicated_frames'] == 0
    assert results['dropped_frames'] == 0
    assert results['median_av_delay_ms'] != 0
    assert results['matching_missing'] == 0
    assert results['av_delay_accel'] > 0
    assert exit_code == 1


def test_nobeeps():
    input_file = 'tests/nobeep_data.txt'
    results, exit_code = analyze_file(input_file)
    assert results['duplicated_frames'] == 0
    assert results['dropped_frames'] == 0
    assert results['median_av_delay_ms'] != 0
    assert results['matching_missing'] == 30
    assert results['av_delay_accel'] == "could not measure"
    assert exit_code == 0
