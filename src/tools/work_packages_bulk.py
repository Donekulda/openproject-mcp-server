"""Bulk operations tools for work packages.

This module provides MCP tools for performing bulk operations on multiple
work packages simultaneously, significantly reducing manual effort.

Based on code from haunguyendev (https://github.com/haunguyendev)
Fork: https://github.com/haunguyendev/openproject-mcp-server/tree/main (commit 28f097a)
"""


import json
import asyncio
import time
from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field

from src.server import mcp, get_client
from src.utils.bulk_operations import (
    bulk_update_work_packages,
    bulk_delete_work_packages,
    BulkOperationResult
)
from src.utils.formatting import format_success, format_error


# This module contains 7 bulk operation tools:
# 1. bulk_create_work_packages - Create multiple work packages at once
# 2. bulk_add_comment - Add same comment to multiple work packages
# 3. bulk_update_filtered_work_packages - Most powerful bulk update with filtering
# 4. bulk_set_work_package_parents - Set same parent for multiple work packages
# 5. bulk_remove_work_package_parents - Remove parent from multiple work packages
# 6. bulk_create_work_package_relations - Create multiple relations at once
# 7. bulk_delete_work_package_relations - Delete multiple relations at once


# ============================================================================
# BULK CREATE WORK PACKAGES
# ============================================================================

class BulkCreateTemplateInput(BaseModel):
    """Template with common fields for all work packages."""

    project_id: int = Field(..., description="Project ID where work packages will be created", gt=0)
    type_id: int = Field(..., description="Work package type ID (e.g., Task, Bug, Feature)", gt=0)
    priority_id: Optional[int] = Field(None, description="Default priority ID", gt=0)
    assignee_id: Optional[int] = Field(None, description="Default assignee user ID", gt=0)
    version_id: Optional[int] = Field(None, description="Default version/milestone ID", gt=0)
    start_date: Optional[str] = Field(None, description="Default start date (YYYY-MM-DD)")
    due_date: Optional[str] = Field(None, description="Default due date (YYYY-MM-DD)")
    description: Optional[str] = Field(None, description="Default description for all work packages")


class BulkCreateWorkPackageItem(BaseModel):
    """Individual work package data that can override template fields."""

    subject: str = Field(..., description="Work package subject/title", min_length=1)
    description: Optional[str] = Field(None, description="Override template description")
    priority_id: Optional[int] = Field(None, description="Override template priority", gt=0)
    assignee_id: Optional[int] = Field(None, description="Override template assignee", gt=0)
    version_id: Optional[int] = Field(None, description="Override template version", gt=0)
    start_date: Optional[str] = Field(None, description="Override template start date (YYYY-MM-DD)")
    due_date: Optional[str] = Field(None, description="Override template due date (YYYY-MM-DD)")


class BulkCreateWorkPackagesInput(BaseModel):
    """Input for bulk creating work packages with template pattern."""

    template: BulkCreateTemplateInput = Field(..., description="Common template for all work packages")
    work_packages: list[BulkCreateWorkPackageItem] = Field(
        ..., 
        description="List of work packages to create (max 30)",
        min_length=1,
        max_length=30
    )


@mcp.tool
async def bulk_create_work_packages(input: BulkCreateWorkPackagesInput) -> str:
    """Create multiple work packages at once with a shared template.
    
    This tool significantly reduces time for creating multiple similar tasks.
    Uses template pattern to avoid repetition of common fields.
    
    Performance: Creates 20 work packages in ~2-3 seconds vs ~10 seconds sequentially.
    
    Args:
        input: Template + list of work packages to create (max 30)
    
    Returns:
        Detailed summary of created work packages with success/failure info
    
    Example:
        Create 3 bugs in project 5 with same type and priority:
        {
            "template": {
                "project_id": 5,
                "type_id": 1,
                "priority_id": 3
            },
            "work_packages": [
                {"subject": "Fix login bug", "assignee_id": 7},
                {"subject": "Fix payment bug", "due_date": "2025-01-15"},
                {"subject": "Fix UI bug"}
            ]
        }
    """

    try:
        client = get_client()
        
        # Merge template with individual work package data
        work_packages_data = []
        template_dict = input.template.model_dump(exclude_none=True)
        
        for wp_item in input.work_packages:
            # Start with template
            wp_data = {
                "project": template_dict["project_id"],
                "type": template_dict["type_id"],
                "subject": wp_item.subject,
            }
            
            # Add template fields (using API field names)
            if "priority_id" in template_dict:
                wp_data["priority_id"] = template_dict["priority_id"]
            if "assignee_id" in template_dict:
                wp_data["assignee_id"] = template_dict["assignee_id"]
            if "version_id" in template_dict:
                wp_data["version_id"] = template_dict["version_id"]
            if "start_date" in template_dict:
                wp_data["startDate"] = template_dict["start_date"]
            if "due_date" in template_dict:
                wp_data["dueDate"] = template_dict["due_date"]
            if "description" in template_dict:
                wp_data["description"] = template_dict["description"]
            
            # Override with individual work package fields
            wp_item_dict = wp_item.model_dump(exclude_none=True, exclude={"subject"})
            if "priority_id" in wp_item_dict:
                wp_data["priority_id"] = wp_item_dict["priority_id"]
            if "assignee_id" in wp_item_dict:
                wp_data["assignee_id"] = wp_item_dict["assignee_id"]
            if "version_id" in wp_item_dict:
                wp_data["version_id"] = wp_item_dict["version_id"]
            if "start_date" in wp_item_dict:
                wp_data["startDate"] = wp_item_dict["start_date"]
            if "due_date" in wp_item_dict:
                wp_data["dueDate"] = wp_item_dict["due_date"]
            if "description" in wp_item_dict:
                wp_data["description"] = wp_item_dict["description"]
            
            work_packages_data.append(wp_data)
        
        # Execute bulk create
        from src.utils.bulk_operations import bulk_create_work_packages as bulk_create_util
        result = await bulk_create_util(client, work_packages_data)
        
        # Format response
        text = f"## 📦 Bulk Create Work Packages Results\n\n"
        text += f"**Total**: {result.total} | "
        text += f"**✅ Succeeded**: {result.succeeded} | "
        text += f"**❌ Failed**: {result.failed} | "
        text += f"**⏱️ Duration**: {result.duration:.2f}s\n\n"
        
        # Success rate
        success_rate = result.success_rate()
        if success_rate == 100.0:
            text += f"🎉 **Perfect!** All work packages created successfully!\n\n"
        elif success_rate >= 80.0:
            text += f"✅ **Good!** {success_rate:.1f}% success rate\n\n"
        else:
            text += f"⚠️ **Partial Success**: {success_rate:.1f}% success rate\n\n"
        
        # Show created work packages
        if result.successes:
            text += "### ✅ Created Work Packages\n\n"
            for wp in result.successes:
                wp_id = wp.get("id")
                subject = wp.get("subject", "Unknown")
                
                # Get embedded data
                embedded = wp.get("_embedded", {})
                type_name = embedded.get("type", {}).get("name", "Unknown")
                status_name = embedded.get("status", {}).get("name", "Unknown")
                
                text += f"- **#{wp_id}**: {subject}\n"
                text += f"  - Type: {type_name} | Status: {status_name}\n"
                
                # Add assignee if present
                if "assignee" in embedded:
                    assignee_name = embedded["assignee"].get("name", "Unknown")
                    text += f"  - Assignee: {assignee_name}\n"
                
                # Add dates if present
                dates = []
                if wp.get("startDate"):
                    dates.append(f"Start: {wp['startDate']}")
                if wp.get("dueDate"):
                    dates.append(f"Due: {wp['dueDate']}")
                if dates:
                    text += f"  - {' | '.join(dates)}\n"
                
                text += "\n"
        
        # Show errors
        if result.errors:
            text += "### ❌ Failed to Create\n\n"
            for error in result.errors:
                text += f"- {error}\n"
            text += "\n"
            
            text += "**💡 Tip**: Check that all required fields are valid and the user has permissions.\n"
        
        return text
        
    except ValueError as e:
        return format_error(f"Validation error: {str(e)}")
    except Exception as e:
        return format_error(f"Failed to bulk create work packages: {str(e)}")


# ============================================================================
# BULK ADD COMMENT
# ============================================================================

@mcp.tool
async def bulk_add_comment(
    work_package_ids: str,
    comment: str,
    internal: bool = False
) -> str:
    """Add the same comment to multiple work packages.
    
    Useful for status updates, notifications, or bulk communication.
    Max 50 work packages per call.
    
    Args:
        work_package_ids: Comma-separated work package IDs (e.g., "10,20,30") - max 50
        comment: Comment text to add (supports markdown)
        internal: If True, comment is only visible to project members (default: False)
        
    Returns:
        Success/failure summary
        
    Example:
        Add comment "Please review by Friday" to tasks #10, #20, #30:
        {
            "work_package_ids": "10,20,30",
            "comment": "Please review by Friday",
            "internal": false
        }
    """

    try:
        client = get_client()
        
        # Parse comma-separated IDs
        try:
            wp_ids = [int(id.strip()) for id in work_package_ids.split(",") if id.strip()]
        except ValueError:
            return format_error("work_package_ids must be comma-separated integers")
        
        # Validation
        if not wp_ids:
            return format_error("work_package_ids cannot be empty")
        if len(wp_ids) > 50:
            return format_error(f"Max 50 work packages (got {len(wp_ids)})")
        if not comment or not comment.strip():
            return format_error("Comment cannot be empty")
        
        # Create async tasks for adding comments
        tasks = [
            client.add_work_package_comment(wp_id, comment, internal)
            for wp_id in wp_ids
        ]
        
        # Execute concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        # Process results
        successes = sum(1 for r in results if not isinstance(r, Exception))
        failures = sum(1 for r in results if isinstance(r, Exception))
        errors = [str(r) for r in results if isinstance(r, Exception)]
        
        # Format response
        comment_preview = comment[:50] + "..." if len(comment) > 50 else comment
        
        text = f"✅ **Bulk Comment Complete!**\n\n"
        text += f"**Comment**: \"{comment_preview}\"\n"
        text += f"**Internal**: {internal}\n"
        text += f"**Total**: {len(wp_ids)} | **Success**: {successes} | **Failed**: {failures}\n"
        text += f"**Success Rate**: {(successes/len(wp_ids)*100) if wp_ids else 0:.1f}%\n"
        text += f"**Duration**: {duration:.2f}s\n\n"
        
        if failures > 0:
            text += f"**Errors** (first 5):\n"
            for i, error in enumerate(errors[:5], 1):
                text += f"{i}. {error}\n"
            if failures > 5:
                text += f"... and {failures - 5} more\n"
        
        if successes > 0:
            text += f"\n✅ Comment added to {successes} work package(s)\n"
        
        return text
        
    except Exception as e:
        return format_error(f"Bulk comment failed: {str(e)}")


@mcp.tool
async def bulk_update_filtered_work_packages(
    # Filter criteria (reuse from list_work_packages)
    project_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    priority_ids: Optional[str] = None,
    type_ids: Optional[str] = None,
    status_ids: Optional[str] = None,
    overdue_only: bool = False,
    unassigned_only: bool = False,
    
    # Update data
    update_assignee_id: Optional[int] = None,
    update_status_id: Optional[int] = None,
    update_priority_id: Optional[int] = None,
    update_version_id: Optional[int] = None,
    
    # Safety
    dry_run: bool = True,
    max_results: int = 50
) -> str:
    """Apply bulk update to work packages matching filter criteria.
    
    This is the MOST POWERFUL bulk operation tool - combines flexible
    filtering with bulk updates.
    
    **SAFETY**: dry_run=True by default - shows preview without updating.
    Set dry_run=False to execute the updates.
    
    Args:
        # Filter params (same as list_work_packages)
        project_id: Filter by project
        assignee_id: Filter by assignee  
        priority_ids: Comma-separated priority IDs
        type_ids: Comma-separated type IDs
        status_ids: Comma-separated status IDs
        overdue_only: Only overdue tasks
        unassigned_only: Only unassigned tasks
        
        # Update params
        update_assignee_id: New assignee to set
        update_status_id: New status to set
        update_priority_id: New priority to set
        update_version_id: New version to set
        
        # Safety params
        dry_run: If True, only show preview (default: True)
        max_results: Max work packages to update (default: 50)
        
    Returns:
        Preview (if dry_run=True) or update summary (if dry_run=False)
        
    Example 1 - PREVIEW:
        Preview: Assign all overdue unassigned tasks to user #5:
        {
            "overdue_only": true,
            "unassigned_only": true,
            "update_assignee_id": 5,
            "dry_run": true
        }
        
    Example 2 - EXECUTE:
        Execute the update:
        {
            "overdue_only": true,
            "unassigned_only": true,
            "update_assignee_id": 5,
            "dry_run": false
        }
    """

    try:
        client = get_client()
        
        # Build filters (reuse logic from list_work_packages)
        filters_list = []
        
        # Status filter
        if status_ids:
            # Parse comma-separated IDs
            sids = [s.strip() for s in status_ids.split(",") if s.strip()]
            if sids:
                filters_list.append({"status": {"operator": "=", "values": sids}})
        elif overdue_only:
            filters_list.append({"status": {"operator": "o", "values": []}})
            filters_list.append({
                "dueDate": {
                    "operator": "<>d",
                    "values": ["2000-01-01", date.today().isoformat()]
                }
            })
        else:
            filters_list.append({"status": {"operator": "o", "values": []}})
        
        # Assignee filter
        if unassigned_only:
            filters_list.append({"assignee": {"operator": "!*", "values": []}})
        elif assignee_id:
            filters_list.append({"assignee": {"operator": "=", "values": [str(assignee_id)]}})
        
        # Priority filter
        if priority_ids:
            pids = [p.strip() for p in priority_ids.split(",") if p.strip()]
            if pids:
                filters_list.append({"priority": {"operator": "=", "values": pids}})
        
        # Type filter
        if type_ids:
            tids = [t.strip() for t in type_ids.split(",") if t.strip()]
            if tids:
                filters_list.append({"type": {"operator": "=", "values": tids}})
        
        filters = json.dumps(filters_list) if filters_list else None
        
        # Query work packages matching filter
        result = await client.get_work_packages(
            project_id=project_id,
            filters=filters,
            page_size=max_results
        )
        
        work_packages = result.get("_embedded", {}).get("elements", [])
        total_found = result.get("total", 0)
        
        if not work_packages:
            return "✅ No work packages match the filter criteria."
        
        # Build update data
        update_data = {}
        if update_assignee_id is not None:
            update_data["assignee_id"] = update_assignee_id
        if update_status_id is not None:
            update_data["status_id"] = update_status_id
        if update_priority_id is not None:
            update_data["priority_id"] = update_priority_id
        if update_version_id is not None:
            update_data["version_id"] = update_version_id
        
        if not update_data:
            return format_error("At least one update field must be provided")
        
        # DRY RUN MODE
        if dry_run:
            text = f"🔍 **DRY RUN - Preview of Bulk Update**\n\n"
            text += f"**Filter Matched**: {total_found} work package(s)\n"
            text += f"**Will Update**: {len(work_packages)} work package(s) (max: {max_results})\n\n"
            
            text += f"**Updates to Apply**:\n"
            for key, value in update_data.items():
                text += f"- {key}: {value}\n"
            
            text += f"\n**Preview of Affected Work Packages** (first 10):\n"
            for wp in work_packages[:10]:
                text += f"- #{wp.get('id')}: {wp.get('subject', 'Unknown')}\n"
            
            if len(work_packages) > 10:
                text += f"... and {len(work_packages) - 10} more\n"
            
            text += f"\n⚠️ **This is a DRY RUN** - No changes were made.\n"
            text += f"To execute, call again with: dry_run=false\n"
            
            return text
        
        # EXECUTE MODE
        wp_ids = [wp["id"] for wp in work_packages]
        
        # Execute bulk update
        bulk_result = await bulk_update_work_packages(client, wp_ids, update_data)
        
        # Format response
        text = f"✅ **Bulk Update Complete!**\n\n"
        text += f"**Filter Matched**: {total_found} total\n"
        text += f"**Updated**: {bulk_result.succeeded}/{bulk_result.total}\n"
        text += f"**Failed**: {bulk_result.failed}\n"
        text += f"**Success Rate**: {bulk_result.success_rate():.1f}%\n"
        text += f"**Duration**: {bulk_result.duration:.2f}s\n\n"
        
        if bulk_result.failed > 0:
            text += f"**Errors** (first 3):\n"
            for i, error in enumerate(bulk_result.errors[:3], 1):
                text += f"{i}. {error}\n"
        
        if bulk_result.succeeded > 0:
            text += f"\n**Updated Work Packages** (first 5):\n"
            for wp in bulk_result.successes[:5]:
                text += f"- #{wp.get('id')}: {wp.get('subject', 'Unknown')}\n"
            if bulk_result.succeeded > 5:
                text += f"... and {bulk_result.succeeded - 5} more\n"
        
        return text
        
    except Exception as e:
        return format_error(f"Bulk filtered update failed: {str(e)}")
# ============================================================================
# BULK HIERARCHY OPERATIONS
# ============================================================================

@mcp.tool
async def bulk_set_work_package_parents(
    child_ids: str,
    parent_id: int
) -> str:
    """Set same parent for multiple work packages at once.
    
    Useful for sprint planning, epic management, and creating work breakdown structures.
    Max 50 work packages per call.
    
    Args:
        child_ids: Comma-separated child work package IDs (e.g., "10,20,30") - max 50
        parent_id: Parent work package ID to set for all children
        
    Returns:
        Success/failure summary with details
        
    Example:
        Set work packages #10, #20, #30 as children of Epic #5:
        {
            "child_ids": "10,20,30",
            "parent_id": 5
        }
    """

    try:
        client = get_client()
        
        # Parse comma-separated IDs
        try:
            wp_ids = [int(id.strip()) for id in child_ids.split(",") if id.strip()]
        except ValueError:
            return format_error("child_ids must be comma-separated integers")
        
        # Validation
        if not wp_ids:
            return format_error("child_ids cannot be empty")
        
        # Execute bulk set parents
        from src.utils.bulk_operations import bulk_set_parents
        result = await bulk_set_parents(client, wp_ids, parent_id)
        
        # Format response
        text = f"## 🔗 Bulk Set Parents Results\\n\\n"
        text += f"**Parent**: #{parent_id}\\n"
        text += f"**Total Children**: {result.total} | "
        text += f"**✅ Succeeded**: {result.succeeded} | "
        text += f"**❌ Failed**: {result.failed} | "
        text += f"**⏱️ Duration**: {result.duration:.2f}s\\n\\n"
        
        # Success rate
        success_rate = result.success_rate()
        if success_rate == 100.0:
            text += f"🎉 **Perfect!** All work packages now have parent #{parent_id}!\\n\\n"
        elif success_rate >= 80.0:
            text += f"✅ **Good!** {success_rate:.1f}% success rate\\n\\n"
        else:
            text += f"⚠️ **Partial Success**: {success_rate:.1f}% success rate\\n\\n"
        
        # Show errors if any
        if result.errors:
            text += "### ❌ Failed to Set Parent\\n\\n"
            for error in result.errors[:10]:  # Show first 10
                text += f"- {error}\\n"
            if len(result.errors) > 10:
                text += f"... and {len(result.errors) - 10} more\\n"
            text += "\\n"
        
        if result.succeeded > 0:
            text += f"✅ Successfully set parent for {result.succeeded} work package(s)\\n"
        
        return text
        
    except Exception as e:
        return format_error(f"Bulk set parents failed: {str(e)}")


@mcp.tool
async def bulk_remove_work_package_parents(
    work_package_ids: str
) -> str:
    """Remove parent from multiple work packages (promote to top-level).
    
    This promotes child work packages to top-level tasks by removing their parent.
    Useful for restructuring work breakdown or promoting tasks.
    Max 50 work packages per call.
    
    Args:
        work_package_ids: Comma-separated work package IDs (e.g., "10,20,30") - max 50
        
    Returns:
        Success/failure summary with details
        
    Example:
        Remove parent from work packages #10, #20, #30:
        {
            "work_package_ids": "10,20,30"
        }
    """

    try:
        client = get_client()
        
        # Parse comma-separated IDs
        try:
            wp_ids = [int(id.strip()) for id in work_package_ids.split(",") if id.strip()]
        except ValueError:
            return format_error("work_package_ids must be comma-separated integers")
        
        # Validation
        if not wp_ids:
            return format_error("work_package_ids cannot be empty")
        
        # Execute bulk remove parents
        from src.utils.bulk_operations import bulk_remove_parents
        result = await bulk_remove_parents(client, wp_ids)
        
        # Format response
        text = f"## 🔓 Bulk Remove Parents Results\\n\\n"
        text += f"**Total**: {result.total} | "
        text += f"**✅ Succeeded**: {result.succeeded} | "
        text += f"**❌ Failed**: {result.failed} | "
        text += f"**⏱️ Duration**: {result.duration:.2f}s\\n\\n"
        
        # Success rate
        success_rate = result.success_rate()
        if success_rate == 100.0:
            text += f"🎉 **Perfect!** All work packages promoted to top-level!\\n\\n"
        elif success_rate >= 80.0:
            text += f"✅ **Good!** {success_rate:.1f}% success rate\\n\\n"
        else:
            text += f"⚠️ **Partial Success**: {success_rate:.1f}% success rate\\n\\n"
        
        # Show errors if any
        if result.errors:
            text += "### ❌ Failed to Remove Parent\\n\\n"
            for error in result.errors[:10]:
                text += f"- {error}\\n"
            if len(result.errors) > 10:
                text += f"... and {len(result.errors) - 10} more\\n"
            text += "\\n"
        
        if result.succeeded > 0:
            text += f"✅ Successfully removed parent from {result.succeeded} work package(s)\\n"
        
        return text
        
    except Exception as e:
        return format_error(f"Bulk remove parents failed: {str(e)}")


# ============================================================================
# BULK RELATIONS OPERATIONS
# ============================================================================

class BulkCreateRelationItem(BaseModel):
    """Single relation to create."""

    from_id: int = Field(..., description="Source work package ID", gt=0)
    to_id: int = Field(..., description="Target work package ID", gt=0)
    type: str = Field(..., description="Relation type (follows, blocks, relates, etc.)")
    lag: Optional[int] = Field(None, description="Lag in working days")
    description: Optional[str] = Field(None, description="Relation description")


class BulkCreateRelationsInput(BaseModel):
    """Input for bulk creating work package relations."""

    relations: list[BulkCreateRelationItem] = Field(
        ..., 
        description="List of relations to create (max 30)",
        min_length=1,
        max_length=30
    )


@mcp.tool
async def bulk_create_work_package_relations(
    input: BulkCreateRelationsInput
) -> str:
    """Create multiple work package relations at once.
    
    Useful for creating dependency chains, marking duplicates, setting up blocks, etc.
    Much faster than creating relations one by one.
    Max 30 relations per call.
    
    Relation types: relates, duplicates, blocks, precedes, follows, includes, requires, partof
    
    Args:
        input: List of relations to create with from_id, to_id, type, and optional lag/description
        
    Returns:
        Detailed summary of created relations with success/failure info
        
    Example - Create dependency chain:
        {
            "relations": [
                {"from_id": 10, "to_id": 20, "type": "follows"},
                {"from_id": 20, "to_id": 30, "type": "follows"},
                {"from_id": 30, "to_id": 40, "type": "follows", "lag": 2}
            ]
        }
    """

    try:
        client = get_client()
        
        # Convert Pydantic models to dicts for API
        relations_data = []
        for rel_item in input.relations:
            rel_dict = {
                "from_id": rel_item.from_id,
                "to_id": rel_item.to_id,
                "type": rel_item.type
            }
            if rel_item.lag is not None:
                rel_dict["lag"] = rel_item.lag
            if rel_item.description:
                rel_dict["description"] = rel_item.description
            
            relations_data.append(rel_dict)
        
        # Execute bulk create
        from src.utils.bulk_operations import bulk_create_relations
        result = await bulk_create_relations(client, relations_data)
        
        # Format response
        text = f"## 🔗 Bulk Create Relations Results\\n\\n"
        text += f"**Total**: {result.total} | "
        text += f"**✅ Succeeded**: {result.succeeded} | "
        text += f"**❌ Failed**: {result.failed} | "
        text += f"**⏱️ Duration**: {result.duration:.2f}s\\n\\n"
        
        # Success rate
        success_rate = result.success_rate()
        if success_rate == 100.0:
            text += f"🎉 **Perfect!** All relations created successfully!\\n\\n"
        elif success_rate >= 80.0:
            text += f"✅ **Good!** {success_rate:.1f}% success rate\\n\\n"
        else:
            text += f"⚠️ **Partial Success**: {success_rate:.1f}% success rate\\n\\n"
        
        # Show created relations
        if result.successes:
            text += "### ✅ Created Relations\\n\\n"
            for rel in result.successes[:15]:  # Show first 15
                rel_id = rel.get("id", "?")
                rel_type = rel.get("type", "Unknown")
                
                # Get embedded data
                embedded = rel.get("_embedded", {})
                from_subject = embedded.get("from", {}).get("subject", "Unknown")
                to_subject = embedded.get("to", {}).get("subject", "Unknown")
                
                text += f"- **#{rel_id}**: {from_subject} **{rel_type}** {to_subject}"
                
                if rel.get("lag"):
                    text += f" (lag: {rel['lag']} days)"
                text += "\\n"
            
            if len(result.successes) > 15:
                text += f"... and {len(result.successes) - 15} more\\n"
            text += "\\n"
        
        # Show errors
        if result.errors:
            text += "### ❌ Failed to Create\\n\\n"
            for error in result.errors[:10]:
                text += f"- {error}\\n"
            if len(result.errors) > 10:
                text += f"... and {len(result.errors) - 10} more\\n"
            text += "\\n"
            
            text += "**💡 Tip**: Check that work package IDs exist and relation types are valid.\\n"
        
        return text
        
    except ValueError as e:
        return format_error(f"Validation error: {str(e)}")
    except Exception as e:
        return format_error(f"Failed to bulk create relations: {str(e)}")


@mcp.tool
async def bulk_delete_work_package_relations(
    relation_ids: str
) -> str:
    """Delete multiple work package relations at once.
    
    **WARNING**: This is a destructive operation. Deleted relations cannot be recovered.
    Max 30 relations per call.
    
    Args:
        relation_ids: Comma-separated relation IDs (e.g., "100,101,102") - max 30
        
    Returns:
        Success/failure summary with details
        
    Example:
        Delete relations #100, #101, #102:
        {
            "relation_ids": "100,101,102"
        }
    """

    try:
        client = get_client()
        
        # Parse comma-separated IDs
        try:
            rel_ids = [int(id.strip()) for id in relation_ids.split(",") if id.strip()]
        except ValueError:
            return format_error("relation_ids must be comma-separated integers")
        
        # Validation
        if not rel_ids:
            return format_error("relation_ids cannot be empty")
        
        # Execute bulk delete
        from src.utils.bulk_operations import bulk_delete_relations
        result = await bulk_delete_relations(client, rel_ids)
        
        # Format response
        text = f"## 🗑️ Bulk Delete Relations Results\\n\\n"
        text += f"**Total**: {result.total} | "
        text += f"**✅ Succeeded**: {result.succeeded} | "
        text += f"**❌ Failed**: {result.failed} | "
        text += f"**⏱️ Duration**: {result.duration:.2f}s\\n\\n"
        
        # Success rate
        success_rate = result.success_rate()
        if success_rate == 100.0:
            text += f"🎉 **Perfect!** All relations deleted successfully!\\n\\n"
        elif success_rate >= 80.0:
            text += f"✅ **Good!** {success_rate:.1f}% success rate\\n\\n"
        else:
            text += f"⚠️ **Partial Success**: {success_rate:.1f}% success rate\\n\\n"
        
        # Show errors if any
        if result.errors:
            text += "### ❌ Failed to Delete\\n\\n"
            for error in result.errors[:10]:
                text += f"- {error}\\n"
            if len(result.errors) > 10:
                text += f"... and {len(result.errors) - 10} more\\n"
            text += "\\n"
        
        if result.succeeded > 0:
            text += f"✅ Successfully deleted {result.succeeded} relation(s)\\n"
        
        return text
        
    except Exception as e:
        return format_error(f"Bulk delete relations failed: {str(e)}")
