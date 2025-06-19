"""
Factory for creating kanban provider instances

Simplifies the process of creating the right kanban provider
based on configuration.
"""

from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv

from src.integrations.kanban_interface import KanbanInterface, KanbanProvider
from src.integrations.providers import PlankaKanban, LinearKanban, GitHubKanban
from src.integrations.providers.planka_kanban_simple import PlankaKanbanSimple


class KanbanFactory:
    """Factory for creating kanban provider instances"""
    
    @staticmethod
    def create(provider: str, config: Optional[Dict[str, Any]] = None) -> KanbanInterface:
        """
        Create a kanban provider instance
        
        Args:
            provider: Provider name ('planka', 'linear', 'github')
            config: Optional configuration override
            
        Returns:
            KanbanInterface implementation
            
        Raises:
            ValueError: If provider is not supported
        """
        load_dotenv()
        
        provider_lower = provider.lower()
        
        if provider_lower == KanbanProvider.PLANKA.value:
            if not config:
                config = {
                    'project_name': os.getenv('PLANKA_PROJECT_NAME', 'Task Master Test'),
                }
            # Use SimpleMCPKanbanClient-based implementation
            return PlankaKanbanSimple(config)
            
        elif provider_lower == KanbanProvider.LINEAR.value:
            if not config:
                config = {
                    'api_key': os.getenv('LINEAR_API_KEY'),
                    'team_id': os.getenv('LINEAR_TEAM_ID'),
                    'project_id': os.getenv('LINEAR_PROJECT_ID')
                }
            return LinearKanban(config)
            
        elif provider_lower == KanbanProvider.GITHUB.value:
            if not config:
                config = {
                    'token': os.getenv('GITHUB_TOKEN'),
                    'owner': os.getenv('GITHUB_OWNER'),
                    'repo': os.getenv('GITHUB_REPO'),
                    'project_number': int(os.getenv('GITHUB_PROJECT_NUMBER', '1'))
                }
            return GitHubKanban(config)
            
        else:
            raise ValueError(f"Unsupported kanban provider: {provider}")
            
    @staticmethod
    def get_default_provider() -> str:
        """Get the default provider from environment"""
        return os.getenv('KANBAN_PROVIDER', 'planka')
        
    @staticmethod
    def create_default(config: Optional[Dict[str, Any]] = None) -> KanbanInterface:
        """Create the default kanban provider"""
        provider = KanbanFactory.get_default_provider()
        return KanbanFactory.create(provider, config)