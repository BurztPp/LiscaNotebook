#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 28 15:36:57 2018

Plugin to load saved grid parameters 

@author: Viraj.Nistane
"""

import gui_tk
from stack import Stack
from stackviewer_tk import StackViewer
from threading import Condition
import tkinter as tk

import os
import sys
import time
import json

my_id = "grid_loader"

def register(meta):
    meta.name = "Load grid"
    meta.id = my_id
    meta.conf_ret = "_path"
    meta.run_dep = (
            ("", "stack"),
            (my_id, "_path"),
        )
#    meta.run_ret = ("stack", "_StackViewer")
    
def conf(d, *_, **__):
    print("Configuring 'grid_loader'.")
    f = gui_tk.askopenfilename(parent=gui_tk.root)
    print(f)
    return {"_path": f}

#def conf(d, *_, **__):
#    path = os.path.join(os.getcwd(), "out" , "grid_out")
#
#    if not os.path.isdir(path):
#        try:
#            os.mkdir(path)
#        except Exception as e:
#            print("Cannot create directory: {}".format(e))
#
#    return {"_path": path}


def run(d, *_, **__):
    print("Running 'grid_loader'.")
    path = d[my_id]['_path']
    s=stack(path)
    loaded = json.load(f1)
    Stack.new_roi_collection(loaded[0]['rois'])
        
        
        




























