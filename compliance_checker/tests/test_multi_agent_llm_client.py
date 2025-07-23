"""Tests for MultiAgentLLMClient."""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import Dict, Any, List

from compliance_checker.llm.multi_agent_client import (
    MultiAgentLLMClient,
    AgentType,
    ChainOfThoughtResponse,
    AgentRequest,
    AgentResponse,
    ModelUnavailableError
)


class TestMultiAgentLLMClient:
    """Test cases for MultiAgentLLMClient."""
    
    @pytest.fixture
    def mock_ollama_server(self):
        """Mock Ollama server responses."""
        with patch('requests.Session') as mock_session:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'models': [
                    {'name': 'deepseek-r1:8b'},
                    {'name': 'gemma3:27b'},
                    {'name': 'qwq:32b'}
                ]
            }
            mock_session.return_value.get.return_value = mock_response
            mock_session.return_value.post.return_value = mock_response
            yield mock_session
    
    @pytest.fixture
    def client(self, mock_ollama_server):
        """Create MultiAgentLLMClient instance with mocked server."""
        return MultiAgentLLMClient(
            base_url="http://localhost:11434",
            timeout=30,
            max_retries=2,
            retry_delay=0.1
        )
    
    def test_initialization_success(self, mock_ollama_server):
        """Test successful client initialization."""
        client = MultiAgentLLMClient()
        assert client.base_url == "http://localhost:11434"
        assert client.timeout == 120
        assert client.max_retries == 3
        assert client.exponential_backoff is True
    
    def test_initialization_missing_models(self):
        """Test initialization failure when required models are missing."""
        with patch('requests.Session') as mock_session:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'models': []}  # No models available
            mock_session.return_value.get.return_value = mock_response
            
            with pytest.raises(ModelUnavailableError) as exc_info:
                MultiAgentLLMClient()
            
            assert "Required models not available" in str(exc_info.value)
    
    def test_get_agent_model(self, client):
        """Test getting model for different agent types."""
        assert client.get_agent_model(AgentType.CC_AGENT_1) == "deepseek-r1:8b"
        assert client.get_agent_model(AgentType.CC_AGENT_2) == "gemma3:27b"
        assert client.get_agent_model(AgentType.RA_AGENT) == "qwq:32b"
        
        # Test string input
        assert client.get_agent_model("cc_agent_1") == "deepseek-r1:8b"
        
        # Test invalid agent type
        with pytest.raises(ValueError):
            client.get_agent_model("invalid_agent")
    
    def test_verify_model_availability(self, client):
        """Test model availability verification."""
        with patch.object(client, 'list_models') as mock_list:
            mock_list.return_value = ['deepseek-r1:8b', 'gemma3:27b', 'qwq:32b']
            
            availability = client.verify_model_availability()
            
            assert availability['deepseek-r1:8b'] is True
            assert availability['gemma3:27b'] is True
            assert availability['qwq:32b'] is True
    
    def test_verify_model_availability_partial(self, client):
        """Test model availability verification with some models missing."""
        with patch.object(client, 'list_models') as mock_list:
            mock_list.return_value = ['deepseek-r1:8b']  # Only one model available
            
            availability = client.verify_model_availability()
            
            assert availability['deepseek-r1:8b'] is True
            assert availability['gemma3:27b'] is False
            assert availability['qwq:32b'] is False
    
    def test_execute_chain_of_thought_success(self, client):
        """Test successful chain-of-thought execution."""
        mock_response = {
            'response': json.dumps({
                'reasoning_steps': ['Step 1: Analyze', 'Step 2: Conclude'],
                'conclusion': 'Final conclusion',
                'confidence_score': 0.85
            })
        }
        
        with patch.object(client, '_make_request_with_backoff') as mock_request:
            mock_request.return_value = mock_response
            
            response = client.execute_chain_of_thought(
                prompt="Test prompt",
                agent_type=AgentType.CC_AGENT_1
            )
            
            assert response.success is True
            assert len(response.reasoning_steps) == 2
            assert response.conclusion == 'Final conclusion'
            assert response.confidence_score == 0.85
            assert response.model == 'deepseek-r1:8b'
    
    def test_execute_chain_of_thought_json_parse_error(self, client):
        """Test chain-of-thought execution with JSON parsing error."""
        mock_response = {
            'response': 'Invalid JSON response that cannot be parsed'
        }
        
        with patch.object(client, '_make_request_with_backoff') as mock_request:
            mock_request.return_value = mock_response
            
            response = client.execute_chain_of_thought(
                prompt="Test prompt",
                agent_type=AgentType.CC_AGENT_1
            )
            
            assert response.success is True  # Fallback parsing should succeed
            assert response.error is not None
            assert "JSON parsing failed" in response.error
            assert response.confidence_score == 0.5  # Lower confidence for fallback
    
    def test_execute_chain_of_thought_model_unavailable(self, client):
        """Test chain-of-thought execution when model is unavailable."""
        with patch.object(client, '_should_check_health') as mock_health_check:
            mock_health_check.return_value = True
            
            with patch.object(client, 'verify_model_availability') as mock_verify:
                mock_verify.return_value = {'deepseek-r1:8b': False}
                
                response = client.execute_chain_of_thought(
                    prompt="Test prompt",
                    agent_type=AgentType.CC_AGENT_1
                )
                
                assert response.success is False
                assert "not available" in response.error
    
    def test_batch_process_agents(self, client):
        """Test batch processing of agent requests."""
        requests = [
            AgentRequest(
                agent_type=AgentType.CC_AGENT_1,
                prompt="Test prompt 1",
                metadata={'test': 'data1'}
            ),
            AgentRequest(
                agent_type=AgentType.CC_AGENT_2,
                prompt="Test prompt 2",
                metadata={'test': 'data2'}
            )
        ]
        
        mock_llm_response = Mock()
        mock_llm_response.content = "Test response"
        mock_llm_response.success = True
        mock_llm_response.error = None
        
        with patch.object(client, 'generate') as mock_generate:
            mock_generate.return_value = mock_llm_response
            
            responses = client.batch_process_agents(requests)
            
            assert len(responses) == 2
            assert responses[0].agent_type == AgentType.CC_AGENT_1
            assert responses[1].agent_type == AgentType.CC_AGENT_2
            assert all(r.success for r in responses)
            assert responses[0].metadata == {'test': 'data1'}
            assert responses[1].metadata == {'test': 'data2'}
    
    def test_batch_process_agents_with_failure(self, client):
        """Test batch processing with one agent failing."""
        requests = [
            AgentRequest(
                agent_type=AgentType.CC_AGENT_1,
                prompt="Test prompt 1"
            ),
            AgentRequest(
                agent_type=AgentType.CC_AGENT_2,
                prompt="Test prompt 2"
            )
        ]
        
        def mock_generate_side_effect(*args, **kwargs):
            if kwargs.get('model') == 'deepseek-r1:8b':
                mock_response = Mock()
                mock_response.content = "Success"
                mock_response.success = True
                mock_response.error = None
                return mock_response
            else:
                raise Exception("Model error")
        
        with patch.object(client, 'generate') as mock_generate:
            mock_generate.side_effect = mock_generate_side_effect
            
            responses = client.batch_process_agents(requests)
            
            assert len(responses) == 2
            assert responses[0].success is True
            assert responses[1].success is False
            assert "Model error" in responses[1].error
    
    @pytest.mark.asyncio
    async def test_batch_process_agents_async(self, client):
        """Test asynchronous batch processing of agent requests."""
        requests = [
            AgentRequest(
                agent_type=AgentType.CC_AGENT_1,
                prompt="Test prompt 1"
            ),
            AgentRequest(
                agent_type=AgentType.CC_AGENT_2,
                prompt="Test prompt 2"
            )
        ]
        
        mock_llm_response = Mock()
        mock_llm_response.content = "Test response"
        mock_llm_response.success = True
        mock_llm_response.error = None
        
        with patch.object(client, 'generate') as mock_generate:
            mock_generate.return_value = mock_llm_response
            
            responses = await client.batch_process_agents_async(requests)
            
            assert len(responses) == 2
            assert all(r.success for r in responses)
    
    def test_make_request_with_backoff_success(self, client):
        """Test successful request with backoff."""
        mock_response = {'test': 'data'}
        
        with patch.object(client, '_make_request') as mock_request:
            mock_request.return_value = mock_response
            
            result = client._make_request_with_backoff('test', {})
            
            assert result == mock_response
            assert mock_request.call_count == 1
    
    def test_make_request_with_backoff_retry(self, client):
        """Test request with backoff and retry logic."""
        mock_response = {'test': 'data'}
        
        with patch.object(client, '_make_request') as mock_request:
            # Fail twice, then succeed
            mock_request.side_effect = [
                Exception("Network error"),
                Exception("Network error"),
                mock_response
            ]
            
            with patch('time.sleep'):  # Speed up test
                result = client._make_request_with_backoff('test', {}, max_retries=2)
            
            assert result == mock_response
            assert mock_request.call_count == 3
    
    def test_make_request_with_backoff_max_retries_exceeded(self, client):
        """Test request failing after max retries."""
        with patch.object(client, '_make_request') as mock_request:
            mock_request.side_effect = Exception("Persistent error")
            
            with patch('time.sleep'):  # Speed up test
                with pytest.raises(Exception) as exc_info:
                    client._make_request_with_backoff('test', {}, max_retries=1)
            
            assert "Persistent error" in str(exc_info.value)
            assert mock_request.call_count == 2  # Initial + 1 retry
    
    def test_extract_reasoning_fallback_numbered_steps(self, client):
        """Test fallback reasoning extraction with numbered steps."""
        raw_response = """
        1. First step of analysis
        2. Second step of reasoning
        3. Final conclusion step
        """
        
        steps = client._extract_reasoning_fallback(raw_response)
        
        assert len(steps) == 3
        assert "1. First step" in steps[0]
        assert "2. Second step" in steps[1]
        assert "3. Final conclusion" in steps[2]
    
    def test_extract_reasoning_fallback_bullet_points(self, client):
        """Test fallback reasoning extraction with bullet points."""
        raw_response = """
        - First analysis point
        - Second reasoning point
        * Third conclusion point
        """
        
        steps = client._extract_reasoning_fallback(raw_response)
        
        assert len(steps) == 3
        assert "First analysis" in steps[0]
        assert "Second reasoning" in steps[1]
        assert "Third conclusion" in steps[2]
    
    def test_extract_reasoning_fallback_sentences(self, client):
        """Test fallback reasoning extraction with sentences."""
        raw_response = "This is the first sentence. This is the second sentence. This is the third sentence."
        
        steps = client._extract_reasoning_fallback(raw_response)
        
        assert len(steps) <= 5  # Limited to 5 sentences
        assert len(steps) >= 1  # Should have at least one step
        if len(steps) >= 2:
            assert "first sentence" in steps[0]
            assert "second sentence" in steps[1]
    
    def test_get_model_health_status(self, client):
        """Test getting model health status."""
        mock_llm_response = Mock()
        mock_llm_response.success = True
        mock_llm_response.error = None
        
        with patch.object(client, 'generate') as mock_generate:
            mock_generate.return_value = mock_llm_response
            
            health_status = client.get_model_health_status()
            
            assert len(health_status) == 3  # Three models
            assert 'deepseek-r1:8b' in health_status
            assert 'gemma3:27b' in health_status
            assert 'qwq:32b' in health_status
            
            for model, status in health_status.items():
                assert status['available'] is True
                assert 'response_time' in status
                assert 'last_checked' in status
    
    def test_get_model_health_status_with_failure(self, client):
        """Test getting model health status with some models failing."""
        def mock_generate_side_effect(*args, **kwargs):
            if kwargs.get('model') == 'deepseek-r1:8b':
                mock_response = Mock()
                mock_response.success = True
                mock_response.error = None
                return mock_response
            else:
                raise Exception("Model unavailable")
        
        with patch.object(client, 'generate') as mock_generate:
            mock_generate.side_effect = mock_generate_side_effect
            
            health_status = client.get_model_health_status()
            
            assert health_status['deepseek-r1:8b']['available'] is True
            assert health_status['gemma3:27b']['available'] is False
            assert health_status['qwq:32b']['available'] is False
            assert "Model unavailable" in health_status['gemma3:27b']['error']


class TestDataClasses:
    """Test data classes used by MultiAgentLLMClient."""
    
    def test_chain_of_thought_response(self):
        """Test ChainOfThoughtResponse data class."""
        response = ChainOfThoughtResponse(
            reasoning_steps=["Step 1", "Step 2"],
            conclusion="Final conclusion",
            confidence_score=0.85,
            raw_response="Raw text",
            model="test-model",
            success=True
        )
        
        assert len(response.reasoning_steps) == 2
        assert response.conclusion == "Final conclusion"
        assert response.confidence_score == 0.85
        assert response.success is True
        assert response.error is None
    
    def test_agent_request(self):
        """Test AgentRequest data class."""
        request = AgentRequest(
            agent_type=AgentType.CC_AGENT_1,
            prompt="Test prompt",
            system_prompt="System prompt",
            temperature=0.2,
            max_tokens=1000,
            metadata={"key": "value"}
        )
        
        assert request.agent_type == AgentType.CC_AGENT_1
        assert request.prompt == "Test prompt"
        assert request.temperature == 0.2
        assert request.metadata == {"key": "value"}
    
    def test_agent_response(self):
        """Test AgentResponse data class."""
        response = AgentResponse(
            agent_type=AgentType.RA_AGENT,
            content="Response content",
            model="test-model",
            success=True,
            processing_time=1.5,
            metadata={"result": "success"}
        )
        
        assert response.agent_type == AgentType.RA_AGENT
        assert response.content == "Response content"
        assert response.processing_time == 1.5
        assert response.success is True
        assert response.error is None


class TestAgentType:
    """Test AgentType enum."""
    
    def test_agent_type_values(self):
        """Test AgentType enum values."""
        assert AgentType.CC_AGENT_1.value == "cc_agent_1"
        assert AgentType.CC_AGENT_2.value == "cc_agent_2"
        assert AgentType.RA_AGENT.value == "ra_agent"
    
    def test_agent_type_from_string(self):
        """Test creating AgentType from string."""
        assert AgentType("cc_agent_1") == AgentType.CC_AGENT_1
        assert AgentType("cc_agent_2") == AgentType.CC_AGENT_2
        assert AgentType("ra_agent") == AgentType.RA_AGENT
        
        with pytest.raises(ValueError):
            AgentType("invalid_agent")


if __name__ == "__main__":
    pytest.main([__file__])