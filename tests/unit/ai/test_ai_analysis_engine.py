"""
Unit tests for the AI Analysis Engine.

This module tests the AI-powered decision-making capabilities of Marcus,
including task assignment optimization, blocker analysis, and project risk assessment.

Notes
-----
Tests use mocked Anthropic API calls to ensure reproducibility and avoid
external dependencies during testing.
"""

import pytest
import json
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from src.core.models import Task, TaskStatus, Priority, WorkerStatus, ProjectState, RiskLevel, BlockerReport, ProjectRisk
from src.integrations.ai_analysis_engine_fixed import AIAnalysisEngine


class TestAIAnalysisEngine:
    """
    Test suite for the AI Analysis Engine.
    
    This tests the core intelligence of Marcus - how it makes decisions
    about task assignments, analyzes blockers, and provides recommendations.
    """
    
    @pytest.fixture
    def ai_engine(self) -> AIAnalysisEngine:
        """
        Create a test instance of the AI Analysis Engine.
        
        Returns
        -------
        AIAnalysisEngine
            An AI engine instance with mocked Anthropic client.
        
        Notes
        -----
        The Anthropic client is mocked to avoid real API calls during tests.
        This fixture runs before each test method.
        """
        with patch('anthropic.Anthropic') as mock_anthropic:
            engine = AIAnalysisEngine()
            # Mock the client to avoid real API calls in tests
            engine.client = Mock()
            return engine
    
    @pytest.fixture
    def sample_tasks(self) -> List[Task]:
        """
        Create sample task data for testing.
        
        Returns
        -------
        List[Task]
            A list of task objects with varying priorities and requirements.
        
        Notes
        -----
        Tasks represent different scenarios including high-priority features,
        bug fixes, and technical debt items to test various decision paths.
        """
        return [
            Task(
                id="TASK-001",
                name="Implement user authentication",
                description="Add OAuth2 login functionality",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=datetime.now() + timedelta(days=3),
                estimated_hours=16.0,
                dependencies=[],
                labels=["backend", "security", "oauth"]
            ),
            Task(
                id="TASK-002",
                name="Create dashboard UI",
                description="Design and implement analytics dashboard",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=datetime.now() + timedelta(days=5),
                estimated_hours=24.0,
                dependencies=["TASK-001"],
                labels=["frontend", "react", "ui/ux"]
            ),
            Task(
                id="TASK-003",
                name="Fix critical bug in payment system",
                description="Payment processing fails for certain cards",
                status=TaskStatus.TODO,
                priority=Priority.URGENT,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=datetime.now() + timedelta(hours=4),
                estimated_hours=4.0,
                dependencies=[],
                labels=["backend", "payments", "bug", "critical"]
            )
        ]
    
    @pytest.fixture
    def sample_workers(self):
        """
        STEP 3: Create sample worker profiles
        
        What's happening:
        - We create different worker personas with varying skills and capacities
        - Each worker has different strengths (backend vs frontend, senior vs junior)
        - This tests how the AI matches tasks to the right people
        """
        return {
            "backend_senior": WorkerStatus(
                worker_id="dev-001",
                name="Alice Johnson",
                role="Senior Backend Developer",
                email="alice@example.com",
                current_tasks=[],
                completed_tasks_count=50,
                capacity=40,
                skills=["python", "django", "postgresql", "oauth", "payments", "security"],
                availability={"monday": True, "tuesday": True, "wednesday": True},
                performance_score=1.2  # Above average performer
            ),
            "frontend_dev": WorkerStatus(
                worker_id="dev-002", 
                name="Bob Smith",
                role="Frontend Developer",
                email="bob@example.com",
                current_tasks=[],
                completed_tasks_count=30,
                capacity=35,
                skills=["react", "typescript", "css", "ui/ux", "javascript"],
                availability={"monday": True, "tuesday": True},
                performance_score=1.0
            ),
            "fullstack_junior": WorkerStatus(
                worker_id="dev-003",
                name="Charlie Davis",
                role="Junior Full-stack Developer",
                email="charlie@example.com",
                current_tasks=[],
                completed_tasks_count=10,
                capacity=30,
                skills=["python", "react", "basic"],
                availability={"monday": True},
                performance_score=0.8  # Still learning
            )
        }
    
    @pytest.mark.asyncio
    async def test_match_task_to_agent_urgent_priority(self, ai_engine, sample_tasks, sample_workers):
        """
        TEST 1: Verify AI assigns urgent tasks to the most qualified available agent
        
        What's being tested:
        1. The AI recognizes task priority (URGENT > HIGH > MEDIUM)
        2. It matches task requirements (payments) to worker skills
        3. It selects the senior developer for critical work
        
        Step-by-step:
        1. We mock the AI's response to return TASK-003 (urgent payment bug)
        2. We ask the AI to find a task for our senior backend developer
        3. We verify it chose the urgent task over others
        """
        # STEP 1: Mock the Claude API response
        mock_response = {
            "recommended_task_id": "TASK-003",  # The urgent payment bug
            "confidence_score": 0.95,
            "reasoning": "Urgent payment bug requires immediate attention from experienced developer",
            "alternative_tasks": ["TASK-001"],
            "considerations": ["Critical business impact", "Matches developer skills"]
        }
        
        ai_engine._call_claude = AsyncMock(return_value=json.dumps(mock_response))
        
        # STEP 2: Create a simple project state
        project_state = ProjectState(
            board_id="BOARD-001",
            project_name="Test Project",
            total_tasks=10,
            completed_tasks=3,
            in_progress_tasks=2,
            blocked_tasks=0,
            progress_percent=30.0,
            overdue_tasks=[],
            team_velocity=5.0,
            risk_level=RiskLevel.MEDIUM,
            last_updated=datetime.now()
        )
        
        # STEP 3: Call the AI to match a task
        result = await ai_engine.match_task_to_agent(
            sample_tasks,
            sample_workers["backend_senior"],
            project_state
        )
        
        # STEP 4: Verify the results
        assert result is not None
        assert result.id == "TASK-003"
        assert result.priority == Priority.URGENT
        
        # STEP 5: Verify the AI was called with proper context
        call_args = ai_engine._call_claude.call_args[0][0]
        assert "payment" in call_args.lower()
        assert "urgent" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_generate_task_instructions(self, ai_engine, sample_tasks, sample_workers):
        """
        TEST 2: Verify AI generates appropriate instructions based on worker experience
        
        What's being tested:
        1. The AI tailors instructions to the worker's skill level
        2. Instructions are comprehensive and actionable
        3. The AI considers the task context and requirements
        
        Step-by-step:
        1. We test with both senior and junior developers
        2. We verify instructions are more detailed for juniors
        3. We check that instructions include relevant technical details
        """
        # Test Case 1: Instructions for senior developer
        senior_task = sample_tasks[0]  # Auth implementation
        senior_worker = sample_workers["backend_senior"]
        
        # Mock response for senior developer
        ai_engine._call_claude = AsyncMock(
            return_value="""## OAuth2 Implementation Instructions

Given your experience with authentication systems, here's the streamlined approach:

1. **Setup OAuth2 Provider**
   - Configure Google/GitHub OAuth credentials
   - Set up redirect URIs in provider console

2. **Implementation**
   - Use `authlib` or `python-social-auth` 
   - Implement callback handlers
   - Store tokens securely (consider Redis for sessions)

3. **Security Considerations**
   - Implement PKCE flow for additional security
   - Set up proper CORS policies
   - Add rate limiting on auth endpoints

You're familiar with these patterns, so focus on our specific business requirements."""
        )
        
        senior_instructions = await ai_engine.generate_task_instructions(
            senior_task,
            senior_worker
        )
        
        # Verify senior instructions are concise but thorough
        assert "OAuth2" in senior_instructions
        assert "PKCE" in senior_instructions  # Advanced security concept
        assert len(senior_instructions) < 1000  # Not overly verbose
        
        # Test Case 2: Instructions for junior developer
        junior_worker = sample_workers["fullstack_junior"]
        
        # Mock more detailed response for junior
        ai_engine._call_claude = AsyncMock(
            return_value="""## OAuth2 Implementation Instructions - Detailed Guide

Since this is your first OAuth2 implementation, here's a step-by-step guide:

1. **Understanding OAuth2**
   - OAuth2 is a protocol that allows users to log in using existing accounts
   - Read this primer first: [link to OAuth2 basics]

2. **Detailed Implementation Steps**
   
   a. Install required packages:
   ```bash
   pip install authlib requests
   ```
   
   b. Create OAuth configuration:
   ```python
   # config/oauth.py
   OAUTH_PROVIDERS = {
       'google': {
           'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
           'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET'),
           'authorize_url': 'https://accounts.google.com/o/oauth2/v2/auth',
           'token_url': 'https://oauth2.googleapis.com/token'
       }
   }
   ```
   
   c. Implement the login route:
   ```python
   @app.route('/login/<provider>')
   def login(provider):
       # Detailed implementation here...
   ```

3. **Testing Your Implementation**
   - Start with local testing
   - Use ngrok for callback URL testing
   - Write unit tests for each component

4. **Getting Help**
   - Check with Alice (senior backend) if you get stuck
   - Useful debugging tips: check network tab, log all responses

Remember: Take your time, test thoroughly, and ask questions!"""
        )
        
        junior_instructions = await ai_engine.generate_task_instructions(
            senior_task,
            junior_worker
        )
        
        # Verify junior instructions are more detailed
        assert len(junior_instructions) > len(senior_instructions)
        assert "step-by-step" in junior_instructions.lower()
        assert "pip install" in junior_instructions  # Includes basic setup
        assert "Getting Help" in junior_instructions  # Guidance on asking for help
    
    @pytest.mark.asyncio
    async def test_analyze_blocker_with_escalation(self, ai_engine):
        """
        TEST 3: Verify AI correctly analyzes blockers and determines escalation needs
        
        What's being tested:
        1. The AI identifies root causes of blockers
        2. It determines when escalation is needed
        3. It provides actionable resolution steps
        
        Step-by-step:
        1. We present a serious production blocker
        2. The AI analyzes it and determines escalation is needed
        3. We verify the response includes proper escalation procedures
        """
        # Simulate a critical production blocker
        task_id = "TASK-100"
        blocker_description = "Production database is showing 90% CPU usage, queries timing out"
        severity = "critical"
        
        # Mock AI response for critical blocker
        mock_analysis = {
            "root_cause": "Database query optimization needed - missing indexes on large tables",
            "impact_assessment": "All users experiencing slow response times, potential data loss",
            "needs_coordination": True,
            "resolution_steps": [
                "1. Immediately add read replica to distribute load",
                "2. Identify slow queries using pg_stat_statements",
                "3. Add missing indexes on user_transactions table",
                "4. Implement query result caching",
                "5. Schedule database maintenance window"
            ],
            "required_resources": ["DBA", "Senior Backend Developer", "DevOps"],
            "estimated_hours": 6,
            "escalation_needed": True,
            "prevention_measures": [
                "Implement query performance monitoring",
                "Add automated index recommendations",
                "Set up capacity planning alerts"
            ]
        }
        
        ai_engine._call_claude = AsyncMock(return_value=json.dumps(mock_analysis))
        
        # Call the blocker analysis
        result = await ai_engine.analyze_blocker(task_id, blocker_description, severity)
        
        # Verify critical elements of the response
        assert result["escalation_needed"] is True
        assert result["needs_coordination"] is True
        assert "DBA" in result["required_resources"]
        assert result["estimated_hours"] >= 4  # Significant time needed
        assert len(result["resolution_steps"]) >= 3  # Multiple steps required
        assert "prevention_measures" in result  # Includes future prevention
    
    @pytest.mark.asyncio 
    async def test_project_health_analysis(self, ai_engine):
        """
        TEST 4: Verify AI correctly assesses overall project health
        
        What's being tested:
        1. The AI synthesizes multiple data points into health assessment
        2. It identifies risks and provides recommendations
        3. It predicts timeline impacts
        
        Step-by-step:
        1. We provide project data showing warning signs
        2. The AI analyzes trends and team capacity
        3. We verify it identifies the issues and suggests fixes
        """
        # Create project state with some concerning metrics
        project_state = ProjectState(
            board_id="BOARD-001",
            project_name="E-commerce Platform",
            total_tasks=100,
            completed_tasks=25,
            in_progress_tasks=30,  # Too many tasks in progress
            blocked_tasks=8,       # High number of blockers
            progress_percent=25.0,
            overdue_tasks=[],      # Will be populated
            team_velocity=3.0,     # Low velocity
            risk_level=RiskLevel.HIGH,
            last_updated=datetime.now()
        )
        
        # Recent activities showing problems
        recent_activities = [
            {"type": "task_blocked", "count": 5, "timeframe": "last_week"},
            {"type": "task_completed", "count": 3, "timeframe": "last_week"},
            {"type": "deadline_missed", "count": 2, "timeframe": "last_week"}
        ]
        
        # Team showing capacity issues
        team_status = [
            WorkerStatus(
                worker_id="dev-001",
                name="Alice",
                role="Senior Dev",
                email="alice@example.com",
                current_tasks=[Mock(), Mock(), Mock(), Mock()],  # Overloaded
                completed_tasks_count=20,
                capacity=40,
                skills=["python"],
                availability={},
                performance_score=0.7  # Performance dropping
            )
        ]
        
        # Mock AI health analysis response
        mock_analysis = {
            "overall_health": "red",
            "progress_assessment": "Project is at high risk of missing deadline",
            "risk_factors": [
                {
                    "type": "resource",
                    "severity": "high",
                    "description": "Team is overloaded - 30 tasks in progress with only 5 developers"
                },
                {
                    "type": "technical",
                    "severity": "medium", 
                    "description": "High blocker rate indicates architectural issues"
                },
                {
                    "type": "timeline",
                    "severity": "high",
                    "description": "Current velocity of 3 tasks/week won't meet deadline"
                }
            ],
            "recommendations": [
                {
                    "action": "Immediately limit work in progress to 2 tasks per developer",
                    "priority": "high",
                    "owner": "Project Manager"
                },
                {
                    "action": "Conduct blocker retrospective to identify patterns",
                    "priority": "high",
                    "owner": "Tech Lead"
                },
                {
                    "action": "Consider bringing in additional resources or extending timeline",
                    "priority": "medium",
                    "owner": "Stakeholders"
                }
            ],
            "timeline_prediction": {
                "on_track": False,
                "estimated_completion": "2024-06-15",  # 3 months late
                "confidence": 0.3
            },
            "resource_optimization": [
                {
                    "suggestion": "Redistribute tasks from overloaded developers",
                    "impact": "Could improve velocity by 40%"
                }
            ]
        }
        
        ai_engine._call_claude = AsyncMock(return_value=json.dumps(mock_analysis))
        
        # Run the analysis
        result = await ai_engine.analyze_project_health(
            project_state,
            recent_activities,
            team_status
        )
        
        # Verify the AI identified all major issues
        assert result["overall_health"] == "red"
        assert result["timeline_prediction"]["on_track"] is False
        assert len(result["risk_factors"]) >= 3
        assert any(risk["type"] == "resource" for risk in result["risk_factors"])
        assert len(result["recommendations"]) >= 2
        assert result["timeline_prediction"]["confidence"] < 0.5  # Low confidence
    
    @pytest.mark.asyncio
    async def test_fallback_behavior_on_api_error(self, ai_engine, sample_tasks, sample_workers):
        """
        TEST 5: Verify system degrades gracefully when AI is unavailable
        
        What's being tested:
        1. The system doesn't crash when Claude API fails
        2. It falls back to reasonable defaults
        3. Basic functionality continues working
        
        Step-by-step:
        1. We simulate an API error
        2. The system falls back to simple priority-based assignment
        3. We verify the fallback produces valid results
        """
        # Simulate API failure
        ai_engine._call_claude = AsyncMock(side_effect=Exception("API rate limit exceeded"))
        
        project_state = ProjectState(
            board_id="BOARD-001",
            project_name="Test Project",
            total_tasks=10,
            completed_tasks=5,
            in_progress_tasks=3,
            blocked_tasks=0,
            progress_percent=50.0,
            overdue_tasks=[],
            team_velocity=5.0,
            risk_level=RiskLevel.LOW,
            last_updated=datetime.now()
        )
        
        # Should fall back to highest priority task
        result = await ai_engine.match_task_to_agent(
            sample_tasks,
            sample_workers["backend_senior"],
            project_state
        )
        
        # Verify fallback behavior
        assert result is not None
        assert result.priority == Priority.URGENT  # Picked highest priority
        
        # Test blocker analysis fallback
        blocker_result = await ai_engine.analyze_blocker(
            "TASK-999",
            "Cannot connect to external API",
            "high"
        )
        
        # Verify fallback provides basic structure
        assert "resolution_steps" in blocker_result
        assert "escalation_needed" in blocker_result
        assert blocker_result["escalation_needed"] is True  # Conservative approach
    
    @pytest.mark.asyncio
    async def test_client_initialization_with_api_key(self, monkeypatch):
        """Test successful client initialization with API key"""
        # Mock environment variable
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key")
        
        # Mock config loader to return test API key
        with patch('src.config.config_loader.get_config') as mock_get_config:
            mock_config = Mock()
            mock_config.get.return_value = 'test-api-key'
            mock_get_config.return_value = mock_config
            
            # Mock anthropic module
            with patch('src.integrations.ai_analysis_engine_fixed.anthropic') as mock_anthropic:
                mock_client = Mock()
                mock_anthropic.Anthropic.return_value = mock_client
                
                # Create engine - should initialize client
                engine = AIAnalysisEngine()
                
                assert engine.client == mock_client
                mock_anthropic.Anthropic.assert_called_once_with(api_key="test-api-key")
    
    @pytest.mark.asyncio
    async def test_client_initialization_failure(self, monkeypatch, capsys):
        """Test client initialization when Anthropic raises exception"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key")
        
        # Mock config loader
        with patch('src.config.config_loader.get_config') as mock_get_config:
            mock_config = Mock()
            mock_config.get.return_value = 'test-api-key'
            mock_get_config.return_value = mock_config
            
            with patch('src.integrations.ai_analysis_engine_fixed.anthropic') as mock_anthropic:
                mock_anthropic.Anthropic.side_effect = Exception("Connection failed")
                
                engine = AIAnalysisEngine()
                
                assert engine.client is None
            captured = capsys.readouterr()
            assert "Failed to initialize Anthropic client" in captured.err
    
    
    @pytest.mark.asyncio
    async def test_generate_task_instructions_with_agent(self, ai_engine, sample_tasks, sample_workers):
        """Test instruction generation with agent context"""
        task = sample_tasks[0]
        agent = sample_workers["backend_senior"]
        
        mock_response = """## Task Instructions

**Setup Steps:**
1. Install dependencies
2. Configure OAuth

**Implementation Steps:**
1. Create auth module
2. Add OAuth endpoints

**Testing Approach:**
Write unit tests for auth flow

**Acceptance Criteria:**
- Users can login
- Tokens are secure"""
        
        ai_engine._call_claude = AsyncMock(return_value=mock_response)
        
        result = await ai_engine.generate_task_instructions(task, agent)
        
        assert isinstance(result, str)
        assert "Setup Steps" in result
        assert "Implementation Steps" in result
    
    @pytest.mark.asyncio
    async def test_generate_task_instructions_fallback(self, ai_engine, sample_tasks):
        """Test instruction generation fallback when AI fails"""
        task = sample_tasks[0]
        
        # Make AI call fail
        ai_engine._call_claude = AsyncMock(side_effect=Exception("API error"))
        
        result = await ai_engine.generate_task_instructions(task)
        
        # Should return fallback instructions
        assert isinstance(result, str)
        assert "Task Assignment" in result
        assert task.name in result
    
    @pytest.mark.asyncio
    async def test_analyze_blocker_json_error(self, ai_engine):
        """Test blocker analysis with JSON parsing error"""
        ai_engine._call_claude = AsyncMock(return_value="Not valid JSON")
        
        result = await ai_engine.analyze_blocker("TASK-001", "Database down", "high")
        
        # Should return fallback
        assert result["escalation_needed"] is True
        assert "resolution_steps" in result
    
    @pytest.mark.asyncio
    async def test_analyze_project_risks_with_blockers(self, ai_engine, sample_workers):
        """Test project risk analysis with recent blockers"""
        project_state = ProjectState(
            board_id="BOARD-001",
            project_name="Test Project",
            total_tasks=50,
            completed_tasks=10,
            in_progress_tasks=20,
            blocked_tasks=5,
            progress_percent=20.0,
            overdue_tasks=[],
            team_velocity=2.0,
            risk_level=RiskLevel.HIGH,
            last_updated=datetime.now()
        )
        
        blockers = [
            BlockerReport(
                task_id="TASK-001",
                reporter_id="dev-001",
                description="API rate limit",
                severity=RiskLevel.HIGH,
                reported_at=datetime.now(),
                resolved=False,
                resolution=None,
                resolved_at=None
            )
        ]
        
        team = [sample_workers["backend_senior"]] 
        
        mock_response = json.dumps({
            "risks": [
                {
                    "type": "technical",
                    "description": "API dependencies causing delays",
                    "likelihood": "high",
                    "impact": "high",
                    "mitigation": "Implement caching layer"
                }
            ],
            "overall_risk_level": "high",
            "recommendations": ["Add redundancy", "Review architecture"]
        })
        
        ai_engine._call_claude = AsyncMock(return_value=mock_response)
        
        result = await ai_engine.analyze_project_risks(project_state, blockers, team)
        
        assert len(result) > 0
        assert result[0].risk_type == "project"
        assert result[0].severity == RiskLevel.HIGH
    
    @pytest.mark.asyncio
    async def test_analyze_project_risks_json_error(self, ai_engine):
        """Test risk analysis with JSON parsing error"""
        project_state = ProjectState(
            board_id="BOARD-001",
            project_name="Test Project",
            total_tasks=10,
            completed_tasks=5,
            in_progress_tasks=3,
            blocked_tasks=0,
            progress_percent=50.0,
            overdue_tasks=[],
            team_velocity=5.0,
            risk_level=RiskLevel.LOW,
            last_updated=datetime.now()
        )
        
        ai_engine._call_claude = AsyncMock(return_value="Invalid response")
        
        result = await ai_engine.analyze_project_risks(project_state, [], [])
        
        # Should return empty list on error for low risk project
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_fallback_risk_analysis_high_risk(self):
        """Test fallback risk analysis for high risk project"""
        engine = AIAnalysisEngine()
        
        project_state = ProjectState(
            board_id="BOARD-001",
            project_name="Test Project",
            total_tasks=10,
            completed_tasks=2,
            in_progress_tasks=3,
            blocked_tasks=2,
            progress_percent=20.0,
            overdue_tasks=[],
            team_velocity=1.0,
            risk_level=RiskLevel.HIGH,
            last_updated=datetime.now()
        )
        
        risks = engine._generate_fallback_risk_analysis(project_state)
        
        assert len(risks) > 0
        assert risks[0].risk_type == "timeline"
        assert risks[0].severity == RiskLevel.HIGH
    
    @pytest.mark.asyncio
    async def test_call_claude_success(self, ai_engine):
        """Test successful Claude API call"""
        mock_response = Mock()
        mock_response.content = [Mock(text="AI response")]
        
        ai_engine.client = Mock()
        ai_engine.client.messages.create.return_value = mock_response
        
        result = await ai_engine._call_claude("test prompt")
        
        assert result == "AI response"
        ai_engine.client.messages.create.assert_called_once_with(
            model=ai_engine.model,
            max_tokens=2000,
            temperature=0.7,
            messages=[{"role": "user", "content": "test prompt"}]
        )
    
    @pytest.mark.asyncio
    async def test_call_claude_no_client(self, ai_engine):
        """Test Claude call when client is None"""
        ai_engine.client = None
        
        with pytest.raises(Exception, match="Anthropic client not available"):
            await ai_engine._call_claude("test prompt")
    
    @pytest.mark.asyncio
    async def test_call_claude_api_error(self, ai_engine, capsys):
        """Test Claude call with API error"""
        ai_engine.client = Mock()
        ai_engine.client.messages.create.side_effect = Exception("API rate limit")
        
        with pytest.raises(Exception):
            await ai_engine._call_claude("test prompt")
        
        captured = capsys.readouterr()
        assert "Error calling Claude" in captured.err
    
    @pytest.mark.asyncio 
    async def test_fallback_health_analysis_comprehensive(self):
        """Test comprehensive fallback health analysis"""
        engine = AIAnalysisEngine()
        
        # High risk project with many issues
        project_state = ProjectState(
            board_id="BOARD-001",
            project_name="Test Project",
            total_tasks=100,
            completed_tasks=20,
            in_progress_tasks=30,
            blocked_tasks=5,
            progress_percent=40.0,  # Should be 40% but only 20% complete
            overdue_tasks=[Mock(), Mock(), Mock()],  # 3 overdue tasks
            team_velocity=1.5,  # Low velocity
            risk_level=RiskLevel.HIGH,
            last_updated=datetime.now()
        )
        
        team_status = {}  # Not used in fallback
        
        result = engine._generate_fallback_health_analysis(project_state, team_status)
        
        assert result["overall_health"] == "red"
        assert result["timeline_prediction"]["on_track"] is False
        assert len(result["risk_factors"]) >= 2  # Both blocked and overdue risks
        assert len(result["recommendations"]) >= 2
        assert result["timeline_prediction"]["confidence"] == 0.3
    
    @pytest.mark.asyncio
    async def test_match_task_edge_cases(self, ai_engine):
        """Test task matching with edge cases"""
        # Empty task list
        result = await ai_engine.match_task_to_agent([], Mock(), Mock())
        assert result is None
        
        # Task with valid priority 
        task_with_priority = Task(
            id="TASK-999",
            name="Task with priority",
            description="Test",
            status=TaskStatus.TODO,
            priority=Priority.LOW,  # Valid priority
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=1.0,
            dependencies=[],
            labels=[]
        )
        
        agent = WorkerStatus(
            worker_id="test-001",
            name="Test Worker",
            role="Developer",
            email="test@example.com",
            current_tasks=[],
            completed_tasks_count=0,
            capacity=40,
            skills=[],
            availability={},
            performance_score=1.0
        )
        
        project_state = ProjectState(
            board_id="BOARD-001",
            project_name="Test",
            total_tasks=10,
            completed_tasks=5,
            in_progress_tasks=3,
            blocked_tasks=0,
            progress_percent=50.0,
            overdue_tasks=[],
            team_velocity=5.0,
            risk_level=RiskLevel.LOW,
            last_updated=datetime.now()
        )
        
        result = await ai_engine.match_task_to_agent([task_with_priority], agent, project_state)
        assert result == task_with_priority  # Should return the only task
    
    @pytest.mark.asyncio
    async def test_project_health_with_dict_team_status(self, ai_engine):
        """Test project health analysis with dict team status"""
        project_state = Mock()
        project_state.board_id = "BOARD-001"
        project_state.project_name = "Test"
        project_state.total_tasks = 10
        project_state.completed_tasks = 5
        project_state.in_progress_tasks = 3
        project_state.blocked_tasks = 1
        project_state.progress_percent = 50.0
        project_state.team_velocity = 5.0
        project_state.risk_level = RiskLevel.LOW
        project_state.last_updated = datetime.now()
        project_state.overdue_tasks = []
        
        # Pass team status as dict instead of list
        team_status = {"team_size": 5, "avg_capacity": 35}
        
        mock_response = json.dumps({
            "overall_health": "green",
            "timeline_prediction": {
                "on_track": True,
                "estimated_completion": "On schedule",
                "confidence": 0.8
            },
            "risk_factors": [],
            "recommendations": [],
            "resource_optimization": []
        })
        
        ai_engine._call_claude = AsyncMock(return_value=mock_response)
        
        result = await ai_engine.analyze_project_health(
            project_state, 
            [], 
            team_status  # Dict instead of list
        )
        
        assert result["overall_health"] == "green"
    
    @pytest.mark.asyncio
    async def test_no_client_fallback_all_methods(self):
        """Test all methods work with no client"""
        # Create engine with no client
        engine = AIAnalysisEngine()
        engine.client = None
        
        # Test data
        task = Task(
            id="TASK-001",
            name="Test task",
            description="Test",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=1.0,
            dependencies=[],
            labels=["test"]
        )
        
        worker = WorkerStatus(
            worker_id="test-001",
            name="Test Worker",
            role="Developer",
            email="test@example.com",
            current_tasks=[],
            completed_tasks_count=0,
            capacity=40,
            skills=["test"],
            availability={},
            performance_score=1.0
        )
        
        project_state = ProjectState(
            board_id="BOARD-001",
            project_name="Test",
            total_tasks=10,
            completed_tasks=5,
            in_progress_tasks=3,
            blocked_tasks=0,
            progress_percent=50.0,
            overdue_tasks=[],
            team_velocity=5.0,
            risk_level=RiskLevel.LOW,
            last_updated=datetime.now()
        )
        
        # Test match_task_to_agent with no client
        result = await engine.match_task_to_agent([task], worker, project_state)
        assert result == task
        
        # Test generate_task_instructions with no client
        instructions = await engine.generate_task_instructions(task, worker)
        assert "Task Assignment" in instructions
        
        # Test analyze_blocker with no client
        blocker_result = await engine.analyze_blocker("TASK-001", "Test blocker", "high")
        assert blocker_result["escalation_needed"] is True
        
        # Test analyze_project_health with no client
        health_result = await engine.analyze_project_health(project_state, [], [])
        assert "overall_health" in health_result
        
        # Test analyze_project_risks with no client
        risks = await engine.analyze_project_risks(project_state, [], [])
        assert isinstance(risks, list)
    
    @pytest.mark.asyncio
    async def test_generate_instructions_no_agent(self, ai_engine):
        """Test instruction generation without agent"""
        task = Task(
            id="TASK-001",
            name="Test task",
            description="Test description",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=3),
            estimated_hours=8.0,
            dependencies=["TASK-999"],
            labels=["backend"]
        )
        
        mock_instructions = "Test instructions"
        ai_engine._call_claude = AsyncMock(return_value=mock_instructions)
        
        result = await ai_engine.generate_task_instructions(task, None)
        assert result == mock_instructions
    
    @pytest.mark.asyncio
    async def test_health_analysis_edge_cases(self):
        """Test health analysis with edge cases"""
        engine = AIAnalysisEngine()
        
        # Project with no blocked tasks and no overdue tasks
        project_state = ProjectState(
            board_id="BOARD-001",
            project_name="Test",
            total_tasks=10,
            completed_tasks=5,
            in_progress_tasks=3,
            blocked_tasks=0,
            progress_percent=50.0,
            overdue_tasks=[],
            team_velocity=5.0,  # Good velocity
            risk_level=RiskLevel.LOW,
            last_updated=datetime.now()
        )
        
        result = engine._generate_fallback_health_analysis(project_state, {})
        
        assert result["overall_health"] == "green"
        assert len(result["risk_factors"]) == 0  # No risks
        assert len(result["recommendations"]) == 0  # No recommendations needed
    
    @pytest.mark.asyncio
    async def test_health_analysis_yellow_status(self):
        """Test health analysis with yellow status (medium risk)"""
        engine = AIAnalysisEngine()
        
        # Project with medium risk 
        project_state = ProjectState(
            board_id="BOARD-001",
            project_name="Test",
            total_tasks=10,
            completed_tasks=5,
            in_progress_tasks=3,
            blocked_tasks=3,  # More than 2 blocked tasks
            progress_percent=50.0,
            overdue_tasks=[],
            team_velocity=5.0,
            risk_level=RiskLevel.MEDIUM,
            last_updated=datetime.now()
        )
        
        result = engine._generate_fallback_health_analysis(project_state, {})
        
        assert result["overall_health"] == "yellow"
        assert len(result["risk_factors"]) > 0
        assert len(result["recommendations"]) > 0
    
    @pytest.mark.asyncio
    async def test_blocker_severity_mapping(self, ai_engine):
        """Test blocker analysis with different severity mappings"""
        # Test medium severity
        result = await ai_engine.analyze_blocker("TASK-001", "Database slow", "medium")
        assert result["escalation_needed"] is False
        
        # Test low severity
        result = await ai_engine.analyze_blocker("TASK-001", "Minor UI issue", "low") 
        assert result["escalation_needed"] is False
        
        # Test unknown severity (defaults to False)
        result = await ai_engine.analyze_blocker("TASK-001", "System down", "unknown")
        assert result["escalation_needed"] is False
    
    @pytest.mark.asyncio
    async def test_blocker_analysis_all_fields(self, ai_engine):
        """Test blocker analysis returns all expected fields"""
        mock_response = json.dumps({
            "root_cause": "Database connection pool exhausted",
            "resolution_steps": [
                "Check database connection settings",
                "Increase connection pool size",
                "Review query optimization"
            ],
            "estimated_resolution_time": "2-4 hours",
            "escalation_needed": False,
            "suggested_experts": ["DBA team", "Backend lead"],
            "similar_past_issues": [
                {
                    "issue": "Connection timeouts in production",
                    "resolution": "Increased pool size and added monitoring"
                }
            ]
        })
        
        ai_engine._call_claude = AsyncMock(return_value=mock_response)
        
        result = await ai_engine.analyze_blocker("TASK-001", "Database connection errors", "high")
        
        # Verify all fields are present
        assert "root_cause" in result
        assert "resolution_steps" in result
        assert "estimated_resolution_time" in result
        assert "escalation_needed" in result
        assert "suggested_experts" in result
        assert "similar_past_issues" in result
        assert len(result["resolution_steps"]) == 3
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, capsys):
        """Test successful initialization"""
        with patch('src.integrations.ai_analysis_engine_fixed.anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [Mock(text="test")]
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.Anthropic.return_value = mock_client
            
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                engine = AIAnalysisEngine()
                engine.client = mock_client
                await engine.initialize()
                
                captured = capsys.readouterr()
                assert "AI Engine connection verified" in captured.err
    
    @pytest.mark.asyncio
    async def test_initialize_no_client(self, capsys):
        """Test initialize with no client"""
        engine = AIAnalysisEngine()
        engine.client = None
        
        await engine.initialize()
        
        captured = capsys.readouterr()
        assert "AI Engine running in fallback mode" in captured.err
    
    @pytest.mark.asyncio
    async def test_initialize_connection_failure(self, capsys):
        """Test initialize when connection test fails"""
        with patch('src.integrations.ai_analysis_engine_fixed.anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_client.messages.create.side_effect = Exception("Connection failed")
            mock_anthropic.Anthropic.return_value = mock_client
            
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                engine = AIAnalysisEngine()
                engine.client = mock_client
                await engine.initialize()
                
                captured = capsys.readouterr()
                assert "AI Engine test failed" in captured.err
                assert engine.client is None
