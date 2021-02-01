from typing import TYPE_CHECKING
from qtpy.QtCore import Qt
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import QHBoxLayout, QLabel, QPushButton, QStyle, QWidget

if TYPE_CHECKING:
    from napari_imcreg import IMCRegController


class RegistrationWidget(QWidget):
    def __init__(self, view_controller: 'IMCRegController.ViewController', parent=None):
        super(RegistrationWidget, self).__init__(parent)
        self._view_controller = view_controller

        self._status_label = QLabel('Initializing', self)
        self._status_label.setAlignment(Qt.AlignCenter)

        self._prev_button = QPushButton(self)
        self._prev_button.setShortcut(QKeySequence(Qt.Key_Left))
        self._prev_button.setIcon(self.window().style().standardIcon(QStyle.SP_ArrowBack))

        self._next_button = QPushButton(self)
        self._next_button.setShortcut(QKeySequence(Qt.Key_Right))
        self._next_button.setIcon(self.window().style().standardIcon(QStyle.SP_ArrowForward))

        # noinspection PyUnresolvedReferences
        @self._prev_button.clicked.connect
        def on_prev_button_clicked(checked=False):
            view_controller.controller.show_prev()

        # noinspection PyUnresolvedReferences
        @self._next_button.clicked.connect
        def on_next_button_clicked(checked=False):
            view_controller.controller.show_next()

        layout = QHBoxLayout()
        layout.addStretch()
        layout.addWidget(self._prev_button)
        layout.addWidget(self._status_label)
        layout.addWidget(self._next_button)
        layout.addStretch()
        self.setLayout(layout)

    def refresh(self):
        path_name = self._view_controller.image_path.name
        num_control_points = self._view_controller.control_points.shape[0]
        text = f'{path_name}\n{num_control_points} points'
        if self._view_controller.controller.current_transform is not None:
            num_matched_control_points = self._view_controller.controller.matched_control_points.shape[0]
            residuals_mean = self._view_controller.controller.current_residuals.mean()
            text += f' ({num_matched_control_points} matched, residuals mean: {residuals_mean:.2f})'
        else:
            text += f' (not enough matching points)'
        self._status_label.setText(text)

