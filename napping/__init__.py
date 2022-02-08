try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

from ._napping_application import NappingApplication
from ._napping_exception import NappingException
from ._napping_navigator import NappingNavigator


__all__ = ["NappingApplication", "NappingException", "NappingNavigator"]
