import gi
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')
gi.require_version('Gst', '1.0')

from gi.repository import Gst, GObject, GLib, Adw

from .ui.main_window import MainWindow
from .pipeline import Pipeline

class App(Adw.Application):
    def __init__(self, debug=False, **kwargs):
        "Main application class"

        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

        self.debug = debug
        self.pipeline = Pipeline()

    def on_activate(self, app):
        self.main_win = MainWindow(
            application=app,
            title="ELK Recorder",
            fullscreened=False
        )
        self.main_win.present()
