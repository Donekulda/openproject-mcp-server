"""Test script for bulk create work packages functionality.

Run this to verify bulk create operations are working correctly.
"""

import asyncio
import sys
import pytest
from src.server import get_client


@pytest.mark.asyncio
async def test_bulk_create_helper():
    """Test the bulk_create_work_packages helper function."""
    print("\n🧪 Testing Bulk Create Helper Function\n")
    print("=" * 60)
    
    try:
        from src.utils.bulk_operations import (
            BulkOperationResult,
            bulk_create_work_packages
        )
        
        print("✅ Successfully imported bulk_create_work_packages")
        print()
        
        client = get_client()
        
        # Test empty list validation
        try:
            await bulk_create_work_packages(client, [])
            print("❌ Should reject empty list")
            pytest.fail("Should have raised ValueError for empty list")
        except ValueError as e:
            assert "cannot be empty" in str(e)
            print("✅ Empty list validation works")
        
        # Test max limit validation (31 items > 30 limit)
        try:
            too_many = [
                {"project": 1, "subject": f"Task {i}", "type": 1}
                for i in range(31)
            ]
            await bulk_create_work_packages(client, too_many)
            print("❌ Should reject >30 items")
            pytest.fail("Should have raised ValueError for >30 items")
        except ValueError as e:
            assert "30" in str(e)
            print("✅ Max limit (30) validation works")
        
        # Test required field validation - missing 'project'
        try:
            invalid_data = [{"subject": "Test", "type": 1}]
            await bulk_create_work_packages(client, invalid_data)
            print("❌ Should reject missing 'project' field")
            pytest.fail("Should have raised ValueError for missing 'project'")
        except ValueError as e:
            assert "project" in str(e).lower()
            print("✅ Required field 'project' validation works")
        
        # Test required field validation - missing 'subject'
        try:
            invalid_data = [{"project": 1, "type": 1}]
            await bulk_create_work_packages(client, invalid_data)
            print("❌ Should reject missing 'subject' field")
            pytest.fail("Should have raised ValueError for missing 'subject'")
        except ValueError as e:
            assert "subject" in str(e).lower()
            print("✅ Required field 'subject' validation works")
        
        # Test required field validation - missing 'type'
        try:
            invalid_data = [{"project": 1, "subject": "Test"}]
            await bulk_create_work_packages(client, invalid_data)
            print("❌ Should reject missing 'type' field")
            pytest.fail("Should have raised ValueError for missing 'type'")
        except ValueError as e:
            assert "type" in str(e).lower()
            print("✅ Required field 'type' validation works")
        
        print("\n" + "=" * 60)
        print("✅ ALL HELPER VALIDATION TESTS PASSED!")
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("\nMake sure bulk_operations.py has bulk_create_work_packages")
        pytest.fail(f"Import Error: {e}")
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Test Failed: {e}")


@pytest.mark.asyncio
async def test_bulk_create_tool():
    """Test the bulk_create_work_packages MCP tool."""
    print("\n🧪 Testing Bulk Create MCP Tool\n")
    print("=" * 60)
    
    try:
        from src.tools import work_packages_bulk
        
        print("✅ Successfully imported work_packages_bulk module")
        
        # Check if tool exists
        assert hasattr(work_packages_bulk, 'bulk_create_work_packages'), \
            "Missing bulk_create_work_packages tool"
        print("✅ Found tool: bulk_create_work_packages")
        
        # Check if models exist
        assert hasattr(work_packages_bulk, 'BulkCreateTemplateInput'), \
            "Missing BulkCreateTemplateInput model"
        print("✅ Found model: BulkCreateTemplateInput")
        
        assert hasattr(work_packages_bulk, 'BulkCreateWorkPackageItem'), \
            "Missing BulkCreateWorkPackageItem model"
        print("✅ Found model: BulkCreateWorkPackageItem")
        
        assert hasattr(work_packages_bulk, 'BulkCreateWorkPackagesInput'), \
            "Missing BulkCreateWorkPackagesInput model"
        print("✅ Found model: BulkCreateWorkPackagesInput")
        
        print("\n" + "=" * 60)
        print("✅ TOOL STRUCTURE TESTS PASSED!")
        print("\nTo use in Claude, restart the MCP server and try:")
        print('  "Create 3 tasks in project 5: Setup DB, Create API, Write tests"')
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("\nMake sure work_packages_bulk.py is in src/tools/")
        pytest.fail(f"Import Error: {e}")
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Test Failed: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("BULK CREATE WORK PACKAGES TEST SUITE")
    print("=" * 60 + "\n")
    
    success = True
    
    # Run helper tests
    if not asyncio.run(test_bulk_create_helper()):
        success = False
    
    # Run tool tests
    if not asyncio.run(test_bulk_create_tool()):
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED! Bulk create is ready to use.")
        print("=" * 60)
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED! Please review errors above.")
        print("=" * 60)
        sys.exit(1)
