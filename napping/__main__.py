import napari
import sys

from qtpy.QtWidgets import QMessageBox

from napping.napping import Napping, NappingException

try:
    # noinspection PyPackageRequirements
    from PIL import Image
except:
    Image = None

# fix DecompressionBombWarning for large images
if Image is not None:
    Image.MAX_IMAGE_PIXELS = None


def main() -> int:
    source_viewer = napari.Viewer(title='napping [source]')
    target_viewer = napari.Viewer(title='napping [target]')
    napari.run()

    try:
        controller = Napping(source_viewer, target_viewer)
        controller.initialize()
        if not controller.show_dialog():
            # noinspection PyArgumentList
            QMessageBox.critical(source_viewer.window.qt_viewer, 'napping error',
                                 'File matching aborted or no matching files found')
            return 1
    except NappingException as e:
        # noinspection PyArgumentList
        QMessageBox.critical(source_viewer.window.qt_viewer, 'napping exception', str(e))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
