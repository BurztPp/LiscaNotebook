from .stack import Stack #deprecated
from .metastack import MetaStack #deprecated

# New stack API
from .base import BaseStack
from .tiffstack import TiffStack
#from .numpystack import NumpyStack #TODO
#from .ilastikstack import IlastikStack #TODO
#from .virtualstack import VirtualStack #TODO

from . import const


import os

def open_stack(path, **kwargs):
    if isinstance(path, os.PathLike):
        path = path.__fspath__()
    ext = os.path.splitext[-1].lower()
    if ext in ('.tif', '.tiff'):
        return TiffStack(path, **kwargs)
    elif ext in ('.npy', '.npz'):
        raise NotImplementedError #TODO
        #return NumpyStack(path, **kwargs)
    elif ext in ('.hdf5', '.h5'):
        raise NotImplementedError #TODO
        #return IlastikStack(path, **kwargs)
    else:
        raise ValueError(f"Unknown file extension: '{ext}'")

