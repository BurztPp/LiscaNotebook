# Provides a background correction based on Schwarzfischer et al.:
# Efficient fluorescence image normalization for time lapse movies
# https://push-zb.helmholtz-muenchen.de/frontdoor.php?source_opus=6773
#
# Based on "background_correction.py"
# of commit f46236d89b18ec8833e54bbdfe748f3e5bce6924
# in repository https://gitlab.physik.uni-muenchen.de/lsr-pyama/schwarzfischer
from contextlib import ExitStack

import numpy as np
import numpy.ma as ma
import scipy.interpolate as scint
import scipy.stats as scst

from ..util_tmpdir import mktmpf


def _make_tiles(n, div, name='center'):
    borders = np.rint(np.linspace(0, n, 2*div-1)).astype(np.uint16)
    tiles = np.empty(len(borders)-2, dtype=[(name, np.float), ('slice', object)])
    for i, (b1, b2) in enumerate(zip(borders[:-2], borders[2:])):
        tiles[i] = (b1 + b2) / 2, slice(b1, b2)
    return tiles

def background_schwarzfischer(fluor_chan, bin_chan, div_horiz=7, div_vert=5, exit_stack=None, memmap=None):
    """Perform background correction according to Schwarzfischer et al.

    Arguments:
        fluor_chan -- (frames x height x width) numpy array; the fluorescence channel to be corrected
        bin_chan -- boolean numpy array of same shape as `fluor_chan`; segmentation map (background=False, cell=True)
        div_horiz -- int; number of (non-overlapping) tiles in horizontal direction
        div_vert -- int; number of (non-overlapping) tiles in vertical direction
        exit_stack -- ExitStack instance to be closed at function end (e.g. for closing temporary files)
        mmemmap -- boolean flag whether to store large arrays as memmap (None defaults to True)

    Returns:
        Background-corrected fluorescence channel as numpy array (dtype single) of same shape as `fluor_chan`
    """
    with ExitStack() as stack:
        if exit_stack is not None:
            stack.enter_context(exit_stack)

        n_frames, height, width = fluor_chan.shape
        if memmap is None:
            memmap = True

        # Construct tiles for background interpolation
        # Each pair of neighboring tiles is overlapped by a third tile, resulting in a total tile number
        # of `2 * div_i - 1` tiles for each direction `i` in {`horiz`, `vert`}.
        # Due to integer rounding, the sizes may slightly vary between tiles.
        tiles_vert = _make_tiles(height, div_vert)
        tiles_horiz = _make_tiles(height, div_horiz)

        # Interplolate background as cubic spline with each tile’s median as support point at the tile center
        supp = np.empty((tiles_horiz.size, tiles_vert.size))
        if memmap:
            tf_interp = stack.enter_context(mktmpf())
            bg_interp = np.memmap(tf_interp, mode='w+', shape=bin_chan.shape, dtype=np.single)
        else:
            bg_interp = np.empty_like(bin_chan, dtype=np.single)
        for t in range(fluor_chan.shape[0]):
            print(f"Interpolate background in frame {t:3d} …")
            masked_frame = ma.masked_array(fluor_chan[t, ...], mask=bin_chan[t, ...])
            for iy, (y, sy) in enumerate(tiles_vert):
                for ix, (x, sx) in enumerate(tiles_horiz):
                    supp[ix, iy] = ma.median(masked_frame[sy, sx])
            bg_spline = scint.RectBivariateSpline(x=tiles_horiz['center'], y=tiles_vert['center'], z=supp)
            bg_interp[t, ...] = bg_spline(x=range(width), y=range(height)).T

        # Calculated background using Schwarzfischer’s formula
        print("Calculating mean background …") #DEBUG
        bg_mean = np.mean(bg_interp, axis=(1,2)).reshape((-1, 1, 1))
        print("Calculating gain …") #DEBUG
        if memmap:
            tf_gain = stack.enter_context(mktmpf())
            gain = np.memmap(tf_gain, mode='w+', shape=bg_interp.shape[1:], dtype=bg_interp.dtype)
        else:
            gain = np.empty(shape=bg_interp.shape[1:], dtype=bg_interp.dtype)
        np.median(bg_interp / bg_mean, axis=0, out=gain)
        print("Calculating correction …") #DEBUG
        if memmap:
            stack_corr = np.memmap(mktmpf(), mode='w+', shape=fluor_chan.shape, dtype=np.single)
        else:
            stack_corr = np.empty_like(fluor_chan, dtype=np.single)
        stack_corr[...] = (fluor_chan - bg_interp) / gain
        print("Returning from background correction …") #DEBUG
        return stack_corr

def corr_gauss(img, n_sigma=4, memmap=True):
    """Eliminate normal noise around 0 in background-corrected image
    
    Arguments:
        img -- 2-dim float numpy array; the image to be de-noised
        n_sigma -- float; interval up to which values should be reduced
        memmap -- boolean flag whether to use memmap
        
    Returns
        2-dim uint16 numpy array with de-noised image
    """
    print("corr_gauss") #DEBUG
    print("Calculating sigma …") #DEBUG
    sigma = np.sqrt(np.sum(img[img < 0]**2) / np.sum(img < 0))
    sigma_dist = n_sigma * sigma

    print("Calculating img_corr …") #DEBUG
    if memmap:
        img_corr = np.memmap(mktmpf(), mode='w+', shape=img.shape, dtype=np.uint16)
    else:
        img_corr = np.zeros_like(img, dtype=np.uint16)
    img_corr[img >= sigma_dist] = np.rint(img[img >= sigma_dist])

    print("Distribution correction …") #DEBUG
    if memmap:
        idx_dist = np.memmap(mktmpf(), mode='w+', shape=img.shape, dtype=np.bool_)
    else:
        idx_dist = np.empty(shape=img.shape, dtype=np.bool_)
    np.logical_and(img > 0, img < sigma_dist, out=idx_dist)
    vals_dist = img[idx_dist]
    print("Calculate bell") #DEBUG
    bell = scst.norm.pdf(vals_dist, 0, sigma) / scst.norm.pdf(0, 0, sigma)
    print("Populate img_corr") #DEBUG
    img_corr[idx_dist] = np.rint(vals_dist * (1 - bell))
    
    print("Returning from corr_gauss …") #DEBUG
    return img_corr
    
