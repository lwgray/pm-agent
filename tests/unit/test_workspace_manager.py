"""
Unit tests for WorkspaceManager
"""

import os
import json
import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.workspace_manager import WorkspaceManager, WorkspaceSecurityError, WorkspaceConfig


class TestWorkspaceManager:
    """Test suite for WorkspaceManager"""
    
    def test_pm_agent_root_detection(self):
        """Test that Marcus root is correctly detected"""
        manager = WorkspaceManager()
        
        # Should detect the Marcus root directory
        assert manager.pm_agent_root.endswith('pm-agent')
        assert os.path.exists(manager.pm_agent_root)
        
        # Marcus root should be in forbidden paths
        assert manager.pm_agent_root in manager.forbidden_paths
    
    def test_forbidden_paths_initialization(self):
        """Test that forbidden paths are properly initialized"""
        manager = WorkspaceManager()
        
        # Marcus root and its parent should be forbidden
        assert manager.pm_agent_root in manager.forbidden_paths
        assert os.path.dirname(manager.pm_agent_root) in manager.forbidden_paths
        
        # Should have multiple forbidden paths (including system paths)
        assert len(manager.forbidden_paths) > 2
    
    def test_path_validation_forbidden(self):
        """Test that forbidden paths are rejected"""
        manager = WorkspaceManager()
        
        # Try to access Marcus directory
        with pytest.raises(WorkspaceSecurityError):
            manager.validate_path(manager.pm_agent_root)
        
        # Try to access subdirectory of Marcus
        pm_agent_subdir = os.path.join(manager.pm_agent_root, 'src', 'core')
        with pytest.raises(WorkspaceSecurityError):
            manager.validate_path(pm_agent_subdir)
    
    def test_path_validation_allowed(self):
        """Test that allowed paths pass validation"""
        manager = WorkspaceManager()
        
        # Create a temporary directory outside Marcus
        with tempfile.TemporaryDirectory() as tmpdir:
            # This should be allowed
            validated_path = manager.validate_path(tmpdir)
            assert validated_path == os.path.abspath(tmpdir)
            
            # Check with is_path_allowed
            assert manager.is_path_allowed(tmpdir)
    
    def test_workspace_assignment(self):
        """Test agent workspace assignment"""
        manager = WorkspaceManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Assign workspace to agent
            workspace = manager.assign_agent_workspace('agent1', tmpdir)
            
            assert workspace.agent_id == 'agent1'
            assert workspace.path == os.path.abspath(tmpdir)
            assert workspace.workspace_id == 'agent1_workspace'
            
            # Should be retrievable
            retrieved = manager.get_agent_workspace('agent1')
            assert retrieved == workspace
    
    def test_workspace_assignment_forbidden(self):
        """Test that forbidden paths cannot be assigned as workspaces"""
        manager = WorkspaceManager()
        
        # Try to assign Marcus directory as workspace
        with pytest.raises(WorkspaceSecurityError):
            manager.assign_agent_workspace('agent1', manager.pm_agent_root)
    
    def test_project_workspace_config(self):
        """Test loading project workspace configuration"""
        manager = WorkspaceManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test configuration
            config = {
                "project": {
                    "workspaces": {
                        "main": tmpdir,
                        "agents": {
                            "frontend": os.path.join(tmpdir, "frontend"),
                            "backend": os.path.join(tmpdir, "backend")
                        }
                    }
                }
            }
            
            # Write config to file
            config_path = os.path.join(tmpdir, "test_config.json")
            with open(config_path, 'w') as f:
                json.dump(config, f)
            
            # Load configuration
            manager.load_config(config_path)
            
            assert manager.project_config is not None
            assert manager.project_config.main_workspace == os.path.abspath(tmpdir)
            assert len(manager.project_config.agent_workspaces) == 2
    
    def test_project_workspace_overlap_detection(self):
        """Test that overlapping workspaces with forbidden paths are detected"""
        manager = WorkspaceManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config that tries to use Marcus directory
            config = {
                "project": {
                    "workspaces": {
                        "main": manager.pm_agent_root,  # Forbidden!
                        "agents": {}
                    }
                }
            }
            
            config_path = os.path.join(tmpdir, "bad_config.json")
            with open(config_path, 'w') as f:
                json.dump(config, f)
            
            # Should raise security error
            with pytest.raises(WorkspaceSecurityError):
                manager.load_config(config_path)
    
    def test_task_assignment_data(self):
        """Test generation of task assignment data"""
        manager = WorkspaceManager()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Assign workspace
            manager.assign_agent_workspace('agent1', tmpdir)
            
            # Get task assignment data
            data = manager.get_task_assignment_data('agent1')
            
            assert 'workspace_path' in data
            assert 'forbidden_paths' in data
            assert data['workspace_path'] == os.path.abspath(tmpdir)
            assert manager.pm_agent_root in data['forbidden_paths']
    
    def test_add_forbidden_path(self):
        """Test adding custom forbidden paths"""
        manager = WorkspaceManager()
        
        # Add a custom forbidden path
        custom_forbidden = "/etc/sensitive"
        manager.add_forbidden_path(custom_forbidden)
        
        assert os.path.abspath(custom_forbidden) in manager.forbidden_paths
        
        # Should be forbidden now
        with pytest.raises(WorkspaceSecurityError):
            manager.validate_path(custom_forbidden)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])