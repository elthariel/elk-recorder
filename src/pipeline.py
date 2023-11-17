import logging

import gi
from gi.repository import Gst, GObject, GLib, GstAudio

logger = logging.getLogger(__name__)

class Pipeline:
    def __init__(self):
        "Create the ELK Recorder pipeline"

        self.pipeline = Gst.ElementFactory.make("pipeline", 'elkr-pipeline')
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.elements = {}
        self.build_pipeline()

    def build_pipeline(self):
        self.make_and_add('capsfilter', 'src-caps')
        self.make_and_add('queue', 'input-queue')
        self.make_and_add('audioconvert', 'audioconvert')
        self.make_and_add('tee', 'encoder-tee')
        self.make_and_add('fakesink', 'blackhole')
        self.add('encoder', self.make_encoder())



    def __getitem__(self, name):
        return self.elements[name]

    def add(self, name, element):
        if name in self.elements:
            raise KeyError("An element with the name {name} already exists")
        self.elements[name] = element
        self.pipeline.add(element)

    def make_and_add(self, kind, name):
        name = name.replace('-', '_')

        element = Gst.ElementFactory.make(kind, name)
        self.add(name, element)

        return element

    def make_encoder(self):
        element = Gst.ElementFactory.make("wavpackenc", None)
        element.props.md5 = True
        # A value from 1 to 4, with 1 being the fastest and 4 the highest compression ratio
        element.props.mode = 4
        return element

    def start(self):
        self.pipeline.set_state(Gst.State.PLAYING)

    def stop(self):
        self.pipeline.set_state(Gst.State.NULL)

    def pause(self):
        self.pipeline.set_state(Gst.State.PAUSED)

    def dump_dot(self):
        Gst.debug_bin_to_dot_file_with_ts(self.pipeline, Gst.DebugGraphDetails.ALL, 'pipeline')
