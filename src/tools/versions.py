"""
Version/milestone management tools.

Based on code from haunguyendev (https://github.com/haunguyendev)
Fork: https://github.com/haunguyendev/openproject-mcp-server/tree/main (commit 28f097a)
"""

from typing import Optional
from pydantic import BaseModel, Field
from src.server import mcp, get_client
from src.utils.formatting import format_success, format_error


class CreateVersionInput(BaseModel):
    """Input model for creating versions."""

    project_id: int = Field(..., description="Project ID", gt=0)
    name: str = Field(..., description="Version name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Version description")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    due_date: Optional[str] = Field(None, description="Due date (YYYY-MM-DD)")
    status: Optional[str] = Field(None, description="Status (open, locked, closed)")


class UpdateVersionInput(BaseModel):
    """Input model for updating versions."""

    version_id: int = Field(..., description="Version ID to update", gt=0)
    name: Optional[str] = Field(None, description="New version name", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="New version description")
    start_date: Optional[str] = Field(None, description="New start date (YYYY-MM-DD)")
    due_date: Optional[str] = Field(None, description="New due date (YYYY-MM-DD)")
    status: Optional[str] = Field(None, description="New status (open, locked, closed)")


@mcp.tool
async def list_versions(project_id: int) -> str:
    """List all versions/milestones in a project.

    Args:
        project_id: The project ID

    Returns:
        List of versions with their details
    """
    try:
        client = get_client()

        result = await client.get_versions(project_id)
        versions = result.get("_embedded", {}).get("elements", [])

        if not versions:
            return f"No versions found for project #{project_id}."

        text = f"✅ **Versions for Project #{project_id} ({len(versions)}):**\n\n"
        for version in versions:
            text += f"**{version.get('name', 'Unnamed')}** (ID: {version.get('id', 'N/A')})\n"

            if version.get('description', {}).get('raw'):
                text += f"  Description: {version['description']['raw']}\n"

            if version.get('startDate'):
                text += f"  Start: {version['startDate']}\n"
            if version.get('endDate'):
                text += f"  End: {version['endDate']}\n"

            text += f"  Status: {version.get('status', 'Unknown')}\n"

            if "_embedded" in version and "definingProject" in version["_embedded"]:
                project = version["_embedded"]["definingProject"]
                text += f"  Project: {project.get('name', 'Unknown')}\n"

            text += "\n"

        return text

    except Exception as e:
        return format_error(f"Failed to list versions: {str(e)}")


@mcp.tool
async def get_version(version_id: int) -> str:
    """Get detailed information about a specific version/milestone.

    Args:
        version_id: The version ID

    Returns:
        Detailed version information including dates, status, and description
    """

    try:
        client = get_client()
        version = await client.get_version(version_id)

        text = f"✅ **Version #{version.get('id')}**\n\n"
        text += f"**Name**: {version.get('name', 'Unknown')}\n"

        if version.get('description', {}).get('raw'):
            text += f"**Description**: {version['description']['raw']}\n"

        if version.get('startDate'):
            text += f"**Start Date**: {version['startDate']}\n"
        if version.get('endDate'):
            text += f"**End Date**: {version['endDate']}\n"

        text += f"**Status**: {version.get('status', 'Unknown')}\n"

        # Add project information if available
        if "_embedded" in version and "definingProject" in version["_embedded"]:
            project = version["_embedded"]["definingProject"]
            text += f"**Project**: {project.get('name', 'Unknown')} (#{project.get('id', 'N/A')})\n"

        if version.get('createdAt'):
            text += f"**Created**: {version['createdAt']}\n"
        if version.get('updatedAt'):
            text += f"**Updated**: {version['updatedAt']}\n"

        return text

    except Exception as e:
        return format_error(f"Failed to get version: {str(e)}")


@mcp.tool
async def create_version(input: CreateVersionInput) -> str:
    """Create a new version/milestone in a project.

    Args:
        input: Version data including project_id, name, and optional fields

    Returns:
        Success message with created version details

    Example:
        {
            "project_id": 5,
            "name": "Version 1.0",
            "description": "First major release",
            "due_date": "2025-03-31",
            "status": "open"
        }
    """

    try:
        client = get_client()

        data = {
            "name": input.name,
        }

        if input.description:
            data["description"] = input.description
        if input.start_date:
            data["start_date"] = input.start_date
        if input.due_date:
            data["due_date"] = input.due_date
        if input.status:
            data["status"] = input.status

        result = await client.create_version(input.project_id, data)

        text = format_success("Version created successfully!\n\n")
        text += f"**Name**: {result.get('name', 'N/A')}\n"
        text += f"**ID**: #{result.get('id', 'N/A')}\n"

        if result.get('description', {}).get('raw'):
            text += f"**Description**: {result['description']['raw']}\n"

        if result.get('startDate'):
            text += f"**Start Date**: {result['startDate']}\n"
        if result.get('endDate'):
            text += f"**End Date**: {result['endDate']}\n"

        text += f"**Status**: {result.get('status', 'Unknown')}\n"

        return text

    except Exception as e:
        return format_error(f"Failed to create version: {str(e)}")


@mcp.tool
async def update_version(input: UpdateVersionInput) -> str:
    """Update an existing version/milestone.

    Args:
        input: Version update data including version_id and fields to update

    Returns:
        Success message with updated version details

    Example:
        Update version end date and status:
        {
            "version_id": 10,
            "due_date": "2025-04-30",
            "status": "locked"
        }
    """

    try:
        client = get_client()

        # Build update data dict (only include provided fields)
        data = {}

        if input.name is not None:
            data["name"] = input.name
        if input.description is not None:
            data["description"] = input.description
        if input.start_date is not None:
            data["start_date"] = input.start_date
        if input.due_date is not None:
            data["due_date"] = input.due_date
        if input.status is not None:
            data["status"] = input.status

        if not data:
            return format_error("No fields provided to update")

        result = await client.update_version(input.version_id, data)

        text = format_success(f"Version #{input.version_id} updated successfully!\n\n")
        text += f"**Name**: {result.get('name', 'N/A')}\n"

        if result.get('description', {}).get('raw'):
            text += f"**Description**: {result['description']['raw']}\n"

        if result.get('startDate'):
            text += f"**Start Date**: {result['startDate']}\n"
        if result.get('endDate'):
            text += f"**End Date**: {result['endDate']}\n"

        text += f"**Status**: {result.get('status', 'Unknown')}\n"

        return text

    except Exception as e:
        return format_error(f"Failed to update version: {str(e)}")


@mcp.tool
async def delete_version(version_id: int) -> str:
    """Delete a version/milestone.

    ⚠️ WARNING: This will remove the version and unassign it from all work packages.
    Work packages will NOT be deleted, only the version assignment will be removed.

    Args:
        version_id: ID of the version to delete

    Returns:
        Success or error message
    """

    try:
        client = get_client()

        success = await client.delete_version(version_id)

        if success:
            return format_success(f"Version #{version_id} deleted successfully")
        else:
            return format_error(f"Failed to delete version #{version_id}")

    except Exception as e:
        return format_error(f"Failed to delete version: {str(e)}")
