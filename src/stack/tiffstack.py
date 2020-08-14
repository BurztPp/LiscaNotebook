from collections import OrderedDict

import tifffile

from .base import BaseStack
from . import const

class TiffStack(BaseStack):
    def __init__(self, path, caching=True):
        super().__init__()

        self._path = path
        self._tiff = tifffile.TiffFile(path)
        self._n_images = len(self._tiff.pages)
        if not self._n_images:
            return

        if self._tiff.imagej_metadata:
            self._get_imagej_metadata()
        elif self._tiff.ome_metadata:
            self._get_ome_metadata()
        else:
            self._get_default_shape()

        if caching:
            #TODO caching
            print("TiffStack.__init__: Caching not implemented yet")


    def close(self):
        super().close()
        with self.lock:
            self.__del_tiff()


    def __del_tiff(self):
        if self._tiff is not None:
            self._tiff.close()
            self._tiff = None


    def __del__(self):
        self.__del_tiff()


    def _load_into_cache(self):
        #TODO
        pass


    def get_image(self, **kwargs):
        i = self.get_linear_index(**kwargs)
        return self._tiff.pages[i].asarray()


    def _get_default_shape(self):
        raise NotImplementedError


    def _get_imagej_metadata(self):
        dim_order = 'TZCYXS' # default ImageJ order
        meta = {}

        # Read information from file-wide metadata catalogue
        for k, v in self._tiff.imagej_metadata.items():
            if k == 'images' and v != self._n_images:
                raise ValueError(f"TIFF metadata are inconsistent: {v} images specified, but found {self._n_images}")
            elif k == 'channels':
                meta[const.C] = v
            elif k == 'slices':
                meta[const.Z] = v
            elif k == 'frames':
                meta[const.T] = v
            elif k == 'min':
                self._min_val = v
            elif k == 'max':
                self._max_val = v

        # Read information from page-specific metadata catalogue
        # (assume same specification for all pages)
        p = self._tiff.pages[0]
        self._dtype = p._dtype
        meta[const.Y] = p.imagelength
        meta[const.X] = p.imagewidth
        if p.samplesperpixel > 1 or p.ndim > 2:
            meta[const.S] = p.samplesperpixel

        # Set shape
        self._shape = OrderedDict()
        for k in dim_order:
            v = meta.get(k)
            if v is not None:
                self._shape[k] = v


    def _get_ome_metadata(self):
        raise NotImplementedError
