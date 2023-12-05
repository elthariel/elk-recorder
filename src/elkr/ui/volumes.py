import logging

import gi
from gi.repository import Gtk, GLib, Gst, Gio

from .volume import Volume

logger = logging.getLogger(__name__)


class Volumes(Gtk.Box):
    def __init__(self, app, *args, **kwargs):
        kwargs['orientation'] = Gtk.Orientation.VERTICAL
        super().__init__(*args, **kwargs)

        self.app = app
        self.mon = Gio.VolumeMonitor.get()
        self.volumes = {}

        self.title_label = Gtk.Label.new()
        self.title_label.set_markup('<span size="small">Volumes</span>')
        self.title_label.props.margin_top = 4
        self.title_label.props.margin_bottom = 4
        self.append(self.title_label)

        self.no_volumes_label = Gtk.Label.new()
        self.no_volumes_label.set_markup(
            '<span color="grey" size="small">No drives found. Insert a storage device</span>'
        )
        self.no_volumes_label.set_margin_top(8)

        self.append(self.no_volumes_label)

        self.mon.connect('volume-added', self.on_volume_added)
        self.mon.connect('volume-changed', self.on_volume_changed)
        self.mon.connect('volume-removed', self.on_volume_removed)

        logger.debug("Volumes Manager created")
        for vol in self.mon.get_volumes():
            self.on_volume_added(self.mon, vol)

        GLib.timeout_add_seconds(1, self.on_time_callback)

    def on_time_callback(self):
        for _, volume in self.volumes.items():
            volume['widget'].on_time_callback()

        return True

    def on_volume_added(self, _, vol):
        logger.debug(f"Volume added: {vol.get_name()}")
        uuid = vol.get_identifier('uuid')
        widget = Volume(self, vol)

        self.volumes[uuid] = {
            'widget': widget,
            'volume': vol
        }

        self.no_volumes_label.hide()

        self.append(widget)

    def on_volume_changed(self, _, vol):
        logger.debug(f"Volume changed: {vol.get_name()}")
        uuid = vol.get_identifier('uuid')
        if uuid in self.volumes:
            self.volumes[uuid]['widget'].on_changed()

    def on_volume_removed(self, _, vol):
        logger.debug(f"Volume removed: {vol.get_name()}")
        uuid = vol.get_identifier('uuid')
        if uuid in self.volumes:
            self.remove(self.volumes[uuid]['widget'])
            del self.volumes[uuid]

        if len(self.volumes) == 0:
            self.no_volumes_label.show()
