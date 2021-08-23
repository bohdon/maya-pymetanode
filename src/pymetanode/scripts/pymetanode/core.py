
import ast
import re

import pymel.core as pm
import maya.cmds as cmds
import maya.OpenMaya as api

from . import utils


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
    'setAllMetaData',
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


def _getUniqueNodeName(mfnnode):
    """
    Return the unique name of a Dependency node.
    If the node is already unique, simply returns its
    name, otherwise returns the unique path to the node.

    Args:
        mfnnode (MFnDependencyNode): A MFnDependencyNode with a node object

    Returns:
        The unique name or path (str) of the node.
        E.g. 'node' or 'my|node'
    """
    if not mfnnode.hasUniqueName():
        node = mfnnode.object()
        if node.hasFn(api.MFn.kDagNode):
            mfndag = api.MFnDagNode(mfnnode.object())
            dagPath = api.MDagPath()
            mfndag.getPath(dagPath)
            return dagPath.partialPathName()
    return mfnnode.name()


def _getUniquePlugName(mfnnode, mplug):
    """
    Return the unique name of a MPlug, including its nodes name.

    Args:
        mfnnode (MFnDependencyNode): A MFnDependencyNode with the node.
            Provided for performance reasons, since it is common to have
            both this and the MPlug when needing the plug name in this package.
        mplug (MPlug): A MPlug of a node

    Returns:
        The unique name or path including attribute (str) of the plug.
        E.g. 'my|node.myPlug'
    """
    return _getUniqueNodeName(mfnnode) + '.' + mplug.partialName()


def _getOrCreateMetaDataPlug(mfnnode, undoable=True):
    """
    Return the MPlug for the meta data attribute on a node,
    adding the attribute if it does not already exist.

    Args:
        mfnnode (MFnDependencyNode): The MFnDependencyNode of a node
        undoable (bool): When True, the operation will be undoable

    Returns:
        The plug (MPlug) for the meta data attribute.
    """
    try:
        plug = mfnnode.findPlug(METADATA_ATTR)
    except:
        if undoable:
            name = _getUniqueNodeName(mfnnode)
            cmds.addAttr(name, ln=METADATA_ATTR, dt='string')
        else:
            mfnattr = api.MFnTypedAttribute()
            attr = mfnattr.create(
                METADATA_ATTR, METADATA_ATTR, api.MFnData.kString)
            mfnnode.addAttribute(attr)
        plug = mfnnode.findPlug(METADATA_ATTR)

    return plug


def _addMetaClassAttr(mfnnode, className, undoable=True):
    """
    Add a meta class attribute to a node.
    Does nothing if the attribute already exists.

    Args:
        mfnnode (MFnDependencyNode): The MFnDependencyNode of a node
        className (str): The meta data class name
        undoable (bool): When True, the operation will be undoable
    """
    if not VALID_CLASSATTR.match(className):
        raise ValueError('Invalid meta class name: ' + className)
    classAttr = METACLASS_ATTR_PREFIX + className
    try:
        mfnnode.attribute(classAttr)
    except RuntimeError:
        if undoable:
            name = _getUniqueNodeName(mfnnode)
            cmds.addAttr(name, ln=classAttr, at='short')
        else:
            mfnattr = api.MFnNumericAttribute()
            attr = mfnattr.create(
                classAttr, classAttr, api.MFnNumericData.kShort)
            mfnnode.addAttribute(attr)


def _removeMetaClassAttr(mfnnode, className, undoable=True):
    """
    Remove a meta class attribute from a node.
    Does nothing if the attribute does not exist.

    Args:
        mfnnode (MFnDependencyNode): The api MFnDependencyNode of a node
        undoable (bool): When True, the operation will be undoable

    Returns:
        True if the attr was removed or didn't exist,
        False if it couldn't be removed.
    """
    classPlug = _getMetaClassPlug(mfnnode, className)
    if not classPlug:
        return True

    if classPlug.isLocked():
        return False
    else:
        if undoable:
            plugName = _getUniquePlugName(mfnnode, classPlug)
            cmds.deleteAttr(plugName)
        else:
            mfnnode.removeAttribute(classPlug.attribute())
        return True


def encodeMetaData(data):
    """
    Return the given meta data encoded into a string

    Args:
        data: A python dictionary-like object representing
            the data to serialize.
    """
    return repr(encodeMetaDataValue(data))


def encodeMetaDataValue(value):
    """
    Encode and return a meta data value. Handles special
    data types like Maya nodes.

    Args:
        value: Any python value to be encoded
    """
    if isinstance(value, dict):
        result = {}
        for k, v in value.items():
            result[k] = encodeMetaDataValue(v)
        return result
    elif isinstance(value, (list, tuple)):
        return value.__class__([encodeMetaDataValue(v) for v in value])
    elif isinstance(value, pm.nt.DependNode):
        return utils.getUUID(value)
    else:
        return value


def decodeMetaData(data, refNode=None):
    """
    Parse the given meta data and return it as a valid
    python object.

    Args:
        data: A string representing encoded meta data.
    """
    if not data:
        return {}
    # convert from string to python object
    try:
        data = ast.literal_eval(data.replace('\r', ''))
    except Exception as e:
        raise ValueError("Failed to decode meta data: {0}".format(e))
    return decodeMetaDataValue(data, refNode)


def decodeMetaDataValue(value, refNode):
    """
    Parse string formatted meta data and return the
    resulting python object.

    Args:
        data: A str representing encoded meta data
    """
    if isinstance(value, dict):
        result = {}
        for k, v in value.items():
            result[k] = decodeMetaDataValue(v, refNode)
        return result
    elif isinstance(value, (list, tuple)):
        return value.__class__([decodeMetaDataValue(v, refNode) for v in value])
    elif utils.isUUID(value):
        return utils.findNodeByUUID(value, refNode)
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


def findMetaNodes(className=None, asPyNodes=True):
    """
    Return a list of all meta nodes of the given class type.
    If no class is given, all nodes with meta data are returned.

    Args:
        className: A string name of the meta class type.
        asPyNodes: A bool, when True, returns a list of PyNodes,
            otherwise returns a list of MObjects
    """
    if className is not None:
        plugName = METACLASS_ATTR_PREFIX + className
    else:
        plugName = METADATA_ATTR
    objs = utils.getMObjectsByPlug(plugName)
    if asPyNodes:
        return [pm.PyNode(o) for o in objs]
    else:
        return objs


def setMetaData(node, className, data, undoable=True, replace=False):
    """
    Set the meta data for the a meta class type on a node.

    The className must be a valid attribute name.

    Args:
        node (PyNode or str): The node on which to set data
        className (str): The data's meta class type name
        data (dict): The data to serialize and store on the node
        undoable (bool): When True, the operation will be undoable
        replace (bool): When True, will replace all data on the node
            with the new meta data. This uses setAllMetaData and can
            be much faster with large data sets.
    """
    if replace:
        setAllMetaData(node, {className: data}, undoable)
        return

    mfnnode = utils.getMFnDependencyNode(node)
    plug = _getOrCreateMetaDataPlug(mfnnode, undoable)
    _addMetaClassAttr(mfnnode, className, undoable)

    # update meta data
    refNode = None
    if cmds.referenceQuery(str(node), isNodeReferenced=True):
        refNode = cmds.referenceQuery(str(node), rfn=True)
    fullData = decodeMetaData(plug.asString(), refNode)
    fullData[className] = data
    newValue = encodeMetaData(fullData)

    if undoable:
        plugName = _getUniquePlugName(mfnnode, plug)
        cmds.setAttr(plugName, newValue, type='string')
    else:
        plug.setString(newValue)


def setAllMetaData(node, data, undoable=True):
    """
    Set all meta data on a node. This is faster because the
    existing data on the node is not retrieved first and then
    modified. The data must be first indexed by strings that
    are valid meta class names, otherwise errors may occur
    when retrieving it later.

    New meta class attributes will be added automatically,
    but existing meta class attributes will not be removed.
    If old meta class attributes on this node will no longer
    be applicable, they should be removed with removeAllData
    first.

    Args:
        node (PyNode or str): The node on which to set data
        data (dict): The data to serialize and store on the node
        undoable (bool): When True, the operation will be undoable
    """
    mfnnode = utils.getMFnDependencyNode(node)
    plug = _getOrCreateMetaDataPlug(mfnnode, undoable)

    # add class attributes
    if data:
        for className in data.keys():
            _addMetaClassAttr(mfnnode, className, undoable)

    # set meta data
    newValue = encodeMetaData(data)

    if undoable:
        plugName = _getUniquePlugName(mfnnode, plug)
        cmds.setAttr(plugName, newValue, type='string')
    else:
        plug.setString(newValue)


def getMetaData(node, className=None):
    """
    Return meta data from a node. If `className` is given,
    return only meta data for that meta class type.

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
        return {}
    else:
        refNode = None
        if cmds.referenceQuery(str(node), isNodeReferenced=True):
            refNode = cmds.referenceQuery(str(node), rfn=True)
        data = decodeMetaData(datastr, refNode)

        if className is not None:
            return data.get(className, {})

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
        raise ValueError(
            "meta data for node '{0}' is not "
            "a dict and cannot be updated".format(node))
    fullData.update(data)
    setMetaData(node, className, fullData)


def removeMetaData(node, className=None, undoable=True):
    """
    Remove meta data from a node. If no `className` is given
    then all meta data is removed.

    Args:
        node: A PyMel node or string node name
        className: A string name of the meta class type.
        undoable: A bool, when True the change will be undoable

    Returns:
        True if node is fully clean of relevant meta data.
    """
    if not isMetaNode(node):
        return True

    mfnnode = utils.getMFnDependencyNode(node)

    # this may become true if we find there are no
    # classes left after removing one
    removeAllData = False

    if className is not None:
        # remove meta data for the given class only

        # make sure data attribute is unlocked
        dataPlug = _getMetaDataPlug(mfnnode)
        if dataPlug and dataPlug.isLocked():
            return False

        # attempt to remove class attribute
        if not _removeMetaClassAttr(mfnnode, className, undoable):
            return False

        # remove class-specific data from all meta data
        # TODO(bsayre): add a partialDecodeMetaData for uses like this
        #   since we will only be modifying the core dict object and not
        #   using any meta data values (like nodes)
        data = decodeMetaData(dataPlug.asString())
        if className in data:
            del data[className]
            newValue = encodeMetaData(data)

            if undoable:
                plugName = _getUniquePlugName(mfnnode, dataPlug)
                cmds.setAttr(plugName, newValue, type='string')
            else:
                dataPlug.setString(newValue)

        # check if any classes left
        if len(data) == 0:
            removeAllData = True

    else:
        # no className was given
        removeAllData = True

    if removeAllData:
        # remove all meta data from the node

        # make sure data attribute is unlocked
        dataPlug = _getMetaDataPlug(mfnnode)
        if dataPlug and dataPlug.isLocked():
            return False

        # make sure all class attributes are unlocked
        classPlugs = [_getMetaClassPlug(mfnnode, c)
                      for c in getMetaClasses(node)]
        for cp in classPlugs:
            if cp and cp.isLocked():
                return False

        # remove class attributes
        for classPlug in classPlugs:
            if classPlug:
                if undoable:
                    plugName = _getUniquePlugName(mfnnode, classPlug)
                    cmds.deleteAttr(plugName)
                else:
                    mfnnode.removeAttribute(classPlug.attribute())

        # remove data attribute
        if dataPlug:
            if undoable:
                plugName = _getUniquePlugName(mfnnode, dataPlug)
                cmds.deleteAttr(plugName)
            else:
                mfnnode.removeAttribute(dataPlug.attribute())

    return True


def getMetaClasses(node):
    """
    Return the name of the meta class types that the given
    node has meta data for.

    Args:
        node: A PyMel node or string node name
    """
    attrs = cmds.listAttr(str(node))
    metaClassAttrs = [a for a in attrs if a.startswith(METACLASS_ATTR_PREFIX)]
    classes = [a[len(METACLASS_ATTR_PREFIX):] for a in metaClassAttrs]
    return classes
