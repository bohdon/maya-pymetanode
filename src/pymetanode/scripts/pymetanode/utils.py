
import pymel.core as pm
import maya.OpenMaya as api


__all__ = [
    'getMObject',
    'getMPlugs',
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


def getMObject(nodeName):
    """
    Return the MObject from the scene for the given node name

    Args:
        nodeName: A string node name
    """
    sel = api.MSelectionList()
    sel.add(str(nodeName))
    node = api.MObject()
    sel.getDependNode(0, node)
    return node


def getMPlugs(matchStrings):
    """
    Return all MPlugs in the scene that match the given match strings.

    Args:
        matchStrings: A list of `ls` command style strings that must
            include an attribute, e.g. `*.pyMetaData`
    """
    sel = api.MSelectionList()
    for s in matchStrings:
        try:
            sel.add(s)
        except:
            pass
    count = sel.length()
    result = [api.MPlug() for i in range(count)]
    [sel.getPlug(i, result[i]) for i in range(count)]
    return result


def getUUID(nodeName):
    """
    Return the UUID of the given node

    Args:
        nodeName: A string node name
    """
    sel = api.MSelectionList()
    sel.add(nodeName)
    node = api.MObject()
    sel.getDependNode(0, node)
    val = api.MFnDependencyNode(node)
    return val.uuid().asString()

