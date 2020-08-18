#! /usr/bin/env python3
import os.path as op
import sys
pyama_dir = op.abspath(op.join(op.dirname(__file__), '..', '..'))
print(pyama_dir)
sys.path.append(pyama_dir)

import tkinter as tk
import src.session # Fix import dependency circle
import src.gui.channel_control_pane as ccp

root=tk.Tk()
ccp.ChannelControlPane_Tk(root).pack(fill=tk.BOTH, expand=True)
root.mainloop()
