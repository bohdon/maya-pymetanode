
import unittest
import pymel.core as pm

import pymetanode as meta

class TestMetaData(unittest.TestCase):

    def setUp(self):
        self.node = pm.group(em=True)

    def tearDown(self):
        pm.delete(self.node)

    def test_setAndGetData(self):
        setData = ['myData', {'a':1, 'b':2}, ('x', 'y', 'z')]
        className = 'myMetaClass'
        meta.setMetaData(self.node, className, setData)
        self.assertEqual(meta.getMetaData(self.node, className), setData)

    def test_multiClassData(self):
        cls1 = 'myMetaClass1'
        cls2 = 'myMetaClass2'
        meta.setMetaData(self.node, cls1, None)
        meta.setMetaData(self.node, cls2, None)
        self.assertEqual(meta.getMetaData(self.node), {cls1: None, cls2: None})

    def test_removeData(self):
        meta.setMetaData(self.node, 'myMetaClass', None)
        self.assertTrue(meta.isMetaNode(self.node))
        result = meta.removeMetaData(self.node)
        self.assertTrue(result)
        self.assertFalse(meta.isMetaNode(self.node))

    def test_removeLockedData(self):
        meta.setMetaData(self.node, 'myMetaClass', 'myTestData')
        self.node.attr(meta.core.METADATA_ATTR).setLocked(True)
        result = meta.removeMetaData(self.node)
        self.assertFalse(result)
        data = meta.getMetaData(self.node)
        self.assertEqual(data, {'myMetaClass': 'myTestData'})

    def test_removeLockedClass(self):
        meta.setMetaData(self.node, 'myMetaClass', 'myTestData')
        self.node.attr(meta.core.METACLASS_ATTR_PREFIX + 'myMetaClass').setLocked(True)
        result = meta.removeMetaData(self.node)
        self.assertFalse(result)
        data = meta.getMetaData(self.node)
        self.assertEqual(data, {'myMetaClass': 'myTestData'})


class TestNodeFinding(unittest.TestCase):

    def setUp(self):
        self.nodeA = pm.group(em=True)
        meta.setMetaData(self.nodeA, 'ClassA', 'A')
        self.nodeB = pm.group(em=True)
        meta.setMetaData(self.nodeB, 'ClassB', 'B')
        meta.setMetaData(self.nodeB, 'ClassD', 'D')
        self.nodeC = pm.group(em=True)
        meta.setMetaData(self.nodeC, 'ClassC', 'C')
        meta.setMetaData(self.nodeC, 'ClassD', 'D')

    def tearDown(self):
        pm.delete([self.nodeA, self.nodeB, self.nodeC])

    def test_findAll(self):
        nodes = meta.findMetaNodes()
        self.assertTrue(self.nodeA in nodes)
        self.assertTrue(self.nodeB in nodes)
        self.assertTrue(self.nodeC in nodes)

    def test_findClassA(self):
        nodes = meta.findMetaNodes('ClassA')
        self.assertTrue(self.nodeA in nodes)
        self.assertTrue(self.nodeB not in nodes)
        self.assertTrue(self.nodeC not in nodes)

    def test_findClassD(self):
        nodes = meta.findMetaNodes('ClassD')
        self.assertTrue(self.nodeA not in nodes)
        self.assertTrue(self.nodeB in nodes)
        self.assertTrue(self.nodeC in nodes)


