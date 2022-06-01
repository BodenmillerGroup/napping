from pathlib import Path
from typing import Optional

from qtpy.QtWidgets import QFileDialog, QLineEdit, QStyle


class FileLineEdit(QLineEdit):
    def __init__(self, check_exists: bool = False, **line_edit_kwargs) -> None:
        super(FileLineEdit, self).__init__(**line_edit_kwargs)
        self._file_dialog = QFileDialog(self)
        self._file_dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
        self._browse_action = self.addAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self._browse_action.triggered.connect(self._on_browse_action_triggered)
        if check_exists:
            self.textChanged.connect(self._on_text_changed)

    def get_path(self) -> Optional[Path]:
        return Path(self.text()) if self.text() else None

    def set_path(self, path: Optional[Path]) -> None:
        self.setText(str(path) if path is not None else "")

    def _on_browse_action_triggered(self, checked=False) -> None:
        path = self.get_path()
        if path is not None:
            if path.parent.is_dir():
                self._file_dialog.setDirectory(str(path.parent))
            if path.exists():
                self._file_dialog.selectFile(str(path))
        if self._file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            selected_files = self._file_dialog.selectedFiles()
            self.setText(selected_files[0])

    def _on_text_changed(self, text) -> None:
        if not text or Path(text).exists():
            self.setStyleSheet("")
        else:
            self.setStyleSheet("background-color: #88ff0000")

    @property
    def file_dialog(self) -> QFileDialog:
        return self._file_dialog
