from os import PathLike
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Union

import pandas as pd
from napari.layers import Image, Points
from napari.layers.utils.layer_utils import features_to_pandas_dataframe
from napari.viewer import Viewer


class NappingViewer:
    ControlPointsChangedHandler = Callable[
        ["NappingViewer", Optional[pd.DataFrame]], None
    ]

    def __init__(self, img_file: Union[str, PathLike], **viewer_kwargs) -> None:
        self._control_points_changed_handlers: List[
            NappingViewer.ControlPointsChangedHandler
        ] = []
        self._viewer = Viewer(**viewer_kwargs)
        self._image_layers = self._load_image_layers(Path(img_file))
        self._points_layer = self._create_points_layer()

    def show(self) -> None:
        self._viewer.show()

    def close(self) -> None:
        self._viewer.close()

    def get_control_points(self) -> Optional[pd.DataFrame]:
        if self._points_layer is not None:
            features = features_to_pandas_dataframe(self._points_layer.features)
            return pd.DataFrame(
                data=self._points_layer.data[:, ::-1],
                index=features["id"].to_numpy(),
                columns=["x", "y"],
            )
        return None

    def set_control_points(self, value: pd.DataFrame) -> None:
        if self._points_layer is None:
            raise RuntimeError("points layer is None")
        self._points_layer.data = value.loc[:, ["y", "x"]].to_numpy()
        features = features_to_pandas_dataframe(self._points_layer.features).copy()
        features["id"] = value.index.to_numpy()
        self._points_layer.features = features
        self._points_layer.refresh()

    def _load_image_layers(self, img_file: Path) -> List[Image]:
        if img_file.suffix.lower() in [".jfif", ".jpe", ".jpg", ".jpeg"]:
            # workaround to set exifrotate=False for JPEG-PIL
            # TODO https://github.com/napari/napari/issues/2278
            from imageio import imread

            img = imread(img_file, exifrotate=False)
            return self._viewer.add_image(data=img, name=img_file.name)
        return self._viewer.open(str(img_file), plugin=None, layer_type="image")

    def _create_points_layer(self) -> Points:
        points_layer = self._viewer.add_points(
            features=pd.DataFrame(columns=["id"]),
            text={
                "text": "id",
                "anchor": "upper_left",
                "color": "red",
                "translation": (0, 20),
            },
            symbol="cross",
            edge_width=0,
            face_color="red",
            name="Control points",
        )
        points_layer.mode = "add"
        points_layer.mouse_drag_callbacks.append(self._on_points_layer_mouse_drag)
        points_layer.events.data.connect(self._on_points_layer_data_changed)
        return points_layer

    def _on_points_layer_mouse_drag(self, layer: Points, event) -> None:
        # https://github.com/napari/napari/issues/2259
        if layer.mode == "add":
            layer.current_properties["id"][0] = (
                max(layer.features["id"].tolist(), default=0) + 1
            )
        elif layer.mode == "select":
            yield
            while event.type == "mouse_move":
                yield
            self._handle_control_points_changed()

    def _on_points_layer_data_changed(self, _) -> None:
        # called when control points are added or deleted; for dragging, see
        # layer.mode == "select" block in _on_points_layer_mouse_drag
        self._handle_control_points_changed()

    def _handle_control_points_changed(self) -> None:
        control_points = self.get_control_points()
        for f in self._control_points_changed_handlers:
            f(self, control_points)

    @property
    def viewer(self) -> Viewer:
        return self._viewer

    @property
    def image_layers(self) -> Sequence[Image]:
        return self._image_layers

    @property
    def points_layer(self) -> Points:
        return self._points_layer

    @property
    def control_points_changed_handlers(
        self,
    ) -> List[ControlPointsChangedHandler]:
        return self._control_points_changed_handlers
