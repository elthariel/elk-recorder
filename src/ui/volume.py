import logging

import gi
from gi.repository import Gtk, Adw, Gst, Gio

logger = logging.getLogger(__name__)


class Volume(Gtk.Box):
    def __init__(self, parent, volume, *args, **kwargs):
        kwargs['orientation'] = Gtk.Orientation.HORIZONTAL
        super().__init__(*args, **kwargs)

        self.parent = parent
        self.volume = volume

        self.label = Gtk.Label.new(self.name)
        self.append(self.label)

        self.mount_btn = Gtk.Button.new()
        self.mount_btn.set_label("Mount")
        # self.mount_btn.set_icon_name("drive-removable-media")
        self.mount_btn.connect('clicked', self.on_mount_btn_clicked)
        self.append(self.mount_btn)

        self.eject_btn = Gtk.Button.new_from_icon_name('media-eject')
        self.eject_btn.connect('clicked', self.on_eject_btn_clicked)
        self.append(self.eject_btn)

        self.record_btn =  Gtk.Button.new_from_icon_name('media-record')
        self.record_btn.connect('clicked', self.on_record_btn_clicked)
        self.append(self.record_btn)

        self.on_changed()

    @property
    def name(self):
        return self.volume.get_name()

    @property
    def mounted(self):
        return self.volume.get_mount() is not None

    @property
    def mountable(self):
        return self.volume.can_mount()

    @property
    def ejectable(self):
        return self.volume.can_eject()

    def on_changed(self):
        self.mount_btn.props.sensitive = self.mountable and not self.mounted
        self.eject_btn.props.sensitive = self.mounted and self.ejectable

    def on_mount_callback(self, source_object, result, _):
        self.volume.mount_finish(result)

    def on_mount_btn_clicked(self, btn):
        logger.debug(f"Mount {self.name}")
        self.volume.mount(Gio.MountMountFlags.NONE, None, None, None, None)

    def on_eject_callback(self, source_object, result, _):
        self.volume.eject_with_operation_finish(result)

    def on_eject_btn_clicked(self, btn):
        logger.debug(f"Eject {self.name}")
        self.volume.eject_with_operation(
            Gio.MountUnmountFlags.NONE, None, None, self.on_eject_callback, None
        )

    def on_record_btn_clicked(self, btn):
        logger.debug(f"Record {self.name}")
