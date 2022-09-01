##File for tracking on lisca

import numpy as np
import sys
import trackpy as tp
from tqdm import tqdm
#from skimage.segmentation import find_boundaries
import pandas as pd


def get_centroids(masks, f_image):

    print('hi')
    nframes = masks.shape[0]
    ids=np.unique(masks)
    ids = ids[ids!=0]
    
    df = pd.DataFrame(columns=['id', 'frame', 'x', 'y', 'fluorescence'])
    for frame in range(nframes):
        for identifier in ids:
            mask = masks[frame]
            count = np.sum(mask==identifier)
            if count==0:
                continue
            points =  np.argwhere(mask==identifier)
            fluorescence = (f_image[frame][points]).sum()
            y = points[:,0].sum()/count
            x = points[:, 1].sum()/count
            
            data = {'id': [identifier],
            'frame':[frame],
            'x':[x], 'y':[y], 'fluorescence': [fluorescence]}

            new_df = pd.DataFrame.from_dict(data)

            df = pd.concat([df, new_df])

    return df

def track(masks, f_image, track_memory=15, max_travel=5, min_frames=10, pixel_to_um=1, verbose=False):

    """
    Parameters

    ----------

    track_memory : TYPE, optional

        Maximum number of time frames where nucleus position is interpolated if it is not detected. The default is 15.

    max_travel : TYPE, optional

        Maximum . The default is 5.

    min_frames : TYPE, optional

        DESCRIPTION. The default is 10.


    Returns

    -------

    t : TYPE

        DESCRIPTION.


    """

    max_travel = np.round(max_travel) #Maximum distance between nuclei in subsequent frames

    if not verbose:

        tp.quiet()

    if verbose:
        print('Getting centroids...')


    f = get_centroids(masks, f_image)
    if verbose:
        print('Tracking')
    t = tp.link(f, max_travel, memory=track_memory)

    t = tp.filter_stubs(t, min_frames)

    if verbose:
        print('Tracking of nuclei completed.')

    return t

