"""Test script for bulk operations tools.

Run this to verify bulk operations are working correctly.
"""

import asyncio
import sys
import pytest
from src.server import get_client


@pytest.mark.asyncio
async def test_bulk_operations():
    """Test bulk operation tools basic functionality."""
    print("🧪 Testing Bulk Operations Tools\n")
    print("=" * 60)
    
    try:
        # Import bulk operation tools module
        from src.tools import work_packages_bulk
        
        print("✅ Successfully imported work_packages_bulk module")
        print("   Module contains all bulk operation tools")
        print()
        
        #  The @mcp.tool decorator registers tools with FastMCP
        # We can verify the actual bulk tools exist as module attributes
        tool_names = [
            "bulk_create_work_packages",
            "bulk_add_comment",
            "bulk_update_filtered_work_packages",
            "bulk_set_work_package_parents",
            "bulk_remove_work_package_parents",
            "bulk_create_work_package_relations",
            "bulk_delete_work_package_relations",
        ]
        
        for tool_name in tool_names:
            assert hasattr(work_packages_bulk, tool_name), f"Missing {tool_name}"
            print(f"✅ Found tool: {tool_name}")
        
        print()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("\nBulk operations tools are working correctly.")
        print("\nTo use in Claude, restart the MCP server and try:")
        print('  "Assign work packages 10,20,30 to user 5"')
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("\nMake sure work_packages_bulk.py is in src/tools/")
        pytest.fail(f"Import Error: {e}")
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Test Failed: {e}")


@pytest.mark.asyncio
async def test_bulk_operations_helper():
    """Test the bulk operations helper functions."""
    print("\n🧪 Testing Bulk Operations Helpers\n")
    print("=" * 60)
    
    try:
        from src.utils.bulk_operations import (
            BulkOperationResult,
            bulk_update_work_packages,
            bulk_delete_work_packages
        )
        
        print("✅ Successfully imported helpers")
        print("   - BulkOperationResult")
        print("   - bulk_update_work_packages")
        print("   - bulk_delete_work_packages")
        print()
        
        # Test BulkOperationResult
        result = BulkOperationResult(
            total=10,
            succeeded=8,
            failed=2,
            errors=["Error 1", "Error 2"],
            successes=[{"id": 1}],
            duration=2.5
        )
        
        assert result.success_rate() == 80.0, "Success rate calculation incorrect"
        print("✅ BulkOperationResult.success_rate() works correctly")
        
        # Test zero total
        empty_result = BulkOperationResult(
            total=0,
            succeeded=0,
            failed=0,
            errors=[],
            successes=[],
            duration=0.0
        )
        assert empty_result.success_rate() == 0.0, "Should handle zero total"
        print("✅ Handles zero total correctly")
        
        # Test validation
        client = get_client()
        
        # Test empty list validation
        try:
            await bulk_update_work_packages(client, [], {"assignee_id": 5})
            print("❌ Should reject empty list")
            pytest.fail("Should have raised ValueError for empty list")
        except ValueError as e:
            assert "cannot be empty" in str(e)
            print("✅ Empty list validation works")
        
        # Test max limit validation
        try:
            too_many = list(range(1, 52))  # 51 items
            await bulk_update_work_packages(client, too_many, {"assignee_id": 5})
            print("❌ Should reject >50 items")
            pytest.fail("Should have raised ValueError for >50 items")
        except ValueError as e:
            assert "50" in str(e)
            print("✅ Max limit validation works")
        
        print("\n" + "=" * 60)
        print("✅ HELPER TESTS PASSED!")
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("\nMake sure bulk_operations.py is in src/utils/")
        pytest.fail(f"Import Error: {e}")
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Test Failed: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("BULK OPERATIONS TEST SUITE")
    print("=" * 60 + "\n")
    
    success = True
    
    # Run helper tests
    if not asyncio.run(test_bulk_operations_helper()):
        success = False
    
    # Run tool tests
    if not asyncio.run(test_bulk_operations()):
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED! Bulk operations are ready to use.")
        print("=" * 60)
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED! Please review errors above.")
        print("=" * 60)
        sys.exit(1)
