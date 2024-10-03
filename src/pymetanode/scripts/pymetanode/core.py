"""
The core functionality of pymetanode for adding and removing metadata.
"""

from __future__ import annotations

import ast
import re
from typing import Optional, Any, Union

import maya.OpenMaya as api
from maya import cmds

from . import utils, core_utils

METACLASS_ATTR_PREFIX = "pyMetaClass_"
METADATA_ATTR = "pyMetaData"
VALID_CLASS_ATTR = re.compile(r"^[_a-z0-9]*$", re.IGNORECASE)


def find_meta_nodes(class_name: str = None) -> list[api.MObject]:
    """
    Return a list of all meta nodes of the given class type. If no class is given,
    all nodes with metadata are returned.

    Args:
        class_name: The metaclass name to search for, or None to find all metadata nodes.

    Returns:
        A list of PyNodes or MObjects that have metadata.
    """
    plug_name = f"{METACLASS_ATTR_PREFIX}{class_name}" if class_name else METADATA_ATTR
    return core_utils.get_m_objects_by_plug(plug_name)


def get_metaclass_names(node_name: str) -> list[str]:
    """
    Return all metaclass names that a node has metadata for.

    Args:
        node_name: A string node name.
    """
    attrs: list[str] = cmds.listAttr(node_name)
    metaclass_attrs = [a for a in attrs if a.startswith(METACLASS_ATTR_PREFIX)]
    metaclass_names = [a[len(METACLASS_ATTR_PREFIX) :] for a in metaclass_attrs]
    return metaclass_names


def get_unique_node_name(mfn_node: api.MFnDependencyNode) -> str:
    """
    Return the unique name of a MFnDependencyNode.

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


def get_metadata_plug(mfn_node: api.MFnDependencyNode) -> Optional[api.MPlug]:
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


def get_metaclass_plug(mfn_node: api.MFnDependencyNode, class_name: str) -> Optional[api.MPlug]:
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


def get_unique_plug_name(mfn_node: api.MFnDependencyNode, plug: api.MPlug) -> str:
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
    return get_unique_node_name(mfn_node) + "." + plug.partialName()


class MetadataEncoder(object):
    """
    Base class for an encoder/decoder that processes data when
    storing and loading it from nodes.
    """

    def encode_metadata(self, data: Any) -> str:
        """
        Return the given metadata encoded into a string.

        Args:
            data: The data to serialize.
        """
        return repr(self.encode_metadata_value(data))

    def encode_metadata_value(self, value: Any) -> Any:
        """
        Return a metadata value, possibly encoding it into an alternate format that supports string serialization.

        Handles special data types like Maya nodes.

        Args:
            value: Any python value to be encoded.

        Returns:
            The encoded value, or the unchanged value if no encoding was necessary.
        """
        if isinstance(value, dict):
            result = {}
            for k, v in value.items():
                result[k] = self.encode_metadata_value(v)
            return result
        elif isinstance(value, (list, tuple)):
            return value.__class__([self.encode_metadata_value(v) for v in value])
        elif self.is_node(value):
            return self.get_node_id(value)
        else:
            return value

    def decode_metadata(self, data: str, ref_node: str = None) -> Any:
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
        return self.decode_metadata_value(data, ref_node)

    def decode_metadata_value(self, value: str, ref_node: str = None) -> Any:
        """
        Parse string formatted metadata and return the resulting python object.

        Args:
            value: A str representing encoded metadata.
            ref_node: The name of the reference node that contains any nodes in the metadata.
        """
        if isinstance(value, dict):
            result = {}
            for k, v in value.items():
                result[k] = self.decode_metadata_value(v, ref_node)
            return result
        elif isinstance(value, (list, tuple)):
            return value.__class__([self.decode_metadata_value(v, ref_node) for v in value])
        elif core_utils.is_node_id(value):
            return self.find_node_by_id(value, ref_node)
        else:
            return value

    def is_node(self, value: Any) -> bool:
        return utils.is_node(value)

    def get_node_id(self, value: Any) -> str:
        return utils.get_node_id(value)

    def find_node_by_id(self, node_id: str, ref_node: str = None) -> Optional[Any]:
        return utils.find_node_by_id(node_id, ref_node)


class MetadataController(object):
    # the default encoder class to use if none is specified
    _default_encoder_cls = MetadataEncoder

    @classmethod
    def from_node(cls, node: Any, encoder: MetadataEncoder = None, undoable=True) -> MetadataController:
        """
        Create a MetadataController from a node.
        Uses cls._get_mfn_node(node) to retrieve the mfn_node.
        """
        mfn_node = cls._get_mfn_node(node)
        return cls(mfn_node, encoder, undoable=undoable)

    @classmethod
    def _get_mfn_node(cls, node: Any) -> api.MFnDependencyNode:
        return utils.get_mfn_node(node)

    def __init__(self, mfn_node: api.MFnDependencyNode, encoder: MetadataEncoder = None, undoable=True):
        """
        Args:
            mfn_node: A MFnDependencyNode to operate on.
            encoder: A MetadataEncoder to use for reading/writing values.
            undoable: If true, make operations undoable by using cmds (slightly less performant) instead of the api.
        """
        if encoder is None:
            encoder = self._default_encoder_cls()

        self.mfn_node = mfn_node
        self.encoder = encoder
        self.undoable = undoable

    def get_ref_node(self) -> Optional[str]:
        """
        Return the name of the reference to use when encoding or decoding nodes.
        """
        node_name = get_unique_node_name(self.mfn_node)
        if cmds.referenceQuery(node_name, isNodeReferenced=True):
            return cmds.referenceQuery(node_name, referenceNode=True)

    def get_metadata(self, class_name: str = None) -> Union[dict, Any]:
        """
        Return the metadata on a node. If `class_name` is given, return only data for that metaclass.

        Args:
            class_name: The metaclass of the data to find and return.

        Returns:
            A dict if returning all metadata, or potentially any value if returning data for a specific class.
        """
        try:
            plug = self.mfn_node.findPlug(METADATA_ATTR)
            datastr = plug.asString()
        except RuntimeError:
            return {}
        else:
            data = self.encoder.decode_metadata(datastr, self.get_ref_node())

            if class_name is not None:
                return data.get(class_name, {})

            return data

    def set_metadata(self, class_name: str, data: Any, replace=False):
        """
        Set the metadata for a metaclass type on the node.

        The class_name must be a valid attribute name.

        Args:
            class_name: The data's metaclass type name.
            data: The data to serialize and store on the node.
            replace: Replace all metadata on the node with the new metadata.
                This uses set_all_metadata and can be much faster with large data sets,
                but will remove data for any other metaclass types.
        """
        if replace:
            self.set_all_metadata({class_name: data})
            return

        plug = self._get_or_create_metadata_plug()
        self._add_metaclass_attr(class_name)

        # update meta data
        full_data = self.encoder.decode_metadata(plug.asString(), self.get_ref_node())
        full_data[class_name] = data
        new_value = self.encoder.encode_metadata(full_data)

        if self.undoable:
            plug_name = get_unique_plug_name(self.mfn_node, plug)
            cmds.setAttr(plug_name, new_value, type="string")
        else:
            plug.setString(new_value)

    def set_all_metadata(self, data: dict):
        """
        Set all metadata on a node. This is faster because the existing data
        on the node is not retrieved first and then modified.

        The data must be of the form {"<metaclass>": <data>} otherwise errors
        may occur when retrieving it later.

        New metaclass attributes will be added automatically, but existing metaclass
        attributes will not be removed. If old metaclass attributes on this node will
        no longer be applicable, they should be removed with `remove_metadata` first.

        Args:
            data: The data to serialize and store on the node.
        """
        plug = self._get_or_create_metadata_plug()

        # add class attributes
        if data:
            for class_name in data.keys():
                self._add_metaclass_attr(class_name)

        # set meta data
        new_value = self.encoder.encode_metadata(data)

        if self.undoable:
            plug_name = get_unique_plug_name(self.mfn_node, plug)
            cmds.setAttr(plug_name, new_value, type="string")
        else:
            plug.setString(new_value)

    def update_metadata(self, class_name: str, data: dict):
        """
        Update existing dict metadata on a node for a metaclass type.

        Args:
            class_name: A string name of the metaclass type.
            data: A dict object containing metadata to add to the node.

        Raises:
            ValueError: The existing metadata on the node for the given metaclass was not a dict.
        """
        full_data = self.get_metadata(class_name)

        if not isinstance(full_data, dict):
            raise ValueError(
                f"Expected dict metadata for '{class_name}', but got '{type(full_data)}' from node: '{get_unique_node_name(self.mfn_node)}'"
            )

        full_data.update(data)
        self.set_metadata(class_name, full_data)

    def remove_metadata(self, class_name: str = None) -> bool:
        """
        Remove metadata from a node. If no `class_name` is given then all metadata is removed.

        Args:
            class_name: A string name of the metaclass type.

        Returns:
            True if node is fully clean of relevant metadata.
        """
        # make sure data attribute is unlocked
        data_plug = get_metadata_plug(self.mfn_node)
        if data_plug and data_plug.isLocked():
            return False

        # this may become true if we find there are no
        # classes left after removing the target one
        remove_all_data = False

        if class_name:
            # attempt to remove class attribute
            if not self._remove_metaclass_attr(class_name):
                return False

            # remove just the data for this metaclass
            # TODO(bsayre): add a `partial_decode_metadata` for uses like this since we will only be modifying
            #   the core dict object and not using any meta data values (like nodes)
            data = self.encoder.decode_metadata(data_plug.asString())
            if class_name in data:
                del data[class_name]

                # set the new metadata
                new_value = self.encoder.encode_metadata(data)
                if self.undoable:
                    plug_name = get_unique_plug_name(self.mfn_node, data_plug)
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
            node_name = get_unique_node_name(self.mfn_node)
            class_plugs = [get_metaclass_plug(self.mfn_node, c) for c in get_metaclass_names(node_name)]
            class_plugs = [c for c in class_plugs if c]

            # make sure all class attributes are unlocked
            for class_plug in class_plugs:
                if class_plug.isLocked():
                    return False

            # remove class attributes
            for classPlug in class_plugs:
                if self.undoable:
                    plug_name = get_unique_plug_name(self.mfn_node, classPlug)
                    cmds.deleteAttr(plug_name)
                else:
                    self.mfn_node.removeAttribute(classPlug.attribute())

            # remove data attribute
            if data_plug:
                if self.undoable:
                    plug_name = get_unique_plug_name(self.mfn_node, data_plug)
                    cmds.deleteAttr(plug_name)
                else:
                    self.mfn_node.removeAttribute(data_plug.attribute())

        return True

    def _get_or_create_metadata_plug(self) -> api.MPlug:
        """
        Return the MPlug for the metadata attribute on a node, adding the attribute if it does not already exist.

        Returns:
            The MPlug for the metadata attribute.
        """
        try:
            plug = self.mfn_node.findPlug(METADATA_ATTR)
        except RuntimeError:
            if self.undoable:
                name = get_unique_node_name(self.mfn_node)
                cmds.addAttr(name, longName=METADATA_ATTR, dataType="string")
            else:
                mfn_attr = api.MFnTypedAttribute()
                attr = mfn_attr.create(METADATA_ATTR, METADATA_ATTR, api.MFnData.kString)
                self.mfn_node.addAttribute(attr)
            plug = self.mfn_node.findPlug(METADATA_ATTR)

        return plug

    def _add_metaclass_attr(self, class_name: str) -> None:
        """
        Add a metaclass attribute to a node.

        Does nothing if the attribute already exists.

        Args:
            class_name: The metadata class name.

        Raises:
            ValueError: The class_name was invalid.
        """
        if not VALID_CLASS_ATTR.match(class_name):
            raise ValueError("Invalid metaclass name: " + class_name)

        class_attr = METACLASS_ATTR_PREFIX + class_name

        try:
            self.mfn_node.attribute(class_attr)
        except RuntimeError:
            if self.undoable:
                name = get_unique_node_name(self.mfn_node)
                cmds.addAttr(name, longName=class_attr, attributeType="short")
            else:
                mfn_attr = api.MFnNumericAttribute()
                attr = mfn_attr.create(class_attr, class_attr, api.MFnNumericData.kShort)
                self.mfn_node.addAttribute(attr)

    def _remove_metaclass_attr(self, class_name: str) -> bool:
        """
        Remove a metaclass attribute from a node.

        Does nothing if the attribute does not exist.

        Args:
            class_name: The metadata class name.

        Returns:
            True if the attr was removed or didn't exist, False if it couldn't be removed.
        """
        class_plug = get_metaclass_plug(self.mfn_node, class_name)
        if not class_plug:
            return True

        if class_plug.isLocked():
            return False
        else:
            if self.undoable:
                plug_name = get_unique_plug_name(self.mfn_node, class_plug)
                cmds.deleteAttr(plug_name)
            else:
                self.mfn_node.removeAttribute(class_plug.attribute())
            return True
