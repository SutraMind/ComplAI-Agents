# 🧠 Compliance Memory Management Module

A sophisticated AI-powered system that extracts, stores, and manages knowledge from compliance assessment interactions. The system processes compliance reports and human expert feedback to build both **Short-Term Memory (STM)** for detailed case files and **Long-Term Memory (LTM)** for generalized compliance rules.

## 🎯 Overview

The Compliance Memory Management Module enables organizations to:

- 📝 **Extract structured data** from compliance reports and human feedback
- 🗄️ **Store detailed case files** in Redis (Short-Term Memory)
- 🧠 **Generate reusable compliance rules** in Neo4j (Long-Term Memory)
- 🔗 **Maintain full traceability** between assessments and rules
- 📊 **Provide APIs** for integration with compliance systems
- 🎯 **Learn from expert corrections** to improve future assessments

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐
│ Compliance      │    │ Human Feedback  │
│ Report          │    │                 │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          └──────┬─────────────┬─┘
                 │             │
         ┌───────▼─────────────▼───────┐
         │   Memory Extractor          │
         │   (Main Orchestrator)       │
         └─────────────┬───────────────┘
                       │
         ┌─────────────┼───────────────┐
         │             │               │
    ┌────▼────┐   ┌────▼────┐   ┌─────▼─────┐
    │   STM   │   │   LTM   │   │   Rule    │
    │Processor│   │ Manager │   │Extractor  │
    └────┬────┘   └────┬────┘   └───────────┘
         │             │
    ┌────▼────┐   ┌────▼────┐
    │  Redis  │   │ Neo4j   │
    │  (STM)  │   │ (LTM)   │
    └─────────┘   └─────────┘
```

## 🔧 Prerequisites

### System Requirements
- **Python 3.8+**
- **Docker** (for Redis and Neo4j)
- **8GB RAM** minimum
- **Windows/Linux/macOS**

### Required Services
- **Redis** (Short-Term Memory storage)
- **Neo4j** (Long-Term Memory storage)
- **Ollama** (LLM for text processing)

## 🚀 Installation Guide

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd compliance-memory-management
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Set Up Ollama (LLM Service)

#### Windows:
```powershell
# Download and install Ollama from: https://ollama.ai
# Then pull the required model:
ollama pull deepseek-r1:8b
```

#### Linux/macOS:
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the required model
ollama pull deepseek-r1:8b
```

### Step 4: Set Up Redis (Short-Term Memory)

```bash
# Using Docker (Recommended)
docker run -d --name redis-memory -p 6379:6379 redis:latest
```

### Step 5: Set Up Neo4j (Long-Term Memory)

```bash
# Using Docker (Recommended)
docker run -d --name neo4j-memory -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password123 -v neo4j_data:/data neo4j:latest
```

**Wait 30-60 seconds** for Neo4j to fully start.

### Step 6: Verify Installation

```bash
# Run the setup verification script
python verify_setup.py
```

You should see all green checkmarks (✅) for:
- Environment Configuration
- Python Dependencies  
- Ollama LLM Service
- Redis Database
- Neo4j Database

## 📋 Configuration

The system uses environment variables defined in `.env`. Key settings:

```env
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Neo4j Configuration  
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password123

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=deepseek-r1:8b
```

## 🎮 Usage

### Quick Start

1. **Prepare your input files:**
   - `Compliance_report_ra_agent.txt` - Your compliance assessment report
   - `human_feedback.txt` - Expert feedback on the assessment

2. **Run the memory extraction:**
   ```bash
   python demo_memory_extractor_fixed.py
   ```

3. **View the results:**
   - Console output shows processing statistics
   - `memory_extraction_results_fixed.json` contains detailed results
   - Redis contains STM entries (detailed case files)
   - Neo4j contains LTM rules (generalized compliance knowledge)

### Expected Output

```
🧠 Compliance Memory Management Module - Fixed Demo
============================================================

🔍 CHECKING INPUT FILES
✅ Found: Compliance_report_ra_agent.txt
✅ Found: human_feedback.txt

🚀 INITIALIZING MEMORY EXTRACTOR
✅ Memory extractor initialized successfully

⚙️ EXTRACTING MEMORY FROM FILES
⏱️ Extraction completed in X.XX seconds

📊 EXTRACTION RESULTS
✅ Extraction successful!

📈 Statistics:
   Success Rate: XX.X%
   STM Entries Created: X
   LTM Rules Created: X
   Entries with Feedback: X

📝 Short-Term Memory Entries (X):
   1. ecommerce_r1_consent
      Status: Non-Compliant
      Requirement: During account signup...

🧠 Long-Term Memory Rules (X):
   1. GDPR_Consent_Granular_01
      Confidence: 0.95
      Rule: For GDPR Article 7 compliance...
```

## 🔍 Exploring Results

### View Redis Entries (STM)
```bash
# View all STM entries
python view_redis_entries.py

# Or use Redis CLI
docker exec -it redis-memory redis-cli
KEYS *
GET ecommerce_r1_consent
```

### View Neo4j Entries (LTM)
1. Open Neo4j Browser: http://localhost:7474
2. Login: `neo4j` / `password123`
3. Run queries:
   ```cypher
   // View all LTM rules
   MATCH (r:Rule) RETURN r LIMIT 10
   
   // View rules with concepts
   MATCH (r:Rule)-[:RELATES_TO]->(c:Concept) 
   RETURN r.rule_id, r.rule_text, collect(c.name) as concepts
   ```

### View Complete Results
```bash
# View the detailed JSON results
notepad memory_extraction_results_fixed.json
```

## 📊 Input File Formats

### Compliance Report Format
```
## FINAL COMPLIANCE ASSESSMENT REPORT (RA_Agent) ##

**Project:** Your Project Name
**Governing Policy:** GDPR
**Status:** X Non-Compliant, Y Compliant Requirements Identified.

---
**Requirement R1:** [Requirement description]
*   **Status:** [Compliant/Non-Compliant/Partially Compliant]
*   **Rationale:** [Detailed reasoning]
*   **Recommendation:** [Suggested actions]
```

### Human Feedback Format
```
## HUMAN EXPERT FEEDBACK ##

**Reviewer:** [Expert Name]
**Date:** [Date]

**Feedback on R1 ([Topic]):**
*   **Decision:** [No change/Change status/etc.]
*   **Rationale:** [Expert reasoning]
*   **Suggestion:** [Expert recommendations]
```

## 🧪 Testing

### Run Comprehensive Tests
```bash
# Run all tests with mocked components
python -m pytest test_comprehensive_mocked.py -v

# Run specific test categories
python -m pytest test_comprehensive_mocked.py::TestRequirementsValidationMocked -v
```

### Run Performance Tests
```bash
python -m pytest test_performance_optimizations.py -v
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Neo4j Authentication Error
```
Error: {code: Neo.ClientError.Security.Unauthorized}
```
**Solution:**
```bash
# Recreate Neo4j container with correct password
docker stop neo4j-memory && docker rm neo4j-memory
docker run -d --name neo4j-memory -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password123 neo4j:latest
```

#### 2. Redis Connection Error
```
Error: Client sent AUTH, but no password is set
```
**Solution:** Ensure `REDIS_PASSWORD=` (empty) in your `.env` file.

#### 3. Ollama Model Not Found
```
Error: Model 'deepseek-r1:8b' not found
```
**Solution:**
```bash
ollama pull deepseek-r1:8b
```

#### 4. Low Processing Success Rate
If you see success rates below 80%, check that your input files follow the expected format and contain complete data for each requirement.

### Debug Scripts

```bash
# Test individual components
python debug_memory_extractor.py

# Test database connections
python test_neo4j_auth.py

# Verify complete setup
python verify_setup.py
```

## 📚 API Usage

The system provides REST APIs for integration:

```python
from memory_management.api.memory_api import MemoryAPI

api = MemoryAPI()

# Get STM entry
response = api.get_stm_entry("ecommerce_r1_consent")

# Search LTM rules
response = api.search_ltm_rules("GDPR", ["Consent", "Privacy"])

# Add new assessment
response = api.add_new_assessment({
    "scenario_id": "new_scenario_001",
    "requirement_text": "New requirement...",
    "initial_assessment": {
        "status": "Non-Compliant",
        "rationale": "Reasoning...",
        "recommendation": "Actions..."
    }
})
```

## 🏗️ Architecture Details

### Components

- **Memory Extractor**: Main orchestrator for the extraction workflow
- **STM Processor**: Manages short-term memory entries in Redis
- **LTM Manager**: Manages long-term memory rules in Neo4j
- **Rule Extractor**: Generates reusable rules from human feedback
- **Parsers**: Extract structured data from text files
- **API Layer**: Provides REST endpoints for system integration

### Data Models

#### STM Entry (Redis)
```json
{
  "scenario_id": "ecommerce_r1_consent",
  "requirement_text": "During account signup...",
  "initial_assessment": {
    "status": "Non-Compliant",
    "rationale": "Bundled consent violates...",
    "recommendation": "Implement separate..."
  },
  "human_feedback": {
    "decision": "No change",
    "rationale": "Agent's analysis is correct...",
    "suggestion": "Implement granular consent..."
  },
  "final_status": "Non-Compliant"
}
```

#### LTM Rule (Neo4j)
```json
{
  "rule_id": "GDPR_Consent_Granular_01",
  "rule_text": "For GDPR Article 7 compliance...",
  "related_concepts": ["Consent", "GDPR Article 7", "Data Processing"],
  "source_scenario_id": ["ecommerce_r1_consent"],
  "confidence_score": 0.95
}
```

## 📈 Performance

The system is optimized for:
- **STM Operations**: Sub-second response times
- **LTM Search**: Complex graph queries under 500ms
- **Concurrent Access**: Handles multiple simultaneous operations
- **Memory Efficiency**: Optimized connection pooling and caching

## 🔒 Security

- Database connections use authentication
- API endpoints support rate limiting
- Sensitive data is properly encrypted
- Audit trails maintain compliance history

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Run debug scripts to identify issues
3. Create an issue on GitHub with:
   - Error messages
   - System information
   - Steps to reproduce

## 🎯 Roadmap

- [ ] Web-based dashboard for memory exploration
- [ ] Support for additional compliance frameworks
- [ ] Advanced analytics and reporting
- [ ] Integration with popular compliance tools
- [ ] Machine learning-based rule optimization

---

**🚀 Ready to get started?** Run `python verify_setup.py` to check your installation, then `python demo_memory_extractor_fixed.py` to process your first compliance memory extraction!