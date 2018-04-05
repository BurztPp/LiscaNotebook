#! /usr/bin/env python3
from gui_tk import get_root, new_toplevel
import tkinter as tk
from tkinter import ttk

PAD_X = 10
PAD_Y = 10


class WorkflowGUI:
    def __init__(self, module_manager=None):
        """Set up the workflow GUI."""
        self.modman = module_manager
        self.main = new_toplevel()
        self.root = get_root()
        self.modman.register_builtin_data("workflow_gui_tk", self)
        self.main.title("Workflow")
        self.main.minsize(width=200, height=500)

        self.mainframe = ttk.Frame(self.main)
        self.mainframe.pack(fill=tk.BOTH, expand=True)

        self.add_button = ttk.Button(self.mainframe, text="New", command=self.new_module)
        self.add_button.pack(side=tk.TOP, fill=tk.X, padx=PAD_X, pady=PAD_Y)


    def new_module(self):
        self.add_button.pack_forget()
        m = ModuleFrame(self.mainframe, self.modman)
        self.add_button.pack(fill=tk.X, padx=PAD_X, pady=PAD_Y)


    def mainloop(self):
        """Start the tkinter mainloop."""
        self.root.mainloop()


class ModuleFrame:
    """Frame representing a module"""
    def __init__(self, parent, modman):
        """Set up the frame."""
        self.parent = parent
        self.modman = modman

        # Build frame
        self.frame = ttk.Frame(self.parent, relief=tk.RAISED,
            borderwidth=2, width=250, height=150)
        self.frame.pack(fill=tk.X, padx=PAD_X, pady=PAD_Y)
        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)

        # Drop-down menu for selecting the model
        self.modlist = self.modman.list_display()
        self.mod_sel = tk.StringVar(get_root(self.parent))
        self.mod_menu = ttk.OptionMenu(self.frame, self.mod_sel, "[Select a plugin]", *[m['name'] for m in self.modlist])
        self.mod_menu.grid(row=0, column=0, columnspan=2, sticky=tk.W+tk.E)

        # Buttons for configuring and running the module
        self.mod_config_but = ttk.Button(self.frame, text="Configure", command=self.configure_module)
        self.mod_config_but.grid(row=1, column=0, sticky=tk.W+tk.E)
        self.mod_run_but = ttk.Button(self.frame, text="Run", command=self.run_module)
        self.mod_run_but.grid(row=1, column=1, sticky=tk.W+tk.E)


    def configure_module(self):
        """Configure the selected module."""
        name = self.mod_sel.get()
        for m in self.modlist:
            if m['name'] == name:
                #print(f"Configure module {m['name']} with id {m['id']}")
                self.modman.configure_module(m['id'])
                return
        print("No module found for configuring.")


    def run_module(self):
        """Run the selected module."""
        name = self.mod_sel.get()
        for m in self.modlist:
            if m['name'] == name:
                #print(f"Run module {m['name']} with id {m['id']}")
                self.modman.run_module(m['id'])
                return
        print("No module found for running.")
