
import re
import pymel.core as pm
import maya.OpenMaya as api


__all__ = [
    'findNodeByUUID',
    'getMFnDependencyNode',
    'getMObject',
    'getMObjectsByPlug',
    'getUUID',
    'hasAttr',
    'hasAttrFast',
    'isNode',
    'isUUID',
]


VALID_UUID = re.compile('^[A-F0-9]{8}-([A-F0-9]{4}-){3}[A-F0-9]{12}$')


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
        try:
            sel.add(node)
        except:
            # node does not exist or invalid arg
            return
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
        sel.add('*.' + plugName, True)
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
        if node.exists():
            return node.__apimfn__()
    else:
        mobj = getMObject(node)
        if mobj:
            return api.MFnDependencyNode(mobj)

def isNode(obj):
    """
    Returns whether an object represents a Maya node
    """
    if isinstance(obj, api.MObject) or isinstance(obj, pm.PyNode):
        return True
    elif isinstance(obj, str):
        return isUUID(obj) or pm.cmds.objExists(obj)

def isUUID(obj):
    """
    Returns whether an object is a valid UUID
    """
    return isinstance(obj, str) and VALID_UUID.match(obj)

def getUUID(node):
    """
    Return the UUID of the given node

    Args:
        node: A MObject, pymel node, or node name
    """
    mfnnode = getMFnDependencyNode(node)
    if mfnnode:
        return mfnnode.uuid().asString()

def findNodeByUUID(uuid, refNode=None):
    """
    Args:
        uuid: A string UUID representing the node
        refNode: A string name of the reference node
            that the node should be associated with
    """
    nodes = pm.ls(uuid)
    if refNode:
        # filter result by nodes from the same reference file
        for n in nodes:
            if pm.cmds.referenceQuery(str(n), isNodeReferenced=True):
                if pm.cmds.referenceQuery(str(n), rfn=True) == refNode:
                    return n
    elif nodes:
        # take the first result
        return nodes[0]
