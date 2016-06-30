# QrLipsync

QrLipsync is an audio-video latency (also referred to as [lipsync](https://en.wikipedia.org/wiki/Lip_sync)) measurement and validation tool. 

It works by

* crafting a special video whose video and audio tracks contain encoded metadata (into a qrcode for the video, and as an easily detectable frequency)
* capturing this special video with a video playback or capture system
* extracting the encoded metadata by analyzing the recorded file audio and video
* computing statistics about the extracted data (actual framerate, frame drops/duplications, audio/video delay)

For instance, in order to validate a playback device (e.g. an embedded mediacenter), just playback the special media file generated with QrLipsync and capture the hdmi output using a validated capture device; analyzing the captured file will effectively measure how well the playback device did handle the a/v latency. Note that being qrcode-based, this method will work very well in degraded conditions, like filming a screen in a non-ortoghonal situation.

You can refer to [this talk](https://gstconf.ubicast.tv/videos/robust-lipsync-calibration-and-error-detection-using-gstreamer-and-qr-codes/) for details.

## Usage

### qr-lipsync-generate.py

Will build a cam1-qrcode.qt reference video

```$ ./qr-lipsync-generate.py```

![Screenshot of reference video](https://raw.githubusercontent.com/UbiCastTeam/qr-lipsync/master/sample.png)

### qr-lipsync-detect.py

Will extract metadata and write it into the cam1-qrcode_data.txt file

```$ ./qr-lipsync-detect.py cam1-qrcode.qt```

### qr-lipsync-analyze.py

```$ ./qr-lipsync-analyze.py cam1-qrcode_data.txt```

Sample output:

    INFO:qr-lipsync-analyze:Nb total duplicated frames : 0
    INFO:qr-lipsync-analyze:Nb total dropped frame : 0
    INFO:qr-lipsync-analyze:Avg framerate is 30.000
    INFO:qr-lipsync-analyze:Avg real framerate is 30.000
    INFO:qr-lipsync-analyze:Avg delay between beep and qrcode : 0.064 ms, video is late
    INFO:qr-lipsync-analyze:Max delay between beep and qrcode : 62.667 ms at 59.066666666 s
    INFO:qr-lipsync-analyze:Video duration is 59.967 sec
    INFO:qr-lipsync-analyze:Audio duration is 59.939 sec


## Dependencies

* python3 or python2.7
* gstreamer 1.0
* gobject-introspection
* [gst-qroverlay](https://github.com/UbiCastTeam/gst-qroverlay) gstreamer qrcode generation plugin
* [zbar](https://gstreamer.freedesktop.org/data/doc/gstreamer/head/gst-plugins-bad-plugins/html/gst-plugins-bad-plugins-zbar.html) qrcode extraction gstreamer plugin (included in by gst-plugins-bad)
