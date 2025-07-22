import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Box,
  Typography,
  Paper,
  IconButton,
  Chip,
  Divider,
} from '@mui/material';
import {
  Close as CloseIcon,
  Comment as CommentIcon,
  FormatQuote as QuoteIcon,
  Send as SendIcon,
  Person as PersonIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';

const CommentModal = ({ open, onClose, onSave, selectedText }) => {
  const [comment, setComment] = useState('');
  const [author, setAuthor] = useState('Expert');
  const [loading, setLoading] = useState(false);

  // Reset form when modal opens/closes
  useEffect(() => {
    if (open) {
      setComment('');
      setAuthor('Expert');
    }
  }, [open]);

  const handleSave = async () => {
    if (!comment.trim()) {
      return;
    }

    setLoading(true);
    try {
      await onSave({
        comment: comment.trim(),
        author: author.trim() || 'Expert',
      });
      onClose();
    } catch (error) {
      console.error('Error saving comment:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      handleSave();
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <Dialog
          open={open}
          onClose={onClose}
          maxWidth="md"
          fullWidth
          PaperProps={{
            component: motion.div,
            initial: { opacity: 0, scale: 0.9, y: 50 },
            animate: { opacity: 1, scale: 1, y: 0 },
            exit: { opacity: 0, scale: 0.9, y: 50 },
            transition: { duration: 0.3, ease: 'easeOut' },
            sx: {
              borderRadius: 3,
              overflow: 'hidden',
            },
          }}
        >
          {/* Header */}
          <DialogTitle
            sx={{
              bgcolor: 'primary.main',
              color: 'white',
              display: 'flex',
              alignItems: 'center',
              gap: 2,
              py: 2,
            }}
          >
            <CommentIcon />
            <Typography variant="h6" sx={{ flex: 1, fontWeight: 600 }}>
              Add Comment
            </Typography>
            <IconButton
              onClick={onClose}
              sx={{ color: 'white' }}
              size="small"
            >
              <CloseIcon />
            </IconButton>
          </DialogTitle>

          <DialogContent sx={{ p: 0 }}>
            <Box sx={{ p: 3 }}>
              {/* Selected Text Preview */}
              <Box sx={{ mb: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <QuoteIcon sx={{ color: 'primary.main', fontSize: 20 }} />
                  <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                    Selected Text
                  </Typography>
                  <Chip 
                    label={`${selectedText?.length || 0} characters`} 
                    size="small" 
                    color="primary"
                    variant="outlined"
                  />
                </Box>
                
                <Paper
                  elevation={0}
                  sx={{
                    p: 3,
                    bgcolor: 'primary.50',
                    border: '2px solid',
                    borderColor: 'primary.200',
                    borderRadius: 2,
                    position: 'relative',
                    overflow: 'hidden',
                  }}
                >
                  <Box
                    sx={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: 4,
                      bgcolor: 'primary.main',
                    }}
                  />
                  <Typography
                    variant="body1"
                    sx={{
                      fontStyle: 'italic',
                      color: 'primary.dark',
                      lineHeight: 1.6,
                      fontSize: '1rem',
                      maxHeight: 120,
                      overflow: 'auto',
                    }}
                  >
                    "{selectedText || 'No text selected'}"
                  </Typography>
                </Paper>
              </Box>

              <Divider sx={{ my: 3 }} />

              {/* Author Input */}
              <Box sx={{ mb: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <PersonIcon sx={{ color: 'secondary.main', fontSize: 20 }} />
                  <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                    Author
                  </Typography>
                </Box>
                <TextField
                  fullWidth
                  value={author}
                  onChange={(e) => setAuthor(e.target.value)}
                  placeholder="Enter your name"
                  variant="outlined"
                  size="small"
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      borderRadius: 2,
                    },
                  }}
                />
              </Box>

              {/* Comment Input */}
              <Box sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <CommentIcon sx={{ color: 'success.main', fontSize: 20 }} />
                  <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                    Your Comment
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    (Ctrl+Enter to save)
                  </Typography>
                </Box>
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Enter your comment here..."
                  variant="outlined"
                  autoFocus
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      borderRadius: 2,
                    },
                    '& .MuiInputBase-input': {
                      fontSize: '1rem',
                      lineHeight: 1.6,
                    },
                  }}
                />
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    {comment.length} characters
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Minimum 3 characters required
                  </Typography>
                </Box>
              </Box>
            </Box>
          </DialogContent>

          {/* Actions */}
          <DialogActions
            sx={{
              p: 3,
              pt: 0,
              gap: 2,
            }}
          >
            <Button
              onClick={onClose}
              variant="outlined"
              size="large"
              sx={{ minWidth: 100 }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              variant="contained"
              size="large"
              disabled={!comment.trim() || comment.trim().length < 3 || loading}
              startIcon={loading ? null : <SendIcon />}
              sx={{ minWidth: 120 }}
            >
              {loading ? 'Saving...' : 'Save Comment'}
            </Button>
          </DialogActions>
        </Dialog>
      )}
    </AnimatePresence>
  );
};

export default CommentModal;