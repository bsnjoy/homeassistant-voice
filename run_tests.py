#!/usr/bin/env python3
import unittest
import sys

if __name__ == '__main__':
    # Load the integration test module
    test_suite = unittest.defaultTestLoader.loadTestsFromName('tests.test_ai_integration')
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Exit with non-zero code if tests failed
    sys.exit(not result.wasSuccessful())
