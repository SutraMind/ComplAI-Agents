# Compliance Checker Framework

A multi-agent AI system for GDPR compliance analysis of software specification documents. The framework uses intelligent agents to analyze requirements and generate detailed compliance reports.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Components](#components)
3. [Getting Started](#getting-started)
4. [Usage Examples](#usage-examples)
5. [Configuration](#configuration)
6. [API Reference](#api-reference)
7. [Chunking & Reranking](#chunking--reranking)
8. [Testing](#testing)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Agent Orchestrator                               │
│                  (coordinates all agents)                               │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
   ┌────▼────────────┐      ┌─────▼────────────┐      ┌──────▼──────────┐
   │  CC_Agent_1     │      │  CC_Agent_2      │      │   RA_Agent      │
   │ (deepseek-r1)  │      │ (gemma3:27b)     │      │   (qwq:32b)     │
   └────┬────────────┘      └─────┬────────────┘      └──────┬──────────┘
        │                         │                         │
        └─────────────────────────┼─────────────────────────┘
                                  │
                   ┌──────────────▼──────────────┐
                   │   Multi-Agent LLM Client    │
                   │   (communicates with Ollama) │
                   └──────────────┬──────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
  ┌─────▼─────────┐       ┌──────▼────────┐       ┌───────▼─────────┐
  │GDPR Knowledge │       │Document Model │       │  Report Model  │
  │    Base       │       │               │       │                │
  │  (FAISS)     │       │               │       │                │
  └──────────────┘       └───────────────┘       └────────────────┘
```

### Agent Workflow

1. **Document Input**: Specification document is provided
2. **Requirement Extraction**: Requirements are extracted from the document
3. **CC_Agent Analysis**: Two compliance checker agents analyze requirements against GDPR
4. **Conflict Detection**: RA_Agent identifies conflicts between agent reports
5. **Conflict Resolution**: RA_Agent resolves conflicts using chain-of-thought reasoning
6. **Consolidation**: RA_Agent creates final consolidated report
7. **Feedback Loop** (optional): RA_Agent provides feedback to CC_Agents for improvement

---

## Components

### Agents

| Agent | Model | Purpose |
|-------|-------|---------|
| CC_Agent_1 | deepseek-r1:8b | Primary compliance analysis |
| CC_Agent_2 | gemma3:27b | Secondary compliance analysis |
| RA_Agent | qwq:32b | Report assessment & consolidation |

### Modules

```
compliance_checker/
├── agents/              # AI Agent implementations
│   ├── base.py         # Abstract base classes
│   ├── cc_agent.py     # Compliance Checker Agent
│   └── ra_agent.py    # Report Assessor Agent
├── knowledge/          # Knowledge management
│   └── gdpr_knowledge_base.py  # GDPR vector store (FAISS)
├── llm/               # LLM communication
│   └── multi_agent_client.py   # Multi-model LLM client
├── models/            # Data models
│   ├── document.py    # Specification document model
│   ├── report.py      # Compliance report models
│   └── gdpr.py       # GDPR article models
├── orchestration/     # Workflow coordination
│   ├── orchestrator.py  # Main orchestrator
│   ├── session.py      # Session management
│   └── progress.py     # Progress tracking
├── processors/        # Document processing
│   ├── chunking.py    # Modular chunking strategies
│   ├── reranking.py   # Reranking strategies
│   ├── rag_pipeline.py # Complete RAG pipeline
│   └── document_processor.py # Document parsing
├── config/            # Configuration
└── exceptions.py     # Custom exceptions
```

---

## Getting Started

### Prerequisites

```bash
# Python dependencies
pip install -r requirements.txt

# Services required
docker run -d --name redis -p 6379:6379 redis:latest
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password123 neo4j:latest
ollama serve
ollama pull deepseek-r1:8b
ollama pull gemma3:27b
ollama pull qwq:32b
```

### Basic Usage

```python
from compliance_checker.orchestration.orchestrator import AgentOrchestrator
from compliance_checker.llm.multi_agent_client import MultiAgentLLMClient
from compliance_checker.knowledge.gdpr_knowledge_base import GDPRKnowledgeBase
from compliance_checker.processors.document_processor import DocumentProcessor

# Initialize components
llm_client = MultiAgentLLMClient()
kb = GDPRKnowledgeBase(gdpr_docs_path="policies")
kb.build_vector_store()

# Process document
doc_processor = DocumentProcessor()
document = doc_processor.parse_specification("spec.pdf")

# Run analysis
orchestrator = AgentOrchestrator(llm_client, kb)
final_report = orchestrator.execute_compliance_analysis(document)

# View results
print(f"Status: {final_report.overall_compliance_status}")
print(f"Confidence: {final_report.confidence_score}")
print(f"Findings: {len(final_report.consolidated_findings)}")
```

---

## Usage Examples

### Example 1: Simple Compliance Analysis

```python
from compliance_checker.orchestration.orchestrator import AgentOrchestrator
from compliance_checker.llm.multi_agent_client import MultiAgentLLMClient
from compliance_checker.knowledge.gdpr_knowledge_base import GDPRKnowledgeBase

# Quick start
llm_client = MultiAgentLLMClient()
kb = GDPRKnowledgeBase(gdpr_docs_path="policies")
kb.build_vector_store()

orchestrator = AgentOrchestrator(llm_client, kb)
report = orchestrator.execute_compliance_analysis(document)

print(report.overall_assessment)
```

### Example 2: With Chunking & Reranking

```python
from compliance_checker.knowledge.gdpr_knowledge_base import GDPRKnowledgeBase

# Create KB with custom chunking and reranking
kb = GDPRKnowledgeBase(
    gdpr_docs_path="policies",
    chunking_strategy='semantic',    # or 'fixed', 'recursive', 'agentic'
    use_reranking=True,               # Enable reranking
    reranking_strategy='bm25'          # or 'cross_encoder', 'rrf'
)

# Query with reranking
articles = kb.query_relevant_articles("GDPR consent", top_k=10)
```

### Example 3: Standalone RAG Pipeline

```python
from compliance_checker.processors.rag_pipeline import create_rag_pipeline

# Create modular RAG pipeline
pipeline = create_rag_pipeline(
    chunking_strategy='agentic',
    use_reranking=True,
    reranking_strategy='cross_encoder',
    llm_client=llm_client
)

# Ingest documents
pipeline.ingest_document(requirement_text, metadata={'source': 'spec'})

# Retrieve relevant content
results = pipeline.retrieve("What are the GDPR consent requirements?")
```

### Example 4: Using Document Processor

```python
from compliance_checker.processors.document_processor import DocumentProcessor

processor = DocumentProcessor()
document = processor.parse_specification("requirements.pdf")

# Extract requirements
requirements = processor.extract_requirements(document)
print(f"Found {len(requirements)} requirements")

# Filter by category
functional = [r for r in requirements if r.category == 'functional']
data_requirements = [r for r in requirements if r.category == 'data']
```

---

## Configuration

### GDPRKnowledgeBase Configuration

```python
kb = GDPRKnowledgeBase(
    gdpr_docs_path="policies",        # Path to GDPR documents
    index_path="gdpr_index",          # Path to store FAISS index
    embedding_model="all-MiniLM-L6-v2", # Embedding model
    chunking_strategy='recursive',     # Chunking: 'fixed', 'semantic', 'recursive', 'agentic'
    use_reranking=False,               # Enable/disable reranking
    reranking_strategy='none',         # 'none', 'bm25', 'cross_encoder', 'rrf'
    llm_client=llm_client               # For agentic chunking
)
```

### Orchestrator Configuration

```python
orchestrator = AgentOrchestrator(
    llm_client=llm_client,
    gdpr_knowledge_base=kb,
    max_feedback_iterations=3,          # Max feedback loops
    concurrent_execution=True,         # Run CC_Agents in parallel
    session_timeout=3600               # 1 hour timeout
)
```

### Agent Models Configuration

```python
# In orchestrator
orchestrator.cc_agent_models = {
    "cc_agent_1": "deepseek-r1:8b",
    "cc_agent_2": "gemma3:27b"
}
orchestrator.ra_agent_model = "qwq:32b"
```

---

## API Reference

### Core Classes

#### AgentOrchestrator

```python
# Main entry point for compliance analysis
orchestrator = AgentOrchestrator(llm_client, kb)

# Execute analysis
final_report = orchestrator.execute_compliance_analysis(
    document,                    # SpecificationDocument
    session_id=None,              # Optional session ID
    progress_callback=None        # Optional progress callback
)

# Get session status
status = orchestrator.get_session_status(session_id)

# Get performance metrics
metrics = orchestrator.get_performance_metrics()
```

#### CCAgent

```python
# Compliance Checker Agent
agent = CCAgent(
    agent_id="cc_agent_1",
    model_name="deepseek-r1:8b",
    llm_client=llm_client,
    gdpr_knowledge_base=kb
)

# Analyze document
report = agent.analyze_compliance(document)

# Process feedback
agent.process_feedback("Consider Article 7 for consent requirements")
```

#### RAAgent

```python
# Report Assessor Agent
ra_agent = RAAgent(llm_client=llm_client, model_name="qwq:32b")

# Assess multiple reports
final_report = ra_agent.assess_reports([cc_report_1, cc_report_2])

# Generate feedback for CC_Agents
feedback = ra_agent.generate_feedback([cc_report_1, cc_report_2])
```

#### GDPRKnowledgeBase

```python
# Knowledge base for GDPR regulations
kb = GDPRKnowledgeBase(
    gdpr_docs_path="policies",
    chunking_strategy='semantic',
    use_reranking=True,
    reranking_strategy='bm25'
)

# Build index
kb.build_vector_store()

# Query articles
articles = kb.query_relevant_articles("consent requirements", top_k=10)

# Change strategies at runtime
kb.set_chunking_strategy('agentic')
kb.set_reranking(enabled=True, strategy='cross_encoder')

# Get statistics
stats = kb.get_statistics()
```

---

## Chunking & Reranking

### Available Chunking Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| `fixed` | Fixed-size chunks with overlap | Simple documents |
| `semantic` | Chunk by semantic boundaries | Well-structured docs |
| `recursive` | Multi-level splitting | Complex documents |
| `agentic` | LLM-powered intelligent chunking | Compliance docs |

### Available Reranking Strategies

| Strategy | Description | When to Use |
|----------|-------------|-------------|
| `none` | No reranking | Default, for speed |
| `cross_encoder` | Cross-encoder model | Best accuracy |
| `llm` | LLM-based scoring | High-quality |
| `bm25` | Keyword-based | When semantic fails |
| `rrf` | Reciprocal Rank Fusion | Multiple methods |

### Using Chunking/Reranking

```python
# Direct chunking
from compliance_checker.processors.chunking import ChunkingFactory

chunker = ChunkingFactory.create('semantic', min_chunk_size=200, max_chunk_size=1500)
chunks = chunker.chunk(document_text)

# Direct reranking
from compliance_checker.processors.reranking import RerankerFactory

reranker = RerankerFactory.create('bm25')
reranked = reranker.rerank(query, documents)

# Full pipeline
from compliance_checker.processors.rag_pipeline import create_rag_pipeline

pipeline = create_rag_pipeline(
    chunking_strategy='agentic',
    use_reranking=True,
    reranking_strategy='cross_encoder',
    llm_client=llm_client
)
```

---

## Testing

### Run Tests

```bash
# All tests
pytest compliance_checker/tests/ -v

# Specific test file
pytest compliance_checker/tests/test_cc_agent.py -v

# With coverage
pytest compliance_checker/tests/ --cov=compliance_checker --cov-report=html
```

### Test Categories

- `test_cc_agent.py` - Compliance Checker Agent tests
- `test_ra_agent.py` - Report Assessor Agent tests
- `test_agent_orchestration.py` - Orchestrator tests
- `test_gdpr_knowledge_base.py` - Knowledge base tests
- `test_document_processor.py` - Document processing tests
- `test_multi_agent_llm_client.py` - LLM client tests
- `test_config.py` - Configuration tests

### Demo Scripts

```bash
# Run demos
python demo_cc_agent.py
python demo_ra_agent.py
python demo_gdpr_knowledge_base.py
python demo_gdpr_kb_reranking.py
python demo_chunking_reranking.py
python demo_agent_orchestration.py
```

---

## Data Models

### SpecificationDocument

```python
@dataclass
class SpecificationDocument:
    content: str                    # Full document text
    requirements: List[Requirement]  # Extracted requirements
    sections: List[DocumentSection] # Document sections
    document_id: str               # Unique ID
    filename: str                  # Original filename
```

### ComplianceReport

```python
@dataclass
class ComplianceReport:
    agent_id: str                   # Which agent generated it
    model_used: str                # LLM model used
    findings: List[ComplianceFinding]  # Individual findings
    overall_assessment: str        # Summary assessment
    confidence_score: float        # Confidence (0-1)
    processing_time: float         # Time taken
```

### ComplianceFinding

```python
@dataclass
class ComplianceFinding:
    requirement_id: str             # Related requirement
    compliance_status: ComplianceStatus  # COMPLIANT, NON_COMPLIANT, etc.
    severity: SeverityLevel         # CRITICAL, HIGH, MEDIUM, LOW
    gdpr_articles: List[str]       # Referenced GDPR articles
    reasoning: str                # Detailed reasoning
    recommendations: List[str]      # Improvement suggestions
```

---

## FAQ

### Q: What models are required?
**A**: deepseek-r1:8b, gemma3:27b, and qwq:32b (all via Ollama)

### Q: Can I use different LLM providers?
**A**: Currently designed for Ollama. See ENHANCEMENT_PLAN.md for multi-provider support.

### Q: How does agentic chunking work?
**A**: The LLM analyzes document structure and identifies optimal chunk boundaries based on semantic coherence and compliance relevance.

### Q: What is the feedback loop?
**A**: If confidence is low or critical issues exist, RA_Agent generates feedback for CC_Agents to improve their analysis in subsequent iterations.

### Q: How do I add new regulations?
**A**: Add PDF/TXT files to the `policies` folder and call `kb.build_vector_store()` to update the knowledge base.

---

## Troubleshooting

### Model Not Available
```bash
# Pull required models
ollama pull deepseek-r1:8b
ollama pull gemma3:27b
ollama pull qwq:32b
```

### Knowledge Base Issues
```python
# Rebuild index
kb = GDPRKnowledgeBase(gdpr_docs_path="policies")
kb.build_vector_store()
```

### Check Setup
```bash
python compliance_checker/verify_setup.py
```

---

## License

This is part of the ComplAI Agents project.

---

*Last Updated: March 2026*
