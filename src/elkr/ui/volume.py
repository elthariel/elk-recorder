import os, logging, datetime

import gi
from gi.repository import Gtk, Gst, Gio

from .clock import Clock

logger = logging.getLogger(__name__)

RECORD_ICON = 'media-record'
STOP_ICON = 'media-playback-stop'

class Volume(Gtk.Box):
    def __init__(self, parent, volume, *args, **kwargs):
        kwargs['orientation'] = Gtk.Orientation.HORIZONTAL
        super().__init__(*args, **kwargs)

        self.parent = parent
        self.volume = volume
        self.record_path = None
        self.clock = None
        self.recorded_at = None

        self.label = Gtk.Label.new(self.name)
        self.append(self.label)

        self.make_buttons()

    def make_buttons(self):
        self.mount_btn = Gtk.Button.new()
        self.mount_btn.set_label("Mount")
        # self.mount_btn.set_icon_name("drive-removable-media")
        self.mount_btn.connect('clicked', self.on_mount_btn_clicked)
        self.append(self.mount_btn)

        self.eject_btn = Gtk.Button.new_from_icon_name('media-eject')
        self.eject_btn.connect('clicked', self.on_eject_btn_clicked)
        self.append(self.eject_btn)

        self.record_btn =  Gtk.Button.new_from_icon_name(RECORD_ICON)
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

        if self.record_path is None:
            self.add_filesink()
            self.record_btn.set_icon_name(STOP_ICON)
        else:
            self.remove_filesink()
            self.record_btn.set_icon_name(RECORD_ICON)

    def on_time_callback(self):
        if self.clock is not None and self.recorded_at is not None:
            dt = datetime.datetime.now()
            delta = dt - self.recorded_at
            self.clock.set_time_in_seconds(int(delta.total_seconds()))

        return True

    def make_record_path(self, record_dir, ext="wv", attempts=23):
        """
        Returns the path of a file to point the filesink to. The file name
        includes a timestamps to prevent collision, but if the file already exists, it
        attempts to find unique file names a few times.

        Returns None if no unique file name was available
        """
        now = datetime.datetime.now()
        ts = now.strftime("%y%m%d-%H%M%S")

        for attempt in range(attempts):
            suffix = "" if attempt == 0 else "-{attempt}"
            path = os.path.join(
                record_dir,
                f"elkr-{ts}{suffix}.{ext}"
            )

            if not os.path.exists(path):
                return path


    def add_filesink(self):
        if not self.mounted:
            logger.error(f"Trying to record on an unmounted volume {self.name}")
            return
        root = self.volume.get_mount().get_root().get_path()
        record_dir = os.path.join(root, 'elk-recorder')

        if not os.path.exists(record_dir):
            os.mkdir(record_dir)

        self.record_path = self.make_record_path(record_dir)
        if self.record_path is None:
            logger.error(f"Unable to find a non existent file name in {record_dir}")
            return

        self.parent.app.pipeline.add_filesink(self.record_path)
        self.eject_btn.props.sensitive = False
        self.recorded_at = datetime.datetime.now()

        self.start_clock()

    def remove_filesink(self):
        self.parent.app.pipeline.remove_filesink(self.record_path)
        self.eject_btn.props.sensitive = True
        self.record_path = None
        self.recorded_at = None
        self.stop_clock()

    def start_clock(self):
        self.clock = Clock()
        self.clock.set_time_in_seconds()
        self.append(self.clock)

    def stop_clock(self):
        if self.clock is None:
            return

        self.remove(self.clock)
