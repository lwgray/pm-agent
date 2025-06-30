#!/usr/bin/env python3
"""
Marcus MCP Server - Modularized Version

A lean MCP server implementation that delegates all tool logic
to specialized modules for better maintainability.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import atexit

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

from src.core.models import (
    TaskStatus, Priority, RiskLevel,
    ProjectState, WorkerStatus, TaskAssignment
)
from src.integrations.kanban_factory import KanbanFactory
from src.integrations.kanban_interface import KanbanInterface
from src.integrations.ai_analysis_engine_fixed import AIAnalysisEngine
from src.core.code_analyzer import CodeAnalyzer
from src.monitoring.project_monitor import ProjectMonitor
from src.communication.communication_hub import CommunicationHub
from src.config.settings import Settings
from src.logging.conversation_logger import conversation_logger
from src.core.assignment_persistence import AssignmentPersistence
from src.monitoring.assignment_monitor import AssignmentMonitor
from src.config.config_loader import get_config

from .handlers import get_tool_definitions, handle_tool_call


class MarcusServer:
    """Marcus MCP Server with modularized architecture"""
    
    def __init__(self):
        """Initialize Marcus server instance"""
        # Config is already loaded by marcus.py, but ensure it's available
        self.config = get_config()
        self.settings = Settings()
        
        # Get kanban provider from config
        self.provider = self.config.get('kanban.provider', 'planka')
        print(f"Initializing Marcus with {self.provider.upper()} kanban provider...")
        
        # Create realtime log with line buffering
        log_dir = Path("logs/conversations")
        log_dir.mkdir(parents=True, exist_ok=True)
        self.realtime_log = open(
            log_dir / f"realtime_{datetime.now():%Y%m%d_%H%M%S}.jsonl", 
            'a', 
            buffering=1  # Line buffering
        )
        atexit.register(self.realtime_log.close)
        
        # Core components
        self.kanban_client: Optional[KanbanInterface] = None
        self.ai_engine = AIAnalysisEngine()
        self.monitor = ProjectMonitor()
        self.comm_hub = CommunicationHub()
        
        # Code analyzer for GitHub
        self.code_analyzer = None
        if self.provider == 'github':
            self.code_analyzer = CodeAnalyzer()
        
        # State tracking
        self.agent_tasks: Dict[str, TaskAssignment] = {}
        self.agent_status: Dict[str, WorkerStatus] = {}
        self.project_state: Optional[ProjectState] = None
        self.project_tasks: List[Any] = []
        
        # Assignment persistence and locking
        self.assignment_persistence = AssignmentPersistence()
        self.assignment_lock = asyncio.Lock()
        self.tasks_being_assigned: set = set()
        
        # Assignment monitoring
        self.assignment_monitor = None
        
        # Log startup
        self.log_event("server_startup", {
            "provider": self.provider,
            "timestamp": datetime.now().isoformat()
        })
        
        # Create MCP server instance
        self.server = Server("marcus")
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register MCP tool handlers"""
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """Return list of available tools"""
            return get_tool_definitions()
        
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, 
            arguments: Optional[Dict[str, Any]]
        ) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """Handle tool calls"""
            return await handle_tool_call(name, arguments, self)
    
    async def initialize_kanban(self):
        """Initialize kanban client if not already done"""
        from src.core.error_framework import KanbanIntegrationError, ErrorContext
        
        if not self.kanban_client:
            try:
                # Ensure configuration is loaded before creating kanban client
                self._ensure_environment_config()
                
                # Create kanban client
                self.kanban_client = KanbanFactory.create(self.provider)
                
                # Validate the client supports task creation
                if not hasattr(self.kanban_client, 'create_task'):
                    raise KanbanIntegrationError(
                        board_name=self.provider,
                        operation="client_initialization",
                        details=f"Kanban client {type(self.kanban_client).__name__} does not support task creation. "
                               f"Expected KanbanClientWithCreate or compatible implementation.",
                        context=ErrorContext(
                            operation="kanban_initialization",
                            integration_name="mcp_server",
                            provider=self.provider
                        )
                    )
                
                # Connect to the kanban board
                if hasattr(self.kanban_client, 'connect'):
                    await self.kanban_client.connect()
                
                # Initialize assignment monitor
                if self.assignment_monitor is None:
                    self.assignment_monitor = AssignmentMonitor(
                        self.assignment_persistence,
                        self.kanban_client
                    )
                    await self.assignment_monitor.start()
                    
                print(f"✅ Kanban client initialized: {type(self.kanban_client).__name__}", file=sys.stderr)
                
            except Exception as e:
                if isinstance(e, KanbanIntegrationError):
                    raise
                raise KanbanIntegrationError(
                    board_name=self.provider,
                    operation="client_initialization",
                    details=f"Failed to initialize kanban client: {str(e)}",
                    context=ErrorContext(
                        operation="kanban_initialization",
                        integration_name="mcp_server",
                        provider=self.provider
                    )
                ) from e
    
    def _ensure_environment_config(self):
        """Ensure environment variables are set from config_marcus.json"""
        from src.core.error_framework import ConfigurationError, ErrorContext
        
        try:
            # Load from config_marcus.json if environment variables aren't set
            import json
            from pathlib import Path
            
            config_path = Path(__file__).parent.parent.parent / "config_marcus.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                # Set Planka environment variables if not already set
                if 'planka' in config:
                    planka_config = config['planka']
                    if 'PLANKA_BASE_URL' not in os.environ:
                        os.environ['PLANKA_BASE_URL'] = planka_config.get('base_url', 'http://localhost:3333')
                    if 'PLANKA_AGENT_EMAIL' not in os.environ:
                        os.environ['PLANKA_AGENT_EMAIL'] = planka_config.get('email', 'demo@demo.demo')
                    if 'PLANKA_AGENT_PASSWORD' not in os.environ:
                        os.environ['PLANKA_AGENT_PASSWORD'] = planka_config.get('password', 'demo')
                    if 'PLANKA_PROJECT_NAME' not in os.environ:
                        os.environ['PLANKA_PROJECT_NAME'] = config.get('project_name', 'Task Master Test')
                
                # Support GitHub if configured in the future
                if 'github' in config:
                    github_config = config['github']
                    if 'GITHUB_TOKEN' not in os.environ and github_config.get('token'):
                        os.environ['GITHUB_TOKEN'] = github_config['token']
                    if 'GITHUB_OWNER' not in os.environ and github_config.get('owner'):
                        os.environ['GITHUB_OWNER'] = github_config['owner']
                    if 'GITHUB_REPO' not in os.environ and github_config.get('repo'):
                        os.environ['GITHUB_REPO'] = github_config['repo']
                
                # Support Linear if configured in the future  
                if 'linear' in config:
                    linear_config = config['linear']
                    if 'LINEAR_API_KEY' not in os.environ and linear_config.get('api_key'):
                        os.environ['LINEAR_API_KEY'] = linear_config['api_key']
                    if 'LINEAR_TEAM_ID' not in os.environ and linear_config.get('team_id'):
                        os.environ['LINEAR_TEAM_ID'] = linear_config['team_id']
                
                print(f"✅ Loaded configuration from {config_path}", file=sys.stderr)
                
        except FileNotFoundError as e:
            raise ConfigurationError(
                service_name="MCP Server",
                config_type="config_marcus.json",
                missing_field="configuration file",
                context=ErrorContext(
                    operation="environment_config_loading",
                    integration_name="mcp_server"
                )
            ) from e
        except Exception as e:
            raise ConfigurationError(
                service_name="MCP Server", 
                config_type="environment variables",
                missing_field="kanban configuration",
                context=ErrorContext(
                    operation="environment_config_loading",
                    integration_name="mcp_server"
                )
            ) from e
    
    def log_event(self, event_type: str, data: dict):
        """Log events immediately to realtime log"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            **data
        }
        self.realtime_log.write(json.dumps(event) + '\n')
    
    async def refresh_project_state(self):
        """Refresh project state from kanban board"""
        if not self.kanban_client:
            await self.initialize_kanban()
        
        try:
            # Get all tasks from the board
            self.project_tasks = await self.kanban_client.get_all_tasks()
            
            # Update project state
            if self.project_tasks:
                total_tasks = len(self.project_tasks)
                completed_tasks = len([t for t in self.project_tasks if t.status == TaskStatus.DONE])
                in_progress_tasks = len([t for t in self.project_tasks if t.status == TaskStatus.IN_PROGRESS])
                
                self.project_state = ProjectState(
                    board_id=self.kanban_client.board_id,
                    project_name="Current Project",  # Would need to get from board
                    total_tasks=total_tasks,
                    completed_tasks=completed_tasks,
                    in_progress_tasks=in_progress_tasks,
                    blocked_tasks=0,  # Would need to track this separately
                    progress_percent=(completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0,
                    overdue_tasks=[],  # Would need to check due dates
                    team_velocity=0.0,  # Would need to calculate
                    risk_level=RiskLevel.LOW,  # Simplified
                    last_updated=datetime.now()
                )
            
            # Create a JSON-serializable version of project_state
            project_state_data = None
            if self.project_state:
                project_state_data = {
                    "board_id": self.project_state.board_id,
                    "project_name": self.project_state.project_name,
                    "total_tasks": self.project_state.total_tasks,
                    "completed_tasks": self.project_state.completed_tasks,
                    "in_progress_tasks": self.project_state.in_progress_tasks,
                    "blocked_tasks": self.project_state.blocked_tasks,
                    "progress_percent": self.project_state.progress_percent,
                    "team_velocity": self.project_state.team_velocity,
                    "risk_level": self.project_state.risk_level.value,  # Convert enum to string
                    "last_updated": self.project_state.last_updated.isoformat()
                }
            
            self.log_event("project_state_refreshed", {
                "task_count": len(self.project_tasks),
                "project_state": project_state_data
            })
            
        except Exception as e:
            self.log_event("project_state_refresh_error", {"error": str(e)})
            raise
    
    async def run(self):
        """Run the MCP server"""
        print(f"\nMarcus MCP Server Running")
        print(f"Kanban Provider: {self.provider.upper()}")
        print(f"Logs: logs/conversations/")
        print("="*50)
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point"""
    server = MarcusServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())