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

from roi import RectRoi
from roi import ContourRoi


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
    print(RectRoi.key())
    path = d[my_id]["_path"]
    grids = d[""]["stack"].rois
    for key in grids:
#        if type(key) is not str:
#            try:
#                RectRoi[str(key)] = RectRoi[key]
#            except:
#                try:
#                    RectRoi[repr(key)] = RectRoi[key]
#                except:
#                    pass
##                  del RectRoi[key]
#        for key in RectRoi.key():
#            if type(key) is not str:
#                try:
#                    RectRoi[str(key)] = RectRoi[key]
#                except:
#                    try:
#                        RectRoi[repr(key)] = RectRoi[key]
#                    except:
#                        pass
#                   del RectRoi[key]
        if key == RectRoi.key():
            corndict = {}
            for i in grids[key][Ellipsis]:
                corns=i.corners.tolist()
                corndict[i] = json.dumps({"%s"%(i.label):corns}, sort_keys=True, indent=4, separators=(',', ':'))
                f=open(os.path.join(path,"grid_out_{}.txt".format(time.strftime("%d%m%Y-%H%M%S"))),"a")
                f.write(json.dumps({"(%s)"%(repr(key)):corndict}, sort_keys=True, indent=4, separators=(',', ':')))
                f.close()
#        elif key == ContourRoi.key():
#            corndict2 = {}
#            for i in grids[key][Ellipsis]:
#                corns=i.corners.tolist()
#                corndict2[i] = json.dumps({"%s"%(i.label):corns}, sort_keys=True, indent=4, separators=(',', ':'))
#                f=open(os.path.join(path,"grid_out_{}.txt".format(time.strftime("%d%m%Y-%H%M%S"))),"a")
#                f.write(json.dumps({"(%s,%s)"%(key[0],key[1]):corndict2}, sort_keys=True, indent=4, separators=(',', ':')),'\n')
#                f.close()
        else:
            raise TypeError("incompatible ROI type")














