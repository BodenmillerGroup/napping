import numpy as np
import pandas as pd
import re

from contextlib import contextmanager
from napari import Viewer
from napari.layers import Points
from napari.layers.utils.text_manager import TextManager
from os import PathLike
from pathlib import Path
from qtpy.QtCore import QSettings
from skimage.transform import (
    AffineTransform,
    EuclideanTransform,
    ProjectiveTransform,
    SimilarityTransform,
)
from typing import Callable, List, Optional, Tuple, Type, Union

from napping._qt import NappingDialog, NappingWidget


class Napping:
    MATCH_ALPHABETICAL = "alphabetical"
    MATCH_FILENAME = "filename"
    MATCH_REGEX = "regex"

    def __init__(self, source_viewer: Viewer, target_viewer: Viewer):
        self._settings = QSettings("Bodenmiller Lab", "napping")
        self._source_controller = Napping.Controller(source_viewer, self)
        self._target_controller = Napping.Controller(target_viewer, self)
        self._source_img_files: Optional[List[Path]] = None
        self._target_img_files: Optional[List[Path]] = None
        self._control_points_files: Optional[List[Path]] = None
        self._joint_transform_files: Optional[List[Path]] = None
        self._transform_type: Optional[Type[ProjectiveTransform]] = None
        self._source_coords_files: Optional[List[Path]] = None
        self._transformed_coords_files: Optional[List[Path]] = None
        self._pre_transform: Optional[np.ndarray] = None
        self._post_transform: Optional[np.ndarray] = None
        self._current_index: Optional[int] = None
        self._current_transform: Optional[np.ndarray] = None
        self._current_source_coords: Optional[pd.DataFrame] = None
        self._current_transformed_coords: Optional[pd.DataFrame] = None
        self._write_blocked = False

    def initialize(self):
        self._source_controller.initialize()
        self._target_controller.initialize()

    def show_dialog(self) -> bool:
        dialog = NappingDialog(self._settings)
        if dialog.exec() == NappingDialog.Accepted:
            transform_type = {
                NappingDialog.TransformType.EUCLIDEAN: EuclideanTransform,
                NappingDialog.TransformType.SIMILARITY: SimilarityTransform,
                NappingDialog.TransformType.AFFINE: AffineTransform,
            }[dialog.transform_type]
            if dialog.selection_mode == NappingDialog.SelectionMode.FILE:
                return self.load_file(
                    dialog.source_img_path,
                    dialog.target_img_path,
                    dialog.control_points_path,
                    dialog.joint_transform_path,
                    transform_type,
                    source_coords_file=dialog.source_coords_path,
                    transformed_coords_file=dialog.transformed_coords_path,
                    pre_transform_file=dialog.pre_transform_path,
                    post_transform_file=dialog.post_transform_path,
                )
            if dialog.selection_mode == NappingDialog.SelectionMode.DIR:
                dialog.control_points_path.mkdir(exist_ok=True)
                dialog.joint_transform_path.mkdir(exist_ok=True)
                if dialog.transformed_coords_path is not None:
                    dialog.transformed_coords_path.mkdir(exist_ok=True)
                matching_strategy = {
                    NappingDialog.MatchingStrategy.ALPHABETICAL: (
                        self.MATCH_ALPHABETICAL
                    ),
                    NappingDialog.MatchingStrategy.FILENAME: (
                        self.MATCH_FILENAME
                    ),
                    NappingDialog.MatchingStrategy.REGEX: self.MATCH_REGEX,
                }[dialog.matching]
                return self.load_dir(
                    matching_strategy,
                    dialog.source_img_path,
                    dialog.target_img_path,
                    dialog.control_points_path,
                    dialog.joint_transform_path,
                    transform_type,
                    source_coords_dir=dialog.source_coords_path,
                    transformed_coords_dir=dialog.transformed_coords_path,
                    pre_transform_file=dialog.pre_transform_path,
                    post_transform_file=dialog.post_transform_path,
                    source_regex=dialog.source_regex,
                    target_regex=dialog.target_regex,
                    source_coords_regex=dialog.source_coords_regex,
                )
        return False

    def load_file(
        self,
        source_img_file: Union[str, PathLike],
        target_img_file: Union[str, PathLike],
        control_points_file: Union[str, PathLike],
        joint_transform_file: Union[str, PathLike],
        transform_type: Type[ProjectiveTransform],
        source_coords_file: Union[str, PathLike, None] = None,
        transformed_coords_file: Union[str, PathLike, None] = None,
        pre_transform_file: Union[str, PathLike, None] = None,
        post_transform_file: Union[str, PathLike, None] = None,
    ) -> bool:
        self._source_img_files = [Path(source_img_file)]
        self._target_img_files = [Path(target_img_file)]
        self._control_points_files = [Path(control_points_file)]
        self._joint_transform_files = [Path(joint_transform_file)]
        self._transform_type = transform_type
        if source_coords_file is not None:
            self._source_coords_files = [Path(source_coords_file)]
        else:
            self._source_coords_files = None
        if transformed_coords_file is not None:
            self._transformed_coords_files = [Path(transformed_coords_file)]
        else:
            self._transformed_coords_files = None
        self._load_pre_post_transforms(pre_transform_file, post_transform_file)
        self._current_index = 0
        return self._show()

    def load_dir(
        self,
        matching_strategy: str,
        source_img_dir: Union[str, PathLike],
        target_img_dir: Union[str, PathLike],
        control_points_dir: Union[str, PathLike],
        joint_transform_dir: Union[str, PathLike],
        transform_type: Type[ProjectiveTransform],
        source_coords_dir: Optional[Union[str, PathLike]] = None,
        transformed_coords_dir: Optional[Union[str, PathLike]] = None,
        pre_transform_file: Union[str, PathLike, None] = None,
        post_transform_file: Union[str, PathLike, None] = None,
        source_regex: Optional[str] = None,
        target_regex: Optional[str] = None,
        source_coords_regex: Optional[str] = None,
    ) -> bool:
        source_img_dir = Path(source_img_dir)
        target_img_dir = Path(target_img_dir)
        control_points_dir = Path(control_points_dir)
        joint_transform_dir = Path(joint_transform_dir)
        if source_coords_dir is not None:
            source_coords_dir = Path(source_coords_dir)
        if transformed_coords_dir is not None:
            transformed_coords_dir = Path(transformed_coords_dir)
        if matching_strategy == self.MATCH_ALPHABETICAL:
            files = self._match_alphabetical(
                source_img_dir, target_img_dir, source_coords_dir
            )
        elif matching_strategy == self.MATCH_FILENAME:
            files = self._match_filename(
                source_img_dir, target_img_dir, source_coords_dir
            )
        elif matching_strategy == self.MATCH_REGEX:
            files = self._match_regex(
                source_img_dir,
                source_regex,
                target_img_dir,
                target_regex,
                source_coords_dir,
                source_coords_regex,
            )
        else:
            raise ValueError(
                f"Unsupported file matching strategy: {matching_strategy}"
            )
        (
            self._source_img_files,
            self._target_img_files,
            self._source_coords_files,
        ) = files
        self._control_points_files = [
            control_points_dir / f"{path.stem}.csv"
            for path in self._target_img_files
        ]
        self._joint_transform_files = [
            joint_transform_dir / f"{path.stem}.npy"
            for path in self._target_img_files
        ]
        self._transform_type = transform_type
        self._transformed_coords_files = None
        if transformed_coords_dir is not None:
            self._transformed_coords_files = [
                transformed_coords_dir / f"{path.stem}.csv"
                for path in self._target_img_files
            ]
        self._load_pre_post_transforms(pre_transform_file, post_transform_file)
        self._current_index = 0
        return self._show()

    def show_previous(self) -> bool:
        self._current_index = self._current_index - 1
        self._current_index %= len(self._source_img_files)
        return self._show()

    def show_next(self) -> bool:
        self._current_index = self._current_index + 1
        self._current_index %= len(self._source_img_files)
        return self._show()

    @property
    def settings(self) -> QSettings:
        return self._settings

    @property
    def source_controller(self) -> "Napping.Controller":
        return self._source_controller

    @property
    def target_controller(self) -> "Napping.Controller":
        return self._target_controller

    @property
    def source_img_files(self) -> Optional[List[Path]]:
        return self._source_img_files

    @property
    def target_img_files(self) -> Optional[List[Path]]:
        return self._target_img_files

    @property
    def control_points_files(self) -> Optional[List[Path]]:
        return self._control_points_files

    @property
    def joint_transform_files(self) -> Optional[List[Path]]:
        return self._joint_transform_files

    @property
    def transform_type(self) -> Optional[Type[ProjectiveTransform]]:
        return self._transform_type

    @property
    def source_coords_files(self) -> Optional[List[Path]]:
        return self._source_coords_files

    @property
    def transformed_coords_files(self) -> Optional[List[Path]]:
        return self._transformed_coords_files

    @property
    def pre_transform(self) -> Optional[np.ndarray]:
        return self._pre_transform

    @property
    def post_transform(self) -> Optional[np.ndarray]:
        return self._post_transform

    @property
    def current_source_img_file(self) -> Optional[Path]:
        if self._current_index is not None:
            return self._source_img_files[self._current_index]
        return None

    @property
    def current_target_img_file(self) -> Optional[Path]:
        if self._current_index is not None:
            return self._target_img_files[self._current_index]
        return None

    @property
    def current_control_points_file(self) -> Optional[Path]:
        if self._current_index is not None:
            return self._control_points_files[self._current_index]
        return None

    @property
    def current_joint_transform_file(self) -> Optional[Path]:
        if self._current_index is not None:
            return self._joint_transform_files[self._current_index]
        return None

    @property
    def current_source_coords_file(self) -> Optional[Path]:
        if (
            self._current_index is not None
            and self._source_coords_files is not None
        ):
            return self._source_coords_files[self._current_index]
        return None

    @property
    def current_transformed_coords_file(self) -> Optional[Path]:
        if (
            self._current_index is not None
            and self._transformed_coords_files is not None
        ):
            return self._transformed_coords_files[self._current_index]
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
        source_control_points = self._source_controller.control_points
        target_control_points = self._target_controller.control_points
        if (
            source_control_points is not None
            and target_control_points is not None
        ):
            return pd.merge(
                source_control_points,
                target_control_points,
                left_index=True,
                right_index=True,
                suffixes=("_source", "_target"),
            )
        return None

    @current_matched_control_points.setter
    def current_matched_control_points(self, value: Optional[pd.DataFrame]):
        source_control_points = value.loc[:, ["x_source", "y_source"]]
        target_control_points = value.loc[:, ["x_target", "y_target"]]
        source_control_points.columns = ["x", "y"]
        target_control_points.columns = ["x", "y"]
        with self._block_write():
            self.source_controller.control_points = source_control_points
            self.target_controller.control_points = target_control_points

    @property
    def current_matched_control_point_residuals(self) -> Optional[np.ndarray]:
        if self._current_transform is not None:
            cp = self.current_matched_control_points
            if cp is not None and not cp.empty:
                tf = self._transform_type(self._current_transform)
                return tf.residuals(
                    cp.loc[:, ["x_source", "y_source"]].values,
                    cp.loc[:, ["x_target", "y_target"]].values,
                )
        return None

    @staticmethod
    def _match_alphabetical(
        source_dir: Path,
        target_dir: Path,
        source_coords_dir: Optional[Path],
    ) -> Tuple[List[Path], List[Path], List[Path]]:
        source_files = sorted(
            (f for f in source_dir.glob("*") if f.is_file()),
            key=lambda f: f.stem,
        )
        target_files = sorted(
            (f for f in target_dir.glob("*") if f.is_file()),
            key=lambda f: f.stem,
        )
        if len(target_files) != len(source_files):
            raise NappingException(
                "Number of target images does not match "
                "the number of source images"
            )
        source_coords_files = None
        if source_coords_dir is not None:
            source_coords_files = sorted(
                (f for f in source_coords_dir.glob("*") if f.is_file()),
                key=lambda f: f.stem,
            )
            if len(source_coords_files) != len(source_files):
                raise NappingException(
                    "Number of coordinate files does not match "
                    "the number of source images"
                )
        return source_files, target_files, source_coords_files

    @classmethod
    def _match_filename(
        cls,
        source_dir: Path,
        target_dir: Path,
        soruce_coords_dir: Optional[Path],
    ) -> Tuple[List[Path], List[Path], List[Path]]:
        def match_target(target_file: Path, source_file: Path):
            return target_file.stem == source_file.stem

        def match_source_coords(source_coords_file: Path, source_file: Path):
            return source_coords_file.stem == source_file.stem

        return cls._match(
            source_dir,
            target_dir,
            match_target,
            soruce_coords_dir,
            match_source_coords,
        )

    @classmethod
    def _match_regex(
        cls,
        source_dir: Path,
        source_regex: str,
        target_dir: Path,
        target_regex: str,
        source_coords_dir: Optional[Path],
        source_coords_regex: Optional[str],
    ) -> Tuple[List[Path], List[Path], List[Path]]:
        source_pattern = re.compile(source_regex)
        target_pattern = re.compile(target_regex)
        source_coords_pattern = re.compile(source_coords_regex)

        def match_target(target_file: Path, source_file: Path):
            target_match = target_pattern.search(target_file.name)
            source_match = source_pattern.search(source_file.name)
            if target_match is not None and source_match is not None:
                return target_match.group() == source_match.group()
            return False

        def match_source_coords(source_coords_file: Path, source_file: Path):
            source_coords_match = source_coords_pattern.search(
                source_coords_file.name
            )
            source_match = source_pattern.search(source_file.name)
            if source_coords_match is not None and source_match is not None:
                return source_coords_match.group() == source_match.group()
            return False

        return cls._match(
            source_dir,
            target_dir,
            match_target,
            source_coords_dir,
            match_source_coords,
        )

    @staticmethod
    def _match(
        source_dir: Path,
        target_dir: Path,
        target_criterion: Callable[[Path, Path], bool],
        source_coords_dir: Optional[Path],
        source_coords_criterion: Optional[Callable[[Path, Path], bool]],
    ) -> Tuple[List[Path], List[Path], List[Path]]:
        source_files = [f for f in source_dir.glob("*") if f.is_file()]
        target_files = [f for f in target_dir.glob("*") if f.is_file()]
        source_coords_files = None
        if source_coords_dir is not None:
            source_coords_files = [
                f
                for f in source_coords_dir.glob("*")
                if f.is_file() and f.suffix.lower() == ".csv"
            ]
        matched_source_files = []
        matched_target_files = []
        matched_source_coords_files = None
        if source_coords_files is not None:
            matched_source_coords_files = []
        for matched_source_file in source_files:
            matched_target_file = next(
                (
                    target_file
                    for target_file in target_files
                    if target_criterion(target_file, matched_source_file)
                ),
                None,
            )
            if matched_target_file is None:
                continue
            matched_source_coords_file = None
            if source_coords_files is not None:
                matched_source_coords_file = next(
                    (
                        source_coords_file
                        for source_coords_file in source_coords_files
                        if source_coords_criterion(
                            source_coords_file, matched_source_file
                        )
                    ),
                    None,
                )
                if matched_source_coords_file is None:
                    continue
            matched_source_files.append(matched_source_file)
            matched_target_files.append(matched_target_file)
            if matched_source_coords_files is not None:
                matched_source_coords_files.append(matched_source_coords_file)
        return (
            matched_source_files,
            matched_target_files,
            matched_source_coords_files,
        )

    def _load_pre_post_transforms(
        self,
        pre_transform_file: Union[str, PathLike],
        post_transform_file: Union[str, PathLike],
    ):
        self._pre_transform = None
        if pre_transform_file is not None:
            self._pre_transform = np.load(pre_transform_file)
        self._post_transform = None
        if post_transform_file is not None:
            self._post_transform = np.load(post_transform_file)

    def _show(self) -> bool:
        if 0 <= self._current_index < len(self._source_img_files):
            self._source_controller.show(self.current_source_img_file)
            self._target_controller.show(self.current_target_img_file)
            if self.current_control_points_file.is_file():
                df = pd.read_csv(self.current_control_points_file, index_col=0)
                if len(df.index) > 0:
                    self.current_matched_control_points = df
            if (
                self.current_source_coords_file is not None
                and self.current_source_coords_file.is_file()
            ):
                df = pd.read_csv(self.current_source_coords_file)
                if len(df.index) > 0:
                    self._current_source_coords = df
            self._update_current_transform()
            self._update_current_transformed_coords()
            self._source_controller.refresh()
            self._target_controller.refresh()
            return True
        return False

    def _handle_control_points_changed(self):
        if not self._write_blocked:
            with self.current_control_points_file.open(
                mode="wb", buffering=0
            ) as f:
                self.current_matched_control_points.to_csv(f, mode="wb")
        self._update_current_transform()
        if not self._write_blocked:
            np.save(
                self.current_joint_transform_file, self.current_joint_transform
            )
        self._update_current_transformed_coords()
        if (
            self._current_transformed_coords is not None
            and not self._write_blocked
        ):
            with self.current_transformed_coords_file.open(
                mode="wb", buffering=0
            ) as f:
                self._current_transformed_coords.to_csv(
                    f, mode="wb", index=False
                )
        self.source_controller.refresh()
        self.target_controller.refresh()

    def _update_current_transform(self):
        self._current_transform = None
        matched_control_points = self.current_matched_control_points
        if matched_control_points.shape[0] >= 3:
            tf = self._transform_type()
            if tf.estimate(
                matched_control_points.loc[:, ["x_source", "y_source"]].values,
                matched_control_points.loc[:, ["x_target", "y_target"]].values,
            ):
                self._current_transform = tf.params

    def _update_current_transformed_coords(self):
        self._current_transformed_coords = None
        if (
            self._current_source_coords is not None
            and self.current_joint_transform is not None
        ):
            coords = np.ones((self._current_source_coords.shape[0], 3))
            coords[:, :2] = self._current_source_coords.loc[
                :, ["X", "Y"]
            ].values
            self._current_transformed_coords = (
                self._current_source_coords.copy()
            )
            self._current_transformed_coords.loc[:, ["X", "Y"]] = (
                self.current_joint_transform @ coords.T
            ).T[:, :2]

    @contextmanager
    def _block_write(self):
        self._write_blocked = True
        yield
        self._write_blocked = False

    class Controller:
        _points_layer_args = {
            # see https://github.com/napari/napari/issues/2115
            "properties": {"id": np.arange(1, 1000)},
            "text": {
                "text": "id",
                "anchor": "upper_left",
                "color": "red",
                "translation": (0, 20),
            },
            "symbol": "cross",
            "edge_width": 0,
            "face_color": "red",
            "name": "Control points",
        }

        def __init__(self, viewer: Viewer, parent: "Napping"):
            self._viewer = viewer
            self._parent = parent
            self._widget: Optional[NappingWidget] = None
            self._img_file: Optional[Path] = None
            self._points_layer: Optional[Points] = None

        def initialize(self):
            self._widget = NappingWidget(self)
            self._viewer.window.add_dock_widget(
                self._widget,
                name="Napping",
                area="bottom",
                allowed_areas=["top", "bottom"],
            )

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
        def parent(self) -> "Napping":
            return self._parent

        @property
        def widget(self) -> Optional[NappingWidget]:
            return self._widget

        @property
        def img_file(self) -> Optional[Path]:
            return self._img_file

        @property
        def points_layer(self) -> Optional[Points]:
            return self._points_layer

        @property
        def control_points(self) -> Optional[pd.DataFrame]:
            if self._points_layer is not None:
                return pd.DataFrame(
                    data=self._points_layer.data[:, ::-1],
                    index=self._points_layer.properties["id"],
                    columns=["x", "y"],
                )
            return None

        @control_points.setter
        def control_points(self, value: pd.DataFrame):
            if self._points_layer is None:
                raise RuntimeError("points layer is None")
            self._points_layer.data = value.loc[:, ["y", "x"]].values
            properties = self._points_layer.properties
            properties["id"] = value.index.values
            self._points_layer.properties = properties
            self._points_layer.refresh()

        def _open_image(self, img_file: Path):
            self._img_file = img_file
            if img_file.suffix.lower() in [".jfif", ".jpe", ".jpg", ".jpeg"]:
                # workaround to set exifrotate=False for JPEG-PIL
                # TODO https://github.com/napari/napari/issues/2278
                from imageio import imread

                img = imread(img_file, exifrotate=False)
                self._viewer.add_image(data=img, name=img_file.name)
            else:
                self._viewer.open(str(img_file), layer_type="image")

        def _close_image(self):
            self._img_file = None
            image_layers = [
                layer
                for layer in self._viewer.layers
                if layer != self._points_layer
            ]
            for image_layer in image_layers:
                self._viewer.layers.remove(image_layer)

        def _add_points_layer(self):
            self._points_layer = self._viewer.add_points(
                **self._points_layer_args
            )
            self._points_layer.mode = "add"

            @self._points_layer.mouse_drag_callbacks.append
            def on_points_layer_mouse_drag(layer, event):
                if layer.mode == "add":
                    layer.current_properties["id"][0] = (
                        max(layer.properties["id"], default=0) + 1
                    )
                # TODO https://github.com/napari/napari/issues/2259
                elif layer.mode == "select":
                    yield
                    while event.type == "mouse_move":
                        yield
                    self._parent._handle_control_points_changed()

            # called when control points are added/deleted
            # (for dragging, see on_points_layer_mouse_drag)
            @self._points_layer.events.data.connect
            def on_points_layer_data_changed(_):
                self._parent._handle_control_points_changed()

            @self._points_layer.events.current_properties.connect
            def on_points_layer_current_properties_changed(_):
                self._points_layer_text_workaround()

        def _remove_points_layer(self):
            if self._points_layer is not None:
                self._viewer.layers.remove(self._points_layer)
                self._points_layer = None

        # see https://github.com/napari/napari/issues/2115
        def _points_layer_text_workaround(self):
            text_args = self._points_layer_args["text"]
            if not isinstance(text_args, dict):
                text_args = {"text": text_args}
            n_text = len(self._points_layer.data)
            self._points_layer._text = TextManager(
                **text_args,
                n_text=n_text,
                properties=self._points_layer.properties,
            )
            self._points_layer.refresh_text()


class NappingException(Exception):
    pass
