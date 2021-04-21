from .stack import Stack #deprecated
from .metastack import MetaStack #deprecated

# New stack API
from .base import BaseStack
from .tiffstack import TiffStack
from .numpystack import NumpyStack #TODO
from .ilastikstack import IlastikStack #TODO
from .virtualstack import VirtualStack #TODO

from . import const

import os


stack_formats = {
        const.ST_FMT_BASE: BaseStack,
        const.ST_FMT_TIFF: TiffStack,
        const.ST_FMT_NUMPY: NumpyStack,
        const.ST_FMT_ILASTIK: IlastikStack,
        const.ST_FMT_VIRTUAL: VirtualStack,
        }

def open_stack(path, stack_format=None, **kwargs):
    if stack_format is None:
        if isinstance(path, os.PathLike):
            path = path.__fspath__()
        ext = os.path.splitext(path)[-1].lower()
        if ext in ('.tif', '.tiff'):
            stack_format = const.ST_FMT_TIFF
        elif ext in ('.npy', '.npz'):
            stack_format = const.ST_FMT_NUMPY
        elif ext in ('.hdf5', '.h5'):
            stack_format = const.ST_FMT_ILASTIK
        else:
            raise ValueError(f"Unknown file extension: '{ext}'")

    return stack_formats[stack_format](path, **kwargs)

