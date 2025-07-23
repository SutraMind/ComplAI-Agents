import React, { useState } from 'react';
import {
  Paper,
  Typography,
  Box,
  List,
  ListItem,
  IconButton,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Avatar,
  Tooltip,
  Badge,
} from '@mui/material';
import {
  Comment as CommentIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Schedule as TimeIcon,
  Clear as ClearIcon,
  FormatQuote as QuoteIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-toastify';

const CommentsSidebar = ({ comments, onCommentDelete, onCommentEdit, reportTitle, onSaveComments }) => {
  const [editingComment, setEditingComment] = useState(null);
  const [editText, setEditText] = useState('');
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [commentToDelete, setCommentToDelete] = useState(null);

  const handleEditStart = (comment) => {
    setEditingComment(comment.id);
    setEditText(comment.comment_text);
  };

  const handleEditCancel = () => {
    setEditingComment(null);
    setEditText('');
  };

  const handleEditSave = async () => {
    try {
      if (!editText.trim()) {
        toast.error('Comment text cannot be empty');
        return;
      }

      if (onCommentEdit) {
        await onCommentEdit(editingComment, editText.trim());
        toast.success('Comment updated successfully!');
      }

      handleEditCancel();
    } catch (err) {
      console.error('Error updating comment:', err);
      toast.error('Failed to update comment');
    }
  };

  const handleDeleteClick = (comment) => {
    setCommentToDelete(comment);
    setDeleteConfirmOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (commentToDelete && onCommentDelete) {
      await onCommentDelete(commentToDelete.id);
    }
    setDeleteConfirmOpen(false);
    setCommentToDelete(null);
  };

  const handleDeleteCancel = () => {
    setDeleteConfirmOpen(false);
    setCommentToDelete(null);
  };

  const formatDate = (dateString) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return 'Unknown';
    }
  };

  const getAuthorColor = (author) => {
    const colors = ['#2563eb', '#7c3aed', '#059669', '#dc2626', '#ea580c'];
    const hash = author.split('').reduce((a, b) => {
      a = ((a << 5) - a) + b.charCodeAt(0);
      return a & a;
    }, 0);
    return colors[Math.abs(hash) % colors.length];
  };

  const sortedComments = [...comments].sort((a, b) => {
    const aPos = a.text_selection?.start_position || 0;
    const bPos = b.text_selection?.start_position || 0;
    return aPos - bPos;
  });

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
          <Badge badgeContent={comments.length} color="primary">
            <CommentIcon sx={{ color: 'primary.main' }} />
          </Badge>
          <Typography variant="h6" sx={{ fontWeight: 600, color: 'text.primary' }}>
            Comments
          </Typography>
        </Box>

        {reportTitle && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            On: {reportTitle}
          </Typography>
        )}

        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
          <Chip
            label={`${comments.length} total`}
            size="small"
            color="primary"
            variant="outlined"
          />
          {comments.length > 0 && (
            <>
              <Button
                variant="contained"
                size="small"
                onClick={onSaveComments}
                sx={{ minWidth: 'auto', px: 2 }}
              >
                Save Feedback
              </Button>
              <Tooltip title="Clear all comments">
                <IconButton
                  size="small"
                  color="error"
                  onClick={() => toast.info('Clear all functionality coming soon!')}
                >
                  <ClearIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </>
          )}
        </Box>
      </Box>

      {/* Comments List */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {comments.length === 0 ? (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              p: 3,
              textAlign: 'center',
            }}
          >
            <CommentIcon sx={{ fontSize: 64, color: 'grey.300', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
              No comments yet
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Select text in the report to add your first comment
            </Typography>
          </Box>
        ) : (
          <List sx={{ p: 0 }}>
            <AnimatePresence>
              {sortedComments.map((comment, index) => (
                <motion.div
                  key={comment.id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                >
                  <ListItem
                    sx={{
                      flexDirection: 'column',
                      alignItems: 'stretch',
                      p: 3,
                      borderBottom: '1px solid',
                      borderColor: 'grey.100',
                      '&:hover': {
                        bgcolor: 'grey.50',
                      },
                    }}
                  >
                    {/* Comment Header */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                      <Avatar
                        sx={{
                          width: 32,
                          height: 32,
                          bgcolor: getAuthorColor(comment.author),
                          fontSize: '0.875rem',
                        }}
                      >
                        {comment.author.charAt(0).toUpperCase()}
                      </Avatar>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                          {comment.author}
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <TimeIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                          <Typography variant="caption" color="text.secondary">
                            {formatDate(comment.timestamp)}
                          </Typography>
                        </Box>
                      </Box>
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        <Tooltip title="Edit comment">
                          <IconButton
                            size="small"
                            onClick={() => handleEditStart(comment)}
                            sx={{ color: 'primary.main' }}
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Delete comment">
                          <IconButton
                            size="small"
                            onClick={() => handleDeleteClick(comment)}
                            sx={{ color: 'error.main' }}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </Box>

                    {/* Selected Text */}
                    <Box
                      sx={{
                        bgcolor: 'primary.50',
                        border: '1px solid',
                        borderColor: 'primary.200',
                        borderRadius: 2,
                        p: 2,
                        mb: 2,
                        position: 'relative',
                      }}
                    >
                      <QuoteIcon
                        sx={{
                          position: 'absolute',
                          top: 8,
                          left: 8,
                          fontSize: 16,
                          color: 'primary.main',
                          opacity: 0.6,
                        }}
                      />
                      <Typography
                        variant="body2"
                        sx={{
                          fontStyle: 'italic',
                          color: 'primary.dark',
                          pl: 3,
                          lineHeight: 1.5,
                        }}
                      >
                        "{comment.text_selection?.selected_text || 'No text selected'}"
                      </Typography>
                    </Box>

                    {/* Comment Text or Edit */}
                    {editingComment === comment.id ? (
                      <Box sx={{ mb: 2 }}>
                        <TextField
                          fullWidth
                          multiline
                          rows={3}
                          value={editText}
                          onChange={(e) => setEditText(e.target.value)}
                          variant="outlined"
                          size="small"
                          sx={{ mb: 2 }}
                          autoFocus
                        />
                        <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
                          <Button size="small" onClick={handleEditCancel}>
                            Cancel
                          </Button>
                          <Button
                            size="small"
                            variant="contained"
                            onClick={handleEditSave}
                            disabled={!editText.trim()}
                          >
                            Save
                          </Button>
                        </Box>
                      </Box>
                    ) : (
                      <Typography
                        variant="body1"
                        sx={{
                          mb: 2,
                          lineHeight: 1.6,
                          color: 'text.primary',
                        }}
                      >
                        {comment.comment_text}
                      </Typography>
                    )}

                    {/* Section Context */}
                    {comment.section_context && (
                      <Chip
                        label={`Section: ${comment.section_context}`}
                        size="small"
                        variant="outlined"
                        color="secondary"
                        sx={{ alignSelf: 'flex-start' }}
                      />
                    )}
                  </ListItem>
                </motion.div>
              ))}
            </AnimatePresence>
          </List>
        )}
      </Box>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteConfirmOpen}
        onClose={handleDeleteCancel}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <DeleteIcon color="error" />
            Delete Comment
          </Box>
        </DialogTitle>
        <DialogContent>
          <Typography variant="body1" sx={{ mb: 2 }}>
            Are you sure you want to delete this comment? This action cannot be undone.
          </Typography>
          {commentToDelete && (
            <Box
              sx={{
                bgcolor: 'grey.50',
                border: '1px solid',
                borderColor: 'grey.200',
                borderRadius: 2,
                p: 2,
              }}
            >
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Comment by {commentToDelete.author}:
              </Typography>
              <Typography variant="body2">
                {commentToDelete.comment_text}
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDeleteCancel}>Cancel</Button>
          <Button
            onClick={handleDeleteConfirm}
            color="error"
            variant="contained"
            startIcon={<DeleteIcon />}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};

export default CommentsSidebar;
