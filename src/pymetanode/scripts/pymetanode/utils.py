import re
import logging
from typing import Union, Optional, List

import maya.OpenMaya as api
import pymel.core as pm
from maya import cmds

__all__ = [
    "find_node_by_id",
    "find_node_by_name",
    "find_node_by_uuid",
    "get_m_object",
    "get_m_objects_by_plug",
    "get_mfn_dependency_node",
    "get_node_id",
    "get_uuid",
    "has_attr",
    "has_attr_fast",
    "is_node",
    "is_node_id",
    "is_uuid",
]

LOG = logging.getLogger(__name__)

# matches a node UUID, e.g. "ABC12345-AB12-AB12-AB12-ABCDEF123456"
UUID_REGEX = re.compile(r"[A-F0-9]{8}-([A-F0-9]{4}-){3}[A-F0-9]{12}")

# matches a node id, accepting also just a UUID, e.g. "myNode@ABC12345-AB12-AB12-AB12-ABCDEF123456"
NODE_ID_REGEX = re.compile(rf"((?P<name>\w+)@)?(?P<uuid>{UUID_REGEX.pattern})")


def has_attr(node: Union[api.MObject, pm.nt.DependNode, str], attr_name: str) -> bool:
    """
    Return True if the given node has the given attribute.

    Runs a fast version of has_attr if the node is an MObject, otherwise falls back to using `cmds.objExists`.

    Args:
        node: An MObject, PyNode, or string representing a node.
        attr_name: The name of the attribute to find.
    """
    if isinstance(node, api.MObject):
        return has_attr_fast(node, attr_name)
    elif isinstance(node, pm.nt.DependNode):
        return has_attr_fast(node.__apimobject__(), attr_name)
    else:
        return cmds.objExists(node + "." + attr_name)


def has_attr_fast(m_object: api.MObject, attr_name: str) -> bool:
    """
    Return True if the given node has the given attribute.

    Uses the api for performance, and performs no validation or type-checking.

    Args:
        m_object: An MObject node.
        attr_name: The name of the attribute to find.
    """
    try:
        api.MFnDependencyNode(m_object).attribute(attr_name)
        return True
    except RuntimeError:
        return False


def get_m_object(node: Union[pm.nt.DependNode, str]) -> Optional[api.MObject]:
    """
    Return the MObject for a node.

    Args:
        node: A PyNode or string node name.

    Returns:
        An MObject, or None if the node was not found.
    """
    if isinstance(node, pm.nt.DependNode):
        return node.__apimobject__()
    else:
        sel = api.MSelectionList()
        try:
            sel.add(node)
        except RuntimeError:
            # node does not exist or invalid arg
            return
        m_object = api.MObject()
        sel.getDependNode(0, m_object)
        return m_object


def get_m_objects_by_plug(plug_name: str) -> List[api.MObject]:
    """
    Return all nodes in the scene that have a specific plug.

    Args:
        plug_name: A string name of a maya plug to search for on nodes

    Returns:
        A list of MObjects that have the plug.
    """
    sel = api.MSelectionList()
    try:
        sel.add("*." + plug_name, True)
    except RuntimeError:
        pass

    count = sel.length()
    result = [api.MObject() for i in range(count)]
    [sel.getDependNode(i, result[i]) for i in range(count)]
    return result


def get_mfn_dependency_node(node: Union[api.MObject, pm.nt.DependNode, str]) -> api.MFnDependencyNode:
    """
    Return an MFnDependencyNode for a node.

    Args:
        node: An MObject, PyNode, or string node name.
    """
    if isinstance(node, api.MObject):
        return api.MFnDependencyNode(node)
    elif isinstance(node, pm.nt.DependNode):
        if node.exists():
            return node.__apimfn__()
    else:
        m_object = get_m_object(node)
        if m_object:
            return api.MFnDependencyNode(m_object)


def is_node(obj: Union[api.MObject, pm.nt.DependNode, str]) -> bool:
    """
    Return True if an object represents a Maya node.

    Args:
        obj: A MObject, PyNode, uuid, node id, or string node name.
    """
    if isinstance(obj, api.MObject) or isinstance(obj, pm.nt.DependNode):
        return True
    elif isinstance(obj, str):
        return is_node(obj) or is_uuid(obj) or cmds.objExists(obj)
    return False


def is_uuid(obj) -> bool:
    """
    Returns true if an object is a valid UUID, e.g. "ABC12345-AB12-AB12-AB12-ABCDEF123456"
    """
    return isinstance(obj, str) and UUID_REGEX.fullmatch(obj)


def get_uuid(node: Union[api.MObject, pm.nt.DependNode, str]) -> str:
    """
    Return the UUID of a node.

    Args:
        node: A MObject, PyNode, or string node name.
    """
    mfn_node = get_mfn_dependency_node(node)
    if mfn_node:
        return str(mfn_node.uuid().asString())
    return ""


def find_node_by_uuid(uuid: str, ref_node: str = None) -> Optional[pm.PyNode]:
    """
    Find and return a node by its UUID.

    Args:
        uuid: A string UUID representing the node.
        ref_node: The name of the reference node that contains the node to find.

    Returns:
        A PyNode with the UUID from the given reference, or None if not found.
    """
    nodes = pm.ls(uuid)
    if not nodes:
        return

    if ref_node:
        # return the first node that belongs to the given reference
        for node in nodes:
            node_name = str(node)
            if cmds.referenceQuery(node_name, isNodeReferenced=True):
                if cmds.referenceQuery(node_name, referenceNode=True) == ref_node:
                    return node
    else:
        # take the first result
        return nodes[0]


def find_node_by_name(name: str, ref_node: str = None) -> Optional[pm.PyNode]:
    """
    Find and return a node by its name.

    Args:
        name: A string representing the node name.
        ref_node: The name of the reference node that contains the node to find.

    Returns:
        A PyNode.
    """
    nodes = pm.ls(name)
    if not nodes:
        return

    if ref_node:
        # return the first node that belongs to the given reference
        for node in nodes:
            node_name = str(node)
            if cmds.referenceQuery(node_name, isNodeReferenced=True):
                if cmds.referenceQuery(node_name, referenceNode=True) == ref_node:
                    return node
    else:
        # take the first result
        return nodes[0]


def is_node_id(obj):
    """
    Return true if an object is a valid node id, e.g. "myNode@ABC12345-AB12-AB12-AB12-ABCDEF123456"
    """
    return isinstance(obj, str) and NODE_ID_REGEX.fullmatch(obj)


def get_node_id(node: Union[api.MObject, pm.nt.DependNode, str]) -> str:
    """
    Return a string representation of a node that includes both its name and UUID.

    Args:
        node: A MObject, PyNode, or string node name.
    """
    mfn_node = get_mfn_dependency_node(node)
    if mfn_node:
        return f"{mfn_node.name()}@{mfn_node.uuid().asString()}"
    return ""


def find_node_by_id(node_id: str, ref_node: str = None) -> Optional[pm.PyNode]:
    """
    Find and return a node by id.

    Args:
        node_id: A string representing the node, in the format of either a UUID, or name[UUID] .
        ref_node: The name of the reference node that contains the node to find.
    """
    match = NODE_ID_REGEX.fullmatch(node_id)
    if not match:
        raise ValueError("Not a valid node id: %s" % node_id)

    node_name = match.groupdict()["name"]
    uuid = match.groupdict()["uuid"]

    # try finding by UUID first
    node = find_node_by_uuid(uuid, ref_node)
    if node:
        return node

    # try finding by name as a fallback
    if node_name:
        node = find_node_by_name(node_name, ref_node)
        if node:
            return node

    LOG.error("Could not find node by UUID or name: %s", node_id)
    return None
