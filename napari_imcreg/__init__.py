try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

from napari_imcreg.imcreg_controller import IMCRegController, IMCRegControllerException

__all__ = [
    'IMCRegController',
    'IMCRegControllerException',
]