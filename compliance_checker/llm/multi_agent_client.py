"""Multi-agent LLM client extending the base LLMClient for compliance checking."""

import json
import time
import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import the base LLMClient
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from memory_management.llm.client import LLMClient, LLMResponse

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Types of agents in the multi-agent system."""
    CC_AGENT_1 = "cc_agent_1"
    CC_AGENT_2 = "cc_agent_2"
    RA_AGENT = "ra_agent"


@dataclass
class ChainOfThoughtResponse:
    """Response from chain-of-thought prompting."""
    reasoning_steps: List[str]
    conclusion: str
    confidence_score: float
    raw_response: str
    model: str
    success: bool
    error: Optional[str] = None


@dataclass
class AgentRequest:
    """Request for agent processing."""
    agent_type: AgentType
    prompt: str
    system_prompt: Optional[str] = None
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AgentResponse:
    """Response from agent processing."""
    agent_type: AgentType
    content: str
    model: str
    success: bool
    processing_time: float
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ModelUnavailableError(Exception):
    """Raised when a required model is not available."""
    pass


class MultiAgentLLMClient(LLMClient):
    """Extended LLM client with multi-agent support for compliance checking."""
    
    # Agent-specific model configurations
    AGENT_MODELS = {
        AgentType.CC_AGENT_1: "deepseek-r1:8b",
        AgentType.CC_AGENT_2: "gemma3:27b", 
        AgentType.RA_AGENT: "qwq:32b"
    }
    
    # Required models for the compliance checker
    REQUIRED_MODELS = ["deepseek-r1:8b", "gemma3:27b", "qwq:32b"]
    
    def __init__(self, 
                 base_url: str = "http://localhost:11434",
                 timeout: int = 120,
                 max_retries: int = 3,
                 retry_delay: float = 1.0,
                 exponential_backoff: bool = True):
        """
        Initialize multi-agent LLM client.
        
        Args:
            base_url: Ollama server URL
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds
            exponential_backoff: Whether to use exponential backoff for retries
        """
        super().__init__(base_url, timeout, max_retries, retry_delay)
        self.exponential_backoff = exponential_backoff
        self._model_availability = {}
        self._last_health_check = 0
        self._health_check_interval = 300  # 5 minutes
        
        # Verify required models on initialization
        self._verify_required_models()
    
    def get_agent_model(self, agent_type: Union[AgentType, str]) -> str:
        """
        Get the model name for a specific agent type.
        
        Args:
            agent_type: Type of agent
            
        Returns:
            Model name for the agent
            
        Raises:
            ValueError: If agent type is not supported
        """
        if isinstance(agent_type, str):
            try:
                agent_type = AgentType(agent_type)
            except ValueError:
                raise ValueError(f"Unsupported agent type: {agent_type}")
        
        if agent_type not in self.AGENT_MODELS:
            raise ValueError(f"No model configured for agent type: {agent_type}")
        
        return self.AGENT_MODELS[agent_type]
    
    def verify_model_availability(self, models: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Verify availability of specified models or all required models.
        
        Args:
            models: List of model names to check. If None, checks all required models.
            
        Returns:
            Dictionary mapping model names to availability status
        """
        if models is None:
            models = self.REQUIRED_MODELS
        
        availability = {}
        
        try:
            available_models = self.list_models()
            for model in models:
                availability[model] = model in available_models
                
            # Cache the results
            self._model_availability.update(availability)
            self._last_health_check = time.time()
            
        except Exception as e:
            logger.error(f"Failed to verify model availability: {str(e)}")
            # Return cached results if available, otherwise assume unavailable
            for model in models:
                availability[model] = self._model_availability.get(model, False)
        
        return availability
    
    def _verify_required_models(self) -> None:
        """
        Verify that all required models are available.
        
        Raises:
            ModelUnavailableError: If any required model is unavailable
        """
        availability = self.verify_model_availability()
        unavailable_models = [model for model, available in availability.items() if not available]
        
        if unavailable_models:
            raise ModelUnavailableError(
                f"Required models not available: {unavailable_models}. "
                f"Please ensure these models are installed in Ollama."
            )
    
    def _should_check_health(self) -> bool:
        """Check if it's time to perform a health check."""
        return time.time() - self._last_health_check > self._health_check_interval
    
    def _make_request_with_backoff(self, endpoint: str, data: Dict[str, Any], 
                                  max_retries: Optional[int] = None) -> Dict[str, Any]:
        """
        Make HTTP request with exponential backoff retry logic.
        
        Args:
            endpoint: API endpoint
            data: Request payload
            max_retries: Override default max retries
            
        Returns:
            Response data
            
        Raises:
            requests.RequestException: On API communication failure after all retries
        """
        if max_retries is None:
            max_retries = self.max_retries
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return self._make_request(endpoint, data)
            except Exception as e:
                last_exception = e
                
                if attempt < max_retries:
                    if self.exponential_backoff:
                        delay = self.retry_delay * (2 ** attempt)
                    else:
                        delay = self.retry_delay
                    
                    logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries + 1}), "
                                 f"retrying in {delay}s: {str(e)}")
                    time.sleep(delay)
                else:
                    logger.error(f"Request failed after {max_retries + 1} attempts")
        
        raise last_exception
    
    def execute_chain_of_thought(self, 
                                prompt: str, 
                                agent_type: Union[AgentType, str],
                                system_prompt: Optional[str] = None,
                                temperature: float = 0.1) -> ChainOfThoughtResponse:
        """
        Execute chain-of-thought prompting for structured reasoning.
        
        Args:
            prompt: Input prompt for reasoning
            agent_type: Type of agent to use
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            
        Returns:
            ChainOfThoughtResponse with reasoning steps and conclusion
        """
        if isinstance(agent_type, str):
            agent_type = AgentType(agent_type)
        
        model = self.get_agent_model(agent_type)
        
        # Check model availability if needed
        if self._should_check_health():
            availability = self.verify_model_availability([model])
            if not availability.get(model, False):
                return ChainOfThoughtResponse(
                    reasoning_steps=[],
                    conclusion="",
                    confidence_score=0.0,
                    raw_response="",
                    model=model,
                    success=False,
                    error=f"Model {model} is not available"
                )
        
        # Construct chain-of-thought prompt
        cot_prompt = f"""Think through this step by step using chain-of-thought reasoning.

{prompt}

Please structure your response as follows:
1. Break down the problem into reasoning steps
2. Work through each step systematically
3. Provide a clear conclusion
4. Include a confidence score (0.0 to 1.0)

Format your response as JSON:
{{
    "reasoning_steps": ["step 1", "step 2", "step 3", ...],
    "conclusion": "your final conclusion",
    "confidence_score": 0.85
}}"""
        
        if not system_prompt:
            system_prompt = ("You are an expert analyst. Use systematic chain-of-thought reasoning "
                           "to analyze problems step by step. Always respond with valid JSON.")
        
        try:
            start_time = time.time()
            
            # Use the enhanced request method with backoff
            data = {
                'model': model,
                'prompt': cot_prompt,
                'system': system_prompt,
                'stream': False,
                'options': {
                    'temperature': temperature,
                }
            }
            
            response_data = self._make_request_with_backoff('api/generate', data)
            processing_time = time.time() - start_time
            
            raw_response = response_data.get('response', '')
            
            # Parse the JSON response
            try:
                cleaned_response = self._clean_llm_response(raw_response)
                parsed_response = json.loads(cleaned_response)
                
                return ChainOfThoughtResponse(
                    reasoning_steps=parsed_response.get('reasoning_steps', []),
                    conclusion=parsed_response.get('conclusion', ''),
                    confidence_score=float(parsed_response.get('confidence_score', 0.0)),
                    raw_response=raw_response,
                    model=model,
                    success=True
                )
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Failed to parse chain-of-thought response: {str(e)}")
                logger.error(f"Raw response: {raw_response}")
                
                # Fallback: extract reasoning from raw text
                reasoning_steps = self._extract_reasoning_fallback(raw_response)
                
                return ChainOfThoughtResponse(
                    reasoning_steps=reasoning_steps,
                    conclusion=raw_response.split('\n')[-1] if raw_response else "",
                    confidence_score=0.5,  # Lower confidence for fallback parsing
                    raw_response=raw_response,
                    model=model,
                    success=True,
                    error=f"JSON parsing failed, used fallback: {str(e)}"
                )
                
        except Exception as e:
            logger.error(f"Chain-of-thought execution failed: {str(e)}")
            return ChainOfThoughtResponse(
                reasoning_steps=[],
                conclusion="",
                confidence_score=0.0,
                raw_response="",
                model=model,
                success=False,
                error=str(e)
            )
    
    def batch_process_agents(self, requests: List[AgentRequest]) -> List[AgentResponse]:
        """
        Process multiple agent requests concurrently.
        
        Args:
            requests: List of agent requests to process
            
        Returns:
            List of agent responses
        """
        responses = []
        
        for request in requests:
            start_time = time.time()
            
            try:
                model = self.get_agent_model(request.agent_type)
                
                # Execute the request
                llm_response = self.generate(
                    prompt=request.prompt,
                    model=model,
                    system_prompt=request.system_prompt,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                )
                
                processing_time = time.time() - start_time
                
                response = AgentResponse(
                    agent_type=request.agent_type,
                    content=llm_response.content,
                    model=model,
                    success=llm_response.success,
                    processing_time=processing_time,
                    error=llm_response.error,
                    metadata=request.metadata
                )
                
            except Exception as e:
                processing_time = time.time() - start_time
                logger.error(f"Agent request failed for {request.agent_type}: {str(e)}")
                
                response = AgentResponse(
                    agent_type=request.agent_type,
                    content="",
                    model="",
                    success=False,
                    processing_time=processing_time,
                    error=str(e),
                    metadata=request.metadata
                )
            
            responses.append(response)
        
        return responses
    
    async def batch_process_agents_async(self, requests: List[AgentRequest]) -> List[AgentResponse]:
        """
        Process multiple agent requests asynchronously.
        
        Args:
            requests: List of agent requests to process
            
        Returns:
            List of agent responses
        """
        async def process_single_request(request: AgentRequest) -> AgentResponse:
            """Process a single agent request asynchronously."""
            loop = asyncio.get_event_loop()
            
            def sync_process():
                start_time = time.time()
                try:
                    model = self.get_agent_model(request.agent_type)
                    
                    llm_response = self.generate(
                        prompt=request.prompt,
                        model=model,
                        system_prompt=request.system_prompt,
                        temperature=request.temperature,
                        max_tokens=request.max_tokens
                    )
                    
                    processing_time = time.time() - start_time
                    
                    return AgentResponse(
                        agent_type=request.agent_type,
                        content=llm_response.content,
                        model=model,
                        success=llm_response.success,
                        processing_time=processing_time,
                        error=llm_response.error,
                        metadata=request.metadata
                    )
                    
                except Exception as e:
                    processing_time = time.time() - start_time
                    logger.error(f"Async agent request failed for {request.agent_type}: {str(e)}")
                    
                    return AgentResponse(
                        agent_type=request.agent_type,
                        content="",
                        model="",
                        success=False,
                        processing_time=processing_time,
                        error=str(e),
                        metadata=request.metadata
                    )
            
            return await loop.run_in_executor(None, sync_process)
        
        # Process all requests concurrently
        tasks = [process_single_request(request) for request in requests]
        return await asyncio.gather(*tasks)
    
    def _extract_reasoning_fallback(self, raw_response: str) -> List[str]:
        """
        Extract reasoning steps from raw text as fallback when JSON parsing fails.
        
        Args:
            raw_response: Raw LLM response text
            
        Returns:
            List of reasoning steps extracted from text
        """
        if not raw_response:
            return []
        
        # Look for numbered steps or bullet points
        lines = raw_response.split('\n')
        reasoning_steps = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for numbered steps (1., 2., etc.)
            if any(line.startswith(f"{i}.") for i in range(1, 20)):
                reasoning_steps.append(line)
            # Check for bullet points
            elif line.startswith(('- ', '* ', '• ')):
                reasoning_steps.append(line)
            # Check for step indicators
            elif any(keyword in line.lower() for keyword in ['step', 'first', 'second', 'third', 'then', 'next', 'finally']):
                reasoning_steps.append(line)
        
        # If no structured steps found, split into sentences
        if not reasoning_steps:
            sentences = [s.strip() for s in raw_response.split('.') if s.strip()]
            reasoning_steps = sentences[:5]  # Limit to first 5 sentences
        
        return reasoning_steps
    
    def get_model_health_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive health status for all agent models.
        
        Returns:
            Dictionary with health status for each model
        """
        health_status = {}
        
        for agent_type, model in self.AGENT_MODELS.items():
            try:
                # Test model with a simple prompt
                start_time = time.time()
                response = self.generate(
                    prompt="Test prompt for health check",
                    model=model,
                    temperature=0.1
                )
                response_time = time.time() - start_time
                
                health_status[model] = {
                    'agent_type': agent_type.value,
                    'available': response.success,
                    'response_time': response_time,
                    'error': response.error,
                    'last_checked': time.time()
                }
                
            except Exception as e:
                health_status[model] = {
                    'agent_type': agent_type.value,
                    'available': False,
                    'response_time': None,
                    'error': str(e),
                    'last_checked': time.time()
                }
        
        return health_status