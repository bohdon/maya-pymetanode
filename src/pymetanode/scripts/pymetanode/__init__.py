from . import core

try:
    from .pm_api import *
    from .pm_utils import *

    IS_PYMEL_AVAILABLE = True
except ImportError:
    from .api import *
    from .utils import *

    IS_PYMEL_AVAILABLE = False

__version__ = "v2.2.0"
