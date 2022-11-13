import unittest
import pymel.core as pm

import pymetanode as meta


class TestMetaData(unittest.TestCase):
    def setUp(self):
        self.node = pm.group(empty=True)

    def tearDown(self):
        pm.delete(self.node)

    def test_set_and_get_data(self):
        set_data = ["myData", {"a": 1, "b": 2}, ("x", "y", "z")]
        class_name = "myMetaClass"
        meta.set_metadata(self.node, class_name, set_data)
        self.assertEqual(meta.get_metadata(self.node, class_name), set_data)

    def test_multi_class_data(self):
        cls1 = "myMetaClass1"
        cls2 = "myMetaClass2"
        meta.set_metadata(self.node, cls1, None)
        meta.set_metadata(self.node, cls2, None)
        self.assertEqual(meta.get_metadata(self.node), {cls1: None, cls2: None})

    def test_remove_data(self):
        meta.set_metadata(self.node, "myMetaClass", None)
        self.assertTrue(meta.is_meta_node(self.node))
        result = meta.remove_metadata(self.node)
        self.assertTrue(result)
        self.assertFalse(meta.is_meta_node(self.node))

    def test_remove_locked_data(self):
        meta.set_metadata(self.node, "myMetaClass", "myTestData")
        self.node.attr(meta.core.METADATA_ATTR).setLocked(True)
        result = meta.remove_metadata(self.node)
        self.assertFalse(result)
        data = meta.get_metadata(self.node)
        self.assertEqual(data, {"myMetaClass": "myTestData"})

    def test_remove_class_data(self):
        meta.set_metadata(self.node, "myMetaClass", None)
        meta.set_metadata(self.node, "mySecondMetaClass", None)
        result = meta.remove_metadata(self.node, "myMetaClass")
        self.assertTrue(result)
        self.assertTrue(meta.is_meta_node(self.node))
        self.assertFalse(meta.has_metaclass(self.node, "myMetaClass"))
        self.assertTrue(meta.has_metaclass(self.node, "mySecondMetaClass"))

    def test_remove_locked_class(self):
        meta.set_metadata(self.node, "myMetaClass", "myTestData")
        self.node.attr(meta.core.METACLASS_ATTR_PREFIX + "myMetaClass").setLocked(True)
        result = meta.remove_metadata(self.node)
        self.assertFalse(result)
        data = meta.get_metadata(self.node)
        self.assertEqual(data, {"myMetaClass": "myTestData"})


class TestNodeFinding(unittest.TestCase):
    def setUp(self):
        self.nodeA = pm.group(empty=True)
        meta.set_metadata(self.nodeA, "ClassA", "A")
        self.nodeB = pm.group(empty=True)
        meta.set_metadata(self.nodeB, "ClassB", "B")
        meta.set_metadata(self.nodeB, "ClassD", "D")
        self.nodeC = pm.group(empty=True)
        meta.set_metadata(self.nodeC, "ClassC", "C")
        meta.set_metadata(self.nodeC, "ClassD", "D")

    def tearDown(self):
        pm.delete([self.nodeA, self.nodeB, self.nodeC])

    def test_find_all(self):
        nodes = meta.find_meta_nodes()
        self.assertTrue(self.nodeA in nodes)
        self.assertTrue(self.nodeB in nodes)
        self.assertTrue(self.nodeC in nodes)

    def test_find_class_a(self):
        nodes = meta.find_meta_nodes("ClassA")
        self.assertTrue(self.nodeA in nodes)
        self.assertTrue(self.nodeB not in nodes)
        self.assertTrue(self.nodeC not in nodes)

    def test_find_class_d(self):
        nodes = meta.find_meta_nodes("ClassD")
        self.assertTrue(self.nodeA not in nodes)
        self.assertTrue(self.nodeB in nodes)
        self.assertTrue(self.nodeC in nodes)
