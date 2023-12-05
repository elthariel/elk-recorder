import logging

import gi
from gi.repository import GLib, Gtk, Adw, Gst

from .clock import Clock

logger = logging.getLogger(__name__)


class AudioControls(Gtk.Box):
    def __init__(self, app, *args, **kwargs):
        kwargs['orientation'] = Gtk.Orientation.VERTICAL
        super().__init__(*args, **kwargs)

        self.app = app
        self.devices = {}
        self.make_device_dropdown()
        self.make_device_monitor()
        self.app.pipeline.connect('state-changed', self.on_pipeline_state_changed)

        self.row = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 2)
        self.append(self.row)
        self.make_time_counter()
        self.make_buttons()

    def make_device_monitor(self):
        self.monitor = Gst.DeviceMonitor.new()
        self.monitor.add_filter("Audio/Source", None)

        monitor_bus = self.monitor.get_bus()
        monitor_bus.add_signal_watch()
        monitor_bus.connect('message', self.on_device_monitor_message)

        self.monitor.start()

    def make_device_dropdown(self):
        self.device_dropdown_label = Gtk.Label.new("Input")
        self.append(self.device_dropdown_label)
        # self.device_dropdown = Gtk.ComboBoxText()
        self.device_dropdown = Gtk.DropDown.new_from_strings([])
        # self.device_dropdown.props.sensitive = False
        self.device_dropdown.connect("notify::selected", self.on_device_selected)
        self.append(self.device_dropdown)

    def make_time_counter(self):
        self.clock = Clock()
        self.row.append(self.clock)
        GLib.timeout_add_seconds(1, self.update_time_counter)

    def make_buttons(self):
        self.stop_button = Gtk.Button.new_from_icon_name('media-playback-stop')
        self.stop_button.props.sensitive = False
        self.rec_button = Gtk.Button.new_from_icon_name('media-record')
        self.rec_button.props.sensitive = False

        self.row.append(self.stop_button)
        self.stop_button.connect('clicked', self.stop_button_clicked)
        self.row.append(self.rec_button)
        self.rec_button.connect('clicked', self.rec_button_clicked)

        self.dump_button = Gtk.Button.new_with_label('Dump pipeline')
        if self.app.debug:
            self.row.append(self.dump_button)
        self.dump_button.connect('clicked', self.dump_button_clicked)

    def update_time_counter(self):
        pos = self.app.pipeline.current_position

        if pos == -1:
            self.clock.set_time_in_seconds()
        else:
            self.clock.set_time_in_seconds(pos // Gst.SECOND)

        # The callback will be removed if we return a falsy value
        return True

    def rec_button_clicked(self, button):
        logger.debug('rec_button_clicked')
        self.app.pipeline.start()

    def stop_button_clicked(self, button):
        logger.debug('stop_button_clicked')
        self.app.pipeline.stop()

    def dump_button_clicked(self, button):
        logger.debug('Requested pipeline dump')
        self.app.pipeline.dump_dot()

    def on_device_monitor_message(self, bus, message):
        # The int cast works around the bug described in
        # https://bugzilla.gnome.org/show_bug.cgi?id=786948
        # This didn't exist in more recent versions of gst/gst-python
        t = int(message.type)

        if t == int(Gst.MessageType.DEVICE_ADDED):
            device = message.parse_device_added()
            self.on_device_added(device)
        elif t == int(Gst.MessageType.DEVICE_REMOVED):
            device = message.parse_device_removed()
            self.on_device_removed(device)

    def on_device_added(self, device):
        name = device.props.display_name
        logger.info(f"Discovered device: {name}")
        self.devices[name] = device
        self.device_dropdown.get_model().append(name)

    def on_device_removed(self, device):
        name = device.props.display_name
        logger.info(f"Device removed: {name}")

        idx = 0
        for row in self.device_dropdown.get_model():
            if row[0] == name:
                self.device_dropdown.get_model().remove(idx)
            idx += 1

        del self.devices[name]

    def on_device_selected(self, *args):
        name = self.device_dropdown.props.selected_item.props.string
        logger.debug(f"Selected device '{name}'")

        if name not in self.devices:
            logger.error(f"Device {name} not found")
            return

        device = self.devices[name]
        self.app.pipeline.select_device(device)
        self.rec_button.props.sensitive = True

    def on_pipeline_state_changed(self, _, old_state, new_state):
        logger.debug(f"State changed to {new_state}")

        # self.stop_button.props.sensitive = True
        if new_state == 'null':
            self.rec_button.props.sensitive = True
            self.stop_button.props.sensitive = False
        elif new_state == 'ready':
            self.rec_button.props.sensitive = False
            self.stop_button.props.sensitive = True
        elif new_state == 'paused':
            self.rec_button.props.sensitive = False
            self.stop_button.props.sensitive = True
            pass
        elif new_state == 'playing':
            self.rec_button.props.sensitive = False
            self.stop_button.props.sensitive = True
        else:
            logger.error(f"Unknown pipeline state: {new_state}")
