import os, sys, logging

try:
    import gi

    gi.require_version('GLib', '2.0')
    gi.require_version('GObject', '2.0')
    gi.require_version('Gst', '1.0')
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1' )

    from gi.repository import Gst
except ImportError:
    print("Please install gstreamer, its plugins and the following packages:")
    print("gobject-introspection python3-gi python3-gst-1.0")
    sys.exit(1)
except ValueError as err:
    print(f"Error loading the GI library: {err}")
    sys.exit(1)

from .app import App

DEFAULT_GST_DEBUG_DUMP_DOT_DIR = "/tmp/elkr-pipelines"

def debug_enabled():
    return 'ELKR_DEBUG' in os.environ and os.environ['ELKR_DEBUG'] == '1'

def setup_logging():
    level = logging.INFO
    if debug_enabled():
        level = logging.DEBUG

    logging.basicConfig(level=logging.DEBUG, format="[%(name)s] [%(levelname)8s] - %(message)s")
    return logging.getLogger(__name__)


def setup_gst_debug_dot_dir():
    if not "GST_DEBUG_DUMP_DOT_DIR" in os.environ:
        os.environ["GST_DEBUG_DUMP_DOT_DIR"] = DEFAULT_GST_DEBUG_DUMP_DOT_DIR
        if not os.path.exists(DEFAULT_GST_DEBUG_DUMP_DOT_DIR):
            os.makedirs(DEFAULT_GST_DEBUG_DUMP_DOT_DIR)
    return os.environ["GST_DEBUG_DUMP_DOT_DIR"]

def main():
    logger = setup_logging()

    logger.info("Starting ElkRecorder !")

    dst = setup_gst_debug_dot_dir()
    logger.debug(f"Dumping gst pipeline dot dumps to: {dst}")

    Gst.init(sys.argv)

    app = App(debug=debug_enabled(), application_id="io.lta.elk-recorder")
    app.run(sys.argv)
