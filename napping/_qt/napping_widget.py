from qtpy.QtCore import Qt, QObject
from qtpy.QtWidgets import QHBoxLayout, QLabel, QPushButton, QStyle, QWidget
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from napping import Napping


class NappingWidget(QWidget):
    def __init__(
        self,
        controller: "Napping.Controller",
        parent: Optional[QObject] = None,
    ):
        super(NappingWidget, self).__init__(parent)
        self._controller = controller

        self._status_label = QLabel("Initializing", self)
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._previous_button = QPushButton(self)
        self._previous_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack)
        )

        self._next_button = QPushButton(self)
        self._next_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward)
        )

        @self._previous_button.clicked.connect
        def on_previous_button_clicked(checked=False):
            controller.parent.show_previous()

        @self._next_button.clicked.connect
        def on_next_button_clicked(checked=False):
            controller.parent.show_next()

        layout = QHBoxLayout()
        layout.addStretch()
        layout.addWidget(self._previous_button)
        layout.addWidget(self._status_label)
        layout.addWidget(self._next_button)
        layout.addStretch()
        self.setLayout(layout)

    def refresh(self):
        img_file_name = self._controller.img_file.name
        num_control_points = self._controller.control_points.shape[0]
        text = f"{img_file_name}\n{num_control_points} points"
        if self._controller.parent.current_transform is not None:
            napping_instance = self._controller.parent
            num_matched_control_points = (
                napping_instance.current_matched_control_points.shape[0]
            )
            residuals_mean = (
                napping_instance.current_matched_control_point_residuals.mean()
            )
            text += (
                f" ({num_matched_control_points} matched, "
                f"residuals mean: {residuals_mean:.2f})"
            )
        else:
            text += " (not enough matching points)"
        self._status_label.setText(text)
