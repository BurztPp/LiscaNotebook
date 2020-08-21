import tkinter as tk

from ..session import const as sess_const


class ChannelAddDialog(tk.Toplevel):
    def __init__(self, parent, n_channels, stack_name=None):
        super().__init__(parent)
        self.title("PyAMA – Add channel")
        self.resizable(width=True, height=False)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(n_channels+2, weight=1)

        self.value = None

        sn = "" if stack_name is None else f" from stack '{stack_name}'"
        tk.Label(self, text=f"Select channels to add{sn}:").grid(row=0, column=0, columnspan=3)
        tk.Label(self, text="Channel").grid(row=1, column=0, sticky=tk.E+tk.W)
        tk.Label(self, text="Category").grid(row=1, column=1, sticky=tk.E+tk.W)
        tk.Label(self, text="Name").grid(row=1, column=2, sticky=tk.E+tk.W)

        self.data = tuple(dict() for _ in range(n_channels))
        for i, d in enumerate(self.data):
            d['var_check'] = tk.BooleanVar(self, value=True)
            d['check'] = tk.Checkbutton(self, variable=d['var_check'], text=str(i+1), anchor=tk.E, padx=5)
            d['check'].grid(row=i+2, column=0, sticky=tk.E+tk.W, padx=5)
            d['var_menu'] = tk.StringVar(self, value=sess_const.CH_CAT_FL)
            d['var_menu'].trace_add('write', lambda *_, i=i: self.activate(i))
            d['menu'] = tk.OptionMenu(self, d['var_menu'], sess_const.CH_CAT_PHC, sess_const.CH_CAT_FL, sess_const.CH_CAT_BIN)
            d['menu'].grid(row=i+2, column=1, sticky=tk.E+tk.W)
            d['menu'].config(takefocus=True, bd=1, indicatoron=False, direction='flush')
            d['var_name'] = tk.StringVar(self, value="")
            d['var_name'].trace_add('write', lambda *_, i=i: self.activate(i))
            d['ent_name'] = tk.Entry(self, justify=tk.LEFT, exportselection=False, textvariable=d['var_name'])
            d['ent_name'].grid(row=i+2, column=2, sticky=tk.E+tk.W)

        fr_buttons = tk.Frame(self)
        fr_buttons.grid(row=n_channels+2, column=0, columnspan=3, sticky='NESW')
        fr_buttons.grid_columnconfigure(0, weight=1, uniform='uniform_buttons', pad=20)
        fr_buttons.grid_columnconfigure(1, weight=1, uniform='uniform_buttons', pad=20)

        tk.Button(fr_buttons, text="OK", command=self.click_ok).grid(row=0, column=0, sticky='NESW')
        tk.Button(fr_buttons, text="Close", command=self.destroy).grid(row=0, column=1, sticky='NESW')

        self.bind('<Return>', self.click_ok)
        self.bind('<KP_Enter>', self.click_ok)
        self.bind('<Escape>', self.destroy)


    def activate(self, i):
        self.data[i]['var_check'].set(True)


    def click_ok(self, *_):
        res = []
        for i, d in enumerate(self.data):
            if d['var_check'].get():
                name = d['var_name'].get()
                if not name:
                    name = None
                res.append(dict(
                    index=i,
                    category=d['var_menu'].get(),
                    name=name))
        if res:
            self.value = res
        self.destroy()


    @classmethod
    def run(cls, parent, n_channels, stack_name=None):
        d = cls(parent, n_channels, stack_name)
        d.transient(parent)
        d.grab_set()
        d.wait_window(d)
        return d.value


if __name__ == '__main__':
    import sys
    try:
        n_channels = int(sys.argv[1])
    except IndexError:
        n_channels = 3
    try:
        stack_name = sys.argv[2]
    except IndexError:
        stack_name = None

    def test(root, n_channels, stack_name):
        res = ChannelAddDialog.run(root, n_channels, stack_name)
        root.quit()
        if res is None:
            print("None")
        else:
            for r in res:
                print(", ".join(f"{k}={v}" for k, v in r.items()))

    root = tk.Tk()
    root.after(5, test, root, n_channels, stack_name)
    root.mainloop()
