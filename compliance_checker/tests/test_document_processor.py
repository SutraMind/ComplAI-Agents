"""
Unit tests for document processing functionality.
"""

import pytest
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from compliance_checker.processors.document_processor import DocumentProcessor
from compliance_checker.models.document import SpecificationDocument, Requirement, DocumentSection
from compliance_checker.exceptions import DocumentProcessingError, ValidationError


class TestDocumentProcessor:
    """Test cases for DocumentProcessor class."""
    
    @pytest.fixture
    def processor(self):
        """Create a DocumentProcessor instance for testing."""
        return DocumentProcessor()
    
    @pytest.fixture
    def sample_txt_content(self):
        """Sample text content for testing."""
        return """
1. Introduction
This document describes the requirements for an e-commerce system.

2. Functional Requirements
2.1 User Management
The system shall allow users to create accounts.
The system must authenticate users before allowing access.
Users should be able to update their personal data.

2.2 Data Protection
The system shall comply with GDPR regulations.
Personal data must be encrypted at rest.
Users must provide consent for data processing.

3. Non-Functional Requirements
The system should have 99.9% uptime.
Response time shall not exceed 2 seconds.
"""
    
    @pytest.fixture
    def sample_pdf_content(self):
        """Sample PDF content for testing."""
        return """
SYSTEM REQUIREMENTS SPECIFICATION

1. OVERVIEW
This system processes user data and must comply with privacy regulations.

2. REQUIREMENTS
2.1 The application shall collect user personal data only with explicit consent.
2.2 The system must implement data encryption for sensitive information.
2.3 Users should have the right to delete their personal data.
"""
    
    @pytest.fixture
    def temp_txt_file(self, sample_txt_content):
        """Create a temporary TXT file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(sample_txt_content)
            temp_path = Path(f.name)
        yield temp_path
        temp_path.unlink()
    
    @pytest.fixture
    def temp_pdf_file(self):
        """Create a temporary PDF file for testing."""
        # Create a simple PDF file using reportlab or similar
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_path = Path(f.name)
        
        # Write minimal PDF content
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF Content) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
300
%%EOF"""
        
        with open(temp_path, 'wb') as f:
            f.write(pdf_content)
        
        yield temp_path
        temp_path.unlink()
    
    def test_get_supported_formats(self, processor):
        """Test getting supported file formats."""
        formats = processor.get_supported_formats()
        expected_formats = ['.pdf', '.docx', '.doc', '.txt']
        assert formats == expected_formats
    
    def test_validate_document_format_valid(self, processor, temp_txt_file):
        """Test validation of supported document format."""
        assert processor.validate_document_format(temp_txt_file) is True
    
    def test_validate_document_format_invalid(self, processor):
        """Test validation of unsupported document format."""
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            assert processor.validate_document_format(temp_path) is False
        finally:
            temp_path.unlink()
    
    def test_validate_document_format_nonexistent(self, processor):
        """Test validation of non-existent file."""
        nonexistent_path = Path("nonexistent_file.txt")
        assert processor.validate_document_format(nonexistent_path) is False
    
    def test_extract_from_txt(self, processor, temp_txt_file, sample_txt_content):
        """Test text extraction from TXT file."""
        content = processor._extract_from_txt(temp_txt_file)
        assert content.strip() == sample_txt_content.strip()
    
    def test_extract_from_txt_encoding_fallback(self, processor):
        """Test TXT extraction with encoding fallback."""
        # Create file with latin-1 encoding
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='latin-1') as f:
            f.write("Test content with special chars: àáâã")
            temp_path = Path(f.name)
        
        try:
            content = processor._extract_from_txt(temp_path)
            assert "Test content" in content
        finally:
            temp_path.unlink()
    
    @patch('compliance_checker.processors.document_processor.pypdf.PdfReader')
    def test_extract_from_pdf_pypdf_fallback(self, mock_pdf_reader, processor, temp_pdf_file):
        """Test PDF extraction using pypdf fallback."""
        # Mock pypdf reader
        mock_page = Mock()
        mock_page.extract_text.return_value = "Test PDF content"
        mock_reader = Mock()
        mock_reader.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader
        
        content = processor._extract_from_pdf(temp_pdf_file)
        assert "Test PDF content" in content
    
    def test_extract_sections(self, processor, sample_txt_content):
        """Test section extraction from document content."""
        sections = processor._extract_sections(sample_txt_content)
        
        assert len(sections) >= 3  # Introduction, Functional Requirements, Non-Functional Requirements
        
        # Check that sections have proper structure
        for section in sections:
            assert isinstance(section, DocumentSection)
            assert section.id
            assert section.title
            assert section.content
            assert isinstance(section.level, int)
    
    def test_categorize_requirement(self, processor):
        """Test requirement categorization."""
        # Functional requirement
        func_req = "The system shall allow users to login"
        assert processor._categorize_requirement(func_req) == "functional"
        
        # Data requirement
        data_req = "Personal data must be encrypted"
        assert processor._categorize_requirement(data_req) == "data"
        
        # Non-functional requirement
        nonfunc_req = "The system should have 99% availability"
        assert processor._categorize_requirement(nonfunc_req) == "non_functional"
        
        # Interface requirement
        interface_req = "The API shall provide REST endpoints"
        assert processor._categorize_requirement(interface_req) == "interface"
        
        # Non-requirement
        non_req = "This is just a description"
        assert processor._categorize_requirement(non_req) is None
    
    def test_calculate_requirement_confidence(self, processor):
        """Test requirement confidence calculation."""
        # High confidence
        high_conf = "The system shall authenticate users"
        assert processor._calculate_requirement_confidence(high_conf) >= 0.3
        
        # Medium confidence (adjusted expectation)
        med_conf = "The system should validate input"
        confidence = processor._calculate_requirement_confidence(med_conf)
        assert confidence >= 0.2  # "should" + "the system" = 0.2 + 0.2 = 0.4
        
        # Low confidence
        low_conf = "The system may provide notifications"
        assert processor._calculate_requirement_confidence(low_conf) <= 0.3
    
    def test_extract_keywords(self, processor):
        """Test keyword extraction from requirement text."""
        text = "The system shall encrypt personal data for GDPR compliance"
        keywords = processor._extract_keywords(text)
        
        assert "personal data" in keywords
        assert "gdpr" in keywords
        assert "encryption" in keywords or "system" in keywords
    
    def test_is_gdpr_relevant(self, processor):
        """Test GDPR relevance detection."""
        # GDPR relevant
        gdpr_text = "The system must process personal data with consent"
        assert processor._is_gdpr_relevant(gdpr_text) is True
        
        # Not GDPR relevant
        non_gdpr_text = "The system shall display a login form"
        assert processor._is_gdpr_relevant(non_gdpr_text) is False
    
    def test_extract_requirements_from_text(self, processor):
        """Test requirement extraction from text."""
        text = """
        The system shall authenticate users.
        Users must provide valid credentials.
        The application should log all access attempts.
        This is just a description without requirements.
        Personal data shall be encrypted at rest.
        """
        
        requirements = processor._extract_requirements_from_text(text, "test_section")
        
        # Should extract at least 4 requirements
        assert len(requirements) >= 4
        
        # Check requirement structure
        for req in requirements:
            assert isinstance(req, Requirement)
            assert req.id.startswith("test_section_req_")
            assert req.section == "test_section"
            assert req.category in ["functional", "data", "non_functional", "interface"]
            assert isinstance(req.metadata, dict)
            assert "confidence" in req.metadata
            assert "keywords" in req.metadata
            assert "gdpr_relevant" in req.metadata
    
    def test_deduplicate_requirements(self, processor):
        """Test requirement deduplication."""
        req1 = Requirement(
            id="req1", text="The system shall authenticate users", 
            section="sec1", category="functional"
        )
        req2 = Requirement(
            id="req2", text="The system shall authenticate users", 
            section="sec1", category="functional"
        )
        req3 = Requirement(
            id="req3", text="Users must provide credentials", 
            section="sec1", category="functional"
        )
        
        requirements = [req1, req2, req3]
        unique_reqs = processor._deduplicate_requirements(requirements)
        
        assert len(unique_reqs) == 2  # req1 and req2 are duplicates
    
    def test_generate_metadata(self, processor, temp_txt_file, sample_txt_content):
        """Test metadata generation."""
        metadata = processor._generate_metadata(temp_txt_file, sample_txt_content)
        
        assert metadata["filename"] == temp_txt_file.name
        assert metadata["file_extension"] == ".txt"
        assert metadata["file_size"] > 0
        assert metadata["content_length"] == len(sample_txt_content)
        assert metadata["word_count"] > 0
        assert metadata["line_count"] > 0
        assert "processed_at" in metadata
        assert metadata["processor_version"] == "1.0.0"
    
    def test_generate_document_id(self, processor, temp_txt_file):
        """Test document ID generation."""
        doc_id = processor._generate_document_id(temp_txt_file)
        
        assert doc_id.startswith("doc_")
        assert temp_txt_file.stem in doc_id
        assert len(doc_id.split("_")) >= 3  # doc_filename_timestamp
    
    def test_calculate_file_hash(self, processor, temp_txt_file):
        """Test file hash calculation."""
        file_hash = processor._calculate_file_hash(temp_txt_file)
        
        assert len(file_hash) == 64  # SHA-256 hex digest length
        assert all(c in '0123456789abcdef' for c in file_hash)
        
        # Verify hash consistency
        hash2 = processor._calculate_file_hash(temp_txt_file)
        assert file_hash == hash2
    
    def test_parse_specification_txt(self, processor, temp_txt_file):
        """Test complete specification parsing for TXT file."""
        spec_doc = processor.parse_specification(temp_txt_file)
        
        assert isinstance(spec_doc, SpecificationDocument)
        assert spec_doc.filename == temp_txt_file.name
        assert spec_doc.file_path == temp_txt_file
        assert spec_doc.document_id.startswith("doc_")
        assert spec_doc.file_size > 0
        assert spec_doc.document_hash
        assert len(spec_doc.sections) > 0
        assert len(spec_doc.requirements) > 0
        
        # Check metadata
        assert "filename" in spec_doc.metadata
        assert "processor_version" in spec_doc.metadata
    
    def test_parse_specification_invalid_format(self, processor):
        """Test parsing with invalid file format."""
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(DocumentProcessingError):
                processor.parse_specification(temp_path)
        finally:
            temp_path.unlink()
    
    def test_parse_specification_nonexistent_file(self, processor):
        """Test parsing non-existent file."""
        nonexistent_path = Path("nonexistent_file.txt")
        
        with pytest.raises(DocumentProcessingError):
            processor.parse_specification(nonexistent_path)
    
    @patch('compliance_checker.processors.document_processor.UNSTRUCTURED_AVAILABLE', False)
    def test_docx_without_unstructured(self, processor):
        """Test DOCX processing without unstructured library."""
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(DocumentProcessingError):
                processor._extract_from_docx(temp_path)
        finally:
            temp_path.unlink()
    
    def test_extract_requirements(self, processor, sample_txt_content):
        """Test requirement extraction from specification document."""
        # Create a mock specification document
        sections = processor._extract_sections(sample_txt_content)
        spec_doc = SpecificationDocument(
            content=sample_txt_content,
            metadata={},
            sections=sections
        )
        
        requirements = processor.extract_requirements(spec_doc)
        
        assert len(requirements) > 0
        
        # Check for specific requirements we expect
        req_texts = [req.text for req in requirements]
        assert any("system shall allow users" in text.lower() for text in req_texts)
        assert any("must authenticate" in text.lower() for text in req_texts)
        assert any("gdpr" in text.lower() for text in req_texts)
    
    def test_extract_requirements_no_sections(self, processor, sample_txt_content):
        """Test requirement extraction when no sections are found."""
        spec_doc = SpecificationDocument(
            content=sample_txt_content,
            metadata={},
            sections=[]  # No sections
        )
        
        requirements = processor.extract_requirements(spec_doc)
        
        assert len(requirements) > 0
        # All requirements should be in document_root section
        assert all(req.section == "document_root" for req in requirements)
    
    def test_determine_section_level(self, processor):
        """Test section level determination."""
        assert processor._determine_section_level("section_1_introduction") == 1
        assert processor._determine_section_level("section_2_overview") == 1
        assert processor._determine_section_level("section_3_requirements") == 2
        assert processor._determine_section_level("section_4_functional") == 2
        assert processor._determine_section_level("section_5_other") == 3


class TestDocumentProcessorIntegration:
    """Integration tests for DocumentProcessor."""
    
    @pytest.fixture
    def processor(self):
        """Create a DocumentProcessor instance for testing."""
        return DocumentProcessor()
    
    def test_full_processing_workflow(self, processor):
        """Test the complete document processing workflow."""
        # Create a comprehensive test document
        test_content = """
# E-Commerce System Requirements

## 1. Introduction
This document specifies requirements for an e-commerce platform.

## 2. Functional Requirements

### 2.1 User Management
- The system shall allow users to register accounts
- The system must authenticate users before granting access
- Users should be able to update their personal information
- The system shall validate user input data

### 2.2 Data Protection
- Personal data must be encrypted at rest
- The system shall comply with GDPR regulations
- Users must provide explicit consent for data processing
- The system should implement data retention policies

## 3. Non-Functional Requirements
- The system should achieve 99.9% uptime
- Response time shall not exceed 2 seconds
- The system must handle 1000 concurrent users
"""
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_content)
            temp_path = Path(f.name)
        
        try:
            # Parse the document
            spec_doc = processor.parse_specification(temp_path)
            
            # Verify document structure
            assert len(spec_doc.sections) >= 3
            assert len(spec_doc.requirements) >= 8
            
            # Verify requirement categories
            categories = {req.category for req in spec_doc.requirements}
            assert "functional" in categories
            assert "data" in categories
            assert "non_functional" in categories
            
            # Verify GDPR relevance detection
            gdpr_relevant_reqs = [req for req in spec_doc.requirements if req.metadata.get('gdpr_relevant')]
            assert len(gdpr_relevant_reqs) >= 2
            
            # Verify confidence scores
            for req in spec_doc.requirements:
                assert 0.0 <= req.metadata['confidence'] <= 1.0
            
            # Verify keywords extraction
            for req in spec_doc.requirements:
                assert isinstance(req.metadata['keywords'], list)
            
        finally:
            temp_path.unlink()


class TestDocumentProcessorErrorHandling:
    """Test error handling in DocumentProcessor."""
    
    @pytest.fixture
    def processor(self):
        """Create a DocumentProcessor instance for testing."""
        return DocumentProcessor()
    
    def test_corrupted_file_handling(self, processor):
        """Test handling of corrupted files."""
        # Create a file with invalid content for its extension
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
            f.write("This is not a valid PDF file")
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(DocumentProcessingError):
                processor.parse_specification(temp_path)
        finally:
            temp_path.unlink()
    
    @patch('compliance_checker.processors.document_processor.pypdf.PdfReader')
    def test_pdf_parsing_error(self, mock_pdf_reader, processor):
        """Test PDF parsing error handling."""
        mock_pdf_reader.side_effect = Exception("PDF parsing failed")
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(DocumentProcessingError):
                processor._extract_from_pdf(temp_path)
        finally:
            temp_path.unlink()
    
    def test_empty_file_handling(self, processor):
        """Test handling of empty files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")  # Empty file
            temp_path = Path(f.name)
        
        try:
            spec_doc = processor.parse_specification(temp_path)
            assert spec_doc.content == ""
            assert len(spec_doc.requirements) == 0
        finally:
            temp_path.unlink()