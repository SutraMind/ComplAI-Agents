#!/usr/bin/env python3
"""
Demo script for MultiAgentLLMClient functionality.
This script demonstrates the key features of the multi-agent LLM client.
"""

import json
import asyncio
from compliance_checker.llm.multi_agent_client import (
    MultiAgentLLMClient,
    AgentType,
    AgentRequest,
    ModelUnavailableError
)


def demo_basic_functionality():
    """Demonstrate basic multi-agent client functionality."""
    print("=== Multi-Agent LLM Client Demo ===\n")
    
    try:
        # Initialize the client
        print("1. Initializing MultiAgentLLMClient...")
        client = MultiAgentLLMClient(
            base_url="http://localhost:11434",
            timeout=30,
            max_retries=2
        )
        print("✓ Client initialized successfully")
        
        # Check model availability
        print("\n2. Checking model availability...")
        availability = client.verify_model_availability()
        for model, available in availability.items():
            status = "✓ Available" if available else "✗ Not available"
            print(f"   {model}: {status}")
        
        # Test agent model mapping
        print("\n3. Testing agent model mapping...")
        for agent_type in AgentType:
            model = client.get_agent_model(agent_type)
            print(f"   {agent_type.value} -> {model}")
        
        # Test health status
        print("\n4. Getting model health status...")
        health_status = client.get_model_health_status()
        for model, status in health_status.items():
            available = "✓" if status['available'] else "✗"
            print(f"   {model}: {available} (Response time: {status.get('response_time', 'N/A')}s)")
        
        print("\n✓ Basic functionality demo completed successfully!")
        return client
        
    except ModelUnavailableError as e:
        print(f"✗ Model availability error: {e}")
        print("Please ensure Ollama is running with required models:")
        print("- deepseek-r1:8b")
        print("- gemma3:27b") 
        print("- qwq:32b")
        return None
    except Exception as e:
        print(f"✗ Error during initialization: {e}")
        return None


def demo_chain_of_thought(client):
    """Demonstrate chain-of-thought reasoning."""
    if not client:
        return
    
    print("\n=== Chain-of-Thought Reasoning Demo ===\n")
    
    compliance_prompt = """
    Analyze this software requirement for GDPR compliance:
    
    "The mobile app collects user location data continuously in the background 
    and shares it with third-party advertising partners to provide personalized ads."
    
    Consider the following GDPR aspects:
    1. Legal basis for processing personal data
    2. Consent requirements and user rights
    3. Data minimization principle
    4. Third-party data sharing regulations
    """
    
    try:
        print("Executing chain-of-thought analysis with CC_Agent_1...")
        response = client.execute_chain_of_thought(
            prompt=compliance_prompt,
            agent_type=AgentType.CC_AGENT_1,
            temperature=0.1
        )
        
        if response.success:
            print("✓ Chain-of-thought analysis completed")
            print(f"Model used: {response.model}")
            print(f"Confidence score: {response.confidence_score}")
            print("\nReasoning steps:")
            for i, step in enumerate(response.reasoning_steps, 1):
                print(f"  {i}. {step}")
            print(f"\nConclusion: {response.conclusion}")
        else:
            print(f"✗ Chain-of-thought analysis failed: {response.error}")
            
    except Exception as e:
        print(f"✗ Error during chain-of-thought analysis: {e}")


def demo_batch_processing(client):
    """Demonstrate batch processing of multiple agents."""
    if not client:
        return
    
    print("\n=== Batch Processing Demo ===\n")
    
    # Create requests for multiple agents
    specification = """
    User Authentication System:
    1. Users register with email and password
    2. System stores user credentials in database
    3. Users can reset passwords via email
    4. System logs all login attempts
    5. User data is backed up to cloud storage daily
    """
    
    requests = [
        AgentRequest(
            agent_type=AgentType.CC_AGENT_1,
            prompt=f"Analyze this specification for GDPR compliance issues: {specification}",
            system_prompt="You are a GDPR compliance expert. Focus on data protection violations.",
            metadata={'agent_name': 'CC_Agent_1', 'analysis_type': 'primary'}
        ),
        AgentRequest(
            agent_type=AgentType.CC_AGENT_2,
            prompt=f"Review this specification for GDPR compliance: {specification}",
            system_prompt="You are a GDPR compliance specialist. Identify privacy risks.",
            metadata={'agent_name': 'CC_Agent_2', 'analysis_type': 'secondary'}
        )
    ]
    
    try:
        print("Processing requests with multiple CC agents...")
        responses = client.batch_process_agents(requests)
        
        print(f"✓ Processed {len(responses)} agent requests")
        
        for i, response in enumerate(responses, 1):
            print(f"\nAgent {i} ({response.agent_type.value}):")
            print(f"  Model: {response.model}")
            print(f"  Success: {'✓' if response.success else '✗'}")
            print(f"  Processing time: {response.processing_time:.2f}s")
            if response.error:
                print(f"  Error: {response.error}")
            else:
                # Show first 200 characters of response
                content_preview = response.content[:200] + "..." if len(response.content) > 200 else response.content
                print(f"  Response preview: {content_preview}")
                
    except Exception as e:
        print(f"✗ Error during batch processing: {e}")


async def demo_async_processing(client):
    """Demonstrate asynchronous batch processing."""
    if not client:
        return
    
    print("\n=== Async Processing Demo ===\n")
    
    # Create multiple requests for concurrent processing
    requests = [
        AgentRequest(
            agent_type=AgentType.CC_AGENT_1,
            prompt=f"Quick analysis task {i}: Check if storing user emails requires consent.",
            metadata={'task_id': i}
        )
        for i in range(3)
    ]
    
    try:
        print("Processing requests asynchronously...")
        start_time = asyncio.get_event_loop().time()
        
        responses = await client.batch_process_agents_async(requests)
        
        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time
        
        print(f"✓ Processed {len(responses)} requests in {total_time:.2f}s")
        
        successful = sum(1 for r in responses if r.success)
        print(f"  Successful: {successful}/{len(responses)}")
        
        total_processing_time = sum(r.processing_time for r in responses)
        print(f"  Total processing time: {total_processing_time:.2f}s")
        print(f"  Concurrency benefit: {total_processing_time - total_time:.2f}s saved")
        
    except Exception as e:
        print(f"✗ Error during async processing: {e}")


def main():
    """Main demo function."""
    print("Multi-Agent LLM Client Demonstration")
    print("=" * 50)
    
    # Basic functionality demo
    client = demo_basic_functionality()
    
    if client:
        # Chain-of-thought demo
        demo_chain_of_thought(client)
        
        # Batch processing demo
        demo_batch_processing(client)
        
        # Async processing demo
        print("\nRunning async processing demo...")
        asyncio.run(demo_async_processing(client))
        
        print("\n" + "=" * 50)
        print("✓ All demos completed successfully!")
        print("\nThe MultiAgentLLMClient is ready for use in the compliance checker system.")
    else:
        print("\n" + "=" * 50)
        print("✗ Demo failed due to client initialization issues.")
        print("Please check Ollama server and model availability.")


if __name__ == "__main__":
    main()