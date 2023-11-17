import logging

import gi
from gi.repository import Gtk, Adw, Gst

logger = logging.getLogger(__name__)


class AudioControls(Gtk.Box):
    def __init__(self, app, *args, **kwargs):
        kwargs['orientation'] = Gtk.Orientation.HORIZONTAL
        super().__init__(*args, **kwargs)

        self.app = app
        self.devices = {}
        self.make_device_dropdown()
        self.make_device_monitor()
        self.make_buttons()

    def make_device_monitor(self):
        self.monitor = Gst.DeviceMonitor.new()
        self.monitor.add_filter("Audio/Source", None)

        monitor_bus = self.monitor.get_bus()
        monitor_bus.add_signal_watch()
        monitor_bus.connect('message', self.on_device_monitor_message)

        self.monitor.start()

    def make_device_dropdown(self):
        self.device_dropdown_label = Gtk.Label.new("Select Input")
        self.append(self.device_dropdown_label)
        self.device_dropdown = Gtk.ComboBoxText()
        # self.device_dropdown.props.sensitive = False
        self.append(self.device_dropdown)

    def make_buttons(self):
        self.rec_button = Gtk.Button.new_with_label('Record')
        self.rec_button.sensitive = False
        self.append(self.rec_button)
        self.rec_button.connect('clicked', self.rec_button_clicked)

        self.dump_button = Gtk.Button.new_with_label('Dump pipeline')
        if self.app.debug:
            self.append(self.dump_button)
        self.dump_button.connect('clicked', self.dump_button_clicked)

    def rec_button_clicked(self, button):
        logger.debug('rec_button_clicked')
        self.app.pipeline.start()

    def dump_button_clicked(self, button):
        logger.debug('dump_button_clicked')
        self.app.pipeline.dump_dot()

    def on_device_monitor_message(self, bus, message):
        t = message.type

        if t == Gst.MessageType.DEVICE_ADDED:
            device = message.parse_device_added()
            self.on_device_added(device)
        elif t == Gst.MessageType.DEVICE_REMOVED:
            device = message.parse_device_removed()
            self.on_device_removed(device)

    def on_device_added(self, device):
        name = device.props.display_name
        logger.info(f"Discovered device: {name}")
        self.devices[name] = device
        self.device_dropdown.append_text(name)

        # import pdb; pdb.set_trace()

    def on_device_removed(self, device):
        name = device.props.display_name
        logger.info(f"Device removed: {name}")

        idx = 0
        for row in self.device_dropdown.model:
            if row[0] == name:
                self.device_dropdown.remove(idx)
            idx += 1

        del self.devices[name]
