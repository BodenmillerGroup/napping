import napari

from qtpy.QtWidgets import QApplication, QMessageBox

from napping.napping import Napping, NappingException

try:
    # noinspection PyPackageRequirements
    from PIL import Image
except:
    Image = None

# fix DecompressionBombWarning for large images
if Image is not None:
    Image.MAX_IMAGE_PIXELS = None


def main() -> None:
    app = QApplication([])
    source_viewer = napari.Viewer(title='napping [source]')
    target_viewer = napari.Viewer(title='napping [target]')
    try:
        controller = Napping(source_viewer, target_viewer)
        controller.initialize()
        if not controller.show_dialog():
            # noinspection PyArgumentList
            QMessageBox.critical(source_viewer.window.qt_viewer, 'napping error',
                                 'File matching aborted or no matching files found')
            return
    except NappingException as e:
        # noinspection PyArgumentList
        QMessageBox.critical(source_viewer.window.qt_viewer, 'napping exception', str(e))
        return
    app.exec_()


if __name__ == '__main__':
    main()
