from contextlib import ExitStack
import time

import tifffile

from .binarize import binarize_phasecontrast_stack
from ..img_op import background_correction as bgcorr
from ..session.status import DummyStatus

def perform_background_correction(chan_fl, chan_bin, outfile, exit_stack=None, status=None):
    if status is None:
        status = DummyStatus()

    with status("Performing background correction …") as s:
        chan_corr_float = bgcorr.background_schwarzfischer(chan_fl, chan_bin, exit_stack=exit_stack)
        chan_corr = bgcorr.corr_gauss(chan_corr_float)
        del chan_corr_float

        n_frames, height, width = chan_corr.shape
        tiff_shape = (n_frames, 1, 1, height, width, 1)
        tifffile.imwrite(outfile, chan_corr.reshape(tiff_shape), shape=tiff_shape, imagej=True)
        del chan_corr

        msg = f"Background correction written to: {outfile}"
        s.set(msg)
        print(msg)
        sleep(2)

