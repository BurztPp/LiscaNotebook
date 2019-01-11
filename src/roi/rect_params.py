import contextlib
import threading

from listener import Listeners


TYPE_SQUARE = 'square'
TYPE_RECT = 'rect'
MIN_ROI_SIZE = 1

class RectRoiParameters:

    def __init__(self, stack=None, props=None):
        self._listeners = Listeners()
        self.__lock = threading.RLock()
        self.__ongoing_transaction = 0
        self.__grid = {}

        self.__update_stack()
        self._offset_x = 0
        self._offset_y = 0
        self._width = 55
        self._height = 55
        self._pad_x = 82
        self._pad_y = 82
        self._pivot_x = 0
        self._pivot_y = 0
        self._angle = .5
        self._max_x = self.stack_width - 1
        self._max_y = self.stack_height - 1
        self._type_roi = TYPE_SQUARE
        if self._width != self._height or self._pad_x != self._pad_y:
            self._type_roi = TYPE_RECT

    def __update_stack(self, stack=None):
        with self.__lock:
            if stack is None:
                self.stack_width = 100
                self.stack_height = 100
            elif isinstance(stack, tuple):
                self.stack_width = stack[0];
                self.stack_height = stack[1];
            else:
                self.stack_width = stack.width
                self.stack_height = stack.height

    @property
    def stack_width(self):
        with self.__lock:
            return self._stack_width

    @stack_width.setter
    def stack_width(self, width):
        with self.__lock:
            if width != self._stack_width:
                self._stack_width = width
                self.max_x = self._stack_width - 1

    @property
    def stack_height(self):
        with self.__lock:
            return self._stack_height

    @stack_height.setter
    def stack_height(self, height):
        with self.__lock:
            if height != self._stack_height:
                self._stack_height = height
                self.max_y = self._stack_height - 1

    @property
    def max_x(self):
        with self.__lock:
            return self._max_x

    @max_x.setter
    def max_x(self, x):
        with self.__lock:
            if x != self._max_x:
                self._max_x = x
                self.update_grid()

    @property
    def max_y(self):
        with self.__lock:
            return self._max_y

    @max_y.setter
    def max_y(self, y):
        with self.__lock:
            if y != self._max_y:
                self._max_y = y
                self.update_grid()

    @property
    def offset_x(self):
        with self.__lock:
            return self._offset_x

    @offset_x.setter
    def offset_x(self, off_x):
        with self.__lock:
            if off_x != self._offset_x:
                self._offset_x = off_x
                self.update_grid()

    @property
    def offset_y(self):
        with self.__lock:
            return self._offset_y

    @offset_y.setter
    def offset_y(self, off_y):
        with self.__lock:
            if off_y != self._offset_y:
                self._offset_y = off_y
                self.update_grid()

    @property
    def pivot_x(self):
        with self.__lock:
            return self._pivot_x

    @pivot_x.setter
    def pivot_x(self, pivot_x):
        with self.__lock:
            if pivot_x != self._pivot_x:
                self._pivot_x = pivot_x
                self.update_grid()

    @property
    def pivot_y(self):
        with self.__lock:
            return self._pivot_y

    @pivot_y.setter
    def pivot_y(self, pivot_y):
        with self.__lock:
            if pivot_y != self._pivot_y:
                self._pivot_y = pivot_y
                self.update_grid()

    @property
    def width(self):
        with self.__lock:
            return self._width

    @width.setter
    def width(self, wid):
        with self.__lock:
            if wid < MIN_ROI_SIZE or wid == self._width:
                return
            self._width = wid
            if self.roi_type == TYPE_SQUARE:
                self._height = self._width
            self.update_grid()

    @property
    def height(self):
        with self.__lock:
            return self._height

    @height.setter
    def height(self, heig):
        with self.__lock:
            if heig < MIN_ROI_SIZE or heig == self._height:
                return
            self._height = heig
            if self.roi_type == TYPE_SQUARE:
                self._width = self._height
            self.update_grid()

    @property
    def pad_x(self):
        with self.__lock:
            return self._pad_x

    @pad_x.setter
    def pad_x(self, px):
        with self.__lock:
            if px < 0 or px == self._pad_x:
                return
            self._pad_x = px
            if self.roi_type == TYPE_SQUARE:
                self._pad_y = self._pad_x
            self.update_grid()

    @property
    def pad_y(self):
        with self.__lock:
            return self._pad_y

    @pad_y.setter
    def pad_y(self, py):
        with self.__lock:
            if py < 0 or py == self._pad_y:
                return
            self._pad_y = py
            if self.roi_type == TYPE_SQUARE:
                self._pad_x = self._pad_y
            self.update_grid()

    @property
    def angle(self):
        with self.__lock:
            return self._angle

    @angle.setter
    def angle(self, ang):
        with self.__lock:
            if ang != self._angle:
                self._angle = ang
                self.update_grid()

     @property
     def type_roi(self):
        with self.__lock:
            return self._type_roi

    @type_roi.setter
    def type_roi(self, type_):
        with self.__lock:
            if type_ == self._type_roi:
                return
            elif type_ != TYPE_RECT and type_ != TYPE_SQUARE:
                raise ValueError(f"Unknown type: {type_}")
            with self.transaction():
                if type_ == TYPE_SQUARE:
                    self._type_roi = TYPE_SQUARE
                    self.height = self._width
                    self.pad_y = self._pad_x
                else:
                    self._type_roi = TYPE_RECT


    def register_listener(self, fun):
        """Register a new function ``fun`` to be executed on change"""
        return self._listeners.register(fun)

    def delete_listener(self, lid):
        """Delete listener with ID ``lid``"""
        self._listeners.delete(lid)

    def _notify_listeners(self):
        """Execute listeners due to grid change"""
        self._listeners.notify()


    @contextlib.contextmanager
    def transaction(self):
        """Perform multiple changes in one transaction

        Use ``transaction`` as contextmanager (in a ``with`` block)
        to change multiple grid parameters and update the grid only
        once after all parameters have been changed.

        While the context is active, all grid updates are blocked.
        When the context is released, the grid is updated automatically.
        """
        with self.__lock:
            try:
                self.__ongoing_transaction += 1
                yield None
            finally:
                self.__ongoing_transaction -= 1
                self.update_grid()



    def update_grid(self):
        if self.__ongoing_transaction:
            return
        pass




def span_rois(width, height, pad_x, pad_y, max_x, max_y, angle=0, pivot_x=0, pivot_y=0, off_x=0, off_y=0, canvas=None):
    """Calculate the coordinates of the ROI grid sites.

    :param width: width (in pixels) of a ROI
    :type width: float
    :param height: height (in pixels) of a ROI
    :type height: float
    :param pad_x: distance (in pixels) between adjacent ROIs in x-direction
    :type pad_x: float
    :param pad_y: distance (in pixels) between adjacent ROIs in y-direction
    :type pad_y: float
    :param max_x: maximum x-coordinate (in pixels) of viewport/image on which to draw ROIs
    :type max_x: float
    :param max_y: maximum y-coordinate (in pixels) of viewport/image on which to draw ROIs
    :type max_y: float
    :param angle: angle (in degrees) by which to rotate the ROI grid
    :type angle: float
    :param pivot_x: x-coordinate (in pixels) of the rotation center and origin of the new coordinate system
    :type pivot_x: float
    :param pivot_y: y-coordinate (in pixels) of the rotation center and origin of the new coordinate system
    :type pivot_y: float
    :param off_x: offset (in pixels) in x-direction of the ROI grid from the origin of the new coordinate system
    :type off_x: float
    :param off_y: offset (in pixels) in y-direction of the ROI grid from the origin of the new coordinate system
    :type off_y: float
    :param canvas: (only for debugging) canvas for drawing debug information
    :type canvas: :py:class:`tkinter.Canvas`
    :return: the generated ROIs
    :rtype: list of 4-to-2 :py:class:`np.array`
    """
    # Set up function for ROI rotation
    trans_fun = make_transformation(angle, x_new=pivot_x, y_new=pivot_y)

    # Calculate limits for ROIs (corresponding to image size)
    limits = np.zeros([4,2])
    limits[(1,2),X] = max_x
    limits[(2,3),Y] = max_y
    limits = trans_fun(limits)
    limit_minX = limits[:,X].min()
    limit_maxX = limits[:,X].max()
    limit_minY = limits[:,Y].min()
    limit_maxY = limits[:,Y].max()

    # Get limits check function
    check_limit = make_limit_check(limits)

    # Get leftmost and uppermost ROI edge
    x_unit = pad_x + width
    y_unit = pad_y + height
    y0 = first_value(y_unit, limit_minY, off_y)
    x00 = first_value(x_unit, limit_minX, off_x)

    # Get unit vector coefficients
    n_y = round((y0 - off_y) / y_unit)
    is_start_y = True

    # Iterate over rows and columns
    rois = []
    while True:
        y1 = y0 + height
        if y1 > limit_maxY:
            break
        x0 = x00
        while True:
            x1 = x0 + width
            if x1 > limit_maxX:
                break
            if check_limit(x0, x1, y0, y1):
                # Add roi to list
                roi = np.array([[x0,y0],[x1,y0],[x1,y1],[x0,y1]])
                roi = trans_fun(roi, inverse=True)
                rois.append(roi)
            x0 += x_unit
        y0 += y_unit

    return rois



def first_value(unit, limit=0., offset=0.):
    """Calculate a first value for grid construction.

    :param unit: a unit length of the grid
    :type unit: float
    :param limit: the minimum value for grid sites
    :type limit: float
    :param offset: grid offset w.r.t. origin
    :type offset: float
    :return: Minimum allowed grid site
    :rtype: float

    The returned value is the smallest grid site larger or equal to
    ``limit``. The grid is shifted by ``offset``. Only the modulus
    ``offset % unit`` is considered; larger values of ``offset``
    are ignored.
    """
    # Get offset (with absolute value less than `unit`)
    if abs(offset) >= unit:
        offset = offset % unit
    offset_left = offset - unit
    offset_right = offset

    # Get multiple of `unit` next larger to `limit`
    m_limit = limit // unit
    if m_limit < 0:
        m_limit += 1
    first_val = m_limit * unit

    # Apply offset
    if limit - first_val <= offset_left:
        first_val += offset_left
    else:
        first_val += offset_right

    return first_val


def last_value(unit, limit=0., offset=0.):
    #TODO add 'size'
    """Calculate a last value for grid construction.

    :param unit: a unit length of the grid
    :type unit: float
    :param limit: the minimum value for grid sites
    :type limit: float
    :param offset: grid offset w.r.t. origin
    :type offset: float
    :return: Minimum allowed grid site
    :rtype: float

    The returned value is the largest grid site smaller or equal to
    ``limit``. The grid is shifted by ``offset``. Only the modulus
    ``offset % unit`` is considered; larger values of ``offset``
    are ignored.
    """
    # Get offset (with absolute value less than `unit`)
    if abs(offset) >= unit:
        offset = offset % unit
    offset_left = offset - unit
    offset_right = offset

    # Get multiple of `unit` next larger to `limit`
    m_limit = limit // unit
    if m_limit < 0:
        m_limit += 1
    last_val = m_limit * unit

    # Apply offset
    if limit - last_val <= offset_left:
        last_val += offset_left
    else:
        last_val += offset_right

    return last_val

