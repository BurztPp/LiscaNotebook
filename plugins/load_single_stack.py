"""
This plug-in displays a file selection dialog and opens the
stack from the file.
"""
import gui_tk
from stack import Stack
from stackviewer_tk import StackViewer

my_id = "simple_stack_reader"

def register(meta):
    meta.name = "Read stack"
    meta.id = my_id
    meta.conf_ret = "path"
    meta.run_dep = (my_id, "", "path")
    meta.run_ret = ("stack", "StackViewer")


def configure(**d):
    print("Configuring 'load_single_stack'.")
    f = gui_tk.askopenfilename(parent=gui_tk.root)
    print(f)
    return {"path": f}


def run(**d):
    print("Running 'load_single_stack'.")
    path = d[my_id]['path']

    s = Stack(path)
    tl_win = gui_tk.new_toplevel()
    sv = StackViewer(tl_win)
    sv.set_stack(s)

    return {"stack": s,
            "StackViewer": sv}

