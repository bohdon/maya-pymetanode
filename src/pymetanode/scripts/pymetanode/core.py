import ast
import re
from typing import Optional, Any, List, Union

import pymel.core as pm
from maya import cmds
import maya.OpenMaya as api

from . import utils

__all__ = [
    "decode_metadata",
    "decode_metadata_value",
    "encode_metadata",
    "encode_metadata_value",
    "find_meta_nodes",
    "get_metaclass_names",
    "get_metadata",
    "has_metaclass",
    "is_meta_node",
    "remove_metadata",
    "set_all_metadata",
    "set_metadata",
    "update_metadata",
]

METACLASS_ATTR_PREFIX = "pyMetaClass_"
METADATA_ATTR = "pyMetaData"
VALID_CLASS_ATTR = re.compile(r"^[_a-z0-9]*$", re.IGNORECASE)


def _get_metadata_plug(mfn_node: api.MFnDependencyNode) -> Optional[api.MPlug]:
    """
    Return the MPlug for the metadata attribute on a node.

    Args:
        mfn_node: An MFnDependencyNode with a node.

    Returns:
        The MPlug for the metadata attribute, or None if not found.
    """
    try:
        return mfn_node.findPlug(METADATA_ATTR)
    except RuntimeError:
        pass


def _get_metaclass_plug(mfn_node: api.MFnDependencyNode, class_name: str) -> Optional[api.MPlug]:
    """
    Return the MPlug for a metaclass attribute on a node.

    Args:
        mfn_node: An MFnDependencyNode with a node.
        class_name: The metaclass name for the plug to find.

    Returns:
        The MPlug for the metaclass attribute, or None if not found.
    """
    attr_name = METACLASS_ATTR_PREFIX + class_name
    try:
        return mfn_node.findPlug(attr_name)
    except RuntimeError:
        pass


def _get_unique_node_name(mfn_node: api.MFnDependencyNode) -> str:
    """
    Return the unique name of a Dependency node.

    If the node is already unique, simply returns its name, otherwise returns the unique path to the node.

    Args:
        mfn_node: An MFnDependencyNode with a node.

    Returns:
        The unique name or path (str) of the node. E.g. 'node' or 'my|node'
    """
    if not mfn_node.hasUniqueName():
        node = mfn_node.object()
        if node.hasFn(api.MFn.kDagNode):
            mfn_dag = api.MFnDagNode(mfn_node.object())
            dag_path = api.MDagPath()
            mfn_dag.getPath(dag_path)
            return dag_path.partialPathName()
    return mfn_node.name()


def _get_unique_plug_name(mfn_node: api.MFnDependencyNode, plug: api.MPlug) -> str:
    """
    Return the unique name of a MPlug, including its nodes name.

    Args:
        mfn_node: An MFnDependencyNode with a node.
            Provided for performance reasons, since it is common to have both this
            and the MPlug when needing the plug name in this package.
        plug: A MPlug of a node.

    Returns:
        The unique name or path including attribute (str) of the plug. E.g. 'my|node.myPlug'
    """
    return _get_unique_node_name(mfn_node) + "." + plug.partialName()


def _get_or_create_metadata_plug(mfn_node: api.MFnDependencyNode, undoable=True) -> api.MPlug:
    """
    Return the MPlug for the metadata attribute on a node, adding the attribute if it does not already exist.

    Args:
        mfn_node: An MFnDependencyNode with a node.
        undoable: Make the operation undoable by using cmds instead of the api.

    Returns:
        The MPlug for the metadata attribute.
    """
    try:
        plug = mfn_node.findPlug(METADATA_ATTR)
    except RuntimeError:
        if undoable:
            name = _get_unique_node_name(mfn_node)
            cmds.addAttr(name, longName=METADATA_ATTR, dataType="string")
        else:
            mfn_attr = api.MFnTypedAttribute()
            attr = mfn_attr.create(METADATA_ATTR, METADATA_ATTR, api.MFnData.kString)
            mfn_node.addAttribute(attr)
        plug = mfn_node.findPlug(METADATA_ATTR)

    return plug


def _add_metaclass_attr(mfn_node: api.MFnDependencyNode, class_name: str, undoable=True) -> None:
    """
    Add a metaclass attribute to a node.

    Does nothing if the attribute already exists.

    Args:
        mfn_node: An MFnDependencyNode with a node.
        class_name: The metadata class name.
        undoable: Make the operation undoable by using cmds instead of the api.

    Raises:
        ValueError: The class_name was invalid.
    """
    if not VALID_CLASS_ATTR.match(class_name):
        raise ValueError("Invalid metaclass name: " + class_name)

    class_attr = METACLASS_ATTR_PREFIX + class_name

    try:
        mfn_node.attribute(class_attr)
    except RuntimeError:
        if undoable:
            name = _get_unique_node_name(mfn_node)
            cmds.addAttr(name, longName=class_attr, attributeType="short")
        else:
            mfn_attr = api.MFnNumericAttribute()
            attr = mfn_attr.create(class_attr, class_attr, api.MFnNumericData.kShort)
            mfn_node.addAttribute(attr)


def _remove_metaclass_attr(mfn_node: api.MFnDependencyNode, class_name: str, undoable=True) -> bool:
    """
    Remove a metaclass attribute from a node.

    Does nothing if the attribute does not exist.

    Args:
        mfn_node: An MFnDependencyNode with a node.
        class_name: The metadata class name.
        undoable: Make the operation undoable by using cmds instead of the api.

    Returns:
        True if the attr was removed or didn't exist, False if it couldn't be removed.
    """
    class_plug = _get_metaclass_plug(mfn_node, class_name)
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


def encode_metadata(data: Any) -> str:
    """
    Return the given metadata encoded into a string.

    Args:
        data: The data to serialize.
    """
    return repr(encode_metadata_value(data))


def encode_metadata_value(value: Any) -> Any:
    """
    Return a metadata value, possibly encoding it into an alternate format that supports string serialization.

    Handles special data types like Maya nodes.

    Args:
        value: Any python value to be encoded.

    Returns:
        The encoded value, or the unchanged value if no encoding was necessary.
    """
    # TODO (bsayre): add support for custom encoding/decoding rules
    if isinstance(value, dict):
        result = {}
        for k, v in value.items():
            result[k] = encode_metadata_value(v)
        return result
    elif isinstance(value, (list, tuple)):
        return value.__class__([encode_metadata_value(v) for v in value])
    elif isinstance(value, pm.nt.DependNode):
        return utils.get_node_id(value)
    else:
        return value


def decode_metadata(data: str, ref_node: str = None) -> Any:
    """
    Parse the given metadata and return it as a valid python object.

    Args:
        data: A string representing encoded metadata.
        ref_node: The name of the reference node that contains any nodes in the metadata.
    """
    if not data:
        return {}

    try:
        data = ast.literal_eval(data.replace("\r", ""))
    except Exception as e:
        raise ValueError(f"Failed to decode meta data: {e}")
    return decode_metadata_value(data, ref_node)


def decode_metadata_value(value: str, ref_node: str = None) -> Any:
    """
    Parse string formatted metadata and return the resulting python object.

    Args:
        value: A str representing encoded metadata.
        ref_node: The name of the reference node that contains any nodes in the metadata.
    """
    if isinstance(value, dict):
        result = {}
        for k, v in value.items():
            result[k] = decode_metadata_value(v, ref_node)
        return result
    elif isinstance(value, (list, tuple)):
        return value.__class__([decode_metadata_value(v, ref_node) for v in value])
    elif utils.is_node_id(value):
        return utils.find_node_by_id(value, ref_node)
    else:
        return value


def is_meta_node(node: Union[api.MObject, pm.nt.DependNode, str]) -> bool:
    """
    Return True if the given node has any metadata.

    Args:
        node: An MObject, PyNode, or string representing a node.
    """
    return utils.has_attr(node, METADATA_ATTR)


def has_metaclass(node: Union[api.MObject, pm.nt.DependNode, str], class_name: str) -> bool:
    """
    Return True if the given node has data for the given metaclass type

    Args:
        node: An MObject, PyNode, or string representing a node.
        class_name: The metaclass name to check for.
    """
    return utils.has_attr(node, METACLASS_ATTR_PREFIX + class_name)


def find_meta_nodes(class_name: str = None, as_py_nodes=True) -> Union[List[pm.PyNode], List[api.MObject]]:
    """
    Return a list of all meta nodes of the given class type. If no class is given,
    all nodes with metadata are returned.

    Args:
        class_name: The metaclass name to search for, or None to find all metadata nodes.
        as_py_nodes: Return a list of PyNodes. If false, return a list of MObjects.

    Returns:
        A list of PyNodes or MObjects that have metadata.
    """
    plug_name = f"{METACLASS_ATTR_PREFIX}{class_name}" if class_name else METADATA_ATTR

    objs = utils.get_m_objects_by_plug(plug_name)

    if as_py_nodes:
        return [pm.PyNode(obj) for obj in objs]
    else:
        return objs


def set_metadata(node: Union[pm.nt.DependNode, str], class_name: str, data: Any, undoable=True, replace=False):
    """
    Set the metadata for a metaclass type on a node.

    The class_name must be a valid attribute name.

    Args:
        node: The node on which to set data.
        class_name: The data's metaclass type name.
        data: The data to serialize and store on the node.
        undoable: Make the operation undoable by using cmds instead of the api.
        replace: Replace all metadata on the node with the new metadata.
            This uses set_all_metadata and can be much faster with large data sets,
            but will remove data for any other metaclass types.
    """
    if replace:
        set_all_metadata(node, {class_name: data}, undoable)
        return

    mfn_node = utils.get_mfn_dependency_node(node)
    plug = _get_or_create_metadata_plug(mfn_node, undoable)
    _add_metaclass_attr(mfn_node, class_name, undoable)

    # determine the reference to use when decoding node data
    ref_node = None
    node_name = str(node)
    if cmds.referenceQuery(node_name, isNodeReferenced=True):
        ref_node = cmds.referenceQuery(node_name, referenceNode=True)

    # update meta data
    full_data = decode_metadata(plug.asString(), ref_node)
    full_data[class_name] = data
    new_value = encode_metadata(full_data)

    if undoable:
        plug_name = _get_unique_plug_name(mfn_node, plug)
        cmds.setAttr(plug_name, new_value, type="string")
    else:
        plug.setString(new_value)


def set_all_metadata(node: Union[pm.nt.DependNode, str], data: dict, undoable=True):
    """
    Set all metadata on a node. This is faster because the existing data
    on the node is not retrieved first and then modified.

    The data must be of the form {"<metaclass>": <data>} otherwise errors
    may occur when retrieving it later.

    New metaclass attributes will be added automatically, but existing metaclass
    attributes will not be removed. If old metaclass attributes on this node will
    no longer be applicable, they should be removed with `remove_metadata` first.

    Args:
        node: The node on which to set data.
        data: The data to serialize and store on the node.
        undoable: Make the operation undoable by using cmds instead of the api.
    """
    mfn_node = utils.get_mfn_dependency_node(node)
    plug = _get_or_create_metadata_plug(mfn_node, undoable)

    # add class attributes
    if data:
        for class_name in data.keys():
            _add_metaclass_attr(mfn_node, class_name, undoable)

    # set meta data
    new_value = encode_metadata(data)

    if undoable:
        plug_name = _get_unique_plug_name(mfn_node, plug)
        cmds.setAttr(plug_name, new_value, type="string")
    else:
        plug.setString(new_value)


def get_metadata(node: Union[pm.nt.DependNode, str], class_name: str = None) -> Union[dict, Any]:
    """
    Return the metadata on a node. If `class_name` is given, return only data for that metaclass.

    Args:
        node: A PyNode or string node name.
        class_name: The metaclass of the data to find and return.

    Returns:
        A dict if returning all metadata, or potentially any value if returning data for a specific class.
    """
    mfn_node = utils.get_mfn_dependency_node(node)
    try:
        plug = mfn_node.findPlug(METADATA_ATTR)
        datastr = plug.asString()
    except RuntimeError:
        return {}
    else:
        # determine the reference node to use when decoding node data
        ref_node = None
        node_name = str(node)
        if cmds.referenceQuery(node_name, isNodeReferenced=True):
            ref_node = cmds.referenceQuery(node_name, referenceNode=True)
        data = decode_metadata(datastr, ref_node)

        if class_name is not None:
            return data.get(class_name, {})

        return data


def update_metadata(node: Union[pm.nt.DependNode, str], class_name: str, data: dict):
    """
    Update existing dict metadata on a node for a metaclass type.

    Args:
        node: A PyNode or string node name.
        class_name: A string name of the metaclass type.
        data: A dict object containing metadata to add to the node.

    Raises:
        ValueError: The existing metadata on the node for the given metaclass was not a dict.
    """
    full_data = get_metadata(node, class_name)

    if not isinstance(full_data, dict):
        raise ValueError(f"Expected dict metadata for '{class_name}', but got '{type(full_data)}' from node: '{node}'")

    full_data.update(data)
    set_metadata(node, class_name, full_data)


def remove_metadata(node: Union[pm.nt.DependNode, str], class_name: str = None, undoable=True) -> bool:
    """
    Remove metadata from a node. If no `class_name` is given
    then all metadata is removed.

    Args:
        node: A PyNode or string node name.
        class_name: A string name of the metaclass type.
        undoable: Make the operation undoable by using cmds instead of the api.

    Returns:
        True if node is fully clean of relevant metadata.
    """
    if not is_meta_node(node):
        return True

    mfn_node = utils.get_mfn_dependency_node(node)

    # make sure data attribute is unlocked
    data_plug = _get_metadata_plug(mfn_node)
    if data_plug and data_plug.isLocked():
        return False

    # this may become true if we find there are no
    # classes left after removing the target one
    remove_all_data = False

    if class_name:
        # attempt to remove class attribute
        if not _remove_metaclass_attr(mfn_node, class_name, undoable):
            return False

        # remove just the data for this metaclass
        # TODO(bsayre): add a `partial_decode_metadata` for uses like this since we will only be modifying
        #   the core dict object and not using any meta data values (like nodes)
        data = decode_metadata(data_plug.asString())
        if class_name in data:
            del data[class_name]

            # set the new metadata
            new_value = encode_metadata(data)
            if undoable:
                plug_name = _get_unique_plug_name(mfn_node, data_plug)
                cmds.setAttr(plug_name, new_value, type="string")
            else:
                data_plug.setString(new_value)

            if not data:
                # no data left, remove all metadata attributes
                remove_all_data = True

    else:
        # no class_name was given, remove everything
        remove_all_data = True

    if remove_all_data:
        class_plugs = [_get_metaclass_plug(mfn_node, c) for c in get_metaclass_names(node)]
        class_plugs = [c for c in class_plugs if c]

        # make sure all class attributes are unlocked
        for class_plug in class_plugs:
            if class_plug.isLocked():
                return False

        # remove class attributes
        for classPlug in class_plugs:
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


def get_metaclass_names(node: Union[pm.nt.DependNode, str]) -> List[str]:
    """
    Return all metaclass names that a node has metadata for.

    Args:
        node: A PyNode, or string representing a node
    """
    attrs: List[str] = cmds.listAttr(str(node))
    metaclass_attrs = [a for a in attrs if a.startswith(METACLASS_ATTR_PREFIX)]
    metaclass_names = [a[len(METACLASS_ATTR_PREFIX) :] for a in metaclass_attrs]
    return metaclass_names
