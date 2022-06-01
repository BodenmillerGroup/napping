from enum import Enum, IntEnum
from os import PathLike
from pathlib import Path
from typing import Optional, Union

from qtpy.QtCore import QSettings, Qt
from qtpy.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
)

from ._file_line_edit import FileLineEdit


class NappingDialog(QDialog):
    class SelectionMode(IntEnum):
        FILE = 0
        DIR = 1

    class MatchingStrategy(Enum):
        ALPHABETICAL = "Alphabetical order"
        FILENAME = "Filename (without extension)"
        REGEX = "Python regular expression (RegEx)"

    class TransformType(Enum):
        EUCLIDEAN = "Euclidean (rotation, translation)"
        SIMILARITY = "Similarity (Euclidean transform + uniform scaling)"
        AFFINE = "Affine (Similarity transform + non-uniform scaling + shear)"

    SELECTION_MODE_SETTING = "registrationDialog/selectionMode"
    MATCHING_STRATEGY_SETTING = "registrationDialog/matchingStrategy"
    SOURCE_IMG_PATH_SETTING = "registrationDialog/sourceImages"
    SOURCE_IMG_REGEX_SETTING = "registrationDialog/sourceRegex"
    TARGET_IMG_PATH_SETTING = "registrationDialog/targetImages"
    TARGET_IMG_REGEX_SETTING = "registrationDialog/targetRegex"
    CONTROL_POINTS_PATH_SETTING = "registrationDialog/controlPointsDest"
    JOINT_TRANSFORM_PATH_SETTING = "registrationDialog/jointTransformDest"
    TRANSFORM_TYPE_SETTING = "registrationDialog/transformType"
    SOURCE_COORDS_PATH_SETTING = "registrationDialog/sourceCoords"
    SOURCE_COORDS_REGEX_SETTING = "registrationDialog/sourceCoordsRegex"
    TRANSF_COORDS_PATH_SETTING = "registrationDialog/transformedCoordsDest"
    PRE_TRANSFORM_SETTING = "registrationDialog/preTransformFile"
    POST_TRANSFORM_SETTING = "registrationDialog/postTransformFile"

    DEFAULT_SELECTION_MODE = SelectionMode.FILE
    DEFAULT_MATCHING_STRATEGY = MatchingStrategy.FILENAME
    DEFAULT_SOURCE_IMG_PATH = ""
    DEFAULT_SOURCE_IMG_REGEX = ""
    DEFAULT_TARGET_IMG_PATH = ""
    DEFAULT_TARGET_IMG_REGEX = ""
    DEFAULT_CONTROL_POINTS_PATH = ""
    DEFAULT_JOINT_TRANSFORM_PATH = ""
    DEFAULT_TRANSFORM_TYPE = TransformType.SIMILARITY
    DEFAULT_SOURCE_COORDS_PATH = ""
    DEFAULT_SOURCE_COORDS_REGEX = ""
    DEFAULT_TRANSF_COORDS_PATH = ""
    DEFAULT_PRE_TRANSFORM = ""
    DEFAULT_POST_TRANSFORM = ""

    def __init__(self, **dialog_kwargs) -> None:
        super(NappingDialog, self).__init__(**dialog_kwargs)
        self._settings = QSettings("Bodenmiller Lab", "napping")

        selection_mode = NappingDialog.SelectionMode(
            int(
                self._settings.value(
                    self.SELECTION_MODE_SETTING,
                    defaultValue=self.DEFAULT_SELECTION_MODE.value,
                )
            )
        )
        self._file_selection_mode_button = QRadioButton("Single file pair", self)
        self._file_selection_mode_button.setChecked(
            selection_mode == NappingDialog.SelectionMode.FILE
        )
        self._dir_selection_mode_button = QRadioButton(
            "Directories (multiple file pairs)", self
        )
        self._dir_selection_mode_button.setChecked(
            selection_mode == NappingDialog.SelectionMode.DIR
        )
        self._selection_mode_buttons = QButtonGroup(self)
        self._selection_mode_buttons.addButton(
            self._file_selection_mode_button, NappingDialog.SelectionMode.FILE
        )
        self._selection_mode_buttons.addButton(
            self._dir_selection_mode_button, NappingDialog.SelectionMode.DIR
        )
        self._selection_mode_buttons.buttonClicked.connect(lambda _: self.refresh())

        matching_strategy_str = self._settings.value(
            self.MATCHING_STRATEGY_SETTING,
            defaultValue=self.DEFAULT_MATCHING_STRATEGY.value,
        )
        self._matching_strategy_combo_box = QComboBox(self)
        self._matching_strategy_combo_box.addItems(
            [x.value for x in NappingDialog.MatchingStrategy]
        )
        self._matching_strategy_combo_box.setCurrentText(matching_strategy_str)
        self._matching_strategy_combo_box.currentIndexChanged.connect(
            lambda _: self.refresh()
        )

        source_img_path_str = str(
            self._settings.value(
                self.SOURCE_IMG_PATH_SETTING,
                defaultValue=self.DEFAULT_SOURCE_IMG_PATH,
            )
        )
        self._source_img_path_edit = FileLineEdit(check_exists=True, parent=self)
        self._source_img_path_edit.file_dialog.setWindowTitle("Select source image(s)")
        self._source_img_path_edit.setText(source_img_path_str)
        self._source_img_path_edit.textChanged.connect(lambda text: self.refresh(text))

        source_regex = str(
            self._settings.value(
                self.SOURCE_IMG_REGEX_SETTING,
                defaultValue=self.DEFAULT_SOURCE_IMG_REGEX,
            )
        )
        self._source_regex_label = QLabel("        RegEx:")
        self._source_regex_edit = QLineEdit(self)
        self._source_regex_edit.setText(source_regex)
        self._source_regex_edit.textChanged.connect(lambda _: self.refresh())

        target_img_path_str = str(
            self._settings.value(
                self.TARGET_IMG_PATH_SETTING,
                defaultValue=self.DEFAULT_TARGET_IMG_PATH,
            )
        )
        self._target_img_path_edit = FileLineEdit(check_exists=True, parent=self)
        self._target_img_path_edit.file_dialog.setWindowTitle("Select target image(s)")
        self._target_img_path_edit.setText(target_img_path_str)
        self._target_img_path_edit.textChanged.connect(lambda text: self.refresh(text))

        target_regex = str(
            self._settings.value(
                self.TARGET_IMG_REGEX_SETTING,
                defaultValue=self.DEFAULT_TARGET_IMG_REGEX,
            )
        )
        self._target_regex_label = QLabel("        RegEx:")
        self._target_regex_edit = QLineEdit(self)
        self._target_regex_edit.setText(target_regex)
        self._target_regex_edit.textChanged.connect(lambda _: self.refresh())

        control_points_path_str = str(
            self._settings.value(
                self.CONTROL_POINTS_PATH_SETTING,
                defaultValue=self.DEFAULT_CONTROL_POINTS_PATH,
            )
        )
        self._control_points_path_edit = FileLineEdit(parent=self)
        self._control_points_path_edit.file_dialog.setWindowTitle(
            "Select control points destination"
        )
        self._control_points_path_edit.setText(control_points_path_str)
        self._control_points_path_edit.textChanged.connect(
            lambda text: self.refresh(text)
        )

        joint_transform_path_str = str(
            self._settings.value(
                self.JOINT_TRANSFORM_PATH_SETTING,
                defaultValue=self.DEFAULT_JOINT_TRANSFORM_PATH,
            )
        )
        self._joint_transform_path_edit = FileLineEdit(parent=self)
        self._joint_transform_path_edit.file_dialog.setWindowTitle(
            "Select joint transform destination"
        )
        self._joint_transform_path_edit.setText(joint_transform_path_str)
        self._joint_transform_path_edit.textChanged.connect(
            lambda text: self.refresh(text)
        )

        transform_type_str = str(
            self._settings.value(
                self.TRANSFORM_TYPE_SETTING,
                defaultValue=self.DEFAULT_TRANSFORM_TYPE,
            )
        )
        self._transform_type_combo_box = QComboBox(self)
        self._transform_type_combo_box.addItems(
            [x.value for x in NappingDialog.TransformType]
        )
        self._transform_type_combo_box.setCurrentText(transform_type_str)
        self._transform_type_combo_box.currentIndexChanged.connect(
            lambda _: self.refresh()
        )

        source_coords_path_str = str(
            self._settings.value(
                self.SOURCE_COORDS_PATH_SETTING,
                defaultValue=self.DEFAULT_SOURCE_COORDS_PATH,
            )
        )
        self._source_coords_path_edit = FileLineEdit(check_exists=True, parent=self)
        self._source_coords_path_edit.file_dialog.setWindowTitle(
            "Select source coordinates"
        )
        self._source_coords_path_edit.setText(source_coords_path_str)
        self._source_coords_path_edit.textChanged.connect(
            lambda text: self.refresh(text)
        )

        source_coords_regex = str(
            self._settings.value(
                self.SOURCE_COORDS_REGEX_SETTING,
                defaultValue=self.DEFAULT_SOURCE_COORDS_REGEX,
            )
        )
        self._source_coords_regex_label = QLabel("        RegEx:")
        self._source_coords_regex_edit = QLineEdit(self)
        self._source_coords_regex_edit.setText(source_coords_regex)
        self._source_coords_regex_edit.textChanged.connect(lambda _: self.refresh())

        transf_coords_path_str = str(
            self._settings.value(
                self.TRANSF_COORDS_PATH_SETTING,
                defaultValue=self.DEFAULT_TRANSF_COORDS_PATH,
            )
        )
        self._transf_coords_path_edit = FileLineEdit(parent=self)
        self._transf_coords_path_edit.file_dialog.setWindowTitle(
            "Select transf. coordinates destination"
        )
        self._transf_coords_path_edit.setText(transf_coords_path_str)
        self._transf_coords_path_edit.textChanged.connect(
            lambda text: self.refresh(text)
        )

        pre_transform_file_str = str(
            self._settings.value(
                self.PRE_TRANSFORM_SETTING,
                defaultValue=self.DEFAULT_PRE_TRANSFORM,
            )
        )
        self._pre_transform_file_edit = FileLineEdit(parent=self)
        self._pre_transform_file_edit.file_dialog.setWindowTitle("Select pre-transform")
        self._pre_transform_file_edit.setText(pre_transform_file_str)
        self._pre_transform_file_edit.file_dialog.setFileMode(
            QFileDialog.FileMode.ExistingFile
        )
        self._pre_transform_file_edit.file_dialog.setNameFilter("Numpy files (*.npy)")
        self._pre_transform_file_edit.textChanged.connect(
            lambda text: self.refresh(text)
        )

        post_transform_file_str = str(
            self._settings.value(
                self.POST_TRANSFORM_SETTING,
                defaultValue=self.DEFAULT_POST_TRANSFORM,
            )
        )
        self._post_transform_file_edit = FileLineEdit(parent=self)
        self._post_transform_file_edit.file_dialog.setWindowTitle(
            "Select post-transform"
        )
        self._post_transform_file_edit.file_dialog.setFileMode(
            QFileDialog.FileMode.ExistingFile
        )
        self._post_transform_file_edit.file_dialog.setNameFilter("Numpy files (*.npy)")
        self._post_transform_file_edit.setText(post_transform_file_str)
        self._post_transform_file_edit.textChanged.connect(
            lambda text: self.refresh(text)
        )

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self._button_box.rejected.connect(self.reject)
        self._button_box.accepted.connect(self._on_button_box_accepted)

        required_group_box = QGroupBox(self)
        required_group_box_layout = QFormLayout()
        required_group_box_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        required_group_box_layout.setRowWrapPolicy(
            QFormLayout.RowWrapPolicy.DontWrapRows
        )
        required_group_box_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        required_group_box_layout.addRow("Source image(s):", self._source_img_path_edit)
        required_group_box_layout.addRow(
            self._source_regex_label, self._source_regex_edit
        )
        required_group_box_layout.addRow("Target image(s):", self._target_img_path_edit)
        required_group_box_layout.addRow(
            self._target_regex_label, self._target_regex_edit
        )
        required_group_box_layout.addRow(
            "Control points dest.:", self._control_points_path_edit
        )
        required_group_box_layout.addRow(
            "Joint transform dest.:", self._joint_transform_path_edit
        )
        required_group_box_layout.addRow(
            "Transform type:", self._transform_type_combo_box
        )
        required_group_box.setLayout(required_group_box_layout)

        optional_group_box = QGroupBox(self)
        optional_group_box_layout = QFormLayout()
        optional_group_box_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        optional_group_box_layout.setRowWrapPolicy(
            QFormLayout.RowWrapPolicy.DontWrapRows
        )
        optional_group_box_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        optional_group_box_layout.addRow(
            "Source coordinates:", self._source_coords_path_edit
        )
        optional_group_box_layout.addRow(
            self._source_coords_regex_label, self._source_coords_regex_edit
        )
        optional_group_box_layout.addRow(
            "Transf. coord. dest.:", self._transf_coords_path_edit
        )
        optional_group_box_layout.addRow(
            "Pre-transform:", self._pre_transform_file_edit
        )
        optional_group_box_layout.addRow(
            "Post-transform:", self._post_transform_file_edit
        )
        optional_group_box.setLayout(optional_group_box_layout)

        layout = QVBoxLayout()
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(self._file_selection_mode_button)
        mode_layout.addWidget(self._dir_selection_mode_button)
        mode_layout.addWidget(self._matching_strategy_combo_box)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)
        layout.addWidget(required_group_box)
        layout.addWidget(optional_group_box)
        layout.addWidget(self._button_box)
        self.setLayout(layout)

        self.setWindowTitle("Control point matching")
        self.setMinimumWidth(600)
        self.refresh()

    def refresh(self, last_path: Union[str, PathLike, None] = None) -> None:
        if last_path:
            directory = str(Path(last_path).parent)
            self._source_img_path_edit.file_dialog.setDirectory(directory)
            self._target_img_path_edit.file_dialog.setDirectory(directory)
            self._control_points_path_edit.file_dialog.setDirectory(directory)
            self._joint_transform_path_edit.file_dialog.setDirectory(directory)
            self._source_coords_path_edit.file_dialog.setDirectory(directory)
            self._transf_coords_path_edit.file_dialog.setDirectory(directory)
            self._pre_transform_file_edit.file_dialog.setDirectory(directory)
            self._post_transform_file_edit.file_dialog.setDirectory(directory)

        if self.selection_mode in (
            NappingDialog.SelectionMode.FILE,
            NappingDialog.SelectionMode.DIR,
        ):
            if self.selection_mode == NappingDialog.SelectionMode.FILE:
                any_file_mode = QFileDialog.FileMode.AnyFile
                existing_file_mode = QFileDialog.FileMode.ExistingFile
                control_points_name_filter = "CSV files (*.csv)"
                control_points_default_suffix = ".csv"
                transform_name_filter = "Numpy files (*.npy)"
                transform_default_suffix = ".npy"
                source_coords_name_filter = (
                    transf_coords_name_filter
                ) = "CSV files (*.csv)"
                source_coords_default_suffix = transf_coords_default_suffix = ".csv"
                show_dirs_only = False
            else:
                any_file_mode = QFileDialog.FileMode.Directory
                existing_file_mode = QFileDialog.FileMode.Directory
                control_points_name_filter = None
                control_points_default_suffix = None
                transform_name_filter = None
                transform_default_suffix = None
                source_coords_name_filter = transf_coords_name_filter = None
                source_coords_default_suffix = transf_coords_default_suffix = None
                show_dirs_only = True

            self._source_img_path_edit.file_dialog.setFileMode(existing_file_mode)
            self._source_img_path_edit.file_dialog.setOption(
                QFileDialog.Option.ShowDirsOnly, show_dirs_only
            )

            self._target_img_path_edit.file_dialog.setFileMode(existing_file_mode)
            self._target_img_path_edit.file_dialog.setOption(
                QFileDialog.Option.ShowDirsOnly, show_dirs_only
            )

            self._control_points_path_edit.file_dialog.setFileMode(any_file_mode)
            self._control_points_path_edit.file_dialog.setNameFilter(
                control_points_name_filter
            )
            self._control_points_path_edit.file_dialog.setDefaultSuffix(
                control_points_default_suffix
            )
            self._control_points_path_edit.file_dialog.setOption(
                QFileDialog.Option.ShowDirsOnly, show_dirs_only
            )

            self._joint_transform_path_edit.file_dialog.setFileMode(any_file_mode)
            self._joint_transform_path_edit.file_dialog.setNameFilter(
                transform_name_filter
            )
            self._joint_transform_path_edit.file_dialog.setDefaultSuffix(
                transform_default_suffix
            )
            self._joint_transform_path_edit.file_dialog.setOption(
                QFileDialog.Option.ShowDirsOnly, show_dirs_only
            )

            self._source_coords_path_edit.file_dialog.setFileMode(existing_file_mode)
            self._source_coords_path_edit.file_dialog.setNameFilter(
                source_coords_name_filter
            )
            self._source_coords_path_edit.file_dialog.setDefaultSuffix(
                source_coords_default_suffix
            )
            self._source_coords_path_edit.file_dialog.setOption(
                QFileDialog.Option.ShowDirsOnly, show_dirs_only
            )

            self._transf_coords_path_edit.file_dialog.setFileMode(any_file_mode)
            self._transf_coords_path_edit.file_dialog.setNameFilter(
                transf_coords_name_filter
            )
            self._transf_coords_path_edit.file_dialog.setDefaultSuffix(
                transf_coords_default_suffix
            )
            self._transf_coords_path_edit.file_dialog.setOption(
                QFileDialog.Option.ShowDirsOnly, show_dirs_only
            )

        if self.selection_mode == NappingDialog.SelectionMode.DIR:
            self._matching_strategy_combo_box.setEnabled(True)
        else:
            self._matching_strategy_combo_box.setEnabled(False)

        dir_selection_mode = self.selection_mode == NappingDialog.SelectionMode.DIR
        regex_matching_strategy = (
            self.matching_strategy == NappingDialog.MatchingStrategy.REGEX
        )
        self._source_regex_label.setEnabled(
            dir_selection_mode and regex_matching_strategy
        )
        self._source_regex_edit.setEnabled(
            dir_selection_mode and regex_matching_strategy
        )
        self._target_regex_label.setEnabled(
            dir_selection_mode and regex_matching_strategy
        )
        self._target_regex_edit.setEnabled(
            dir_selection_mode and regex_matching_strategy
        )
        self._source_coords_regex_label.setEnabled(
            dir_selection_mode and regex_matching_strategy
        )
        self._source_coords_regex_edit.setEnabled(
            dir_selection_mode and regex_matching_strategy
        )

        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            self.is_valid()
        )

    def is_valid(self) -> bool:
        if self.selection_mode == NappingDialog.SelectionMode.FILE:
            if self.source_img_path is None or not self.source_img_path.is_file():
                return False
            if self.target_img_path is None or not self.target_img_path.is_file():
                return False
            if self.control_points_path is None or self.control_points_path.is_dir():
                return False
            if self.joint_transform_path is None or self.joint_transform_path.is_dir():
                return False
            if (
                self.source_coords_path is not None
                and not self.source_coords_path.is_file()
            ):
                return False
            if (
                self.transf_coords_path is not None
                and self.control_points_path.is_dir()
            ):
                return False
        elif self.selection_mode == NappingDialog.SelectionMode.DIR:
            if self.source_img_path is None or not self.source_img_path.is_dir():
                return False
            if self.target_img_path is None or not self.target_img_path.is_dir():
                return False
            if self.control_points_path is None or self.control_points_path.is_file():
                return False
            if self.joint_transform_path is None or self.joint_transform_path.is_file():
                return False
            if (
                self.source_coords_path is not None
                and not self.source_coords_path.is_dir()
            ):
                return False
            if (
                self.transf_coords_path is not None
                and self.control_points_path.is_file()
            ):
                return False
            if self.matching_strategy == NappingDialog.MatchingStrategy.REGEX:
                if not self.source_regex:
                    return False
                if not self.target_regex:
                    return False
                if self.source_coords_path is not None and not self.source_coords_regex:
                    return False
        else:
            return False
        if (
            self.pre_transform_path is not None
            and not self.pre_transform_path.is_file()
        ):
            return False
        if (
            self.post_transform_path is not None
            and not self.post_transform_path.is_file()
        ):
            return False
        if bool(self.source_coords_path) != bool(self.transf_coords_path):
            return False
        if (
            bool(self.pre_transform_path) or bool(self.post_transform_path)
        ) and not bool(self.source_coords_path):
            return False
        unique_paths = {
            self.source_img_path,
            self.target_img_path,
            self.control_points_path,
            self.joint_transform_path,
        }
        if self.source_coords_path is not None and self.transf_coords_path is not None:
            unique_paths.update({self.source_coords_path, self.transf_coords_path})
            if len(unique_paths) != 6:
                return False
        elif len(unique_paths) != 4:
            return False
        return True

    def _on_button_box_accepted(self) -> None:
        self._settings.setValue(self.SELECTION_MODE_SETTING, self.selection_mode.value)
        self._settings.setValue(self.SOURCE_IMG_PATH_SETTING, str(self.source_img_path))
        self._settings.setValue(self.SOURCE_IMG_REGEX_SETTING, self.source_regex)
        self._settings.setValue(self.TARGET_IMG_PATH_SETTING, str(self.target_img_path))
        self._settings.setValue(self.TARGET_IMG_REGEX_SETTING, self.target_regex)
        self._settings.setValue(
            self.CONTROL_POINTS_PATH_SETTING, str(self.control_points_path)
        )
        self._settings.setValue(
            self.JOINT_TRANSFORM_PATH_SETTING,
            str(self.joint_transform_path),
        )
        self._settings.setValue(self.TRANSFORM_TYPE_SETTING, self.transform_type.value)
        self._settings.setValue(
            self.MATCHING_STRATEGY_SETTING, self.matching_strategy.value
        )
        self._settings.setValue(
            self.SOURCE_COORDS_PATH_SETTING,
            str(self.source_coords_path or ""),
        )
        self._settings.setValue(
            self.SOURCE_COORDS_REGEX_SETTING, self.source_coords_regex
        )
        self._settings.setValue(
            self.TRANSF_COORDS_PATH_SETTING,
            str(self.transf_coords_path or ""),
        )
        self._settings.setValue(
            self.PRE_TRANSFORM_SETTING, str(self.pre_transform_path or "")
        )
        self._settings.setValue(
            self.POST_TRANSFORM_SETTING,
            str(self.post_transform_path or ""),
        )
        self._settings.sync()
        self.accept()

    @property
    def selection_mode(self) -> Optional["NappingDialog.SelectionMode"]:
        selection_mode_value = self._selection_mode_buttons.checkedId()
        if selection_mode_value >= 0:
            return NappingDialog.SelectionMode(selection_mode_value)
        return None

    @selection_mode.setter
    def selection_mode(
        self, selection_mode: Optional["NappingDialog.SelectionMode"]
    ) -> None:
        if selection_mode is None:
            selection_mode = self.DEFAULT_SELECTION_MODE
        if selection_mode == NappingDialog.SelectionMode.FILE:
            self._file_selection_mode_button.setChecked(True)
        if selection_mode == NappingDialog.SelectionMode.DIR:
            self._dir_selection_mode_button.setChecked(True)

    @property
    def matching_strategy(self) -> Optional["NappingDialog.MatchingStrategy"]:
        try:
            return NappingDialog.MatchingStrategy(
                self._matching_strategy_combo_box.currentText()
            )
        except Exception:
            return None

    @matching_strategy.setter
    def matching_strategy(
        self, matching_strategy: Optional["NappingDialog.MatchingStrategy"]
    ) -> None:
        if matching_strategy is None:
            matching_strategy = self.DEFAULT_MATCHING_STRATEGY
        self._matching_strategy_combo_box.setCurrentText(matching_strategy.value)

    @property
    def source_img_path(self) -> Optional[Path]:
        return self._source_img_path_edit.get_path()

    @source_img_path.setter
    def source_img_path(self, source_img_path: Optional[Path]) -> None:
        self._source_img_path_edit.set_path(source_img_path)

    @property
    def source_regex(self) -> Optional[str]:
        return self._source_regex_edit.text() or None

    @source_regex.setter
    def source_regex(self, source_regex: Optional[str]) -> None:
        self._source_regex_edit.setText(source_regex or "")

    @property
    def target_img_path(self) -> Optional[Path]:
        return self._target_img_path_edit.get_path()

    @target_img_path.setter
    def target_img_path(self, target_img_path: Optional[Path]) -> None:
        self._target_img_path_edit.set_path(target_img_path)

    @property
    def target_regex(self) -> Optional[str]:
        return self._target_regex_edit.text() or None

    @target_regex.setter
    def target_regex(self, target_regex: Optional[str]) -> None:
        self._target_regex_edit.setText(target_regex or "")

    @property
    def control_points_path(self) -> Optional[Path]:
        return self._control_points_path_edit.get_path()

    @control_points_path.setter
    def control_points_path(self, control_points_path: Optional[Path]) -> None:
        self._control_points_path_edit.set_path(control_points_path)

    @property
    def joint_transform_path(self) -> Optional[Path]:
        return self._joint_transform_path_edit.get_path()

    @joint_transform_path.setter
    def joint_transform_path(self, joint_transform_path: Optional[Path]) -> None:
        self._joint_transform_path_edit.set_path(joint_transform_path)

    @property
    def transform_type(self) -> Optional["NappingDialog.TransformType"]:
        try:
            return NappingDialog.TransformType(
                self._transform_type_combo_box.currentText()
            )
        except Exception:
            return None

    @transform_type.setter
    def transform_type(
        self, transform_type: Optional["NappingDialog.TransformType"]
    ) -> None:
        if transform_type is None:
            transform_type = self.DEFAULT_TRANSFORM_TYPE
        self._transform_type_combo_box.setCurrentText(transform_type.value)

    @property
    def source_coords_path(self) -> Optional[Path]:
        return self._source_coords_path_edit.get_path()

    @source_coords_path.setter
    def source_coords_path(self, source_coords_path: Optional[Path]) -> None:
        self._source_coords_path_edit.set_path(source_coords_path)

    @property
    def source_coords_regex(self) -> Optional[str]:
        return self._source_coords_regex_edit.text() or None

    @source_coords_regex.setter
    def source_coords_regex(self, source_coords_regex: Optional[str]) -> None:
        self._source_coords_regex_edit.setText(source_coords_regex or "")

    @property
    def transf_coords_path(self) -> Optional[Path]:
        return self._transf_coords_path_edit.get_path()

    @transf_coords_path.setter
    def transf_coords_path(self, transf_coords_path: Optional[Path]) -> None:
        self._transf_coords_path_edit.set_path(transf_coords_path)

    @property
    def pre_transform_path(self) -> Optional[Path]:
        return self._pre_transform_file_edit.get_path()

    @pre_transform_path.setter
    def pre_transform_path(self, pre_transform_path: Optional[Path]) -> None:
        self._pre_transform_file_edit.set_path(pre_transform_path)

    @property
    def post_transform_path(self) -> Optional[Path]:
        return self._post_transform_file_edit.get_path()

    @post_transform_path.setter
    def post_transform_path(self, post_transform_path: Optional[Path]) -> None:
        self._post_transform_file_edit.set_path(post_transform_path)
