from qtpy.QtCore import Qt, QObject
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import QHBoxLayout, QLabel, QPushButton, QStyle, QWidget
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from napping import Napping


class NappingWidget(QWidget):
    def __init__(self, view_controller: 'Napping.ViewController', parent: Optional[QObject] = None):
        # noinspection PyArgumentList
        super(NappingWidget, self).__init__(parent)
        self._view_controller = view_controller

        self._status_label = QLabel('Initializing', self)
        self._status_label.setAlignment(Qt.AlignCenter)

        self._prev_button = QPushButton(self)
        self._prev_button.setShortcut(QKeySequence(Qt.Key_Left))
        self._prev_button.setIcon(self.window().style().standardIcon(QStyle.SP_ArrowBack))

        self._next_button = QPushButton(self)
        self._next_button.setShortcut(QKeySequence(Qt.Key_Right))
        self._next_button.setIcon(self.window().style().standardIcon(QStyle.SP_ArrowForward))

        # noinspection PyUnusedLocal
        # noinspection PyUnresolvedReferences
        @self._prev_button.clicked.connect
        def on_prev_button_clicked(checked=False):
            view_controller.controller.show_prev()

        # noinspection PyUnusedLocal
        # noinspection PyUnresolvedReferences
        @self._next_button.clicked.connect
        def on_next_button_clicked(checked=False):
            view_controller.controller.show_next()

        layout = QHBoxLayout()
        layout.addStretch()
        # noinspection PyArgumentList
        layout.addWidget(self._prev_button)
        # noinspection PyArgumentList
        layout.addWidget(self._status_label)
        # noinspection PyArgumentList
        layout.addWidget(self._next_button)
        layout.addStretch()
        self.setLayout(layout)

    def refresh(self):
        path_name = self._view_controller.image_path.name
        num_control_points = self._view_controller.control_points.shape[0]
        text = f'{path_name}\n{num_control_points} points'
        if self._view_controller.controller.current_transform is not None:
            num_matched_control_points = self._view_controller.controller.current_matched_control_points.shape[0]
            residuals_mean = self._view_controller.controller.current_matched_control_points_residuals.mean()
            text += f' ({num_matched_control_points} matched, residuals mean: {residuals_mean:.2f})'
        else:
            text += f' (not enough matching points)'
        self._status_label.setText(text)
