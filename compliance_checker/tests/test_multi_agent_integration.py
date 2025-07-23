"""Integration tests for MultiAgentLLMClient with existing system."""

import pytest
import json
import asyncio
from unittest.mock import Mock, patch, MagicMock

from compliance_checker.llm.multi_agent_client import (
    MultiAgentLLMClient,
    AgentType,
    AgentRequest,
    ModelUnavailableError
)


class TestMultiAgentIntegration:
    """Integration tests for multi-agent LLM client."""
    
    @pytest.fixture
    def mock_ollama_healthy(self):
        """Mock a healthy Ollama server with all required models."""
        with patch('requests.Session') as mock_session:
            # Mock successful health check
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'models': [
                    {'name': 'deepseek-r1:8b'},
                    {'name': 'gemma3:27b'},
                    {'name': 'qwq:32b'}
                ]
            }
            mock_response.raise_for_status.return_value = None
            
            # Mock successful generation
            mock_generate_response = Mock()
            mock_generate_response.status_code = 200
            mock_generate_response.json.return_value = {
                'response': 'Test response from model',
                'eval_count': 50
            }
            mock_generate_response.raise_for_status.return_value = None
            
            mock_session_instance = Mock()
            mock_session_instance.get.return_value = mock_response
            mock_session_instance.post.return_value = mock_generate_response
            mock_session.return_value = mock_session_instance
            
            yield mock_session
    
    @pytest.fixture
    def client(self, mock_ollama_healthy):
        """Create a MultiAgentLLMClient with mocked healthy server."""
        return MultiAgentLLMClient(
            base_url="http://localhost:11434",
            timeout=30,
            max_retries=2
        )
    
    def test_full_compliance_analysis_workflow(self, client):
        """Test complete compliance analysis workflow with multiple agents."""
        # Simulate a compliance analysis scenario
        specification_text = """
        User Registration System:
        1. Users must provide email and password
        2. System stores user data in database
        3. Users can delete their accounts
        4. System sends marketing emails to users
        """
        
        # Create requests for both CC agents
        cc_requests = [
            AgentRequest(
                agent_type=AgentType.CC_AGENT_1,
                prompt=f"Analyze this specification for GDPR compliance: {specification_text}",
                system_prompt="You are a GDPR compliance expert. Analyze the specification and identify any compliance issues.",
                metadata={'document_id': 'test_spec_001'}
            ),
            AgentRequest(
                agent_type=AgentType.CC_AGENT_2,
                prompt=f"Analyze this specification for GDPR compliance: {specification_text}",
                system_prompt="You are a GDPR compliance expert. Analyze the specification and identify any compliance issues.",
                metadata={'document_id': 'test_spec_001'}
            )
        ]
        
        # Mock different responses from each agent
        def mock_generate_side_effect(*args, **kwargs):
            mock_response = Mock()
            mock_response.success = True
            mock_response.error = None
            
            if kwargs.get('model') == 'deepseek-r1:8b':
                mock_response.content = json.dumps({
                    'findings': [
                        {
                            'requirement': 'Marketing emails',
                            'compliance_status': 'non_compliant',
                            'reason': 'No explicit consent mechanism for marketing emails'
                        }
                    ],
                    'overall_assessment': 'Partially compliant'
                })
            elif kwargs.get('model') == 'gemma3:27b':
                mock_response.content = json.dumps({
                    'findings': [
                        {
                            'requirement': 'Data storage',
                            'compliance_status': 'unclear',
                            'reason': 'No data retention policy specified'
                        },
                        {
                            'requirement': 'Account deletion',
                            'compliance_status': 'compliant',
                            'reason': 'Right to erasure is implemented'
                        }
                    ],
                    'overall_assessment': 'Needs improvement'
                })
            else:
                mock_response.content = "RA Agent consolidation response"
            
            return mock_response
        
        with patch.object(client, 'generate') as mock_generate:
            mock_generate.side_effect = mock_generate_side_effect
            
            # Process CC agent requests
            cc_responses = client.batch_process_agents(cc_requests)
            
            assert len(cc_responses) == 2
            assert all(response.success for response in cc_responses)
            assert cc_responses[0].agent_type == AgentType.CC_AGENT_1
            assert cc_responses[1].agent_type == AgentType.CC_AGENT_2
            
            # Verify different models were used
            assert mock_generate.call_count == 2
            calls = mock_generate.call_args_list
            models_used = [call[1]['model'] for call in calls]
            assert 'deepseek-r1:8b' in models_used
            assert 'gemma3:27b' in models_used
            
            # Create RA agent request to consolidate reports
            ra_request = AgentRequest(
                agent_type=AgentType.RA_AGENT,
                prompt=f"Consolidate these compliance reports: {cc_responses[0].content} and {cc_responses[1].content}",
                system_prompt="You are a report assessor. Consolidate the findings from multiple compliance reports.",
                metadata={'consolidation_task': True}
            )
            
            # Process RA agent request
            ra_responses = client.batch_process_agents([ra_request])
            
            assert len(ra_responses) == 1
            assert ra_responses[0].success
            assert ra_responses[0].agent_type == AgentType.RA_AGENT
    
    def test_chain_of_thought_compliance_analysis(self, client):
        """Test chain-of-thought reasoning for compliance analysis."""
        compliance_prompt = """
        Analyze this requirement for GDPR compliance:
        "The system automatically sends promotional emails to all registered users."
        
        Consider:
        1. Legal basis for processing
        2. Consent requirements
        3. Right to object
        4. Data minimization
        """
        
        # Mock chain-of-thought response
        mock_cot_response = {
            'response': json.dumps({
                'reasoning_steps': [
                    'Step 1: Identify the data processing activity - sending promotional emails',
                    'Step 2: Determine legal basis - likely requires consent under Article 6(1)(a)',
                    'Step 3: Check consent requirements - must be freely given, specific, informed',
                    'Step 4: Consider right to object - users must be able to opt-out easily',
                    'Step 5: Evaluate data minimization - only necessary data should be used'
                ],
                'conclusion': 'Non-compliant: Automatic promotional emails without explicit consent violate GDPR',
                'confidence_score': 0.9
            })
        }
        
        with patch.object(client, '_make_request_with_backoff') as mock_request:
            mock_request.return_value = mock_cot_response
            
            response = client.execute_chain_of_thought(
                prompt=compliance_prompt,
                agent_type=AgentType.CC_AGENT_1
            )
            
            assert response.success
            assert len(response.reasoning_steps) == 5
            assert 'Non-compliant' in response.conclusion
            assert response.confidence_score == 0.9
            assert response.model == 'deepseek-r1:8b'
    
    def test_error_handling_and_recovery(self, client):
        """Test error handling and recovery mechanisms."""
        # Test model unavailability
        with patch.object(client, 'verify_model_availability') as mock_verify:
            with patch.object(client, '_should_check_health') as mock_health_check:
                mock_health_check.return_value = True
                mock_verify.return_value = {
                    'deepseek-r1:8b': False,
                    'gemma3:27b': True,
                    'qwq:32b': True
                }
                
                # Chain-of-thought should fail for unavailable model
                response = client.execute_chain_of_thought(
                    prompt="Test prompt",
                    agent_type=AgentType.CC_AGENT_1
                )
                
                assert not response.success
                assert "not available" in response.error
        
        # Test retry mechanism
        with patch.object(client, '_make_request') as mock_request:
            # Simulate network errors followed by success
            mock_request.side_effect = [
                Exception("Connection timeout"),
                Exception("Server error"),
                {'response': 'Success after retries'}
            ]
            
            with patch('time.sleep'):  # Speed up test
                result = client._make_request_with_backoff('api/generate', {})
            
            assert result == {'response': 'Success after retries'}
            assert mock_request.call_count == 3
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_processing(self, client):
        """Test concurrent processing of multiple agents."""
        # Create multiple requests for concurrent processing
        requests = [
            AgentRequest(
                agent_type=AgentType.CC_AGENT_1,
                prompt=f"Analyze requirement {i}",
                metadata={'req_id': i}
            )
            for i in range(5)
        ]
        
        mock_response = Mock()
        mock_response.success = True
        mock_response.content = "Analysis complete"
        mock_response.error = None
        
        with patch.object(client, 'generate') as mock_generate:
            mock_generate.return_value = mock_response
            
            start_time = asyncio.get_event_loop().time()
            responses = await client.batch_process_agents_async(requests)
            end_time = asyncio.get_event_loop().time()
            
            # Verify all requests were processed
            assert len(responses) == 5
            assert all(r.success for r in responses)
            
            # Verify concurrent execution (should be faster than sequential)
            processing_time = end_time - start_time
            assert processing_time < 5.0  # Should complete quickly with mocking
    
    def test_model_health_monitoring(self, client):
        """Test model health monitoring functionality."""
        # Mock successful health checks for all models
        mock_responses = {
            'deepseek-r1:8b': Mock(success=True, error=None),
            'gemma3:27b': Mock(success=True, error=None),
            'qwq:32b': Mock(success=False, error="Model timeout")
        }
        
        def mock_generate_side_effect(*args, **kwargs):
            model = kwargs.get('model')
            return mock_responses.get(model, Mock(success=False, error="Unknown model"))
        
        with patch.object(client, 'generate') as mock_generate:
            mock_generate.side_effect = mock_generate_side_effect
            
            health_status = client.get_model_health_status()
            
            assert len(health_status) == 3
            assert health_status['deepseek-r1:8b']['available'] is True
            assert health_status['gemma3:27b']['available'] is True
            assert health_status['qwq:32b']['available'] is False
            assert "Model timeout" in health_status['qwq:32b']['error']
    
    def test_exponential_backoff_timing(self, client):
        """Test exponential backoff timing behavior."""
        # Set client retry delay for testing
        client.retry_delay = 0.1
        
        with patch.object(client, '_make_request') as mock_request:
            mock_request.side_effect = [
                Exception("Error 1"),
                Exception("Error 2"),
                {'response': 'Success'}
            ]
            
            with patch('time.sleep') as mock_sleep:
                client._make_request_with_backoff('test', {}, max_retries=2)
                
                # Verify exponential backoff delays
                sleep_calls = mock_sleep.call_args_list
                assert len(sleep_calls) == 2
                
                # First retry: 0.1s (base delay)
                assert sleep_calls[0][0][0] == 0.1
                # Second retry: 0.2s (2 * base delay)
                assert sleep_calls[1][0][0] == 0.2
    
    def test_integration_with_existing_llm_client(self, client):
        """Test that MultiAgentLLMClient maintains compatibility with base LLMClient."""
        # Test that base methods still work
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': 'Base client response',
            'eval_count': 25
        }
        mock_response.raise_for_status.return_value = None
        
        with patch.object(client.session, 'post') as mock_post:
            mock_post.return_value = mock_response
            
            # Test base generate method
            response = client.generate(
                prompt="Test prompt",
                model="deepseek-r1:8b"
            )
            
            assert response.success
            assert response.content == 'Base client response'
            assert response.model == 'deepseek-r1:8b'
            
            # Test structured data extraction
            schema = {'findings': [], 'assessment': ''}
            response = client.extract_structured_data(
                prompt="Extract compliance data",
                expected_schema=schema,
                model="gemma3:27b"
            )
            
            # Should work with base functionality
            assert mock_post.call_count >= 1


class TestModelConfiguration:
    """Test model configuration and mapping."""
    
    def test_agent_model_mapping(self):
        """Test that agent types map to correct models."""
        expected_mapping = {
            AgentType.CC_AGENT_1: "deepseek-r1:8b",
            AgentType.CC_AGENT_2: "gemma3:27b",
            AgentType.RA_AGENT: "qwq:32b"
        }
        
        assert MultiAgentLLMClient.AGENT_MODELS == expected_mapping
    
    def test_required_models_list(self):
        """Test that all required models are listed."""
        expected_models = ["deepseek-r1:8b", "gemma3:27b", "qwq:32b"]
        assert set(MultiAgentLLMClient.REQUIRED_MODELS) == set(expected_models)
    
    def test_model_verification_on_init(self):
        """Test that model verification happens during initialization."""
        with patch('requests.Session') as mock_session:
            # Mock missing models
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'models': [{'name': 'deepseek-r1:8b'}]  # Missing other models
            }
            mock_session.return_value.get.return_value = mock_response
            
            with pytest.raises(ModelUnavailableError) as exc_info:
                MultiAgentLLMClient()
            
            error_message = str(exc_info.value)
            assert "gemma3:27b" in error_message
            assert "qwq:32b" in error_message


if __name__ == "__main__":
    pytest.main([__file__])