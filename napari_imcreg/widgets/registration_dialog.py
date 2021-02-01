from enum import Enum, IntEnum
from pathlib import Path
from typing import Optional, TYPE_CHECKING, Union
from qtpy.QtCore import Qt, QSettings
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
    QVBoxLayout
)

from napari_imcreg.widgets._file_line_edit import FileLineEdit

if TYPE_CHECKING:
    from napari_imcreg import IMCRegController


class RegistrationDialog(QDialog):
    class SelectionMode(IntEnum):
        FILE = 0
        DIR = 1

    class FileMatchingStrategy(Enum):
        ALPHABETICAL = 'Alphabetical order'
        FILENAME = 'Filename (without extension)'
        REGEX = 'Python regular expression (RegEx)'

    class CoordinateTransformType(Enum):
        EUCLIDEAN = 'Euclidean (rotation, translation)'
        SIMILARITY = 'Similarity (Euclidean transform + uniform scaling)'
        AFFINE = 'Affine (Similarity transform + non-uniform scaling + shear)'

    SELECTION_MODE_SETTING = 'registrationDialog/selectionMode'
    SOURCE_SETTING = 'registrationDialog/source'
    SOURCE_REGEX_SETTING = 'registrationDialog/sourceRegex'
    TARGET_SETTING = 'registrationDialog/target'
    TARGET_REGEX_SETTING = 'registrationDialog/targetRegex'
    CONTROL_POINTS_SETTING = 'registrationDialog/controlPoints'
    FILE_MATCHING_STRATEGY_SETTING = 'registrationDialog/fileMatchingStrategy'
    SOURCE_COORDS_SETTING = 'registrationDialog/sourceCoords'
    SOURCE_COORDS_REGEX_SETTING = 'registrationDialog/sourceCoordsRegex'
    TRANSFORMED_COORDS_SETTING = 'registrationDialog/transformedCoords'
    COORD_TRANSFORM_TYPE_SETTING = 'registrationDialog/coordTransformType'

    DEFAULT_SELECTION_MODE = SelectionMode.FILE
    DEFAULT_SOURCE = ''
    DEFAULT_SOURCE_REGEX = ''
    DEFAULT_TARGET = ''
    DEFAULT_TARGET_REGEX = ''
    DEFAULT_CONTROL_POINTS = ''
    DEFAULT_FILE_MATCHING_STRATEGY = FileMatchingStrategy.FILENAME
    DEFAULT_SOURCE_COORDS = ''
    DEFAULT_SOURCE_COORDS_REGEX = ''
    DEFAULT_TRANSFORMED_COORDS = ''
    DEFAULT_COORD_TRANSFORM_TYPE = CoordinateTransformType.SIMILARITY

    def __init__(self, controller: 'IMCRegController', parent=None):
        super(RegistrationDialog, self).__init__(parent)
        self._controller = controller
        settings = QSettings()

        checked_selection_mode = RegistrationDialog.SelectionMode(int(settings.value(
            self.SELECTION_MODE_SETTING, defaultValue=self.DEFAULT_SELECTION_MODE.value
        )))
        self._file_selection_mode_button = QRadioButton('Single file pair', self)
        self._file_selection_mode_button.setChecked(checked_selection_mode == RegistrationDialog.SelectionMode.FILE)
        self._dir_selection_mode_button = QRadioButton('Directories (multiple file pairs)', self)
        self._dir_selection_mode_button.setChecked(checked_selection_mode == RegistrationDialog.SelectionMode.DIR)
        self._selection_mode_buttons_group = QButtonGroup(self)
        self._selection_mode_buttons_group.addButton(self._file_selection_mode_button,
                                                     RegistrationDialog.SelectionMode.FILE)
        self._selection_mode_buttons_group.addButton(self._dir_selection_mode_button,
                                                     RegistrationDialog.SelectionMode.DIR)
        # noinspection PyUnresolvedReferences
        self._selection_mode_buttons_group.buttonClicked.connect(lambda _: self.refresh())

        source_file_line_edit_text = str(settings.value(
            self.SOURCE_SETTING, defaultValue=self.DEFAULT_SOURCE
        ))
        self._source_file_line_edit = FileLineEdit(check_exists=True, parent=self)
        self._source_file_line_edit.file_dialog.setWindowTitle('Select source image(s)')
        self._source_file_line_edit.setText(source_file_line_edit_text)
        # noinspection PyUnresolvedReferences
        self._source_file_line_edit.textChanged.connect(lambda text: self.refresh(text))

        source_regex_line_edit_text = str(settings.value(
            self.SOURCE_REGEX_SETTING, defaultValue=self.DEFAULT_SOURCE_REGEX
        ))
        self._source_regex_label = QLabel('        RegEx:')
        self._source_regex_line_edit = QLineEdit(self)
        self._source_regex_line_edit.setText(source_regex_line_edit_text)
        # noinspection PyUnresolvedReferences
        self._source_regex_line_edit.textChanged.connect(lambda _: self.refresh())

        target_file_line_edit_text = str(settings.value(
            self.TARGET_SETTING, defaultValue=self.DEFAULT_TARGET
        ))
        self._target_file_line_edit = FileLineEdit(check_exists=True, parent=self)
        self._target_file_line_edit.file_dialog.setWindowTitle('Select target image(s)')
        self._target_file_line_edit.setText(target_file_line_edit_text)
        # noinspection PyUnresolvedReferences
        self._target_file_line_edit.textChanged.connect(lambda text: self.refresh(text))

        target_regex_line_edit_text = str(settings.value(
            self.TARGET_REGEX_SETTING, defaultValue=self.DEFAULT_TARGET_REGEX
        ))
        self._target_regex_label = QLabel('        RegEx:')
        self._target_regex_line_edit = QLineEdit(self)
        self._target_regex_line_edit.setText(target_regex_line_edit_text)
        # noinspection PyUnresolvedReferences
        self._target_regex_line_edit.textChanged.connect(lambda _: self.refresh())

        control_points_file_line_edit_text = str(settings.value(
            self.CONTROL_POINTS_SETTING, defaultValue=self.DEFAULT_CONTROL_POINTS
        ))
        self._control_points_file_line_edit = FileLineEdit(parent=self)
        self._control_points_file_line_edit.file_dialog.setWindowTitle('Select control points destination')
        self._control_points_file_line_edit.setText(control_points_file_line_edit_text)
        # noinspection PyUnresolvedReferences
        self._control_points_file_line_edit.textChanged.connect(lambda text: self.refresh(text))

        file_matching_strategy_combo_box_current_text = str(settings.value(
            self.FILE_MATCHING_STRATEGY_SETTING,
            defaultValue=self.DEFAULT_FILE_MATCHING_STRATEGY.value
        ))
        self._file_matching_strategy_label = QLabel('File matching:')
        self._file_matching_strategy_combo_box = QComboBox(self)
        self._file_matching_strategy_combo_box.addItems([x.value for x in RegistrationDialog.FileMatchingStrategy])
        self._file_matching_strategy_combo_box.setCurrentText(file_matching_strategy_combo_box_current_text)
        # noinspection PyUnresolvedReferences
        self._file_matching_strategy_combo_box.currentIndexChanged.connect(lambda _: self.refresh())

        source_coords_file_line_edit_text = str(settings.value(
            self.SOURCE_COORDS_SETTING, defaultValue=self.DEFAULT_SOURCE_COORDS
        ))
        self._source_coords_file_line_edit = FileLineEdit(check_exists=True, parent=self)
        self._source_coords_file_line_edit.file_dialog.setWindowTitle('Select source coordinates')
        self._source_coords_file_line_edit.setText(source_coords_file_line_edit_text)
        # noinspection PyUnresolvedReferences
        self._source_coords_file_line_edit.textChanged.connect(lambda text: self.refresh(text))

        source_coords_regex_line_edit_text = str(settings.value(
            self.SOURCE_COORDS_REGEX_SETTING, defaultValue=self.DEFAULT_SOURCE_COORDS_REGEX
        ))
        self._source_coords_regex_label = QLabel('        RegEx:')
        self._source_coords_regex_line_edit = QLineEdit(self)
        self._source_coords_regex_line_edit.setText(source_coords_regex_line_edit_text)
        # noinspection PyUnresolvedReferences
        self._source_coords_regex_line_edit.textChanged.connect(lambda _: self.refresh())

        transformed_coords_file_line_edit_text = str(settings.value(
            self.TRANSFORMED_COORDS_SETTING, defaultValue=self.DEFAULT_TRANSFORMED_COORDS
        ))
        self._transformed_coords_file_line_edit = FileLineEdit(parent=self)
        self._transformed_coords_file_line_edit.file_dialog.setWindowTitle('Select transformed coordinates destination')
        self._transformed_coords_file_line_edit.setText(transformed_coords_file_line_edit_text)
        # noinspection PyUnresolvedReferences
        self._transformed_coords_file_line_edit.textChanged.connect(lambda text: self.refresh(text))

        coord_transform_type_combo_box_current_text = str(settings.value(
            self.COORD_TRANSFORM_TYPE_SETTING, defaultValue=self.DEFAULT_COORD_TRANSFORM_TYPE
        ))
        self._coord_transform_type_combo_box = QComboBox(self)
        self._coord_transform_type_combo_box.addItems([x.value for x in RegistrationDialog.CoordinateTransformType])
        self._coord_transform_type_combo_box.setCurrentText(coord_transform_type_combo_box_current_text)
        # noinspection PyUnresolvedReferences
        self._coord_transform_type_combo_box.currentIndexChanged.connect(lambda _: self.refresh())

        self._button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        # noinspection PyUnresolvedReferences
        self._button_box.rejected.connect(self.reject)

        # noinspection PyUnresolvedReferences
        @self._button_box.accepted.connect
        def on_button_box_accepted():
            settings.setValue(self.SELECTION_MODE_SETTING, self.selection_mode.value)
            settings.setValue(self.SOURCE_SETTING, str(self.source_path))
            settings.setValue(self.SOURCE_REGEX_SETTING, self.source_regex)
            settings.setValue(self.TARGET_SETTING, str(self.target_path))
            settings.setValue(self.TARGET_REGEX_SETTING, self.target_regex)
            settings.setValue(self.CONTROL_POINTS_SETTING, str(self.control_points_path))
            settings.setValue(self.FILE_MATCHING_STRATEGY_SETTING, self.file_matching_strategy.value)
            settings.setValue(self.SOURCE_COORDS_SETTING, str(self.source_coords_path or ''))
            settings.setValue(self.SOURCE_COORDS_REGEX_SETTING, self.source_coords_regex)
            settings.setValue(self.TRANSFORMED_COORDS_SETTING, str(self.transformed_coords_path or ''))
            settings.setValue(self.COORD_TRANSFORM_TYPE_SETTING, self.coord_transform_type.value)
            settings.sync()
            self.accept()

        required_group_box = QGroupBox(self)
        required_group_box_layout = QFormLayout()
        required_group_box_layout.setLabelAlignment(Qt.AlignLeft)
        required_group_box_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        required_group_box_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        required_group_box_layout.addRow('Source image(s):', self._source_file_line_edit)
        required_group_box_layout.addRow(self._source_regex_label, self._source_regex_line_edit)
        required_group_box_layout.addRow('Target image(s):', self._target_file_line_edit)
        required_group_box_layout.addRow(self._target_regex_label, self._target_regex_line_edit)
        required_group_box_layout.addRow('Control points dest.:', self._control_points_file_line_edit)
        required_group_box_layout.addRow(self._file_matching_strategy_label, self._file_matching_strategy_combo_box)
        required_group_box.setLayout(required_group_box_layout)

        optional_group_box = QGroupBox(self)
        optional_group_box_layout = QFormLayout()
        optional_group_box_layout.setLabelAlignment(Qt.AlignLeft)
        optional_group_box_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        optional_group_box_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        optional_group_box_layout.addRow('Source coordinates:', self._source_coords_file_line_edit)
        optional_group_box_layout.addRow(self._source_coords_regex_label, self._source_coords_regex_line_edit)
        optional_group_box_layout.addRow('Transformed coord. dest.:', self._transformed_coords_file_line_edit)
        optional_group_box_layout.addRow('Coordinate transform type:', self._coord_transform_type_combo_box)
        optional_group_box.setLayout(optional_group_box_layout)

        layout = QVBoxLayout()
        mode_buttons_layout = QHBoxLayout()
        # noinspection PyArgumentList
        mode_buttons_layout.addWidget(self._file_selection_mode_button)
        # noinspection PyArgumentList
        mode_buttons_layout.addWidget(self._dir_selection_mode_button)
        mode_buttons_layout.addStretch()
        layout.addLayout(mode_buttons_layout)
        # noinspection PyArgumentList
        layout.addWidget(required_group_box)
        # noinspection PyArgumentList
        layout.addWidget(optional_group_box)
        # noinspection PyArgumentList
        layout.addWidget(self._button_box)
        self.setLayout(layout)

        self.setWindowTitle('Control point matching')
        self.setMinimumWidth(600)
        self.refresh()

    @property
    def selection_mode(self) -> Optional['RegistrationDialog.SelectionMode']:
        selection_mode_value = self._selection_mode_buttons_group.checkedId()
        if selection_mode_value >= 0:
            return RegistrationDialog.SelectionMode(selection_mode_value)
        return None

    @property
    def source_path(self) -> Optional[Path]:
        return self._source_file_line_edit.path

    @property
    def source_regex(self) -> str:
        return self._source_regex_line_edit.text()

    @property
    def target_path(self) -> Optional[Path]:
        return self._target_file_line_edit.path

    @property
    def target_regex(self) -> str:
        return self._target_regex_line_edit.text()

    @property
    def control_points_path(self) -> Optional[Path]:
        return self._control_points_file_line_edit.path

    @property
    def file_matching_strategy(self) -> 'RegistrationDialog.FileMatchingStrategy':
        return RegistrationDialog.FileMatchingStrategy(self._file_matching_strategy_combo_box.currentText())

    @property
    def source_coords_path(self) -> Optional[Path]:
        return self._source_coords_file_line_edit.path

    @property
    def source_coords_regex(self) -> str:
        return self._source_coords_regex_line_edit.text()

    @property
    def transformed_coords_path(self) -> Optional[Path]:
        return self._transformed_coords_file_line_edit.path

    @property
    def coord_transform_type(self) -> 'RegistrationDialog.CoordinateTransformType':
        return RegistrationDialog.CoordinateTransformType(self._coord_transform_type_combo_box.currentText())

    @property
    def is_valid(self) -> bool:
        if self.selection_mode == RegistrationDialog.SelectionMode.FILE:
            if self.source_path is None or not self.source_path.is_file():
                return False
            if self.target_path is None or not self.target_path.is_file():
                return False
            if self.control_points_path is None or self.control_points_path.is_dir():
                return False
            if self.source_coords_path is not None and not self.source_coords_path.is_file():
                return False
            if self.transformed_coords_path is not None and self.control_points_path.is_dir():
                return False
        elif self.selection_mode == RegistrationDialog.SelectionMode.DIR:
            if self.source_path is None or not self.source_path.is_dir():
                return False
            if self.target_path is None or not self.target_path.is_dir():
                return False
            if self.control_points_path is None or self.control_points_path.is_file():
                return False
            if self.source_coords_path is not None and not self.source_coords_path.is_dir():
                return False
            if self.transformed_coords_path is not None and self.control_points_path.is_file():
                return False
            if self.file_matching_strategy == RegistrationDialog.FileMatchingStrategy.REGEX:
                if not self.source_regex:
                    return False
                if not self.target_regex:
                    return False
                if self.source_coords_path is not None and not self.source_coords_regex:
                    return False
        else:
            return False
        if bool(self.source_coords_path) != bool(self.transformed_coords_path):
            return False
        paths = {self.source_path, self.target_path, self.control_points_path}
        if self.source_coords_path is not None and self.transformed_coords_path is not None:
            paths.update({self.source_coords_path, self.transformed_coords_path})
            if len(paths) != 5:
                return False
        elif len(paths) != 3:
            return False
        return True

    def refresh(self, last_path: Union[str, Path, None] = None):
        if last_path:
            directory = str(Path(last_path).parent)
            self._source_file_line_edit.file_dialog.setDirectory(directory)
            self._target_file_line_edit.file_dialog.setDirectory(directory)
            self._control_points_file_line_edit.file_dialog.setDirectory(directory)
            self._source_coords_file_line_edit.file_dialog.setDirectory(directory)
            self._transformed_coords_file_line_edit.file_dialog.setDirectory(directory)

        if self.selection_mode in (RegistrationDialog.SelectionMode.FILE, RegistrationDialog.SelectionMode.DIR):
            if self.selection_mode == RegistrationDialog.SelectionMode.FILE:
                any_file_mode = QFileDialog.AnyFile
                existing_file_mode = QFileDialog.ExistingFile
                control_points_name_filter = 'Numpy arrays (*.npy)'
                control_points_default_suffix = '.npy'
                source_coords_name_filter = transformed_coords_name_filter = 'CSV files (*.csv)'
                source_coords_default_suffix = transformed_coords_default_suffix = '.csv'
                show_dirs_only = False
            else:
                any_file_mode = QFileDialog.Directory
                existing_file_mode = QFileDialog.Directory
                control_points_name_filter = None
                control_points_default_suffix = None
                source_coords_name_filter = transformed_coords_name_filter = None
                source_coords_default_suffix = transformed_coords_default_suffix = None
                show_dirs_only = True
            self._source_file_line_edit.file_dialog.setFileMode(existing_file_mode)
            self._source_file_line_edit.file_dialog.setOption(QFileDialog.ShowDirsOnly, show_dirs_only)
            self._target_file_line_edit.file_dialog.setFileMode(existing_file_mode)
            self._target_file_line_edit.file_dialog.setOption(QFileDialog.ShowDirsOnly, show_dirs_only)
            self._control_points_file_line_edit.file_dialog.setFileMode(any_file_mode)
            self._control_points_file_line_edit.file_dialog.setNameFilter(control_points_name_filter)
            self._control_points_file_line_edit.file_dialog.setDefaultSuffix(control_points_default_suffix)
            self._control_points_file_line_edit.file_dialog.setOption(QFileDialog.ShowDirsOnly, show_dirs_only)
            self._source_coords_file_line_edit.file_dialog.setFileMode(existing_file_mode)
            self._source_coords_file_line_edit.file_dialog.setNameFilter(source_coords_name_filter)
            self._source_coords_file_line_edit.file_dialog.setDefaultSuffix(source_coords_default_suffix)
            self._source_coords_file_line_edit.file_dialog.setOption(QFileDialog.ShowDirsOnly, show_dirs_only)
            self._transformed_coords_file_line_edit.file_dialog.setFileMode(any_file_mode)
            self._transformed_coords_file_line_edit.file_dialog.setNameFilter(transformed_coords_name_filter)
            self._transformed_coords_file_line_edit.file_dialog.setDefaultSuffix(transformed_coords_default_suffix)
            self._transformed_coords_file_line_edit.file_dialog.setOption(QFileDialog.ShowDirsOnly, show_dirs_only)

        if self.selection_mode == RegistrationDialog.SelectionMode.DIR:
            self._file_matching_strategy_label.show()
            self._file_matching_strategy_combo_box.show()
        else:
            self._file_matching_strategy_label.hide()
            self._file_matching_strategy_combo_box.hide()

        dir_selection_mode = RegistrationDialog.SelectionMode.DIR
        regex_file_matching_strategy = RegistrationDialog.FileMatchingStrategy.REGEX
        if self.selection_mode == dir_selection_mode and self.file_matching_strategy == regex_file_matching_strategy:
            self._source_regex_label.show()
            self._source_regex_line_edit.show()
            self._target_regex_label.show()
            self._target_regex_line_edit.show()
            self._source_coords_regex_label.show()
            self._source_coords_regex_line_edit.show()
        else:
            self._source_regex_label.hide()
            self._source_regex_line_edit.hide()
            self._target_regex_label.hide()
            self._target_regex_line_edit.hide()
            self._source_coords_regex_label.hide()
            self._source_coords_regex_line_edit.hide()

        self._button_box.button(QDialogButtonBox.Ok).setEnabled(self.is_valid)
