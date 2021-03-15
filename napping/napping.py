import numpy as np
import pandas as pd
import re

from contextlib import contextmanager
from napari import Viewer
from napari.layers import Points
from napari.layers.utils.text import TextManager
from pathlib import Path
from qtpy.QtCore import QSettings
from skimage.transform import ProjectiveTransform
from typing import Callable, List, Optional, Tuple, Type, Union

from napping.utils import iter_files
from napping.widgets import NappingDialog, NappingWidget


class Napping:
    MATCH_ALPHABETICAL = 'alphabetical'
    MATCH_FILENAME = 'filename'
    MATCH_REGEX = 'regex'

    def __init__(self, source_viewer: Viewer, target_viewer: Viewer):
        self._settings = QSettings('Bodenmiller Lab', 'napping')
        self._source_view_controller = self.ViewController(source_viewer, self)
        self._target_view_controller = self.ViewController(target_viewer, self)
        self._source_image_file_paths: Optional[List[Path]] = None
        self._target_image_file_paths: Optional[List[Path]] = None
        self._control_points_dest_file_paths: Optional[List[Path]] = None
        self._joint_transform_dest_file_paths: Optional[List[Path]] = None
        self._transform_class: Optional[Type[ProjectiveTransform]] = None
        self._source_coords_file_paths: Optional[List[Path]] = None
        self._transformed_coords_dest_file_paths: Optional[List[Path]] = None
        self._pre_transform: Optional[np.ndarray] = None
        self._post_transform: Optional[np.ndarray] = None
        self._current_index: Optional[int] = None
        self._current_transform: Optional[np.ndarray] = None
        self._current_source_coords: Optional[pd.DataFrame] = None
        self._current_transformed_coords: Optional[pd.DataFrame] = None
        self._write_blocked = False

    def initialize(self):
        self._source_view_controller.initialize()
        self._target_view_controller.initialize()

    def show_dialog(self) -> bool:
        registration_dialog = NappingDialog(self._settings)
        if registration_dialog.exec() == NappingDialog.Accepted:
            if registration_dialog.selection_mode == NappingDialog.SelectionMode.FILE:
                return self.load_file(
                    registration_dialog.source_images_path,
                    registration_dialog.target_images_path,
                    registration_dialog.control_points_dest_path,
                    registration_dialog.joint_transform_dest_path,
                    registration_dialog.transform_class,
                    source_coords_file_path=registration_dialog.source_coords_path,
                    transformed_coords_dest_file_path=registration_dialog.transformed_coords_dest_path,
                    pre_transform_file_path=registration_dialog.pre_transform_path,
                    post_transform_file_path=registration_dialog.post_transform_path,
                )
            if registration_dialog.selection_mode == NappingDialog.SelectionMode.DIR:
                registration_dialog.control_points_dest_path.mkdir(exist_ok=True)
                registration_dialog.joint_transform_dest_path.mkdir(exist_ok=True)
                if registration_dialog.transformed_coords_dest_path is not None:
                    registration_dialog.transformed_coords_dest_path.mkdir(exist_ok=True)
                matching_strategy = {
                    NappingDialog.MatchingStrategy.ALPHABETICAL: self.MATCH_ALPHABETICAL,
                    NappingDialog.MatchingStrategy.FILENAME: self.MATCH_FILENAME,
                    NappingDialog.MatchingStrategy.REGEX: self.MATCH_REGEX,
                }[registration_dialog.matching_strategy]
                return self.load_dir(
                    matching_strategy,
                    registration_dialog.source_images_path,
                    registration_dialog.target_images_path,
                    registration_dialog.control_points_dest_path,
                    registration_dialog.joint_transform_dest_path,
                    registration_dialog.transform_class,
                    source_coords_dir_path=registration_dialog.source_coords_path,
                    transformed_coords_dest_dir_path=registration_dialog.transformed_coords_dest_path,
                    pre_transform_file_path=registration_dialog.pre_transform_path,
                    post_transform_file_path=registration_dialog.post_transform_path,
                    source_regex=registration_dialog.source_regex,
                    target_regex=registration_dialog.target_regex,
                    source_coords_regex=registration_dialog.source_coords_regex,
                )
        return False

    def load_file(
            self,
            source_image_file_path: Union[str, Path],
            target_image_file_path: Union[str, Path],
            control_points_dest_file_path: Union[str, Path],
            joint_transform_dest_file_path: Union[str, Path],
            transform_class: Type[ProjectiveTransform],
            source_coords_file_path: Union[str, Path, None] = None,
            transformed_coords_dest_file_path: Union[str, Path, None] = None,
            pre_transform_file_path: Union[str, Path, None] = None,
            post_transform_file_path: Union[str, Path, None] = None,

    ) -> bool:
        self._source_image_file_paths = [Path(source_image_file_path)]
        self._target_image_file_paths = [Path(target_image_file_path)]
        self._control_points_dest_file_paths = [Path(control_points_dest_file_path)]
        self._joint_transform_dest_file_paths = [Path(joint_transform_dest_file_path)]
        self._transform_class = transform_class
        self._source_coords_file_paths = None
        if source_coords_file_path is not None:
            self._source_coords_file_paths = [Path(source_coords_file_path)]
        self._transformed_coords_dest_file_paths = None
        if transformed_coords_dest_file_path is not None:
            self._transformed_coords_dest_file_paths = [Path(transformed_coords_dest_file_path)]
        self._load_pre_post_transforms(pre_transform_file_path, post_transform_file_path)
        self._current_index = 0
        return self._show()

    def load_dir(
            self,
            matching_strategy: str,
            source_image_dir_path: Union[str, Path],
            target_image_dir_path: Union[str, Path],
            control_points_dest_dir_path: Union[str, Path],
            joint_transform_dest_dir_path: Union[str, Path],
            transform_class: Type[ProjectiveTransform],
            source_coords_dir_path: Optional[Union[str, Path]] = None,
            transformed_coords_dest_dir_path: Optional[Union[str, Path]] = None,
            pre_transform_file_path: Union[str, Path, None] = None,
            post_transform_file_path: Union[str, Path, None] = None,
            source_regex: Optional[str] = None,
            target_regex: Optional[str] = None,
            source_coords_regex: Optional[str] = None,
    ) -> bool:
        source_image_dir_path = Path(source_image_dir_path)
        target_image_dir_path = Path(target_image_dir_path)
        control_points_dest_dir_path = Path(control_points_dest_dir_path)
        joint_transform_dest_dir_path = Path(joint_transform_dest_dir_path)
        if source_coords_dir_path is not None:
            source_coords_dir_path = Path(source_coords_dir_path)
        if transformed_coords_dest_dir_path is not None:
            transformed_coords_dest_dir_path = Path(transformed_coords_dest_dir_path)
        if matching_strategy == self.MATCH_ALPHABETICAL:
            file_paths = self._match_alphabetical(source_image_dir_path, target_image_dir_path, source_coords_dir_path)
        elif matching_strategy == self.MATCH_FILENAME:
            file_paths = self._match_filename(source_image_dir_path, target_image_dir_path, source_coords_dir_path)
        elif matching_strategy == self.MATCH_REGEX:
            file_paths = self._match_regex(source_image_dir_path, source_regex, target_image_dir_path, target_regex,
                                           source_coords_dir_path, source_coords_regex)
        else:
            raise ValueError(f'Unsupported file matching strategy: {matching_strategy}')
        self._source_image_file_paths, self._target_image_file_paths, self._source_coords_file_paths = file_paths
        self._control_points_dest_file_paths = [
            control_points_dest_dir_path / f'{path.stem}.csv' for path in self._target_image_file_paths
        ]
        self._joint_transform_dest_file_paths = [
            joint_transform_dest_dir_path / f'{path.stem}.npy' for path in self._target_image_file_paths
        ]
        self._transform_class = transform_class
        self._transformed_coords_dest_file_paths = None
        if transformed_coords_dest_dir_path is not None:
            self._transformed_coords_dest_file_paths = [
                transformed_coords_dest_dir_path / f'{path.stem}.csv' for path in self._target_image_file_paths
            ]
        self._load_pre_post_transforms(pre_transform_file_path, post_transform_file_path)
        self._current_index = 0
        return self._show()

    def show_prev(self) -> bool:
        self._current_index = (self._current_index - 1) % len(self._source_image_file_paths)
        return self._show()

    def show_next(self) -> bool:
        self._current_index = (self._current_index + 1) % len(self._source_image_file_paths)
        return self._show()

    @property
    def settings(self) -> QSettings:
        return self._settings

    @property
    def source_view_controller(self) -> 'Napping.ViewController':
        return self._source_view_controller

    @property
    def target_view_controller(self) -> 'Napping.ViewController':
        return self._target_view_controller

    @property
    def source_image_file_paths(self) -> Optional[List[Path]]:
        return self._source_image_file_paths

    @property
    def target_image_file_paths(self) -> Optional[List[Path]]:
        return self._target_image_file_paths

    @property
    def control_points_dest_file_paths(self) -> Optional[List[Path]]:
        return self._control_points_dest_file_paths

    @property
    def joint_transform_dest_file_paths(self) -> Optional[List[Path]]:
        return self._joint_transform_dest_file_paths

    @property
    def transform_class(self) -> Optional[Type[ProjectiveTransform]]:
        return self._transform_class

    @property
    def source_coords_file_paths(self) -> Optional[List[Path]]:
        return self._source_coords_file_paths

    @property
    def transformed_coords_dest_file_paths(self) -> Optional[List[Path]]:
        return self._transformed_coords_dest_file_paths

    @property
    def pre_transform(self) -> Optional[np.ndarray]:
        return self._pre_transform

    @property
    def post_transform(self) -> Optional[np.ndarray]:
        return self._post_transform

    @property
    def current_source_image_file_path(self) -> Optional[Path]:
        if self._current_index is not None:
            return self._source_image_file_paths[self._current_index]
        return None

    @property
    def current_target_image_file_path(self) -> Optional[Path]:
        if self._current_index is not None:
            return self._target_image_file_paths[self._current_index]
        return None

    @property
    def current_control_points_dest_file_path(self) -> Optional[Path]:
        if self._current_index is not None:
            return self._control_points_dest_file_paths[self._current_index]
        return None

    @property
    def current_joint_transform_dest_file_path(self) -> Optional[Path]:
        if self._current_index is not None:
            return self._joint_transform_dest_file_paths[self._current_index]
        return None

    @property
    def current_source_coords_file_path(self) -> Optional[Path]:
        if self._current_index is not None and self._source_coords_file_paths is not None:
            return self._source_coords_file_paths[self._current_index]
        return None

    @property
    def current_transformed_coords_dest_file_path(self) -> Optional[Path]:
        if self._current_index is not None and self._transformed_coords_dest_file_paths is not None:
            return self._transformed_coords_dest_file_paths[self._current_index]
        return None

    @property
    def current_transform(self) -> Optional[np.ndarray]:
        return self._current_transform

    @property
    def current_joint_transform(self) -> Optional[np.ndarray]:
        if self._current_transform is not None:
            transform = self._current_transform
            if self._pre_transform is not None:
                transform = transform @ self._pre_transform
            if self._post_transform is not None:
                transform = self._post_transform @ transform
            return transform
        return None

    @property
    def current_source_coords(self) -> Optional[pd.DataFrame]:
        return self._current_source_coords

    @property
    def current_transformed_coords(self) -> Optional[pd.DataFrame]:
        return self._current_transformed_coords

    @property
    def current_matched_control_points(self) -> Optional[pd.DataFrame]:
        source_control_points = self._source_view_controller.control_points
        target_control_points = self._target_view_controller.control_points
        if source_control_points is not None and target_control_points is not None:
            return pd.merge(
                source_control_points, target_control_points,
                left_index=True, right_index=True, suffixes=('_source', '_target')
            )
        return None

    @current_matched_control_points.setter
    def current_matched_control_points(self, value: Optional[pd.DataFrame]):
        source_control_points = value.loc[:, ['x_source', 'y_source']]
        target_control_points = value.loc[:, ['x_target', 'y_target']]
        source_control_points.columns = ['x', 'y']
        target_control_points.columns = ['x', 'y']
        with self._block_write():
            self.source_view_controller.control_points = source_control_points
            self.target_view_controller.control_points = target_control_points

    @property
    def current_matched_control_points_residuals(self) -> Optional[np.ndarray]:
        if self._current_transform is not None:
            matched_control_points = self.current_matched_control_points
            if matched_control_points is not None and not matched_control_points.empty:
                tf = self._transform_class(self._current_transform)
                return tf.residuals(
                    matched_control_points.loc[:, ['x_source', 'y_source']].values,
                    matched_control_points.loc[:, ['x_target', 'y_target']].values
                )
        return None

    @staticmethod
    def _match_alphabetical(
            source_dir_path: Path,
            target_dir_path: Path,
            source_coords_dir_path: Optional[Path],
    ) -> Tuple[List[Path], List[Path], List[Path]]:
        source_file_paths = sorted(iter_files(source_dir_path), key=lambda p: p.stem)
        target_file_paths = sorted(iter_files(target_dir_path), key=lambda p: p.stem)
        if len(target_file_paths) != len(source_file_paths):
            raise NappingException('Number of target images does not match the number of source images')
        source_coords_file_paths = None
        if source_coords_dir_path is not None:
            source_coords_file_paths = sorted(iter_files(source_coords_dir_path, suffix='.csv'), key=lambda p: p.stem)
            if len(source_coords_file_paths) != len(source_file_paths):
                raise NappingException('Number of coordinate files does not match the number of source images')
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

    def _load_pre_post_transforms(self, pre_transform_file_path: Union[str, Path],
                                  post_transform_file_path: Union[str, Path]):
        self._post_transform = None
        if pre_transform_file_path is not None:
            self._pre_transform = np.load(pre_transform_file_path)
        self._post_transform = None
        if post_transform_file_path is not None:
            self._post_transform = np.load(post_transform_file_path)

    def _show(self) -> bool:
        if 0 <= self._current_index < len(self._source_image_file_paths):
            self._source_view_controller.show(self.current_source_image_file_path)
            self._target_view_controller.show(self.current_target_image_file_path)
            if self.current_control_points_dest_file_path.is_file():
                df = pd.read_csv(self.current_control_points_dest_file_path, index_col=0)
                if len(df.index) > 0:
                    self.current_matched_control_points = df
            if self.current_source_coords_file_path is not None and self.current_source_coords_file_path.is_file():
                df = pd.read_csv(self.current_source_coords_file_path)
                if len(df.index) > 0:
                    self._current_source_coords = df
            self._update_current_transform()
            self._update_current_transformed_coords()
            self._source_view_controller.refresh()
            self._target_view_controller.refresh()
            return True
        return False

    def _handle_control_points_changed(self):
        if not self._write_blocked:
            with self.current_control_points_dest_file_path.open(mode='wb', buffering=0) as f:
                self.current_matched_control_points.to_csv(f, mode='wb')

        self._update_current_transform()
        if not self._write_blocked:
            np.save(self.current_joint_transform_dest_file_path, self.current_joint_transform)

        self._update_current_transformed_coords()
        if self._current_transformed_coords is not None and not self._write_blocked:
            with self.current_transformed_coords_dest_file_path.open(mode='wb', buffering=0) as f:
                self._current_transformed_coords.to_csv(f, mode='wb', index=False)

        self.source_view_controller.refresh()
        self.target_view_controller.refresh()

    def _update_current_transform(self):
        self._current_transform = None
        matched_control_points = self.current_matched_control_points
        if matched_control_points.shape[0] >= 3:
            src = matched_control_points.loc[:, ['x_source', 'y_source']].values
            dst = matched_control_points.loc[:, ['x_target', 'y_target']].values
            tf = self._transform_class()
            if tf.estimate(src, dst):
                self._current_transform = tf.params

    def _update_current_transformed_coords(self):
        self._current_transformed_coords = None
        if self._current_source_coords is not None and self.current_joint_transform is not None:
            coords = np.ones((self._current_source_coords.shape[0], 3))
            coords[:, :2] = self._current_source_coords.loc[:, ['X', 'Y']].values
            self._current_transformed_coords = self._current_source_coords.copy()
            self._current_transformed_coords.loc[:, ['X', 'Y']] = (self.current_joint_transform @ coords.T).T[:, :2]

    @contextmanager
    def _block_write(self):
        self._write_blocked = True
        yield
        self._write_blocked = False

    class ViewController:
        _points_layer_args = {
            'properties': {'id': np.arange(1, 1000)},  # see https://github.com/napari/napari/issues/2115
            'text': {'text': 'id', 'anchor': 'upper_left', 'color': 'red', 'translation': (0, 20)},
            'symbol': 'cross',
            'edge_width': 0,
            'face_color': 'red',
            'name': 'Control points',
        }

        def __init__(self, viewer: Viewer, controller: 'Napping'):
            self._viewer = viewer
            self._controller = controller
            self._widget: Optional[NappingWidget] = None
            self._image_path: Optional[Path] = None
            self._points_layer: Optional[Points] = None

        def initialize(self):
            self._widget = NappingWidget(self)
            self._viewer.window.add_dock_widget(self._widget, name='Napping')

        def show(self, path: Path):
            self._close_image()
            self._remove_points_layer()
            self._open_image(path)
            self._add_points_layer()

        def refresh(self):
            self._widget.refresh()

        @property
        def viewer(self) -> Viewer:
            return self._viewer

        @property
        def controller(self) -> 'Napping':
            return self._controller

        @property
        def widget(self) -> Optional[NappingWidget]:
            return self._widget

        @property
        def image_path(self) -> Optional[Path]:
            return self._image_path

        @property
        def points_layer(self) -> Optional[Points]:
            return self._points_layer

        @property
        def control_points(self) -> Optional[pd.DataFrame]:
            if self._points_layer is not None:
                return pd.DataFrame(
                    data=self._points_layer.data[:, ::-1],
                    index=self._points_layer.properties['id'],
                    columns=['x', 'y']
                )
            return None

        @control_points.setter
        def control_points(self, control_points: pd.DataFrame):
            if self._points_layer is None:
                raise RuntimeError('points layer is None')
            self._points_layer.data = control_points.loc[:, ['y', 'x']].values
            properties = self._points_layer.properties
            properties['id'] = control_points.index.values
            self._points_layer.properties = properties
            self._points_layer.refresh()

        def _open_image(self, path: Path):
            self._image_path = path
            if path.suffix.lower() in ['.jfif', '.jpe', '.jpg', '.jpeg']:
                # workaround to set exifrotate=False for JPEG-PIL
                # TODO https://github.com/napari/napari/issues/2278
                from imageio import imread
                img = imread(path, exifrotate=False)
                self._viewer.add_image(data=img, name=path.name)
            else:
                self._viewer.open(str(path), layer_type='image')

        def _close_image(self):
            self._image_path = None
            image_layers = [layer for layer in self._viewer.layers if layer != self._points_layer]
            for image_layer in image_layers:
                self._viewer.layers.remove(image_layer)

        def _add_points_layer(self):
            # noinspection PyUnresolvedReferences
            self._points_layer: Points = self._viewer.add_points(**self._points_layer_args)
            self._points_layer.mode = 'add'

            @self._points_layer.mouse_drag_callbacks.append
            def on_points_layer_mouse_drag(layer, event):
                if layer.mode == 'add':
                    layer.current_properties['id'][0] = max(layer.properties['id'], default=0) + 1
                elif layer.mode == 'select':  # TODO https://github.com/napari/napari/issues/2259
                    yield
                    while event.type == 'mouse_move':
                        yield
                    self._controller._handle_control_points_changed()

            # called when control points are added/deleted (for dragging, see on_points_layer_mouse_drag)
            @self._points_layer.events.data.connect
            def on_points_layer_data_changed(_):
                self._controller._handle_control_points_changed()

            @self._points_layer.events.current_properties.connect
            def on_points_layer_current_properties_changed(_):
                self._points_layer_text_workaround()

        def _remove_points_layer(self):
            if self._points_layer is not None:
                self._viewer.layers.remove(self._points_layer)
                self._points_layer = None

        # see https://github.com/napari/napari/issues/2115
        def _points_layer_text_workaround(self):
            text_args = self._points_layer_args['text']
            if not isinstance(text_args, dict):
                text_args = {'text': text_args}
            n_text = len(self._points_layer.data)
            self._points_layer._text = TextManager(**text_args, n_text=n_text, properties=self._points_layer.properties)
            self._points_layer.refresh_text()


class NappingException(Exception):
    pass
