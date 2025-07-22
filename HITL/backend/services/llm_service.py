"""
LLM service for intelligent text analysis using Ollama.
"""

import json
import requests
from typing import Dict, Any, List, Optional
from flask import current_app

from ..ollama_config import ollama_config
from ..utils.security import SecurityValidator


class LLMService:
    """Service class for LLM-powered text analysis operations."""
    
    def __init__(self):
        """Initialize the LLM service."""
        self.ollama = ollama_config
        self.security = SecurityValidator()
        self.max_text_length = 8000  # Reasonable limit for LLM processing
    
    def analyze_text_sections(self, content: str) -> Dict[str, Any]:
        """
        Analyze text content to identify logical sections and themes.
        
        Args:
            content: Text content to analyze
            
        Returns:
            Dictionary containing section analysis results
        """
        try:
            if not content.strip():
                raise ValueError("Content cannot be empty")
            
            if len(content) > self.max_text_length:
                content = content[:self.max_text_length] + "..."
            
            prompt = self._build_section_analysis_prompt(content)
            
            response = self._call_ollama(prompt)
            if not response:
                return self._get_fallback_section_analysis(content)
            
            # Parse LLM response
            analysis = self._parse_section_analysis_response(response)
            
            return {
                'status': 'success',
                'sections': analysis.get('sections', []),
                'themes': analysis.get('themes', []),
                'summary': analysis.get('summary', ''),
                'confidence': analysis.get('confidence', 0.5)
            }
            
        except Exception as e:
            current_app.logger.error(f"Error in text section analysis: {str(e)}")
            return self._get_fallback_section_analysis(content)
    
    def analyze_comment_sentiment(self, comment_text: str) -> Dict[str, Any]:
        """
        Analyze sentiment and themes in a comment.
        
        Args:
            comment_text: Comment text to analyze
            
        Returns:
            Dictionary containing sentiment analysis results
        """
        try:
            if not comment_text.strip():
                raise ValueError("Comment text cannot be empty")
            
            prompt = self._build_sentiment_analysis_prompt(comment_text)
            
            response = self._call_ollama(prompt)
            if not response:
                return self._get_fallback_sentiment_analysis()
            
            # Parse LLM response
            analysis = self._parse_sentiment_response(response)
            
            return {
                'status': 'success',
                'sentiment': analysis.get('sentiment', 'neutral'),
                'confidence': analysis.get('confidence', 0.5),
                'themes': analysis.get('themes', []),
                'category': analysis.get('category', 'general'),
                'urgency': analysis.get('urgency', 'low')
            }
            
        except Exception as e:
            current_app.logger.error(f"Error in sentiment analysis: {str(e)}")
            return self._get_fallback_sentiment_analysis()
    
    def categorize_comments(self, comments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Categorize a list of comments by themes and importance.
        
        Args:
            comments: List of comment dictionaries
            
        Returns:
            Dictionary containing categorization results
        """
        try:
            if not comments:
                return {
                    'status': 'success',
                    'categories': {},
                    'themes': [],
                    'priority_comments': []
                }
            
            # Prepare comments for analysis
            comment_texts = []
            for i, comment in enumerate(comments[:20]):  # Limit to 20 comments
                text = comment.get('comment_text', comment.get('comment', ''))
                if text.strip():
                    comment_texts.append(f"{i+1}. {text}")
            
            if not comment_texts:
                return self._get_empty_categorization()
            
            prompt = self._build_categorization_prompt(comment_texts)
            
            response = self._call_ollama(prompt)
            if not response:
                return self._get_fallback_categorization(comments)
            
            # Parse LLM response
            analysis = self._parse_categorization_response(response)
            
            return {
                'status': 'success',
                'categories': analysis.get('categories', {}),
                'themes': analysis.get('themes', []),
                'priority_comments': analysis.get('priority_comments', []),
                'summary': analysis.get('summary', '')
            }
            
        except Exception as e:
            current_app.logger.error(f"Error in comment categorization: {str(e)}")
            return self._get_fallback_categorization(comments)
    
    def generate_comment_suggestions(self, selected_text: str, context: str) -> List[str]:
        """
        Generate suggested comments for selected text.
        
        Args:
            selected_text: The text that was selected
            context: Surrounding context
            
        Returns:
            List of suggested comment texts
        """
        try:
            if not selected_text.strip():
                return []
            
            prompt = self._build_suggestion_prompt(selected_text, context)
            
            response = self._call_ollama(prompt)
            if not response:
                return self._get_fallback_suggestions(selected_text)
            
            # Parse suggestions from response
            suggestions = self._parse_suggestions_response(response)
            
            return suggestions[:5]  # Return top 5 suggestions
            
        except Exception as e:
            current_app.logger.error(f"Error generating comment suggestions: {str(e)}")
            return self._get_fallback_suggestions(selected_text)
    
    def extract_key_themes(self, text_content: str, comments: List[Dict[str, Any]]) -> List[str]:
        """
        Extract key themes from text content and associated comments.
        
        Args:
            text_content: Main text content
            comments: List of comment dictionaries
            
        Returns:
            List of key themes
        """
        try:
            if not text_content.strip() and not comments:
                return []
            
            # Prepare content for analysis
            content_preview = text_content[:2000] if text_content else ""
            comment_texts = [
                comment.get('comment_text', comment.get('comment', ''))
                for comment in comments[:10]  # Limit to 10 comments
            ]
            comment_texts = [text for text in comment_texts if text.strip()]
            
            prompt = self._build_theme_extraction_prompt(content_preview, comment_texts)
            
            response = self._call_ollama(prompt)
            if not response:
                return self._get_fallback_themes(text_content, comments)
            
            # Parse themes from response
            themes = self._parse_themes_response(response)
            
            return themes[:10]  # Return top 10 themes
            
        except Exception as e:
            current_app.logger.error(f"Error extracting themes: {str(e)}")
            return self._get_fallback_themes(text_content, comments)
    
    def _call_ollama(self, prompt: str) -> Optional[str]:
        """
        Make a call to the Ollama API.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            Response text if successful, None otherwise
        """
        try:
            # Check if Ollama is available
            status = self.ollama.check_model_availability()
            if status['status'] != 'available':
                current_app.logger.warning(f"Ollama model not available: {status.get('message')}")
                return None
            
            # Prepare request
            payload = {
                'model': self.ollama.model,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.3,  # Lower temperature for more consistent results
                    'top_p': 0.9,
                    'max_tokens': 1000
                }
            }
            
            # Make request
            response = requests.post(
                f"{self.ollama.url}/api/generate",
                json=payload,
                timeout=60  # Longer timeout for LLM processing
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                current_app.logger.error(f"Ollama API error: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            current_app.logger.error("Ollama API timeout")
            return None
        except Exception as e:
            current_app.logger.error(f"Error calling Ollama API: {str(e)}")
            return None
    
    def _build_section_analysis_prompt(self, content: str) -> str:
        """Build prompt for section analysis."""
        return f"""Analyze the following text and identify logical sections, themes, and provide a brief summary.

Text to analyze:
{content}

Please respond in JSON format with the following structure:
{{
    "sections": [
        {{"title": "Section Title", "start_line": 1, "end_line": 10, "theme": "Main theme"}},
        ...
    ],
    "themes": ["theme1", "theme2", ...],
    "summary": "Brief summary of the content",
    "confidence": 0.8
}}

Focus on identifying clear section boundaries and main themes."""
    
    def _build_sentiment_analysis_prompt(self, comment_text: str) -> str:
        """Build prompt for sentiment analysis."""
        return f"""Analyze the sentiment and themes of this comment:

Comment: "{comment_text}"

Please respond in JSON format:
{{
    "sentiment": "positive|negative|neutral",
    "confidence": 0.8,
    "themes": ["theme1", "theme2"],
    "category": "suggestion|concern|question|praise|criticism",
    "urgency": "low|medium|high"
}}

Consider the tone, content, and implied meaning."""
    
    def _build_categorization_prompt(self, comment_texts: List[str]) -> str:
        """Build prompt for comment categorization."""
        comments_text = "\n".join(comment_texts)
        return f"""Categorize these comments by themes and identify priority items:

Comments:
{comments_text}

Please respond in JSON format:
{{
    "categories": {{
        "suggestions": [1, 3, 5],
        "concerns": [2, 4],
        "questions": [6]
    }},
    "themes": ["theme1", "theme2"],
    "priority_comments": [2, 4],
    "summary": "Brief summary of comment patterns"
}}

Use comment numbers to reference specific comments."""
    
    def _build_suggestion_prompt(self, selected_text: str, context: str) -> str:
        """Build prompt for comment suggestions."""
        return f"""Generate helpful comment suggestions for this selected text:

Selected text: "{selected_text}"
Context: "{context[:500]}"

Please provide 3-5 relevant comment suggestions that could help improve or clarify this text.
Respond with a simple list, one suggestion per line, without numbering."""
    
    def _build_theme_extraction_prompt(self, content: str, comment_texts: List[str]) -> str:
        """Build prompt for theme extraction."""
        comments_text = "\n".join(f"- {text}" for text in comment_texts)
        return f"""Extract key themes from this content and related comments:

Content preview:
{content}

Related comments:
{comments_text}

Please list the main themes, one per line, without numbering or bullets."""
    
    def _parse_section_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse section analysis response from LLM."""
        try:
            # Try to extract JSON from response
            if '{' in response and '}' in response:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except:
            pass
        
        # Fallback parsing
        return {
            'sections': [],
            'themes': [],
            'summary': response[:200] if response else '',
            'confidence': 0.3
        }
    
    def _parse_sentiment_response(self, response: str) -> Dict[str, Any]:
        """Parse sentiment analysis response from LLM."""
        try:
            if '{' in response and '}' in response:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except:
            pass
        
        # Fallback parsing
        sentiment = 'neutral'
        if any(word in response.lower() for word in ['positive', 'good', 'excellent', 'great']):
            sentiment = 'positive'
        elif any(word in response.lower() for word in ['negative', 'bad', 'poor', 'concern']):
            sentiment = 'negative'
        
        return {
            'sentiment': sentiment,
            'confidence': 0.3,
            'themes': [],
            'category': 'general',
            'urgency': 'low'
        }
    
    def _parse_categorization_response(self, response: str) -> Dict[str, Any]:
        """Parse categorization response from LLM."""
        try:
            if '{' in response and '}' in response:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except:
            pass
        
        return {
            'categories': {},
            'themes': [],
            'priority_comments': [],
            'summary': response[:200] if response else ''
        }
    
    def _parse_suggestions_response(self, response: str) -> List[str]:
        """Parse suggestions response from LLM."""
        if not response:
            return []
        
        # Split by lines and clean up
        suggestions = []
        for line in response.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # Remove numbering if present
                if line[0].isdigit() and '.' in line[:5]:
                    line = line.split('.', 1)[1].strip()
                if line.startswith('- '):
                    line = line[2:].strip()
                if line:
                    suggestions.append(line)
        
        return suggestions
    
    def _parse_themes_response(self, response: str) -> List[str]:
        """Parse themes response from LLM."""
        if not response:
            return []
        
        themes = []
        for line in response.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # Remove bullets and numbering
                if line.startswith('- '):
                    line = line[2:].strip()
                if line[0].isdigit() and '.' in line[:5]:
                    line = line.split('.', 1)[1].strip()
                if line:
                    themes.append(line)
        
        return themes
    
    def _get_fallback_section_analysis(self, content: str) -> Dict[str, Any]:
        """Provide fallback section analysis when LLM is unavailable."""
        return {
            'status': 'fallback',
            'sections': [{
                'title': 'Main Content',
                'start_line': 1,
                'end_line': len(content.split('\n')),
                'theme': 'General content'
            }],
            'themes': ['General content'],
            'summary': 'Content analysis unavailable - LLM service not accessible',
            'confidence': 0.1
        }
    
    def _get_fallback_sentiment_analysis(self) -> Dict[str, Any]:
        """Provide fallback sentiment analysis when LLM is unavailable."""
        return {
            'status': 'fallback',
            'sentiment': 'neutral',
            'confidence': 0.1,
            'themes': [],
            'category': 'general',
            'urgency': 'low'
        }
    
    def _get_fallback_categorization(self, comments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Provide fallback categorization when LLM is unavailable."""
        return {
            'status': 'fallback',
            'categories': {'general': list(range(1, min(len(comments) + 1, 21)))},
            'themes': ['General feedback'],
            'priority_comments': [],
            'summary': 'Comment categorization unavailable - LLM service not accessible'
        }
    
    def _get_empty_categorization(self) -> Dict[str, Any]:
        """Provide empty categorization result."""
        return {
            'status': 'success',
            'categories': {},
            'themes': [],
            'priority_comments': [],
            'summary': 'No comments to categorize'
        }
    
    def _get_fallback_suggestions(self, selected_text: str) -> List[str]:
        """Provide fallback suggestions when LLM is unavailable."""
        return [
            f"Consider clarifying this section: '{selected_text[:50]}...'",
            "This might need more explanation",
            "Could this be simplified?",
            "Is this information accurate?",
            "Consider adding an example here"
        ]
    
    def _get_fallback_themes(self, text_content: str, comments: List[Dict[str, Any]]) -> List[str]:
        """Provide fallback themes when LLM is unavailable."""
        themes = ['General content']
        
        # Simple keyword-based theme detection
        if text_content:
            content_lower = text_content.lower()
            if 'security' in content_lower or 'secure' in content_lower:
                themes.append('Security')
            if 'performance' in content_lower or 'speed' in content_lower:
                themes.append('Performance')
            if 'user' in content_lower or 'interface' in content_lower:
                themes.append('User Experience')
            if 'data' in content_lower or 'database' in content_lower:
                themes.append('Data Management')
        
        return themes[:5]