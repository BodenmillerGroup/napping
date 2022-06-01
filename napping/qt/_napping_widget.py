from typing import TYPE_CHECKING

import numpy as np
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from .. import NappingApplication


class ReadonlyQLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs) -> None:
        super(ReadonlyQLineEdit, self).__init__(*args, **kwargs)
        self.setMinimumWidth(400)
        self.setReadOnly(True)


class NappingWidget(QWidget):
    def __init__(self, app: "NappingApplication", **widget_kwargs) -> None:
        super(NappingWidget, self).__init__(**widget_kwargs)
        self._app = app
        self._refreshing = False

        self._source_img_file_label = ReadonlyQLineEdit(parent=self)
        self._target_img_file_label = ReadonlyQLineEdit(parent=self)
        self._control_points_file_label = ReadonlyQLineEdit(parent=self)
        self._joint_transform_file_label = ReadonlyQLineEdit(parent=self)
        self._source_coords_file_label = ReadonlyQLineEdit(parent=self)
        self._transf_coords_file_label = ReadonlyQLineEdit(parent=self)

        self._progress_label = QLabel(parent=self)
        self._point_count_label = QLabel(parent=self)
        self._residuals_mean_label = QLabel(parent=self)

        self._prev_button = QPushButton(parent=self)
        self._prev_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack)
        )
        self._prev_button.clicked.connect(self._on_prev_button_clicked)

        self._next_button = QPushButton(parent=self)
        self._next_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward)
        )
        self._next_button.clicked.connect(self._on_next_button_clicked)

        layout = QVBoxLayout()

        files_box = QGroupBox(parent=self)
        files_box_layout = QFormLayout()
        files_box_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        files_box_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        files_box_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        files_box_layout.addRow("Source image:", self._source_img_file_label)
        files_box_layout.addRow("Target image:", self._target_img_file_label)
        files_box_layout.addRow("Control points:", self._control_points_file_label)
        files_box_layout.addRow("Joint transform:", self._joint_transform_file_label)
        files_box_layout.addRow("Source coords:", self._source_coords_file_label)
        files_box_layout.addRow("Transf. coords:", self._transf_coords_file_label)
        files_box.setLayout(files_box_layout)
        layout.addWidget(files_box)

        status_box = QGroupBox(parent=self)
        status_box_layout = QFormLayout()
        status_box_layout.addRow("Progress:", self._progress_label)
        status_box_layout.addRow("Point count:", self._point_count_label)
        status_box_layout.addRow("Residuals mean:", self._residuals_mean_label)
        status_box.setLayout(status_box_layout)
        layout.addWidget(status_box)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self._prev_button)
        button_layout.addWidget(self._next_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def refresh(self) -> None:
        self._refreshing = True
        if self._app.navigator.current_source_img_file is not None:
            self._source_img_file_label.setText(
                self._app.navigator.current_source_img_file.name
            )
        else:
            self._source_img_file_label.setText(None)
        if self._app.navigator.current_target_img_file is not None:
            self._target_img_file_label.setText(
                self._app.navigator.current_target_img_file.name
            )
        else:
            self._target_img_file_label.setText(None)
        if self._app.navigator.current_control_points_file is not None:
            self._control_points_file_label.setText(
                self._app.navigator.current_control_points_file.name
            )
        else:
            self._control_points_file_label.setText(None)
        if self._app.navigator.current_joint_transform_file is not None:
            self._joint_transform_file_label.setText(
                self._app.navigator.current_joint_transform_file.name
            )
        else:
            self._joint_transform_file_label.setText(None)
        if self._app.navigator.current_source_coords_file is not None:
            self._source_coords_file_label.setText(
                self._app.navigator.current_source_coords_file.name
            )
        else:
            self._source_coords_file_label.setText(None)
        if self._app.navigator.current_transf_coords_file is not None:
            self._transf_coords_file_label.setText(
                self._app.navigator.current_transf_coords_file.name
            )
        else:
            self._transf_coords_file_label.setText(None)
        if len(self._app.navigator) > 0:
            self._progress_label.setText(
                f"{self._app.navigator.current_index + 1}"
                f"/{len(self._app.navigator)}"
            )
        else:
            self._progress_label.setText(None)
        current_control_points = self._app.get_current_control_points()
        if current_control_points is not None:
            self._point_count_label.setText(str(len(current_control_points.index)))
        else:
            self._point_count_label.setText(None)
        current_control_points_residuals = (
            self._app.get_current_control_point_residuals()
        )
        if current_control_points_residuals is not None:
            self._residuals_mean_label.setText(
                f"{np.mean(current_control_points_residuals):.6f}"
            )
        else:
            self._residuals_mean_label.setText(None)
        self._refreshing = False

    def _on_prev_button_clicked(self, checked: bool = False) -> None:
        self._app.navigator.prev()
        self._app.restart()

    def _on_next_button_clicked(self, checked: bool = False) -> None:
        self._app.navigator.next()
        self._app.restart()
