"""
Utils for working with nodes and the maya api.
"""

from __future__ import annotations

import logging
import re

import maya.OpenMaya as api
from maya import cmds

__all__ = [
    "get_m_objects_by_plug",
    "get_mfn_node_id",
    "get_mfn_node_uuid",
    "has_attr_fast",
    "is_node_from_ref",
    "is_node_id",
    "is_uuid",
    "parse_node_id",
]

LOG = logging.getLogger(__name__)

# matches a node UUID, e.g. "ABC12345-AB12-AB12-AB12-ABCDEF123456"
UUID_REGEX = re.compile(r"[A-F0-9]{8}-([A-F0-9]{4}-){3}[A-F0-9]{12}")

# matches a node id, accepting also just a UUID, e.g. "myNode@ABC12345-AB12-AB12-AB12-ABCDEF123456"
NODE_ID_REGEX = re.compile(rf"((?P<name>[\w:]+)@)?(?P<uuid>{UUID_REGEX.pattern})")


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


def get_m_objects_by_plug(plug_name: str) -> list[api.MObject]:
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
    result = [api.MObject() for _ in range(count)]
    [sel.getDependNode(i, result[i]) for i in range(count)]
    return result


def get_mfn_node_uuid(mfn_node: api.MFnDependencyNode):
    if mfn_node:
        return str(mfn_node.uuid().asString())
    return ""


def is_uuid(obj) -> bool:
    """
    Returns true if an object is a valid UUID, e.g. "ABC12345-AB12-AB12-AB12-ABCDEF123456"
    """
    return isinstance(obj, str) and UUID_REGEX.fullmatch(obj)


def is_node_from_ref(node_name: str, ref_node: str):
    if not ref_node:
        raise ValueError("ref_node invalid")

    if cmds.referenceQuery(node_name, isNodeReferenced=True):
        return cmds.referenceQuery(node_name, referenceNode=True) == ref_node
    return False


def is_node_id(obj):
    """
    Return true if an object is a valid node id, e.g. "myNode@ABC12345-AB12-AB12-AB12-ABCDEF123456"
    """
    return isinstance(obj, str) and NODE_ID_REGEX.fullmatch(obj)


def get_mfn_node_id(mfn_node: api.MFnDependencyNode):
    if mfn_node:
        return f"{mfn_node.name()}@{mfn_node.uuid().asString()}"
    return ""


def parse_node_id(node_id: str) -> (str, str):
    """
    Parse a node id and return a tuple of (node_name, uuid)

    Args:
        node_id: A string representing the node, in the format of either a UUID, or name@UUID.
    """
    match = NODE_ID_REGEX.fullmatch(node_id)
    if not match:
        raise ValueError("Not a valid node id: %s" % node_id)

    node_name = match.groupdict()["name"]
    uuid = match.groupdict()["uuid"]

    return node_name, uuid
