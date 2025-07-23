#!/usr/bin/env python3
"""
Verification script to test the basic setup of the multi-agent compliance checker.
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test that all core modules can be imported."""
    print("Testing imports...")
    
    try:
        # Test base interfaces
        from compliance_checker.agents.base import BaseAgent, ComplianceCheckerAgent, ReportAssessorAgent
        from compliance_checker.processors.base import DocumentProcessor, ChainOfThoughtProcessor, ReportGenerator
        print("✓ Base interfaces imported successfully")
        
        # Test data models
        from compliance_checker.models.document import SpecificationDocument, Requirement
        from compliance_checker.models.report import ComplianceReport, ComplianceFinding, ComplianceStatus
        from compliance_checker.models.gdpr import GDPRArticle
        print("✓ Data models imported successfully")
        
        # Test configuration
        from compliance_checker.config.settings import SystemConfig
        from compliance_checker.config.manager import ConfigurationManager
        print("✓ Configuration system imported successfully")
        
        # Test exceptions
        from compliance_checker.exceptions import ComplianceCheckerError, ModelUnavailableError
        print("✓ Exception classes imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_configuration():
    """Test configuration system."""
    print("\nTesting configuration system...")
    
    try:
        from compliance_checker.config.settings import SystemConfig
        
        # Test default configuration
        config = SystemConfig()
        print(f"✓ Default config created")
        print(f"  - Ollama URL: {config.ollama.base_url}")
        print(f"  - CC Agent 1 Model: {config.ollama.cc_agent_1_model}")
        print(f"  - CC Agent 2 Model: {config.ollama.cc_agent_2_model}")
        print(f"  - RA Agent Model: {config.ollama.ra_agent_model}")
        print(f"  - Max feedback iterations: {config.agents.max_feedback_iterations}")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


def test_data_models():
    """Test data model creation."""
    print("\nTesting data models...")
    
    try:
        from compliance_checker.models.document import SpecificationDocument, Requirement
        from compliance_checker.models.report import ComplianceReport, ComplianceFinding, ComplianceStatus, SeverityLevel
        from compliance_checker.models.gdpr import GDPRArticle
        from datetime import datetime
        
        # Test document model
        doc = SpecificationDocument(
            content="Test specification content",
            metadata={"filename": "test.pdf", "author": "Test Author"},
            document_id="doc-001"
        )
        print(f"✓ SpecificationDocument created: {doc.document_id}")
        
        # Test requirement model
        req = Requirement(
            id="req-001",
            text="The system shall protect user data",
            section="Security",
            category="Data Protection"
        )
        print(f"✓ Requirement created: {req.id}")
        
        # Test GDPR article model
        article = GDPRArticle(
            article_number="6",
            title="Lawfulness of processing",
            content="Processing shall be lawful only if...",
            keywords=["lawfulness", "processing", "consent"]
        )
        print(f"✓ GDPRArticle created: {article.get_full_reference()}")
        
        # Test compliance finding
        finding = ComplianceFinding(
            requirement_id="req-001",
            requirement_text="The system shall protect user data",
            compliance_status=ComplianceStatus.NON_COMPLIANT,
            gdpr_articles=["Article 6"],
            reasoning="No explicit consent mechanism found",
            severity=SeverityLevel.HIGH
        )
        print(f"✓ ComplianceFinding created: {finding.compliance_status.value}")
        
        # Test compliance report
        report = ComplianceReport(
            agent_id="cc_agent_1",
            model_used="deepseek-r1:8b",
            findings=[finding],
            overall_assessment="Document requires GDPR compliance improvements",
            confidence_score=0.85
        )
        print(f"✓ ComplianceReport created with {len(report.findings)} findings")
        
        # Test report utility methods
        stats = report.get_summary_stats()
        print(f"  - Summary stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"✗ Data model test failed: {e}")
        return False


def test_abstract_interfaces():
    """Test that abstract interfaces work correctly."""
    print("\nTesting abstract interfaces...")
    
    try:
        from compliance_checker.agents.base import ComplianceCheckerAgent
        from compliance_checker.models.document import SpecificationDocument
        from compliance_checker.models.report import ComplianceReport
        from compliance_checker.models.gdpr import GDPRArticle
        from unittest.mock import Mock
        
        # Create a concrete implementation of ComplianceCheckerAgent
        class TestCCAgent(ComplianceCheckerAgent):
            def initialize(self):
                self.status = "ready"
                return True
            
            def get_status(self):
                return {"status": self.status, "model": self.model_name}
            
            def analyze_compliance(self, document, gdpr_context):
                # Mock implementation
                return Mock(spec=ComplianceReport)
            
            def process_feedback(self, feedback):
                print(f"Processing feedback: {feedback}")
        
        # Test the concrete implementation
        agent = TestCCAgent("deepseek-r1:8b", "test_cc_agent")
        print(f"✓ TestCCAgent created: {agent.agent_id}")
        
        # Test initialization
        result = agent.initialize()
        print(f"✓ Agent initialized: {result}")
        
        # Test status
        status = agent.get_status()
        print(f"✓ Agent status: {status}")
        
        # Test analysis (mock)
        mock_doc = Mock(spec=SpecificationDocument)
        mock_articles = [Mock(spec=GDPRArticle)]
        report = agent.analyze_compliance(mock_doc, mock_articles)
        print(f"✓ Analysis completed: {report is not None}")
        
        # Test feedback processing
        agent.process_feedback("Test feedback message")
        print("✓ Feedback processing completed")
        
        return True
        
    except Exception as e:
        print(f"✗ Abstract interface test failed: {e}")
        return False


def check_directory_structure():
    """Check that the directory structure is correct."""
    print("\nChecking directory structure...")
    
    base_path = Path(__file__).parent
    expected_dirs = [
        "agents",
        "models", 
        "processors",
        "config",
        "tests"
    ]
    
    expected_files = [
        "__init__.py",
        "exceptions.py",
        "agents/__init__.py",
        "agents/base.py",
        "models/__init__.py",
        "models/document.py",
        "models/report.py",
        "models/gdpr.py",
        "processors/__init__.py",
        "processors/base.py",
        "config/__init__.py",
        "config/settings.py",
        "config/manager.py",
        "config/config.example.yaml",
        "tests/__init__.py",
        "tests/test_base_interfaces.py",
        "tests/test_config.py"
    ]
    
    all_good = True
    
    # Check directories
    for dir_name in expected_dirs:
        dir_path = base_path / dir_name
        if dir_path.exists() and dir_path.is_dir():
            print(f"✓ Directory exists: {dir_name}/")
        else:
            print(f"✗ Directory missing: {dir_name}/")
            all_good = False
    
    # Check files
    for file_path in expected_files:
        full_path = base_path / file_path
        if full_path.exists() and full_path.is_file():
            print(f"✓ File exists: {file_path}")
        else:
            print(f"✗ File missing: {file_path}")
            all_good = False
    
    return all_good


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Multi-Agent Compliance Checker - Setup Verification")
    print("=" * 60)
    
    tests = [
        ("Directory Structure", check_directory_structure),
        ("Module Imports", test_imports),
        ("Configuration System", test_configuration),
        ("Data Models", test_data_models),
        ("Abstract Interfaces", test_abstract_interfaces)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:.<40} {status}")
        if result:
            passed += 1
    
    print(f"\nTests passed: {passed}/{len(results)}")
    
    if passed == len(results):
        print("\n🎉 All tests passed! The project structure and core interfaces are set up correctly.")
        print("\nNext steps:")
        print("- Implement GDPR knowledge base with FAISS vector storage")
        print("- Extend existing LLMClient for multi-agent support")
        print("- Create document processing pipeline")
        return True
    else:
        print(f"\n❌ {len(results) - passed} test(s) failed. Please check the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)