#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# * This Program is free software; you can redistribute it and/or
# * modify it under the terms of the GNU Lesser General Public
# * License as published by the Free Software Foundation; either
# * version 2.1 of the License, or (at your option) any later version.
# *
# * Libav is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# * Lesser General Public License for more details.
# *
# * You should have received a copy of the GNU Lesser General Public
# * License along with Libav; if not, write to the Free Software
# * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""
Gstmanager: convenience fonctions for Gstreamer pipeline manipulation
Copyright 2009, Florent Thiery, under the terms of LGPL
Copyright 2013, Dirk Van Haerenborgh, under the terms of LGPL
"""
__author__ = ("Florent Thiery <fthiery@gmail.com>", "Dirk Van Haerenborgh <vhdirk@gmail.com>")

import os
import logging
logger = logging.getLogger('Gstmanager')

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst


pipeline_desc = "videotestsrc ! xvimagesink"
try:
    import easyevent
    easyevent.dispatcher = 'gobject'
except Exception:
    from . import event as easyevent
    easyevent.dispatcher = 'gobject'


class PipelineManager(easyevent.User):
    def __init__(self, pipeline_string=None, name=None):
        easyevent.User.__init__(self)
        Gst.init(None)
        self.send_debug = False
        self.name = name
        if pipeline_string is not None:
            self.parse_description(pipeline_string)
        else:
            if name is not None:
                self.pipeline = Gst.Pipeline(name)
            else:
                self.pipeline = Gst.Pipeline()
            self.activate_bus()

    def get_name(self):
        if hasattr(self, "pipeline"):
            return self.pipeline.get_name()

    def redefine_pipeline(self, widget=None, new_string=None):
        if new_string is None:
            new_string = self.pipeline_desc
            logger.debug("Reinitializing pipeline")
        else:
            logger.debug('Redefining pipeline {0} pipeline to {1}'.format(self.pipeline.get_name(), new_string))
        self.parse_description(new_string)

    def is_running(self):
        if hasattr(self, "pipeline"):
            if self.get_state() == Gst.State.PLAYING:
                logger.debug("Pipeline is up and running")
                return True
            else:
                logger.debug("Pipeline is not in running state")
                return False
        else:
                logger.debug("Pipeline has not been initialized yet")
                return False

    def parse_description(self, string):
        self.pipeline_desc = string
        try:
            self.pipeline = Gst.parse_launch(string)
        except Exception as e:
            if self.name is not None:
                e = "{0} : {1}".format(self.name, e)
            logger.error('Error in parse_description: {0}'.format(e))
            self.launch_event('gst_error', str(e))
            return
        if self.name is not None:
            self.pipeline.set_name(self.name)
        hstring = self.get_pastable_string(string)
        logger.debug("Launching pipeline {0}; copy-paste the following for manual debugging: \n\ngst-launch-1.0 {1}\n".format(self.pipeline.get_name(), hstring))
        self.activate_bus()

    def activate_bus(self):
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message', self.on_message)

    def run(self, *args):
        logger.info("Starting pipeline {0}".format(self.pipeline.get_name()))
        self.launch_event("sos", self.pipeline)
        self.pipeline.set_state(Gst.State.PLAYING)
        return False

    def play(self, *args):
        self.run()

    def pause(self, *args):
        logger.info("Pausing pipeline")
        self.pipeline.set_state(Gst.State.PAUSED)

    def stop(self, *args):
        if hasattr(self, 'pipeline'):
            logger.info("Stopping pipeline {0}".format(self.pipeline.get_name()))
            self.pipeline.set_state(Gst.State.NULL)
        else:
            logger.error('Cannot stop non-running pipeline')

    def get_state(self, *args):
        state = self.pipeline.get_state(Gst.CLOCK_TIME_NONE)[1]
        return state.value_name

    def get_position(self, *args):
        try:
            position = self.pipeline.query_position(Gst.Format.TIME)[0]
            return self.convert_time_to_seconds(position)
        except Gst.QueryError:
            logger.error('Position query failed')
            return 0

    def get_duration(self, *args):
        try:
            duration = self.pipeline.query_duration(Gst.Format.TIME)[0]
            return self.convert_time_to_seconds(duration)
        except Gst.QueryError:
            logger.error('Duration query failed')
            return 0

    def has_duration(self):
        duration = self.pipeline.query_duration(Gst.Format.TIME)[0]
        logger.info(duration)
        if duration != -1:
            return True
        else:
            return False

    def seek_seconds(self, widget, getter):
        logger.info("Trying to seek to {0}".format(getter()))
        self.pipeline.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, getter() * 1000000000)

    def send_eos(self, *args):
        logger.info("Sending EOS")
        event = Gst.Event.new_eos()
        Gst.Element.send_event(self.pipeline, event)

    def set_caps(self, caps_name="capsfilter", caps=None):
        logger.info("Setting caps {0} on capsfilter named {1}".format(caps, caps_name))
        capsfilter = self.pipeline.get_by_name(caps_name)
        GstCaps = Gst.caps_from_string(caps)
        capsfilter.set_property("caps", GstCaps)

    def set_property_on_element(self, element_name="whatever", property_name="property", value="value"):
        logger.debug("Setting value {0} to property {1} of element {2}" .format(value, property_name, element_name))
        elt = self.pipeline.get_by_name(element_name)
        elt.set_property(property_name, value)

    def get_property_on_element(self, element_name="whatever", property_name="property"):
        elt = self.pipeline.get_by_name(element_name)
        result = elt.get_property(property_name)
        logger.debug("Getting value of property {0} of element {1}: {2}".format(property_name, element_name, result))
        return returnesult

    def activate_caps_reporting_on_element(self, element_name="whatever"):
        logger.debug("Activating caps reporting on element {0}".format(element_name))
        elt = self.pipeline.get_by_name(element_name)
        out_pad = elt.get_static_pad("src")
        caps = out_pad.query_caps()
        # let = new Gst.CapsFeatures();
        self.send_caps(out_pad, caps)
        # out_pad.set_setcaps_function(self.send_caps)
        # out_pad.set_activate_function_full(self.send_caps)


    def activate_polling_of_property_on_element(self, element_name="whatever", property="property", interval_ms=1000):
        GObject.timeout_add(interval_ms, self.poll_property, element_name, property)
        self.do_poll = True

    def deactivate_pollings(self):
        self.do_poll = False

    def poll_property(self, element_name, property):
        value = self.get_property_on_element(element_name, property)
        self.launch_event("{0}_value_change".format(property), {"source": element_name, "property": property, "value": value})
        return self.do_poll

    def send_caps(self, pad, caps):
        logger.debug("Got negociated caps")
        caps = pad.query_caps()
        caps_str = caps.to_string()
        self.launch_event("caps", caps_str)
        return True

    def on_message(self, bus, message):
        t = message.type
        # print t
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            error_string = "{0} {1}".format(err, debug)
            logger.info("Error: {0}".format(error_string))
            self.launch_event("gst_error", error_string)
        elif t == Gst.MessageType.EOS:
            self.launch_event("eos", self.pipeline.get_name())
        elif t == Gst.MessageType.ELEMENT:
            name = message.get_structure().get_name()
            res = message.get_structure()
            source = message.src.get_name()  # (str(message.src)).split(":")[2].split(" ")[0]
            self.launch_event(name, {"source": source, "data": res})
            self.launch_event('gst_element_message', {"source": source, "name": name, "data": res})
        else:
            if self.send_debug:
                logger.debug("got unhandled message type {0}, structure {1}".format(t, message))

    def dump_dot_file(self, basename='pipeline'):
        directory = os.environ.get('GST_DEBUG_DUMP_DOT_DIR', os.getcwd())
        if directory:
            dotfile = os.path.join(directory, '{0}.dot'.format(basename))
            if os.path.isfile(dotfile):
                logger.debug('Removing existing dotfile {0}'.format(dotfile))
                os.remove(dotfile)
            logger.debug('Dumping graph to {0}'.format(dotfile))
            Gst.debug_bin_to_dot_file(self.pipeline, Gst.DebugGraphDetails.ALL, basename)
            return dotfile
        else:
            logger.error('You need to define the Gst_DEBUG_DUMP_DOT_DIR env var to dump a .dot graph of the running pipeline')
            return None

    def convert_time_to_seconds(self, time):
        if time == -1:
            time = "infinite"
        else:
            time = time / 1000000000
        return time

    def get_pastable_string(self, string):
        hstring = string
        parts = string.split(" ! ")
        for part in parts:
            if part.startswith("video/") or part.startswith("audio/") or part.startswith("image/"):
                hpart = '"{0}"'.format(part)
                hstring = hstring.replace(part, hpart)
        return hstring
