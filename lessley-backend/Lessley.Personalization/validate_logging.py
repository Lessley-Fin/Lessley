#!/usr/bin/env python3
"""
Validation script to verify structured logging implementation.
Run this to ensure all imports and syntax are correct.
"""

import sys
import os

# Add the parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Test that all modules can be imported without errors."""
    print("Testing imports...")

    try:
        from config.structured_logging import (
            StructuredFormatter,
            StructuredLogger,
            ContextInjectingFilter,
        )

        print("✓ config.structured_logging imported successfully")
    except Exception as e:
        print(f"✗ Failed to import config.structured_logging: {e}")
        return False

    try:
        from config.logging import root_logger

        print("✓ config.logging imported successfully")
    except Exception as e:
        print(f"✗ Failed to import config.logging: {e}")
        return False

    try:
        from middleware.request_id import RequestIDMiddleware

        print("✓ middleware.request_id imported successfully")
    except Exception as e:
        print(f"✗ Failed to import middleware.request_id: {e}")
        return False

    return True


def test_logging():
    """Test basic logging functionality."""
    print("\nTesting logging functionality...")

    try:
        from config.structured_logging import StructuredLogger
        import logging

        logger = logging.getLogger("test_module")

        # Set test context
        StructuredLogger.set_request_context("test-request-id", "test-user")

        # Test basic log
        logger.info("Test log message")

        # Test with context using standard logging
        logger.info(
            "Test with context",
            extra={"reason": "Testing logging system", "extra_data": {"test": True}},
        )

        print("✓ Logging functionality works correctly")
        return True
    except Exception as e:
        print(f"✗ Logging functionality test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Structured Logging Implementation Validation")
    print("=" * 60)

    imports_ok = test_imports()
    logging_ok = test_logging()

    print("\n" + "=" * 60)
    if imports_ok and logging_ok:
        print("✓ All validation tests passed!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("✗ Some validation tests failed")
        print("=" * 60)
        sys.exit(1)
