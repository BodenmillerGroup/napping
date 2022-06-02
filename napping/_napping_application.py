from contextlib import contextmanager
from os import PathLike
from typing import Optional, Type, Union

import numpy as np
import pandas as pd
from qtpy.QtWidgets import QApplication
from skimage.transform import (
    AffineTransform,
    EuclideanTransform,
    ProjectiveTransform,
    SimilarityTransform,
)

from ._napping_navigator import NappingNavigator
from .qt import NappingDialog, NappingViewer, NappingWidget


class NappingApplication:
    RESTART_RETURN_CODE = 1000

    def __init__(self) -> None:
        self._navigator = NappingNavigator()
        self._current_app: Optional[QApplication] = None
        self._current_widget: Optional[NappingWidget] = None
        self._current_source_viewer: Optional[NappingViewer] = None
        self._current_target_viewer: Optional[NappingViewer] = None
        self._transform_type: Optional[Type[ProjectiveTransform]] = None
        self._pre_transform: Optional[np.ndarray] = None
        self._post_transform: Optional[np.ndarray] = None
        self._current_transform: Optional[np.ndarray] = None
        self._current_source_coords: Optional[pd.DataFrame] = None
        self._current_transf_coords: Optional[pd.DataFrame] = None
        self._write_blocked = False

    def exec(self, app: Optional[QApplication] = None) -> None:
        return_code = NappingApplication.RESTART_RETURN_CODE
        while return_code == NappingApplication.RESTART_RETURN_CODE:
            self._current_app = app or QApplication([])
            self._current_source_viewer = self._create_source_viewer(
                self._navigator.current_source_img_file
            )
            self._current_target_viewer = self._create_target_viewer(
                self._navigator.current_target_img_file
            )
            self._current_widget = self._create_widget()
            if self._navigator.current_control_points_file.is_file():
                current_control_points = pd.read_csv(
                    self._navigator.current_control_points_file,
                    index_col=0,
                )
                if len(current_control_points.index) > 0:
                    self.set_current_control_points(current_control_points)
            if (
                self._navigator.current_source_coords_file is not None
                and self._navigator.current_source_coords_file.is_file()
            ):
                current_source_coords = pd.read_csv(
                    self._navigator.current_source_coords_file
                )
                if len(current_source_coords.index) > 0:
                    self._current_source_coords = current_source_coords
            self._update_current_transform()
            self._update_current_transf_coords()
            self._current_source_viewer.control_points_changed_handlers.append(
                self._handle_control_points_changed
            )
            self._current_target_viewer.control_points_changed_handlers.append(
                self._handle_control_points_changed
            )
            self._current_source_viewer.show()
            self._current_target_viewer.show()
            self._current_widget.show()
            self._current_widget.refresh()
            return_code = self._current_app.exec()

    def exec_dialog(self, app: Optional[QApplication] = None) -> None:
        if app is None:
            app = QApplication([])
        dialog = self._create_dialog()
        if dialog.exec() == NappingDialog.DialogCode.Accepted:
            self._transform_type = {
                NappingDialog.TransformType.EUCLIDEAN: EuclideanTransform,
                NappingDialog.TransformType.SIMILARITY: SimilarityTransform,
                NappingDialog.TransformType.AFFINE: AffineTransform,
            }[dialog.transform_type]
            if dialog.pre_transform_path is not None:
                self._pre_transform = np.load(dialog.pre_transform_path)
            else:
                self._pre_transform = None
            if dialog.post_transform_path is not None:
                self._post_transform = np.load(dialog.post_transform_path)
            else:
                self._post_transform = None
            if dialog.selection_mode == NappingDialog.SelectionMode.FILE:
                self._navigator.load_file(
                    dialog.source_img_path,
                    dialog.target_img_path,
                    dialog.control_points_path,
                    dialog.joint_transform_path,
                    source_coords_file=dialog.source_coords_path,
                    transf_coords_file=dialog.transf_coords_path,
                )
            elif dialog.selection_mode == NappingDialog.SelectionMode.DIR:
                dialog.control_points_path.mkdir(exist_ok=True)
                dialog.joint_transform_path.mkdir(exist_ok=True)
                if dialog.transf_coords_path is not None:
                    dialog.transf_coords_path.mkdir(exist_ok=True)
                self._navigator.load_dir(
                    dialog.source_img_path,
                    dialog.target_img_path,
                    dialog.control_points_path,
                    dialog.joint_transform_path,
                    {
                        NappingDialog.MatchingStrategy.ALPHABETICAL: (
                            NappingNavigator.MatchingStrategy.ALPHABETICAL
                        ),
                        NappingDialog.MatchingStrategy.FILENAME: (
                            NappingNavigator.MatchingStrategy.FILENAME
                        ),
                        NappingDialog.MatchingStrategy.REGEX: (
                            NappingNavigator.MatchingStrategy.REGEX
                        ),
                    }[dialog.matching_strategy],
                    source_regex=dialog.source_regex,
                    target_regex=dialog.target_regex,
                    source_coords_regex=dialog.source_coords_regex,
                    source_coords_dir=dialog.source_coords_path,
                    transf_coords_dir=dialog.transf_coords_path,
                )
            else:
                raise RuntimeError("Unexpected dialog selection mode")
            self.exec(app=app)

    def restart(self) -> None:
        self._current_source_viewer.close()
        self._current_target_viewer.close()
        self._current_widget.close()
        self._current_app.exit(returnCode=NappingApplication.RESTART_RETURN_CODE)
        self._current_app = None
        self._current_widget = None
        self._current_source_viewer = None
        self._current_target_viewer = None

    def get_current_joint_transform(self) -> Optional[np.ndarray]:
        if self._current_transform is not None:
            current_joint_transform = self._current_transform
            if self._pre_transform is not None:
                current_joint_transform = current_joint_transform @ self._pre_transform
            if self._post_transform is not None:
                current_joint_transform = self._post_transform @ current_joint_transform
            return current_joint_transform
        return None

    def get_current_control_points(self) -> Optional[pd.DataFrame]:
        if (
            self._current_source_viewer is not None
            and self._current_target_viewer is not None
        ):
            current_source_control_points = (
                self._current_source_viewer.get_control_points()
            )
            current_target_control_points = (
                self._current_target_viewer.get_control_points()
            )
            if (
                current_source_control_points is not None
                and current_target_control_points is not None
            ):
                return pd.merge(
                    current_source_control_points,
                    current_target_control_points,
                    left_index=True,
                    right_index=True,
                    suffixes=("_source", "_target"),
                )
        return None

    def set_current_control_points(
        self, current_control_points: Optional[pd.DataFrame]
    ) -> None:
        with self._block_write():
            if current_control_points is not None:
                current_source_control_points = current_control_points.loc[
                    :, ["x_source", "y_source"]
                ].copy()
                current_target_control_points = current_control_points.loc[
                    :, ["x_target", "y_target"]
                ].copy()
                current_source_control_points.columns = ["x", "y"]
                current_target_control_points.columns = ["x", "y"]
                self._current_source_viewer.set_control_points(
                    current_source_control_points
                )
                self._current_target_viewer.set_control_points(
                    current_target_control_points
                )
            else:
                self.current_source_viewer.set_control_points(None)
                self.current_target_viewer.set_control_points(None)

    def get_current_control_point_residuals(
        self,
    ) -> Optional[np.ndarray]:
        if self._current_transform is not None:
            current_control_points = self.get_current_control_points()
            if current_control_points is not None and not current_control_points.empty:
                tf = self._transform_type(self._current_transform)
                return tf.residuals(
                    current_control_points.loc[:, ["x_source", "y_source"]].to_numpy(),
                    current_control_points.loc[:, ["x_target", "y_target"]].to_numpy(),
                )
        return None

    def _create_dialog(self) -> NappingDialog:
        return NappingDialog()

    def _create_source_viewer(self, img_file: Union[str, PathLike]) -> NappingViewer:
        return NappingViewer(img_file)

    def _create_target_viewer(self, img_file: Union[str, PathLike]) -> NappingViewer:
        return NappingViewer(img_file)

    def _create_widget(self) -> NappingWidget:
        return NappingWidget(self)

    def _handle_control_points_changed(
        self, viewer: NappingViewer, control_points: Optional[pd.DataFrame]
    ) -> None:
        current_control_points = self.get_current_control_points()
        if not self._write_blocked and current_control_points is not None:
            with self._navigator.current_control_points_file.open(
                mode="wb", buffering=0
            ) as f:
                current_control_points.to_csv(f, mode="wb")
        self._update_current_transform()
        current_joint_transform = self.get_current_joint_transform()
        if not self._write_blocked and current_joint_transform is not None:
            np.save(
                self._navigator.current_joint_transform_file,
                current_joint_transform,
            )
        self._update_current_transf_coords()
        if not self._write_blocked and self._current_transf_coords is not None:
            with self._navigator.current_transf_coords_file.open(
                mode="wb", buffering=0
            ) as f:
                self._current_transf_coords.to_csv(f, mode="wb", index=False)
        self._current_widget.refresh()

    def _update_current_transform(self) -> None:
        self._current_transform = None
        current_control_points = self.get_current_control_points()
        if current_control_points.shape[0] >= 3:
            tf = self._transform_type()
            if tf.estimate(
                current_control_points.loc[:, ["x_source", "y_source"]].to_numpy(),
                current_control_points.loc[:, ["x_target", "y_target"]].to_numpy(),
            ):
                self._current_transform = tf.params

    def _update_current_transf_coords(self) -> None:
        self._current_transf_coords = None
        current_joint_transform = self.get_current_joint_transform()
        if (
            self._current_source_coords is not None
            and current_joint_transform is not None
        ):
            x = np.ones((self._current_source_coords.shape[0], 3))
            x[:, :2] = self._current_source_coords.loc[:, ["X", "Y"]].to_numpy()
            self._current_transf_coords = self._current_source_coords.copy()
            self._current_transf_coords.loc[:, ["X", "Y"]] = (
                current_joint_transform @ x.T
            ).T[:, :2]

    @contextmanager
    def _block_write(self) -> None:
        self._write_blocked = True
        yield
        self._write_blocked = False

    @property
    def navigator(self) -> NappingNavigator:
        return self._navigator

    @property
    def current_app(self) -> Optional[QApplication]:
        return self._current_app

    @property
    def current_widget(self) -> Optional[NappingWidget]:
        return self._current_widget

    @property
    def current_source_viewer(self) -> Optional[NappingViewer]:
        return self._current_source_viewer

    @property
    def current_target_viewer(self) -> Optional[NappingViewer]:
        return self._current_target_viewer

    @property
    def transform_type(self) -> Optional[Type[ProjectiveTransform]]:
        return self._transform_type

    @transform_type.setter
    def transform_type(
        self, transform_type: Optional[Type[ProjectiveTransform]]
    ) -> None:
        self._transform_type = transform_type

    @property
    def pre_transform(self) -> Optional[np.ndarray]:
        return self._pre_transform

    @pre_transform.setter
    def pre_transform(self, pre_transform: Optional[np.ndarray]) -> None:
        self._pre_transform = pre_transform

    @property
    def post_transform(self) -> Optional[np.ndarray]:
        return self._post_transform

    @post_transform.setter
    def post_transform(self, post_transform: Optional[np.ndarray]) -> None:
        self._post_transform = post_transform

    @property
    def current_transform(self) -> Optional[np.ndarray]:
        return self._current_transform

    @property
    def current_source_coords(self) -> Optional[pd.DataFrame]:
        return self._current_source_coords

    @property
    def current_transf_coords(self) -> Optional[pd.DataFrame]:
        return self._current_transf_coords
