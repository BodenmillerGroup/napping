import napari

from qtpy.QtWidgets import QApplication, QMessageBox

from napping.napping import Napping, NappingException

try:
    from PIL import Image
except Exception:
    Image = None

# avoid DecompressionBombWarning for large images
if Image is not None:
    Image.MAX_IMAGE_PIXELS = None


def main():
    app = QApplication([])
    source_viewer = napari.Viewer(title="napping [source]")
    target_viewer = napari.Viewer(title="napping [target]")
    try:
        controller = Napping(source_viewer, target_viewer)
        controller.initialize()
        if not controller.show_dialog():
            QMessageBox.critical(
                source_viewer.window.qt_viewer,
                "napping error",
                "File matching aborted or no matching files found",
            )
            return
    except NappingException as e:
        QMessageBox.critical(
            source_viewer.window.qt_viewer, "napping exception", str(e)
        )
        return
    app.exec_()


if __name__ == "__main__":
    main()
