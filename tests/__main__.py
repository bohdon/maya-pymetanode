import sys
import os
import unittest
import maya.standalone


def update_sys_paths():
    """
    Update `sys.path` to contain any missing script paths found in MAYA_SCRIPT_PATH.
    This must be performed after maya standalone is initialized
    """
    script_paths = os.environ["MAYA_SCRIPT_PATH"].split(":")
    for p in script_paths:
        if p not in sys.path:
            sys.path.append(p)


def run_tests():
    # lazy loading to wait for maya env to be initialized
    import test_core

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromModule(test_core))
    unittest.TextTestRunner(verbosity=2).run(suite)


def main():
    maya.standalone.initialize()
    update_sys_paths()
    # insert the package to test at beginning of sys path in
    # case its already installed in maya modules path
    module_scripts = os.path.join(sys.argv[1], "scripts")
    sys.path.insert(0, os.path.abspath(module_scripts))
    run_tests()


main()
