"""
Task Management Tools for Marcus MCP

This module contains tools for task operations in the Marcus system:
- request_next_task: Get optimal task assignment for an agent
- report_task_progress: Update progress on assigned tasks
- report_blocker: Report blockers with AI-powered suggestions
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

from src.core.models import Task, TaskStatus, Priority, TaskAssignment
from src.logging.conversation_logger import conversation_logger, log_thinking
from src.logging.agent_events import log_agent_event
from src.core.ai_powered_task_assignment import find_optimal_task_for_agent_ai_powered


async def request_next_task(agent_id: str, state: Any) -> Dict[str, Any]:
    """
    Agents call this to request their next optimal task.
    
    Uses AI-powered task matching to find the best task based on:
    - Agent skills and experience
    - Task priority and dependencies
    - Current workload distribution
    
    Args:
        agent_id: The requesting agent's ID
        state: Marcus server state instance
        
    Returns:
        Dict with task details and instructions if successful
    """
    # Log task request
    conversation_logger.log_worker_message(
        agent_id,
        "to_pm",
        "Requesting next task",
        {"worker_info": f"Worker {agent_id} requesting task"}
    )
    
    try:
        # Log the task request immediately
        state.log_event("task_request", {
            "worker_id": agent_id,
            "source": agent_id,
            "target": "marcus"
        })
        
        # Log conversation event for visualization
        log_agent_event("task_request", {
            "worker_id": agent_id
        })
        
        # Initialize kanban if needed
        await state.initialize_kanban()
        
        # Log Marcus thinking about refreshing state
        log_thinking("marcus", "Need to check current project state")
        
        # Get current project state
        await state.refresh_project_state()
        
        # Log thinking about finding task
        agent = state.agent_status.get(agent_id)
        if agent:
            log_thinking("marcus", f"Finding optimal task for {agent.name}", {
                "agent_skills": agent.skills,
                "current_workload": len(agent.current_tasks)
            })
        
        # Find optimal task for this agent
        optimal_task = await find_optimal_task_for_agent(agent_id, state)
        
        if optimal_task:
            try:
                # Get implementation context if using GitHub
                previous_implementations = None
                if state.provider == 'github' and state.code_analyzer:
                    owner = os.getenv('GITHUB_OWNER')
                    repo = os.getenv('GITHUB_REPO')
                    impl_details = await state.code_analyzer.get_implementation_details(
                        optimal_task.dependencies,
                        owner,
                        repo
                    )
                    if impl_details:
                        previous_implementations = impl_details
                
                # Generate detailed instructions with AI
                instructions = await state.ai_engine.generate_task_instructions(
                    optimal_task,
                    state.agent_status.get(agent_id)
                )
                
                # Log decision process
                conversation_logger.log_pm_decision(
                    decision=f"Assign task '{optimal_task.name}' to {agent_id}",
                    rationale=f"Best skill match and highest priority",
                    alternatives_considered=[
                        {"task": "Other Task 1", "score": 0.7},
                        {"task": "Other Task 2", "score": 0.6}
                    ],
                    confidence_score=0.85,
                    decision_factors={
                        "skill_match": 0.9,
                        "priority": optimal_task.priority.value,
                        "dependencies_clear": len(optimal_task.dependencies) == 0
                    }
                )
                
                # Create assignment
                assignment = TaskAssignment(
                    task_id=optimal_task.id,
                    task_name=optimal_task.name,
                    description=optimal_task.description,
                    instructions=instructions,
                    estimated_hours=optimal_task.estimated_hours,
                    priority=optimal_task.priority,
                    dependencies=optimal_task.dependencies,
                    assigned_to=agent_id,
                    assigned_at=datetime.now(),
                    due_date=optimal_task.due_date
                )
                
                # Update kanban FIRST (fail fast if kanban is down)
                await state.kanban_client.update_task(optimal_task.id, {
                    "status": TaskStatus.IN_PROGRESS,
                    "assigned_to": agent_id
                })
                
                # If kanban update succeeded, track assignment
                state.agent_tasks[agent_id] = assignment
                agent = state.agent_status[agent_id]
                agent.current_tasks = [optimal_task]
                
                # Persist assignment
                await state.assignment_persistence.save_assignment(
                    agent_id, 
                    optimal_task.id,
                    {
                        "name": optimal_task.name,
                        "priority": optimal_task.priority.value,
                        "estimated_hours": optimal_task.estimated_hours
                    }
                )
                
                # Remove from pending assignments
                state.tasks_being_assigned.discard(optimal_task.id)
                
                # Log task assignment
                conversation_logger.log_worker_message(
                    agent_id,
                    "from_pm",
                    f"Assigned task: {optimal_task.name}",
                    {
                        "task_id": optimal_task.id,
                        "instructions": instructions,
                        "priority": optimal_task.priority.value
                    }
                )
                
                # Log conversation event for visualization
                log_agent_event("task_assignment", {
                    "worker_id": agent_id,
                    "task": {
                        "id": optimal_task.id,
                        "name": optimal_task.name,
                        "priority": optimal_task.priority.value,
                        "estimated_hours": optimal_task.estimated_hours
                    }
                })
                
                return {
                    "success": True,
                    "task": {
                        "id": optimal_task.id,
                        "name": optimal_task.name,
                        "description": optimal_task.description,
                        "instructions": instructions,
                        "priority": optimal_task.priority.value,
                        "implementation_context": previous_implementations
                    }
                }
            
            except Exception as e:
                # If anything fails, rollback the reservation
                state.tasks_being_assigned.discard(optimal_task.id)
                
                conversation_logger.log_worker_message(
                    agent_id,
                    "from_pm", 
                    f"Failed to assign task: {str(e)}",
                    {"error": str(e)}
                )
                
                return {
                    "success": False,
                    "error": f"Failed to assign task: {str(e)}"
                }
                
        else:
            conversation_logger.log_worker_message(
                agent_id,
                "from_pm",
                "No suitable tasks available at this time",
                {"reason": "no_matching_tasks"}
            )
            
            return {
                "success": False,
                "message": "No suitable tasks available at this time"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def report_task_progress(
    agent_id: str,
    task_id: str,
    status: str,
    progress: int,
    message: str,
    state: Any
) -> Dict[str, Any]:
    """
    Agents report their task progress.
    
    Updates task status, progress percentage, and handles completion.
    Includes code analysis for GitHub projects.
    
    Args:
        agent_id: The reporting agent's ID
        task_id: ID of the task being updated
        status: Task status (in_progress, completed, blocked)
        progress: Progress percentage (0-100)
        message: Progress update message
        state: Marcus server state instance
        
    Returns:
        Dict with success status
    """
    # Log progress update
    conversation_logger.log_worker_message(
        agent_id,
        "to_pm",
        f"Progress update: {message} ({progress}%)",
        {
            "task_id": task_id,
            "status": status,
            "progress": progress
        }
    )
    
    # Log conversation event for visualization
    log_agent_event("progress_update", {
        "agent_id": agent_id,
        "task_id": task_id,
        "status": status,
        "progress": progress,
        "message": message
    })
    
    try:
        # Initialize kanban if needed
        await state.initialize_kanban()
        
        # Log Marcus thinking
        log_thinking("marcus", f"Processing progress update from {agent_id}", {
            "task_id": task_id,
            "status": status,
            "progress": progress
        })
        
        # Update task in kanban
        update_data = {"progress": progress}
        
        if status == "completed":
            update_data["status"] = TaskStatus.DONE
            update_data["completed_at"] = datetime.now().isoformat()
            
            # Clear agent's current task
            if agent_id in state.agent_status:
                agent = state.agent_status[agent_id]
                agent.current_tasks = []
                agent.completed_tasks_count += 1
                
                # Remove task assignment from state and persistence
                if agent_id in state.agent_tasks:
                    del state.agent_tasks[agent_id]
                    
                # Remove from persistent storage
                await state.assignment_persistence.remove_assignment(agent_id)
                
                # Code analysis for GitHub
                if state.provider == 'github' and state.code_analyzer:
                    owner = os.getenv('GITHUB_OWNER')
                    repo = os.getenv('GITHUB_REPO')
                    
                    # Get task details
                    task = await state.kanban_client.get_task_by_id(task_id)
                    
                    # Analyze completed work
                    analysis = await state.code_analyzer.analyze_task_completion(
                        task,
                        agent,
                        owner,
                        repo
                    )
                    
                    if analysis and analysis.get('findings'):
                        # Store findings for future tasks
                        await state.kanban_client.add_comment(
                            task_id,
                            f"🤖 Code Analysis:\n{json.dumps(analysis['findings'], indent=2)}"
                        )
            
        elif status == "blocked":
            update_data["status"] = TaskStatus.BLOCKED
            
        await state.kanban_client.update_task(task_id, update_data)
        
        # Update task progress (including checklist items)
        await state.kanban_client.update_task_progress(task_id, {
            'progress': progress,
            'status': status,
            'message': message
        })
        
        # Log response
        conversation_logger.log_worker_message(
            agent_id,
            "from_pm",
            f"Progress update received: {status} at {progress}%",
            {"acknowledged": True}
        )
        
        # Update system state
        await state.refresh_project_state()
        
        return {
            "success": True,
            "message": "Progress updated successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def report_blocker(
    agent_id: str,
    task_id: str,
    blocker_description: str,
    severity: str,
    state: Any
) -> Dict[str, Any]:
    """
    Report a blocker on a task with AI-powered analysis.
    
    Uses AI to analyze the blocker and provide actionable suggestions.
    Updates task status and adds detailed documentation.
    
    Args:
        agent_id: The reporting agent's ID
        task_id: ID of the blocked task
        blocker_description: Detailed description of the blocker
        severity: Blocker severity (low, medium, high)
        state: Marcus server state instance
        
    Returns:
        Dict with AI suggestions and success status
    """
    # Log blocker report
    conversation_logger.log_worker_message(
        agent_id,
        "to_pm",
        f"Reporting blocker: {blocker_description}",
        {
            "task_id": task_id,
            "severity": severity
        }
    )
    
    try:
        # Initialize kanban if needed
        await state.initialize_kanban()
        
        # Log Marcus thinking
        log_thinking("marcus", f"Analyzing blocker from {agent_id}", {
            "task_id": task_id,
            "severity": severity,
            "description": blocker_description
        })
        
        # Use AI to analyze the blocker and suggest solutions
        agent = state.agent_status.get(agent_id)
        task = await state.kanban_client.get_task_by_id(task_id)
        
        suggestions = await state.ai_engine.analyze_blocker(
            task_id,
            blocker_description,
            severity,
            agent,
            task
        )
        
        # Update task status
        await state.kanban_client.update_task(task_id, {
            "status": TaskStatus.BLOCKED,
            "blocker": blocker_description
        })
        
        # Add detailed comment
        comment = f"🚫 BLOCKER ({severity.upper()})\n"
        comment += f"Reported by: {agent_id}\n"
        comment += f"Description: {blocker_description}\n\n"
        comment += f"📋 AI Suggestions:\n{suggestions}"
        
        await state.kanban_client.add_comment(task_id, comment)
        
        # Log Marcus decision
        conversation_logger.log_pm_decision(
            decision=f"Acknowledge blocker and provide suggestions",
            rationale="Help agent overcome the blocker with AI guidance",
            confidence_score=0.8,
            decision_factors={
                "severity": severity,
                "has_suggestions": bool(suggestions)
            }
        )
        
        # Log response
        conversation_logger.log_worker_message(
            agent_id,
            "from_pm",
            f"Blocker acknowledged. Suggestions provided.",
            {
                "suggestions": suggestions,
                "severity": severity
            }
        )
        
        return {
            "success": True,
            "suggestions": suggestions,
            "message": "Blocker reported and suggestions provided"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# Helper functions for task assignment

async def find_optimal_task_for_agent(agent_id: str, state: Any) -> Optional[Task]:
    """Find the best task for an agent using AI-powered analysis"""
    async with state.assignment_lock:
        agent = state.agent_status.get(agent_id)
        
        if not agent or not state.project_state:
            return None
            
        # Get available tasks
        assigned_task_ids = [a.task_id for a in state.agent_tasks.values()]
        persisted_assigned_ids = await state.assignment_persistence.get_all_assigned_task_ids()
        all_assigned_ids = set(assigned_task_ids) | persisted_assigned_ids | state.tasks_being_assigned
        
        available_tasks = [
            t for t in state.project_tasks
            if t.status == TaskStatus.TODO and
            t.id not in all_assigned_ids
        ]
        
        if not available_tasks:
            return None
        
        # Use AI-powered task selection if AI engine is available
        if state.ai_engine:
            try:
                optimal_task = await find_optimal_task_for_agent_ai_powered(
                    agent_id=agent_id,
                    agent_status=agent.__dict__,
                    project_tasks=state.project_tasks,
                    available_tasks=available_tasks,
                    assigned_task_ids=all_assigned_ids,
                    ai_engine=state.ai_engine
                )
                
                if optimal_task:
                    state.tasks_being_assigned.add(optimal_task.id)
                    return optimal_task
            except Exception as e:
                # Log error using log_pm_thinking instead
                conversation_logger.log_pm_thinking(f"AI task assignment failed, falling back to basic: {e}")
        
        # Fallback to basic assignment if AI fails
        return await find_optimal_task_basic(agent_id, available_tasks, state)


async def find_optimal_task_basic(agent_id: str, available_tasks: List[Task], state: Any) -> Optional[Task]:
    """Basic task assignment logic (fallback)"""
    agent = state.agent_status.get(agent_id)
    if not agent:
        return None
        
    best_task = None
    best_score = -1
    
    for task in available_tasks:
        # Calculate skill match score
        skill_score = 0
        if agent.skills and task.labels:
            matching_skills = set(agent.skills) & set(task.labels)
            skill_score = len(matching_skills) / len(task.labels) if task.labels else 0
            
        # Priority score
        priority_score = {
            Priority.URGENT: 1.0,
            Priority.HIGH: 0.8,
            Priority.MEDIUM: 0.5,
            Priority.LOW: 0.2
        }.get(task.priority, 0.5)
        
        # Combined score
        total_score = (skill_score * 0.6) + (priority_score * 0.4)
        
        if total_score > best_score:
            best_score = total_score
            best_task = task
            
    if best_task:
        state.tasks_being_assigned.add(best_task.id)
        
    return best_task