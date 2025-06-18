"""
GitHub Projects implementation of KanbanInterface

Uses GitHub MCP Server to manage tasks
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from src.integrations.kanban_interface import KanbanInterface, KanbanProvider
from src.core.models import Task, TaskStatus, Priority


class GitHubKanban(KanbanInterface):
    """GitHub Projects kanban board implementation using MCP Server"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize GitHub MCP connection
        
        Args:
            config: Dictionary containing:
                - mcp_function_caller: Function to call MCP tools
                - owner: Repository owner (user or org)
                - repo: Repository name
                - project_number: Project number (for v2 projects)
        """
        super().__init__(config)
        self.provider = KanbanProvider.GITHUB
        self.mcp_caller = config.get('mcp_function_caller')
        self.owner = config.get('owner')
        self.repo = config.get('repo')
        self.project_number = config.get('project_number')
        
        if not self.mcp_caller:
            raise ValueError("mcp_function_caller is required for GitHub MCP integration")
        
    async def connect(self) -> bool:
        """Connect to GitHub MCP Server"""
        try:
            # Test connection by getting authenticated user
            result = await self.mcp_caller('github.get_me', {})
            return 'user' in result
        except Exception as e:
            print(f"Failed to connect to GitHub MCP: {e}")
            return False
            
    async def disconnect(self):
        """Disconnect from GitHub MCP"""
        # No persistent connection to close for MCP
        pass
        
    async def get_available_tasks(self) -> List[Task]:
        """Get unassigned tasks from backlog"""
        # Search for unassigned issues in the repository
        query = f"repo:{self.owner}/{self.repo} is:issue is:open no:assignee"
        
        result = await self.mcp_caller('github.search_issues', {
            "query": query,
            "sort": "created",
            "order": "desc",
            "perPage": 100
        })
        
        tasks = []
        if result.get('items'):
            for issue in result['items']:
                tasks.append(self._github_issue_to_task(issue))
                
        return tasks
        
    def _github_issue_to_task(self, issue: Dict[str, Any]) -> Task:
        """Convert GitHub issue to Task model"""
        # Extract labels
        labels = []
        if issue.get('labels'):
            if isinstance(issue['labels'], list):
                labels = [label.get('name', '') if isinstance(label, dict) else str(label) 
                         for label in issue['labels']]
        
        # Determine priority from labels
        priority = Priority.MEDIUM
        for label in labels:
            label_lower = label.lower()
            if "urgent" in label_lower or "critical" in label_lower:
                priority = Priority.URGENT
                break
            elif "high" in label_lower or "priority/high" in label_lower:
                priority = Priority.HIGH
                break
            elif "low" in label_lower or "priority/low" in label_lower:
                priority = Priority.LOW
                break
                
        # Determine status
        status = TaskStatus.BACKLOG
        state = issue.get('state', 'open')
        if state == 'closed':
            status = TaskStatus.DONE
        else:
            # Check labels for status
            for label in labels:
                label_lower = label.lower()
                if "in progress" in label_lower or "in-progress" in label_lower:
                    status = TaskStatus.IN_PROGRESS
                    break
                elif "blocked" in label_lower:
                    status = TaskStatus.BLOCKED
                    break
                elif "ready" in label_lower:
                    status = TaskStatus.READY
                    break
                    
        # Parse dates
        created_at = issue.get('created_at', '')
        updated_at = issue.get('updated_at', '')
        
        if created_at:
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        else:
            created_at = datetime.now()
            
        if updated_at:
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        else:
            updated_at = datetime.now()
                
        # Extract assignee
        assignee = None
        if issue.get('assignee'):
            assignee = issue['assignee'].get('login')
        elif issue.get('assignees') and len(issue['assignees']) > 0:
            assignee = issue['assignees'][0].get('login')
                
        return Task(
            id=str(issue.get('number', issue.get('id', ''))),
            name=issue.get('title', 'Untitled'),
            description=issue.get('body', ''),
            status=status,
            priority=priority,
            labels=labels,
            estimated_hours=8,  # Default, could parse from body
            assigned_to=assignee,
            dependencies=[],
            created_at=created_at,
            updated_at=updated_at
        )
        
    async def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get specific task by ID"""
        try:
            # task_id should be the issue number
            result = await self.mcp_caller('github.get_issue', {
                "owner": self.owner,
                "repo": self.repo,
                "issue_number": int(task_id)
            })
            
            if result.get('issue'):
                return self._github_issue_to_task(result['issue'])
            return None
        except:
            return None
        
    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """Create new issue in repository"""
        # Map priority to labels
        priority_labels = {
            Priority.URGENT: "priority/urgent",
            Priority.HIGH: "priority/high",
            Priority.MEDIUM: "priority/medium",
            Priority.LOW: "priority/low"
        }
        
        labels = task_data.get("labels", [])
        priority = task_data.get("priority", Priority.MEDIUM)
        if priority in priority_labels:
            labels.append(priority_labels[priority])
            
        result = await self.mcp_caller('github.create_issue', {
            "owner": self.owner,
            "repo": self.repo,
            "title": task_data.get("name", "Untitled Task"),
            "body": task_data.get("description", ""),
            "labels": labels
        })
        
        if not result.get('issue'):
            raise Exception(f"Failed to create issue: {result.get('error', 'Unknown error')}")
            
        return self._github_issue_to_task(result['issue'])
        
        
    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> Task:
        """Update existing issue"""
        update_data = {
            "owner": self.owner,
            "repo": self.repo,
            "issue_number": int(task_id)
        }
        
        if "name" in updates:
            update_data["title"] = updates["name"]
        if "description" in updates:
            update_data["body"] = updates["description"]
        if "status" in updates:
            update_data["state"] = "closed" if updates["status"] == TaskStatus.DONE else "open"
            
        result = await self.mcp_caller('github.update_issue', update_data)
        
        if not result.get('issue'):
            raise Exception(f"Failed to update issue: {result.get('error', 'Unknown error')}")
            
        return self._github_issue_to_task(result['issue'])
        
    async def assign_task(self, task_id: str, assignee_id: str) -> bool:
        """Assign issue to user"""
        result = await self.mcp_caller('github.update_issue', {
            "owner": self.owner,
            "repo": self.repo,
            "issue_number": int(task_id),
            "assignees": [assignee_id]
        })
        
        return result.get('success', False)
        
    async def move_task_to_column(self, task_id: str, column_name: str) -> bool:
        """Move task to specific status column"""
        # Map column names to GitHub states/labels
        column_lower = column_name.lower()
        
        # Update issue state if moving to done
        if column_lower in ["done", "completed", "closed"]:
            await self.mcp_caller('github.update_issue', {
                "owner": self.owner,
                "repo": self.repo,
                "issue_number": int(task_id),
                "state": "closed"
            })
        elif column_lower in ["in progress", "in-progress"]:
            # Add in-progress label
            await self.mcp_caller('github.update_issue', {
                "owner": self.owner,
                "repo": self.repo,
                "issue_number": int(task_id),
                "labels": ["in-progress"]
            })
        elif column_lower == "blocked":
            # Add blocked label
            await self.mcp_caller('github.update_issue', {
                "owner": self.owner,
                "repo": self.repo,
                "issue_number": int(task_id),
                "labels": ["blocked"]
            })
            
        return True
        
    async def add_comment(self, task_id: str, comment: str) -> bool:
        """Add comment to issue"""
        result = await self.mcp_caller('github.add_issue_comment', {
            "owner": self.owner,
            "repo": self.repo,
            "issue_number": int(task_id),
            "body": comment
        })
        
        return result.get('success', False)
        
    async def get_project_metrics(self) -> Dict[str, Any]:
        """Get project metrics"""
        metrics = {
            "total_tasks": 0,
            "backlog_tasks": 0,
            "in_progress_tasks": 0,
            "completed_tasks": 0,
            "blocked_tasks": 0
        }
        
        # Get open issues
        open_result = await self.mcp_caller('github.list_issues', {
            "owner": self.owner,
            "repo": self.repo,
            "state": "open",
            "perPage": 100
        })
        
        # Get closed issues
        closed_result = await self.mcp_caller('github.list_issues', {
            "owner": self.owner,
            "repo": self.repo,
            "state": "closed",
            "perPage": 100
        })
        
        # Count open issues by labels
        if open_result.get('issues'):
            for issue in open_result['issues']:
                labels = [label.get('name', '').lower() for label in issue.get('labels', [])]
                
                if 'blocked' in labels:
                    metrics["blocked_tasks"] += 1
                elif 'in-progress' in labels or 'in progress' in labels:
                    metrics["in_progress_tasks"] += 1
                else:
                    metrics["backlog_tasks"] += 1
                    
        # Count closed issues
        if closed_result.get('issues'):
            metrics["completed_tasks"] = len(closed_result['issues'])
            
        metrics["total_tasks"] = metrics["backlog_tasks"] + metrics["in_progress_tasks"] + \
                                metrics["completed_tasks"] + metrics["blocked_tasks"]
                                
        return metrics
        
    async def report_blocker(self, task_id: str, blocker_description: str, severity: str = "medium") -> bool:
        """Report blocker on task"""
        # Add blocker comment
        comment = f"🚫 **BLOCKER** ({severity.upper()}): {blocker_description}"
        await self.add_comment(task_id, comment)
        
        # Add blocker label
        rest_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/issues/{task_id}/labels"
        
        await self.client.post(
            rest_url,
            json={"labels": [f"blocked/{severity}"]},
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        
        # Try to move to blocked column
        await self.move_task_to_column(task_id, "Blocked")
        
        return True
        
    async def update_task_progress(self, task_id: str, progress_data: Dict[str, Any]) -> bool:
        """Update task progress"""
        progress = progress_data.get("progress", 0)
        status = progress_data.get("status", "")
        message = progress_data.get("message", "")
        
        # Add progress comment
        comment = f"📊 **Progress Update**: {progress}%"
        if message:
            comment += f"\n\n{message}"
            
        await self.add_comment(task_id, comment)
        
        # Update column based on progress
        if progress >= 100:
            await self.move_task_to_column(task_id, "Done")
        elif progress > 0 and status == "in_progress":
            await self.move_task_to_column(task_id, "In Progress")
            
        return True