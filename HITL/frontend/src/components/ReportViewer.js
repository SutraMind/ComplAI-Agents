import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Paper,
  Typography,
  Box,
  Skeleton,
  Chip,
  Divider,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Description as DocumentIcon,
  Visibility as ViewIcon,
  Comment as CommentIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';

const ReportViewer = ({ report, comments, onTextSelection, loading }) => {
  const [selectedRange, setSelectedRange] = useState(null);
  const [highlightedComments, setHighlightedComments] = useState([]);
  const contentRef = useRef(null);

  // Process comments to create highlights
  useEffect(() => {
    if (comments && comments.length > 0) {
      setHighlightedComments(comments);
    } else {
      setHighlightedComments([]);
    }
  }, [comments]);

  // Handle text selection
  const handleMouseUp = useCallback(() => {
    const selection = window.getSelection();
    
    if (!selection.rangeCount || selection.isCollapsed) {
      setSelectedRange(null);
      return;
    }

    const range = selection.getRangeAt(0);
    const selectedText = selection.toString().trim();
    
    if (!selectedText || selectedText.length < 3) {
      setSelectedRange(null);
      return;
    }

    // Check if selection is within the report content
    if (!contentRef.current || !contentRef.current.contains(range.commonAncestorContainer)) {
      setSelectedRange(null);
      return;
    }

    // Calculate text offsets
    const startOffset = getTextOffset(range.startContainer, range.startOffset);
    const endOffset = getTextOffset(range.endContainer, range.endOffset);

    // Get section context
    const sectionContext = getSectionContext(range);

    const selectionData = {
      text: selectedText,
      startOffset,
      endOffset,
      sectionContext,
      range: range.cloneRange(),
    };

    setSelectedRange(selectionData);
    
    // Trigger callback with selection data
    if (onTextSelection) {
      onTextSelection(selectionData);
    }

    // Clear the selection visually
    setTimeout(() => {
      selection.removeAllRanges();
    }, 100);
  }, [onTextSelection]);

  // Get text offset within the document
  const getTextOffset = (node, offset) => {
    if (!contentRef.current) return 0;

    const walker = document.createTreeWalker(
      contentRef.current,
      NodeFilter.SHOW_TEXT,
      null,
      false
    );

    let textOffset = 0;
    let currentNode;

    while (currentNode = walker.nextNode()) {
      if (currentNode === node) {
        return textOffset + offset;
      }
      textOffset += currentNode.textContent.length;
    }

    return textOffset;
  };

  // Get section context for selection
  const getSectionContext = (range) => {
    let container = range.commonAncestorContainer;
    
    // Find the nearest section element
    while (container && container.nodeType !== Node.ELEMENT_NODE) {
      container = container.parentNode;
    }
    
    while (container && !container.classList?.contains('report-section')) {
      container = container.parentNode;
    }
    
    if (container) {
      const titleElement = container.querySelector('.section-title');
      return titleElement ? titleElement.textContent : 'Unknown Section';
    }
    
    return 'Main Content';
  };

  // Render report content with highlights
  const renderContent = () => {
    if (!report || !report.content) {
      return (
        <Box sx={{ textAlign: 'center', py: 8 }}>
          <DocumentIcon sx={{ fontSize: 64, color: 'grey.300', mb: 2 }} />
          <Typography variant="h6" color="text.secondary">
            No report selected
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Choose a report from the dropdown to start reviewing
          </Typography>
        </Box>
      );
    }

    // If we have sections, render them
    if (report.sections && report.sections.length > 0) {
      return report.sections.map((section, index) => (
        <motion.div
          key={section.id || index}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: index * 0.1 }}
          className="report-section"
          style={{ marginBottom: '2rem' }}
        >
          {section.title && (
            <Typography 
              variant="h5" 
              className="section-title"
              sx={{ 
                mb: 2, 
                color: 'primary.main',
                fontWeight: 600,
                borderBottom: '2px solid',
                borderColor: 'primary.main',
                pb: 1,
              }}
            >
              {section.title}
            </Typography>
          )}
          <Typography 
            variant="body1" 
            component="div"
            sx={{ 
              lineHeight: 1.8,
              fontSize: '1rem',
              color: 'text.primary',
              whiteSpace: 'pre-wrap',
              userSelect: 'text',
              cursor: 'text',
            }}
          >
            {renderTextWithHighlights(section.content)}
          </Typography>
        </motion.div>
      ));
    }

    // Render plain content
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="report-section"
      >
        <Typography 
          variant="body1" 
          component="div"
          sx={{ 
            lineHeight: 1.8,
            fontSize: '1rem',
            color: 'text.primary',
            whiteSpace: 'pre-wrap',
            userSelect: 'text',
            cursor: 'text',
          }}
        >
          {renderTextWithHighlights(report.content)}
        </Typography>
      </motion.div>
    );
  };

  // Render text with comment highlights
  const renderTextWithHighlights = (text) => {
    if (!highlightedComments.length) {
      return text;
    }

    // Sort comments by start position
    const sortedComments = [...highlightedComments].sort(
      (a, b) => (a.text_selection?.start_position || 0) - (b.text_selection?.start_position || 0)
    );

    let lastIndex = 0;
    const elements = [];

    sortedComments.forEach((comment, index) => {
      const selection = comment.text_selection;
      if (!selection) return;

      const start = selection.start_position || 0;
      const end = selection.end_position || 0;
      const selectedText = selection.selected_text || '';

      // Add text before highlight
      if (start > lastIndex) {
        elements.push(
          <span key={`text-${index}`}>
            {text.substring(lastIndex, start)}
          </span>
        );
      }

      // Add highlighted text
      elements.push(
        <Tooltip
          key={`highlight-${index}`}
          title={
            <Box>
              <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                Comment by {comment.author}
              </Typography>
              <Typography variant="body2">
                {comment.comment_text}
              </Typography>
            </Box>
          }
          arrow
          placement="top"
        >
          <span
            style={{
              backgroundColor: '#fef3c7',
              borderBottom: '2px solid #f59e0b',
              cursor: 'pointer',
              padding: '2px 0',
              borderRadius: '2px',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={(e) => {
              e.target.style.backgroundColor = '#fde68a';
              e.target.style.boxShadow = '0 2px 4px rgba(245, 158, 11, 0.3)';
            }}
            onMouseLeave={(e) => {
              e.target.style.backgroundColor = '#fef3c7';
              e.target.style.boxShadow = 'none';
            }}
          >
            {selectedText}
          </span>
        </Tooltip>
      );

      lastIndex = end;
    });

    // Add remaining text
    if (lastIndex < text.length) {
      elements.push(
        <span key="text-end">
          {text.substring(lastIndex)}
        </span>
      );
    }

    return elements;
  };

  if (loading) {
    return (
      <Paper 
        elevation={0}
        sx={{ 
          p: 3, 
          height: '100%',
          border: '1px solid',
          borderColor: 'grey.200',
          borderRadius: 3,
        }}
      >
        <Skeleton variant="text" width="60%" height={40} sx={{ mb: 2 }} />
        <Skeleton variant="text" width="100%" height={20} sx={{ mb: 1 }} />
        <Skeleton variant="text" width="100%" height={20} sx={{ mb: 1 }} />
        <Skeleton variant="text" width="80%" height={20} sx={{ mb: 3 }} />
        <Skeleton variant="rectangular" width="100%" height={200} />
      </Paper>
    );
  }

  return (
    <Paper 
      elevation={0}
      sx={{ 
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        border: '1px solid',
        borderColor: 'grey.200',
        borderRadius: 3,
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <Box 
        sx={{ 
          p: 3, 
          pb: 2,
          bgcolor: 'grey.50',
          borderBottom: '1px solid',
          borderColor: 'grey.200',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
          <ViewIcon sx={{ color: 'primary.main' }} />
          <Typography variant="h5" sx={{ fontWeight: 600, color: 'text.primary' }}>
            {report?.filename || 'Report Viewer'}
          </Typography>
        </Box>
        
        {report && (
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip 
              label={`${report.metadata?.line_count || 0} lines`} 
              size="small" 
              color="primary"
              variant="outlined"
            />
            <Chip 
              label={`${Math.round((report.metadata?.file_size || 0) / 1024)} KB`} 
              size="small" 
              color="secondary"
              variant="outlined"
            />
            <Chip 
              label={`${highlightedComments.length} comments`} 
              size="small" 
              color="success"
              variant="outlined"
              icon={<CommentIcon />}
            />
          </Box>
        )}
      </Box>

      {/* Content */}
      <Box 
        ref={contentRef}
        onMouseUp={handleMouseUp}
        sx={{ 
          flex: 1,
          p: 3,
          overflow: 'auto',
          cursor: 'text',
          '&::selection': {
            backgroundColor: '#3b82f6',
            color: 'white',
          },
        }}
      >
        <AnimatePresence mode="wait">
          {renderContent()}
        </AnimatePresence>
      </Box>

      {/* Selection indicator */}
      <AnimatePresence>
        {selectedRange && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.2 }}
          >
            <Box 
              sx={{ 
                p: 2, 
                bgcolor: 'primary.main',
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                gap: 2,
              }}
            >
              <CommentIcon />
              <Typography variant="body2">
                Text selected: "{selectedRange.text.substring(0, 50)}..."
              </Typography>
              <Typography variant="body2" sx={{ opacity: 0.8 }}>
                Click to add comment
              </Typography>
            </Box>
          </motion.div>
        )}
      </AnimatePresence>
    </Paper>
  );
};

export default ReportViewer;