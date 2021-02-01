from pathlib import Path
from typing import Optional, Union


def iter_files(path: Union[str, Path], include_hidden: bool = False, suffix: Optional[str] = None):
    path = Path(path)
    it = filter(lambda p: p.is_file(), path.iterdir())
    if not include_hidden:
        it = filter(lambda p: not p.name.startswith('.'), it)
    if suffix is not None:
        it = filter(lambda p: p.suffix.lower() == suffix.lower(), it)
    return it
