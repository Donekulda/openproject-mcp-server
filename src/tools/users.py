"""
User and role management tools.

Based on code from haunguyendev (https://github.com/haunguyendev)
Fork: https://github.com/haunguyendev/openproject-mcp-server/tree/main (commit 28f097a)
"""

from typing import Optional
from src.server import mcp, get_client
from src.utils.formatting import format_success, format_error


@mcp.tool
async def list_users(name: Optional[str] = None, status: Optional[str] = None) -> str:
    """List users in OpenProject.

    Args:
        name: Optional name filter (searches for partial matches)
        status: Optional status filter (e.g., "active", "locked")

    Returns:
        List of users with their details
    """
    try:
        client = get_client()

        filters = []
        if name:
            filters.append({"name": {"operator": "~", "values": [name]}})
        if status:
            filters.append({"status": {"operator": "=", "values": [status]}})

        import json
        filters_json = json.dumps(filters) if filters else None

        result = await client.get_users(filters_json)
        users = result.get("_embedded", {}).get("elements", [])

        if not users:
            return "No users found."

        text = f"✅ **Found {len(users)} user(s):**\n\n"
        for user in users:
            text += f"- **{user.get('name', 'Unknown')}** (ID: {user.get('id', 'N/A')})\n"
            text += f"  Email: {user.get('email', 'N/A')}\n"
            text += f"  Login: {user.get('login', 'N/A')}\n"
            text += f"  Status: {user.get('status', 'N/A')}\n"
            if user.get("admin"):
                text += "  ✓ Administrator\n"
            text += "\n"

        return text

    except Exception as e:
        return format_error(f"Failed to list users: {str(e)}")


@mcp.tool
async def get_user(user_id: int) -> str:
    """Get detailed information about a specific user.

    Args:
        user_id: The user ID

    Returns:
        Detailed user information
    """

    try:
        client = get_client()
        user = await client.get_user(user_id)

        text = f"✅ **User #{user.get('id')}**\n\n"
        text += f"**Name**: {user.get('name', 'Unknown')}\n"
        text += f"**Email**: {user.get('email', 'N/A')}\n"
        text += f"**Login**: {user.get('login', 'N/A')}\n"
        text += f"**Status**: {user.get('status', 'N/A')}\n"
        text += f"**Admin**: {'Yes' if user.get('admin') else 'No'}\n"

        if user.get('createdAt'):
            text += f"**Created**: {user['createdAt']}\n"
        if user.get('updatedAt'):
            text += f"**Updated**: {user['updatedAt']}\n"

        return text

    except Exception as e:
        return format_error(f"Failed to get user: {str(e)}")


@mcp.tool
async def list_roles() -> str:
    """List available user roles in OpenProject.

    Returns:
        List of roles with their permissions
    """

    try:
        client = get_client()

        result = await client.get_roles()
        roles = result.get("_embedded", {}).get("elements", [])

        if not roles:
            return "No roles found."

        text = "✅ **Available Roles:**\n\n"
        for role in roles:
            text += f"- **{role.get('name', 'Unnamed')}** (ID: {role.get('id', 'N/A')})\n"

        return text

    except Exception as e:
        return format_error(f"Failed to list roles: {str(e)}")


@mcp.tool
async def get_role(role_id: int) -> str:
    """Get detailed information about a specific role.

    Args:
        role_id: The role ID

    Returns:
        Detailed role information including permissions
    """

    try:
        client = get_client()
        role = await client.get_role(role_id)

        text = f"✅ **Role #{role.get('id')}**\n\n"
        text += f"**Name**: {role.get('name', 'Unknown')}\n"

        # Add permissions if available
        if "_embedded" in role and "permissions" in role["_embedded"]:
            perms = role["_embedded"]["permissions"]
            if perms:
                text += f"\n**Permissions** ({len(perms)}):\n"
                for perm in perms[:10]:  # Show first 10
                    text += f"- {perm.get('name', 'Unknown')}\n"
                if len(perms) > 10:
                    text += f"... and {len(perms) - 10} more\n"

        return text

    except Exception as e:
        return format_error(f"Failed to get role: {str(e)}")



@mcp.tool
async def list_user_projects(user_id: int) -> str:
    """List all projects a user is a member of.

    Args:
        user_id: The user ID

    Returns:
        List of projects the user belongs to
    """

    try:
        client = get_client()

        import json
        filters = json.dumps([{"principal": {"operator": "=", "values": [str(user_id)]}}])

        result = await client.get_memberships(filters)
        memberships = result.get("_embedded", {}).get("elements", [])

        if not memberships:
            return f"User #{user_id} is not a member of any projects."

        text = f"✅ **Projects for User #{user_id} ({len(memberships)}):**\n\n"
        for member in memberships:
            embedded = member.get("_embedded", {})

            if "project" in embedded:
                project_name = embedded["project"].get("name", "Unknown")
                text += f"- **{project_name}**\n"

            if "roles" in embedded:
                roles = [r.get("name", "Unknown") for r in embedded["roles"]]
                text += f"  Roles: {', '.join(roles)}\n"

            text += "\n"

        return text

    except Exception as e:
        return format_error(f"Failed to list user projects: {str(e)}")
