#!/usr/bin/env python3
"""
Create Todo App tasks in Planka for testing PM Agent
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.integrations.mcp_kanban_client_refactored import MCPKanbanClient

# Task definitions for the Todo App project
TASKS = [
    # Phase 1: Project Setup
    {
        "name": "BACKEND-001: Initialize Python project with FastAPI",
        "description": """Create the initial Python project structure for our Todo API:

1. Create project directory structure:
   - src/
   - src/api/
   - src/models/
   - src/services/
   - tests/

2. Create requirements.txt with:
   - fastapi
   - uvicorn
   - sqlalchemy
   - pytest
   - httpx (for testing)

3. Create main.py with basic FastAPI app
4. Add .gitignore for Python
5. Create README.md with setup instructions""",
        "labels": ["backend", "python", "setup"],
        "priority": "high",
        "estimated_hours": 2
    },
    {
        "name": "FRONTEND-001: Initialize React project",
        "description": """Create React application with TypeScript:

1. Use create-react-app with TypeScript template
2. Set up folder structure:
   - src/components/
   - src/services/
   - src/types/
   - src/styles/

3. Install additional dependencies:
   - axios for API calls
   - react-query for data fetching
   - styled-components or tailwind for styling

4. Configure TypeScript properly
5. Set up basic App component""",
        "labels": ["frontend", "react", "setup"],
        "priority": "high",
        "estimated_hours": 2
    },
    {
        "name": "DEVOPS-001: Create Docker compose setup",
        "description": """Create Docker configuration for development:

1. Create Dockerfile for backend API
2. Create Dockerfile for frontend (nginx to serve build)
3. Create docker-compose.yml with:
   - backend service (port 8000)
   - frontend service (port 3000)
   - volume mounts for development

4. Add docker-compose.dev.yml for development
5. Create .env.example file""",
        "labels": ["devops", "docker", "setup"],
        "priority": "high",
        "estimated_hours": 3
    },
    
    # Phase 2: Core API
    {
        "name": "BACKEND-002: Create Todo model and database schema",
        "description": """Implement database model for todos:

1. Create SQLAlchemy model:
   - id (UUID primary key)
   - title (string, required)
   - description (text, optional)
   - completed (boolean, default false)
   - created_at (timestamp)
   - updated_at (timestamp)

2. Create database initialization script
3. Set up Alembic for migrations
4. Create initial migration""",
        "labels": ["backend", "database", "python"],
        "priority": "high",
        "dependencies": ["BACKEND-001"],
        "estimated_hours": 3
    },
    {
        "name": "BACKEND-003: Implement CRUD endpoints",
        "description": """Create REST API endpoints:

1. POST /api/todos - Create new todo
2. GET /api/todos - List all todos (with pagination)
3. GET /api/todos/{id} - Get single todo
4. PUT /api/todos/{id} - Update todo
5. DELETE /api/todos/{id} - Delete todo

Include:
- Proper error handling
- Input validation with Pydantic
- Status codes
- Response models""",
        "labels": ["backend", "api", "python"],
        "priority": "high",
        "dependencies": ["BACKEND-002"],
        "estimated_hours": 4
    },
]


def get_label_color(label: str) -> str:
    """Get color for label based on type"""
    color_map = {
        "backend": "#4CAF50",      # Green
        "frontend": "#2196F3",     # Blue  
        "testing": "#FF9800",      # Orange
        "devops": "#9C27B0",       # Purple
        "setup": "#F44336",        # Red
        "api": "#00BCD4",          # Cyan
        "database": "#795548",     # Brown
        "python": "#3776AB",       # Python blue
        "react": "#61DAFB",        # React blue
        "docker": "#0066CC",       # Docker blue
    }
    return color_map.get(label, "#757575")  # Default gray


async def create_tasks_in_planka():
    """Create all tasks in Planka"""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    config_path = os.path.join(project_root, 'config_pm_agent.json')
    
    client = MCPKanbanClient()
    client.project_id = "1533678301472621705"  # Task Master project
    
    print("🚀 Creating Todo App tasks in Planka...")
    print("📋 Project ID:", client.project_id)
    
    try:
        # First, load config if it exists
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                if config.get("board_id"):
                    client.board_id = config["board_id"]
                    print(f"📋 Using board from config: {client.board_id}")
        except FileNotFoundError:
            print("⚠️  No config file found")
        
        async with client.connect() as conn:
            # If no board_id, the connect method should find it
            print(f"✅ Connected. Board ID: {client.board_id}")
            
            if not client.board_id:
                print("\n❌ No board found in Task Master project!")
                print("Please run one of these commands first:")
                print("  1. python scripts/examples/select_task_master_board.py")
                print("  2. Create a board manually in Planka")
                return
            
            # Get the lists in the board
            print("\n🔍 Getting lists...")
            lists_result = await conn.call_tool("mcp_kanban_list_manager", {
                "action": "get_all",
                "boardId": client.board_id
            })
            lists = json.loads(lists_result.content[0].text)
            
            if not lists:
                print("❌ No lists found in board")
                return
            
            # Find "To Do" list or use first list
            todo_list = None
            for lst in lists:
                if "to do" in lst["name"].lower() or "todo" in lst["name"].lower():
                    todo_list = lst
                    break
            
            if not todo_list:
                todo_list = lists[0]  # Use first list
            
            print(f"📝 Adding tasks to list: {todo_list['name']}")
            print("-" * 50)
            
            # Create tasks
            created_count = 0
            for i, task_data in enumerate(TASKS):
                try:
                    print(f"\n[{i+1}/{len(TASKS)}] Creating: {task_data['name'][:50]}...")
                    
                    # Prepare task for creation
                    task = {
                        "name": task_data["name"],
                        "description": task_data["description"],
                        "listId": todo_list["id"],
                        "position": created_count + 1
                    }
                    
                    # Create the task
                    result = await conn.call_tool("mcp_kanban_card_manager", {
                        "action": "create",
                        **task
                    })
                    
                    card_data = json.loads(result.content[0].text)
                    card_id = card_data["id"]
                    print(f"   ✅ Created card ID: {card_id}")
                    
                    # Add labels
                    if task_data.get("labels"):
                        print(f"   🏷️  Adding {len(task_data['labels'])} labels...")
                        for label in task_data["labels"]:
                            try:
                                await conn.call_tool("mcp_kanban_label_manager", {
                                    "action": "add_label",
                                    "cardId": card_id,
                                    "name": label,
                                    "color": get_label_color(label)
                                })
                            except Exception as e:
                                print(f"      ⚠️  Failed to add label '{label}': {e}")
                    
                    # Add priority as comment
                    if task_data.get("priority"):
                        print("   💬 Adding priority comment...")
                        try:
                            await conn.call_tool("mcp_kanban_comment_manager", {
                                "action": "create_comment",
                                "cardId": card_id,
                                "text": f"Priority: {task_data['priority']}\nEstimated hours: {task_data.get('estimated_hours', 'TBD')}"
                            })
                        except Exception as e:
                            print(f"      ⚠️  Failed to add comment: {e}")
                    
                    created_count += 1
                    
                except Exception as e:
                    print(f"   ❌ Failed to create task: {e}")
                    import traceback
                    traceback.print_exc()
            
            print("\n" + "=" * 50)
            print(f"🎉 Created {created_count}/{len(TASKS)} tasks successfully!")
            
            if created_count > 0:
                print("\n📋 Next steps:")
                print("1. View tasks in Planka: http://localhost:3333")
                print("2. Start PM Agent: python start_pm_agent_task_master.py")
                print("3. Start worker agents to work on these tasks")
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(create_tasks_in_planka())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)