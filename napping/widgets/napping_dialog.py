from enum import Enum, IntEnum
from pathlib import Path
from typing import Optional, Union
from qtpy.QtCore import Qt, QObject, QSettings
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

from napping.widgets._file_line_edit import FileLineEdit


class NappingDialog(QDialog):
    class SelectionMode(IntEnum):
        FILE = 0
        DIR = 1

    class MatchingStrategy(Enum):
        ALPHABETICAL = 'Alphabetical order'
        FILENAME = 'Filename (without extension)'
        REGEX = 'Python regular expression (RegEx)'

    class TransformType(Enum):
        EUCLIDEAN = 'Euclidean (rotation, translation)'
        SIMILARITY = 'Similarity (Euclidean transform + uniform scaling)'
        AFFINE = 'Affine (Similarity transform + non-uniform scaling + shear)'

    SELECTION_MODE_SETTING = 'registrationDialog/selectionMode'
    MATCHING_STRATEGY_SETTING = 'registrationDialog/matchingStrategy'
    SOURCE_IMAGES_SETTING = 'registrationDialog/sourceImages'
    SOURCE_REGEX_SETTING = 'registrationDialog/sourceRegex'
    TARGET_IMAGES_SETTING = 'registrationDialog/targetImages'
    TARGET_REGEX_SETTING = 'registrationDialog/targetRegex'
    CONTROL_POINTS_DEST_SETTING = 'registrationDialog/controlPointsDest'
    TRANSFORM_DEST_SETTING = 'registrationDialog/transformDest'
    TRANSFORM_TYPE_SETTING = 'registrationDialog/transformType'
    SOURCE_COORDS_SETTING = 'registrationDialog/sourceCoords'
    SOURCE_COORDS_REGEX_SETTING = 'registrationDialog/sourceCoordsRegex'
    TRANSFORMED_COORDS_DEST_SETTING = 'registrationDialog/transformedCoordsDest'
    PRE_TRANSFORM_SETTING = 'registrationDialog/preTransformFile'
    POST_TRANSFORM_SETTING = 'registrationDialog/postTransformFile'

    DEFAULT_SELECTION_MODE = SelectionMode.FILE
    DEFAULT_MATCHING_STRATEGY = MatchingStrategy.FILENAME
    DEFAULT_SOURCE_IMAGES = ''
    DEFAULT_SOURCE_REGEX = ''
    DEFAULT_TARGET_IMAGES = ''
    DEFAULT_TARGET_REGEX = ''
    DEFAULT_CONTROL_POINTS_DEST = ''
    DEFAULT_TRANSFORM_DEST = ''
    DEFAULT_TRANSFORM_TYPE = TransformType.SIMILARITY
    DEFAULT_SOURCE_COORDS = ''
    DEFAULT_SOURCE_COORDS_REGEX = ''
    DEFAULT_TRANSFORMED_COORDS_DEST = ''
    DEFAULT_PRE_TRANSFORM = ''
    DEFAULT_POST_TRANSFORM = ''

    def __init__(self, settings: QSettings, parent: Optional[QObject] = None):
        # noinspection PyArgumentList
        super(NappingDialog, self).__init__(parent)

        checked_selection_mode = NappingDialog.SelectionMode(int(settings.value(
            self.SELECTION_MODE_SETTING, defaultValue=self.DEFAULT_SELECTION_MODE.value
        )))
        self._file_selection_mode_button = QRadioButton('Single file pair', self)
        self._file_selection_mode_button.setChecked(checked_selection_mode == NappingDialog.SelectionMode.FILE)
        self._dir_selection_mode_button = QRadioButton('Directories (multiple file pairs)', self)
        self._dir_selection_mode_button.setChecked(checked_selection_mode == NappingDialog.SelectionMode.DIR)
        self._selection_mode_buttons_group = QButtonGroup(self)
        self._selection_mode_buttons_group.addButton(self._file_selection_mode_button, NappingDialog.SelectionMode.FILE)
        self._selection_mode_buttons_group.addButton(self._dir_selection_mode_button, NappingDialog.SelectionMode.DIR)
        # noinspection PyUnresolvedReferences
        self._selection_mode_buttons_group.buttonClicked.connect(lambda _: self.refresh())

        matching_strategy_combo_box_current_text = str(settings.value(
            self.MATCHING_STRATEGY_SETTING,
            defaultValue=self.DEFAULT_MATCHING_STRATEGY.value
        ))
        self._matching_strategy_combo_box = QComboBox(self)
        self._matching_strategy_combo_box.addItems([x.value for x in NappingDialog.MatchingStrategy])
        self._matching_strategy_combo_box.setCurrentText(matching_strategy_combo_box_current_text)
        # noinspection PyUnresolvedReferences
        self._matching_strategy_combo_box.currentIndexChanged.connect(lambda _: self.refresh())

        source_images_file_line_edit_text = str(settings.value(
            self.SOURCE_IMAGES_SETTING, defaultValue=self.DEFAULT_SOURCE_IMAGES
        ))
        self._source_images_file_line_edit = FileLineEdit(check_exists=True, parent=self)
        self._source_images_file_line_edit.file_dialog.setWindowTitle('Select source image(s)')
        self._source_images_file_line_edit.setText(source_images_file_line_edit_text)
        # noinspection PyUnresolvedReferences
        self._source_images_file_line_edit.textChanged.connect(lambda text: self.refresh(text))

        source_regex_line_edit_text = str(settings.value(
            self.SOURCE_REGEX_SETTING, defaultValue=self.DEFAULT_SOURCE_REGEX
        ))
        self._source_regex_label = QLabel('        RegEx:')
        self._source_regex_line_edit = QLineEdit(self)
        self._source_regex_line_edit.setText(source_regex_line_edit_text)
        # noinspection PyUnresolvedReferences
        self._source_regex_line_edit.textChanged.connect(lambda _: self.refresh())

        target_images_file_line_edit_text = str(settings.value(
            self.TARGET_IMAGES_SETTING, defaultValue=self.DEFAULT_TARGET_IMAGES
        ))
        self._target_images_file_line_edit = FileLineEdit(check_exists=True, parent=self)
        self._target_images_file_line_edit.file_dialog.setWindowTitle('Select target image(s)')
        self._target_images_file_line_edit.setText(target_images_file_line_edit_text)
        # noinspection PyUnresolvedReferences
        self._target_images_file_line_edit.textChanged.connect(lambda text: self.refresh(text))

        target_regex_line_edit_text = str(settings.value(
            self.TARGET_REGEX_SETTING, defaultValue=self.DEFAULT_TARGET_REGEX
        ))
        self._target_regex_label = QLabel('        RegEx:')
        self._target_regex_line_edit = QLineEdit(self)
        self._target_regex_line_edit.setText(target_regex_line_edit_text)
        # noinspection PyUnresolvedReferences
        self._target_regex_line_edit.textChanged.connect(lambda _: self.refresh())

        control_points_dest_file_line_edit_text = str(settings.value(
            self.CONTROL_POINTS_DEST_SETTING, defaultValue=self.DEFAULT_CONTROL_POINTS_DEST
        ))
        self._control_points_dest_file_line_edit = FileLineEdit(parent=self)
        self._control_points_dest_file_line_edit.file_dialog.setWindowTitle('Select control points destination')
        self._control_points_dest_file_line_edit.setText(control_points_dest_file_line_edit_text)
        # noinspection PyUnresolvedReferences
        self._control_points_dest_file_line_edit.textChanged.connect(lambda text: self.refresh(text))

        transform_dest_file_line_edit_text = str(settings.value(
            self.TRANSFORM_DEST_SETTING, defaultValue=self.DEFAULT_TRANSFORM_DEST
        ))
        self._transform_dest_file_line_edit = FileLineEdit(parent=self)
        self._transform_dest_file_line_edit.file_dialog.setWindowTitle('Select transform destination')
        self._transform_dest_file_line_edit.setText(transform_dest_file_line_edit_text)
        # noinspection PyUnresolvedReferences
        self._transform_dest_file_line_edit.textChanged.connect(lambda text: self.refresh(text))

        transform_type_combo_box_current_text = str(settings.value(
            self.TRANSFORM_TYPE_SETTING, defaultValue=self.DEFAULT_TRANSFORM_TYPE
        ))
        self._transform_type_combo_box = QComboBox(self)
        self._transform_type_combo_box.addItems([x.value for x in NappingDialog.TransformType])
        self._transform_type_combo_box.setCurrentText(transform_type_combo_box_current_text)
        # noinspection PyUnresolvedReferences
        self._transform_type_combo_box.currentIndexChanged.connect(lambda _: self.refresh())

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

        transformed_coords_dest_file_line_edit_text = str(settings.value(
            self.TRANSFORMED_COORDS_DEST_SETTING, defaultValue=self.DEFAULT_TRANSFORMED_COORDS_DEST
        ))
        self._transformed_coords_dest_file_line_edit = FileLineEdit(parent=self)
        self._transformed_coords_dest_file_line_edit.file_dialog.setWindowTitle(
            'Select transformed coordinates destination')
        self._transformed_coords_dest_file_line_edit.setText(transformed_coords_dest_file_line_edit_text)
        # noinspection PyUnresolvedReferences
        self._transformed_coords_dest_file_line_edit.textChanged.connect(lambda text: self.refresh(text))

        pre_transform_file_line_edit_text = str(settings.value(
            self.PRE_TRANSFORM_SETTING, defaultValue=self.DEFAULT_PRE_TRANSFORM
        ))
        self._pre_transform_file_line_edit = FileLineEdit(parent=self)
        self._pre_transform_file_line_edit.file_dialog.setWindowTitle('Select pre-transform')
        self._pre_transform_file_line_edit.setText(pre_transform_file_line_edit_text)
        self._pre_transform_file_line_edit.file_dialog.setFileMode(QFileDialog.ExistingFile)
        self._pre_transform_file_line_edit.file_dialog.setNameFilter('Pickle files (*.pickle)')
        # noinspection PyUnresolvedReferences
        self._pre_transform_file_line_edit.textChanged.connect(lambda text: self.refresh(text))

        post_transform_file_line_edit_text = str(settings.value(
            self.POST_TRANSFORM_SETTING, defaultValue=self.DEFAULT_POST_TRANSFORM
        ))
        self._post_transform_file_line_edit = FileLineEdit(parent=self)
        self._post_transform_file_line_edit.file_dialog.setWindowTitle('Select post-transform')
        self._post_transform_file_line_edit.file_dialog.setFileMode(QFileDialog.ExistingFile)
        self._post_transform_file_line_edit.file_dialog.setNameFilter('Pickle files (*.pickle)')
        self._post_transform_file_line_edit.setText(post_transform_file_line_edit_text)
        # noinspection PyUnresolvedReferences
        self._post_transform_file_line_edit.textChanged.connect(lambda text: self.refresh(text))

        self._button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        # noinspection PyUnresolvedReferences
        self._button_box.rejected.connect(self.reject)

        # noinspection PyUnresolvedReferences
        @self._button_box.accepted.connect
        def on_button_box_accepted():
            settings.setValue(self.SELECTION_MODE_SETTING, self.selection_mode.value)
            settings.setValue(self.SOURCE_IMAGES_SETTING, str(self.source_images_path))
            settings.setValue(self.SOURCE_REGEX_SETTING, self.source_regex)
            settings.setValue(self.TARGET_IMAGES_SETTING, str(self.target_images_path))
            settings.setValue(self.TARGET_REGEX_SETTING, self.target_regex)
            settings.setValue(self.CONTROL_POINTS_DEST_SETTING, str(self.control_points_dest_path))
            settings.setValue(self.TRANSFORM_DEST_SETTING, str(self.transform_dest_path))
            settings.setValue(self.TRANSFORM_TYPE_SETTING, self.transform_type.value)
            settings.setValue(self.MATCHING_STRATEGY_SETTING, self.matching_strategy.value)
            settings.setValue(self.SOURCE_COORDS_SETTING, str(self.source_coords_path or ''))
            settings.setValue(self.SOURCE_COORDS_REGEX_SETTING, self.source_coords_regex)
            settings.setValue(self.TRANSFORMED_COORDS_DEST_SETTING, str(self.transformed_coords_dest_path or ''))
            settings.setValue(self.PRE_TRANSFORM_SETTING, str(self.pre_transform_path or ''))
            settings.setValue(self.POST_TRANSFORM_SETTING, str(self.post_transform_path or ''))
            settings.sync()
            self.accept()

        required_group_box = QGroupBox(self)
        required_group_box_layout = QFormLayout()
        required_group_box_layout.setLabelAlignment(Qt.AlignLeft)
        required_group_box_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        required_group_box_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        required_group_box_layout.addRow('Source image(s):', self._source_images_file_line_edit)
        required_group_box_layout.addRow(self._source_regex_label, self._source_regex_line_edit)
        required_group_box_layout.addRow('Target image(s):', self._target_images_file_line_edit)
        required_group_box_layout.addRow(self._target_regex_label, self._target_regex_line_edit)
        required_group_box_layout.addRow('Control points dest.:', self._control_points_dest_file_line_edit)
        required_group_box_layout.addRow('Transform dest.:', self._transform_dest_file_line_edit)
        required_group_box_layout.addRow('Transform type:', self._transform_type_combo_box)
        required_group_box.setLayout(required_group_box_layout)

        optional_group_box = QGroupBox(self)
        optional_group_box_layout = QFormLayout()
        optional_group_box_layout.setLabelAlignment(Qt.AlignLeft)
        optional_group_box_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        optional_group_box_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        optional_group_box_layout.addRow('Source coordinates:', self._source_coords_file_line_edit)
        optional_group_box_layout.addRow(self._source_coords_regex_label, self._source_coords_regex_line_edit)
        optional_group_box_layout.addRow('Transformed coord. dest.:', self._transformed_coords_dest_file_line_edit)
        optional_group_box_layout.addRow('Pre-transform:', self._pre_transform_file_line_edit)
        optional_group_box_layout.addRow('Post-transform:', self._post_transform_file_line_edit)
        optional_group_box.setLayout(optional_group_box_layout)

        layout = QVBoxLayout()
        mode_layout = QHBoxLayout()
        # noinspection PyArgumentList
        mode_layout.addWidget(self._file_selection_mode_button)
        # noinspection PyArgumentList
        mode_layout.addWidget(self._dir_selection_mode_button)
        # noinspection PyArgumentList
        mode_layout.addWidget(self._matching_strategy_combo_box)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)
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
    def selection_mode(self) -> Optional['NappingDialog.SelectionMode']:
        selection_mode_value = self._selection_mode_buttons_group.checkedId()
        if selection_mode_value >= 0:
            return NappingDialog.SelectionMode(selection_mode_value)
        return None

    @property
    def matching_strategy(self) -> 'NappingDialog.MatchingStrategy':
        return NappingDialog.MatchingStrategy(self._matching_strategy_combo_box.currentText())

    @property
    def source_images_path(self) -> Optional[Path]:
        return self._source_images_file_line_edit.path

    @property
    def source_regex(self) -> str:
        return self._source_regex_line_edit.text()

    @property
    def target_images_path(self) -> Optional[Path]:
        return self._target_images_file_line_edit.path

    @property
    def target_regex(self) -> str:
        return self._target_regex_line_edit.text()

    @property
    def control_points_dest_path(self) -> Optional[Path]:
        return self._control_points_dest_file_line_edit.path

    @property
    def transform_dest_path(self) -> Optional[Path]:
        return self._transform_dest_file_line_edit.path

    @property
    def transform_type(self) -> 'NappingDialog.TransformType':
        return NappingDialog.TransformType(self._transform_type_combo_box.currentText())

    @property
    def source_coords_path(self) -> Optional[Path]:
        return self._source_coords_file_line_edit.path

    @property
    def source_coords_regex(self) -> str:
        return self._source_coords_regex_line_edit.text()

    @property
    def transformed_coords_dest_path(self) -> Optional[Path]:
        return self._transformed_coords_dest_file_line_edit.path

    @property
    def pre_transform_path(self) -> Optional[Path]:
        return self._pre_transform_file_line_edit.path

    @property
    def post_transform_path(self) -> Optional[Path]:
        return self._post_transform_file_line_edit.path

    @property
    def is_valid(self) -> bool:
        if self.selection_mode == NappingDialog.SelectionMode.FILE:
            if self.source_images_path is None or not self.source_images_path.is_file():
                return False
            if self.target_images_path is None or not self.target_images_path.is_file():
                return False
            if self.control_points_dest_path is None or self.control_points_dest_path.is_dir():
                return False
            if self.transform_dest_path is None or self.transform_dest_path.is_dir():
                return False
            if self.source_coords_path is not None and not self.source_coords_path.is_file():
                return False
            if self.transformed_coords_dest_path is not None and self.control_points_dest_path.is_dir():
                return False
        elif self.selection_mode == NappingDialog.SelectionMode.DIR:
            if self.source_images_path is None or not self.source_images_path.is_dir():
                return False
            if self.target_images_path is None or not self.target_images_path.is_dir():
                return False
            if self.control_points_dest_path is None or self.control_points_dest_path.is_file():
                return False
            if self.transform_dest_path is None or self.transform_dest_path.is_file():
                return False
            if self.source_coords_path is not None and not self.source_coords_path.is_dir():
                return False
            if self.transformed_coords_dest_path is not None and self.control_points_dest_path.is_file():
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
        if self.pre_transform_path is not None and not self.pre_transform_path.is_file():
            return False
        if self.post_transform_path is not None and not self.post_transform_path.is_file():
            return False
        if bool(self.source_coords_path) != bool(self.transformed_coords_dest_path):
            return False
        if (bool(self.pre_transform_path) or bool(self.post_transform_path)) and not bool(self.source_coords_path):
            return False
        unique_paths = {
            self.source_images_path,
            self.target_images_path,
            self.control_points_dest_path,
            self.transform_dest_path
        }
        if self.source_coords_path is not None and self.transformed_coords_dest_path is not None:
            unique_paths.update({self.source_coords_path, self.transformed_coords_dest_path})
            if len(unique_paths) != 6:
                return False
        elif len(unique_paths) != 4:
            return False
        return True

    def refresh(self, last_path: Union[str, Path, None] = None):
        if last_path:
            directory = str(Path(last_path).parent)
            self._source_images_file_line_edit.file_dialog.setDirectory(directory)
            self._target_images_file_line_edit.file_dialog.setDirectory(directory)
            self._control_points_dest_file_line_edit.file_dialog.setDirectory(directory)
            self._transform_dest_file_line_edit.file_dialog.setDirectory(directory)
            self._source_coords_file_line_edit.file_dialog.setDirectory(directory)
            self._transformed_coords_dest_file_line_edit.file_dialog.setDirectory(directory)
            self._pre_transform_file_line_edit.file_dialog.setDirectory(directory)
            self._post_transform_file_line_edit.file_dialog.setDirectory(directory)

        if self.selection_mode in (NappingDialog.SelectionMode.FILE, NappingDialog.SelectionMode.DIR):
            if self.selection_mode == NappingDialog.SelectionMode.FILE:
                any_file_mode = QFileDialog.AnyFile
                existing_file_mode = QFileDialog.ExistingFile
                control_points_name_filter = 'CSV files (*.csv)'
                control_points_default_suffix = '.csv'
                transform_name_filter = 'Pickle files (*.pickle)'
                transform_default_suffix = '.pickle'
                source_coords_name_filter = transformed_coords_name_filter = 'CSV files (*.csv)'
                source_coords_default_suffix = transformed_coords_default_suffix = '.csv'
                show_dirs_only = False
            else:
                any_file_mode = QFileDialog.Directory
                existing_file_mode = QFileDialog.Directory
                control_points_name_filter = None
                control_points_default_suffix = None
                transform_name_filter = None
                transform_default_suffix = None
                source_coords_name_filter = transformed_coords_name_filter = None
                source_coords_default_suffix = transformed_coords_default_suffix = None
                show_dirs_only = True

            self._source_images_file_line_edit.file_dialog.setFileMode(existing_file_mode)
            self._source_images_file_line_edit.file_dialog.setOption(QFileDialog.ShowDirsOnly, show_dirs_only)

            self._target_images_file_line_edit.file_dialog.setFileMode(existing_file_mode)
            self._target_images_file_line_edit.file_dialog.setOption(QFileDialog.ShowDirsOnly, show_dirs_only)

            self._control_points_dest_file_line_edit.file_dialog.setFileMode(any_file_mode)
            self._control_points_dest_file_line_edit.file_dialog.setNameFilter(control_points_name_filter)
            self._control_points_dest_file_line_edit.file_dialog.setDefaultSuffix(control_points_default_suffix)
            self._control_points_dest_file_line_edit.file_dialog.setOption(QFileDialog.ShowDirsOnly, show_dirs_only)

            self._transform_dest_file_line_edit.file_dialog.setFileMode(any_file_mode)
            self._transform_dest_file_line_edit.file_dialog.setNameFilter(transform_name_filter)
            self._transform_dest_file_line_edit.file_dialog.setDefaultSuffix(transform_default_suffix)
            self._transform_dest_file_line_edit.file_dialog.setOption(QFileDialog.ShowDirsOnly, show_dirs_only)

            self._source_coords_file_line_edit.file_dialog.setFileMode(existing_file_mode)
            self._source_coords_file_line_edit.file_dialog.setNameFilter(source_coords_name_filter)
            self._source_coords_file_line_edit.file_dialog.setDefaultSuffix(source_coords_default_suffix)
            self._source_coords_file_line_edit.file_dialog.setOption(QFileDialog.ShowDirsOnly, show_dirs_only)

            self._transformed_coords_dest_file_line_edit.file_dialog.setFileMode(any_file_mode)
            self._transformed_coords_dest_file_line_edit.file_dialog.setNameFilter(transformed_coords_name_filter)
            self._transformed_coords_dest_file_line_edit.file_dialog.setDefaultSuffix(transformed_coords_default_suffix)
            self._transformed_coords_dest_file_line_edit.file_dialog.setOption(QFileDialog.ShowDirsOnly, show_dirs_only)

        if self.selection_mode == NappingDialog.SelectionMode.DIR:
            self._matching_strategy_combo_box.setEnabled(True)
        else:
            self._matching_strategy_combo_box.setEnabled(False)

        dir_selection_mode = (self.selection_mode == NappingDialog.SelectionMode.DIR)
        regex_matching_strategy = (self.matching_strategy == NappingDialog.MatchingStrategy.REGEX)
        self._source_regex_label.setEnabled(dir_selection_mode and regex_matching_strategy)
        self._source_regex_line_edit.setEnabled(dir_selection_mode and regex_matching_strategy)
        self._target_regex_label.setEnabled(dir_selection_mode and regex_matching_strategy)
        self._target_regex_line_edit.setEnabled(dir_selection_mode and regex_matching_strategy)
        self._source_coords_regex_label.setEnabled(dir_selection_mode and regex_matching_strategy)
        self._source_coords_regex_line_edit.setEnabled(dir_selection_mode and regex_matching_strategy)

        self._button_box.button(QDialogButtonBox.Ok).setEnabled(self.is_valid)
