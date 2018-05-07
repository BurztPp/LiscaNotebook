"""
.. py:module:: modules
    :synopsis: The module management

.. moduleauthor:: Daniel Woschée <daniel.woschee@physik.lmu.de>

This is the docstring of the :py:mod:`modules` module.
"""
import importlib.util as imputil
from listener import Listeners
import os
import random
import string
import sys
import threading
import traceback
import warnings


PERFORM_KINDS = {"conf", "run", "loop_next", "loop_finished"}
RETURN_KINDS = {"init", *PERFORM_KINDS}
LISTENER_KINDS = {"order", "dependency", "workflow"}


def _load_module(name, path, return_init_ret=True):
    """
    Load and register a given module.

    :param name: the name of the module
    :type name: str
    :param path: the path to the module file
    :type path: str
    :param return_init_ret: flag whether to return also the return value of the ``register`` function
    :type return_init_ret: bool

    For loading a package, give the path of the package’s
    ``__init__.py`` file as path.

    :return: Metadata of the module, or ``None`` if module couldn’t be loaded. If ``return_init_ret`` is ``True``, a tuple of module metadata and ``register`` return value is returned.
    """
    if return_init_ret:
        RETURN_BAD = (None, None)
    else:
        RETURN_BAD = None

    # Load the module
    spec = imputil.spec_from_file_location(name, path)
    if spec is None:
        return RETURN_BAD
    mod = imputil.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        print("Cannot load module '{}' from '{}':\n{}: {}".format(name, path, e.__class__.__name__, e), file=sys.stderr)
        return RETURN_BAD

    # Check if module is valid (has `register` function)
    if not hasattr(mod, 'register'):
        print("Ignoring invalid plugin {} at {}:\nNo 'register' function found.".format(name, path), file=sys.stderr)
        return RETURN_BAD

    # Register the module
    meta = ModuleMetadata(mod)

    # First, pre-fill auto-detected version and `conf` and `run` function
    if hasattr(mod, '__version__'):
        meta.version = mod.__version__
    if hasattr(mod, 'configure'):
        meta.set_fun("conf", mod.configure)
    if hasattr(mod, 'run'):
        meta.set_fun("run", mod.run)
    
    # Second, let module fill in its own properties
    try:
        init_ret = mod.register(meta)
    except Exception as e:
        print("\nIgnore module '{}' due to exception:".format(name),
                file=sys.stderr, end='')
        _print_exception_string(e)
        return RETURN_BAD

    # Check meta data
    meta_check_failed = meta.check()
    if meta_check_failed:
        print("Ignoring invalid plugin {} at {}:\n{}".format(name, path, meta_check_failed), file=sys.stderr)
        return RETURN_BAD

    # Memorize return data of kind "init"
    if init_ret is not None:
        meta.set_ret("init", tuple(init_ret.keys()))

    # Return
    if return_init_ret:
        return meta, init_ret
    return meta


def _search_modules(plugins_path):
    """Find modules to be loaded."""
    modules = set()

    # Search plugins directory for plugins
    for f in os.listdir(plugins_path):
        # Ignore files starting with a dot
        if f.startswith(('.', '_')):
            continue

        # Get file parts and full path
        name, ext = os.path.splitext(f)
        fp = os.path.join(plugins_path, f)

        # Check for valid module (or package) name
        isValid = False
        if os.path.isdir(fp) and os.path.isfile(os.path.join(fp, '__init__.py')):
            # The path is a package
            fp = os.path.join(fp, '__init__.py')
            isValid = True

        elif ext.startswith('.py') and (len(ext) == 3 or (len(ext) == 4 and ext[-1] in 'co')):
            # The path is a module
            isValid = True

        # Skip invalid file names
        if not isValid:
            continue

        # Add file to list of potential modules
        modules.add((name, fp))
    return modules


def _parse_version(ver, isComparison=False):
    """
    Parse a version string.

    The version string should consist of numbers
    separated by dots, e.g. "1.0.2", "2", or "3".
    Different versions of a plugin should have different version
    strings such that the version string of the newer version is
    the larger operand in version comparison.

    For version comparison, the string will be split at the dots,
    and the resulting substrings will be compared beginning with
    the first using python’s default comparison operators.
    Multiple consecutive dots are ignored.

    An empty version can also be specified by ``None``, and a version
    consisting of a single number can also be specified as a
    positive integer number.

    The version is returned as a tuple of strings, as an empty tuple
    for an unspecified version or as ``None`` for an invalid argument.

    :param ver: the version string
    :type ver: str
    :param isComparison: boolean flag whether ver is a comparison
    :type isComparison: bool

    :return: A tuple of subversion strings, obtained by splitting
        the version string at dots.

        If ``isComparison`` is ``True``, the comparison mode is returned
        before the tuple of subversion strings.
        The comparison mode is one of the following strings:

        ``>=``, ``<=``, ``!=``, ``>``, ``<``, ``=``
    """
    # Catch special cases
    if ver is None or ver is () or ver is '':
        return (None, ()) if isComparison else ()
    elif isinstance(ver, int) and ver >= 0:
        ver = str(ver)
        #return ((str(ver),)
    elif not isinstance(ver, str):
        return None

    # Parse version string
    # TODO: add optional dependency ('?')
    comp_flags = ('>=', '<=', '!=', '>', '<', '=')
    #starts_with_comparison = ver.startswith(comp_flags)
    if isComparison:
        if ver[:2] in comp_flags:
            comp_mode = ver[:2]
            ver = ver[2:]
        elif ver[0] in comp_flags:
            comp_mode = ver[0]
            ver = ver[1:]
        else:
            comp_mode = '='

    # Split version string into subversions
    ver = tuple([v for v in ver.split('.') if v])

    if isComparison:
        return comp_mode, ver
    else:
        return ver


def _check_versions(version_present, comp_mode, version_required):
    """
    Check if a version fulfills a version requirement.

    TODO: possibly wrong results for subversionstrings
    with different lengths

    :param version_present: The version of the plugin to be evaluated
    :param comp_mode: The comparison mode
    :param version_required: The required version

    :return: ``True`` if version fulfills requirement, else ``False``.
    """
    # TODO: correct for strings with different lengths
    # TODO: add optional dependency ('?')
    if not version_present and not version_required:
        return True

    elif comp_mode == '>=':
        for vp, vr in zip(version_present, version_required):
            if vp < vr:
                return False
        if len(version_present) < len(version_required):
            return False
        return True

    elif comp_mode == '<=':
        for vp, vr in zip(version_present, version_required):
            if vp > vr:
                return False
        if len(version_present) > len(version_required):
            return False
        return True

    elif comp_mode == '!=':
        for vp, vr in zip(version_present, version_required):
            if vp != vr:
                return True
        if len(version_present) == len(version_required):
            return False
        return True

    elif comp_mode == '>':
        for vp, vr in zip(version_present, version_required):
            if vp > vr:
                return True
            elif vp < vr:
                return False
        if len(version_present) > len(version_required):
            return True
        return False

    elif comp_mode == '<':
        for vp, vr in zip(version_present, version_required):
            if vp < vr:
                return True
            elif vp < vr:
                return False
        if len(version_present) < len(version_required):
            return True
        return False

    elif comp_mode == '=':
        if len(version_present) != len(version_required):
            return False
        for vp, vr in zip(version_present, version_required):
            if vp != vr:
                return False
        return True

    # This is never reached for a valid comp_mode
    return False


def _parse_dep(dep):
    """
    Parse the dependency data inserted by the plugin.
    
    :param dep: The dependency data provided by the plugin
    :return: A (possibly empty) tuple of dependencies,
        or ``None`` if dependency data is invalid

    The expected dependency data is::

        [tuple of] tuple of ("id", [tuple of] ("conf_ret" | "run_ret"), [tuple of] [(<, >) [=]] "version" )
    """
    # Expects:
    # [tuple of] tuple of ("id", [tuple of] ("conf_ret" | "run_ret"), [tuple of] [(<, >) [=]] "version" )
    # Returns:
    # tuple of (tuple of ("id", tuple of ("conf_ret" | "run_ret"), tuple of (<cmp_mode>, "version") ))
    # Returns None if input is invalid

    # No dependencies
    if not dep:
        return ()

    # Depending on only one module; convert to tuple
    if isinstance(dep[0], str):
        dep = (dep,)

    # Write all dependencies to standardized structure
    new = []
    isValid = True
    for d in dep:
        n = [None, None, None]
        try:
            # "id" is a string
            n[0] = d[0]

            # "conf_ret" is a string or an iterable of strings
            if isinstance(d[1], str):
                n[1] = (d[1],)
            else:
                n[1] = d[1]

            # "version" is a string or a tuple of strings
            if len(d) > 2:
                if isinstance(d[2], str):
                    versions = (d[2],)
                else:
                    versions = d[2]
                new_versions = []
                for ver in versions:
                    cmp_mode, ver_nr = _parse_version(ver, True)
                    if cmp_mode and ver_nr:
                        new_versions.append((cmp_mode, ver_nr))
                n[2] = tuple(new_versions)
            else:
                n[2] = ()

            # Finally, append the dependency to the list
            new.append(tuple(n))

        except Exception:
            return None

    return tuple(new)


def _print_exception_string(exc, first=0):
    """
    Obtain and print a stacktrace and exception info.

    :param exc: The exception that has been raised
    :type exc: :py:class:`Exception`
    :param first: The first index of the exception traceback to show
    :type first: uint
    """
    stack = traceback.extract_tb(exc.__traceback__)[first:]
    stack_formatted = traceback.format_list(stack)
    msg = "\nTraceback (most recent call last):\n{}{}: {}".format(
            ''.join(stack_formatted), exc.__class__.__name__, exc)
    print(msg, file=sys.stderr)


class ModuleManager:
    """
    Provides means for managing plugins.
    """

    def __init__(self, plugins_path=None, register_builtins=True):
        """
        Set up a new ModuleManager instance.

        Plugins will be searched in the given path.
        By default, the builtin modules are also imported.

        :param plugins_path: The directory in which plugins are searched
        :param register_builtins: Boolean flag whether to import builtin modules
        """
        self.modules = {}
        self.data = [{}]
        self.module_order = ModuleOrder()
        self._listeners = Listeners(kinds=LISTENER_KINDS)
        self.data_lock = threading.RLock()
        self.order_lock = threading.RLock()
        self.run_lock = threading.Lock()

        # Register built-in modules
        if register_builtins:
            self.register_builtins()

        # Register custom plugin modules
        if plugins_path is not None:
            modules_found = _search_modules(plugins_path)
            for name, path in modules_found:
                meta, init_ret = _load_module(name, path)
                if meta is not None:
                    mod_id = meta.id
                    self.modules[mod_id] = meta
                    self.data[0][mod_id] = {}
                    self.memorize_result(mod_id, init_ret)


    def show(self):
        """Print ``self.modules``. Only for debugging."""
        print(self.modules)


    def set_module_order(self, order):
        """
        Set the execution order of the modules.
        
        This method is thread-safe.
        """
        with self.order_lock:
            self.module_order.set(order)
            self._listeners.notify("order")


    def module_order_insert(self, mod, index=-1):
        """
        Insert one module or a loop into the order.
        
        This method is thread-safe.
        """
        with self.order_lock:
            self.module_order[index] = mod
            self._listeners.notify("order")


    def get_module_at_index(self, idx):
        """
        Get the module at a given index or None in case of error.
        """
        if idx is None:
            return None
        elif type(idx) == int:
            idx = [idx,]
        elif not idx:
            return None
        with self.order_lock:
            return self.module_order[idx]


    def check_module_dependencies(self, idx):
        """
        Check if the dependencies for a module are fulfilled.

        A thread-safe check is performed whether "run" dependencies are fulfilled
        and whether "conf" return data is present.

        TODO: Implement loops
        TODO: Check for version conflicts

        :param idx: the index of the module for which to check the dependency
        :type idx: int or tuple of int
        """
        raise NotImplementedError
        if type(idx) == int:
            idx = (idx,)

        mod = self.get_module_at_index(idx)
        mod_id = mod.id

        # Check if "conf" has been run already (if return data is present)
        conf_ret = set()
        if mod.has_fun("conf"):
            with self.data_lock:
                for cret_data in mod.get_ret("conf"):
                    if mod_id not in self.data[0] or cret_data not in self.data[0][mod_id]:
                        conf_ret.add(cret_data)
        # If `conf_ret` is now non-empty, the "conf" function needs to be run.

        # Collect names of "run" dependencies (to see if "run" can be invoked)
        deps = {}
        if mod.has_fun("run"):
            for dep_id, dep_data, _ in mod.get_dep("run"):
                if not dep_id in deps:
                    deps[dep_id] = set()
                deps[dep_id].update(dep_data)

        # Filter out data that is visible to the module
        with self.order_lock:
            iidx = idx
            while len(iidx) > 0:
                pass
                #while 
                    
        # CONTINUE here

        with self.data_lock:
            pass
            

    def module_order_move(self, idx_old, idx_new):
        """
        Move a module in the order

        Move the module at order index ``idx_old`` to ``idx_new``.
        This method is thread-safe.
        """
        with self.order_lock:
            self.module_order.move(idx_old, idx_new)
            
            self._listeners.notify("order")


    def module_order_remove(self, index):
        """
        Remove the module or loop at the given index from the module order.

        This method is thread-safe.
        
        :param index: Index of item to be removed.
        :type index: int or list of int
        """
        with self.order_lock:
            del self.module_order[index]
            self._listeners.notify("order")


    def list_display(self, category=None):
        """
        Return a list of modules for displaying.
        
        This method is thread-safe.
        """
        with self.order_lock:
            return [{'name': m.name, 'id': m.id, 'category': m.category, 'version': '.'.join(m.version)} for _, m in self.modules.items() if m.name != '']


    def is_workflow_running(self):
        """Return True if workflow is running, else False."""
        if self.run_lock.acquire(False):
            self.run_lock.release()
            return False
        else:
            return True


    def invoke_workflow(self):
        """
        Invoke the workflow in a new thread.

        The workflow can only be run once at a time; any trial to
        invoke workflow execution while another instance of
        workflow execution is running will fail.
        """
        thread = threading.Thread(target=self._lock_run_workflow)
        thread.start()
        print("new thread started")


    def _lock_run_workflow(self):
        """Acquire locks for workflow execution."""
        if self.run_lock.acquire(False):
            try:
                self._listeners.notify("workflow")
                with self.order_lock:
                    with self.data_lock:
                        self._run_workflow()
            finally:
                self.run_lock.release()
                self._listeners.notify("workflow")
        else:
            print("Cannot start analysis: seems to be running already.", file=sys.stderr)


    def _run_workflow(self):
        """Execute the workflow from the module order."""
        # TODO: support loops
        print("Running workflow …")
        for mod_id in self.module_order:
            self.module_perform(mod_id, "run")

        print("Workflow finished.")


    def memorize_result(self, mod_id, result):
        """
        Add a result to the internal data memory.
        
        This method is thread-safe.
        """
        # TODO: add test for consistency with metadata
        if result is None:
            return

        with self.data_lock:
            for name, value in result.items():
                self._add_data(mod_id, name, value)


    def acquire_dependencies(self, mod_id, kind):
        """
        Acquire the dependencies for executing a plugin.

        This method is thread-safe.

        :param mod_id: The id of the plugin to be executed
        :type mod_id: str
        :param kind: Indicator what dependency is needed; one of: "conf", "run", "loop_next", "loop_end".
        :type kind: str
        :return:
            * Dictionary {DP: {DN: DV}}, where:

                * the keys DP are the identifiers of the plugins whose return values are required,
                * the sub-keys DN are the names of the required data values,
                * the sub-values DV are the actual data values, and
                * the empty string as a special sub-key DN has the present version of the corresponding plugin as sub-value DV.

            * ``None`` if a dependency requirement cannot be fulfilled
        """
        with self.data_lock:
            mod = self.modules[mod_id]
            mod_ver = mod.version
            dep_list = mod.get_dep(kind)

            # DEBUG message
            #print("[MouleManager.acquire_dependencies] dependency list: {}".format(str(dep_list)))

            if len(dep_list) == 0:
                return {}

            data = {}
            for dep_id, dep_names, dep_ver_req in dep_list:
                # Check if versions match
                if dep_id != "":
                    dep_ver = _parse_version(self.modules[dep_id].version)
                    cmp_mode, dep_ver_req = _parse_version(dep_ver_req, True)
                    if not _check_versions(dep_ver_req, cmp_mode, dep_ver):
                        print("Version mismatch for dependency '{}' of module '{}': found version {} of '{}', but require {}.".format(kind, mod_id, dep_ver, dep_id, dep_ver_req), file=sys.stderr)
                        return None
                else:
                    dep_ver = ()

                # Check if data is available
                if dep_id not in data:
                    dep_data = {'': dep_ver}
                    data[dep_id] = dep_data
                else:
                    dep_data = data[dep_id]

                for name in dep_names:
                    for d in reversed(self.data):
                        dm = d.get(dep_id)
                        if dm is None:
                            continue

                        dmn = dm.get(name)
                        if dmn is None:
                            continue
                        else:
                            dep_data[name] = dmn
                            break
                    else:
                        print("Missing dependency '{}' of plugin '{}': did not find required data '{}' of plugin '{}'.".format(kind, mod_id, name, dep_id), file=sys.stderr)
                        return None

            return data


    def module_perform(self, mod_id, kind):
        """
        Call a function of the module.

        This method is thread-safe with respect to module order.

        :param mod_id: The ID of the module to be called
        :type mod_id: str
        :param kind: The kind of function to be called; eiter "conf" or "run", "loop_next", "loop_end".
        :type kind: str
        """
        # Check if function kind is legal
        if kind != "conf" and kind != "run":
            print("Cannot call function '{}': only 'conf' and 'run' functions can be called directly.".format(kind), file=sys.stderr)
            return

        # Check if function exists
        m = self.modules[mod_id]
        if not m.has_fun(kind):
            print("Cannot call function '{}' of module '{}': function not found.".format(kind, mod_id), file=sys.stderr)
            return

        # Lock order
        with self.order_lock:
            # Get dependencies of function
            dep_data = self.acquire_dependencies(mod_id, kind)
            if dep_data is None:
                print("Cannot call function '{}' of module '{}': dependencies not fulfilled.".format(kind, mod_id), file=sys.stderr)
                return

            # Call the function
            try:
                res = m.call_fun(kind, dep_data)
            except Exception as e:
                _print_exception_string(e, 1)
                return

            # If module is configured, memorize its result and return
            if kind == "conf":
                self.memorize_result(mod_id, res)
                return

            # If this is reached, we have performed the "run" function.
            # Check if the module contains a loop.
            # If not, memorize result and return.
            if m.has_fun("loop_next"):
                self.data.append({})
                self.memorize_result(mod_id, res)
            else:
                self.memorize_result(mod_id, res)
                return

            # Run the loop body
            try:
                while True:
                   # TODO: insert loop body calls here
                   dep_data = self.acquire_dependencies(mod_id, "loop_next")
                   res = m.call_fun("loop_next", dep_data)
                   self.memorize_result(mod_id, res)
            except StopIteration:
                pass
            except Exception as e:
                _print_exception_string(e, 1)
                del self.data[-1]
                return
            
            # Call the loop clean-up function, if given
            if m.has_fun("loop_end"):
                dep_data = self.acquire_dependencies(mod_id, "loop_end")
                try:
                    res = m.call_fun("loop_end", dep_data)
                except Exception as e:
                    _print_exception_string(e, 1)
                    return

                del self.data[-1]
                self.memorize_result(mod_id, res)
            else:
                del self.data[-1]


    def _add_data(self, d_id, name, value, index=-1):
        """
        Add data to the internal data memory.

        This method is thread-safe.

        :param d_id: The id of the plugin providing the data
        :param name: The name of the data
        :param value: The value of the data
        :param index: The index of `self.data` to which to write the data
        """
        with self.data_lock:
            if d_id not in self.data[index]:
                self.data[index][d_id] = {}
            self.data[index][d_id][name] = value


    def register_builtin_data(self, name, value):
        """
        Register built-in data.

        :meth:`register_builtin_data` can be used to add data as built-in
        data. They will be available using an empty string as id.

        :param name: The name of the data
        :param value: The value of the data
        """
        self._add_data("", name, value, index=0)


    def register_builtins(self):
        # TODO
        pass


    def register_listener(self, fun, kind=None):
        """
        Register a listener that will be notified on changes.

        :param fun: The function to be called on change, will be called without parameters
        :type fun: function handle
        :param kind: The kind of events when the function will be called
        :type kind: None, str or iterable containing strings

        The possible kinds are: "order".
        When kind is None, fun will be called by all of these events.

        A listener ID is returned that can be used to delete the listener.
        If the registration was not successful, None is returned.

        Note that if ``fun`` raises an exception, it will not be called anymore.

        :return: a listener ID or None
        :rtype: str or None
        """
        self._listeners.register(fun, kind)

    def delete_listener(self, lid):
        """Delete the listener with ID ``lid``"""
        self._listeners.delete(lid)



class ModuleMetadata:
    """
    Defines the metadata of a module.
    """
    def __init__(self, module=None):
        self.__vals = {}
        self.__vals["name"] = None
        self.__vals["id"] = None
        self.__vals["version"] = ()
        self.__vals["category"] = ()
        self.__vals["group"] = ()
        self.__vals["dep"] = {}
        self.__vals["ret"] = {}
        self.__vals["fun"] = {}
        self.__module = module
        self.__lock = threading.RLock()


    # "name"
    # str
    # A human-readable name. Used for
    # identifying the module in a list.
    @property
    def name(self):
        with self.__lock:
            return self.__vals["name"]
    @name.setter
    def name(self, name):
        with self.__lock:
            self.__vals["name"] = name


    # "id"
    # str
    # A unique module name. Only for internal identification
    # of the module. If several modules use the same id,
    # the latest defined module overwrites all others.
    @property
    def id(self):
        with self.__lock:
            return self.__vals["id"]
    @id.setter
    def id(self, id_):
        with self.__lock:
            self.__vals["id"] = id_


    # "version"
    # str
    # Version of the module. Arbitrarily many subversion
    # numbers may be appended after a dot. Comparison of
    # versions is done using python’s comparison operators,
    # wherein older versions are smaller than newer versions.
    @property
    def version_string(self):
        with self.__lock:
            if self.version is None:
                return None
            return '.'.join(self.__vals["version"])
    @property
    def version(self):
        with self.__lock:
            return self.__vals["version"]
    @version.setter
    def version(self, ver):
        with self.__lock:
            self.__vals["version"] = _parse_version(ver)


    # "category"
    # [tuple of] str
    # One or more human-readable categories of the module.
    # Used in the module selection menu for grouping modules.
    @property
    def category(self):
        with self.__lock:
            return self.__vals["category"]
    @category.setter
    def category(self, cat):
        self.__set_tuple_of_str(cat, "category")


    # "group"
    # [tuple of] "id"
    # One or more "id"s of meta-modules the module belongs to.
    # A meta-module is a placeholder for any module belonging to it.
    # A meta-module must have its own name in "group".
    @property
    def group(self):
        with self.__lock:
            return self.__vals["group"]
    @group.setter
    def group(self, grp):
        self.__set_tuple_of_str(grp, "group")


    # "conf_dep"
    # [tuple of] tuple of ("id", [tuple of] "conf_ret", [tuple of] [(<, >) [=]] "version")
    # Dependencies of the module configuration function.
    @property
    def conf_dep(self):
        return self.get_dep("conf")
    @conf_dep.setter
    def conf_dep(self, dep):
        self.set_dep("conf", dep)


    # "run_dep"
    # [tuple of] tuple of ("id", [tuple of] "ret", [tuple of] [(<, >) [=]] "version")
    # Dependencies of the module run function.
    @property
    def run_dep(self):
        return self.get_dep("run")
    @run_dep.setter
    def run_dep(self, dep):
        self.set_dep("run", dep)


    # "dep"
    # [tuple of] tuple of ("id", [tuple of] "ret", [tuple of] [(<, >) [=]] "version")
    # Dependencies of the module function indicated by `kind`.
    def set_dep(self, kind, dep):
        # Check for bad kind
        if kind not in PERFORM_KINDS:
            print("Cannot set dependency: bad kind: {}".format(kind), file=sys.stderr)
            return

        # Parse dependency
        dep = _parse_dep(dep)

        # Check for bad dependency
        if dep is None:
            print("Cannot set dependency '{}' of plugin '{}': bad dependency given.".format(kind, self.id), file=sys.stderr)
            return

        with self.__lock:
            # Check if overwriting (print warning)
            if kind in self.__vals["dep"]:
                print("Warning: overwriting dependency '{}' of plugin '{}'".format(kind, self.id), file=sys.stderr)

            # Set dependency
            self.__vals["dep"][kind] = dep

    def get_dep(self, kind):
        if kind not in PERFORM_KINDS:
            return None

        with self.__lock:
            return self.__vals["dep"].get(kind, ())


    # "conf_ret"
    # [tuple of] str
    # Identifier for data generated by the configuration function of
    # the module. Used by other modules for defining dependencies on
    # specific data for their configuration functions.
    @property
    def conf_ret(self):
        self.get_ret("conf")
    @conf_ret.setter
    def conf_ret(self, ret):
        self.set_ret("conf", ret)


    # "run_ret"
    # [tuple of] str
    # Identifier for data generated by the run function of
    # the module. Used by other modules for defining dependencies on
    # specific data for their run functions.
    @property
    def run_ret(self):
        return self.get_ret("run")
    @run_ret.setter
    def run_ret(self, ret):
        self.set_ret("run", ret)


    # "ret"
    # [tuple of] str
    # Identifier for data generated by a function of the module.
    # Used by other modules for defining dependencies on
    # specific data for their functions.
    def set_ret(self, kind, ret):
        if kind not in RETURN_KINDS:
            print("Cannot set return data: bad kind: {}".format(kind), file=sys.stderr)
            return
        self.__set_tuple_of_str(ret, "ret", kind)

    def get_ret(self, kind):
        if kind not in RETURN_KINDS:
            return None

        with self.__lock:
            return self.__vals["ret"].get(kind, ())


    # "fun"
    # dict of functions
    # The functions that can be performed by this module.
    # The key must be an entry of `PERFORM_KINDS`.
    def set_fun(self, kind, fun):
        if kind not in PERFORM_KINDS:
            print("Cannot set function: bad kind: {}".format(kind, file=sys.stderr))
            return

        with self.__lock:
            self.__vals["fun"][kind] = fun

    def get_fun(self, kind):
        if kind not in PERFORM_KINDS:
            return None

        with self.__lock:
            return self.__vals["fun"].get(kind)

    def has_fun(self, kind):
        with self.__lock:
            return kind in self.__vals["fun"]

    def call_fun(self, kind, *args, **kwargs):
        with self.__lock:
            fun = self.__vals["fun"].get(kind)
            if fun is None:
                return None
            return fun(*args, **kwargs)


    # "module"
    # module
    # Reference to the actual module; usually set by the
    # module management system.
    @property
    def module(self):
        with self.__lock:
            return self.__module
    @module.setter
    def module(self, mod):
        with self.__lock:
            self.__module = mod


    def check(self):
        """
        Check all metadata values and return a string describing all
        errors in the metadata, or None if no errors found.
        """
        msg = []

        with self.__lock:
            # Check values
            if not self.name or not isinstance(self.name, str):
                msg.append("The plugin name must be a non-empty string.")
            if not self.id or not isinstance(self.id, str):
                msg.append("The plugin id must be a non-empty string.")
            if not isinstance(self.version, tuple):
                msg.append("The plugin version must be a tuple of strings or an empty tuple.")


        # Assemble message string and return it
        if len(msg) > 0:
            msg = '\n'.join(msg)
        else:
            msg = None
        return msg


    def __set_tuple_of_str(self, x, *names):
        """
        Write string or tuple of strings in return data dict.

        The result will always be an empty tuple or a
        tuple of strings. In case of invalid `x`, a
        warning is emitted and the value is not changed.
        'None' always clears the value to an empty tuple.

        `names` is a list of keys for recursively indexing
        into `self.__vals`.
        """
        if isinstance(x, str):
            x = (x,)
        elif isinstance(x, tuple) and all([isinstance(i, str) for i in x]):
            pass
        elif cat is None:
            x = ()
        else:
            warnings.warn('Invalid "{}": {}'.format(names, str(x)))
            return

        with self.__lock:
            if len(names) == 1:
                self.__vals[names[0]] = x
            elif len(names) == 2:
                self.__vals[names[0]][names[1]] = x


class ModuleOrder:
    """
    A class for providing module order operations.
    """
    def __init__(self, order=None, lock=None):
        self._len_cache = None
        if lock is None:
            self.lock = threading.RLock()
        elif type(lock) == threading.RLock():
            self.lock = lock
        else:
            raise TypeError("Bad lock type given.")

        if order is None:
            self.order = []
            self._len_cache = 0
        elif type(order) == list:
            self.order = order
        else:
            raise TypeError("Bad module order type given.")


    def __bool__(self):
        return bool(self.order)


    def __iter__(self):
        index = [0]
        while index:
            try:
                o = self[index]
            except IndexError:
                index.pop()
                continue
            if type(o) == str:
                yield o
            else:
                index.append(0)
                continue
            index[-1] += 1
        return


    def __len__(self):
        if self._len_cache is not None:
            return self._len_cache
        l = 0
        with self.lock:
            for x in self.__iter__():
                l += 1
                print(x)
            self._len_cache = l
        return l

    def _check_key_valid(self, key):
        if type(key) == int:
            key = [key,]
        elif type(key) == tuple or type(key) == list:
            if not key or any(type(i) != int for i in key):
                raise TypeError("Index must be a non-empty list of integers.")
            elif type(key) == tuple:
                key = list(key)
        else:
            raise TypeError("Bad type of index: '{}'.".format(type(key)))
        return key

    def __getitem__(self, key):
        key = self._check_key_valid(key)
        with self.lock:
            o = self.order
            for i in key:
                try:
                    o = o[i]
                except IndexError:
                    pos = len(self.order) - len(o)
                    raise IndexError("Module order index out ouf range at index position {} of index '{}'.".format(pos, str(key)))
            return o


    def __setitem__(self, key, mod_id):
        key = self._check_key_valid(key)
        isLoop = len(key) > 1 and key[-1] == 0
        with self.lock:
            o = self.order
            while key:
                i = key.pop(0)
                if i == -1:
                    i = len(o)
                if isLoop and len(key) == 1:
                    # New loop
                    o.insert(i, [mod_id])
                    if self._len_cache is not None:
                        self._len_cache += 1
                    break
                elif len(key) > 0:
                    o = o[i]
                else:
                    if i > len(o):
                        raise IndexError("Cannot insert item: index too large")
                    o.insert(i, mod_id)
                    if self._len_cache is not None:
                        self._len_cache += 1


    def __delitem__(self, key):
        key = self._check_key_valid(key)
        isLoop = len(key) > 1 and key[-1] == 0
        with self.lock:
            o = self.order
            while key:
                i = key.pop(0)
                if isLoop and len(key) == 1:
                    del o[i]
                    self._len_cache = None
                    break
                elif len(key) > 0:
                    o = o[i]
                else:
                    if type(o[i]) == str:
                        self._len_cache -= 1
                    else:
                        self._len_cache = None
                    del o[i]


    def set(self, order):
        """
        Set the execution order of the modules.
        """
        with self.lock:
            new_order = []
            for o in order:
                i = self._parse_module_insertion(o)
                if i is None:
                    return
                new_order.append(i)
            self.order = new_order
            self._len_cache = None


    def move(self, idx_old, idx_new):
        """
        Move a module in the order

        Move the module at order index ``idx_old`` to ``idx_new``.
        """
        with self.lock:
            order = self.order
            if type(idx_old) != int and type(idx_new) != int:
                if len(idx_old) != len(idx_new):
                    return
                while len(idx_old) > 1:
                    i_o = idx_old.pop(0)
                    i_n = idx_new.pop(0)
                    if i_o != i_n:
                        return
                    order = order[i_o]
                idx_old = i_0
                idx_new = i_n
            if idx_new == -1:
                idx_new = len(order) - 1
            mod = order.pop(idx_old)
            order.insert(idx_new, mod)


    def _parse_insertion(self, ins):
        """
        Check module insertion.

        This method is not thread-safe and must only be called from
        thread-safe functions.
        """
        # If `ins` is a string, return it
        if type(ins) == str:
            return ins

        # If `ins` is None, return None, because None indicates an
        # error during parsing `ins` in a higher parsing instance.
        # Do not print a message, because the message is printed
        # by the instance that encountered the error.
        if ins is None:
            return None

        # If `ins` is not a string, it must be a list representing a loop
        pins = []

        # Check if first loop entry is the “embracing member”
        if type(ins[0]) != str:
            print("Cannot insert new module: embracing member missing in loop", file=sys.stderr)
            return None

        # Check for empty list
        if not ins:
            print("Cannot insert new module: illegal empty list encountered.", file=sys.stderr)
            return None

        # Add all remaining items to the list
        for i in ins:
            if type(i) != str:
                i = self._parse_module_insertion(i)
                if i is None:
                    return None
            pins.append(i)

        # Return parsed insertion item
        return pins

