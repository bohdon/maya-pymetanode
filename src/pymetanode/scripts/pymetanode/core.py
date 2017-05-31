

import pymel.core as pm
import maya.OpenMaya as api


__all__ = [
    'addMetaClass',
    'getAllMetaNodes',
    'getMetaClasses',
    'getMetaData',
    'getMObject',
    'getMPlugs',
    'getUUID',
    'hasAttr',
    'hasAttrFast',
    'isMetaNode',
    'removeMetaClass',
    'removeMetaData',
    'setMetaData',
]


METACLASS_ATTR_PREFIX = 'pyMetaClass_'
METADATA_ATTR = 'pyMetaData'


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
        plug = mfnnode.findPlug(METADATA_ATTR)
    except:
        mfnattr = api.MFnTypedAttribute()
        attr = mfnattr.create(METADATA_ATTR, METADATA_ATTR, api.MFnData.kString)
        mfnnode.addAttribute(attr)
        plug = mfnnode.findPlug(METADATA_ATTR)
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
        plug = api.MFnDependencyNode(mobject).findPlug(METADATA_ATTR)
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
    result = False
    # remove meta data
    mobject = getMObject(node)
    mfnnode = api.MFnDependencyNode(mobject)
    try:
        plug = mfnnode.findPlug(METADATA_ATTR)
    except RuntimeError:
        pass
    else:
        if not plug.isLocked():
            mfnnode.removeAttribute(plug.attribute())
            result = True
    # remove all meta classes
    classes = getMetaClasses(node)
    for c in classes:
        if removeMetaClass(node, c):
            result = True
    return result



def addMetaClass(node, className):
    """
    Add the given meta class type to the given node.

    Args:
        node: A PyMel node or string node name
        className: A string representing the meta class type.
    """
    attrName = METACLASS_ATTR_PREFIX + className
    mobject = getMObject(node)
    mfnnode = api.MFnDependencyNode(mobject)
    try:
        mfnnode.attribute(attrName)
    except RuntimeError:
        mfnattr = api.MFnNumericAttribute()
        attr = mfnattr.create(attrName, attrName, api.MFnNumericData.kInt)
        mfnnode.addAttribute(attr)


def getMetaClasses(node):
    """
    Return the name of the meta class types that the given
    node has meta data for.

    Args:
        node: A PyMel node or string node name
    """
    # TODO: implement with api
    attrs = pm.PyNode(node).listAttr()
    metaClassAttrs = [a for a in attrs if a.longName().startswith(METACLASS_ATTR_PREFIX)]
    classes = [a.longName()[len(METACLASS_ATTR_PREFIX):] for a in metaClassAttrs]
    return classes


def removeMetaClass(node, className):
    """
    Remove the given class type from the given node.

    Args:
        node: A PyMel node or string node name
        className: A string representing the meta class type.

    Returns:
        True if the class type was removed
    """
    attrName = METACLASS_ATTR_PREFIX + className
    mobject = getMObject(node)
    mfnnode = api.MFnDependencyNode(mobject)
    try:
        plug = mfnnode.findPlug(attrName)
    except RuntimeError:
        pass
    else:
        if not plug.isLocked():
            mfnnode.removeAttribute(plug.attribute())
            return True
    return False


def isMetaNode(node, className=None):
    """
    Return True if the given node has meta data, and optionally
    matches the given class type

    Args:
        node: A PyMel node or string node name
        className: A string representing the meta class type.
            If given, the node must be of this class type.
    """
    if className is not None:
        return hasAttr(node, METACLASS_ATTR_PREFIX + className)
    else:
        return hasAttr(node, METADATA_ATTR)


def getAllMetaNodes(className=None):
    """
    Return a list of all meta nodes of the given class type

    Args:
        className: A string representing the meta class type.
            If no class name is given, any node with meta data
            is returned.
    """
    if className is not None:
        searchStr = '*.' + METACLASS_ATTR_PREFIX + className
    else:
        searchStr = '*.' + METADATA_ATTR
    plugs = getMPlugs([searchStr])
    return [pm.PyNode(p.node()) for p in plugs]

