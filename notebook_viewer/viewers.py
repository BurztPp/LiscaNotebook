"""Jupyter notebook viewer stacks viewer"""

import ipywidgets as widgets
import matplotlib.pyplot as plt
from lisca.segmentation import Segmentation
import numpy as np
from nd2reader import ND2Reader
from IPython.display import display
import os
from skimage.morphology import binary_erosion
from skimage.segmentation import find_boundaries

class StackViewer:
    
    def __init__(self, nd2file, manual=False):
        
               
        self.f = ND2Reader(nd2file)
        self.image = self.f.get_frame_2D()
        self.dtype= self.image.dtype
        self.h, self.w = self.image.shape
        self.pixelbits = 8*int(self.image.nbytes/(self.h*self.w))
  
        if not manual:
            self.nfov, self.nframes = self.f.sizes['v'], self.f.sizes['t']
        else:
            self.nfov, self.nframes = 288, 179
            self.f.sizes['v']=self.nfov
            self.f.sizes['t']=self.nframes
            self.f.metadata['fields_of_view']=list(range(self.nfov))
        
        #Widgets
        t_max = self.f.sizes['t']-1
        self.t = widgets.IntSlider(min=0,max=t_max, step=1, description="t", continuous_update=True)

        if 'c' in self.f.sizes:
            c_max = self.f.sizes['c']-1
        else:
            c_max=0
        self.c = widgets.IntSlider(min=0,max=c_max, step=1, description="c", continuous_update=True)

        v_max = self.f.sizes['v']-1
        self.v = widgets.IntSlider(min=0,max=v_max, step=1, description="v", continuous_update=False)
        
        clip_max=2**(self.pixelbits)*0.6
        
        self.clip = widgets.IntRangeSlider(min=0,max=int(2**16 -1), step=1, value=[0,clip_max], description="clip", continuous_update=True, width='200px')
        
        ##Initialize the figure
        plt.ioff()
        self.fig, self.ax = plt.subplots()
        self.fig.tight_layout()
        #self.fig.canvas.toolbar_visible = False
        self.fig.canvas.header_visible = False
        self.fig.canvas.footer_visible = True
        self.im = self.ax.imshow(self.image, cmap='gray', clim=self.clip.value)
                
        #Organize layout and display
        out = widgets.interactive_output(self.update, {'t': self.t, 'c': self.c, 'v': self.v, 'clip': self.clip})
        
        box = widgets.VBox([self.t, self.c, self.v, self.clip]) #, layout=widgets.Layout(width='400px'))
        box1 = widgets.VBox([out, box])
        grid = widgets.widgets.GridspecLayout(3, 3)
        
        grid[:, :2] = self.fig.canvas
        grid[1:,2] = box
        grid[0, 2] = out
        
        #display(self.fig.canvas)
        display(grid)
        plt.ion()
 
    def update(self, t, c, v, clip):

        vmin, vmax = clip
        image = self.f.get_frame_2D(v=v,c=c,t=t)
               
        self.im.set_data(image)
        #lanes = g.get_frame_2D(v=v)
        self.im.set_clim([vmin, vmax])
        #self.fig.canvas.draw()


class CellposeViewer:
    
    def __init__(self, nd2file, channel, manual=False):
        
        self.f = ND2Reader(nd2file)
        
        if not manual:
            self.nfov, self.nframes = self.f.sizes['v'], self.f.sizes['t']
        else:
            self.nfov, self.nframes = 288, 179
            self.f.sizes['v']=self.nfov
            self.f.sizes['t']=self.nframes
            self.f.metadata['fields_of_view']=list(range(self.nfov))
        
        self.channel=channel
        #Widgets
        
        t_max = self.f.sizes['t']-1
        self.t = widgets.IntSlider(min=0,max=t_max, step=1, description="t", continuous_update=False)

        v_max = self.f.sizes['v']-1
        self.v = widgets.IntSlider(min=0,max=v_max, step=1, description="v", continuous_update=False)
        
        self.cclip = widgets.FloatRangeSlider(min=0,max=2**16, step=1, value=[50,8000], description="clip cyto", continuous_update=False, width='200px')
        
        self.flow_threshold = widgets.FloatSlider(min=0, max=1.5, step=0.05, description="flow_threshold", value=1.25, continuous_update=False)
        
        self.diameter = widgets.IntSlider(min=15,max=100, step=2, description="diameter", value=29, continuous_update=False)
        
        self.mask_threshold = widgets.FloatSlider(min=-3,max=3, step=0.1, value=0, description="mask_threshold", continuous_update=False)
        
    
        image = self.f.get_frame_2D(v=0,c=self.channel,t=0)
        
        ##Initialize the figure
        plt.ioff()
        self.fig, self.ax = plt.subplots()
        self.fig.tight_layout()
        #self.fig.canvas.toolbar_visible = False
        self.fig.canvas.header_visible = False
        #self.fig.canvas.footer_visible = False
        self.im = self.ax.imshow(image, clim=self.cclip.value)

        self.segmenter = Segmentation(pretrained_model='mdamb231')
        self.mask = self.segmenter.segment_image(image, self.diameter.value, self.flow_threshold.value, self.mask_threshold.value)

        self.flow_threshold_value = self.flow_threshold.value
        self.diameter_value = self.diameter.value
        self.mask_threshold_value = self.mask_threshold.value
        self.t_value=0

        #Organize layout and display
        out = widgets.interactive_output(self.update, {'t': self.t, 'v': self.v, 'cclip': self.cclip, 'flow_threshold': self.flow_threshold, 'diameter': self.diameter, 'mask_threshold': self.mask_threshold})
        
        box = widgets.VBox([self.t, self.v, self.cclip, self.flow_threshold, self.diameter, self.mask_threshold]) #, layout=widgets.Layout(width='400px'))
        box1 = widgets.VBox([out, box])
        grid = widgets.widgets.GridspecLayout(3, 3)
        
        grid[:, :2] = self.fig.canvas
        grid[1:,2] = box
        grid[0, 2] = out
        
        #display(self.fig.canvas)
        display(grid)
        plt.ion()
    

    def update(self, t, v, cclip, flow_threshold, diameter, mask_threshold):      
        
        bf = self.f.get_frame_2D(v=v, t=t, c=self.channel)

        recompute = (flow_threshold!=self.flow_threshold_value) or (
        diameter!=self.diameter_value) or (
        mask_threshold!= self.mask_threshold_value) or(
        t!=self.t_value)

        if recompute:
            print('recomputing')
            self.mask = self.segmenter.segment_image(bf, diameter, flow_threshold, mask_threshold)
            
        image = self.get_contours_image(bf, self.mask, cclip)

        self.im.set_data(image)

        self.flow_threshold_value = flow_threshold
        self.diameter_value = diameter
        self.mask_threshold_value = mask_threshold
        self.t_value=t

        return
   
        
    def get_contours_image(self, bf, mask, clip):
        
        vmin, vmax = clip

        bin_mask = np.zeros(mask.shape, dtype='bool')
        cell_ids = np.unique(mask)
        cell_ids = cell_ids[cell_ids!=0]
        
        for cell_id in cell_ids:
            bin_mask+=binary_erosion(mask==cell_id)
        
        outlines = find_boundaries(bin_mask, mode='outer')
        try:
            print(f'{cell_ids.max()} Masks detected')
        except ValueError:
            print('No masks detected')
        
        
        bf = np.clip(bf, vmin, vmax)
        bf = (255*(bf-vmin)/(vmax-vmin)).astype('uint8')
        
        image = np.stack((bf, bf, bf), axis=-1)
        
        image[(outlines>0)]=[255,0,0]
        
        return image
    