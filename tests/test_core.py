
import unittest
import pymel.core as pm

import pymetanode as meta

class TestMetaData(unittest.TestCase):

    def setUp(self):
        self.node = pm.group(em=True)

    def tearDown(self):
        pm.delete(self.node)

    def test_setAndGet(self):
        setData = ['myData', {'a':1, 'b':2}, ('x', 'y', 'z')]
        className = 'myMetaClass'
        meta.setMetaData(self.node, setData, className)
        self.assertEqual(meta.getMetaData(self.node, className), setData)

    def test_remove(self):
        meta.setMetaData(self.node, None, 'myMetaClass')
        self.assertTrue(meta.isMetaNode(self.node))
        result = meta.removeMetaData(self.node)
        self.assertTrue(result)
        self.assertFalse(meta.isMetaNode(self.node))

    def test_removeLockedData(self):
        meta.setMetaData(self.node, 'myTestData', 'myMetaClass')
        self.node.attr(meta.core.METADATA_ATTR).setLocked(True)
        result = meta.removeMetaData(self.node)
        self.assertFalse(result)
        data = meta.getMetaData(self.node)
        self.assertEqual(data, {'myMetaClass': 'myTestData'})

    def test_removeLockedClass(self):
        meta.setMetaData(self.node, 'myTestData', 'myMetaClass')
        self.node.attr(meta.core.METACLASS_ATTR_PREFIX + 'myMetaClass').setLocked(True)
        result = meta.removeMetaData(self.node)
        self.assertFalse(result)
        data = meta.getMetaData(self.node)
        self.assertEqual(data, {'myMetaClass': 'myTestData'})

    def test_multiClass(self):
        cls1 = 'myMetaClass1'
        cls2 = 'myMetaClass2'
        meta.setMetaData(self.node, None, cls1)
        meta.setMetaData(self.node, None, cls2)
        self.assertEqual(meta.getMetaData(self.node), {cls1: None, cls2: None})