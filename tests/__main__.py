
import sys
import os
import unittest
import maya.standalone

def updateSysPaths():
    """
    Update sys.path to contain any missing script paths
    found in MAYA_SCRIPT_PATH. This must be performed
    after maya standalone is initialized
    """
    scriptPaths = os.environ['MAYA_SCRIPT_PATH'].split(':')
    for p in scriptPaths:
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
    updateSysPaths()
    run_tests()


main()