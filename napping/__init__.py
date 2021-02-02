try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

from napping.napping import Napping, NappingException

__all__ = [
    'Napping',
    'NappingException',
]
