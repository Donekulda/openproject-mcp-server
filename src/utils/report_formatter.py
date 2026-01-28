"""
Report formatting utilities for weekly reports.

Based on code from haunguyendev (https://github.com/haunguyendev)
Fork: https://github.com/haunguyendev/openproject-mcp-server/tree/main (commit 28f097a)
"""

from typing import Dict, List, Optional, Any
from datetime import datetime


def calculate_metrics(work_packages: List[Dict], time_entries: List[Dict]) -> Dict:
    """Calculate key metrics from work packages and time entries.
    
    Args:
        work_packages: List of work package dictionaries
        time_entries: List of time entry dictionaries
        
    Returns:
        Dictionary with calculated metrics
    """
    metrics = {
        'total_wps': len(work_packages),
        'done_count': 0,
        'in_progress_count': 0,
        'planned_count': 0,
        'blocked_count': 0,
        'bug_count': 0,
        'feature_count': 0,
        'total_hours': 0.0,
        'dev_hours': 0.0,
        'qa_hours': 0.0,
        'management_hours': 0.0,
    }
    
    # Count work packages by status and type
    for wp in work_packages:
        # Status analysis - try _embedded first, fallback to _links.status.title
        status_obj = wp.get('_embedded', {}).get('status', {})
        status_name = status_obj.get('name', '').lower()
        
        # Fallback: if no status in _embedded, try _links
        if not status_name or status_name == 'unknown':
            status_link = wp.get('_links', {}).get('status', {})
            status_name = status_link.get('title', '').lower()
        
        # Handle empty status by treating as planned
        if not status_name or status_name == 'unknown':
            metrics['planned_count'] += 1
        elif 'closed' in status_name or 'done' in status_name or 'resolved' in status_name or 'completed' in status_name or 'finished' in status_name:
            metrics['done_count'] += 1
        elif 'progress' in status_name or 'development' in status_name or 'implementing' in status_name:
            metrics['in_progress_count'] += 1
        elif 'blocked' in status_name:
            metrics['blocked_count'] += 1
        elif 'new' in status_name or 'open' in status_name or 'specified' in status_name or 'to do' in status_name:
            metrics['planned_count'] += 1
        else:
            # Default unknown statuses to planned
            metrics['planned_count'] += 1
            
        # Type analysis
        wp_type = wp.get('_embedded', {}).get('type', {}).get('name', '').lower()
        if 'bug' in wp_type or 'defect' in wp_type:
            metrics['bug_count'] += 1
        elif 'feature' in wp_type or 'story' in wp_type or 'task' in wp_type:
            metrics['feature_count'] += 1
    
    # Calculate hours by activity
    for te in time_entries:
        hours = float(te.get('hours', 0))
        metrics['total_hours'] += hours
        
        activity = te.get('_embedded', {}).get('activity', {}).get('name', '').lower()
        if 'development' in activity or 'implement' in activity:
            metrics['dev_hours'] += hours
        elif 'test' in activity or 'qa' in activity:
            metrics['qa_hours'] += hours
        elif 'management' in activity or 'meeting' in activity:
            metrics['management_hours'] += hours
    
    return metrics


def group_by_status(work_packages: List[Dict]) -> Dict[str, List[Dict]]:
    """Group work packages by status category.
    
    Args:
        work_packages: List of work package dictionaries
        
    Returns:
        Dictionary with keys: done, in_progress, planned, blocked, other
    """
    groups = {
        'done': [],
        'in_progress': [],
        'planned': [],
        'blocked': [],
        'de_scoped': [],
        'other': []
    }
    
    for wp in work_packages:
        # Try _embedded first, fallback to _links.status.title
        status_obj = wp.get('_embedded', {}).get('status', {})
        status_name = status_obj.get('name', '').lower()
        
        # Fallback: if no status in _embedded, try _links
        if not status_name or status_name == 'unknown':
            status_link = wp.get('_links', {}).get('status', {})
            status_name = status_link.get('title', '').lower()
        
        # If status still empty or Unknown, default to 'planned'
        if not status_name or status_name == 'unknown':
            # For work packages without clear status, default to 'planned'
            # This is safer than categorizing as 'other' which won't show in main sections
            groups['planned'].append(wp)
            continue
        
        if 'closed' in status_name or 'done' in status_name or 'resolved' in status_name or 'completed' in status_name or 'finished' in status_name:
            groups['done'].append(wp)
        elif 'progress' in status_name or 'development' in status_name or 'implementing' in status_name:
            groups['in_progress'].append(wp)
        elif 'blocked' in status_name:
            groups['blocked'].append(wp)
        elif 'rejected' in status_name or 'cancelled' in status_name:
            groups['de_scoped'].append(wp)
        elif 'new' in status_name or 'open' in status_name or 'specified' in status_name or 'to do' in status_name:
            groups['planned'].append(wp)
        else:
            # Unknown status types default to 'planned' to ensure visibility
            groups['planned'].append(wp)
    
    return groups


def detect_blockers(work_packages: List[Dict], relations: List[Dict] = None) -> List[Dict]:
    """Detect blocked work packages and their blockers.
    
    Args:
        work_packages: List of work package dictionaries
        relations: Optional list of relation dictionaries
        
    Returns:
        List of blocked work packages with blocker information
    """
    blockers = []
    
    for wp in work_packages:
        status_name = wp.get('_embedded', {}).get('status', {}).get('name', '').lower()
        if 'blocked' in status_name:
            blockers.append({
                'id': wp.get('id'),
                'subject': wp.get('subject'),
                'assignee': wp.get('_embedded', {}).get('assignee', {}).get('name', 'Unassigned'),
                'status': wp.get('_embedded', {}).get('status', {}).get('name'),
                'reason': 'Status marked as blocked'
            })
    
    return blockers


def format_work_package_row(wp: Dict) -> str:
    """Format a single work package as a markdown table row.
    
    Args:
        wp: Work package dictionary
        
    Returns:
        Markdown table row string
    """
    wp_id = wp.get('id', 'N/A')
    subject = wp.get('subject', 'No subject')[:50]  # Truncate long subjects
    
    # Get assignee
    assignee = wp.get('_embedded', {}).get('assignee', {})
    assignee_name = assignee.get('name', 'Unassigned') if assignee else 'Unassigned'
    
    # Get dates
    due_date = wp.get('dueDate', 'N/A')
    updated_at = wp.get('updatedAt', '')
    if updated_at:
        try:
            updated_dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            updated_date = updated_dt.strftime('%Y-%m-%d')
        except:
            updated_date = 'N/A'
    else:
        updated_date = 'N/A'
    
    # Get status and type
    status = wp.get('_embedded', {}).get('status', {}).get('name', 'Unknown')
    wp_type = wp.get('_embedded', {}).get('type', {}).get('name', 'Task')
    
    return f"| [{wp_type} #{wp_id}] | {subject} | {assignee_name} | {due_date or updated_date} | {status} |"


def format_weekly_report_markdown(
    project: Dict,
    work_packages: List[Dict],
    time_entries: List[Dict],
    members: List[Dict],
    from_date: str,
    to_date: str,
    sprint_goal: Optional[str] = None,
    team_name: Optional[str] = None,
    relations: List[Dict] = None
) -> str:
    """Format complete weekly report in markdown.
    
    Args:
        project: Project dictionary
        work_packages: List of work package dictionaries
        time_entries: List of time entry dictionaries
        members: List of project member dictionaries
        from_date: Report start date (YYYY-MM-DD)
        to_date: Report end date (YYYY-MM-DD)
        sprint_goal: Optional sprint goal text
        team_name: Optional team/squad name
        relations: Optional list of work package relations
        
    Returns:
        Formatted markdown report
    """
    # Calculate metrics
    metrics = calculate_metrics(work_packages, time_entries)
    grouped_wps = group_by_status(work_packages)
    blockers = detect_blockers(work_packages, relations)
    
    # Build report
    report = []
    
    # Header
    report.append("# WEEKLY REPORT - AGILE SCRUM\n")
    report.append(f"*Automatically generated from OpenProject*\n")
    
    # A. GENERAL INFORMATION
    report.append("## A. GENERAL INFORMATION\n")
    report.append("| Report Week | Value |")
    report.append("|-------------|-------|")
    report.append(f"| From Date - To Date | {from_date} - {to_date} |")
    report.append(f"| Team/Squad | {team_name or 'N/A'} |")
    report.append(f"| Product/Module | {project.get('name', 'N/A')} |")
    report.append(f"| Project ID | #{project.get('id', 'N/A')} |")
    report.append(f"| Sprint Goal | {sprint_goal or 'N/A'} |")
    report.append("")
    
    # B. EXECUTIVE SUMMARY
    report.append("## B. EXECUTIVE SUMMARY\n")
    
    # Status indicator
    if metrics['blocked_count'] > 0:
        status = "🔴 Off track"
    elif metrics['done_count'] < metrics['in_progress_count']:
        status = "🟡 At risk"
    else:
        status = "🟢 On track"
    
    report.append(f"**Progress vs Sprint Goal:** {status}\n")
    
    # Top deliverables
    report.append("**Key Deliverables (Done):**")
    done_wps = grouped_wps['done'][:3]
    if done_wps:
        for i, wp in enumerate(done_wps, 1):
            report.append(f"{i}. #{wp.get('id')} - {wp.get('subject', 'N/A')}")
    else:
        report.append("- No work packages completed yet")
    report.append("")
    
    # Blockers summary
    if blockers:
        report.append(f"**Main Impediment:** {len(blockers)} work package(s) currently blocked\n")
    else:
        report.append("**Main Impediment:** None\n")
    
    report.append("**Support Needed/Decisions:** _(Requires manual update)_\n")
    
    # C. DELIVERY & BACKLOG MOVEMENT
    report.append("## C. DELIVERY & BACKLOG MOVEMENT\n")
    
    # Done
    report.append("### 1) Completed Work (Done)\n")
    if grouped_wps['done']:
        report.append("| Ticket/Story | Short Description | Owner | Done Date | Status |")
        report.append("|--------------|-------------------|-------|-----------|--------|")
        for wp in grouped_wps['done']:
            report.append(format_work_package_row(wp))
    else:
        report.append("_No work packages completed this week._")
    report.append("")
    
    # In Progress
    report.append("### 2) Work In Progress\n")
    if grouped_wps['in_progress']:
        report.append("| Ticket/Story | Short Description | Owner | ETA | Status |")
        report.append("|--------------|-------------------|-------|-----|--------|")
        for wp in grouped_wps['in_progress']:
            report.append(format_work_package_row(wp))
    else:
        report.append("_No work packages in progress._")
    report.append("")
    
    # Planned/Not Started
    report.append("### 3) Planned Work (Not Started)\n")
    if grouped_wps['planned']:
        report.append("| Ticket/Story | Short Description | Owner | ETA | Status |")
        report.append("|--------------|-------------------|-------|-----|--------|")
        for wp in grouped_wps['planned']:
            report.append(format_work_package_row(wp))
    else:
        report.append("_No planned work packages._")
    report.append("")
    
    # De-scoped
    if grouped_wps['de_scoped']:
        report.append("### 4) De-scoped Work (Stopped/Reprioritized)\n")
        report.append("| Ticket | Reason | Status |")
        report.append("|--------|--------|--------|")
        for wp in grouped_wps['de_scoped']:
            wp_id = wp.get('id', 'N/A')
            subject = wp.get('subject', 'No subject')[:40]
            status = wp.get('_embedded', {}).get('status', {}).get('name', 'Unknown')
            report.append(f"| #{wp_id} {subject} | _(Requires update)_ | {status} |")
        report.append("")
    
    # D. RESOURCES & CAPACITY
    report.append("## D. RESOURCES & EXECUTION CAPACITY\n")
    report.append(f"**Team Size:** {len(members)} member(s)\n")
    report.append(f"**Weekly Capacity:** {metrics['total_hours']:.1f} person-hours\n")
    report.append(f"**Staff Changes:** _(Requires manual update)_\n")
    
    # Time distribution
    if metrics['total_hours'] > 0:
        report.append("**Time Distribution by Activity Type:**\n")
        report.append("| Type | Hours | % |")
        report.append("|------|-------|---|")
        report.append(f"| Development | {metrics['dev_hours']:.1f} | {metrics['dev_hours']/metrics['total_hours']*100:.1f}% |")
        report.append(f"| QA/Testing | {metrics['qa_hours']:.1f} | {metrics['qa_hours']/metrics['total_hours']*100:.1f}% |")
        report.append(f"| Management | {metrics['management_hours']:.1f} | {metrics['management_hours']/metrics['total_hours']*100:.1f}% |")
        report.append("")
    
    # E. IMPEDIMENTS & DEPENDENCIES
    report.append("## E. IMPEDIMENTS & DEPENDENCIES\n")
    
    if blockers:
        report.append("### Impediments (Direct Blockers)\n")
        report.append("| Description | Severity | Owner Handling | Status |")
        report.append("|------------|----------|----------------|--------|")
        for blocker in blockers:
            report.append(f"| #{blocker['id']} {blocker['subject'][:40]} | High | {blocker['assignee']} | {blocker['status']} |")
        report.append("")
    else:
        report.append("_No impediments._\n")
    
    # F. QUALITY & STABILITY
    report.append("## F. QUALITY & SYSTEM STABILITY\n")
    report.append(f"**Bugs Created This Week:** {metrics['bug_count']}\n")
    report.append("**Bugs Closed This Week:** _(Requires further analysis)_\n")
    report.append("**Test Coverage:** _(Requires manual update)_\n")
    report.append("**Incident/Outage:** _(Requires manual update)_\n")
    
    # G. NEXT WEEK PLAN
    report.append("## G. NEXT WEEK PLAN\n")
    report.append("**Top Priorities:**")
    
    # Show planned work as next week priorities
    next_week_wps = grouped_wps['planned'][:5]
    if next_week_wps:
        for i, wp in enumerate(next_week_wps, 1):
            assignee = wp.get('_embedded', {}).get('assignee', {}).get('name', 'Unassigned')
            due_date = wp.get('dueDate', 'TBD')
            report.append(f"{i}. #{wp.get('id')} {wp.get('subject', 'N/A')} ({assignee} - ETA: {due_date})")
    else:
        report.append("_(Planning required)_")
    report.append("")
    
    # H. SPRINT HEALTH & IMPROVEMENTS
    report.append("## H. SPRINT HEALTH & IMPROVEMENTS\n")
    report.append("**What Went Well:** _(Requires update from retro)_\n")
    report.append("**What Needs Improvement:** _(Requires update from retro)_\n")
    report.append("**Action Items:** _(Requires update from retro)_\n")
    
    # APPENDIX: EXECUTIVE SUMMARY
    report.append("---\n")
    report.append("## APPENDIX: EXECUTIVE SUMMARY FOR LEADERSHIP\n")
    report.append(f"**Status:** {status}")
    report.append(f"**Done:** {metrics['done_count']} work packages")
    report.append(f"**In progress:** {metrics['in_progress_count']} work packages")
    report.append(f"**Planned:** {metrics['planned_count']} work packages")
    report.append(f"**Main blockers:** {len(blockers)} blocked items")
    report.append(f"**Hours logged:** {metrics['total_hours']:.1f}h")
    
    return "\n".join(report)


def format_report_data_json(
    project: Dict,
    work_packages: List[Dict],
    time_entries: List[Dict],
    members: List[Dict],
    relations: List[Dict] = None
) -> Dict[str, Any]:
    """Format report data as structured JSON for custom processing.
    
    Args:
        project: Project dictionary
        work_packages: List of work package dictionaries
        time_entries: List of time entry dictionaries
        members: List of project member dictionaries
        relations: Optional list of work package relations
        
    Returns:
        Structured dictionary with all report data
    """
    metrics = calculate_metrics(work_packages, time_entries)
    grouped_wps = group_by_status(work_packages)
    blockers = detect_blockers(work_packages, relations)
    
    return {
        'project': {
            'id': project.get('id'),
            'name': project.get('name'),
            'description': project.get('description', {}).get('raw', ''),
        },
        'metrics': metrics,
        'work_packages': {
            'done': grouped_wps['done'],
            'in_progress': grouped_wps['in_progress'],
            'planned': grouped_wps['planned'],
            'blocked': grouped_wps['blocked'],
            'de_scoped': grouped_wps['de_scoped'],
        },
        'time_entries': time_entries,
        'members': members,
        'blockers': blockers,
        'relations': relations or []
    }
