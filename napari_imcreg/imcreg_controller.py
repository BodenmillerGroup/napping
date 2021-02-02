import numpy as np
import pandas as pd
import re

from napari.layers import Image, Points
from napari.layers.utils.text import TextManager
from napari_imc import IMCController
from napari_imc.models import IMCFileModel
from pathlib import Path
from qtpy.QtCore import QSettings
from skimage.transform import estimate_transform, ProjectiveTransform
from typing import Callable, List, Optional, Tuple, Union

from napari_imcreg.utils import iter_files
from napari_imcreg.widgets import RegistrationDialog, RegistrationWidget


class IMCRegControllerException(Exception):
    pass


class IMCRegController:
    MATCH_ALPHABETICAL = 'alphabetical'
    MATCH_FILENAME = 'filename'
    MATCH_REGEX = 'regex'

    EUCLIDEAN_TRANSFORM = 'euclidean'
    SIMILARITY_TRANSFORM = 'similarity'
    AFFINE_TRANSFORM = 'affine'

    def __init__(self, source_imc_controller: IMCController, target_imc_controller: IMCController):
        self._settings = QSettings('Bodenmiller Lab', 'napari-imcreg')
        self._source_view_controller = self.ViewController(self, source_imc_controller)
        self._target_view_controller = self.ViewController(self, target_imc_controller)
        self._source_file_paths: Optional[List[Path]] = None
        self._target_file_paths: Optional[List[Path]] = None
        self._control_points_file_paths: Optional[List[Path]] = None
        self._source_coords_file_paths: Optional[List[Path]] = None
        self._transformed_coords_file_paths: Optional[List[Path]] = None
        self._coord_transform_type: Optional[str] = None
        self._current_index: Optional[int] = None
        self._current_transform: Optional[ProjectiveTransform] = None
        self._current_source_coords: Optional[pd.DataFrame] = None
        self._current_transformed_coords: Optional[pd.DataFrame] = None

    def initialize(self):
        self._source_view_controller.initialize()
        self._target_view_controller.initialize()

    def show_dialog(self) -> bool:
        registration_dialog = RegistrationDialog(self._settings)
        if registration_dialog.exec() == RegistrationDialog.Accepted:
            if registration_dialog.selection_mode == RegistrationDialog.SelectionMode.FILE:
                return self.load_file(
                    registration_dialog.source_path,
                    registration_dialog.target_path,
                    registration_dialog.control_points_path,
                    source_coords_file_path=registration_dialog.source_coords_path,
                    transformed_coords_file_path=registration_dialog.transformed_coords_path,
                    coord_transform_type=self._to_coord_transform_type(registration_dialog.coord_transform_type),
                )
            return self.load_dir(
                self._to_file_matching_strategy(registration_dialog.file_matching_strategy),
                registration_dialog.source_path,
                registration_dialog.target_path,
                registration_dialog.control_points_path,
                source_coords_dir_path=registration_dialog.source_coords_path,
                transformed_coords_dir_path=registration_dialog.transformed_coords_path,
                coord_transform_type=self._to_coord_transform_type(registration_dialog.coord_transform_type),
                source_regex=registration_dialog.source_regex,
                target_regex=registration_dialog.target_regex,
                source_coords_regex=registration_dialog.source_coords_regex,
            )
        return False

    def load_file(
            self,
            source_file_path: Union[str, Path],
            target_file_path: Union[str, Path],
            control_points_file_path: Union[str, Path],
            source_coords_file_path: Union[str, Path, None] = None,
            transformed_coords_file_path: Union[str, Path, None] = None,
            coord_transform_type: Optional[str] = None,
    ) -> bool:
        self._source_file_paths = [Path(source_file_path)]
        self._target_file_paths = [Path(target_file_path)]
        self._control_points_file_paths = [Path(control_points_file_path)]
        self._source_coords_file_paths = None
        if source_coords_file_path is not None:
            self._source_coords_file_paths = [Path(source_coords_file_path)]
        self._transformed_coords_file_paths = None
        if transformed_coords_file_path is not None:
            self._transformed_coords_file_paths = [Path(transformed_coords_file_path)]
        self._coord_transform_type = coord_transform_type
        self._current_index = 0
        return self._show()

    def load_dir(
            self,
            file_matching_strategy: str,
            source_dir_path: Union[str, Path],
            target_dir_path: Union[str, Path],
            control_points_dir_path: Union[str, Path],
            source_coords_dir_path: Optional[Union[str, Path]] = None,
            transformed_coords_dir_path: Optional[Union[str, Path]] = None,
            coord_transform_type: Optional[str] = None,
            source_regex: Optional[str] = None,
            target_regex: Optional[str] = None,
            source_coords_regex: Optional[str] = None,
    ) -> bool:
        source_dir_path = Path(source_dir_path)
        target_dir_path = Path(target_dir_path)
        control_points_dir_path = Path(control_points_dir_path)
        if source_coords_dir_path is not None:
            source_coords_dir_path = Path(source_coords_dir_path)
        if transformed_coords_dir_path is not None:
            transformed_coords_dir_path = Path(transformed_coords_dir_path)
        if file_matching_strategy == self.MATCH_ALPHABETICAL:
            self._source_file_paths, self._target_file_paths, self._source_coords_file_paths = self._match_alphabetical(
                source_dir_path,
                target_dir_path,
                source_coords_dir_path,
            )
        elif file_matching_strategy == self.MATCH_FILENAME:
            self._source_file_paths, self._target_file_paths, self._source_coords_file_paths = self._match_filename(
                source_dir_path,
                target_dir_path,
                source_coords_dir_path,
            )
        elif file_matching_strategy == self.MATCH_REGEX:
            self._source_file_paths, self._target_file_paths, self._source_coords_file_paths = self._match_regex(
                source_dir_path, source_regex,
                target_dir_path, target_regex,
                source_coords_dir_path, source_coords_regex,
            )
        else:
            raise ValueError(f'Unsupported file matching strategy: {file_matching_strategy}')
        self._control_points_file_paths = [
            control_points_dir_path / f'{path.stem}.npy' for path in self._target_file_paths
        ]
        self._transformed_coords_file_paths = None
        if transformed_coords_dir_path is not None:
            self._transformed_coords_file_paths = [
                transformed_coords_dir_path / f'{path.stem}.csv' for path in self._target_file_paths
            ]
        self._coord_transform_type = coord_transform_type
        self._current_index = 0
        return self._show()

    def show_prev(self) -> bool:
        self._current_index = (self._current_index - 1) % len(self._source_file_paths)
        return self._show()

    def show_next(self) -> bool:
        self._current_index = (self._current_index + 1) % len(self._source_file_paths)
        return self._show()

    @property
    def settings(self) -> QSettings:
        return self._settings

    @property
    def source_view_controller(self) -> 'IMCRegController.ViewController':
        return self._source_view_controller

    @property
    def target_view_controller(self) -> 'IMCRegController.ViewController':
        return self._target_view_controller

    @property
    def source_file_paths(self) -> Optional[List[Path]]:
        return self._source_file_paths

    @property
    def target_file_paths(self) -> Optional[List[Path]]:
        return self._target_file_paths

    @property
    def control_points_file_paths(self) -> Optional[List[Path]]:
        return self._control_points_file_paths

    @property
    def source_coords_file_paths(self) -> Optional[List[Path]]:
        return self._source_coords_file_paths

    @property
    def transformed_coords_file_paths(self) -> Optional[List[Path]]:
        return self._transformed_coords_file_paths

    @property
    def coord_transform_type(self) -> Optional[str]:
        return self._coord_transform_type

    @property
    def current_source_file_path(self) -> Optional[Path]:
        if self._current_index is not None:
            return self._source_file_paths[self._current_index]
        return None

    @property
    def current_target_file_path(self) -> Optional[Path]:
        if self._current_index is not None:
            return self._target_file_paths[self._current_index]
        return None

    @property
    def current_control_points_file_path(self) -> Optional[Path]:
        if self._current_index is not None:
            return self._control_points_file_paths[self._current_index]
        return None

    @property
    def current_source_coords_file_path(self) -> Optional[Path]:
        if self._current_index is not None and self._source_coords_file_paths is not None:
            return self._source_coords_file_paths[self._current_index]
        return None

    @property
    def current_transformed_coords_file_path(self) -> Optional[Path]:
        if self._current_index is not None and self._transformed_coords_file_paths is not None:
            return self._transformed_coords_file_paths[self._current_index]
        return None

    @property
    def current_source_coords(self) -> Optional[pd.DataFrame]:
        return self._current_source_coords

    @property
    def current_transformed_coords(self) -> Optional[pd.DataFrame]:
        return self._current_transformed_coords

    @property
    def current_transform(self) -> Optional[ProjectiveTransform]:
        return self._current_transform

    @property
    def matched_control_points(self) -> Optional[pd.DataFrame]:
        source_control_points = self._source_view_controller.control_points
        target_control_points = self._target_view_controller.control_points
        if source_control_points is not None and target_control_points is not None:
            return pd.merge(
                source_control_points, target_control_points,
                left_index=True, right_index=True, suffixes=('_source', '_target')
            )
        return None

    @property
    def current_residuals(self) -> Optional[np.ndarray]:
        if self._current_transform is not None:
            matched_control_points = self.matched_control_points
            if matched_control_points is not None:
                src = matched_control_points.loc[:, ['x_source', 'y_source']].values
                dst = matched_control_points.loc[:, ['x_target', 'y_target']].values
                return self._current_transform.residuals(src, dst)
        return None

    def _show(self) -> bool:
        if 0 <= self._current_index < len(self._source_file_paths):
            self._source_view_controller.show(self.current_source_file_path)
            self._target_view_controller.show(self.current_target_file_path)
            if self.current_control_points_file_path.is_file():
                self._load_matched_control_points()
            if self.current_source_coords_file_path is not None and self.current_source_coords_file_path.is_file():
                self._load_current_source_coords()
            self._update_current_transform()
            self._update_current_transformed_coords()
            self._source_view_controller.refresh()
            self._target_view_controller.refresh()
            return True
        return False

    @staticmethod
    def _match_alphabetical(
            source_dir_path: Path,
            target_dir_path: Path,
            source_coords_dir_path: Optional[Path],
    ) -> Tuple[List[Path], List[Path], List[Path]]:
        source_file_paths = sorted(iter_files(source_dir_path), key=lambda p: p.stem)
        target_file_paths = sorted(iter_files(target_dir_path), key=lambda p: p.stem)
        if len(target_file_paths) != len(source_file_paths):
            raise IMCRegControllerException('Number of target images does not match the number of source images')
        source_coords_file_paths = None
        if source_coords_dir_path is not None:
            source_coords_file_paths = sorted(iter_files(source_coords_dir_path, suffix='.csv'), key=lambda p: p.stem)
            if len(source_coords_file_paths) != len(source_file_paths):
                raise IMCRegControllerException('Number of coordinate files does not match the number of source images')
        return source_file_paths, target_file_paths, source_coords_file_paths

    @classmethod
    def _match_filename(
            cls,
            source_dir_path: Path,
            target_dir_path: Path,
            source_coords_dir_path: Optional[Path],
    ) -> Tuple[List[Path], List[Path], List[Path]]:
        def match_target(target_file_path: Path, source_file_path: Path):
            return target_file_path.stem == source_file_path.stem

        def match_source_coords(source_coords_file_path: Path, source_file_path: Path):
            return source_coords_file_path.stem == source_file_path.stem

        return cls._match(source_dir_path, target_dir_path, match_target, source_coords_dir_path, match_source_coords)

    @classmethod
    def _match_regex(
            cls,
            source_dir_path: Path, source_regex: str,
            target_dir_path: Path, target_regex: str,
            source_coords_dir_path: Optional[Path], source_coords_regex: Optional[str],
    ) -> Tuple[List[Path], List[Path], List[Path]]:
        source_regex_compiled = re.compile(source_regex)
        target_regex_compiled = re.compile(target_regex)
        source_coords_regex_compiled = re.compile(source_coords_regex)

        def match_target(target_file_path: Path, source_file_path: Path):
            target_match = target_regex_compiled.search(target_file_path.name)
            source_match = source_regex_compiled.search(source_file_path.name)
            if target_match is not None and source_match is not None:
                return target_match.group() == source_match.group()
            return False

        def match_source_coords(source_coords_file_path: Path, source_file_path: Path):
            source_coords_match = source_coords_regex_compiled.search(source_coords_file_path.name)
            source_match = source_regex_compiled.search(source_file_path.name)
            if source_coords_match is not None and source_match is not None:
                return source_coords_match.group() == source_match.group()
            return False

        return cls._match(source_dir_path, target_dir_path, match_target, source_coords_dir_path, match_source_coords)

    @staticmethod
    def _match(
            source_dir_path: Path,
            target_dir_path: Path, target_criterion: Callable[[Path, Path], bool],
            source_coords_dir_path: Optional[Path], source_coords_criterion: Optional[Callable[[Path, Path], bool]]
    ) -> Tuple[List[Path], List[Path], List[Path]]:
        source_file_paths = list(iter_files(source_dir_path))
        target_file_paths = list(iter_files(target_dir_path))
        source_coords_file_paths = None
        if source_coords_dir_path is not None:
            source_coords_file_paths = list(iter_files(source_coords_dir_path, suffix='.csv'))
        matched_source_file_paths = []
        matched_target_file_paths = []
        matched_source_coords_file_paths = None
        if source_coords_file_paths is not None:
            matched_source_coords_file_paths = []
        for matched_source_file_path in source_file_paths:
            matched_target_file_path = next(
                (p for p in target_file_paths if target_criterion(p, matched_source_file_path)),
                None
            )
            if matched_target_file_path is None:
                continue
            matched_source_coords_file_path = None
            if source_coords_file_paths is not None:
                matched_source_coords_file_path = next(
                    (p for p in source_coords_file_paths if source_coords_criterion(p, matched_source_file_path)),
                    None
                )
                if matched_source_coords_file_path is None:
                    continue
            matched_source_file_paths.append(matched_source_file_path)
            matched_target_file_paths.append(matched_target_file_path)
            if matched_source_coords_file_paths is not None:
                matched_source_coords_file_paths.append(matched_source_coords_file_path)
        return matched_source_file_paths, matched_target_file_paths, matched_source_coords_file_paths

    def _handle_control_points_changed(self):
        self._save_matched_control_points()
        self._update_current_transform()
        self._update_current_transformed_coords()
        if self._current_transformed_coords is not None:
            self._save_current_transformed_coords()
        self.source_view_controller.refresh()
        self.target_view_controller.refresh()

    def _load_matched_control_points(self):
        matched_control_points = pd.read_csv(self.current_control_points_file_path)
        source_control_points = matched_control_points.loc[:, ['x_source', 'y_source']]
        target_control_points = matched_control_points.loc[:, ['x_target', 'y_target']]
        source_control_points.columns = ['x', 'y']
        target_control_points.columns = ['x', 'y']
        self.source_view_controller.control_points = source_control_points
        self.target_view_controller.control_points = target_control_points

    def _save_matched_control_points(self):
        self.matched_control_points.to_csv(self.current_control_points_file_path, index=False)

    def _load_current_source_coords(self):
        self._current_source_coords = pd.read_csv(self.current_source_coords_file_path)

    def _save_current_transformed_coords(self):
        self._current_transformed_coords.to_csv(self.current_transformed_coords_file_path, index=False)

    def _update_current_transform(self):
        if self._coord_transform_type == self.EUCLIDEAN_TRANSFORM:
            transform_type = 'euclidean'
        elif self._coord_transform_type == self.SIMILARITY_TRANSFORM:
            transform_type = 'similarity'
        elif self._coord_transform_type == self.AFFINE_TRANSFORM:
            transform_type = 'affine'
        else:
            raise ValueError(f'Unsupported coordinate transform type: {self._coord_transform_type}')
        self._current_transform = None
        matched_control_points = self.matched_control_points
        if matched_control_points.shape[0] >= 3:
            src = matched_control_points.loc[:, ['x_source', 'y_source']].values
            dst = matched_control_points.loc[:, ['x_target', 'y_target']].values
            self._current_transform = estimate_transform(transform_type, src, dst)

    def _update_current_transformed_coords(self):
        if self._current_source_coords is not None and self._current_transform is not None:
            data = self._current_source_coords.loc[:, ['X', 'Y']].values
            self._current_transformed_coords = self._current_source_coords.copy()
            self._current_transformed_coords.loc[:, ['X', 'Y']] = self._current_transform(data)
        else:
            self._current_transformed_coords = None

    @classmethod
    def _to_file_matching_strategy(cls, file_matching_strategy: RegistrationDialog.FileMatchingStrategy) -> str:
        if file_matching_strategy == RegistrationDialog.FileMatchingStrategy.ALPHABETICAL:
            return cls.MATCH_ALPHABETICAL
        if file_matching_strategy == RegistrationDialog.FileMatchingStrategy.FILENAME:
            return cls.MATCH_FILENAME
        if file_matching_strategy == RegistrationDialog.FileMatchingStrategy.REGEX:
            return cls.MATCH_REGEX
        raise ValueError('Unsupported file matching strategy')

    @classmethod
    def _to_coord_transform_type(cls, coord_transform_type: RegistrationDialog.CoordinateTransformType) -> str:
        if coord_transform_type == RegistrationDialog.CoordinateTransformType.EUCLIDEAN:
            return cls.EUCLIDEAN_TRANSFORM
        if coord_transform_type == RegistrationDialog.CoordinateTransformType.SIMILARITY:
            return cls.SIMILARITY_TRANSFORM
        if coord_transform_type == RegistrationDialog.CoordinateTransformType.AFFINE:
            return cls.AFFINE_TRANSFORM
        raise ValueError('Unsupported coordinate transform type')

    class ViewController:
        _points_layer_args = {
            'properties': {'id': np.arange(1, 1000)},  # see https://github.com/napari/napari/issues/2115
            'text': {'text': 'id', 'anchor': 'upper_left', 'color': 'red', 'translation': (0, 20)},
            'symbol': 'cross',
            'edge_width': 0,
            'face_color': 'red',
            'name': 'Control points',
        }

        def __init__(self, controller: 'IMCRegController', imc_controller: IMCController):
            self._controller = controller
            self._imc_controller = imc_controller
            self._widget: Optional[RegistrationWidget] = None
            self._image_path: Optional[Path] = None
            self._image_imc_file: Optional[IMCFileModel] = None
            self._image_layers: List[Image] = []
            self._points_layer: Optional[Points] = None

        def initialize(self):
            self._widget = RegistrationWidget(self)
            self._imc_controller.viewer.window.add_dock_widget(self._widget, name='Control point matching')
            self._imc_controller.dock_widget.hide()

        def show(self, path: Path):
            self._close_image()
            self._remove_points_layer()
            self._open_image(path)
            self._add_points_layer()

        def refresh(self):
            self._widget.refresh()

        @property
        def controller(self) -> 'IMCRegController':
            return self._controller

        @property
        def imc_controller(self) -> IMCController:
            return self._imc_controller

        @property
        def widget(self) -> Optional[RegistrationWidget]:
            return self._widget

        @property
        def image_path(self) -> Optional[Path]:
            return self._image_path

        @property
        def image_imc_file(self) -> Optional[IMCFileModel]:
            return self._image_imc_file

        @property
        def image_layers(self) -> List[Image]:
            return self._image_layers

        @property
        def points_layer(self) -> Optional[Points]:
            return self._points_layer

        @property
        def control_points(self) -> Optional[pd.DataFrame]:
            if self._points_layer is not None:
                return pd.DataFrame(
                    data=self._points_layer.data,
                    index=self._points_layer.properties['id'],
                    columns=['x', 'y']
                )
            return None

        @control_points.setter
        def control_points(self, control_points: pd.DataFrame):
            if self._points_layer is None:
                raise RuntimeError('points layer is None')
            self._points_layer.data = control_points.values
            properties = self._points_layer.properties
            properties['id'] = control_points.index.values
            self._points_layer.properties = properties
            self._widget.refresh()

        def _open_image(self, path: Path):
            self._image_path = path
            if path.suffix.lower() in ('.mcd', '.txt'):
                self._imc_controller.dock_widget.show()
                self._image_imc_file = self._imc_controller.open_imc_file(path)
            else:
                self._imc_controller.dock_widget.hide()
                self._image_layers = self._imc_controller.viewer.open(str(path), layer_type='image')

        def _close_image(self):
            self._image_path = None
            if self._image_imc_file is not None:
                self._imc_controller.close_imc_file(self._image_imc_file)
                self._image_imc_file = None
            while len(self._image_layers) > 0:
                self._imc_controller.viewer.layers.remove(self._image_layers.pop())
            self._imc_controller.dock_widget.hide()

        def _add_points_layer(self):
            # noinspection PyUnresolvedReferences
            self._points_layer: Points = self._imc_controller.viewer.add_points(**self._points_layer_args)
            self._points_layer.mode = 'add'

            @self._points_layer.mouse_drag_callbacks.append
            def on_points_layer_mouse_drag(layer, _):
                if layer.mode == 'add':
                    layer.current_properties['id'][0] = max(layer.properties['id'], default=0) + 1

            @self._points_layer.events.current_properties.connect
            def on_points_layer_current_properties_changed(_):
                self._points_layer_text_workaround()
                self._controller._handle_control_points_changed()

        def _remove_points_layer(self):
            if self._points_layer is not None:
                self._imc_controller.viewer.layers.remove(self._points_layer)
                self._points_layer = None

        # see https://github.com/napari/napari/issues/2115
        def _points_layer_text_workaround(self):
            text_args = self._points_layer_args['text']
            if not isinstance(text_args, dict):
                text_args = {'text': text_args}
            n_text = len(self._points_layer.data)
            self._points_layer._text = TextManager(**text_args, n_text=n_text, properties=self._points_layer.properties)
            self._points_layer.refresh_text()
