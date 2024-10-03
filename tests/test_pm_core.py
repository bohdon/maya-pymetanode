import unittest

import pymel.core as pm

import pymetanode as meta


class TestMetaData(unittest.TestCase):
    def setUp(self):
        self.node = pm.group(empty=True)

    def tearDown(self):
        pm.delete(self.node)

    def test_set_and_get_data(self):
        pm.namespace(add="test_ns")
        node_a = pm.group(name="node_a", empty=True)
        node_b = pm.group(name="test_ns:node_b", empty=True)

        set_data = [
            "myData",
            {"a": 1, "b": 2},
            ("x", "y", "z"),
            [node_a, node_b],
        ]
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
        self.node_a = pm.group(empty=True)
        meta.set_metadata(self.node_a, "ClassA", "A")
        self.node_b = pm.group(empty=True)
        meta.set_metadata(self.node_b, "ClassB", "B")
        meta.set_metadata(self.node_b, "ClassD", "D")
        self.node_c = pm.group(empty=True)
        meta.set_metadata(self.node_c, "ClassC", "C")
        meta.set_metadata(self.node_c, "ClassD", "D")

    def tearDown(self):
        pm.delete([self.node_a, self.node_b, self.node_c])

    def test_find_all(self):
        nodes = meta.find_meta_nodes()
        self.assertTrue(self.node_a in nodes)
        self.assertTrue(self.node_b in nodes)
        self.assertTrue(self.node_c in nodes)

    def test_find_class_a(self):
        nodes = meta.find_meta_nodes("ClassA")
        self.assertTrue(self.node_a in nodes)
        self.assertTrue(self.node_b not in nodes)
        self.assertTrue(self.node_c not in nodes)

    def test_find_class_d(self):
        nodes = meta.find_meta_nodes("ClassD")
        self.assertTrue(self.node_a not in nodes)
        self.assertTrue(self.node_b in nodes)
        self.assertTrue(self.node_c in nodes)
