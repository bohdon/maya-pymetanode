"""
Utils for working with nodes and the maya api.
"""

from __future__ import annotations

import logging
from typing import Union, Optional

import maya.OpenMaya as api
from maya import cmds

from . import core_utils

__all__ = [
    "find_node_by_id",
    "find_node_by_name",
    "find_node_by_uuid",
    "get_m_object",
    "get_mfn_node",
    "get_node_id",
    "get_uuid",
    "has_attr",
    "is_node",
]

LOG = logging.getLogger(__name__)


def has_attr(node: Union[api.MObject, str], attr_name: str) -> bool:
    """
    Return True if the given node has the given attribute.

    Runs a fast version of has_attr if the node is an MObject, otherwise falls back to using `cmds.objExists`.

    Args:
        node: An MObject or string representing a node.
        attr_name: The name of the attribute to find.
    """
    if isinstance(node, api.MObject):
        return core_utils.has_attr_fast(node, attr_name)
    else:
        return cmds.objExists(node + "." + attr_name)


def get_m_object(node: str) -> Optional[api.MObject]:
    """
    Return the MObject for a node.

    Args:
        node: A string node name.

    Returns:
        An MObject, or None if the node was not found.
    """
    sel = api.MSelectionList()
    try:
        sel.add(node)
    except RuntimeError:
        # node does not exist or invalid arg
        return
    m_object = api.MObject()
    sel.getDependNode(0, m_object)
    return m_object


def get_mfn_node(node: Union[api.MObject, str]) -> api.MFnDependencyNode:
    """
    Return an MFnDependencyNode for a node.

    Args:
        node: An MObject, or string node name.
    """
    if isinstance(node, api.MObject):
        return api.MFnDependencyNode(node)
    else:
        m_object = get_m_object(node)
        if m_object:
            return api.MFnDependencyNode(m_object)


def is_node(obj: Union[api.MObject, str]) -> bool:
    """
    Return True if an object represents a Maya node.

    Args:
        obj: A MObject, uuid, node id, or string node name.
    """
    if isinstance(obj, api.MObject):
        return True
    elif isinstance(obj, str):
        return core_utils.is_node_id(obj) or core_utils.is_uuid(obj) or cmds.objExists(obj)
    return False


def get_uuid(node: Union[api.MObject, str]) -> str:
    """
    Return the UUID of a node.

    Args:
        node: A MObject or string node name.
    """
    return core_utils.get_mfn_node_uuid(get_mfn_node(node))


def find_node_by_uuid(uuid: str, ref_node: str = None) -> Optional[str]:
    """
    Find and return a node by its UUID.

    Args:
        uuid: A string UUID representing the node.
        ref_node: The name of the reference node that contains the node to find.

    Returns:
        The name of a node with the UUID from the given reference, or None if not found.
    """
    node_names: list[str] = cmds.ls(uuid)
    if not node_names:
        return

    if ref_node:
        # return the first node that belongs to the given reference
        for node_name in node_names:
            if core_utils.is_node_from_ref(node_name, ref_node):
                return node_name
    else:
        # take the first result
        return node_names[0]


def find_node_by_name(name: str, ref_node: str = None) -> Optional[str]:
    """
    Find and return a node by its name, selecting the one from a specific reference if given.

    Args:
        name: A string representing the node name.
        ref_node: The name of the reference node that contains the node to find.

    Returns:
        A string node name.
    """
    node_names: list[str] = cmds.ls(name)
    if not node_names:
        return

    if ref_node:
        # return the first node that belongs to the given reference
        for node_name in node_names:
            if core_utils.is_node_from_ref(node_name, ref_node):
                return node_name
    else:
        # take the first result
        return node_names[0]


def get_node_id(node: Union[api.MObject, str]) -> str:
    """
    Return a string representation of a node that includes both its name and UUID.

    Args:
        node: A MObject or string node name.
    """
    return core_utils.get_mfn_node_id(get_mfn_node(node))


def find_node_by_id(node_id: str, ref_node: str = None) -> Optional[str]:
    """
    Find and return a node by id.

    Args:
        node_id: A string representing the node, in the format of either a UUID, or name@UUID.
        ref_node: The name of the reference node that contains the node to find.
    """
    node_name, uuid = core_utils.parse_node_id(node_id)

    # try finding by UUID first
    node_name = find_node_by_uuid(uuid, ref_node)
    if node_name:
        return node_name

    # try finding by name as a fallback
    if node_name:
        node_name = find_node_by_name(node_name, ref_node)
        if node_name:
            return node_name

    LOG.error("Could not find node by UUID or name: %s", node_id)
    return None
