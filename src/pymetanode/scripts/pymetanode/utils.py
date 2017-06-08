
import pymel.core as pm
import maya.OpenMaya as api


__all__ = [
    'getMObject',
    'getMObjectsByPlug',
    'getMFnDependencyNode',
    'getUUID',
    'hasAttr',
    'hasAttrFast',
]


def hasAttr(node, attrName):
    """
    Return True if the given node has the given attribute.
    
    Args:
        node: A MObject, PyMel node, or string representing a node
        attrName: A string name of an attribute to test
    """
    if isinstance(node, api.MObject):
        return hasAttrFast(node, attrName)
    elif isinstance(node, pm.nt.DependNode):
        return hasAttrFast(node.__apimobject__(), attrName)
    else:
        return pm.cmds.objExists(node + '.' + attrName)


def hasAttrFast(mobject, attrName):
    """
    Return True if the given node has the given attribute.
    Performs no validation or type-checking.

    Args:
        mobject: A MObject node
    """
    try:
        api.MFnDependencyNode(mobject).attribute(attrName)
        return True
    except RuntimeError:
        return False


def getMObject(node):
    """
    Return the MObject for a node

    Args:
        node: A PyNode or node name
    """
    if isinstance(node, pm.nt.DependNode):
        return node.__apimobject__()
    else:
        sel = api.MSelectionList()
        sel.add(node)
        mobj = api.MObject()
        sel.getDependNode(0, mobj)
        return mobj


def getMObjectsByPlug(plugName):
    """
    Return all dependency nodes in the scene that have a specific plug.

    Args:
        plugName: A string name of a maya plug to search for on nodes
    """
    sel = api.MSelectionList()
    try:
        sel.add('*.' + plugName)
    except:
        pass
    count = sel.length()
    result = [api.MObject() for i in range(count)]
    [sel.getDependNode(i, result[i]) for i in range(count)]
    return result


def getMFnDependencyNode(node):
    """
    Return an MFnDependencyNode for a node

    Args:
        node: A PyNode or string node name
    """
    if isinstance(node, api.MObject):
        return api.MFnDependencyNode(node)
    elif isinstance(node, pm.nt.DependNode):
        return node.__apimfn__()
    else:
        return api.MFnDependencyNode(getMObject(node))


def getUUID(node):
    """
    Return the UUID of the given node

    Args:
        node: A string node name
    """
    if isinstance(node, api.MObject):
        mfnnode = api.MFnDependencyNode(node)
    elif isinstance(node, pm.nt.DependNode):
        mfnnode = node.__apimfn__()
    else:
        sel = api.MSelectionList()
        sel.add(node)
        mobj = api.MObject()
        sel.getDependNode(0, mobj)
        mfnnode = api.MFnDependencyNode(mobj)
    return mfnnode.uuid().asString()

