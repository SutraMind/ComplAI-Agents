"""
Document processing implementation for parsing various file formats.
"""

import hashlib
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

# Document processing libraries
try:
    import pypdf
    from unstructured.partition.auto import partition
    from unstructured.partition.pdf import partition_pdf
    from unstructured.partition.docx import partition_docx
    from unstructured.partition.text import partition_text
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False

from .base import DocumentProcessor as BaseDocumentProcessor
from ..models.document import SpecificationDocument, Requirement, DocumentSection
from ..exceptions import DocumentProcessingError, ValidationError


logger = logging.getLogger(__name__)


class DocumentProcessor(BaseDocumentProcessor):
    """Concrete implementation of document processor for various file formats."""
    
    SUPPORTED_FORMATS = ['.pdf', '.docx', '.doc', '.txt']
    
    def __init__(self):
        """Initialize the document processor."""
        if not UNSTRUCTURED_AVAILABLE:
            logger.warning("Unstructured library not available. Some features may be limited.")
        
        # Requirement patterns for different categories
        self.requirement_patterns = {
            'functional': [
                r'(?i)(?:the system|application|software)\s+(?:shall|must|should|will)\s+',
                r'(?i)(?:user|admin|operator)\s+(?:shall|must|should|will)\s+be able to',
                r'(?i)(?:when|if)\s+.*\s+(?:then|the system)\s+(?:shall|must|should|will)',
            ],
            'non_functional': [
                r'(?i)(?:performance|security|reliability|availability|scalability)',
                r'(?i)(?:response time|throughput|latency|uptime)',
                r'(?i)(?:authentication|authorization|encryption|access control)',
            ],
            'data': [
                r'(?i)(?:data|information|record|database|storage)',
                r'(?i)(?:personal data|sensitive data|user data)',
                r'(?i)(?:gdpr|privacy|consent|data protection)',
            ],
            'interface': [
                r'(?i)(?:api|interface|endpoint|service)',
                r'(?i)(?:integration|external system|third party)',
            ]
        }
    
    def parse_specification(self, file_path: Path) -> SpecificationDocument:
        """Parse a specification document from file."""
        try:
            if not self.validate_document_format(file_path):
                raise ValidationError(f"Unsupported file format: {file_path.suffix}")
            
            # Extract text content based on file type
            content = self._extract_text_content(file_path)
            
            # Generate document metadata
            metadata = self._generate_metadata(file_path, content)
            
            # Create specification document
            spec_doc = SpecificationDocument(
                content=content,
                metadata=metadata,
                document_id=self._generate_document_id(file_path),
                filename=file_path.name,
                file_path=file_path,
                file_size=file_path.stat().st_size,
                document_hash=self._calculate_file_hash(file_path)
            )
            
            # Extract sections
            spec_doc.sections = self._extract_sections(content)
            
            # Extract requirements
            spec_doc.requirements = self.extract_requirements(spec_doc)
            
            logger.info(f"Successfully parsed document: {file_path.name}")
            logger.info(f"Extracted {len(spec_doc.sections)} sections and {len(spec_doc.requirements)} requirements")
            
            return spec_doc
            
        except Exception as e:
            logger.error(f"Failed to parse document {file_path}: {str(e)}")
            raise DocumentProcessingError(file_path.name, str(e))
    
    def extract_requirements(self, document: SpecificationDocument) -> List[Requirement]:
        """Extract requirements from a specification document."""
        requirements = []
        
        # Process each section for requirements
        for section in document.sections:
            section_requirements = self._extract_requirements_from_section(section)
            requirements.extend(section_requirements)
        
        # If no sections found, process the entire content
        if not document.sections:
            requirements = self._extract_requirements_from_text(
                document.content, 
                section_id="document_root"
            )
        
        # Deduplicate requirements based on text similarity
        requirements = self._deduplicate_requirements(requirements)
        
        logger.info(f"Extracted {len(requirements)} unique requirements")
        return requirements
    
    def validate_document_format(self, file_path: Path) -> bool:
        """Validate that the document format is supported."""
        if not file_path.exists():
            return False
        
        suffix = file_path.suffix.lower()
        return suffix in self.SUPPORTED_FORMATS
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported document formats."""
        return self.SUPPORTED_FORMATS.copy()
    
    def _extract_text_content(self, file_path: Path) -> str:
        """Extract text content from various file formats."""
        suffix = file_path.suffix.lower()
        
        try:
            if suffix == '.txt':
                return self._extract_from_txt(file_path)
            elif suffix == '.pdf':
                return self._extract_from_pdf(file_path)
            elif suffix in ['.doc', '.docx']:
                return self._extract_from_docx(file_path)
            else:
                raise ValidationError(f"Unsupported file format: {suffix}")
                
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {str(e)}")
            raise DocumentProcessingError(file_path.name, f"Text extraction failed: {str(e)}")
    
    def _extract_from_txt(self, file_path: Path) -> str:
        """Extract text from TXT file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as file:
                return file.read()
    
    def _extract_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF file."""
        if UNSTRUCTURED_AVAILABLE:
            try:
                elements = partition_pdf(str(file_path))
                return '\n'.join([str(element) for element in elements])
            except Exception as e:
                logger.warning(f"Unstructured PDF parsing failed, falling back to pypdf: {e}")
        
        # Fallback to pypdf
        try:
            with open(file_path, 'rb') as file:
                reader = pypdf.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            raise DocumentProcessingError(file_path.name, f"PDF parsing failed: {str(e)}")
    
    def _extract_from_docx(self, file_path: Path) -> str:
        """Extract text from DOCX file."""
        if UNSTRUCTURED_AVAILABLE:
            try:
                elements = partition_docx(str(file_path))
                return '\n'.join([str(element) for element in elements])
            except Exception as e:
                logger.error(f"DOCX parsing failed: {e}")
                raise DocumentProcessingError(file_path.name, f"DOCX parsing failed: {str(e)}")
        else:
            raise DocumentProcessingError(file_path.name, "DOCX processing requires unstructured library")
    
    def _extract_sections(self, content: str) -> List[DocumentSection]:
        """Extract sections from document content."""
        sections = []
        
        # Enhanced section patterns for markdown and various formats
        section_patterns = [
            r'^#{1,6}\s+(.+)$',             # Markdown headers (# ## ### etc.)
            r'^(\d+\.?\d*\.?\d*)\s+(.+)$',  # Numbered sections (1.1, 1.1.1, etc.)
            r'^([A-Z][A-Z\s]+)$',           # ALL CAPS sections
            r'^([A-Z][a-z\s]+):?\s*$',      # Title case sections
        ]
        
        lines = content.split('\n')
        current_section_id = None
        current_content = []
        section_counter = 0
        
        for line_num, line in enumerate(lines):
            original_line = line
            line = line.strip()
            if not line:
                continue
            
            # Check if line matches section pattern
            section_match = None
            section_title = None
            
            for pattern in section_patterns:
                match = re.match(pattern, line)
                if match:
                    section_match = match
                    if pattern.startswith(r'^#{1,6}'):  # Markdown header
                        section_title = match.group(1).strip()
                    elif len(match.groups()) > 1:  # Numbered or titled sections
                        section_title = match.group(2).strip()
                    else:
                        section_title = match.group(1).strip()
                    break
            
            if section_match and section_title:
                # Save previous section if exists
                if current_section_id and current_content:
                    sections.append(DocumentSection(
                        id=current_section_id,
                        title=current_section_id.split('_', 2)[2] if len(current_section_id.split('_')) > 2 else current_section_id,
                        content='\n'.join(current_content),
                        level=self._determine_section_level(current_section_id)
                    ))
                
                # Start new section
                section_counter += 1
                clean_title = re.sub(r'[^\w\s]', '', section_title).lower().replace(' ', '_')
                current_section_id = f"section_{section_counter}_{clean_title}"
                current_content = []
            else:
                # Add line to current section content
                if current_section_id:
                    current_content.append(original_line)
                else:
                    # Create a default section for content before first section
                    if not current_section_id:
                        section_counter += 1
                        current_section_id = f"section_{section_counter}_document_start"
                    current_content.append(original_line)
        
        # Add final section
        if current_section_id and current_content:
            sections.append(DocumentSection(
                id=current_section_id,
                title=current_section_id.split('_', 2)[2] if len(current_section_id.split('_')) > 2 else current_section_id,
                content='\n'.join(current_content),
                level=self._determine_section_level(current_section_id)
            ))
        
        return sections
    
    def _determine_section_level(self, section_id: str) -> int:
        """Determine the hierarchical level of a section."""
        # Simple heuristic based on section numbering
        if 'introduction' in section_id.lower() or 'overview' in section_id.lower():
            return 1
        elif any(keyword in section_id.lower() for keyword in ['requirement', 'specification', 'functional']):
            return 2
        else:
            return 3
    
    def _extract_requirements_from_section(self, section: DocumentSection) -> List[Requirement]:
        """Extract requirements from a specific section."""
        return self._extract_requirements_from_text(section.content, section.id)
    
    def _extract_requirements_from_text(self, text: str, section_id: str) -> List[Requirement]:
        """Extract requirements from text using pattern matching."""
        requirements = []
        lines = text.split('\n')
        req_counter = 0
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Check if line contains requirement indicators
            category = self._categorize_requirement(line)
            if category:
                req_counter += 1
                requirement_id = f"{section_id}_req_{req_counter}"
                
                requirement = Requirement(
                    id=requirement_id,
                    text=line,
                    section=section_id,
                    category=category,
                    source_line=line_num + 1,
                    metadata={
                        'confidence': self._calculate_requirement_confidence(line),
                        'keywords': self._extract_keywords(line),
                        'gdpr_relevant': self._is_gdpr_relevant(line)
                    }
                )
                requirements.append(requirement)
        
        return requirements
    
    def _categorize_requirement(self, text: str) -> Optional[str]:
        """Categorize a requirement based on its content."""
        text_lower = text.lower()
        
        # Check each category pattern in priority order
        # Check data patterns first (more specific)
        for pattern in self.requirement_patterns['data']:
            if re.search(pattern, text_lower):
                return 'data'
        
        # Check non-functional patterns
        for pattern in self.requirement_patterns['non_functional']:
            if re.search(pattern, text_lower):
                return 'non_functional'
        
        # Check interface patterns
        for pattern in self.requirement_patterns['interface']:
            if re.search(pattern, text_lower):
                return 'interface'
        
        # Check functional patterns last (most general)
        for pattern in self.requirement_patterns['functional']:
            if re.search(pattern, text_lower):
                return 'functional'
        
        # Additional heuristics for requirement detection
        requirement_indicators = [
            'shall', 'must', 'should', 'will', 'required', 'mandatory',
            'the system', 'the application', 'user can', 'user must'
        ]
        
        if any(indicator in text_lower for indicator in requirement_indicators):
            return 'functional'  # Default category
        
        return None
    
    def _calculate_requirement_confidence(self, text: str) -> float:
        """Calculate confidence score for requirement identification."""
        confidence = 0.0
        text_lower = text.lower()
        
        # Strong indicators
        strong_indicators = ['shall', 'must', 'required', 'mandatory']
        for indicator in strong_indicators:
            if indicator in text_lower:
                confidence += 0.3
        
        # Medium indicators
        medium_indicators = ['should', 'will', 'the system', 'user can']
        for indicator in medium_indicators:
            if indicator in text_lower:
                confidence += 0.2
        
        # Weak indicators
        weak_indicators = ['may', 'could', 'might', 'optional']
        for indicator in weak_indicators:
            if indicator in text_lower:
                confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from requirement text."""
        # Simple keyword extraction
        keywords = []
        
        # GDPR-related keywords
        gdpr_keywords = [
            'personal data', 'data protection', 'privacy', 'consent', 'gdpr',
            'data subject', 'controller', 'processor', 'lawful basis'
        ]
        
        # Technical keywords
        tech_keywords = [
            'authentication', 'authorization', 'encryption', 'security',
            'database', 'api', 'interface', 'system', 'user'
        ]
        
        text_lower = text.lower()
        for keyword in gdpr_keywords + tech_keywords:
            if keyword in text_lower:
                keywords.append(keyword)
        
        return keywords
    
    def _is_gdpr_relevant(self, text: str) -> bool:
        """Check if a requirement is potentially GDPR-relevant."""
        gdpr_indicators = [
            'personal data', 'data protection', 'privacy', 'consent', 'gdpr',
            'data subject', 'user data', 'sensitive data', 'data processing',
            'data retention', 'data deletion', 'right to be forgotten'
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in gdpr_indicators)
    
    def _deduplicate_requirements(self, requirements: List[Requirement]) -> List[Requirement]:
        """Remove duplicate requirements based on text similarity."""
        if not requirements:
            return requirements
        
        unique_requirements = []
        seen_texts = set()
        
        for req in requirements:
            # Simple deduplication based on normalized text
            normalized_text = re.sub(r'\s+', ' ', req.text.lower().strip())
            if normalized_text not in seen_texts:
                seen_texts.add(normalized_text)
                unique_requirements.append(req)
        
        return unique_requirements
    
    def _generate_metadata(self, file_path: Path, content: str) -> Dict[str, Any]:
        """Generate metadata for the document."""
        return {
            'filename': file_path.name,
            'file_extension': file_path.suffix,
            'file_size': file_path.stat().st_size,
            'content_length': len(content),
            'word_count': len(content.split()),
            'line_count': len(content.split('\n')),
            'processed_at': datetime.now().isoformat(),
            'processor_version': '1.0.0'
        }
    
    def _generate_document_id(self, file_path: Path) -> str:
        """Generate a unique document ID."""
        # Use filename and timestamp for uniqueness
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"doc_{file_path.stem}_{timestamp}"
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of the file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()