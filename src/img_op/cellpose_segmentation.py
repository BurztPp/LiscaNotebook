import scipy.ndimage as smg
import numpy as np
import numba as nb
import os
import json
from urllib import request

STRUCT3 = np.ones((3,3), dtype=np.bool_)
STRUCT5 = np.ones((5,5), dtype=np.bool_)
STRUCT5[[0,0,-1,-1], [0,-1,0,-1]] = False

@nb.njit
def window_std(img):
    """Calculate unnormed variance of 'img'"""
    return np.sum((img - np.mean(img))**2)


@nb.njit
def generic_filter(img, fun, size=3, reflect=False):
    """Apply filter to image.

    img -- the image to be filtered
    fun -- the filter function to be applied, must accept subimage of 'img' as only argument and return a scalar
    size -- the size (side length) of the mask; must be an odd integer
    reflect -- switch for border mode: True for 'reflect', False for 'mirror'

    Returns a np.float64 array with same shape as 'img'.

    This function is intended to be a numba-capable replacement of scipy.ndimage.generic_filter.
    """
    if size % 2 != 1:
        raise ValueError("'size' must be an odd integer")
    height, width = img.shape
    s2 = size // 2

    # Set up temporary image for correct border handling
    img_temp = np.empty((height+2*s2, width+2*s2), dtype=np.float64)
    img_temp[s2:-s2, s2:-s2] = img
    if reflect:
        img_temp[:s2, s2:-s2] = img[s2-1::-1, :]
        img_temp[-s2:, s2:-s2] = img[:-s2-1:-1, :]
        img_temp[:, :s2] = img_temp[:, 2*s2-1:s2-1:-1]
        img_temp[:, -s2:] = img_temp[:, -s2-1:-2*s2-1:-1]
    else:
        img_temp[:s2, s2:-s2] = img[s2:0:-1, :]
        img_temp[-s2:, s2:-s2] = img[-2:-s2-2:-1, :]
        img_temp[:, :s2] = img_temp[:, 2*s2:s2:-1]
        img_temp[:, -s2:] = img_temp[:, -s2-2:-2*s2-2:-1]

    # Create and populate result image
    filtered_img = np.empty_like(img, dtype=np.float64)
    for y in range(height):
        for x in range(width):
            filtered_img[y, x] = fun(img_temp[y:y+2*s2+1, x:x+2*s2+1])

    return filtered_img


def binarize_frame_cellpose(img, mask_size=3):
    """Coarse segmentation of phase-contrast image frame

    Returns binarized image of frame
    """
    from cellpose import models
    from cellpose.io import logger_setup
    from skimage.morphology import binary_erosion
    
    flow_threshold=0.8
    mask_threshold=0
    pretrained_model=None
    nucleus_bottom_percentile=0.05
    nucleus_top_percentile=99.95
    cyto_bottom_percentile=0.1
    cyto_top_percentile=99.9
    check_preprocessing=False
    diameter=35

    pretrained_model='mdamb231'
    pretrained_model=None
    gpu=True

    if pretrained_model is None:
        model = models.Cellpose(gpu=gpu, model_type='cyto')
    
    else:
        path_to_models = os.path.join(os.path.dirname(__file__), 'cellpose_models')
        with open(os.path.join(path_to_models, 'models.json'), 'r') as f:
            dic = json.load(f)
            
        if pretrained_model in dic.keys():
            path_to_model = os.path.join(path_to_models, dic[pretrained_model]['path'])
            if os.path.isfile(path_to_model):
                pretrained_model = path_to_model
            else: 
                url = dic[pretrained_model]['link']
                print('Downloading model from Nextcloud...')
                request.urlretrieve(url, path_to_model)
                pretrained_model = path_to_model

        model = models.CellposeModel(gpu=gpu, pretrained_model=pretrained_model)
    
    # images = np.stack((cytoplasm, nucleus), axis=-1)

    mask = model.eval(img, diameter=diameter, channels=[0,0], flow_threshold=flow_threshold)[0].astype('uint8')
    
    img_bin = np.zeros(mask.shape, dtype='bool')
    cell_ids = np.unique(mask)
    cell_ids = cell_ids[cell_ids!=0]
    for cell_id in cell_ids:
        img_bin+=binary_erosion(mask==cell_id)

    return img_bin
