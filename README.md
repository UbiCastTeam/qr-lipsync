# QrLipsync

Lip sync should be within +45 to -125 milliseconds for most people not to notice. Our brains are at least two times more sensitive to early audio than to late audio because audio doesn’t come before video in the natural world. Achieving good-enough lipsync (i.e. within this range) is necessary to ensure a good quality of experience for the viewers.

QrLipsync is an audio-video latency (also referred to as [lipsync](https://en.wikipedia.org/wiki/Lip_sync)) measurement and validation tool.

It works by

* crafting a special video whose video and audio tracks contain encoded metadata (into a qrcode for the video, and as an easily detectable frequency), a sample is available for download [here](https://drive.google.com/uc?id=1fyvn7-xKuPcDWNoair28FZCuUnwpAoZF&export=download)
* capturing this special video with a video playback or capture system
* extracting the encoded metadata by analyzing the recorded file audio and video
* computing statistics about the extracted data (actual framerate, frame drops/duplications, audio/video delay)

For instance, in order to validate a playback device (e.g. an embedded mediacenter), just playback the special media file generated with QrLipsync and capture the hdmi output using a validated capture device; analyzing the captured file will effectively measure how well the playback device did handle the a/v latency. Note that being qrcode-based, this method will work very well in degraded conditions, like filming a screen in a non-ortoghonal situation.

You can refer to [this talk](https://gstconf.ubicast.tv/videos/robust-lipsync-calibration-and-error-detection-using-gstreamer-and-qr-codes/) for details.

## Installation

Install the required packages; the following has been tested on ubuntu 18.04:
```
sudo apt install gstreamer1.0-plugins-{base,good,bad,ugly} gstreamer1.0-libav python3-gst-1.0 gstreamer1.0-tools python3-setuptools ffmpeg
```

```
sudo python setup.py install
```

Alternatively, you can run without installing with:
```
PATH=$PATH:bin PYTHONPATH=. qr-lipsync-generate.py
PATH=$PATH:bin PYTHONPATH=. qr-lipsync-detect.py cam1-qrcode-blue-30.qt
```

Or even
```
sudo ln -s `pwd`/bin/*.py /usr/local/bin
sudo ln -s `pwd`/qrlipsync `python -c "import site; print(site.getsitepackages()[0])"`
```

## Running tests

```
python setup.py test
```

## Usage

### Using with docker

To make it easier to get started, a docker-based execution is made possible.

First, build the docker image with:
```
make build_docker_img
```

Then generate a video with:
```
make generate
...
2019-12-11 10:24:02,846 qrcode_generator INFO     Rendering of cam1-qrcode-blue-30.qt took 3.19s (282 fps)
```

To measure lipsync, 
```
make analyze VIDEO=cam1-qrcode-blue-30.qt
...
2019-12-11 10:24:22,651 qr-lipsync-analyze INFO     Reading file /src/cam1-qrcode-blue-30_data.txt
2019-12-11 10:24:22,666 qr-lipsync-analyze INFO     Finished reading, took 0s
2019-12-11 10:24:22,666 qr-lipsync-analyze INFO     Checking AV sync
2019-12-11 10:24:22,667 qr-lipsync-analyze INFO     Checking video stats
2019-12-11 10:24:22,667 qr-lipsync-analyze INFO     Detected frame duration of 33.3ms
2019-12-11 10:24:22,668 qr-lipsync-analyze INFO     ---------------------------- Global report --------------------------
2019-12-11 10:24:22,668 qr-lipsync-analyze INFO     Total duplicated frames : 0/900 (0.0%)
2019-12-11 10:24:22,668 qr-lipsync-analyze INFO     Total dropped frames : 0/900 (0.0%)
2019-12-11 10:24:22,668 qr-lipsync-analyze INFO     Average framerate (based on qrcode content) is 30
2019-12-11 10:24:22,668 qr-lipsync-analyze INFO     Delay between beep and qrcode is perfect (0); average: 0.6ms (0.0 frames), max: 7ms at 0:0:23.007
2019-12-11 10:24:22,668 qr-lipsync-analyze INFO     Video duration is 30.0s (0:0:30.000)
2019-12-11 10:24:22,668 qr-lipsync-analyze INFO     Audio duration is 30.0s (0:0:30.000)
2019-12-11 10:24:22,668 qr-lipsync-analyze INFO     Missed 0 beeps out of 30 qrcodes (0%)
2019-12-11 10:24:22,668 qr-lipsync-analyze INFO     ---------------------------------------------------------------------
2019-12-11 10:24:22,669 qr-lipsync-analyze INFO     Wrote results as JSON into /src/cam1-qrcode-blue-30_data.report.json
```

Custom arguments can be provided with:

```
make analyze ARGS="-h"
usage: qr-lipsync-detect.py [-h] [-a AREA] [-s] [-d DOWNSCALE_WIDTH] [-p] [-v]
                            input_file

positional arguments:
  input_file            filename of video to analyze

optional arguments:
  -h, --help            show this help message and exit
  -a AREA, --area AREA  area in x1:y1:x2:y2 format (in percent) to look
                        qrcodes for; example: 0:30:30:80; reference is top
                        left corner (default: None)
  -s, --skip-results    do not display results right after analysis (default:
                        False)
  -d DOWNSCALE_WIDTH, --downscale-width DOWNSCALE_WIDTH
                        downscale picture to this width to speed up qrcode
                        lookup, 0 to disable (default: 320)
  -p, --preview         display a live preview of the analyzed area (default:
                        False)
  -v, --verbosity       increase output verbosity (default: False)
```

### qr-lipsync-generate.py

Will build a cam1-qrcode.qt reference video

```$ ./qr-lipsync-generate.py```

![Screenshot of reference video](https://raw.githubusercontent.com/UbiCastTeam/qr-lipsync/master/sample.png)

### qr-lipsync-detect.py

Will extract metadata and write it into the cam1-qrcode_data.txt file. Will run analysis too.

```$ ./qr-lipsync-detect.py cam1-qrcode.qt```

### qr-lipsync-analyze.py

Analyze results without re-detecting.

```$ ./qr-lipsync-analyze.py cam1-qrcode_data.txt```

Sample output:

```
2018-04-17 15:04:32,004 qr-lipsync-analyze INFO     ---------------------------- Global report --------------------------
2018-04-17 15:04:32,004 qr-lipsync-analyze INFO     Total duplicated frames : 0/900 (0.0%)
2018-04-17 15:04:32,004 qr-lipsync-analyze INFO     Total dropped frames : 0/900 (0.0%)
2018-04-17 15:04:32,004 qr-lipsync-analyze INFO     Avg real framerate (based on qrcode content) is 30
2018-04-17 15:04:32,004 qr-lipsync-analyze INFO     Delay between beep and qrcode is perfect (0) (median: 0ms (0.0 frames), max: 5ms at 0:0:10.005)
2018-04-17 15:04:32,004 qr-lipsync-analyze INFO     Video duration is 30.0s (0:0:30.000)
2018-04-17 15:04:32,004 qr-lipsync-analyze INFO     Audio duration is 30.0s (0:0:30.000)
2018-04-17 15:04:32,004 qr-lipsync-analyze INFO     Missed 0 beeps out of 30 qrcodes (0%)
2018-04-17 15:04:32,004 qr-lipsync-analyze INFO     ---------------------------------------------------------------------
```

## Dependencies

* python3
* gstreamer 1.0 with fdkaacenc
* gst-python (gobject introspection overrides)
* ffmpeg
* gobject-introspection
* [gst-qroverlay](https://github.com/UbiCastTeam/gst-qroverlay) gstreamer qrcode generation plugin
