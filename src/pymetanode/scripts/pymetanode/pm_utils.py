"""
PyMel wrappers for utils.
"""

from __future__ import annotations

import logging
from typing import Union, Optional

import maya.OpenMaya as api
import pymel.core as pm

from . import core_utils, utils

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


def has_attr(node: Union[api.MObject, pm.nt.DependNode, str], attr_name: str) -> bool:
    """
    Return True if the given node has the given attribute.

    Runs a fast version of has_attr if the node is an MObject, otherwise falls back to using `cmds.objExists`.

    Args:
        node: An MObject, PyNode, or string representing a node.
        attr_name: The name of the attribute to find.
    """
    if isinstance(node, pm.nt.DependNode):
        return core_utils.has_attr_fast(node.__apimobject__(), attr_name)
    return utils.has_attr(node, attr_name)


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
    return utils.get_m_object(node)


def get_mfn_node(node: Union[api.MObject, pm.nt.DependNode, str]) -> api.MFnDependencyNode:
    """
    Return an MFnDependencyNode for a node.

    Args:
        node: An MObject, PyNode, or string node name.
    """
    if isinstance(node, pm.nt.DependNode):
        if node.exists():
            return node.__apimfn__()
    return utils.get_mfn_node(node)


def is_node(obj: Union[api.MObject, pm.nt.DependNode, str]) -> bool:
    """
    Return True if an object represents a Maya node.

    Args:
        obj: A MObject, PyNode, uuid, node id, or string node name.
    """
    if isinstance(obj, pm.nt.DependNode):
        return True
    return utils.is_node(obj)


def get_uuid(node: Union[api.MObject, pm.nt.DependNode, str]) -> str:
    """
    Return the UUID of a node.

    Args:
        node: A MObject, PyNode, or string node name.
    """
    return core_utils.get_mfn_node_uuid(get_mfn_node(node))


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
            if core_utils.is_node_from_ref(node_name, ref_node):
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
            if core_utils.is_node_from_ref(node_name, ref_node):
                return node
    else:
        # take the first result
        return nodes[0]


def get_node_id(node: Union[api.MObject, pm.nt.DependNode, str]) -> str:
    """
    Return a string representation of a node that includes both its name and UUID.

    Args:
        node: A MObject, PyNode, or string node name.
    """
    return core_utils.get_mfn_node_id(get_mfn_node(node))


def find_node_by_id(node_id: str, ref_node: str = None) -> Optional[pm.PyNode]:
    """
    Find and return a node by id.

    Args:
        node_id: A string representing the node, in the format of either a UUID, or name[UUID] .
        ref_node: The name of the reference node that contains the node to find.
    """
    node_name, uuid = core_utils.parse_node_id(node_id)

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
