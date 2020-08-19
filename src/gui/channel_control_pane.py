import queue
from threading import Thread
import tkinter as tk
import tkinter.filedialog as tkfd
import tkinter.ttk as ttk

if __name__ == '__main__':
    # Prevent import error due to dependency circle
    from ..session.channel_collection import ChannelCollection

from ..session import const as sess_const
from ..stack import const as stack_const
from .. import util
from . import scrollutil as scu


class ChannelControlPane_Tk(tk.PanedWindow):
    def __init__(self, parent=None, channel_collection=None):
        super().__init__(parent, orient=tk.VERTICAL)
        self.channel_collection = None
        self.channel_collection_lid = None
        self.queue = queue.Queue()
        self.evt_map = {
                stack_const.EVT_CLOSE: lambda m: self.set_channel_collection(),
                stack_const.EVT_RESHAPE: self.stack_reshaped,
                sess_const.EVT_STACK_ADDED: self.stack_opened,
                sess_const.EVT_STACK_RENAMED: self.stack_renamed,
                sess_const.EVT_STACK_DROPPED: self.stack_closed,
                sess_const.EVT_CHANNELS_REORDERED: self.channels_reordered,
                sess_const.EVT_CHANNEL_SPEC_CHANGE: self.channel_edited,
                }

        # Variables
        self.var_index_add = tk.IntVar(self)
        self.var_index_add.set(1)

        # Stack components
        self.fr_stacks = tk.LabelFrame(self, text="Stacks", padx=5, pady=5)
        self.fr_stacks.grid_columnconfigure(0, weight=1, uniform='a')
        self.fr_stacks.grid_columnconfigure(1, weight=1, uniform='a')
        self.fr_stacks.grid_rowconfigure(0, weight=1)
        self.add(self.fr_stacks)
        self.pane_stackinfo = tk.PanedWindow(self.fr_stacks, orient=tk.VERTICAL)

        ## Treeview
        self.tree_frame = scu.ScrolledWidget(self.pane_stackinfo)
        self.pane_stackinfo.add(self.tree_frame, minsize=80, sticky='NESW')
        self.stack_tree = ttk.Treeview(self.tree_frame,
                columns=['Name', 'File'],
                displaycolumns=('#all'),
                height=3,
                selectmode='browse',
                )
        self.tree_frame.set_widget(self.stack_tree)
        self.stack_tree.column('#0', minwidth=20, width=30, anchor=tk.E, stretch=False)
        self.stack_tree.column('Name', minwidth=100, stretch=True)
        self.stack_tree.column('File', minwidth=300, stretch=True)
        for cn, ct in zip(('#0', 'Name', 'File'), ('#', 'Name', 'File')):
            self.stack_tree.heading(cn, text=ct)

        ## Further components
        self.fr_stackinfo = scu.ScrolledFrame(self.pane_stackinfo,
                relief=tk.SUNKEN, bd=1)
        self.pane_stackinfo.add(self.fr_stackinfo, minsize=40, sticky='NESW')
        self.fr_stackinfo.viewport.config(bg='white')
        self.btn_st_open = tk.Button(self.fr_stacks,
                text="Open...",
                command=self.open_stack,
                )
        self.btn_st_close = tk.Button(self.fr_stacks,
                text="Close",
                command=self.close_stack,
                )
        self.btn_st_reshape = tk.Button(self.fr_stacks,
                text="Reshape...",
                command=self.reshape_stack,
                )
        self.btn_st_add = tk.Button(self.fr_stacks,
                text="Add...",
                command=self.add_channel,
                )

        ## Add stack components to grid
        self.pane_stackinfo.grid(row=0, column=0,
                columnspan=2,
                sticky='NESW',
                pady=(0, 5),
                )
        self.btn_st_open.grid(row=1, column=0, sticky='NESW')
        self.btn_st_close.grid(row=1, column=1, sticky='NESW')
        self.btn_st_reshape.grid(row=2, column=0, sticky='NESW')
        self.btn_st_add.grid(row=2, column=1, sticky='NESW')

        # Channel components
        self.fr_channels = tk.LabelFrame(self, text="Channels", padx=5, pady=5)
        self.fr_channels.grid_columnconfigure(0, weight=1, uniform='a')
        self.fr_channels.grid_columnconfigure(1, weight=1, uniform='a')
        self.fr_channels.grid_rowconfigure(0, weight=1)
        self.add(self.fr_channels)

        ## Channel list Treeview
        self.fr_chanlist = scu.ScrolledWidget(self.fr_channels)
        self.chan_tree = ttk.Treeview(self.fr_chanlist,
                columns=['Name', 'Category'],
                displaycolumns=('#all'),
                height=3,
                selectmode='browse',
                )
        self.fr_chanlist.set_widget(self.chan_tree)
        self.chan_tree.column('#0', minwidth=20, width=30, anchor=tk.W, stretch=False)
        self.chan_tree.column('Name', minwidth=50, stretch=True)
        self.chan_tree.column('Category', minwidth=70, stretch=True)
        for cn, ct in zip(('#0', 'Name', 'Category'), ('#', 'Name', 'Category')):
            self.chan_tree.heading(cn, text=ct)


        ## Buttons
        self.btn_ch_edit = tk.Button(self.fr_channels,
                text="Edit...",
                command=self.edit_channel,
                )
        self.btn_ch_drop = tk.Button(self.fr_channels,
                text="Drop",
                command=self.drop_channel,
                )

        ## Add channel components to grid
        self.fr_chanlist.grid(row=0, column=0, columnspan=2, sticky='NESW')
        self.btn_ch_edit.grid(row=1, column=0, sticky='NESW')
        self.btn_ch_drop.grid(row=1, column=1, sticky='NESW')

        if channel_collection is not None:
            self.set_channel_collection(channel_collection)

        util.poll_event_queue_tk(self, self.queue)


    def set_channel_collection(self, cc=None):
        if self.channel_collection:
            self.channel_collection.delete_listener(self.channel_collection_lid)
            self.channel_collection = None
            self.stack_tree.delete(*self.stack_tree.get_children())
            self.chan_tree.delete(*self.chan_tree.get_children())
            self.update_stackinfo()
        if cc:
            self.channel_collection = cc
            self.channel_collectoin_lid = cc.add_listener(self.process_event, self.queue)


    def process_event(self, message):
        """Call event handler for a given event message"""
        self.evt_map[message['event']](message)
        

    def open_stack(self):
        """Prompt user for a stack to open"""
        #TODO: more advanced dialog
        fn = tkfd.askopenfilename(initialdir='res',
                parent=self,
                title="Select stack to open",
                filetypes=(
                    ("Stack", '*.tif *.tiff *.npy *.npz *.hdf5 *.h5'),
                    ("TIFF", '*.tif *.tiff'),
                    ("Numpy", '*.npy *.npz'),
                    ("Ilastik", '*.hdf5 *.h5'),
                    ("All", '*'),
                    )
                )
        if fn:
            Thread(target=self.channel_collection.add_stack, args=(fn,)).start()


    def close_stack(self):
        """Close the stack selected in 'stack_tree'"""
        sel = self.stack_tree.selection()
        if not sel:
            return
        active_stacks = set(v['stack'] for v in self.channel_collection.channels.values())
        if set(sel) & active_stacks:
            #TODO ask for user confirmation
            pass
        for s in sel:
            self.channel_collection.drop_stack(s)

        
    def reshape_stack(self):
        print("Reshape stack") #TODO

    def update_stackinfo(self):
        print("Update stackinfo") #TODO

    def add_channel(self):
        print("Add channel") #TODO

    def edit_channel(self):
        print("edit_channel") #TODO

    def drop_channel(self):
        print("drop_channel") #TODO

    def stack_opened(self, msg):
        """Callback for 'stack_const.EVT_STACK_ADDED'"""
        stack_id = msg['stack_id']
        n = str(len(self.stack_tree.get_children()) + 1)
        stack = self.channel_collection.stacks[stack_id]
        val = (stack['name'], stack['ref'].path)
        self.stack_tree.insert('', index='end', iid=stack_id, text=n, values=val)

    def stack_renamed(self, msg):
        print("stack_renamed") #TODO
        
    def stack_closed(self, msg):
        """Remove stack from display when closed"""
        self.stack_tree.delete(msg['stack_id'])

    def stack_reshaped(self, msg):
        print("stack_reshaped") #TODO

    def channel_added(self, msg):
        print("channel_added") #TODO

    def channel_edited(self, msg):
        print("channel_edited") #TODO

    def channels_reordered(self, msg):
        print("channels_reordered") #TODO

    def channel_dropped(self, msg):
        print("channel_dropped") #TODO


if __name__ == '__main__':
    root=tk.Tk()
    cc = ChannelCollection()
    ChannelControlPane_Tk(root, cc).pack(fill=tk.BOTH, expand=True)
    root.mainloop()
    cc.close()