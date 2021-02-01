import napari
import sys

from napari_imc import IMCController
from napari_imcreg import IMCRegController, IMCRegControllerException
from qtpy.QtCore import QTimer
from qtpy.QtWidgets import QMessageBox

try:
    from PIL import Image
except:
    Image = None

# fix DecompressionBombWarning for large images
if Image is not None:
    Image.MAX_IMAGE_PIXELS = None


def main() -> int:
    with napari.gui_qt() as app:
        source_viewer = napari.Viewer(title='Source')
        source_imc_controller = IMCController(source_viewer)
        source_imc_controller.initialize(show_open_imc_file_button=False)

        target_viewer = napari.Viewer(title='Target')
        target_imc_controller = IMCController(target_viewer)
        target_imc_controller.initialize(show_open_imc_file_button=False)

        def close_and_quit():
            source_viewer.close()
            target_viewer.close()
            QTimer().singleShot(1000, app.quit)

        try:
            controller = IMCRegController(source_imc_controller, target_imc_controller)
            controller.initialize()
            if not controller.show_dialog():
                QMessageBox.critical(source_viewer.window.qt_viewer, 'napari [IMC] Registration',
                                     'File matching aborted or no matching files found')
                close_and_quit()
                return 1
        except IMCRegControllerException as e:
            QMessageBox.critical(source_viewer.window.qt_viewer, 'napari [IMC] Registration', str(e))
            close_and_quit()
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
