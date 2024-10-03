"""
The core functions of pymetanode, with support for PyMel objects.
Provides utils for adding, settings, and removing metadata.
"""

from __future__ import annotations

from typing import Any, Union, Optional

import maya.OpenMaya as api
import pymel.core as pm

from . import core
from . import pm_utils
from . import utils
from .core import MetadataEncoder, MetadataController

__all__ = [
    "decode_metadata",
    "decode_metadata_value",
    "encode_metadata",
    "encode_metadata_value",
    "find_meta_nodes",
    "get_metadata",
    "has_metaclass",
    "is_meta_node",
    "remove_metadata",
    "set_all_metadata",
    "set_metadata",
    "update_metadata",
]


class PyMelMetadataEncoder(MetadataEncoder):
    """
    Metadata encoder/decoder that handles PyMel nodes
    """

    def encode_metadata_value(self, value: Any) -> Any:
        if isinstance(value, pm.nt.DependNode):
            return utils.get_node_id(value)
        return super().encode_metadata_value(value)

    def is_node(self, value: Any) -> bool:
        return pm_utils.is_node(value)

    def get_node_id(self, value: Any) -> str:
        return pm_utils.get_node_id(value)

    def find_node_by_id(self, node_id: str, ref_node: str = None) -> Optional[Any]:
        # return PyNodes instead of node names
        return pm_utils.find_node_by_id(node_id, ref_node)


class PyMelMetadataController(MetadataController):
    _default_encoder_cls = PyMelMetadataEncoder

    @classmethod
    def _get_mfn_node(cls, node: Any) -> api.MFnDependencyNode:
        return pm_utils.get_mfn_node(node)


def encode_metadata(data: Any) -> str:
    """
    Return the given metadata encoded into a string.

    Args:
        data: The data to serialize.
    """
    return PyMelMetadataEncoder().encode_metadata(data)


def encode_metadata_value(value: Any) -> Any:
    """
    Return a metadata value, possibly encoding it into an alternate format that supports string serialization.

    Handles special data types like Maya nodes.

    Args:
        value: Any python value to be encoded.

    Returns:
        The encoded value, or the unchanged value if no encoding was necessary.
    """
    return PyMelMetadataEncoder().encode_metadata_value(value)


def decode_metadata(data: str, ref_node: str = None) -> Any:
    """
    Parse the given metadata and return it as a valid python object.

    Args:
        data: A string representing encoded metadata.
        ref_node: The name of the reference node that contains any nodes in the metadata.
    """
    return PyMelMetadataEncoder().decode_metadata(data, ref_node)


def decode_metadata_value(value: str, ref_node: str = None) -> Any:
    """
    Parse string formatted metadata and return the resulting python object.

    Args:
        value: A str representing encoded metadata.
        ref_node: The name of the reference node that contains any nodes in the metadata.
    """
    return PyMelMetadataEncoder().decode_metadata_value(value, ref_node)


def is_meta_node(node: Union[api.MObject, pm.nt.DependNode, str]) -> bool:
    """
    Return True if the given node has any metadata.

    Args:
        node: An MObject, PyNode, or string representing a node.
    """
    return pm_utils.has_attr(node, core.METADATA_ATTR)


def has_metaclass(node: Union[api.MObject, pm.nt.DependNode, str], class_name: str) -> bool:
    """
    Return True if the given node has data for the given metaclass type

    Args:
        node: An MObject, PyNode, or string representing a node.
        class_name: The metaclass name to check for.
    """
    return pm_utils.has_attr(node, core.METACLASS_ATTR_PREFIX + class_name)


def find_meta_nodes(class_name: str = None, as_py_nodes=True) -> Union[list[pm.PyNode], list[api.MObject]]:
    """
    Return a list of all meta nodes of the given class type. If no class is given,
    all nodes with metadata are returned.

    Args:
        class_name: The metaclass name to search for, or None to find all metadata nodes.
        as_py_nodes: Return a list of PyNodes. If false, return a list of MObjects.

    Returns:
        A list of PyNodes or MObjects that have metadata.
    """
    objs: list[api.MObject] = core.find_meta_nodes(class_name)

    if as_py_nodes:
        return [pm.PyNode(obj) for obj in objs]
    else:
        return objs


def get_metadata(node: Union[pm.nt.DependNode, str], class_name: str = None) -> Union[dict, Any]:
    """
    Return the metadata on a node. If `class_name` is given, return only data for that metaclass.

    Args:
        node: A PyNode or string node name.
        class_name: The metaclass of the data to find and return.

    Returns:
        A dict if returning all metadata, or potentially any value if returning data for a specific class.
    """
    return PyMelMetadataController.from_node(node).get_metadata(class_name)


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
    return PyMelMetadataController.from_node(node, undoable=undoable).set_metadata(class_name, data, replace)


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
    return PyMelMetadataController.from_node(node, undoable=undoable).set_all_metadata(data)


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
    return PyMelMetadataController.from_node(node).update_metadata(class_name, data)


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

    return PyMelMetadataController.from_node(node, undoable=undoable).remove_metadata(class_name)
