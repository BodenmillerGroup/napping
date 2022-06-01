import re
from enum import IntEnum
from os import PathLike
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple, Union

from ._napping_exception import NappingException


class NappingNavigator:
    class MatchingStrategy(IntEnum):
        ALPHABETICAL = 1
        FILENAME = 2
        REGEX = 3

    def __init__(self) -> None:
        self._source_img_files: Optional[List[Path]] = None
        self._target_img_files: Optional[List[Path]] = None
        self._control_points_files: Optional[List[Path]] = None
        self._joint_transform_files: Optional[List[Path]] = None
        self._source_coords_files: Optional[List[Path]] = None
        self._transf_coords_files: Optional[List[Path]] = None
        self._current_index = 0

    def load_file(
        self,
        source_img_file: Union[str, PathLike],
        target_img_file: Union[str, PathLike],
        control_points_file: Union[str, PathLike],
        joint_transform_file: Union[str, PathLike],
        source_coords_file: Union[str, PathLike, None] = None,
        transf_coords_file: Union[str, PathLike, None] = None,
    ) -> None:
        self._source_img_files = [Path(source_img_file)]
        self._target_img_files = [Path(target_img_file)]
        self._control_points_files = [Path(control_points_file)]
        self._joint_transform_files = [Path(joint_transform_file)]
        if source_coords_file is not None:
            self._source_coords_files = [Path(source_coords_file)]
        else:
            self._source_coords_files = None
        if transf_coords_file is not None:
            self._transf_coords_files = [Path(transf_coords_file)]
        else:
            self._transf_coords_files = None
        self._matching_strategy = None
        self._current_index = 0

    def load_dir(
        self,
        source_img_dir: Union[str, PathLike],
        target_img_dir: Union[str, PathLike],
        control_points_dir: Union[str, PathLike],
        joint_transform_dir: Union[str, PathLike],
        matching_strategy: "NappingNavigator.MatchingStrategy",
        source_regex: Optional[str] = None,
        target_regex: Optional[str] = None,
        source_coords_regex: Optional[str] = None,
        source_coords_dir: Optional[Union[str, PathLike]] = None,
        transf_coords_dir: Optional[Union[str, PathLike]] = None,
    ) -> None:
        source_img_dir = Path(source_img_dir)
        target_img_dir = Path(target_img_dir)
        control_points_dir = Path(control_points_dir)
        joint_transform_dir = Path(joint_transform_dir)
        if source_coords_dir is not None:
            source_coords_dir = Path(source_coords_dir)
        if matching_strategy == NappingNavigator.MatchingStrategy.ALPHABETICAL:
            (
                self._source_img_files,
                self._target_img_files,
                self._source_coords_files,
            ) = self._match_alphabetical(
                source_img_dir, target_img_dir, source_coords_dir
            )
        elif matching_strategy == NappingNavigator.MatchingStrategy.FILENAME:
            (
                self._source_img_files,
                self._target_img_files,
                self._source_coords_files,
            ) = self._match_filename(source_img_dir, target_img_dir, source_coords_dir)
        elif matching_strategy == NappingNavigator.MatchingStrategy.REGEX:
            (
                self._source_img_files,
                self._target_img_files,
                self._source_coords_files,
            ) = self._match_regex(
                source_img_dir,
                source_regex,
                target_img_dir,
                target_regex,
                source_coords_dir,
                source_coords_regex,
            )
        else:
            raise ValueError(f"Unsupported file matching strategy: {matching_strategy}")
        self._control_points_files = [
            control_points_dir / f"{target_img_file.stem}.csv"
            for target_img_file in self._target_img_files
        ]
        self._joint_transform_files = [
            joint_transform_dir / f"{target_img_file.stem}.npy"
            for target_img_file in self._target_img_files
        ]
        if transf_coords_dir is not None:
            self._transf_coords_files = [
                Path(transf_coords_dir) / f"{target_img_file.stem}.csv"
                for target_img_file in self._target_img_files
            ]
        else:
            self._transf_coords_files = None
        self._current_index = 0

    def prev(self) -> None:
        self._current_index = (self._current_index - 1) % len(self)

    def next(self) -> None:
        self._current_index = (self._current_index + 1) % len(self)

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
                "Number of target images does not match " "the number of source images"
            )
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
        else:
            source_coords_files = None
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
            source_coords_match = source_coords_pattern.search(source_coords_file.name)
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
        if source_coords_dir is not None:
            source_coords_files = [
                f
                for f in source_coords_dir.glob("*")
                if f.is_file() and f.suffix.lower() == ".csv"
            ]
        else:
            source_coords_files = None
        matched_source_files = []
        matched_target_files = []
        if source_coords_files is not None:
            matched_source_coords_files = []
        else:
            matched_source_coords_files = None
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
            else:
                matched_source_coords_file = None
            matched_source_files.append(matched_source_file)
            matched_target_files.append(matched_target_file)
            if matched_source_coords_file is not None:
                matched_source_coords_files.append(matched_source_coords_file)
        return (
            matched_source_files,
            matched_target_files,
            matched_source_coords_files,
        )

    def __len__(self) -> int:
        if self._source_img_files is None:
            return 0
        return len(self._source_img_files)

    @property
    def source_img_files(self) -> Optional[Sequence[Path]]:
        return self._source_img_files

    @property
    def target_img_files(self) -> Optional[Sequence[Path]]:
        return self._target_img_files

    @property
    def control_points_files(self) -> Optional[Sequence[Path]]:
        return self._control_points_files

    @property
    def joint_transform_files(self) -> Optional[Sequence[Path]]:
        return self._joint_transform_files

    @property
    def source_coords_files(self) -> Optional[Sequence[Path]]:
        return self._source_coords_files

    @property
    def transf_coords_files(self) -> Optional[Sequence[Path]]:
        return self._transf_coords_files

    @property
    def current_index(self) -> int:
        return self._current_index

    @current_index.setter
    def current_index(self, current_index: int) -> None:
        self._current_index = current_index

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
        if self._current_index is not None and self._source_coords_files is not None:
            return self._source_coords_files[self._current_index]
        return None

    @property
    def current_transf_coords_file(self) -> Optional[Path]:
        if self._current_index is not None and self._transf_coords_files is not None:
            return self._transf_coords_files[self._current_index]
        return None
