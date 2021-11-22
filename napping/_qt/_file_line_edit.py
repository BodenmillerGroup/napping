from pathlib import Path
from qtpy.QtWidgets import QFileDialog, QLineEdit, QStyle, QWidget
from typing import Optional


class FileLineEdit(QLineEdit):
    def __init__(
        self, check_exists: bool = False, parent: Optional[QWidget] = None
    ):
        super(FileLineEdit, self).__init__(parent)

        self._file_dialog = QFileDialog(self)
        self._file_dialog.setOption(QFileDialog.Option.DontUseNativeDialog)

        self._browse_action = self.addAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon),
            QLineEdit.ActionPosition.LeadingPosition,
        )

        @self._browse_action.triggered.connect
        def on_browse_action_triggered(checked=False):
            path = self.path
            if path is not None:
                if path.parent.is_dir():
                    self._file_dialog.setDirectory(str(path.parent))
                if path.exists():
                    self._file_dialog.selectFile(str(path))
            if self._file_dialog.exec() == QFileDialog.DialogCode.Accepted:
                selected_files = self._file_dialog.selectedFiles()
                self.setText(selected_files[0])

        if check_exists:

            @self.textChanged.connect
            def on_text_changed(text):
                if not text or Path(text).exists():
                    self.setStyleSheet("")
                else:
                    self.setStyleSheet("background-color: #88ff0000")

    @property
    def file_dialog(self) -> QFileDialog:
        return self._file_dialog

    @property
    def path(self) -> Optional[Path]:
        return Path(self.text()) if self.text() else None
