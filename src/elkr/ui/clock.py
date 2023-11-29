import logging

import gi
from gi.repository import GLib, Gtk, Gst

logger = logging.getLogger(__name__)

NO_TIME = '-- : -- : --'
TIME_FMT = "{:02} : {:02} : {:02}"

class Clock(Gtk.Label):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.set_time_in_seconds()

    def set_time_in_seconds(self, seconds=None):
        if seconds is None or seconds < 0:
            self.set_text(NO_TIME)
        else:
            hours = (seconds // 3600)
            minutes = (seconds % 3600) // 60
            seconds = (seconds % 60)
            self.set_text(TIME_FMT.format(hours, minutes, seconds))
