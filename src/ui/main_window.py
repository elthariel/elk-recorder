import gi
from gi.repository import Gtk, Adw

from .audio_controls import AudioControls
from .volumes import Volumes


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Things will go here

        self.main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(self.main_vbox)
        self.audio_controls = AudioControls(self.app)
        self.volumes = Volumes(self.app)
        self.main_vbox.append(self.audio_controls)
        self.main_vbox.append(self.volumes)

    @property
    def app(self):
        return self.props.application
