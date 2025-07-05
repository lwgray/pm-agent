#!/usr/bin/env python3
"""
Clear all cards from the Task Master Test board
"""

import asyncio
import json
import os
import sys
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.error_framework import (
    KanbanIntegrationError, 
    ServiceUnavailableError, 
    ErrorContext,
    RemediationSuggestion
)

# Set environment
os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'


async def check_board_availability():
    """Check if the Kanban board service is running"""
    base_url = os.environ.get('PLANKA_BASE_URL', 'http://localhost:3333')
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(base_url, timeout=5.0)
            return True
    except (httpx.ConnectError, httpx.TimeoutException):
        return False
    except Exception:
        return False


async def clear_board():
    """Clear all cards from the Task Master Test board"""
    
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("🧹 Board Cleaner for Task Master Test")
    print("=" * 50)
    
    # Check if board is available first
    print("\n🔍 Checking Kanban board availability...")
    board_available = await check_board_availability()
    
    if not board_available:
        base_url = os.environ.get('PLANKA_BASE_URL', 'http://localhost:3333')
        raise ServiceUnavailableError(
            service_name="Planka Kanban Board",
            context=ErrorContext(
                operation="clear_board",
                integration_name="planka",
                integration_state={"url": base_url, "status": "unreachable"}
            ),
            remediation=RemediationSuggestion(
                immediate_action=f"Start the Planka Kanban board service on {base_url}",
                long_term_solution="Add health checks to verify board is running before operations",
                fallback_strategy="Check if Docker containers are running with 'docker ps'",
                escalation_path="Run 'docker-compose up -d' in the Kanban board directory"
            )
        )
    
    print("✅ Kanban board is available")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Find Task Master Test project
                print("\n📋 Finding Task Master Test project...")
                result = await session.call_tool("mcp_kanban_project_board_manager", {
                    "action": "get_projects",
                    "page": 1,
                    "perPage": 25
                })
                
                # Check if result has content before parsing
                if not result or not result.content or not result.content[0].text:
                    raise KanbanIntegrationError(
                        board_name="Task Master Test",
                        operation="get_projects",
                        context=ErrorContext(
                            operation="clear_board",
                            integration_name="planka_mcp"
                        ),
                        remediation=RemediationSuggestion(
                            immediate_action="Check MCP server logs for errors",
                            long_term_solution="Ensure MCP server is properly configured",
                            fallback_strategy="Restart the MCP server and retry"
                        )
                    )
                
                projects_data = json.loads(result.content[0].text)
                project_id = None
                board_id = None
                
                for project in projects_data["items"]:
                    if project["name"] == "Task Master Test":
                        project_id = project["id"]
                        print(f"✅ Found project: {project['name']} (ID: {project_id})")
                        break
                
                if not project_id:
                    print("❌ Task Master Test project not found!")
                    return
                
                # Find the board
                if "boards" in projects_data.get("included", {}):
                    for board in projects_data["included"]["boards"]:
                        if board["projectId"] == project_id:
                            board_id = board["id"]
                            print(f"✅ Found board: {board['name']} (ID: {board_id})")
                            break
                
                if not board_id:
                    print("❌ No board found for Task Master Test!")
                    return
            
                # Get board summary
                summary_result = await session.call_tool(
                    "mcp_kanban_project_board_manager",
                    {
                        "action": "get_board_summary",
                        "boardId": board_id,
                        "includeTaskDetails": False
                    }
                )
                summary = json.loads(summary_result.content[0].text)
                
                total_cards = 0
                cards_to_delete = []
                
                for lst in summary.get('lists', []):
                    list_cards = lst.get('cards', [])
                    total_cards += len(list_cards)
                    for card in list_cards:
                        cards_to_delete.append({
                            'id': card['id'],
                            'name': card['name'],
                            'list': lst['name']
                        })
                
                if total_cards == 0:
                    print("\n✅ Board is already clean!")
                    return
                
                print(f"\n📊 Found {total_cards} cards to remove:")
                
                # Group by list for better display
                lists_summary = {}
                for card in cards_to_delete:
                    if card['list'] not in lists_summary:
                        lists_summary[card['list']] = 0
                    lists_summary[card['list']] += 1
                
                for list_name, count in lists_summary.items():
                    print(f"   • {list_name}: {count} cards")
                
                # Delete all cards
                print("\n🗑️  Deleting cards...")
                deleted = 0
                
                for card in cards_to_delete:
                    try:
                        await session.call_tool(
                            "mcp_kanban_card_manager",
                            {"action": "delete", "id": card['id']}
                        )
                        deleted += 1
                        print(f"   ❌ Deleted: {card['name']}")
                    except Exception as e:
                        print(f"   ⚠️  Failed to delete: {card['name']} - {str(e)}")
            
                print(f"\n✅ Successfully cleaned {deleted} cards from the board!")
                print("🎯 Board is now empty and ready for new tasks!")
                
    except json.JSONDecodeError as e:
        raise KanbanIntegrationError(
            board_name="Task Master Test",
            operation="parse_response",
            context=ErrorContext(
                operation="clear_board",
                integration_name="planka_mcp",
                custom_context={"error": str(e), "response": str(result.content[0].text if result and result.content else "No content")}
            ),
            remediation=RemediationSuggestion(
                immediate_action="Check if MCP server is returning valid JSON",
                long_term_solution="Add response validation to MCP client",
                fallback_strategy="Enable debug logging to see raw responses"
            ),
            cause=e
        )
    except Exception as e:
        # Re-raise Marcus errors as-is
        if isinstance(e, (ServiceUnavailableError, KanbanIntegrationError)):
            raise
        
        # Wrap other errors
        raise KanbanIntegrationError(
            board_name="Task Master Test",
            operation="clear_board",
            context=ErrorContext(
                operation="clear_board",
                integration_name="planka",
                custom_context={"error": str(e), "error_type": type(e).__name__}
            ),
            remediation=RemediationSuggestion(
                immediate_action="Check logs for detailed error information",
                long_term_solution="Improve error handling and logging",
                fallback_strategy="Try clearing the board manually through the UI"
            ),
            cause=e
        )


async def clear_board_silent():
    """Clear board without prompts (for use by menu)"""
    
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Find Task Master Test project
            result = await session.call_tool("mcp_kanban_project_board_manager", {
                "action": "get_projects",
                "page": 1,
                "perPage": 25
            })
            
            projects_data = json.loads(result.content[0].text)
            project_id = None
            board_id = None
            
            for project in projects_data["items"]:
                if project["name"] == "Task Master Test":
                    project_id = project["id"]
                    break
            
            if not project_id:
                return False, "Task Master Test project not found!"
            
            # Find the board
            if "boards" in projects_data.get("included", {}):
                for board in projects_data["included"]["boards"]:
                    if board["projectId"] == project_id:
                        board_id = board["id"]
                        break
            
            if not board_id:
                return False, "No board found for Task Master Test!"
            
            # Get board summary
            summary_result = await session.call_tool(
                "mcp_kanban_project_board_manager",
                {
                    "action": "get_board_summary",
                    "boardId": board_id,
                    "includeTaskDetails": False
                }
            )
            summary = json.loads(summary_result.content[0].text)
            
            total_cards = 0
            deleted = 0
            
            for lst in summary.get('lists', []):
                for card in lst.get('cards', []):
                    total_cards += 1
                    try:
                        await session.call_tool(
                            "mcp_kanban_card_manager",
                            {"action": "delete", "id": card['id']}
                        )
                        deleted += 1
                    except:
                        pass
            
            return True, f"Deleted {deleted} of {total_cards} cards"


def display_marcus_error(error):
    """Display Marcus error in a user-friendly format"""
    print("\n❌ ERROR DETECTED")
    print("=" * 50)
    print(f"Error: {error.message}")
    print(f"Severity: {error.severity.value}")
    
    if error.remediation:
        print("\n📋 REMEDIATION STEPS:")
        if error.remediation.immediate_action:
            print(f"• Immediate: {error.remediation.immediate_action}")
        if error.remediation.fallback_strategy:
            print(f"• Fallback: {error.remediation.fallback_strategy}")
        if error.remediation.long_term_solution:
            print(f"• Long-term: {error.remediation.long_term_solution}")
        if error.remediation.escalation_path:
            print(f"• Escalation: {error.remediation.escalation_path}")
    
    if error.context and error.context.integration_state:
        print("\n🔍 CONTEXT:")
        for key, value in error.context.integration_state.items():
            print(f"• {key}: {value}")
    
    print("\n" + "=" * 50)


if __name__ == "__main__":
    try:
        asyncio.run(clear_board())
    except (ServiceUnavailableError, KanbanIntegrationError) as e:
        display_marcus_error(e)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)