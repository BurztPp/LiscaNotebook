from collections import OrderedDict, defaultdict
import numbers
import os
import queue

from . import const
from ..stack import const as sconst
from ..stack import open_stack, BaseStack
from .. import util

class ChannelCollection(BaseStack):
    """This class provides all necessary data and methods for
    associating multiple stacks and ROIs with each other.

    Data structures of this class:
    
    __stacks
        dict of loaded stacks
        key: stack ID
        'name': str, user-specified display name of stack
        'ref': reference to stack object
        'listener_id': listener ID for events of the stack

    __channels
        dict of loaded channels
        key: channel ID
        'name': str, user-specified display name of channel
        'categrory': categrory of channel
        'description': str, user-specified description of the channel
        'position': int, index in __channel_order
        'stack': stack ID of corresponding stack
        'index': str, index of channel in corresponding stack


    __channel_order
        list of IDs of loaded channels
        Defines the order of channels in this ChannelCollection

    """
    def __init__(self):
        listeners_kinds = (
                EVT_CLOSE,
                EVT_STACK_ADDED,
                EVT_STACK_RENAMED,
                EVT_STACK_DROPPED,
                EVT_CHANNELS_REORDERED,
                EVT_CHANNEL_SPEC_CHANGE,
                )
        super().__init__(listeners_kinds=listeners_kinds)
        self.__stacks = {}
        self.__channels = {}
        self.__channel_order = []

        self.__queue = queue.Queue()
        util.listen_for_events(self.__queue)


    def close(self):
        """Close this ChannelCollection"""
        self.__queue.put_nowait(None)
        super().close()
        for stack_id in self.__stacks.keys():
            self.drop_stack(stack_id)


    def add_stack(stack, name=None, **kwargs):
        """Insert new stack into ChannelCollection.

        'stack': either path to stack file or reference to existing stack object
        'name': display name of stack
        'kwargs': keyword arguments that will be passed to stack constructor
                 if 'stack' is a path
        """
        if isinstance(stack, (str, os.PathLike)):
            stack = open_stack(stack, **kwargs)
        if not name and stack.path:
            name = os.path.split(os.path.normpath(stack.path))[-1]
        if not name:
            name = f"{stack.__class__.__name__} {stack.id}"
        with self.lock:
            if stack.id not in self.__stacks:
                lid = stack.add_listener(self._hear_event, self.__queue)
                self.__stacks[stack.id] = dict(ref=stack, name=name, listener_id=lid)
                self.listeners.notify(const.EVT_STACK_ADDED, stack_id=stack.id)


    def drop_stack(stack_id):
        """Unload stack with ID `stack_id` and all associated channels"""
        with self.lock:
            self.drop_channel(ch_id for ch_id, ch in self.__channels.items() if ch['stack'] == stack_id)
            stack = self.__stacks.pop(stack_id)
            stack['ref'].delete_listener(stack['listener_id'])
            stack['ref'].close()


    def rename_stack(stack_id, name):
        """Rename stack with ID `stack_id` to `name`"""
        with self.lock:
            self.__stacks[stack_id]['name'] = name
            self.listeners.notify(const.EVT_STACK_RENAMED, stack_id=stack_id)
            

    def add_channel(self, stack_id, index, position=None, name=None, category=None, description=None):
        """Add a channel to the active channel collection.

        Arguments:
            stack_id -- str, ID of the associated stack of the new channel
            index -- int, (zero-based) index of the new channel in the associated stack
            position -- int, (zero-based) position in active channel collection to insert channel
                        (default: append channel)
            name -- str, display name of the channel; if not given, default name will be assigned
            category -- str, channel category; one of `const.CH_CAT_LIST`
            description -- str, human-readable description of channel
        """
        with self.lock:
            stack = self.__stacks[stack_id]['ref']
            if stack.n_channels <= index:
                raise IndexError(f"Stack '{stack_id} has no channel {index}'")

# old stuff; to be deleted
#            if self._shape is not None:
#                #TODO Check if stack is compatible
#                s_shape = stack.shape_dict
#                s_S = s_shape.get[sconst.S]
#                if s_S and s_S > 1
#                    raise ValueError("Stacks with multiple samples are currently not supported")
#                if s_shape[sconst.X] != self._shape[sconst.X] or \
#                        s_shape[sconst.Y] != self._shape[sconst.Y]:
#                        raise ValueError("Incompatible image resolutions: "
#                            f"{s_shape[sconst.X]}x{s_shape[sconst.Y]} does not match "
#                            f"{self._shape[sconst.X]}x{self._shape[sconst.Y]}")
#                for dim in (sconst.T, sconst.Z, sconst.C):
#                    n_stack = s_shape.get(dim)
#                    n_self = self._shape.get(dim)
#                    if all(n not in (None, 1) for n in (n_stack, n_self)) and (n_stack != n_self):
#                        raise ValueError(f"Dimension {dim}=){n_stack} not compatible with {n_self}")
            ch = {}
            ch_id = util.make_uid(ch)
            if not name:
                name = f"Channel {ch_id}"
            if position is None:
                position = len(self.__channel_order)
            ch['name'] = name
            ch['category'] = category
            ch['description'] = description
            ch['position'] = position
            ch['stack'] = stack_id
            ch['index'] = index

            old_channel_order = self.__channel_order.copy()
            self.__channel_order.insert(position, ch)
            for i in range(position+1, len(self.__channel_order)):
                self.__channels[self.__channel_order[i]]['position'] = i
            self.__channels[ch_id] = ch

            try:
                self._update_shape()
            except ValueError:
                self.__channel_order = old_channel_order
                for i in range(position, len(self.__channel_order)):
                    self.__channels[self.__channel_order[i]]['position'] = i
                del self.__channels[ch_id]
                raise


    def drop_channel(self, *channel_id):
        """Remove channels with IDs in `channel_id` from active channel collection"""
        with self.lock:
            for ch_id in channel_id:
                del self.__channels[ch_id]
            i = 0
            new_order = []
            for ch_id in self.__channel_order:
                if ch_id not in channel_id:
                    new_order.append(ch_id)
                    self.__channels[ch_id]['position'] = i
                    i += 1
            self.__channel_order = new_order

            self._update_shape()


    def change_channel_spec(self, channel_id, **new_specs):
        """Change specification of channel with id `channel_id`.

        `new_specs` are the properties to be changed and the new values.
        Changeable properties are: 'name', 'category', 'description'.
        See 'add_channel' for details.
        """
        old_spec = {}
        with self.lock:
            ch = self.__channels[channel_id]
            for spec, val in new_specs.items():
                if spec == 'name':
                    if not val:
                        val = f"Channel {channel_id}"
                    ch['name'] = val
                elif spec == 'category':
                    if val not in const.CH_CAT_LIST and val is not None:
                        raise ValueError(f"Cannot set unknown channel category '{val}'")
                elif spec != 'description':
                    raise ValueError(f"Cannot set unknown channel spec '{spec}'")
                ch[spec] = val
                old_spec[spec] = ch[spec]
            if old_spec:
                msg = dict(
                        event=const.EVT_CHANNEL_SPEC_CHANGE,
                        id=channel_id,
                        old=old_spec,
                        new={spec: ch[spec] for spec in old_spec.keys()}
                        )
                self.listeners.notifiy(const.EVT_CHANNEL_SPEC_CHANGE, message=msg)


    def change_channel_order(self, new_order):
        """Change order of active channel collection.

        `new_order` is the new sequence of channel IDs.
        The channel order must only be permuted.
        Use 'add_channel' or 'drop_channel' to add or
        remove channels from the active channel collection.
        """
        with self.lock:
            if sorted(new_order) != sorted(self.__channel_order):
                raise ValueError("`new_order` is not a permutation of channel order")
            old_order = self.__channel_order
            self.__channel_order = list(new_order)
            for pos, ch_id in enumerate(self.__channel_order):
                self.__channels[ch_id]['position'] = pos
            msg = dict(
                    event=const.EVT_CHANNELS_REORDERED,
                    id=self._id,
                    old=old_order,
                    new=self.__channel_order.copy()
                    )
            self.listeners.notify(const.EVT_CHANNELS_REORDERED, message=msg)


    def get_image(self, *, frame=None, z=None, channel=None):
        """Get image from active channel collection"""
        with self.lock:
            if isinstance(channel, numbers.Integral):
                ch_id = self.__channel_order[channel]
            elif channel in self.__channel_order:
                ch_id = ch_id
            else:
                raise KeyError(f"Unknown channel '{channel}'")
            ch = self.__channels[ch_id]
            stack = self.__stacks[ch['stack']]
            return stack.get_image(frame=frame, z=z, channel=ch['index'])


    @staticmethod
    def _merge_shapes(*shapes):
        """Get merged shape compatible with all `shapes`.

        Returns an OrderedDict of shape, or None if all
        input shapes are empty.
        Raises a ValueError if shapes are not compatible.
        """
        merged = OrderedDict()
        all_shapes = defaultdict(set)
        for d in (*sconst.STACK.DIM, *sconst.IMG_DIM):
            for sh in shapes:
                all_shapes[d].add(sh.get(d))
        for d, s in all_shapes.items():
            if d in sconst.STACK_DIM:
                s -= {None, 1}
                if len(s) > 1:
                    break
                elif s:
                    merged[d] = s.pop()
            elif d in (sconst.X, sconst.Y):
                if len(s) != 1 or None in s:
                    break
                else:
                    merged[d] = s.pop()
            elif d == sconst.S:
                if s - {None, 1}:
                    # Samples are not implemented
                    break
        else:
            if not merged:
                merged = None
            return merged
        raise ValueError("Shapes are not compatible")


    def _update_shape(self):
        """Bring shape of active channel collection in conformity with `__channel_order`.

        Raises ValueError if shapes are incompatible.
        
        Not thread-safe. Only call with `lock` acquired.
        """
        merged = self._merge_shapes(self.__stacks[sid].shape_dict for sid in {ch['stack'] for ch in self.__channels.values()})
        if merged != self._shape:
            msg = dict(
                    event=sconst.EVT_RESHAPE,
                    id=self.stack_id,
                    old=self._shape.copy() if self._shape is not None else None,
                    new=merged.copy() if merged is not None else None,
                    )
            self._shape = merged
            self.listeners.notify(sconst.EVT_RESHAPE, message=msg)


        # Old function body; to be deleted
#        with self.lock:
#            msg = None
#            if not self.__channels:
#                if self._shape:
#                    old_shape = self._shape.copy()
#                    self._shape = None
#                    msg = dict(
#                            event=sconst.EVT_RESHAPE,
#                            id=self.stack_id,
#                            old=old_shape,
#                            new=self._shape)
#            else:
#                if self._shape is None:
#                    old_shape = None
#                else:
#                    s_id = next(iter(self.__channels.values()))['stack']
#                    stack = self.__stacks[s_id]
#                    old_shape = self._shape.copy()
#                    new_shape = OrderedDict()
#                    new_shape[sconst.C] = len(self.__channels)
#                    for dim, n in stack.shape_dict:
#                        if dim == sconst.C:
#                            continue
#                        elif dim == sconst.S:
#                            if n > 1:
#                                raise NotImplementedError("Samples are currently not supported.")
#                            continue
#                        else:
#                            new_shape[dim] = n
#                    msg = dict(
#                            event=sconst.EVT_RESHAPE,
#                            id=self._id,
#                            old=old_shape,
#                            new=new_shape.copy()
#                            )
#                    self._shape = new_shape


    def _hear_event(self, *args, **kwargs):
        """Handle incoming events"""
        if 'message' not in kwargs:
            raise ValueError("Invalid event")
        msg = kwargs['message']
        if msg['event'] == sconst.EVT_RESHAPE:
            self._handle_evt_stack_reshape(msg)
        elif msg['event'] == sconst.EVT_CLOSE:
            self._handle_evt_stack_close(msg)
        else:
            raise ValueError(f"Unknown event '{msg['event']}'")


    def _handle_evt_stack_reshape(self, msg):
        """Event handler for `sconst.EVT_RESHAPE`"""
        is_ok = True
        with self.lock:
            check_chan = [ch for ch in self.__channels if ch['stack'] == msg['id']]
            if not check_chan:
                pass
            elif any(ch['index'] >= self.__stacks[msg['id']].n_channels):
                is_ok = False
            else:
                try:
                    self._update_shape()
                except ValueError:
                    is_ok = False
            if not is_ok:
                self.drop_channel(*check_chan)


    def _handle_evt_stack_close(self, msg):
        """Event handler for `sconst.EVT_CLOSE`"""
        self.drop_stack(msg['id'])


    @property
    def stacks(self):
        with self.lock:
            return self.__stacks.copy()

    @property
    def channels(self):
        with self.lock:
            return self.__channels.copy()

    @property
    def channel_order(self):
        with self.lock:
            return self.__channel_order.copy()


