import sys

from qtpy.QtWidgets import QMessageBox

from ._napping_application import NappingApplication
from ._napping_exception import NappingException

try:
    from PIL import Image
except Exception:
    Image = None

# avoid DecompressionBombWarning for large images
if Image is not None:
    Image.MAX_IMAGE_PIXELS = None


def main():
    app = NappingApplication()
    try:
        app.exec_dialog()
    except NappingException as e:
        QMessageBox.critical(None, "napping exception", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
