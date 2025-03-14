"""A key-frame focused animation engine."""

# Taichi makes it an absolute nightmare to squelch startup noise.
import os

os.environ["ENABLE_TAICHI_HEADER_PRINT"] = "False"
from taichi._logging import ERROR, set_logging_level  # noqa: E402

set_logging_level(ERROR)
del set_logging_level, os

from . import easing  # noqa
from . import highlight  # noqa
from . import transforms  # noqa
from .animation import *  # noqa
from .annotations import *  # noqa
from .base import *  # noqa
from .text import *  # noqa
from .constants import *  # noqa
from .color import *  # noqa
from .compositor import *  # noqa
from .curve import *  # noqa
from .effects import *  # noqa
from .highlight import *  # noqa
from .line import *  # noqa
from .geometry import *  # noqa
from .plot import *  # noqa
from .scene import *  # noqa
from .group import *  # noqa
from .shapes import *  # noqa

# This must go last
from .extras import *  # noqa
