

import pymel.core as pm
import maya.OpenMaya as api


__all__ = [
    'getMetaData',
    'getMObject',
    'getUUID',
    'hasAttr',
    'hasAttrFast',
    'removeMetaData',
    'setMetaData',
]

META_ATTR = 'pyMetaData'


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
    sel.add(nodeName)
    node = api.MObject()
    sel.getDependNode(0, node)
    return node


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



def setMetaData(node, data):
    """
    Set the meta data for the given node

    Args:
        node: A PyMel node or string node name
        data: A python object to serialize and store as meta data
    """
    mobject = getMObject(node)
    mfnnode = api.MFnDependencyNode(mobject)
    try:
        plug = mfnnode.findPlug(META_ATTR)
    except:
        mfnattr = api.MFnTypedAttribute()
        attr = mfnattr.create(META_ATTR, META_ATTR, api.MFnData.kString)
        mfnnode.addAttribute(attr)
        plug = mfnnode.findPlug(META_ATTR)
    plug.setString(str(data))


def getMetaData(node):
    """
    Return all meta data on the given node

    Args:
        node: A PyMel node or string node name

    Returns:
        A python object representing the last stored meta data
    """
    mobject = getMObject(node)
    try:
        plug = api.MFnDependencyNode(mobject).findPlug(META_ATTR)
    except RuntimeError:
        return
    else:
        return plug.asString()


def removeMetaData(node):
    """
    Remove all meta data from the given node

    Args:
        node: A PyMel node or string node name

    Returns:
        True if meta data was removed
    """
    mobject = getMObject(node)
    mfnnode = api.MFnDependencyNode(mobject)
    try:
        plug = mfnnode.findPlug(META_ATTR)
    except RuntimeError:
        pass
    else:
        if not plug.isLocked():
            mfnnode.removeAttribute(plug.attribute())
            return True
    return False



