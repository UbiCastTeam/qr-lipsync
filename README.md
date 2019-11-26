# QrLipsync

Lip sync should be within +45 to -125 milliseconds for most people not to notice. Our brains are at least two times more sensitive to early audio than to late audio because audio doesn’t come before video in the natural world. Achieving good-enough lipsync (i.e. within this range) is necessary to ensure a good quality of experience for the viewers.

QrLipsync is an audio-video latency (also referred to as [lipsync](https://en.wikipedia.org/wiki/Lip_sync)) measurement and validation tool.

It works by

* crafting a special video whose video and audio tracks contain encoded metadata (into a qrcode for the video, and as an easily detectable frequency), a sample is available for download [here](https://u.nu/qrubi)
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
