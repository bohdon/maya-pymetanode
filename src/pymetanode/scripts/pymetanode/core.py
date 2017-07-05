
import ast
import re

import pymel.core as pm
import maya.OpenMaya as api

import utils


__all__ = [
    'decodeMetaData',
    'decodeMetaDataValue',
    'encodeMetaData',
    'encodeMetaDataValue',
    'findMetaNodes',
    'getMetaClasses',
    'getMetaData',
    'hasMetaClass',
    'isMetaNode',
    'removeMetaData',
    'setMetaData',
    'updateMetaData',
]


METACLASS_ATTR_PREFIX = 'pyMetaClass_'
METADATA_ATTR = 'pyMetaData'

VALID_CLASSATTR = re.compile(r'^[_a-z0-9]*$', re.IGNORECASE)

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
    return str(encodeMetaDataValue(data))

def encodeMetaDataValue(value):
    """
    Encode and return a meta data value. Handles special
    data types like Maya nodes.

    Args:
        value: Any python value to be encoded
    """
    if isinstance(value, dict):
        result = {}
        for k, v in value.iteritems():
            result[k] = encodeMetaDataValue(v)
        return result
    elif isinstance(value, (list, tuple)):
        return value.__class__([encodeMetaDataValue(v) for v in value])
    elif isinstance(value, pm.nt.DependNode):
        return utils.getUUID(value)
    else:
        return value


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
        # convert from string to python object
        data = ast.literal_eval(data.replace('\r', ''))
    except SyntaxError as e:
        print("Failed to parse meta data, invalid syntax: {0}".format(e))
        return {}
    else:
        return decodeMetaDataValue(data)

def decodeMetaDataValue(value):
    """
    Parse string formatted meta data and return the
    resulting python object.

    Args:
        data: A str representing encoded meta data
    """
    if isinstance(value, dict):
        result = {}
        for k, v in value.iteritems():
            result[k] = decodeMetaDataValue(v)
        return result
    elif isinstance(value, (list, tuple)):
        return value.__class__([decodeMetaDataValue(v) for v in value])
    elif utils.isUUID(value):
        nodes = pm.ls(value)
        if nodes:
            return nodes[0]
    else:
        return value


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


def findMetaNodes(className=None):
    """
    Return a list of all meta nodes of the given class type.
    If no class is given, all nodes with meta data are returned.

    Args:
        className: A string name of the meta class type.
    """
    if className is not None:
        plugName = METACLASS_ATTR_PREFIX + className
    else:
        plugName = METADATA_ATTR
    objs = utils.getMObjectsByPlug(plugName)
    return [pm.PyNode(o) for o in objs]


def setMetaData(node, className, data):
    """
    Set the meta data for the a meta class type on a node.

    Args:
        node: A PyMel node or string node name
        className: A string name of the meta class type.
        data: A python object to serialize and store as meta data
    """
    # get meta data plug
    mfnnode = utils.getMFnDependencyNode(node)
    try:
        plug = mfnnode.findPlug(METADATA_ATTR)
    except:
        mfnattr = api.MFnTypedAttribute()
        attr = mfnattr.create(METADATA_ATTR, METADATA_ATTR, api.MFnData.kString)
        mfnnode.addAttribute(attr)
        plug = mfnnode.findPlug(METADATA_ATTR)
    # ensure node has meta class type attribute
    if not VALID_CLASSATTR.match(className):
        raise ValueError('Invalid meta class name: ' + className)
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
    mfnnode = utils.getMFnDependencyNode(node)
    try:
        plug = mfnnode.findPlug(METADATA_ATTR)
        datastr = plug.asString()
    except RuntimeError:
        return
    else:
        data = decodeMetaData(datastr)
        if className is not None:
            return data.get(className, None)
        else:
            return data


def updateMetaData(node, className, data):
    """
    Updates existing meta data on a node for a meta class type.
    Only supports dict-type meta data

    Args:
        node: A PyMel node or string node name
        className: A string name of the meta class type
        data: A dict object containing meta data to add to the node
    """
    fullData = getMetaData(node, className)
    if not isinstance(fullData, dict):
        raise ValueError("meta data for node '{0}' is not a dict and cannot be updated".format(node))
    fullData.update(data)
    setMetaData(node, className, fullData)


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

    mfnnode = utils.getMFnDependencyNode(node)

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
    attrs = pm.cmds.listAttr(str(node))
    metaClassAttrs = [a for a in attrs if a.startswith(METACLASS_ATTR_PREFIX)]
    classes = [a[len(METACLASS_ATTR_PREFIX):] for a in metaClassAttrs]
    return classes



