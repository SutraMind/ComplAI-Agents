import React, { useState, useEffect } from 'react';
import {
    Box,
    Container,
    Grid,
    AppBar,
    Toolbar,
    Typography,
    Button,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    CircularProgress,
    Alert,
    Fade,
    Chip,
} from '@mui/material';
import {
    Description as ReportIcon,
    Comment as CommentIcon,
    AutoAwesome as SummaryIcon,
    Refresh as RefreshIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-toastify';

import ReportViewer from './components/ReportViewer';
import CommentsSidebar from './components/CommentsSidebar';
import CommentModal from './components/CommentModal';
import SummaryModal from './components/SummaryModal';
import apiService from './services/apiService';

function App() {
    const [reports, setReports] = useState([]);
    const [selectedReport, setSelectedReport] = useState(null);
    const [currentReport, setCurrentReport] = useState(null);
    const [comments, setComments] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // Modal states
    const [commentModalOpen, setCommentModalOpen] = useState(false);
    const [summaryModalOpen, setSummaryModalOpen] = useState(false);
    const [selectedText, setSelectedText] = useState(null);

    // Load reports on component mount
    useEffect(() => {
        loadReports();
    }, []);

    // Load comments when report changes
    useEffect(() => {
        if (selectedReport) {
            loadComments(selectedReport);
        }
    }, [selectedReport]);

    const loadReports = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await apiService.getReports();
            setReports(response.data || []);

            if (response.data && response.data.length > 0) {
                toast.success(`Loaded ${response.data.length} reports`);
            } else {
                toast.info('No reports found. Add some reports to get started.');
            }
        } catch (err) {
            const errorMsg = 'Failed to load reports. Please check your connection.';
            setError(errorMsg);
            toast.error(errorMsg);
            console.error('Error loading reports:', err);
        } finally {
            setLoading(false);
        }
    };

    const loadReport = async (reportId) => {
        try {
            setLoading(true);
            setError(null);
            const response = await apiService.getReport(reportId);
            setCurrentReport(response.data);
            toast.success(`Loaded report: ${response.data.filename}`);
        } catch (err) {
            const errorMsg = 'Failed to load report content.';
            setError(errorMsg);
            toast.error(errorMsg);
            console.error('Error loading report:', err);
        } finally {
            setLoading(false);
        }
    };

    const loadComments = async (reportId) => {
        try {
            const response = await apiService.getReportComments(reportId);
            setComments(response.data || []);
        } catch (err) {
            console.error('Error loading comments:', err);
            toast.error('Failed to load comments');
        }
    };

    const handleReportSelect = (reportId) => {
        setSelectedReport(reportId);
        if (reportId) {
            loadReport(reportId);
        } else {
            setCurrentReport(null);
            setComments([]);
        }
    };

    const handleTextSelection = (selection) => {
        if (selection && selection.text && selection.text.trim()) {
            setSelectedText(selection);
            setCommentModalOpen(true);
        }
    };

    const handleCommentSave = async (commentData) => {
        try {
            const response = await apiService.createComment(selectedReport, {
                text_selection: {
                    start_position: selectedText.startOffset,
                    end_position: selectedText.endOffset,
                    selected_text: selectedText.text,
                },
                comment_text: commentData.comment,
                author: commentData.author || 'Expert',
                section_context: selectedText.sectionContext || '',
            });

            // Add new comment to the list
            setComments(prev => [...prev, response.data]);

            // Close modal and clear selection
            setCommentModalOpen(false);
            setSelectedText(null);

            toast.success('Comment added successfully!');
        } catch (err) {
            console.error('Error saving comment:', err);
            toast.error('Failed to save comment');
        }
    };

    const handleCommentDelete = async (commentId) => {
        try {
            await apiService.deleteComment(commentId);
            setComments(prev => prev.filter(c => c.id !== commentId));
            toast.success('Comment deleted successfully!');
        } catch (err) {
            console.error('Error deleting comment:', err);
            toast.error('Failed to delete comment');
        }
    };

    const handleCommentEdit = async (commentId, newText) => {
        try {
            const response = await apiService.updateComment(commentId, newText);
            setComments(prev => prev.map(c => 
                c.id === commentId ? { ...c, comment_text: newText } : c
            ));
            toast.success('Comment updated successfully!');
        } catch (err) {
            console.error('Error updating comment:', err);
            toast.error('Failed to update comment');
        }
    };

    const handleSaveComments = async () => {
        try {
            if (!currentReport || comments.length === 0) {
                toast.warning('No report or comments to save');
                return;
            }

            // Call backend API to save feedback file
            const response = await apiService.saveFeedbackFile(selectedReport);
            
            if (response.success) {
                toast.success(`Feedback file saved: ${response.data.filename}`);
                toast.info(`${response.data.comments_count} comments included in feedback`);
            } else {
                throw new Error(response.error || 'Failed to save feedback file');
            }
        } catch (err) {
            console.error('Error saving feedback:', err);
            toast.error('Failed to save feedback file');
        }
    };

    const handleGenerateSummary = () => {
        if (comments.length === 0) {
            toast.warning('No comments to summarize. Add some comments first.');
            return;
        }
        setSummaryModalOpen(true);
    };

    const selectedReportData = reports.find(r => r.id === selectedReport);

    return (
        <Box sx={{ flexGrow: 1, minHeight: '100vh', bgcolor: 'background.default' }}>
            {/* Header */}
            <AppBar
                position="sticky"
                elevation={0}
                sx={{
                    bgcolor: 'background.paper',
                    borderBottom: '1px solid',
                    borderColor: 'grey.200',
                }}
            >
                <Toolbar sx={{ py: 1 }}>
                    <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.5 }}
                        style={{ display: 'flex', alignItems: 'center', flexGrow: 1 }}
                    >
                        <ReportIcon sx={{ mr: 2, color: 'primary.main', fontSize: 32 }} />
                        <Typography
                            variant="h4"
                            component="h1"
                            sx={{
                                color: 'text.primary',
                                fontWeight: 700,
                                background: 'linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)',
                                backgroundClip: 'text',
                                WebkitBackgroundClip: 'text',
                                WebkitTextFillColor: 'transparent',
                            }}
                        >
                            HITL Report Editor
                        </Typography>
                    </motion.div>

                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <FormControl size="small" sx={{ minWidth: 200 }}>
                            <InputLabel>Select Report</InputLabel>
                            <Select
                                value={selectedReport || ''}
                                onChange={(e) => handleReportSelect(e.target.value)}
                                label="Select Report"
                                disabled={loading}
                            >
                                <MenuItem value="">
                                    <em>Choose a report...</em>
                                </MenuItem>
                                {reports.map((report) => (
                                    <MenuItem key={report.id} value={report.id}>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                            <ReportIcon fontSize="small" />
                                            {report.filename}
                                        </Box>
                                    </MenuItem>
                                ))}
                            </Select>
                        </FormControl>

                        <Button
                            variant="outlined"
                            startIcon={<RefreshIcon />}
                            onClick={loadReports}
                            disabled={loading}
                            size="small"
                        >
                            Refresh
                        </Button>

                        <Button
                            variant="contained"
                            startIcon={<SummaryIcon />}
                            onClick={handleGenerateSummary}
                            disabled={!selectedReport || comments.length === 0}
                            size="small"
                        >
                            Generate Summary
                        </Button>
                    </Box>
                </Toolbar>
            </AppBar>

            {/* Main Content */}
            <Container maxWidth={false} sx={{ py: 3, px: 3 }}>
                <AnimatePresence mode="wait">
                    {error && (
                        <motion.div
                            initial={{ opacity: 0, y: -20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            transition={{ duration: 0.3 }}
                        >
                            <Alert
                                severity="error"
                                sx={{ mb: 3, borderRadius: 2 }}
                                action={
                                    <Button color="inherit" size="small" onClick={loadReports}>
                                        Retry
                                    </Button>
                                }
                            >
                                {error}
                            </Alert>
                        </motion.div>
                    )}
                </AnimatePresence>

                {loading && (
                    <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                        <CircularProgress size={40} />
                    </Box>
                )}

                {!loading && !error && (
                    <Grid container spacing={3} sx={{ height: 'calc(100vh - 200px)' }}>
                        {/* Report Viewer */}
                        <Grid item xs={12} md={8}>
                            <motion.div
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ duration: 0.5, delay: 0.1 }}
                                style={{ height: '100%' }}
                            >
                                <ReportViewer
                                    report={currentReport}
                                    comments={comments}
                                    onTextSelection={handleTextSelection}
                                    loading={loading}
                                />
                            </motion.div>
                        </Grid>

                        {/* Comments Sidebar */}
                        <Grid item xs={12} md={4}>
                            <motion.div
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ duration: 0.5, delay: 0.2 }}
                                style={{ height: '100%' }}
                            >
                                <CommentsSidebar
                                    comments={comments}
                                    onCommentDelete={handleCommentDelete}
                                    onCommentEdit={handleCommentEdit}
                                    onSaveComments={handleSaveComments}
                                    reportTitle={selectedReportData?.filename}
                                />
                            </motion.div>
                        </Grid>
                    </Grid>
                )}

                {/* Status Bar */}
                {selectedReportData && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5, delay: 0.3 }}
                    >
                        <Box
                            sx={{
                                mt: 2,
                                p: 2,
                                bgcolor: 'background.paper',
                                borderRadius: 2,
                                border: '1px solid',
                                borderColor: 'grey.200',
                                display: 'flex',
                                alignItems: 'center',
                                gap: 2,
                            }}
                        >
                            <Typography variant="body2" color="text.secondary">
                                Report Status:
                            </Typography>
                            <Chip
                                label={`${comments.length} Comments`}
                                color="primary"
                                size="small"
                                icon={<CommentIcon />}
                            />
                            <Chip
                                label={`${selectedReportData.line_count} Lines`}
                                color="secondary"
                                size="small"
                            />
                            <Chip
                                label={`${Math.round(selectedReportData.file_size / 1024)} KB`}
                                color="default"
                                size="small"
                            />
                        </Box>
                    </motion.div>
                )}
            </Container>

            {/* Modals */}
            <CommentModal
                open={commentModalOpen}
                onClose={() => {
                    setCommentModalOpen(false);
                    setSelectedText(null);
                }}
                onSave={handleCommentSave}
                selectedText={selectedText?.text || ''}
            />

            <SummaryModal
                open={summaryModalOpen}
                onClose={() => setSummaryModalOpen(false)}
                reportId={selectedReport}
                comments={comments}
            />
        </Box>
    );
}

export default App;