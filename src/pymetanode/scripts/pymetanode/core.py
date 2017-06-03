
import ast

import pymel.core as pm
import maya.OpenMaya as api

import utils


__all__ = [
    'decodeMetaData',
    'encodeMetaData',
    'getAllMetaNodes',
    'getMetaClasses',
    'getMetaData',
    'hasMetaClass',
    'isMetaNode',
    'removeMetaData',
    'setMetaData',
]


METACLASS_ATTR_PREFIX = 'pyMetaClass_'
METADATA_ATTR = 'pyMetaData'


def _getMetaDataPlug(mfnnode):
    """
    Return the MPlug for the meta data attribute on a node

    Args:
        mfnnode: A MFnDependencyNode referencing the target node.
    """
    try:
        return mfnnode.findPlug(METADATA_ATTR)
    except RuntimeError:
        pass


def _getMetaClassPlug(mfnnode, className):
    """
    Return the MPlug for a meta class attribute on a node

    Args:
        mfnnode: A MFnDependencyNode referencing the target node.
        className: A string name of the meta class type.
    """
    attrName = METACLASS_ATTR_PREFIX + className
    try:
        return mfnnode.findPlug(attrName)
    except RuntimeError:
        pass


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
    if not data:
        return {}
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
    return utils.hasAttr(node, METADATA_ATTR)


def hasMetaClass(node, className):
    """
    Return True if the given node has data for the given meta class type

    Args:
        node: A PyMel node or string node name
        className: A string name of the meta class type.
            If given, the node must be of this class type.
    """
    return utils.hasAttr(node, METACLASS_ATTR_PREFIX + className)


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
    plugs = utils.getMPlugs([searchStr])
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
    mfnnode = api.MFnDependencyNode(utils.getMObject(node))
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
    mobject = utils.getMObject(node)
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

    mfnnode = api.MFnDependencyNode(utils.getMObject(node))

    if className is not None:
        # remove meta data for the given class only

        # make sure data attribute is unlocked
        dataPlug = _getMetaDataPlug(mfnnode)
        if dataPlug and dataPlug.isLocked():
            return False

        # make sure class attribute is unlocked
        classPlug = _getMetaClassPlug(mfnnode, className)
        if classPlug and classPlug.isLocked():
            return False

        data = decodeMetaData(plug.asString())
        if className in data:
            del data[className]
            plug.setString(encodeMetaData(data))

    else:
        # remove all meta data from the node

        # make sure data attribute is unlocked
        dataPlug = _getMetaDataPlug(mfnnode)
        if dataPlug and dataPlug.isLocked():
            return False

        # make sure all class attributes are unlocked
        classPlugs = [_getMetaClassPlug(mfnnode, c) for c in getMetaClasses(node)]
        for cp in classPlugs:
            if cp and cp.isLocked():
                return False

        # remove all attributes
        if dataPlug:
            mfnnode.removeAttribute(dataPlug.attribute())
        for cp in classPlugs:
            if cp:
                mfnnode.removeAttribute(cp.attribute())
    
    return True


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



