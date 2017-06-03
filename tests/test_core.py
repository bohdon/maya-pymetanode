
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

