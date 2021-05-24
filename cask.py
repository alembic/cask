#-******************************************************************************
#
# Copyright (c) 2012-2021,
#  Sony Pictures Imageworks Inc. and
#  Industrial Light & Magic, a division of Lucasfilm Entertainment Company Ltd.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# *       Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# *       Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
# *       Neither the name of Sony Pictures Imageworks, nor
# Industrial Light & Magic, nor the names of their contributors may be used
# to endorse or promote products derived from this software without specific
# prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#-******************************************************************************

from __future__ import print_function
__doc__ = """
Cask is a high level convenience wrapper for the Alembic Python API. It blurs
the lines between Alembic "I" and "O" objects and properties, abstracting both
into a single class object. It also wraps up a number of lower-level functions
into high level convenience methods.

More information can be found at http://docs.alembic.io/python/cask.html
"""
__version__ = "1.2.0"

import os
import re
import imath
import ctypes
import weakref
import alembic
from functools import wraps

_string_types = (type(u""), type(b""))

# maps cask objects to Alembic IObjects
IOBJECTS = {
    "Camera": alembic.AbcGeom.ICamera,
    "Collections": alembic.AbcCollection.ICollections,
    "Curve": alembic.AbcGeom.ICurves,
    "FaceSet": alembic.AbcGeom.IFaceSet,
    "Light": alembic.AbcGeom.ILight,
    "Material": alembic.AbcMaterial.IMaterial,
    "NuPatch": alembic.AbcGeom.INuPatch,
    "Points": alembic.AbcGeom.IPoints,
    "PolyMesh": alembic.AbcGeom.IPolyMesh,
    "SubD": alembic.AbcGeom.ISubD,
    "Xform": alembic.AbcGeom.IXform,
}

# maps cask objects to Alembic OObjects
OOBJECTS = {
    "Camera": alembic.AbcGeom.OCamera,
    "Collections": alembic.AbcCollection.OCollections,
    "Curve": alembic.AbcGeom.OCurves,
    "FaceSet": alembic.AbcGeom.OFaceSet,
    "Light": alembic.AbcGeom.OLight,
    "Material": alembic.AbcMaterial.OMaterial,
    "NuPatch": alembic.AbcGeom.ONuPatch,
    "Points": alembic.AbcGeom.OPoints,
    "PolyMesh": alembic.AbcGeom.OPolyMesh,
    "SubD": alembic.AbcGeom.OSubD,
    "Xform": alembic.AbcGeom.OXform,
}

# maps cask objects to Alembic IObject schemas
ISCHEMAS = {
    "Camera": alembic.AbcGeom.ICameraSchema,
    "Collections": alembic.AbcCollection.ICollectionsSchema,
    "Curve": alembic.AbcGeom.ICurvesSchema,
    "FaceSet": alembic.AbcGeom.IFaceSetSchema,
    "Light": alembic.AbcGeom.ILightSchema,
    "Material": alembic.AbcMaterial.IMaterialSchema,
    "NuPatch": alembic.AbcGeom.INuPatchSchema,
    "Points": alembic.AbcGeom.IPointsSchema,
    "PolyMesh": alembic.AbcGeom.IPolyMeshSchema,
    "SubD": alembic.AbcGeom.ISubDSchema,
    "Xform": alembic.AbcGeom.IXformSchema,
}


class DataType(object):
    """Base class for data type classes. Used to cast values to
    specific data types when writing property values, e.g. int8_t.
    Should use one of the subclasses and only when setting values, 
    e.g. if prop is a cask Property,

    ::

        prop.set_value(cask.Int8(0), index=0)

    should write out the value as an int8_t data type in the archive.

    TODO: support operations on data types.
    """

    def __init__(self, n, klass, bytes=None):
        if bytes is not None:
            self.n = klass(n & bytes)
        else:
            self.n = klass(n)

    def __repr__(self):
        return self.value()

    def __str__(self):
        return str(self.value()) 

    def value(self):
        return self.n.value


class Int8(DataType):
    def __init__(self, n):
        super(Int8, self).__init__(n, ctypes.c_int8, 0xff)


class Int16(DataType):
    def __init__(self, n):
        super(Int16, self).__init__(n, ctypes.c_int16, 0xffff)


class Int32(DataType):
    def __init__(self, n):
        super(Int32, self).__init__(n, ctypes.c_int32, 0xffffffff)


class Int64(DataType):
    def __init__(self, n):
        super(Int64, self).__init__(n, ctypes.c_int64, 0xffffffffffffffff)


class Uint8(DataType):
    def __init__(self, n):
        super(Uint8, self).__init__(n, ctypes.c_uint8)


class Uint16(DataType):
    def __init__(self, n):
        super(Uint16, self).__init__(n, ctypes.c_uint16)


class Uint32(DataType):
    def __init__(self, n):
        super(Uint32, self).__init__(n, ctypes.c_uint32)


class Uint64(DataType):
    def __init__(self, n):
        super(Uint64, self).__init__(n, ctypes.c_uint64)


# Type functions are deprecated and will be removed in next release
def int8(n):
    return Int8(n).value()


def int16(n):
    return Int16(n).value()


def int32(n):
    return Int32(n).value()


def int64(n):
    return Int64(n).value()


def uint8(n):
    return Uint8(n).value()


def uint16(n):
    return Uint16(n).value()


def uint32(n):
    return Uint32(n).value()


def uint64(n):
    return Uint64(n).value()


# Python class mapping to Imath array class
IMATH_ARRAYS_BY_TYPE = {
    bool: imath.BoolArray,
    float: imath.FloatArray,
    imath.Box2d: imath.Box2dArray,
    imath.Box2f: imath.Box2fArray,
    imath.Box2i: imath.Box2iArray,
    imath.Box2s: imath.Box2sArray,
    imath.Box3d: imath.Box3dArray,
    imath.Box3f: imath.Box3fArray,
    imath.Box3i: imath.Box3iArray,
    imath.Box3s: imath.Box3sArray,
    imath.Color3c: imath.C3cArray,
    imath.Color3f: imath.C3fArray,
    imath.Color4c: imath.C4cArray,
    imath.Color4f: imath.C4fArray,
    imath.M33d: imath.M33dArray,
    imath.M33f: imath.M33fArray,
    imath.M44d: imath.M44dArray,
    imath.M44f: imath.M44fArray,
    imath.V2d: imath.V2dArray,
    imath.V2f: imath.V2fArray,
    imath.V2i: imath.V2iArray,
    imath.V2s: imath.V2sArray,
    imath.V3d: imath.V3dArray,
    imath.V3f: imath.V3fArray,
    imath.V3i: imath.V3iArray,
    imath.V3s: imath.V3sArray,
    imath.V4d: imath.V4dArray,
    imath.V4f: imath.V4fArray,
    imath.V4i: imath.V4iArray,
    imath.V4s: imath.V4sArray,
    int: imath.IntArray,
    str: imath.StringArray,
    Int8: imath.SignedCharArray,
    Int16: imath.ShortArray,
    Int32: imath.IntArray,
    Int64: imath.DoubleArray,
    Uint8: imath.UnsignedCharArray,
    Uint16: imath.UnsignedShortArray,
    Uint32: imath.UnsignedIntArray
}
IMATH_ARRAYS_VALUES = set(IMATH_ARRAYS_BY_TYPE.values())

# Python class mapping to Alembic POD, extent
POD_EXTENT = {
    bool: (alembic.Util.POD.kBooleanPOD, -1),
    Uint8: (alembic.Util.POD.kUint8POD, -1),
    Int8: (alembic.Util.POD.kInt8POD, -1),
    Uint16: (alembic.Util.POD.kUint16POD, -1),
    Int16: (alembic.Util.POD.kInt16POD, -1),
    Uint32: (alembic.Util.POD.kUint32POD, -1),
    int: (alembic.Util.POD.kInt32POD, -1),
    Int32: (alembic.Util.POD.kInt32POD, -1),
    Uint64: (alembic.Util.POD.kUint64POD, -1),
    Int64: (alembic.Util.POD.kInt64POD, -1),
    float: (alembic.Util.POD.kFloat64POD, -1),
    str: (alembic.Util.POD.kStringPOD, -1),
    imath.V3f: (alembic.Util.POD.kFloat32POD, 3),
    imath.V3d: (alembic.Util.POD.kFloat64POD, 3),
    imath.Color3c: (alembic.Util.POD.kUint8POD, -1),
    imath.Color3f: (alembic.Util.POD.kFloat32POD, -1),
    imath.Color4c: (alembic.Util.POD.kUint8POD, -1),
    imath.Color4f: (alembic.Util.POD.kFloat32POD, -1),
    imath.Box3f: (alembic.Util.POD.kFloat32POD, 6),
    imath.Box3d: (alembic.Util.POD.kFloat64POD, 6),
    imath.M33f: (alembic.Util.POD.kFloat32POD, 9),
    imath.M33d: (alembic.Util.POD.kFloat64POD, 9),
    imath.M44f: (alembic.Util.POD.kFloat32POD, 16),
    imath.M44d: (alembic.Util.POD.kFloat64POD, 16),
    imath.StringArray: (alembic.Util.POD.kStringPOD, -1),
    imath.UnsignedCharArray: (alembic.Util.POD.kUint8POD, -1),
    imath.IntArray: (alembic.Util.POD.kInt32POD, -1),
    imath.V3fArray: (alembic.Util.POD.kFloat32POD, 3),
    imath.V3dArray: (alembic.Util.POD.kFloat64POD, 3),
    imath.FloatArray: (alembic.Util.POD.kFloat32POD, -1),
    imath.DoubleArray: (alembic.Util.POD.kFloat64POD, -1),
}

_COMPOUND_PROPERTY_VALUE_ERROR_ = "Compound properties cannot have values"


def get_simple_oprop_class(prop):
    """Returns the alembic simple property class based on a given name and value.

    :param prop: Property object
    :return: Alembic OProperty class
    """
    if prop.is_compound():
        return alembic.Abc.OCompoundProperty
    value = prop.values[0] if len(prop.values) > 0 else []
    if prop.iobject:
        is_array = prop.iobject.isArray()
    elif type(value) in IMATH_ARRAYS_VALUES:
        is_array = True
    else:
        is_array = type(value) in [list, set] and len(value) > 1
    if is_array:
        return alembic.Abc.OArrayProperty
    return alembic.Abc.OScalarProperty


def _delist(val):
    """Returns single value if list len is 1"""
    return val[0] if type(val) in [list, set] and len(val) == 1 else val


def python_to_imath(value):
    """Converts Python lists to Imath arrays."""
    if isinstance(value, DataType):
        return value.value()
    elif type(value) in IMATH_ARRAYS_VALUES:
        return value
    value = _delist(value)
    is_array = type(value) in (set, list)
    value0 = value[0] if is_array and len(value) > 0 else value
    if is_array:
        new_value = IMATH_ARRAYS_BY_TYPE.get(type(value0))(len(value))
        for i, v in enumerate(value):
            new_value[i] = v
        return new_value
    return value


def get_pod_extent(prop):
    """Returns POD, extent tuple for given Property."""
    if len(prop.values) <= 0:
        return 1
    value = _delist(prop.values[0])
    is_array = type(value) in (set, list)
    value0 = value[0] if is_array and len(value) > 0 else value
    try:
        pod, extent = POD_EXTENT.get(type(value0))
    except TypeError as err:
        print("Error getting pod, extent from", prop, value0)
        print(err)
        return (alembic.Util.POD.kUnknownPOD, 1)
    if extent <= 0:
       extent = (len(value0)
            if prop.is_scalar() and
            (type(value0) not in _string_types and hasattr(value0, '__len__'))
            else 1
        )
    return (pod, extent)


def wrapped(func):
    """This decorator function decorates Object methods that require
    access to the alembic schema class.
    """
    @wraps(func)
    def with_wrapped_object(*args, **kwargs):
        """wraps internal alembic iobject"""
        iobj = args[0].iobject
        for klass in IOBJECTS.values():
            if iobj and klass.matches(iobj.getMetaData()):
                args[0].iobject = klass(iobj.getParent(), iobj.getName())
        return func(*args, **kwargs)
    return with_wrapped_object


def wrap(iobject, time_sampling_id=None):
    """Returns a cask-wrapped class object based on the class method "matches".
    """
    if iobject.getName() == "ABC":
        return Top(iobject)
    for cls in Object.__subclasses__():
        if cls.matches(iobject):
            return cls(iobject, time_sampling_id=time_sampling_id)
    return Object(iobject)


def is_valid(archive):
    """Returns True if the archive is a valid alembic archive.
    """
    try:
        alembic.Abc.IArchive(archive)
        return True
    except RuntimeError:
        return False


def find(obj, name=".*", types=None):
    """Finds and returns a list of Objects with names matching
    a given regular expression. ::

        >>> find(a.top, ".*Shape")
        [<PolyMesh "cube1Shape">, <PolyMesh "cube2Shape">]

    :param name: Regular expression to match object name
    :param types: Class type inclusion list
    :return: Sorted list of Object results
    """
    results = [r for r in find_iter(obj, name, types)]
    return sorted(results, key=lambda x: x.name)


def find_iter(obj, name=".*", types=None):
    """Generator that yields Objects with names matching
    a given regular expression.

    :param name: Regular expression to match object name
    :param types: Class type inclusion list
    :yields: Object with name matching name regex
    """
    if re.match(name, obj.name) and (types is None or obj.type() in types):
        yield obj
    for child in obj.children.values():
        for grandchild in find_iter(child, name, types):
            yield grandchild


def copy(item, name=None):
    import copy as _copy
    name = name or item.name
    new_item = item.__class__(name=name)
    if item.metadata:
        new_item.metadata = _copy.copy(item.metadata)
    if item._iobject:
        new_item._iobject = item._iobject
    new_item.time_sampling_id = item.time_sampling_id
    if type(item) in Object.__subclasses__():
        for child in item.children.values():
            new_item.children[child.name] = copy(child)
        for prop in item.properties.values():
            new_item.properties[prop.name] = copy(prop)
    elif type(item) == Property:
        if item.datatype:
            new_item.datatype = item.datatype
        for prop in item.properties.values():
            new_item.properties[prop.name] = copy(prop)
    return new_item


def _deep_getitem(access_func, key):
    """Facilitates deep dict get item on DeepDict class.
    """
    split_key = key.split('/')
    start = split_key[0]
    rest = '/'.join(split_key[1:])
    return access_func(start).get_item(rest)


class DeepDict(dict):
    """Special dict subclass that allows deep dictionary access, renaming when
    setting items and reflective reparenting.
    """

    def __init__(self, parent, klass=None):
        super(DeepDict, self).__init__()
        self.parent = parent
        self.klass = klass
        self.visited = False

    def __getitem__(self, item):
        if type(item) == str:
            if item.startswith("/"):
                item = item[1:]
            if item.endswith("/"):
                item = item[:-1]
            if "/" in item:
                return _deep_getitem(self.__getitem__, item)
            else:
                item = super(DeepDict, self).__getitem__(item)
                item._parent = self.parent
                return item

    def __setitem__(self, name, item):
        if self.klass and not isinstance(item, self.klass):
            raise Exception("Invalid item class: %s" % item.type())

        obj = self.parent
        new = False

        if "/" in name:
            names = name.split("/")
            for name in names:
                try:
                    if type(item) == Property:
                        obj = obj.properties[name]
                    else:
                        obj = obj.children[name]
                except KeyError:
                    # automatically create missing nodes
                    if name != names[-1]:
                        if type(item) == Property:
                            child = obj.properties[name] = Property()
                        else:
                            child = obj.children[name] = Xform()
                        child.parent = obj
                        obj = child
                    new = True
            if new is False:
                obj = obj.parent
            return obj.set_item(name, item)

        item._name = name
        item._parent = obj
        self.visited = True
        return super(DeepDict, self).__setitem__(name, item)

    def remove(self, key):
        """Removes an item if it exists."""
        if key and key in self:
            self.pop(key)


class Archive(object):
    """Archive I/O Object"""

    def __init__(self, filepath=None, fps=24):
        """Creates a new Archive class object.

        :param filepath: Path to Alembic archive file.
        :param fps: Frames per second (default 24).
        """
        if filepath and not os.path.isfile(filepath):
            raise RuntimeError("Nonexistent file: %s" % filepath)

        self.filepath = None
        self.id = id(self)

        # internal object attributes
        self._iobject = None
        self._oobject = None
        self._top = None

        # time sampling attributes
        self.time_sampling_id = 0
        self.fps = fps
        self.__start_time = None
        self.__end_time = None

        # read in the archive
        self.__read_from_file(filepath)

    def __repr__(self):
        return '<%s "%s">' % (self.__class__.__name__, self.filepath)

    def __eq__(self, other):
        return self.id == other.id

    def __get_iobject(self):
        if self._iobject is None:
            if self.filepath and os.path.exists(self.filepath):
                self._iobject = alembic.Abc.IArchive(self.filepath)
        return self._iobject

    def __set_iobject(self, iobject):
        self._iobject = iobject

    iobject = property(__get_iobject, __set_iobject,
                       doc="Internal Alembic IArchive object.")

    def __get_oobject(self):
        if self._oobject is None:
            if self.filepath and not os.path.exists(self.filepath):
                self._oobject = alembic.Abc.OArchive(self.filepath, asOgawa=True)
                self.top.oobject = self._oobject.getTop()
        return self._oobject

    def __set_oobject(self, oobject):
        self._oobject = oobject

    oobject = property(__get_oobject, __set_oobject,
                       doc="Internal Alembic OArchive object.")

    def __get_top(self):
        if not self._top:
            self._top = Top(self)
            if self.iobject:
                self._top = Top(self, self.iobject.getTop())
            if self.oobject:
                if not self._top:
                    self._top = Top(self, self.oobject.getTop())
                self._top.oobject = self.oobject.getTop()
        return self._top

    def __set_top(self, top):
        self._top = top

    top = property(__get_top, __set_top,
                   doc="Hierarchy root, cask.Top object.")

    def __read_from_file(self, filepath):
        """Reads and sets the internal IArchive object.
        """
        self.filepath = filepath
        self.iobject = None
        self.oobject = None
        self.top = None
        self.__get_iobject()
        self.__time_sampling_objects = []
        self.time_sampling_id = max(len(self.timesamplings) - 1, 0)

    def info(self):
        """Returns a metadata dictionary."""
        return alembic.Abc.GetArchiveInfo(self.iobject)

    def alembic_version(self):
        """
        Returns the version of alembic used to write this archive.
        """
        version = self.info().get('libraryVersionString')
        return re.search(r"\d.\d.\d", version).group(0)

    def using_version(self):
        """Returns the version of alembic used to read this archive.
        """
        return alembic.Abc.GetLibraryVersionShort()

    def type(self):
        """Returns "Archive"."""
        return self.__class__.__name__

    def path(self):
        """Returns the filepath for this Archive."""
        return self.filepath

    def is_leaf(self):
        """Returns False."""
        return False

    @property
    def name(self):
        """Returns the basename of this archive."""
        return os.path.basename(self.filepath)

    @property
    def timesamplings(self):
        """Generator that yields tuples of (index, TimeSampling) objects.
        """
        if not self.__time_sampling_objects and self.iobject:
            iarch = self.iobject
            num_samples = iarch.getNumTimeSamplings()
            return [iarch.getTimeSampling(i) for i in range(num_samples)]
        return self.__time_sampling_objects

    def add_timesampling(self, ts):
        if ts not in self.timesamplings:
            self.__time_sampling_objects.append(ts)
            self.__start_time = self.__end_time = None
        return self.timesamplings.index(ts)

    def time_range(self):
        """Returns a tuple of the global start and end time in seconds.

        ** Depends on the X.samples property being set on the Top node,
        which is currently being written by Maya only. **
        """
        top_props = self.top.properties
        g_start_frame, g_end_time = (None, None)

        if self.__start_time is not None and self.__end_time is not None:
            return (self.__start_time, self.__end_time)

        num_stored_times = 1

        for index, ts in enumerate(self.timesamplings):
            tst = ts.getTimeSamplingType()
            if tst.isCyclic() or tst.isUniform():
                tpc = tst.getNumSamplesPerCycle()
                self.__start_time = ts.getStoredTimes()[0]
                self.__end_time = self.__start_time +\
                    (((self.iobject.getMaxNumSamplesForTimeSamplingIndex(index) / tpc) - 1)\
                    / float(self.fps))
            elif tst.isAcyclic():
                num_times = ts.getNumStoredTimes()
                num_stored_times = num_times
                self.__start_time = ts.getSampleTime(0)
                self.__end_time = ts.getSampleTime(num_times-1)

        if self.__start_time is None:
            self.__start_time = 0.0

        if self.__end_time is None:
            self.__end_time = 0.0

        return (self.__start_time, self.__end_time)

    def start_time(self):
        """Returns the global start time in seconds."""
        return self.time_range()[0]

    def set_start_time(self, start):
        """Sets the start time in seconds."""
        self.__start_time = start
        if start > self.__end_time:
            self.__end_time = start

    def start_frame(self):
        """Returns the start frame."""
        return round(self.start_time() * self.fps)

    def set_start_frame(self, frame):
        """Sets the start frame."""
        self.__start_time = frame / float(self.fps)

    def end_time(self):
        """Returns the global end time in seconds."""
        return self.time_range()[1]

    def end_frame(self):
        """Returns the last frame."""
        return round(self.end_time() * self.fps)

    def frame_range(self):
        """Returns a tuple of the global start and end times in frames."""
        return (self.start_frame(), self.end_frame())

    def close(self):
        """Closes this archive and makes it immutable."""
        def close_tree(obj):
            """recursive close"""
            for child in obj.children.values():
                close_tree(child)
                del child
            obj.close()
            del obj

        for child in self.top.children.values():
            close_tree(child)
            del child

        self._iobject = None
        self._oobject = None
        self._top._iobject = None
        self._top._oobject = None
        self._top._parent = None
        self._top._child_dict.clear()
        self._top._prop_dict.clear()

    def __write(self):
        """Recursively calls save() on object hierarchy. Normally, you will
        want to call write_to_file instead.
        """
        if not self.oobject:
            raise ValueError("No output filepath specified")
        self.top.save()
        def save_tree(obj):
            """recursive save"""
            obj.save()
            for child in obj.children.values():
                save_tree(child)
                child.close()
                del child
            obj.close()
            del obj
        for child in self.top.children.values():
            save_tree(child)
        self.top.close()

    # TODO: non-destructive saving (changes are lost)
    def write_to_file(self, filepath=None, asOgawa=True, userDescription=""):
        """Writes this archive to a file on disk and closes the Archive.
        """
        smps = []
        # look for timesampling data on the iarchive first
        if self.timesamplings or (self.iobject and not self.oobject):
            smps = [(i, ts) for i, ts in enumerate(self.timesamplings)]
        # is none exist, create a new one
        if not smps:
            smps.append((1, alembic.AbcCoreAbstract.TimeSampling(
                         1 / float(self.fps), self.start_time())))
            self.time_sampling_id = 1
        # create the oarchive
        if not self.oobject:
            # support for Ogawa archives via CreateArchiveWithInfo
            # came in Alembic 1.5.7
            m1, m2, m3 = (int(m) for m in self.using_version().split("."))
            if m1 == 1 and m2 <= 5 and m3 < 7:
                self.oobject = alembic.Abc.OArchive(filepath, asOgawa=asOgawa)
            else:
                if self.top.iobject:
                    md = self.top.iobject.getMetaData()
                else:
                    md = alembic.AbcCoreAbstract.MetaData()
                for k, v in self.top.metadata.items():
                    md.set(k, v)
                self.oobject = alembic.Abc.CreateArchiveWithInfo(
                    filepath,
                    "cask %s" % __version__,
                    str(userDescription),
                    md, 1
                )
            self.top.oobject = self.oobject.getTop()
        # set timesampling objects on the oarchive
        for i, time_sample in smps:
            self.oobject.addTimeSampling(time_sample)
        self.__write()
        self.close()


class Property(object):
    """Property I/O Object."""
    def __init__(self, iproperty=None, time_sampling_id=0, name=None, klass=None):
        """
        :param iproperty: Alembic IProperty class object.
        :param time_sampling_id: TimeSampling object ID (inherits down).
        :param name: Property name
        :param klass: OProperty class used for writing
        """
        super(Property, self).__init__()
        self.id = id(self)

        # init some private variables
        self._parent = None
        self._name = name
        self._metadata = {}
        self._datatype = None
        self._iobject = iproperty
        self._oobject = None
        self._klass = klass
        self._values = []
        self._prop_dict = DeepDict(self, Property)
        self.time_sampling_id = time_sampling_id

        # if we have an iproperty, get some values from it
        if iproperty:
            self.__read_property(iproperty)

    def __repr__(self):
        return '<Property "%s">' % self.name

    def get_item(self, item):
        """Used for deep dict access"""
        return self.properties[item]

    def set_item(self, name, item):
        """Used for deep dict access"""
        self.properties[name] = item

    def __get_iobject(self):
        return self._iobject

    def __set_iobject(self, iobject):
        self._iobject = iobject

    iobject = property(__get_iobject, __set_iobject,
                       doc="Internal Alembic IProperty object.")

    def __get_oobject(self):
        parent = None

        if not self._oobject and self.parent:
            if self.iobject:
                meta = self.iobject.getMetaData()
            else:
                meta = alembic.AbcCoreAbstract.MetaData()
            for k, v in self.metadata.items():
                meta.set(k, v)
            if not self._klass:
                self._klass = get_simple_oprop_class(self)
            if self.is_compound() and self.iobject:
                meta.set('schema', self.iobject.getMetaData().get('schema'))
            if type(self.parent) == Property and self.parent.is_compound():
                parent = self.parent.oobject
            else:
                if hasattr(self.parent.oobject, 'getProperties'):
                    parent = self.parent.oobject.getProperties()
            if parent and parent.getPropertyHeader(self.name):
                # pre-existing property exists, see Property.__get_oobject
                pass
            elif parent and self._klass:
                if self.is_compound():
                    self._oobject = self._klass(
                        parent, self.name, meta, self.time_sampling_id
                    )
                elif self.datatype:
                    self._oobject = self._klass(
                        parent, self.name, self.datatype, meta, self.time_sampling_id
                    )
        return self._oobject

    def __set_oobject(self, oobject):
        self._oobject = oobject

    oobject = property(__get_oobject, __set_oobject,
                       doc="Internal Alembic OProperty object.")

    def is_scalar(self):
        if not self._klass:
            self._klass = get_simple_oprop_class(self)
        return self._klass == alembic.Abc.OScalarProperty

    def is_array(self):
        return not self.is_scalar()

    def __get_parent(self):
        if self._parent is None and self.iobject:
            self._parent = wrap(self.iobject.getParent())
        return self._parent

    def __set_parent(self, parent):
        self._parent = parent

    parent = property(__get_parent, __set_parent,
                      doc="Parent object or property.")

    def __get_name(self):
        if not self._name:
            if self.iobject:
                self._name = self.iobject.getName()
            else:
                self._name = None
        return self._name

    def __set_name(self, name):
        old = self._name
        self._name = name
        if self._parent and hasattr(self._parent, "_prop_dict"):
            if old and old in self.parent.properties:
                self._parent.properties.remove(old)
                self._parent.properties[name] = self

    name = property(__get_name, __set_name,
                    doc="Gets and sets the property name.")

    def __get_metadata(self):
        if not self._metadata and self.iobject:
            meta = self.iobject.getMetaData()
            for field in meta.serialize().split(';'):
                splits = field.split('=')
                key = splits[0]
                value = '='.join(splits[1:])
                self._metadata[key] = value
        return self._metadata

    def __set_metadata(self, metadata):
        self._metadata = metadata

    metadata = property(__get_metadata, __set_metadata,
                        doc="Metadata as a dict.")

    def __get_datatype(self):
        if not self._datatype:
            if self.iobject:
                self._datatype = self.iobject.getDataType()
            elif len(self.values) > 0:
                pod, extent = get_pod_extent(self)
                if pod is None:
                    raise Exception("Unknown datatype for %s: %s"
                        % (self.name, self.values[0]))
                self._datatype = alembic.AbcCoreAbstract.DataType(pod, extent)
        return self._datatype

    def __set_datatype(self, datatype):
        self._datatype = datatype

    datatype = property(__get_datatype, __set_datatype,
                        doc="DataType object.")

    def type(self):
        """Returns the name of the class."""
        if self.is_compound():
            return "Compound Property"
        return self.__class__.__name__

    def pod(self):
        """Returns the property's datatype POD value."""
        return self.datatype.getPod()

    def extent(self):
        """Returns the property's datatype extent."""
        return self.datatype.getExtent()

    def archive(self):
        """Returns the Archive for this property."""
        parent = self.parent
        while parent and parent.type() != "Archive":
            parent = parent.parent
        return parent

    def path(self):
        """Returns the full path/name of this property."""
        path = [""]
        obj = self
        while obj and obj.type() != "Top":
            path.insert(1, obj.name)
            obj = obj.parent
        return "/".join(path)

    def object(self):
        """Returns the object parent for this property."""
        obj = self.parent
        while obj and "Property" in obj.type():
            obj = obj.parent
        return obj

    def add_property(self, prop):
        """Add a property to this, making this property a compound property.

        :param property: cask.Property class object.
        """
        if len(self.values) > 0:
            raise TypeError("Properties with values cannot have sub-properies")
        self.properties[prop.name] = prop

    def __read_property(self, iproperty=None):
        """Sets the internal IProperty object.

        :param iproperty: Alembic IProperty object.
        """
        if iproperty:
            self.iobject = iproperty
            self.name = iproperty.getName()
        if iproperty.isCompound():
            for i in range(self.iobject.getNumProperties()):
                self.add_property(Property(
                        iproperty = iproperty.getProperty(i),
                        time_sampling_id = self.time_sampling_id
                    )
                 )

    @property
    def properties(self):
        """Child properties accessor."""
        return self._prop_dict

    def is_leaf(self):
        """Returns True if this property is a leaf node, i.e. it has no sub-properties.
        """
        return len(self.properties) == 0

    def is_compound(self):
        """Returns True if this property contains sub-properties.

        Note that compound properties cannot have values, and
        simple properties cannont have sub-properties.
        """
        if self.iobject:
            return self.iobject.isCompound()
        return len(self.properties) > 0

    def __get_sample_index(self, time=None, frame=None):
        """Converts time in secs or frame number to sample index.

        :param time: time in seconds.
        :param frame: frame number.
        :return: sample index.
        """
        if len(self.properties) > 0:
            raise TypeError(_COMPOUND_PROPERTY_VALUE_ERROR_)
        if self.iobject:
            ts = self.iobject.getTimeSampling()
            numSamples = self.iobject.getNumSamples()
        else:
            ts = self.object().schema.getTimeSampling()
            numSamples = self.object().schema.getNumSamples()
        if time is not None:
            return ts.getNearIndex(float(time), numSamples)
        elif frame is not None:
            return ts.getNearIndex((frame / float(self.archive().fps)),
                numSamples)
        else:
            return 0

    @property
    def values(self):
        """Returns dictionary of values stored on this property.
        """
        if not self.is_compound() and not self._values and self.iobject:
            for i in range(len(self.iobject.samples)):
                try:
                    self._values.insert(i, self.iobject.samples[i])
                except RuntimeError as err:
                    print("Bad value on sample:", i, err)
                    self._values.insert(i, str(err))
        return self._values

    def get_value(self, index=None, time=None, frame=None):
        """Returns a the value stored on this property for a given sample
        index, time or frame.

        Provide one of the following args. If none are provided, it will
        return the 0th value.

        :param index: sample index
        :param time: time in seconds
        :param frame: frame number (assumes 24fps, to change set on archive)
        """
        if self.is_compound():
            raise TypeError(_COMPOUND_PROPERTY_VALUE_ERROR_)
        if index == None and time == None and frame == None:
            index = 0
        elif index is None:
            index = self.__get_sample_index(time, frame)
        try:
            return self.values[index]
        except (KeyError, IndexError):
            val = self.iobject.getValue(index)
            self.values[index] = val
            return val

    def set_value(self, value, index=None, time=None, frame=None):
        """Sets a value on the property at a given index.

        Provide one of the following args. If none are provided, it will
        append to the end.

        :param index: sample index
        :param time: time in seconds
        :param frame: frame number (assumes 24fps, to change set on archive)
        """
        if self.is_compound():
            raise TypeError(_COMPOUND_PROPERTY_VALUE_ERROR_)
        value = _delist(value)
        if index == None and time == None and frame == None:
            index = len(self._values)
        elif index is None:
            index = self.__get_sample_index(time, frame)
        if index < len(self.values):
            self.values[index] = value
        else:
            self.values.append(value)

    def clear_properties(self):
        """Clears the properties container."""
        self._prop_dict = DeepDict(self, Property)

    def clear_values(self):
        """Clears the values container."""
        self._values = []

    def close(self):
        """Closes this property by removing references to internal OProperty.
        """
        if self.parent and self.name in self.parent.properties:
            del self.parent.properties[self.name]
        self._iobject = None
        self._oobject = None
        self._klass = None
        self._parent = None
        self._values = []
        for prop in self.properties.values():
            prop.close()

    def save(self):
        """Walks sub-tree and creates corresponding alembic OProperty classes,
        if they don't exist, and sets values.
        """
        if self.oobject and not self.is_compound():
            if self.name in (".selfBnds", ".childBnds"):
                self.oobject.getMetaData().set("interpretation", "box")
            for value in self.values:
                try:
                    value = python_to_imath(value)
                    self.oobject.setValue(value)
                except Exception as err:
                    print("Error setting value on %s: %s %s\n%s" \
                        % (self.name, value, self._klass, err))
                del value
        else:
            for prop in self.properties.values():
                up = False
                if not prop.iobject and not prop.object().iobject:
                    if prop.name == ".childBnds":
                        prop._oobject = prop.object().oobject.getSchema().getChildBoundsProperty()
                    elif prop.parent.name == ".userProperties":
                        up = Property()
                        up._oobject = prop.object().oobject.getSchema().getUserProperties()
                        up.properties[prop.name] = prop
                        prop.parent = up
                    elif prop.parent.name == ".arbGeomParams":
                        up = Property()
                        up._oobject = prop.object().oobject.getSchema().getArbGeomParams()
                        up.properties[prop.name] = prop
                        prop.parent = up
                else:
                    prop.parent = self
                prop.save()
                prop.close()
                del prop
                if up:
                    up.close()
                    del up
        self.close()


class Object(object):
    """Base I/O Object class."""
    _sample_class = None
    def __init__(self, iobject=None, schema=None,
                 time_sampling_id=None, name=None):
        """
        :param iobject: Any alembic.Abc.IObject subclass object
        :param schema: Any alembic.Abc.ISchema subclass object
        :param time_sampling_id: The ID of the TimeSampling object
        """
        super(Object, self).__init__()
        self.id = id(self)

        # init some private variables
        self._name = name
        self._metadata = {}
        self._isamples = []
        self._osamples = []
        self._iobject = iobject
        self._oobject = None
        self._klass = None
        self._schema = schema
        self._parent = None
        self._is_animated = None
        self._tsid = time_sampling_id
        self._prop_dict = DeepDict(self, Property)
        self._child_dict = DeepDict(self, Object)

        # init some stuff
        self.clear_all()
        self.__read_object()

    def __repr__(self):
        return '<%s "%s">' % (self.__class__.__name__, self.name)

    def get_item(self, item):
        """Used for deep dict access"""
        return self.children[item]

    def set_item(self, name, item):
        """Used for deep dict access"""
        self.children[name] = item

    @property
    def __sample_methods(self):
        return dir(self._sample_class)

    def __get_iobject(self):
        return self._iobject

    def __set_iobject(self, iobject):
        self._iobject = iobject

    iobject = property(__get_iobject, __set_iobject,
                       doc="Internal Alembic IObject object.")

    def __get_oobject(self):
        # Using OObject subclasses (like OXform) automatically
        # creates hidden Compound Properties (like .xform) which
        # results in name collisions when saving properties in cask.
        # Using OObjects avoids this problem, but we have to set
        # the metadata manually.

        if self.iobject:
            meta = self.iobject.getMetaData()
        else:
            meta = alembic.AbcCoreAbstract.MetaData()
        for k, v in self.metadata.items():
            meta.set(k, v)
        if self._oobject is None:
            if self.iobject:
                self._klass = alembic.Abc.OObject
            else:
                self._klass = OOBJECTS.get(self.type())
            if self._klass:
                if self.parent:
                    self._oobject = self._klass(self.parent.oobject, self.name,
                                            meta, self.time_sampling_id)
            else:
                print("OObject class not found for: %s" % (self.name))

        return self._oobject

    def __set_oobject(self, oobject):
        self._oobject = oobject

    oobject = property(__get_oobject, __set_oobject,
                       doc="Internal Alembic OObject object.")

    @wrapped
    def __get_schema(self):
        if self.iobject and self._schema is None:
            self._schema = self.iobject.getSchema()
        return self._schema

    def __set_schema(self, schema):
        self._schema = schema

    schema = property(__get_schema, __set_schema,
                      doc="Returns the Alembic schema object.")

    @classmethod
    def matches(cls, iobject):
        """Returns True if a given iobject type matches this type.
        """
        return IOBJECTS.get(cls.__name__).matches(iobject.getMetaData())

    def __get_parent(self):
        if self._parent is None and self.iobject:
            parent = self.iobject.getParent()
            if parent.getFullName() == "/":
                self._parent = Top(parent)
            else:
                self._parent = wrap(parent)
        return self._parent

    def __set_parent(self, parent):
        self._parent = parent
        self._oobject = None
        if parent and type(self) != Top:
            parent.add_child(self)

    parent = property(__get_parent, __set_parent,
                      doc="Parent object accessor.")

    def __get_name(self):
        if not hasattr(self, "_name"):
            if self.iobject:
                self._name = self.iobject.getName()
            else:
                self._name = None
        return self._name

    def __set_name(self, name):
        old = self._name
        self._name = name
        if self.parent and hasattr(self._parent, "_child_dict"):
            if old and old in self._parent._child_dict:
                self._parent._child_dict.remove(old)
                self._parent._child_dict[name] = self

    name = property(__get_name, __set_name,
                    doc="Set and get the name of the object.")

    def __get_tsid(self):
        if self._tsid is None:
            return self.parent.time_sampling_id
        return self._tsid

    def __set_tsid(self, tsid):
        self._tsid = tsid

    time_sampling_id = property(__get_tsid, __set_tsid,
                                doc="Time sampling ID.")

    def __get_metadata(self):
        if not self._metadata and self.iobject:
            meta = self.iobject.getMetaData()
            for field in meta.serialize().split(';'):
                splits = field.split('=')
                key = splits[0]
                value = '='.join(splits[1:])
                self._metadata[key] = value
        return self._metadata

    def __set_metadata(self, metadata):
        self._metadata = metadata

    metadata = property(__get_metadata, __set_metadata,
                        doc="Metadata as a dict.")

    def archive(self):
        """Returns the Archive for this object."""
        parent = self.parent
        while parent and parent.type() != "Archive":
            parent = parent.parent
        return parent

    def path(self):
        """Returns the full path/name of this object."""
        path = [""]
        obj = self
        while obj and obj.type() != "Top":
            path.insert(1, obj.name)
            obj = obj.parent
        return "/".join(path)

    def type(self):
        """Returns the name of the class."""
        return self.__class__.__name__

    def add_child(self, child):
        """Adds a child object to this object.

        :param child: cask.Object
        """
        self.children[child.name] = child

    def __read_object(self):
        """reads object, sets name"""
        if self.iobject and type(self) != Top:
            self.name = self.iobject.getName()

    @property
    def children(self):
        """Returns children sub-tree accessor. """
        if not self._child_dict.visited and self.iobject:
            for i in range(self.iobject.getNumChildren()):
                child = wrap(
                    iobject = self.iobject.getChild(i),
                    time_sampling_id = self.time_sampling_id
                )
                self._child_dict[child.name] = child
        return self._child_dict

    @property
    def properties(self):
        """Properties accessor."""
        if not self._prop_dict.visited and self.iobject:
            props = self.iobject.getProperties()
            for i in range(len(props.propertyheaders)):
                prop = Property(
                    iproperty = props.getProperty(i),
                    time_sampling_id = self.time_sampling_id
                )
                self._prop_dict[prop.name] = prop
        return self._prop_dict

    @property
    def samples(self):
        """Returns samples from the Alembic IObject."""
        if self.iobject and len(self._isamples) == 0:
            num_samples = self.schema.getNumSamples()
            schema = self.schema
            self._isamples = [schema.getValue(i) for i in range(num_samples)]
        return self._isamples

    def set_sample(self, sample, index=None):
        """Sets an Alembic sample object on this object.

        *Do we want to expose samples at all? Should all data
        be set via seting values on properties, directly or with
        high level methods?

        :param sample: Alembic sample object.
        :param index: Index of the sample to set, or None.
        """
        if index is None:
            index = len(self._osamples)
        assert type(sample) == self._sample_class,\
            "Can not set %s on %s object" % (sample.__class__.__name__, self.type())
        self._osamples.insert(index, sample)

    def _set_default_sample(self):
        pass

    def is_leaf(self):
        """Returns True if this object is a leaf node, i.e. it has no children.
        """
        return len(self.children) == 0

    def is_animated(self):
        """Returns True if any properties are not constant.
        """
        self._is_animated = False
        def _is_animated(prop):
            """recursive check"""
            if not prop.is_compound() and not prop.iobject.isConstant():
                self._is_animated = True
            for child in prop.properties.values():
                _is_animated(child)
        for prop in self.properties.values():
            _is_animated(prop)
        return self._is_animated

    def is_deforming(self):
        """Returns True if the object has changing P values.
        """
        try:
            prop = self.properties[".geom/P"]
            if prop:
                return not prop.iobject.isConstant()
            return False
        except KeyError:
            return False

    def start_frame(self):
        """Returns start frame.
        """
        try:
            time_sample = self.iobject.getTimeSampling()
            fps = self.archive().fps
            return round(time_sample.getSampleTime(0) * fps)
        except AttributeError:
            return self.parent.start_frame()

    def end_frame(self):
        """Returns last frame.
        """
        try:
            time_sample = self.iobject.getTimeSampling()
            num_samples = self.iobject.getNumSamples()
            fps = self.archive().fps
            if num_samples:
                return round(time_sample.getSampleTime(num_samples - 1) * fps)
            return round(time_sample.getSampleTime(0) * fps)
        except AttributeError:
            return self.parent.end_frame()

    def global_matrix(self, index=0):
        """Returns world space matrix for this object.
        """
        def accum_xform(xform, obj):
            """recursive xform accum"""
            if Xform.matches(obj._iobject):
                xform *= obj.matrix(index)
        xform = imath.M44d()
        xform.makeIdentity()
        parent = self
        while parent and type(parent) not in [Archive, Top]:
            accum_xform(xform, parent)
            parent = parent.parent
        return xform

    def clear_properties(self):
        """Clears the internal properties container."""
        self._prop_dict = DeepDict(self, Property)

    def clear_samples(self):
        """Clears the internal samples container."""
        self._isamples = []
        self._osamples = []

    def clear_children(self):
        """Clears the internal children container."""
        self._child_dict = DeepDict(self, Object)

    def clear_all(self):
        self.clear_properties()
        self.clear_samples()
        self.clear_children()

    def close(self):
        """Closes this object by removing references to internal OObject.
        """
        if self.parent and self.parent.type() != 'Archive':
            del self.parent.children[self.name]
        self._iobject = None
        self._oobject = None
        self._klass = None
        self._parent = None
        self._schema = None
        self.clear_all()
        for prop in self.properties.values():
            prop.close()
            del prop

    def save(self):
        """Walks child and property sub-trees creating OObjects as necessary.
        """
        obj = self.oobject
        for prop in self.properties.values():
            prop.save()
            prop.close()
            del prop
        if not self._osamples:
            self._set_default_sample()
        # OCameras have no getSchema method, properties written explicitly
        if self.type() == 'Camera' and self.iobject:
            return
        for sample in self._osamples:
            try:
                if self.type() == 'Light' \
                   and type(sample) == alembic.AbcGeom.CameraSample:
                    obj.getSchema().setCameraSample(sample)
                else:
                    obj.getSchema().set(sample)
            except AttributeError as err:
                print("Error setting sample on %s: %s\n%s" \
                    % (self.name, sample, err))
            del sample
        del obj


class Top(Object):
    """Alembic Top Object."""
    def __init__(self, archive, iobject=None):
        super(Top, self).__init__(iobject)
        self._parent = weakref.proxy(archive)
        self._parent._top = self
        self.oobject = None

    @classmethod
    def matches(cls, iobject):
        """Returns True if iobject is a Top object."""
        return iobject.__class__ == cls.__class__

    def is_leaf(self):
        """Returns False."""
        return False

    def path(self):
        """Returns the full path/name of this object."""
        return "/"

    def __get_name(self):
        return "ABC"

    def __set_name(self, name):
        raise TypeError("Can not set name on Top object.")

    name = property(__get_name, __set_name,
                    doc="Returns the object name, which for Top is always ABC")


class Xform(Object):
    """Xform I/O Object subclass."""
    _sample_class = alembic.AbcGeom.XformSample
    def __init__(self, *args, **kwargs):
        super(Xform, self).__init__(*args, **kwargs)

    def matrix(self, index=0):
        """
        Returns the xform matrix value for a given index.

        :param index: Sample index.
        """
        return self.schema.getValue(index).getMatrix()

    def set_scale(self, *args):
        """
        Creates an internal XformSample object and sets the scale value.
        """
        if len(args) == 1 and type(args[0]) == imath.V3d:
            scale = args[0]
        else:
            scale = imath.V3d(args[0], args[1], args[2])
        xform_sample = alembic.AbcGeom.XformSample()
        xform_sample.setScale(scale)
        self.set_sample(xform_sample)


class PolyMesh(Object):
    """PolyMesh I/O Object subclass."""
    _sample_class = alembic.AbcGeom.OPolyMeshSchemaSample
    def __init__(self, *args, **kwargs):
        super(PolyMesh, self).__init__(*args, **kwargs)


class SubD(Object):
    """SubD I/O Object subclass."""
    _sample_class = alembic.AbcGeom.OSubDSchemaSample
    def __init__(self, *args, **kwargs):
        super(SubD, self).__init__(*args, **kwargs)


class FaceSet(Object):
    """FaceSet I/O Object subclass."""
    _sample_class = alembic.AbcGeom.OFaceSetSchemaSample
    def __init__(self, *args, **kwargs):
        super(FaceSet, self).__init__(*args, **kwargs)


class Curve(Object):
    """Curve I/O Object subclass."""
    _sample_class = alembic.AbcGeom.OCurvesSchemaSample
    def __init__(self, *args, **kwargs):
        super(Curve, self).__init__(*args, **kwargs)


class Camera(Object):
    """Camera I/O Object subclass."""
    _sample_class = alembic.AbcGeom.CameraSample
    def __init__(self, *args, **kwargs):
        super(Camera, self).__init__(*args, **kwargs)

    def _set_default_sample(self):
        self.set_sample(alembic.AbcGeom.CameraSample(), 0)


class NuPatch(Object):
    """NuPath I/O Object subclass."""
    _sample_class = alembic.AbcGeom.ONuPatchSchemaSample
    def __init__(self, *args, **kwargs):
        super(NuPatch, self).__init__(*args, **kwargs)


class Material(Object):
    """Material I/O Object subclass."""
    def __init__(self, *args, **kwargs):
        super(Material, self).__init__(*args, **kwargs)


class Light(Object):
    """Light I/O Object subclass."""
    _sample_class = alembic.AbcGeom.CameraSample
    def __init__(self, *args, **kwargs):
        super(Light, self).__init__(*args, **kwargs)


class Points(Object):
    """Points I/O Object subclass."""
    _sample_class = alembic.AbcGeom.OPointsSchemaSample
    def __init__(self, *args, **kwargs):
        super(Points, self).__init__(*args, **kwargs)
