import logging

import gi
from gi.repository import Gst, GObject, GLib, GstAudio

logger = logging.getLogger(__name__)

FILESINK_QUEUE_SIZE_BYTES = 32 * pow(1024, 1)

class Pipeline(GObject.Object):
    @GObject.Signal(name='state-changed', flags=GObject.SignalFlags.RUN_LAST,
                    arg_types=(str, str),
                    return_type=None)
    def state_changed(self, *args):
        # print("State changed signal", args)
        pass

    def __init__(self):
        "Create the ELK Recorder pipeline"
        super().__init__()

        self.pipeline = Gst.ElementFactory.make("pipeline", 'elkr-pipeline')
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message', self.on_bus_message)
        self.elements = {}
        self.filesinks = {}
        self.build_pipeline()

    def build_pipeline(self):
        self.make_and_add('capsfilter', 'src-caps')
        self.make_and_add('queue', 'input-queue')
        self.make_and_add('audioconvert', 'audioconvert')
        self.add(self.make_encoder(), 'encoder')
        self.make_and_add('tee', 'encoder-tee')
        self.make_and_add('fakesink', 'blackhole')

        self['src-caps'].link(self['input-queue'])

        self['input-queue'].link(self['audioconvert'])
        self['audioconvert'].link(self['encoder'])
        self['encoder'].link(self['encoder-tee'])
        self['encoder-tee'].link(self['blackhole'])


    def __getitem__(self, name):
        return self.elements[name]

    def add(self, element, name):
        logger.debug(f"Added '{name}' ({element})")
        if name in self.elements:
            raise KeyError("An element with the name {name} already exists")
        self.elements[name] = element
        self.pipeline.add(element)

    def make_and_add(self, kind, name):
        name = name.replace('_', '-')

        element = Gst.ElementFactory.make(kind, name)
        self.add(element, name)

        return element

    def make_encoder(self):
        element = Gst.ElementFactory.make("wavpackenc", None)
        element.props.md5 = True
        # A value from 1 to 4, with 1 being the fastest and 4 the highest compression ratio
        element.props.mode = 4
        return element

    @property
    def current_state(self):
        (_, current_state, pending_state) = self.pipeline.get_state(Gst.CLOCK_TIME_NONE)
        return current_state

    @property
    def current_position(self):
        _, position = self.pipeline.query_position(Gst.Format.TIME)
        return position

    def select_device(self, device):
        if self.current_state != Gst.State.NULL:
            logger.warning("Trying to change device while pipeline is not stopped")
            return

        if 'source' in self.elements and self.elements['source'] is not None:
            old_src = self.elements.pop('source')
            old_src.unlink(self['src-caps'])
            self.pipeline.remove(old_src)

        new_src = device.create_element()

        # Work around a bug in gstreamer pipewire implementation
        if new_src.__class__.__name__ == 'GstPipeWireSrc':
            logger.debug("Pipewire source, enabling 'always-copy' property")
            new_src.props.always_copy = True

        self.add(new_src, 'source')
        new_src.link(self['src-caps'])

    def start(self):
        self.pipeline.set_state(Gst.State.PLAYING)

    def stop(self):
        state = self.current_state
        res = self.pipeline.set_state(Gst.State.NULL)
        if res == Gst.StateChangeReturn.SUCCESS:
            self.emit(
                'state-changed',
                state.value_nick,
                Gst.State.NULL.value_nick
            )

    def pause(self):
        self.pipeline.set_state(Gst.State.PAUSED)

    def dump_dot(self):
        Gst.debug_bin_to_dot_file_with_ts(self.pipeline, Gst.DebugGraphDetails.ALL, 'pipeline')

    def on_bus_message(self, bus, message):
        t = message.type

        if t == Gst.MessageType.STATE_CHANGED:
            state = message.parse_state_changed()
            if message.src == self.pipeline:
                logger.debug(f"Pipeline state change from {state.oldstate} to {state.newstate}")
                self.emit('state-changed', state.oldstate.value_nick, state.newstate.value_nick)

    def add_filesink(self, path):
        logger.debug(f"Adding a filesink to {path}")

        sink = Gst.ElementFactory.make("filesink", None)
        sink.props.location = path
        queue = Gst.ElementFactory.make("queue", None)

        # Limit the size of the queue in bytes
        # queue.props.max_size_buffers = 0
        # queue.props.max_size_bytes = FILESINK_QUEUE_SIZE_BYTES
        # Drop new buffers when queue is full, preventing to block the whole pipeline if
        # a filesink is to slow.
        # queue.props.leaky = 1

        self.pipeline.add(sink)
        self.pipeline.add(queue)

        tee_pad = self['encoder-tee'].request_pad_simple('src_%u')
        if tee_pad is None:
            logger.error(f"Unable to request tee_pad for {path}")
            return
        queue_pad = queue.get_static_pad('sink')
        if (Gst.Pad.link(tee_pad, queue_pad) != 0):
            logger.error(f"Unable to link filesink pads for file {path}")
            return

        queue.link(sink)
        sink.set_state(Gst.State.PLAYING)
        queue.set_state(Gst.State.PLAYING)

        self.filesinks[path] = {
            'filesink': sink,
            'queue': queue,
            'tee_pad': tee_pad
        }

    def remove_filesink(self, path):
        logger.debug(f"Removing a filesink to {path}")

        if path not in self.filesinks:
            logger.error(f"Trying to remove a non existent filesink to {path}")
            return
        h = self.filesinks.pop(path)

        self['encoder-tee'].unlink(h['queue'])
        self['encoder-tee'].release_request_pad(h['tee_pad'])
        h['queue'].unlink(h['filesink'])

        h['queue'].set_state(Gst.State.NULL)
        h['filesink'].set_state(Gst.State.NULL)
        self.pipeline.remove(h['queue'])
        self.pipeline.remove(h['filesink'])
