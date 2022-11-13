import ast
import re

import pymel.core as pm
import maya.cmds as cmds
import maya.OpenMaya as api

from . import utils

__all__ = [
    "decode_meta_data",
    "decode_meta_data_value",
    "encode_meta_data",
    "encode_meta_data_value",
    "find_meta_nodes",
    "get_meta_classes",
    "get_meta_data",
    "has_meta_class",
    "is_meta_node",
    "remove_meta_data",
    "set_all_meta_data",
    "set_meta_data",
    "update_meta_data",
]

METACLASS_ATTR_PREFIX = "pyMetaClass_"
METADATA_ATTR = "pyMetaData"

VALID_CLASS_ATTR = re.compile(r"^[_a-z0-9]*$", re.IGNORECASE)


def _get_meta_data_plug(mfn_node):
    """
    Return the MPlug for the metadata attribute on a node

    Args:
        mfn_node: A MFnDependencyNode referencing the target node.
    """
    try:
        return mfn_node.findPlug(METADATA_ATTR)
    except RuntimeError:
        pass


def _get_meta_class_plug(mfn_node, class_name):
    """
    Return the MPlug for a metaclass attribute on a node

    Args:
        mfn_node: A MFnDependencyNode referencing the target node.
        class_name: A string name of the metaclass type.
    """
    attr_name = METACLASS_ATTR_PREFIX + class_name
    try:
        return mfn_node.findPlug(attr_name)
    except RuntimeError:
        pass


def _get_unique_node_name(mfn_node):
    """
    Return the unique name of a Dependency node.

    If the node is already unique, simply returns its name, otherwise returns the unique path to the node.

    Args:
        mfn_node (MFnDependencyNode): A MFnDependencyNode with a node object

    Returns:
        The unique name or path (str) of the node.
        E.g. 'node' or 'my|node'
    """
    if not mfn_node.hasUniqueName():
        node = mfn_node.object()
        if node.hasFn(api.MFn.kDagNode):
            mfn_dag = api.MFnDagNode(mfn_node.object())
            dag_path = api.MDagPath()
            mfn_dag.getPath(dag_path)
            return dag_path.partialPathName()
    return mfn_node.name()


def _get_unique_plug_name(mfn_node, mplug):
    """
    Return the unique name of a MPlug, including its nodes name.

    Args:
        mfn_node (MFnDependencyNode): A MFnDependencyNode with the node.
            Provided for performance reasons, since it is common to have
            both this and the MPlug when needing the plug name in this package.
        mplug (MPlug): A MPlug of a node

    Returns:
        The unique name or path including attribute (str) of the plug. E.g. 'my|node.myPlug'
    """
    return _get_unique_node_name(mfn_node) + "." + mplug.partialName()


def _get_or_create_meta_data_plug(mfn_node, undoable=True):
    """
    Return the MPlug for the metadata attribute on a node, adding the attribute if it does not already exist.

    Args:
        mfn_node (MFnDependencyNode): The MFnDependencyNode of a node
        undoable (bool): When True, the operation will be undoable

    Returns:
        The plug (MPlug) for the metadata attribute.
    """
    try:
        plug = mfn_node.findPlug(METADATA_ATTR)
    except:
        if undoable:
            name = _get_unique_node_name(mfn_node)
            cmds.addAttr(name, ln=METADATA_ATTR, dt="string")
        else:
            mfn_attr = api.MFnTypedAttribute()
            attr = mfn_attr.create(METADATA_ATTR, METADATA_ATTR, api.MFnData.kString)
            mfn_node.addAttribute(attr)
        plug = mfn_node.findPlug(METADATA_ATTR)

    return plug


def _add_meta_class_attr(mfn_node, class_name, undoable=True):
    """
    Add a metaclass attribute to a node.

    Does nothing if the attribute already exists.

    Args:
        mfn_node (MFnDependencyNode): The MFnDependencyNode of a node.
        class_name (str): The metadata class name.
        undoable (bool): When True, the operation will be undoable.
    """
    if not VALID_CLASS_ATTR.match(class_name):
        raise ValueError("Invalid meta class name: " + class_name)
    class_attr = METACLASS_ATTR_PREFIX + class_name
    try:
        mfn_node.attribute(class_attr)
    except RuntimeError:
        if undoable:
            name = _get_unique_node_name(mfn_node)
            cmds.addAttr(name, ln=class_attr, at="short")
        else:
            mfn_attr = api.MFnNumericAttribute()
            attr = mfn_attr.create(class_attr, class_attr, api.MFnNumericData.kShort)
            mfn_node.addAttribute(attr)


def _remove_meta_class_attr(mfn_node, class_name, undoable=True):
    """
    Remove a metaclass attribute from a node.

    Does nothing if the attribute does not exist.

    Args:
        mfn_node (MFnDependencyNode): The api MFnDependencyNode of a node.
        undoable (bool): Make the operation will be undoable by using cmds instead of the api.

    Returns:
        True if the attr was removed or didn't exist, False if it couldn't be removed.
    """
    class_plug = _get_meta_class_plug(mfn_node, class_name)
    if not class_plug:
        return True

    if class_plug.isLocked():
        return False
    else:
        if undoable:
            plug_name = _get_unique_plug_name(mfn_node, class_plug)
            cmds.deleteAttr(plug_name)
        else:
            mfn_node.removeAttribute(class_plug.attribute())
        return True


def encode_meta_data(data):
    """
    Return the given metadata encoded into a string

    Args:
        data: A python dictionary-like object representing the data to serialize.
    """
    return repr(encode_meta_data_value(data))


def encode_meta_data_value(value):
    """
    Encode and return a meta data value.

    Handles special data types like Maya nodes.

    Args:
        value: Any python value to be encoded
    """
    if isinstance(value, dict):
        result = {}
        for k, v in value.items():
            result[k] = encode_meta_data_value(v)
        return result
    elif isinstance(value, (list, tuple)):
        return value.__class__([encode_meta_data_value(v) for v in value])
    elif isinstance(value, pm.nt.DependNode):
        return utils.get_uuid(value)
    else:
        return value


def decode_meta_data(data, ref_node=None):
    """
    Parse the given metadata and return it as a valid python object.

    Args:
        data: A string representing encoded metadata.
    """
    if not data:
        return {}
    # convert from string to python object
    try:
        data = ast.literal_eval(data.replace("\r", ""))
    except Exception as e:
        raise ValueError("Failed to decode meta data: {0}".format(e))
    return decode_meta_data_value(data, ref_node)


def decode_meta_data_value(value, ref_node):
    """
    Parse string formatted metadata and return the resulting python object.

    Args:
        data: A str representing encoded metadata.
    """
    if isinstance(value, dict):
        result = {}
        for k, v in value.items():
            result[k] = decode_meta_data_value(v, ref_node)
        return result
    elif isinstance(value, (list, tuple)):
        return value.__class__([decode_meta_data_value(v, ref_node) for v in value])
    elif utils.is_uuid(value):
        return utils.find_node_by_uuid(value, ref_node)
    else:
        return value


def is_meta_node(node):
    """
    Return True if the given node has any meta data

    Args:
        node: A PyMel node or string node name
    """
    return utils.has_attr(node, METADATA_ATTR)


def has_meta_class(node, class_name):
    """
    Return True if the given node has data for the given metaclass type

    Args:
        node: A PyMel node or string node name
        class_name: A string name of the metaclass type.
            If given, the node must be of this class type.
    """
    return utils.has_attr(node, METACLASS_ATTR_PREFIX + class_name)


def find_meta_nodes(class_name=None, as_py_nodes=True):
    """
    Return a list of all meta nodes of the given class type. If no class is given,
    all nodes with metadata are returned.

    Args:
        class_name: A string name of the metaclass type.
        as_py_nodes: A bool, when True, returns a list of PyNodes,
            otherwise returns a list of MObjects
    """
    if class_name is not None:
        plug_name = METACLASS_ATTR_PREFIX + class_name
    else:
        plug_name = METADATA_ATTR
    objs = utils.get_m_objects_by_plug(plug_name)
    if as_py_nodes:
        return [pm.PyNode(o) for o in objs]
    else:
        return objs


def set_meta_data(node, class_name, data, undoable=True, replace=False):
    """
    Set the metadata for a metaclass type on a node.

    The class_name must be a valid attribute name.

    Args:
        node (PyNode or str): The node on which to set data
        class_name (str): The data's metaclass type name
        data (dict): The data to serialize and store on the node
        undoable (bool): When True, the operation will be undoable
        replace (bool): When True, will replace all data on the node
            with the new metadata. This uses set_all_meta_data and can
            be much faster with large data sets.
    """
    if replace:
        set_all_meta_data(node, {class_name: data}, undoable)
        return

    mfn_node = utils.get_mfn_dependency_node(node)
    plug = _get_or_create_meta_data_plug(mfn_node, undoable)
    _add_meta_class_attr(mfn_node, class_name, undoable)

    # update meta data
    ref_node = None
    if cmds.referenceQuery(str(node), isNodeReferenced=True):
        ref_node = cmds.referenceQuery(str(node), rfn=True)
    full_data = decode_meta_data(plug.asString(), ref_node)
    full_data[class_name] = data
    new_value = encode_meta_data(full_data)

    if undoable:
        plug_name = _get_unique_plug_name(mfn_node, plug)
        cmds.setAttr(plug_name, new_value, type="string")
    else:
        plug.setString(new_value)


def set_all_meta_data(node, data, undoable=True):
    """
    Set all metadata on a node. This is faster because the
    existing data on the node is not retrieved first and then
    modified. The data must be first indexed by strings that
    are valid metaclass names, otherwise errors may occur
    when retrieving it later.

    New metaclass attributes will be added automatically,
    but existing metaclass attributes will not be removed.
    If old metaclass attributes on this node will no longer
    be applicable, they should be removed with removeAllData
    first.

    Args:
        node (PyNode or str): The node on which to set data.
        data (dict): The data to serialize and store on the node.
        undoable (bool): When True, the operation will be undoable.
    """
    mfn_node = utils.get_mfn_dependency_node(node)
    plug = _get_or_create_meta_data_plug(mfn_node, undoable)

    # add class attributes
    if data:
        for className in data.keys():
            _add_meta_class_attr(mfn_node, className, undoable)

    # set meta data
    new_value = encode_meta_data(data)

    if undoable:
        plug_name = _get_unique_plug_name(mfn_node, plug)
        cmds.setAttr(plug_name, new_value, type="string")
    else:
        plug.setString(new_value)


def get_meta_data(node, class_name=None):
    """
    Return metadata from a node. If `class_name` is given, return only metadata for that metaclass type.

    Args:
        node: A PyMel node or string node name.
        class_name: A string name of the metaclass type.

    Returns:
        A dict or python object representing the stored metadata.
    """
    mfn_node = utils.get_mfn_dependency_node(node)
    try:
        plug = mfn_node.findPlug(METADATA_ATTR)
        datastr = plug.asString()
    except RuntimeError:
        return {}
    else:
        ref_node = None
        if cmds.referenceQuery(str(node), isNodeReferenced=True):
            ref_node = cmds.referenceQuery(str(node), rfn=True)
        data = decode_meta_data(datastr, ref_node)

        if class_name is not None:
            return data.get(class_name, {})

        return data


def update_meta_data(node, class_name, data):
    """
    Updates existing meta data on a node for a meta class type.
    Only supports dict-type meta data

    Args:
        node: A PyMel node or string node name
        class_name: A string name of the meta class type
        data: A dict object containing meta data to add to the node
    """
    full_data = get_meta_data(node, class_name)
    if not isinstance(full_data, dict):
        raise ValueError("meta data for node '{0}' is not " "a dict and cannot be updated".format(node))
    full_data.update(data)
    set_meta_data(node, class_name, full_data)


def remove_meta_data(node, class_name=None, undoable=True):
    """
    Remove metadata from a node. If no `class_name` is given
    then all metadata is removed.

    Args:
        node: A PyMel node or string node name.
        class_name: A string name of the metaclass type.
        undoable: A bool, when True the change will be undoable

    Returns:
        True if node is fully clean of relevant metadata.
    """
    if not is_meta_node(node):
        return True

    mfn_node = utils.get_mfn_dependency_node(node)

    # this may become true if we find there are no
    # classes left after removing one
    remove_all_data = False

    if class_name is not None:
        # remove metadata for the given class only

        # make sure data attribute is unlocked
        data_plug = _get_meta_data_plug(mfn_node)
        if data_plug and data_plug.isLocked():
            return False

        # attempt to remove class attribute
        if not _remove_meta_class_attr(mfn_node, class_name, undoable):
            return False

        # remove class-specific data from all meta data
        # TODO(bsayre): add a partialDecodeMetaData for uses like this
        #   since we will only be modifying the core dict object and not
        #   using any meta data values (like nodes)
        data = decode_meta_data(data_plug.asString())
        if class_name in data:
            del data[class_name]
            new_value = encode_meta_data(data)

            if undoable:
                plug_name = _get_unique_plug_name(mfn_node, data_plug)
                cmds.setAttr(plug_name, new_value, type="string")
            else:
                data_plug.setString(new_value)

        # check if any classes left
        if len(data) == 0:
            remove_all_data = True

    else:
        # no class_name was given
        remove_all_data = True

    if remove_all_data:
        # remove all meta data from the node

        # make sure data attribute is unlocked
        data_plug = _get_meta_data_plug(mfn_node)
        if data_plug and data_plug.isLocked():
            return False

        # make sure all class attributes are unlocked
        class_plugs = [_get_meta_class_plug(mfn_node, c) for c in get_meta_classes(node)]
        for cp in class_plugs:
            if cp and cp.isLocked():
                return False

        # remove class attributes
        for classPlug in class_plugs:
            if classPlug:
                if undoable:
                    plug_name = _get_unique_plug_name(mfn_node, classPlug)
                    cmds.deleteAttr(plug_name)
                else:
                    mfn_node.removeAttribute(classPlug.attribute())

        # remove data attribute
        if data_plug:
            if undoable:
                plug_name = _get_unique_plug_name(mfn_node, data_plug)
                cmds.deleteAttr(plug_name)
            else:
                mfn_node.removeAttribute(data_plug.attribute())

    return True


def get_meta_classes(node):
    """
    Return the name of the metaclass types that the given node has metadata for.

    Args:
        node: A PyMel node or string node name
    """
    attrs = cmds.listAttr(str(node))
    meta_class_attrs = [a for a in attrs if a.startswith(METACLASS_ATTR_PREFIX)]
    classes = [a[len(METACLASS_ATTR_PREFIX) :] for a in meta_class_attrs]
    return classes
