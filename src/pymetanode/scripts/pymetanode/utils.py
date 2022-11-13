import re
import pymel.core as pm
import maya.OpenMaya as api

__all__ = [
    "find_node_by_uuid",
    "get_mfn_dependency_node",
    "get_m_object",
    "get_m_objects_by_plug",
    "get_uuid",
    "has_attr",
    "has_attr_fast",
    "is_node",
    "is_uuid",
]

VALID_UUID = re.compile("^[A-F0-9]{8}-([A-F0-9]{4}-){3}[A-F0-9]{12}$")


def has_attr(node, attr_name):
    """
    Return True if the given node has the given attribute.

    Runs a fast version of has_attr if the node is an MObject, otherwise falls back to using `cmds.objExists`.

    Args:
        node: A MObject, PyMel node, or string representing a node
        attr_name: A string name of an attribute to test
    """
    if isinstance(node, api.MObject):
        return has_attr_fast(node, attr_name)
    elif isinstance(node, pm.nt.DependNode):
        return has_attr_fast(node.__apimobject__(), attr_name)
    else:
        return pm.cmds.objExists(node + "." + attr_name)


def has_attr_fast(mobject, attr_name):
    """
    Return True if the given node has the given attribute.

    Uses the api for performance, and performs no validation or type-checking.

    Args:
        mobject: A MObject node
    """
    try:
        api.MFnDependencyNode(mobject).attribute(attr_name)
        return True
    except RuntimeError:
        return False


def get_m_object(node):
    """
    Return the MObject for a node

    Args:
        node: A PyNode or node name
    """
    if isinstance(node, pm.nt.DependNode):
        return node.__apimobject__()
    else:
        sel = api.MSelectionList()
        try:
            sel.add(node)
        except:
            # node does not exist or invalid arg
            return
        mobj = api.MObject()
        sel.getDependNode(0, mobj)
        return mobj


def get_m_objects_by_plug(plug_name):
    """
    Return all dependency nodes in the scene that have a specific plug.

    Args:
        plug_name: A string name of a maya plug to search for on nodes
    """
    sel = api.MSelectionList()
    try:
        sel.add("*." + plug_name, True)
    except:
        pass
    count = sel.length()
    result = [api.MObject() for i in range(count)]
    [sel.getDependNode(i, result[i]) for i in range(count)]
    return result


def get_mfn_dependency_node(node):
    """
    Return an MFnDependencyNode for a node

    Args:
        node: A PyNode or string node name
    """
    if isinstance(node, api.MObject):
        return api.MFnDependencyNode(node)
    elif isinstance(node, pm.nt.DependNode):
        if node.exists():
            return node.__apimfn__()
    else:
        mobj = get_m_object(node)
        if mobj:
            return api.MFnDependencyNode(mobj)


def is_node(obj):
    """
    Returns whether an object represents a Maya node
    """
    if isinstance(obj, api.MObject) or isinstance(obj, pm.PyNode):
        return True
    elif isinstance(obj, str):
        return is_uuid(obj) or pm.cmds.objExists(obj)


def is_uuid(obj):
    """
    Returns whether an object is a valid UUID
    """
    return isinstance(obj, str) and VALID_UUID.match(obj)


def get_uuid(node):
    """
    Return the UUID of the given node

    Args:
        node: A MObject, pymel node, or node name
    """
    mfn_node = get_mfn_dependency_node(node)
    if mfn_node:
        return mfn_node.uuid().asString()


def find_node_by_uuid(uuid, ref_node=None):
    """
    Args:
        uuid: A string UUID representing the node
        ref_node: A string name of the reference node
            that the node should be associated with
    """
    nodes = pm.ls(uuid)
    if ref_node:
        # filter result by nodes from the same reference file
        for n in nodes:
            if pm.cmds.referenceQuery(str(n), isNodeReferenced=True):
                if pm.cmds.referenceQuery(str(n), rfn=True) == ref_node:
                    return n
    elif nodes:
        # take the first result
        return nodes[0]
