
import ast

import pymel.core as pm
import maya.OpenMaya as api


__all__ = [
    'decodeMetaData',
    'encodeMetaData',
    'getAllMetaNodes',
    'getMetaClasses',
    'getMetaData',
    'getMObject',
    'getMPlugs',
    'getUUID',
    'hasAttr',
    'hasAttrFast',
    'hasMetaClass',
    'isMetaNode',
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



def encodeMetaData(data):
    """
    Return the given meta data encoded into a string

    Args:
        data: A python dictionary-like object representing
            the data to serialize.
    """
    return str(data)


def decodeMetaData(data):
    """
    Parse the given meta data and return it as a valid
    python object.

    Args:
        data: A string representing encoded meta data.
    """
    try:
        return ast.literal_eval(data.replace('\r', ''))
    except SyntaxError as e:
        print("Failed to parse meta data, invalid syntax: {0}".format(e))
        return {}



def isMetaNode(node):
    """
    Return True if the given node has any meta data

    Args:
        node: A PyMel node or string node name
    """
    return hasAttr(node, METADATA_ATTR)


def hasMetaClass(node, className):
    """
    Return True if the given node has data for the given meta class type

    Args:
        node: A PyMel node or string node name
        className: A string name of the meta class type.
            If given, the node must be of this class type.
    """
    return hasAttr(node, METACLASS_ATTR_PREFIX + className)


def getAllMetaNodes(className=None):
    """
    Return a list of all meta nodes of the given class type

    Args:
        className: A string name of the meta class type.
            If no class name is given, any node with meta data
            is returned.
    """
    if className is not None:
        searchStr = '*.' + METACLASS_ATTR_PREFIX + className
    else:
        searchStr = '*.' + METADATA_ATTR
    plugs = getMPlugs([searchStr])
    return [pm.PyNode(p.node()) for p in plugs]


def setMetaData(node, data, className):
    """
    Set the meta data for the a meta class type on a node.

    Args:
        node: A PyMel node or string node name
        data: A python object to serialize and store as meta data
        className: A string name of the meta class type.
    """
    # get meta data plug
    mfnnode = api.MFnDependencyNode(getMObject(node))
    try:
        plug = mfnnode.findPlug(METADATA_ATTR)
    except:
        mfnattr = api.MFnTypedAttribute()
        attr = mfnattr.create(METADATA_ATTR, METADATA_ATTR, api.MFnData.kString)
        mfnnode.addAttribute(attr)
        plug = mfnnode.findPlug(METADATA_ATTR)
    # ensure node has meta class type attribute
    classAttr = METACLASS_ATTR_PREFIX + className
    try:
        mfnnode.attribute(classAttr)
    except RuntimeError:
        mfnattr = api.MFnNumericAttribute()
        attr = mfnattr.create(classAttr, classAttr, api.MFnNumericData.kInt)
        mfnnode.addAttribute(attr)
    # update meta data
    fullData = decodeMetaData(plug.asString())
    fullData[className] = data
    plug.setString(encodeMetaData(fullData))


def getMetaData(node, className=None):
    """
    Return meta data from a node. If `className` is given
    returns only meta data for that meta class type.

    Args:
        node: A PyMel node or string node name
        className: A string name of the meta class type.

    Returns:
        A dict or python object representing the stored meta data
    """
    mobject = getMObject(node)
    try:
        plug = api.MFnDependencyNode(mobject).findPlug(METADATA_ATTR)
        datastr = plug.asString()
    except RuntimeError:
        return
    else:
        data = decodeMetaData(datastr)
        if className is not None:
            return data.get(className, None)
        else:
            return data


def removeMetaData(node, className=None):
    """
    Remove meta data from a node. If no `className` is given
    then all meta data is removed.

    Args:
        node: A PyMel node or string node name
        className: A string name of the meta class type.

    Returns:
        True if node is fully clean of relevant meta data.
    """
    if not isMetaNode(node):
        return True

    mfnnode = api.MFnDependencyNode(getMObject(node))
    dataRemaining = False

    if className is not None:
        classAttr = METACLASS_ATTR_PREFIX + className
        # remove meta class attr
        if not _removeMetaClass(node, className):
            dataRemaining = True
        # remove meta data for the given class only
        data = decodeMetaData(plug.asString())
        if className in data:
            del data[className]
            plug.setString(encodeMetaData(data))

    else:
        # remove all meta class attrs
        classes = getMetaClasses(node)
        for c in classes:
            if not _removeMetaClass(node, c):
                dataRemaining = True
        # remove meta data attribute
        try:
            plug = mfnnode.findPlug(METADATA_ATTR)
        except RuntimeError:
            pass
        else:
            if not plug.isLocked():
                mfnnode.removeAttribute(plug.attribute())
            else:
                dataRemaining = True
    
    return not dataRemaining


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


def _removeMetaClass(node, className):
    """
    Remove the a meta class type from a node.

    Args:
        node: A PyMel node or string node name
        className: A string name of the meta class type.

    Returns:
        True if node is fully clean of the meta class type.
    """
    attrName = METACLASS_ATTR_PREFIX + className
    mfnnode = api.MFnDependencyNode(getMObject(node))
    try:
        plug = mfnnode.findPlug(attrName)
    except RuntimeError:
        return True
    else:
        if not plug.isLocked():
            mfnnode.removeAttribute(plug.attribute())
        else:
            return False
    return True


