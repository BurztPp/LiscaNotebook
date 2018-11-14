#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 14 12:14:00 2018

Plugin to save grid parameters 


@author: Viraj.Nistane
"""


import numpy as np
import os
import sys
import time
import json 


my_id = "grid_to_json_saver"

def register(meta):
    meta.name = "Save grid to json"
    meta.id = my_id

    #meta.conf_dep = ("", "workflow_gui_tk")
    meta.conf_ret = "_path"
    meta.run_dep = (
            ("", "stack"),
            (my_id, "_path"),
        )

def conf(d, *_, **__):
    path = os.path.join(os.getcwd(), "out" , "grid_out")

    if not os.path.isdir(path):
        try:
            os.mkdir(path)
        except Exception as e:
            print("Cannot create directory: {}".format(e))

    return {"_path": path}



def run(d, *_, **__):
    path = d[my_id]["_path"]
    grids = d[""]["stack"].rois
#    params = grids["stack"].rois.parameters[]
#    name = grids["name"][""]
#    parameters = grids["parameters"][""]
#    if self.i_frame in self.stack.rois:
#        roi_key = self.i_frame
#    elif Ellipsis in self.stack.rois:
#        roi_key = Ellipsis
#    else:
#        return
#    labeldict = {}
#    cornerdict = {}
#    f=open("/home/v/Viraj.Nistane/hiwi_raedler/pyama/out/grid_out_f{:d}_{}.txt".format(i+1,time.strftime("%Y%m%d-%H%M%S")),"w")
#    f.write("name = %s")
#    f.close()

    for i in grids[Ellipsis]:
#        labeldict["%s"%(i)]=i.label
        corns=i.corners.tolist()
        f=open(os.path.join(path,"grid_out_xxtest_{}.txt".format(time.strftime("%Y%m%d-%H%M%S"))),"a")
        f.write(json.dumps({"%s"%(i.label):corns}, sort_keys=True, indent=4))
        f.close()
        
    
    
    
    
#    path = d[my_id]["_path"]
#    intensities = d[""]["integrated_intensity"]
#    n_channels, n_frames = intensities.shape
#    for iCh in range(n_channels):
#        int_tab = np.empty((n_frames, 1 + len(intensities[iCh, 0])))
#        int_tab[:,0] = range(n_frames)
#        for iFr in range(n_frames):
#            for idx, entry in enumerate(intensities[iCh,iFr]):
#                if idx+1 >= int_tab.shape[1]:
#                    print("Found {} ROIs in frame {}, expected {}, ignoring rest.".format(len(intensities[iCh,0]), iFr, int_tab.shape[1])) #DEBUG
#                    break
#                int_tab[iFr, idx+1] = entry
#        outname = os.path.join(path, "integ_intensity_c{:d}_{}.csv".format(iCh+1, time.strftime("%Y%m%d-%H%M%S")))
#        np.savetxt(outname, int_tab, fmt='%.7e', delimiter=',')
#        print("Saved intensities to: {}".format(outname))
#
#
#
#
#
#
















