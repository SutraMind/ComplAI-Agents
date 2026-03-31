"""
Chunking strategies for document processing.
Provides multiple chunking algorithms with agentic support.
"""

import re
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a text chunk with metadata."""
    text: str
    chunk_id: str
    start_index: int
    end_index: int
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'text': self.text,
            'chunk_id': self.chunk_id,
            'start_index': self.start_index,
            'end_index': self.end_index,
            'metadata': self.metadata
        }


class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies."""
    
    @abstractmethod
    def chunk(self, text: str, **kwargs) -> List[Chunk]:
        """Chunk the input text into smaller pieces."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return the name of the chunking strategy."""
        pass


class FixedSizeChunking(ChunkingStrategy):
    """Fixed-size chunking with overlap."""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk(self, text: str, **kwargs) -> List[Chunk]:
        """Chunk text into fixed-size pieces."""
        chunk_size = kwargs.get('chunk_size', self.chunk_size)
        overlap = kwargs.get('overlap', self.overlap)
        
        chunks = []
        start = 0
        chunk_id = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Adjust to not split words mid-way
            if end < len(text):
                # Try to end at a sentence boundary
                sentence_end = max(
                    text.rfind('. ', start, end),
                    text.rfind('.\n', start, end),
                    text.rfind('?\n', start, end),
                    text.rfind('!\n', start, end)
                )
                if sentence_end > start + chunk_size // 2:
                    end = sentence_end + 1
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunks.append(Chunk(
                    text=chunk_text,
                    chunk_id=f"chunk_{chunk_id}",
                    start_index=start,
                    end_index=end,
                    metadata={
                        'strategy': 'fixed_size',
                        'chunk_size': len(chunk_text),
                        'overlap': overlap
                    }
                ))
                chunk_id += 1
            
            start = end - overlap
            if start >= len(text):
                break
        
        logger.info(f"FixedSizeChunking created {len(chunks)} chunks")
        return chunks
    
    def get_strategy_name(self) -> str:
        return f"fixed_size_{self.chunk_size}"


class SemanticChunking(ChunkingStrategy):
    """Chunking by semantic boundaries (paragraphs, sections)."""
    
    def __init__(self, min_chunk_size: int = 200, max_chunk_size: int = 1500):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
    
    def chunk(self, text: str, **kwargs) -> List[Chunk]:
        """Chunk text by semantic boundaries."""
        min_size = kwargs.get('min_chunk_size', self.min_chunk_size)
        max_size = kwargs.get('max_chunk_size', self.max_chunk_size)
        
        # Split by various delimiters
        chunks = []
        chunk_id = 0
        
        # Try splitting by double newlines first (paragraphs)
        paragraphs = re.split(r'\n\n+', text)
        
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If single paragraph exceeds max, split by sentences
            if len(para) > max_size:
                if current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    if len(chunk_text) >= min_size:
                        chunks.append(self._create_chunk(chunk_text, chunk_id, text))
                        chunk_id += 1
                    current_chunk = []
                    current_size = 0
                
                # Split long paragraph
                sentences = re.split(r'(?<=[.!?])\s+', para)
                for sent in sentences:
                    if current_size + len(sent) > max_size and current_chunk:
                        chunk_text = '\n\n'.join(current_chunk)
                        if len(chunk_text) >= min_size:
                            chunks.append(self._create_chunk(chunk_text, chunk_id, text))
                            chunk_id += 1
                        current_chunk = [sent]
                        current_size = len(sent)
                    else:
                        current_chunk.append(sent)
                        current_size += len(sent)
            else:
                if current_size + len(para) > max_size and current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    if len(chunk_text) >= min_size:
                        chunks.append(self._create_chunk(chunk_text, chunk_id, text))
                        chunk_id += 1
                    current_chunk = [para]
                    current_size = len(para)
                else:
                    current_chunk.append(para)
                    current_size += len(para)
        
        # Add remaining chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            if len(chunk_text) >= min_size:
                chunks.append(self._create_chunk(chunk_text, chunk_id, text))
        
        logger.info(f"SemanticChunking created {len(chunks)} chunks")
        return chunks
    
    def _create_chunk(self, text: str, chunk_id: int, full_text: str) -> Chunk:
        start = full_text.find(text)
        end = start + len(text) if start >= 0 else 0
        
        return Chunk(
            text=text,
            chunk_id=f"chunk_{chunk_id}",
            start_index=max(0, start),
            end_index=end,
            metadata={
                'strategy': 'semantic',
                'chunk_size': len(text)
            }
        )
    
    def get_strategy_name(self) -> str:
        return "semantic"


class RecursiveChunking(ChunkingStrategy):
    """Recursive chunking that tries multiple separators."""
    
    def __init__(self, 
                 separators: Optional[List[str]] = None,
                 min_chunk_size: int = 100,
                 max_chunk_size: int = 1500):
        
        if separators is None:
            self.separators = [
                '\n\n\n',  # Triple newline (major sections)
                '\n\n',    # Double newline (paragraphs)
                '\n',      # Single newline
                '. ',      # Sentence
                ', ',      # Clause
                ' ',       # Word
            ]
        else:
            self.separators = separators
            
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
    
    def chunk(self, text: str, **kwargs) -> List[Chunk]:
        """Chunk text recursively using separators."""
        min_size = kwargs.get('min_chunk_size', self.min_chunk_size)
        max_size = kwargs.get('max_chunk_size', self.max_chunk_size)
        
        chunks = self._split_text(text, self.separators, min_size, max_size, 0)
        
        # Assign chunk IDs and indices
        result = []
        current_idx = 0
        for i, chunk_text in enumerate(chunks):
            start = text.find(chunk_text, current_idx)
            end = start + len(chunk_text) if start >= 0 else current_idx + len(chunk_text)
            
            result.append(Chunk(
                text=chunk_text,
                chunk_id=f"chunk_{i}",
                start_index=max(0, start),
                end_index=end,
                metadata={
                    'strategy': 'recursive',
                    'chunk_size': len(chunk_text),
                    'level': self._get_chunk_level(chunk_text, text)
                }
            ))
            current_idx = end
        
        logger.info(f"RecursiveChunking created {len(result)} chunks")
        return result
    
    def _split_text(self, text: str, separators: List[str], 
                   min_size: int, max_size: int, level: int) -> List[str]:
        """Recursively split text."""
        if level >= len(separators) or len(text) <= max_size:
            return [text] if text.strip() else []
        
        separator = separators[level]
        
        if not separator:
            # Word-level splitting
            words = text.split()
            chunks = []
            current_chunk = []
            current_size = 0
            
            for word in words:
                word_size = len(word) + 1
                if current_size + word_size > max_size and current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = [word]
                    current_size = word_size
                else:
                    current_chunk.append(word)
                    current_size += word_size
            
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            
            # If chunks are too small, combine them
            if chunks and any(len(c) < min_size for c in chunks):
                return self._combine_small_chunks(chunks, min_size, max_size)
            
            return chunks
        
        # Split by separator
        parts = text.split(separator)
        
        if len(parts) == 1:
            return self._split_text(text, separators, min_size, max_size, level + 1)
        
        chunks = []
        current = []
        current_size = 0
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            part_size = len(part) + len(separator)
            
            if current_size + part_size > max_size and current:
                chunk = separator.join(current)
                if chunk:
                    chunks.append(chunk)
                current = [part]
                current_size = part_size
            else:
                current.append(part)
                current_size += part_size
        
        if current:
            chunk = separator.join(current)
            if chunk:
                chunks.append(chunk)
        
        # Handle small chunks by combining
        if any(len(c) < min_size for c in chunks):
            chunks = self._combine_small_chunks(chunks, min_size, max_size)
        
        # If still too large, try next level
        if any(len(c) > max_size for c in chunks):
            new_chunks = []
            for chunk in chunks:
                if len(chunk) > max_size:
                    new_chunks.extend(self._split_text(chunk, separators, min_size, max_size, level + 1))
                else:
                    new_chunks.append(chunk)
            chunks = new_chunks
        
        return chunks
    
    def _combine_small_chunks(self, chunks: List[str], min_size: int, max_size: int) -> List[str]:
        """Combine small chunks to meet minimum size."""
        if not chunks:
            return chunks
        
        result = []
        current = []
        current_size = 0
        
        for chunk in chunks:
            chunk_size = len(chunk)
            
            if current_size + chunk_size < min_size:
                current.append(chunk)
                current_size += chunk_size + 2  # Add for separator
            else:
                if current:
                    result.append(' '.join(current))
                    current = []
                    current_size = 0
                
                if chunk_size >= min_size:
                    result.append(chunk)
                else:
                    current = [chunk]
                    current_size = chunk_size
        
        if current:
            result.append(' '.join(current))
        
        return result
    
    def _get_chunk_level(self, chunk: str, full_text: str) -> int:
        """Determine the hierarchical level of a chunk."""
        start = full_text.find(chunk)
        if start < 0:
            return 0
        
        # Count section markers before this chunk
        before = full_text[:start]
        level = 0
        level += before.count('\n\n\n') * 3
        level += before.count('\n\n') * 2
        level += before.count('\n')
        
        return min(level, len(self.separators))
    
    def get_strategy_name(self) -> str:
        return "recursive"


class AgenticChunking(ChunkingStrategy):
    """
    Agentic chunking that uses LLM to intelligently determine chunk boundaries.
    The LLM analyzes the document structure and determines optimal chunk divisions.
    """
    
    def __init__(self, llm_client=None, min_chunk_size: int = 200, max_chunk_size: int = 1500):
        self.llm_client = llm_client
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
    
    def chunk(self, text: str, **kwargs) -> List[Chunk]:
        """Use LLM to intelligently chunk the text."""
        min_size = kwargs.get('min_chunk_size', self.min_chunk_size)
        max_size = kwargs.get('max_chunk_size', self.max_chunk_size)
        
        if self.llm_client is None:
            logger.warning("No LLM client provided for AgenticChunking, falling back to semantic chunking")
            fallback = SemanticChunking(min_chunk_size=min_size, max_chunk_size=max_size)
            return fallback.chunk(text, min_chunk_size=min_size, max_chunk_size=max_size)
        
        # Use LLM to identify chunk boundaries
        chunk_boundaries = self._get_chunk_boundaries(text, min_size, max_size)
        
        # Create chunks from boundaries
        chunks = []
        for i, (start, end) in enumerate(chunk_boundaries):
            chunk_text = text[start:end].strip()
            if chunk_text and len(chunk_text) >= min_size:
                chunks.append(Chunk(
                    text=chunk_text,
                    chunk_id=f"chunk_{i}",
                    start_index=start,
                    end_index=end,
                    metadata={
                        'strategy': 'agentic',
                        'chunk_size': len(chunk_text),
                        'llm_generated': True
                    }
                ))
        
        logger.info(f"AgenticChunking created {len(chunks)} chunks")
        return chunks
    
    def _get_chunk_boundaries(self, text: str, min_size: int, max_size: int) -> List[Tuple[int, int]]:
        """Use LLM to determine chunk boundaries."""
        prompt = f"""Analyze the following text and identify optimal chunk boundaries for compliance analysis.

TEXT:
{text[:5000]}

CRITERIA:
- Each chunk should be between {min_size} and {max_size} characters
- Chunks should respect semantic boundaries (sections, paragraphs, related content)
- Focus on maintaining coherent topics together
- Identify: section headers, paragraph breaks, and logical topic shifts

Return your analysis as a JSON array of objects with:
- "start": character position where chunk starts
- "end": character position where chunk ends  
- "reason": brief reason for this boundary

Example format:
[
  {{"start": 0, "end": 500, "reason": "Introduction section"}},
  {{"start": 501, "end": 1200, "reason": "First main topic"}}
]

JSON:"""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                temperature=0.1,
                max_tokens=2000
            )
            
            if response.success:
                # Parse the response to get boundaries
                boundaries = self._parse_boundaries(response.content, len(text))
                
                if boundaries:
                    # Sort by start position
                    boundaries.sort(key=lambda x: x[0])
                    
                    # Merge overlapping/adjacent boundaries
                    boundaries = self._merge_boundaries(boundaries, min_size)
                    
                    return boundaries
            
            # Fallback on error
            logger.warning("LLM chunking failed, using fallback")
            return self._fallback_boundaries(text, min_size, max_size)
            
        except Exception as e:
            logger.error(f"Error in agentic chunking: {e}")
            return self._fallback_boundaries(text, min_size, max_size)
    
    def _parse_boundaries(self, response: str, text_length: int) -> List[Tuple[int, int]]:
        """Parse LLM response to extract boundaries."""
        try:
            # Try to find JSON in response
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                data = json.loads(json_match.group())
                
                boundaries = []
                for item in data:
                    start = int(item.get('start', 0))
                    end = int(item.get('end', text_length))
                    
                    # Validate bounds
                    start = max(0, min(start, text_length))
                    end = max(start, min(end, text_length))
                    
                    if end > start:
                        boundaries.append((start, end))
                
                return boundaries
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse boundaries: {e}")
        
        return []
    
    def _merge_boundaries(self, boundaries: List[Tuple[int, int]], min_size: int) -> List[Tuple[int, int]]:
        """Merge overlapping or too-small boundaries."""
        if not boundaries:
            return []
        
        merged = [boundaries[0]]
        
        for start, end in boundaries[1:]:
            last_start, last_end = merged[-1]
            
            # If gap is too small or overlaps, merge
            if start - last_end < 100:
                merged[-1] = (last_start, end)
            # If previous chunk is too small, merge with current
            elif last_end - last_start < min_size:
                merged[-1] = (last_start, end)
            else:
                merged.append((start, end))
        
        return merged
    
    def _fallback_boundaries(self, text: str, min_size: int, max_size: int) -> List[Tuple[int, int]]:
        """Fallback to semantic chunking when LLM fails."""
        fallback = SemanticChunking(min_chunk_size=min_size, max_chunk_size=max_size)
        chunks = fallback.chunk(text, min_chunk_size=min_size, max_chunk_size=max_size)
        return [(c.start_index, c.end_index) for c in chunks]
    
    def get_strategy_name(self) -> str:
        return "agentic"


class ChunkingFactory:
    """Factory for creating chunking strategies."""
    
    STRATEGIES = {
        'fixed': FixedSizeChunking,
        'semantic': SemanticChunking,
        'recursive': RecursiveChunking,
        'agentic': AgenticChunking,
    }
    
    @classmethod
    def create(cls, 
               strategy: str, 
               llm_client=None,
               **kwargs) -> ChunkingStrategy:
        """
        Create a chunking strategy.
        
        Args:
            strategy: Name of the chunking strategy ('fixed', 'semantic', 'recursive', 'agentic')
            llm_client: LLM client (required for 'agentic' strategy)
            **kwargs: Additional parameters for the strategy
        
        Returns:
            ChunkingStrategy instance
        """
        if strategy not in cls.STRATEGIES:
            raise ValueError(f"Unknown chunking strategy: {strategy}. "
                           f"Available: {list(cls.STRATEGIES.keys())}")
        
        if strategy == 'agentic':
            return AgenticChunking(llm_client=llm_client, **kwargs)
        
        return cls.STRATEGIES[strategy](**kwargs)
    
    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """Get list of available chunking strategies."""
        return list(cls.STRATEGIES.keys())
