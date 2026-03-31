"""
Query expansion module for RAG pipeline.
Provides multiple query expansion strategies using LLM.
"""

import re
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExpandedQuery:
    """Represents an expanded query with original and expanded terms."""
    original_query: str
    expanded_terms: List[str]
    final_query: str
    expansion_method: str


class QueryExpansionStrategy(ABC):
    """Abstract base class for query expansion strategies."""
    
    @abstractmethod
    def expand(self, query: str, **kwargs) -> ExpandedQuery:
        """Expand the query with additional terms."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return the name of the expansion strategy."""
        pass


class NoExpansionStrategy(QueryExpansionStrategy):
    """No query expansion - returns original query."""
    
    def expand(self, query: str, **kwargs) -> ExpandedQuery:
        return ExpandedQuery(
            original_query=query,
            expanded_terms=[],
            final_query=query,
            expansion_method="none"
        )
    
    def get_strategy_name(self) -> str:
        return "none"


class SynonymExpansionStrategy(QueryExpansionStrategy):
    """Expand query with predefined synonyms."""
    
    def __init__(self, synonym_dict: Optional[Dict[str, List[str]]] = None):
        self.synonym_dict = synonym_dict or self._get_default_synonyms()
    
    def _get_default_synonyms(self) -> Dict[str, List[str]]:
        """Get default GDPR/compliance synonyms."""
        return {
            'gdpr': ['general data protection regulation', 'data protection', 'privacy law'],
            'consent': ['agreement', 'permission', 'authorization', 'opt-in', 'approval'],
            'data': ['information', 'records', 'personal information', 'pii'],
            'processing': ['handling', 'treatment', 'management', 'operations'],
            'rights': ['entitlements', 'privileges', 'capabilities', 'powers'],
            'breach': ['violation', 'incident', 'leak', 'compromise'],
            'encryption': ['cryptography', 'encoding', 'security', 'protection'],
            'retention': ['storage', 'keeping', 'preservation', 'maintenance'],
            'deletion': ['erasure', 'removal', 'wiping', 'destruction'],
            'access': ['retrieval', 'viewing', 'obtaining', 'export'],
            'rectification': ['correction', 'update', 'amendment', 'fix'],
            'personal': ['individual', 'private', 'personally identifiable'],
            'controller': ['organization', 'entity', 'data owner', 'data controller'],
            'processor': ['service provider', 'data handler', 'third party'],
            'supervisory': ['regulatory', 'authority', 'oversight', 'governance'],
            'lawful': ['legal', 'legitimate', 'valid', 'permitted'],
            'basis': ['ground', 'reason', 'foundation', 'cause'],
            'subject': ['individual', 'user', 'customer', 'person'],
            'transfer': ['transmission', 'sharing', 'exchange', 'movement'],
        }
    
    def expand(self, query: str, **kwargs) -> ExpandedQuery:
        """Expand query using synonym dictionary."""
        query_lower = query.lower()
        expanded_terms: List[str] = []
        
        for term, synonyms in self.synonym_dict.items():
            if term in query_lower:
                expanded_terms.extend(synonyms)
        
        if expanded_terms:
            final_query = f"{query} {' '.join(expanded_terms)}"
        else:
            final_query = query
        
        return ExpandedQuery(
            original_query=query,
            expanded_terms=expanded_terms,
            final_query=final_query,
            expansion_method="synonym"
        )
    
    def get_strategy_name(self) -> str:
        return "synonym"


class LLMExpansionStrategy(QueryExpansionStrategy):
    """Expand query using LLM to generate related GDPR-specific terms."""
    
    def __init__(self, llm_client=None, max_expansions: int = 5, temperature: float = 0.3):
        self.llm_client = llm_client
        self.max_expansions = max_expansions
        self.temperature = temperature
    
    def expand(self, query: str, **kwargs) -> ExpandedQuery:
        """Expand query using LLM with GDPR domain awareness."""
        if not self.llm_client:
            return NoExpansionStrategy().expand(query)
        
        max_exp = kwargs.get('max_expansions', self.max_expansions)
        
        query_analysis = self._analyze_query(query)
        prompt = self._build_expansion_prompt(query, query_analysis, max_exp)
        
        try:
            response = self.llm_client.generate(
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=300
            )
            
            if response.success:
                expanded_terms = self._parse_response(response.content)
                
                if expanded_terms:
                    final_query = f"{query} {' '.join(expanded_terms)}"
                else:
                    final_query = query
                
                return ExpandedQuery(
                    original_query=query,
                    expanded_terms=expanded_terms,
                    final_query=final_query,
                    expansion_method="llm_gdpr"
                )
        
        except Exception as e:
            logger.warning(f"LLM expansion failed: {e}")
        
        return NoExpansionStrategy().expand(query)
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query to determine its quality and expansion needs."""
        query_lower = query.lower()
        
        vague_indicators = [
            'how', 'what', 'ways', 'things', 'stuff', 'handle',
            'deal with', 'about', 'regarding', 'concerned'
        ]
        
        incomplete_indicators = [
            'must', 'should', 'need to', 'have to', 'required',
            'ensure', 'make sure', 'guarantee'
        ]
        
        ambiguous_terms = [
            'data', 'user', 'customer', 'information', 'records',
            'consent', 'permission', 'agreement', 'rights'
        ]
        
        is_vague = any(ind in query_lower for ind in vague_indicators)
        is_incomplete = any(ind in query_lower for ind in incomplete_indicators)
        has_ambiguous = any(term in query_lower for term in ambiguous_terms)
        is_short = len(query.split()) <= 3
        
        gdpr_terms = [
            'gdpr', 'consent', 'personal', 'data', 'processing',
            'rights', 'breach', 'privacy', 'protection', 'controller',
            'processor', 'lawful', 'basis', 'article', 'recital'
        ]
        has_gdpr_context = any(term in query_lower for term in gdpr_terms)
        
        return {
            'is_vague': is_vague,
            'is_incomplete': is_incomplete,
            'has_ambiguous': has_ambiguous,
            'is_short': is_short,
            'has_gdpr_context': has_gdpr_context,
            'needs_expansion': is_vague or is_incomplete or is_short or (has_ambiguous and not has_gdpr_context)
        }
    
    def _build_expansion_prompt(self, query: str, analysis: Dict[str, Any], max_exp: int) -> str:
        """Build a GDPR-aware expansion prompt."""
        prompt_parts = [
            f"You are a GDPR compliance expert. Analyze and expand this query: \"{query}\""
        ]
        
        if analysis['is_short']:
            prompt_parts.append("\nThe query is very short and may be ambiguous.")
        
        if analysis['is_vague']:
            prompt_parts.append("\nThe query appears vague and needs clarification.")
        
        if analysis['is_incomplete']:
            prompt_parts.append("\nThe query is incomplete and needs more specific terms.")
        
        if analysis['has_ambiguous'] and not analysis['has_gdpr_context']:
            prompt_parts.append("\nThe query uses general terms that need GDPR-specific context.")
        
        prompt_parts.append("""
CONTEXT: You are helping retrieve relevant GDPR articles and compliance requirements.
The query will be used to search a knowledge base of GDPR regulations.

EXPANSION GUIDELINES:
1. Add specific GDPR Article references (e.g., "Article 6", "Article 7", "Article 17")
2. Add GDPR-specific terminology variations
3. Add related compliance concepts
4. Make the query more specific and searchable

EXAMPLE INPUT: "how to handle user data"
EXAMPLE OUTPUT: ["user data handling", "GDPR Article 6 lawful basis", "personal data processing", 
                "data protection by design", "GDPR compliance requirements", "consent management",
                "data subject rights", "controller obligations"]

EXAMPLE INPUT: "consent requirements"
EXAMPLE OUTPUT: ["explicit consent", "GDPR Article 7", "consent withdrawal", "granular consent",
                "opt-in requirements", "informed consent", "consent records", "withdrawal mechanism"]

Now generate {max_exp} relevant expansion terms for this query:

QUERY: "{query}"

Return ONLY a JSON array of strings, no other text:""".format(query=query, max_exp=max_exp))
        
        return '\n'.join(prompt_parts)
    
    def _parse_response(self, response: str) -> List[str]:
        """Parse LLM response to extract expansion terms."""
        try:
            match = re.search(r'\[[\s\S]*\]', response)
            if match:
                terms = json.loads(match.group())
                return [t for t in terms if isinstance(t, str)]
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse expansion terms: {e}")
        
        return []
    
    def get_strategy_name(self) -> str:
        return "llm"


class HybridExpansionStrategy(QueryExpansionStrategy):
    """Combine multiple expansion strategies."""
    
    def __init__(self, strategies: List[QueryExpansionStrategy], weights: Optional[List[float]] = None):
        self.strategies = strategies
        self.weights = weights or [1.0] * len(strategies)
    
    def expand(self, query: str, **kwargs) -> ExpandedQuery:
        """Combine expansions from multiple strategies."""
        all_terms: Set[str] = set()
        methods_used: List[str] = []
        
        for strategy, weight in zip(self.strategies, self.weights):
            if weight <= 0:
                continue
            
            expanded = strategy.expand(query)
            all_terms.update(expanded.expanded_terms)
            methods_used.append(expanded.expansion_method)
        
        final_query = f"{query} {' '.join(list(all_terms)[:10])}"
        
        return ExpandedQuery(
            original_query=query,
            expanded_terms=list(all_terms),
            final_query=final_query,
            expansion_method="+".join(set(methods_used))
        )
    
    def get_strategy_name(self) -> str:
        names = [s.get_strategy_name() for s in self.strategies]
        return f"hybrid_{'+'.join(names)}"


class QueryExpansionFactory:
    """Factory for creating query expansion strategies."""
    
    STRATEGIES = {
        'none': NoExpansionStrategy,
        'synonym': SynonymExpansionStrategy,
        'llm': LLMExpansionStrategy,
    }
    
    @classmethod
    def create(cls, 
               strategy: str, 
               llm_client=None,
               **kwargs) -> QueryExpansionStrategy:
        """Create a query expansion strategy."""
        if strategy not in cls.STRATEGIES:
            raise ValueError(f"Unknown expansion strategy: {strategy}. "
                           f"Available: {list(cls.STRATEGIES.keys())}")
        
        if strategy == 'synonym':
            return SynonymExpansionStrategy(**kwargs)
        
        if strategy == 'llm':
            return LLMExpansionStrategy(llm_client=llm_client, **kwargs)
        
        return NoExpansionStrategy()
    
    @classmethod
    def create_hybrid(cls, 
                      strategies: List[str],
                      llm_client=None,
                      weights: Optional[List[float]] = None) -> QueryExpansionStrategy:
        """Create a hybrid expansion strategy."""
        strategy_objects = []
        for s in strategies:
            strategy = cls.create(s, llm_client=llm_client)
            strategy_objects.append(strategy)
        
        return HybridExpansionStrategy(strategy_objects, weights)
    
    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """Get list of available expansion strategies."""
        return list(cls.STRATEGIES.keys())
