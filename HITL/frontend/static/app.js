// HITL Report Editor - Frontend JavaScript
// Task 6.1: Report loading and display logic

class HITLReportEditor {
    constructor() {
        this.currentReport = null;
        this.currentSelection = null;
        this.comments = [];
        this.apiBaseUrl = '/api';
        this.sessionKey = 'hitl_session';
        this.reportHashKey = 'hitl_report_hashes';
        this.lastSaveTime = null;
        this.sessionCheckInterval = null;
        
        this.initializeApp();
    }

    // Initialize the application
    initializeApp() {
        this.bindEventListeners();
        this.loadAvailableReports();
        this.restoreSession();
        this.startSessionMonitoring();
        this.showToast('HITL Report Editor initialized', 'info');
    }

    // Bind event listeners for UI interactions
    bindEventListeners() {
        // Report selector change
        const reportSelector = document.getElementById('reportSelector');
        if (reportSelector) {
            reportSelector.addEventListener('change', (e) => {
                if (e.target.value) {
                    this.loadReport(e.target.value);
                } else {
                    this.clearReportViewer();
                }
            });
        }

        // Text selection handling for comment creation
        const reportViewer = document.getElementById('reportViewer');
        if (reportViewer) {
            reportViewer.addEventListener('mouseup', () => {
                this.handleTextSelection();
            });
        }

        // Modal close handlers
        this.bindModalCloseHandlers();
        
        // Comment modal event listeners
        this.bindCommentModalEvents();
        
        // Clear comments button
        const clearCommentsBtn = document.getElementById('clearCommentsBtn');
        if (clearCommentsBtn) {
            clearCommentsBtn.addEventListener('click', () => {
                this.clearAllComments();
            });
        }
        
        // Generate summary button
        const generateSummaryBtn = document.getElementById('generateSummaryBtn');
        if (generateSummaryBtn) {
            generateSummaryBtn.addEventListener('click', () => {
                this.generateSummary();
            });
        }

        // Save feedback button
        const saveFeedbackBtn = document.getElementById('saveFeedback');
        if (saveFeedbackBtn) {
            saveFeedbackBtn.addEventListener('click', () => {
                this.saveFeedback();
            });
        }
        
        // Auto-save interval (every 30 seconds)
        setInterval(() => {
            this.autoSave();
        }, 30000);
    }

    // Bind modal close event handlers
    bindModalCloseHandlers() {
        const closeButtons = document.querySelectorAll('.modal-close');
        closeButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) {
                    this.closeModal(modal.id);
                }
            });
        });

        // Close modal when clicking outside
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.closeModal(e.target.id);
            }
        });
    }

    // Close modal by ID
    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
            
            // Special handling for summary modal
            if (modalId === 'summaryModal') {
                this.closeSummaryModal();
            }
        }
    }

    // Bind comment modal event listeners
    bindCommentModalEvents() {
        // Save comment button
        const saveCommentBtn = document.getElementById('saveComment');
        if (saveCommentBtn) {
            saveCommentBtn.addEventListener('click', () => {
                this.saveComment();
            });
        }

        // Cancel comment button
        const cancelCommentBtn = document.getElementById('cancelComment');
        if (cancelCommentBtn) {
            cancelCommentBtn.addEventListener('click', () => {
                this.closeModal('commentModal');
                this.clearSelection();
            });
        }

        // Enter key to save comment
        const commentTextArea = document.getElementById('commentText');
        if (commentTextArea) {
            commentTextArea.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    this.saveComment();
                }
            });
        }
    }

    // Load available reports from the API
    async loadAvailableReports() {
        try {
            this.showLoading(true);
            const response = await fetch(`${this.apiBaseUrl}/reports`);
            
            if (!response.ok) {
                throw new Error(`Failed to load reports: ${response.status} ${response.statusText}`);
            }

            const reports = await response.json();
            this.populateReportSelector(reports);
            
        } catch (error) {
            console.error('Error loading reports:', error);
            this.showToast(`Error loading reports: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    // Populate the report selector dropdown
    populateReportSelector(reports) {
        const selector = document.getElementById('reportSelector');
        if (!selector) return;

        // Clear existing options except the first one
        while (selector.children.length > 1) {
            selector.removeChild(selector.lastChild);
        }

        // Add report options
        reports.forEach(report => {
            const option = document.createElement('option');
            option.value = report.id;
            option.textContent = report.filename || report.id;
            selector.appendChild(option);
        });

        if (reports.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No reports available';
            option.disabled = true;
            selector.appendChild(option);
        }
    }

    // Load a specific report
    async loadReport(reportId) {
        try {
            this.showLoading(true);
            
            const response = await fetch(`${this.apiBaseUrl}/reports/${reportId}`);
            
            if (!response.ok) {
                throw new Error(`Failed to load report: ${response.status} ${response.statusText}`);
            }

            const report = await response.json();
            this.currentReport = report;
            
            // Display the report
            this.displayReport(report);
            
            // Load existing comments for this report
            await this.loadReportComments(reportId);
            
            // Validate comment positions after loading
            setTimeout(() => {
                this.validateCommentPositions();
                this.trackCommentPositions();
                this.updateGenerateSummaryButton();
            }, 100);
            
            this.showToast(`Report "${report.filename}" loaded successfully`, 'success');
            
        } catch (error) {
            console.error('Error loading report:', error);
            this.showToast(`Error loading report: ${error.message}`, 'error');
            this.clearReportViewer();
        } finally {
            this.showLoading(false);
        }
    }

    // Display report content in the viewer
    displayReport(report) {
        const reportViewer = document.getElementById('reportViewer');
        const reportTitle = document.getElementById('reportTitle');
        const reportStats = document.getElementById('reportStats');

        if (!reportViewer || !reportTitle || !reportStats) return;

        // Update title and stats
        reportTitle.textContent = report.filename || 'Untitled Report';
        
        const stats = [];
        if (report.metadata) {
            if (report.metadata.line_count) stats.push(`${report.metadata.line_count} lines`);
            if (report.metadata.file_size) stats.push(`${this.formatFileSize(report.metadata.file_size)}`);
            if (report.metadata.created_at) stats.push(`Created: ${this.formatDate(report.metadata.created_at)}`);
        }
        reportStats.textContent = stats.join(' • ');

        // Clear existing content
        reportViewer.innerHTML = '';

        // Create report content container
        const contentContainer = document.createElement('div');
        contentContainer.className = 'report-content';
        contentContainer.id = 'reportContent';

        // Process and display report content
        if (report.sections && report.sections.length > 0) {
            // Display structured sections
            report.sections.forEach((section, index) => {
                const sectionElement = this.createSectionElement(section, index);
                contentContainer.appendChild(sectionElement);
            });
        } else if (report.content) {
            // Display plain text content
            const textElement = this.createTextElement(report.content);
            contentContainer.appendChild(textElement);
        } else {
            // No content available
            const emptyElement = document.createElement('div');
            emptyElement.className = 'empty-content';
            emptyElement.innerHTML = '<p>No content available in this report.</p>';
            contentContainer.appendChild(emptyElement);
        }

        reportViewer.appendChild(contentContainer);
    }

    // Create a section element for structured reports
    createSectionElement(section, index) {
        const sectionDiv = document.createElement('div');
        sectionDiv.className = 'report-section';
        sectionDiv.dataset.sectionId = section.id || `section-${index}`;

        if (section.title) {
            const titleElement = document.createElement('h3');
            titleElement.className = 'section-title';
            titleElement.textContent = section.title;
            sectionDiv.appendChild(titleElement);
        }

        const contentElement = document.createElement('div');
        contentElement.className = 'section-content';
        contentElement.innerHTML = this.formatTextContent(section.content);
        sectionDiv.appendChild(contentElement);

        return sectionDiv;
    }

    // Create a text element for plain text reports
    createTextElement(content) {
        const textDiv = document.createElement('div');
        textDiv.className = 'report-text';
        textDiv.innerHTML = this.formatTextContent(content);
        return textDiv;
    }

    // Format text content with proper line breaks and structure
    formatTextContent(content) {
        if (!content) return '';
        
        return content
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/^/, '<p>')
            .replace(/$/, '</p>');
    }

    // Handle text selection for comment creation
    handleTextSelection() {
        const selection = window.getSelection();
        
        if (selection.rangeCount === 0 || selection.isCollapsed) {
            this.currentSelection = null;
            return;
        }

        const selectedText = selection.toString().trim();
        if (selectedText.length === 0) {
            this.currentSelection = null;
            return;
        }

        // Check if selection is within the report content
        const reportContent = document.getElementById('reportContent');
        if (!reportContent || !reportContent.contains(selection.anchorNode)) {
            this.currentSelection = null;
            return;
        }

        // Store selection information
        this.currentSelection = {
            text: selectedText,
            range: selection.getRangeAt(0).cloneRange(),
            startOffset: this.getTextOffset(selection.getRangeAt(0).startContainer, selection.getRangeAt(0).startOffset),
            endOffset: this.getTextOffset(selection.getRangeAt(0).endContainer, selection.getRangeAt(0).endOffset)
        };

        // Show comment creation option
        this.showCommentCreationOption();
    }

    // Get text offset within the document
    getTextOffset(node, offset) {
        const reportContent = document.getElementById('reportContent');
        if (!reportContent) return 0;

        const walker = document.createTreeWalker(
            reportContent,
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
    }

    // Show comment creation option
    showCommentCreationOption() {
        if (!this.currentSelection) return;
        
        // Show the comment modal with selected text
        this.openCommentModal();
    }

    // Open comment modal for creating new comment
    openCommentModal(existingComment = null) {
        const modal = document.getElementById('commentModal');
        const selectedTextPreview = document.getElementById('selectedTextPreview');
        const commentTextArea = document.getElementById('commentText');
        
        if (!modal || !selectedTextPreview || !commentTextArea) return;

        if (existingComment) {
            // Editing existing comment
            selectedTextPreview.textContent = existingComment.text_selection.selected_text;
            commentTextArea.value = existingComment.comment_text;
            modal.dataset.editingCommentId = existingComment.id;
        } else if (this.currentSelection) {
            // Creating new comment
            selectedTextPreview.textContent = this.currentSelection.text;
            commentTextArea.value = '';
            delete modal.dataset.editingCommentId;
        } else {
            return;
        }

        modal.style.display = 'flex';
        commentTextArea.focus();
    }

    // Save comment (create or update)
    async saveComment() {
        const modal = document.getElementById('commentModal');
        const commentTextArea = document.getElementById('commentText');
        
        if (!commentTextArea || !commentTextArea.value.trim()) {
            this.showToast('Please enter a comment', 'warning');
            return;
        }

        const commentText = commentTextArea.value.trim();
        const isEditing = modal.dataset.editingCommentId;

        try {
            this.showLoading(true);

            if (isEditing) {
                // Update existing comment
                await this.updateComment(modal.dataset.editingCommentId, commentText);
            } else {
                // Create new comment
                await this.createComment(commentText);
            }

            this.closeModal('commentModal');
            this.clearSelection();
            
        } catch (error) {
            console.error('Error saving comment:', error);
            this.showToast(`Error saving comment: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    // Create new comment
    async createComment(commentText) {
        if (!this.currentReport || !this.currentSelection) {
            throw new Error('No report or text selection available');
        }

        const commentData = {
            text_selection: {
                start_position: this.currentSelection.startOffset,
                end_position: this.currentSelection.endOffset,
                selected_text: this.currentSelection.text
            },
            comment_text: commentText,
            author: 'Expert', // Could be made configurable
            timestamp: new Date().toISOString(),
            section_context: this.getSectionContext()
        };

        const response = await fetch(`${this.apiBaseUrl}/reports/${this.currentReport.id}/comments`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(commentData)
        });

        if (!response.ok) {
            throw new Error(`Failed to create comment: ${response.status} ${response.statusText}`);
        }

        const responseData = await response.json();
        console.log('Create comment response:', responseData);
        
        // Handle API response structure
        const newComment = responseData.success ? responseData.data : responseData;
        
        // Add to local comments array
        this.comments.push(newComment);
        
        // Update UI
        this.renderComments();
        this.updateCommentCount();
        this.updateGenerateSummaryButton();
        
        this.showToast('Comment added successfully', 'success');
        
        return newComment;
    }

    // Update existing comment
    async updateComment(commentId, commentText) {
        const response = await fetch(`${this.apiBaseUrl}/comments/${commentId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                comment_text: commentText,
                timestamp: new Date().toISOString()
            })
        });

        if (!response.ok) {
            throw new Error(`Failed to update comment: ${response.status} ${response.statusText}`);
        }

        const responseData = await response.json();
        console.log('Update comment response:', responseData);
        
        // Handle API response structure
        const updatedComment = responseData.success ? responseData.data : responseData;
        
        // Update local comments array
        const index = this.comments.findIndex(c => c.id === commentId);
        if (index !== -1) {
            // Preserve the original text_selection data when updating
            this.comments[index] = {
                ...this.comments[index],
                ...updatedComment,
                text_selection: this.comments[index].text_selection
            };
        }
        
        // Update UI
        this.renderComments();
        this.updateCommentCount();
        this.updateGenerateSummaryButton();
        
        this.showToast('Comment updated successfully', 'success');
        
        return updatedComment;
    }

    // Delete comment
    async deleteComment(commentId) {
        if (!confirm('Are you sure you want to delete this comment?')) {
            return;
        }

        try {
            this.showLoading(true);

            const response = await fetch(`${this.apiBaseUrl}/comments/${commentId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error(`Failed to delete comment: ${response.status} ${response.statusText}`);
            }

            // Remove from local comments array
            this.comments = this.comments.filter(c => c.id !== commentId);
            
            // Update UI
            this.renderComments();
            this.updateCommentCount();
            this.updateGenerateSummaryButton();
            
            this.showToast('Comment deleted successfully', 'success');
            
        } catch (error) {
            console.error('Error deleting comment:', error);
            this.showToast(`Error deleting comment: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    // Save feedback file with report and comments
    async saveFeedback() {
        if (!this.currentReport) {
            this.showToast('Please select a report first', 'warning');
            return;
        }

        if (this.comments.length === 0) {
            this.showToast('No comments to save. Add some comments first.', 'warning');
            return;
        }

        try {
            this.showLoading(true);
            this.showToast('Generating feedback file...', 'info');

            const response = await fetch(`${this.apiBaseUrl}/reports/${this.currentReport.id}/feedback`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to save feedback: ${response.status} ${response.statusText}`);
            }

            const result = await response.json();
            
            if (result.success) {
                this.showToast(`Feedback file saved: ${result.data.filename}`, 'success');
                this.showToast(`${result.data.comments_count} comments included in feedback`, 'info');
            } else {
                throw new Error(result.error || 'Failed to save feedback file');
            }

        } catch (error) {
            console.error('Error saving feedback:', error);
            this.showToast(`Error saving feedback: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    // Get section context for the current selection
    getSectionContext() {
        if (!this.currentSelection) return '';
        
        const range = this.currentSelection.range;
        let container = range.commonAncestorContainer;
        
        // Find the nearest section element
        while (container && container.nodeType !== Node.ELEMENT_NODE) {
            container = container.parentNode;
        }
        
        while (container && !container.classList.contains('report-section') && !container.classList.contains('report-text')) {
            container = container.parentNode;
        }
        
        if (container && container.classList.contains('report-section')) {
            const titleElement = container.querySelector('.section-title');
            return titleElement ? titleElement.textContent : 'Unknown Section';
        }
        
        return 'Main Content';
    }

    // Render comments in the sidebar
    renderComments() {
        const commentsList = document.getElementById('commentsList');
        if (!commentsList) return;

        if (this.comments.length === 0) {
            commentsList.innerHTML = `
                <div class="no-comments">
                    <div class="no-comments-icon">💬</div>
                    <p>No comments yet</p>
                    <small>Select text in the report to add your first comment</small>
                </div>
            `;
            return;
        }

        // Sort comments by position in document
        const sortedComments = [...this.comments].sort((a, b) => {
            const aPos = a.text_selection?.start_position || 0;
            const bPos = b.text_selection?.start_position || 0;
            return aPos - bPos;
        });

        // Debug: Log comment structure
        console.log('Comments data:', sortedComments);
        
        commentsList.innerHTML = sortedComments.map(comment => {
            // Debug: Log individual comment structure
            console.log('Comment:', comment);
            console.log('Text selection:', comment.text_selection);
            
            // Get selected text safely
            const selectedText = comment.text_selection?.selected_text || 
                                comment.selected_text || 
                                'No text selected';
            
            return `
                <div class="comment-item" data-comment-id="${comment.id}">
                    <div class="comment-header">
                        <div class="comment-author">👤 ${comment.author || 'Expert'}</div>
                        <div class="comment-timestamp">🕒 ${this.formatDate(comment.timestamp)}</div>
                        <div class="comment-actions">
                            <button class="comment-action edit-comment" title="Edit comment">
                                ✏️
                            </button>
                            <button class="comment-action delete-comment" title="Delete comment">
                                🗑️
                            </button>
                        </div>
                    </div>
                    <div class="comment-selected-text">
                        ${this.escapeHtml(selectedText)}
                    </div>
                    <div class="comment-text">${this.escapeHtml(comment.comment_text)}</div>
                    ${comment.section_context ? `<div class="comment-section">📍 Section: ${comment.section_context}</div>` : ''}
                </div>
            `;
        }).join('');

        // Bind comment action events
        this.bindCommentActions();
    }

    // Bind comment action event listeners
    bindCommentActions() {
        const commentsList = document.getElementById('commentsList');
        if (!commentsList) return;

        // Edit comment buttons
        commentsList.querySelectorAll('.edit-comment').forEach(button => {
            button.addEventListener('click', (e) => {
                const commentItem = e.target.closest('.comment-item');
                const commentId = commentItem.dataset.commentId;
                const comment = this.comments.find(c => c.id === commentId);
                if (comment) {
                    this.openCommentModal(comment);
                }
            });
        });

        // Delete comment buttons
        commentsList.querySelectorAll('.delete-comment').forEach(button => {
            button.addEventListener('click', (e) => {
                const commentItem = e.target.closest('.comment-item');
                const commentId = commentItem.dataset.commentId;
                this.deleteComment(commentId);
            });
        });

        // Comment item hover effects
        commentsList.querySelectorAll('.comment-item').forEach(item => {
            const commentId = item.dataset.commentId;
            
            item.addEventListener('mouseenter', () => {
                this.highlightCommentInText(commentId, true);
            });
            
            item.addEventListener('mouseleave', () => {
                this.highlightCommentInText(commentId, false);
            });
            
            item.addEventListener('click', () => {
                this.scrollToCommentInText(commentId);
            });
        });
    }

    // Highlight commented text in the report
    highlightCommentedText() {
        const reportContent = document.getElementById('reportContent');
        if (!reportContent) return;

        // Remove existing highlights
        this.clearTextHighlights();

        // Add highlights for each comment
        this.comments.forEach(comment => {
            this.addTextHighlight(comment);
        });
    }

    // Clear all text highlights
    clearTextHighlights() {
        const reportContent = document.getElementById('reportContent');
        if (!reportContent) return;

        const highlights = reportContent.querySelectorAll('.highlighted-text');
        highlights.forEach(highlight => {
            const parent = highlight.parentNode;
            parent.replaceChild(document.createTextNode(highlight.textContent), highlight);
            parent.normalize();
        });
    }

    // Add text highlight for a specific comment
    addTextHighlight(comment) {
        const reportContent = document.getElementById('reportContent');
        if (!reportContent) return;

        try {
            const range = this.createRangeFromOffsets(
                comment.text_selection.start_position,
                comment.text_selection.end_position
            );

            if (!range) return;

            const span = document.createElement('span');
            span.className = 'highlighted-text';
            span.dataset.commentId = comment.id;
            span.title = `Comment: ${comment.comment_text.substring(0, 100)}${comment.comment_text.length > 100 ? '...' : ''}`;

            // Add hover effects
            span.addEventListener('mouseenter', () => {
                this.showCommentTooltip(comment, span);
            });

            span.addEventListener('mouseleave', () => {
                this.hideCommentTooltip();
            });

            span.addEventListener('click', () => {
                this.scrollToCommentInSidebar(comment.id);
            });

            try {
                range.surroundContents(span);
            } catch (e) {
                // If surroundContents fails, try extractContents and appendChild
                const contents = range.extractContents();
                span.appendChild(contents);
                range.insertNode(span);
            }

        } catch (error) {
            console.warn('Failed to highlight text for comment:', comment.id, error);
        }
    }

    // Create range from text offsets
    createRangeFromOffsets(startOffset, endOffset) {
        const reportContent = document.getElementById('reportContent');
        if (!reportContent) return null;

        const walker = document.createTreeWalker(
            reportContent,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );

        let currentOffset = 0;
        let startNode = null;
        let startNodeOffset = 0;
        let endNode = null;
        let endNodeOffset = 0;
        let node;

        while (node = walker.nextNode()) {
            const nodeLength = node.textContent.length;
            
            if (startNode === null && currentOffset + nodeLength > startOffset) {
                startNode = node;
                startNodeOffset = startOffset - currentOffset;
            }
            
            if (currentOffset + nodeLength >= endOffset) {
                endNode = node;
                endNodeOffset = endOffset - currentOffset;
                break;
            }
            
            currentOffset += nodeLength;
        }

        if (!startNode || !endNode) return null;

        const range = document.createRange();
        range.setStart(startNode, startNodeOffset);
        range.setEnd(endNode, endNodeOffset);
        
        return range;
    }

    // Highlight specific comment in text (for hover effects)
    highlightCommentInText(commentId, highlight) {
        const highlightElement = document.querySelector(`[data-comment-id="${commentId}"]`);
        if (highlightElement) {
            if (highlight) {
                highlightElement.style.backgroundColor = '#ffeaa7';
                highlightElement.style.boxShadow = '0 0 0 2px #ffc107';
            } else {
                highlightElement.style.backgroundColor = '';
                highlightElement.style.boxShadow = '';
            }
        }
    }

    // Scroll to comment in text
    scrollToCommentInText(commentId) {
        const highlightElement = document.querySelector(`[data-comment-id="${commentId}"]`);
        if (highlightElement) {
            highlightElement.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center' 
            });
            
            // Temporarily highlight
            this.highlightCommentInText(commentId, true);
            setTimeout(() => {
                this.highlightCommentInText(commentId, false);
            }, 2000);
        }
    }

    // Scroll to comment in sidebar
    scrollToCommentInSidebar(commentId) {
        const commentItem = document.querySelector(`.comment-item[data-comment-id="${commentId}"]`);
        if (commentItem) {
            commentItem.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'nearest' 
            });
            
            // Temporarily highlight
            commentItem.style.backgroundColor = '#e3f2fd';
            setTimeout(() => {
                commentItem.style.backgroundColor = '';
            }, 2000);
        }
    }

    // Show comment tooltip
    showCommentTooltip(comment, element) {
        this.hideCommentTooltip(); // Hide any existing tooltip

        const tooltip = document.createElement('div');
        tooltip.className = 'comment-tooltip';
        tooltip.innerHTML = `
            <div class="tooltip-header">
                <strong>${comment.author}</strong>
                <span class="tooltip-time">${this.formatDate(comment.timestamp)}</span>
            </div>
            <div class="tooltip-content">${this.escapeHtml(comment.comment_text)}</div>
        `;

        document.body.appendChild(tooltip);

        // Position tooltip
        const rect = element.getBoundingClientRect();
        tooltip.style.position = 'absolute';
        tooltip.style.left = `${rect.left}px`;
        tooltip.style.top = `${rect.bottom + 5}px`;
        tooltip.style.zIndex = '1000';

        // Adjust position if tooltip goes off screen
        const tooltipRect = tooltip.getBoundingClientRect();
        if (tooltipRect.right > window.innerWidth) {
            tooltip.style.left = `${window.innerWidth - tooltipRect.width - 10}px`;
        }
        if (tooltipRect.bottom > window.innerHeight) {
            tooltip.style.top = `${rect.top - tooltipRect.height - 5}px`;
        }

        this.currentTooltip = tooltip;
    }

    // Hide comment tooltip
    hideCommentTooltip() {
        if (this.currentTooltip) {
            this.currentTooltip.remove();
            this.currentTooltip = null;
        }
    }

    // Update comment count display
    updateCommentCount() {
        const commentCount = document.getElementById('commentCount');
        const clearCommentsBtn = document.getElementById('clearCommentsBtn');
        const saveFeedbackBtn = document.getElementById('saveFeedback');
        
        if (commentCount) {
            commentCount.textContent = `${this.comments.length} comment${this.comments.length !== 1 ? 's' : ''}`;
        }
        
        if (clearCommentsBtn) {
            clearCommentsBtn.disabled = this.comments.length === 0;
        }

        if (saveFeedbackBtn) {
            saveFeedbackBtn.disabled = this.comments.length === 0;
        }
    }

    // Clear all comments
    async clearAllComments() {
        if (this.comments.length === 0) return;
        
        if (!confirm(`Are you sure you want to delete all ${this.comments.length} comments? This action cannot be undone.`)) {
            return;
        }

        try {
            this.showLoading(true);
            
            // Delete all comments via API
            const deletePromises = this.comments.map(comment => 
                fetch(`${this.apiBaseUrl}/comments/${comment.id}`, { method: 'DELETE' })
            );
            
            await Promise.all(deletePromises);
            
            // Clear local state
            this.comments = [];
            
            // Update UI
            this.renderComments();
            this.updateCommentCount();
            
            this.showToast('All comments deleted successfully', 'success');
            
        } catch (error) {
            console.error('Error clearing comments:', error);
            this.showToast(`Error clearing comments: ${error.message}`, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    // Clear current text selection
    clearSelection() {
        if (window.getSelection) {
            window.getSelection().removeAllRanges();
        }
        this.currentSelection = null;
    }

    // Auto-save functionality (called periodically)
    async autoSave() {
        if (!this.currentReport || this.comments.length === 0) return;
        
        try {
            // Save session state
            this.saveSession();
            console.log('Auto-save: Session state saved');
        } catch (error) {
            console.warn('Auto-save failed:', error);
        }
    }

    // Session Persistence Methods - Task 6.3

    // Save current session state to localStorage
    saveSession() {
        if (!this.currentReport) return;

        this.showSessionStatus('saving', 'Saving session...');

        const sessionData = {
            reportId: this.currentReport.id,
            reportFilename: this.currentReport.filename,
            comments: this.comments,
            timestamp: new Date().toISOString(),
            reportHash: this.calculateReportHash(this.currentReport)
        };

        try {
            localStorage.setItem(this.sessionKey, JSON.stringify(sessionData));
            this.lastSaveTime = Date.now();
            this.showSessionStatus('saved', 'Session saved');
            console.log('Session saved for report:', this.currentReport.id);
        } catch (error) {
            console.error('Failed to save session:', error);
            this.showSessionStatus('error', 'Save failed');
            this.showToast('Failed to save session state', 'warning');
        }
    }

    // Restore session from localStorage
    async restoreSession() {
        try {
            const sessionData = localStorage.getItem(this.sessionKey);
            if (!sessionData) return;

            const session = JSON.parse(sessionData);
            
            // Check if session is recent (within 7 days)
            const sessionAge = Date.now() - new Date(session.timestamp).getTime();
            const maxAge = 7 * 24 * 60 * 60 * 1000; // 7 days in milliseconds
            
            if (sessionAge > maxAge) {
                console.log('Session expired, clearing old session data');
                this.clearSession();
                return;
            }

            // Try to restore the report
            const reportSelector = document.getElementById('reportSelector');
            if (reportSelector && session.reportId) {
                // Wait for reports to load first
                await this.waitForReportsToLoad();
                
                // Check if the report still exists
                const reportOption = reportSelector.querySelector(`option[value="${session.reportId}"]`);
                if (reportOption) {
                    reportSelector.value = session.reportId;
                    await this.loadReport(session.reportId);
                    
                    // Check if report has been modified
                    await this.checkReportModification(session);
                    
                    this.showToast('Previous session restored', 'info');
                } else {
                    console.log('Report from session no longer exists');
                    this.clearSession();
                }
            }
        } catch (error) {
            console.error('Failed to restore session:', error);
            this.clearSession();
        }
    }

    // Wait for reports to be loaded
    async waitForReportsToLoad() {
        return new Promise((resolve) => {
            const checkReports = () => {
                const reportSelector = document.getElementById('reportSelector');
                if (reportSelector && reportSelector.children.length > 1) {
                    resolve();
                } else {
                    setTimeout(checkReports, 100);
                }
            };
            checkReports();
        });
    }

    // Check if report has been modified since last session
    async checkReportModification(session) {
        if (!this.currentReport || !session.reportHash) return;

        const currentHash = this.calculateReportHash(this.currentReport);
        
        if (currentHash !== session.reportHash) {
            this.showReportModificationWarning(session);
        }
    }

    // Calculate a simple hash of the report content for change detection
    calculateReportHash(report) {
        if (!report) return '';
        
        let content = '';
        if (report.sections && report.sections.length > 0) {
            content = report.sections.map(s => s.content || '').join('');
        } else if (report.content) {
            content = report.content;
        }
        
        // Simple hash function
        let hash = 0;
        for (let i = 0; i < content.length; i++) {
            const char = content.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }
        
        return hash.toString();
    }

    // Show warning when report has been modified
    showReportModificationWarning(session) {
        const warningDiv = document.createElement('div');
        warningDiv.className = 'report-modification-warning';
        warningDiv.innerHTML = `
            <div class="warning-content">
                <div class="warning-icon">⚠️</div>
                <div class="warning-text">
                    <strong>Report Modified</strong>
                    <p>The report "${session.reportFilename}" has been modified since your last session. 
                    Comment positions may not align correctly with the updated content.</p>
                </div>
                <div class="warning-actions">
                    <button class="btn-warning-continue" onclick="this.parentElement.parentElement.parentElement.remove()">
                        Continue Anyway
                    </button>
                    <button class="btn-warning-clear" onclick="window.hitlEditor.clearSessionAndReload()">
                        Start Fresh
                    </button>
                </div>
            </div>
        `;

        // Insert warning at the top of the report viewer
        const reportViewer = document.getElementById('reportViewer');
        if (reportViewer) {
            reportViewer.insertBefore(warningDiv, reportViewer.firstChild);
        }

        this.showToast('Report has been modified since last session', 'warning');
    }

    // Clear session and reload
    clearSessionAndReload() {
        this.clearSession();
        location.reload();
    }

    // Clear session data
    clearSession() {
        try {
            localStorage.removeItem(this.sessionKey);
            console.log('Session cleared');
        } catch (error) {
            console.error('Failed to clear session:', error);
        }
    }

    // Start monitoring session state
    startSessionMonitoring() {
        // Save session state when comments change
        const originalCreateComment = this.createComment.bind(this);
        const originalUpdateComment = this.updateComment.bind(this);
        const originalDeleteComment = this.deleteComment.bind(this);

        this.createComment = async function(commentText) {
            const result = await originalCreateComment(commentText);
            this.saveSession();
            return result;
        };

        this.updateComment = async function(commentId, commentText) {
            const result = await originalUpdateComment(commentId, commentText);
            this.saveSession();
            return result;
        };

        this.deleteComment = async function(commentId) {
            const result = await originalDeleteComment(commentId);
            this.saveSession();
            return result;
        };

        // Save session when page is about to unload
        window.addEventListener('beforeunload', () => {
            this.saveSession();
        });

        // Save session periodically
        this.sessionCheckInterval = setInterval(() => {
            if (this.currentReport && this.comments.length > 0) {
                this.saveSession();
            }
        }, 60000); // Every minute
    }

    // Stop session monitoring
    stopSessionMonitoring() {
        if (this.sessionCheckInterval) {
            clearInterval(this.sessionCheckInterval);
            this.sessionCheckInterval = null;
        }
    }

    // Track comment position changes for restoration
    trackCommentPositions() {
        if (!this.currentReport || !this.comments.length) return;

        const positionData = {
            reportId: this.currentReport.id,
            positions: this.comments.map(comment => ({
                commentId: comment.id,
                startPosition: comment.text_selection.start_position,
                endPosition: comment.text_selection.end_position,
                selectedText: comment.text_selection.selected_text,
                sectionContext: comment.section_context
            })),
            timestamp: new Date().toISOString()
        };

        try {
            const key = `${this.sessionKey}_positions_${this.currentReport.id}`;
            localStorage.setItem(key, JSON.stringify(positionData));
        } catch (error) {
            console.error('Failed to track comment positions:', error);
        }
    }

    // Restore comment positions
    restoreCommentPositions(reportId) {
        try {
            const key = `${this.sessionKey}_positions_${reportId}`;
            const positionData = localStorage.getItem(key);
            
            if (!positionData) return null;
            
            return JSON.parse(positionData);
        } catch (error) {
            console.error('Failed to restore comment positions:', error);
            return null;
        }
    }

    // Validate comment positions against current report content
    validateCommentPositions() {
        if (!this.currentReport || !this.comments.length) return;

        const reportContent = document.getElementById('reportContent');
        if (!reportContent) return;

        const fullText = reportContent.textContent || '';
        const invalidComments = [];

        this.comments.forEach(comment => {
            const { start_position, end_position, selected_text } = comment.text_selection;
            
            // Check if positions are within bounds
            if (start_position >= fullText.length || end_position > fullText.length) {
                invalidComments.push(comment);
                return;
            }

            // Check if selected text matches current content
            const currentText = fullText.substring(start_position, end_position);
            if (currentText !== selected_text) {
                invalidComments.push(comment);
            }
        });

        if (invalidComments.length > 0) {
            this.showPositionMismatchWarning(invalidComments);
        }
    }

    // Show warning for position mismatches
    showPositionMismatchWarning(invalidComments) {
        const warningDiv = document.createElement('div');
        warningDiv.className = 'position-mismatch-warning';
        warningDiv.innerHTML = `
            <div class="warning-content">
                <div class="warning-icon">🔍</div>
                <div class="warning-text">
                    <strong>Comment Position Mismatch</strong>
                    <p>${invalidComments.length} comment(s) may not be positioned correctly due to report changes.</p>
                </div>
                <div class="warning-actions">
                    <button class="btn-warning-review" onclick="window.hitlEditor.reviewMismatchedComments(${JSON.stringify(invalidComments.map(c => c.id))})">
                        Review Comments
                    </button>
                    <button class="btn-warning-dismiss" onclick="this.parentElement.parentElement.parentElement.remove()">
                        Dismiss
                    </button>
                </div>
            </div>
        `;

        const reportViewer = document.getElementById('reportViewer');
        if (reportViewer) {
            reportViewer.insertBefore(warningDiv, reportViewer.firstChild);
        }
    }

    // Review mismatched comments
    reviewMismatchedComments(commentIds) {
        commentIds.forEach(commentId => {
            const commentItem = document.querySelector(`.comment-item[data-comment-id="${commentId}"]`);
            if (commentItem) {
                commentItem.style.border = '2px solid #ff9800';
                commentItem.style.backgroundColor = '#fff3e0';
            }
        });

        this.showToast(`${commentIds.length} comments highlighted for review`, 'info');
        
        // Remove warning
        const warning = document.querySelector('.position-mismatch-warning');
        if (warning) warning.remove();
    }

    // Session Status Indicator Methods
    showSessionStatus(status, message) {
        const statusElement = document.getElementById('sessionStatus');
        const statusText = document.getElementById('sessionStatusText');
        
        if (!statusElement || !statusText) return;

        statusElement.className = `session-status ${status}`;
        statusText.textContent = message;
        statusElement.style.display = 'flex';

        // Auto-hide after 3 seconds for success states
        if (status === 'saved') {
            setTimeout(() => {
                statusElement.style.display = 'none';
            }, 3000);
        }
    }

    hideSessionStatus() {
        const statusElement = document.getElementById('sessionStatus');
        if (statusElement) {
            statusElement.style.display = 'none';
        }
    }

    // Escape HTML to prevent XSS
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Load existing comments for a report
    async loadReportComments(reportId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/reports/${reportId}/comments`);
            
            if (!response.ok) {
                if (response.status === 404) {
                    // No comments exist yet, that's okay
                    this.comments = [];
                    return;
                }
                throw new Error(`Failed to load comments: ${response.status} ${response.statusText}`);
            }

            const responseData = await response.json();
            console.log('API Response:', responseData);
            
            // Handle API response structure
            if (responseData.success && responseData.data) {
                this.comments = responseData.data;
            } else if (Array.isArray(responseData)) {
                this.comments = responseData;
            } else {
                this.comments = [];
            }
            
            console.log(`Loaded ${this.comments.length} comments for report ${reportId}:`, this.comments);
            
            // Render comments
            this.renderComments();
            this.updateCommentCount();
            
        } catch (error) {
            console.error('Error loading comments:', error);
            this.showToast(`Error loading comments: ${error.message}`, 'warning');
            this.comments = [];
            this.renderComments();
            this.updateCommentCount();
        }
    }

    // Clear the report viewer
    clearReportViewer() {
        const reportViewer = document.getElementById('reportViewer');
        const reportTitle = document.getElementById('reportTitle');
        const reportStats = document.getElementById('reportStats');

        if (reportTitle) reportTitle.textContent = 'No Report Selected';
        if (reportStats) reportStats.textContent = '';

        if (reportViewer) {
            reportViewer.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📄</div>
                    <h3>Select a report to begin</h3>
                    <p>Choose a report from the dropdown above to start reviewing and adding comments.</p>
                </div>
            `;
        }

        this.currentReport = null;
        this.currentSelection = null;
        this.comments = [];
    }

    // Utility: Show/hide loading overlay
    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.style.display = show ? 'flex' : 'none';
        }
    }

    // Utility: Show toast notification
    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span class="toast-message">${message}</span>
            <button class="toast-close">&times;</button>
        `;

        // Add close functionality
        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => {
            toast.remove();
        });

        container.appendChild(toast);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 5000);
    }

    // Utility: Format file size
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Utility: Format date
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }
    // ===== SUMMARY GENERATION FUNCTIONALITY =====
    
    /**
     * Generate summary for the current report
     */
    async generateSummary() {
        if (!this.currentReport) {
            this.showToast('Please select a report first', 'warning');
            return;
        }

        if (this.comments.length === 0) {
            this.showToast('No comments available to generate summary', 'warning');
            return;
        }

        try {
            // Show summary modal and start progress
            this.openSummaryModal();
            this.showSummaryProgress(true);
            
            // Trigger summary generation via API
            const response = await fetch(`${this.apiBaseUrl}/reports/${this.currentReport.id}/summary`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to generate summary: ${response.status} ${response.statusText}`);
            }

            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Failed to generate summary');
            }

            // Display the generated summary
            this.displaySummaryPreview(result.data);
            this.showSummaryProgress(false);
            
            this.showToast('Summary generated successfully', 'success');

        } catch (error) {
            console.error('Error generating summary:', error);
            this.showToast(`Error generating summary: ${error.message}`, 'error');
            this.showSummaryProgress(false);
        }
    }

    /**
     * Open the summary modal
     */
    openSummaryModal() {
        const modal = document.getElementById('summaryModal');
        if (modal) {
            modal.style.display = 'flex';
            
            // Reset modal state
            this.resetSummaryModal();
            
            // Bind summary modal events
            this.bindSummaryModalEvents();
        }
    }

    /**
     * Reset summary modal to initial state
     */
    resetSummaryModal() {
        const progressSection = document.getElementById('summaryProgress');
        const previewSection = document.getElementById('summaryPreview');
        const downloadBtn = document.getElementById('downloadSummary');
        
        if (progressSection) progressSection.style.display = 'none';
        if (previewSection) previewSection.style.display = 'none';
        if (downloadBtn) downloadBtn.style.display = 'none';
        
        // Clear previous content
        const summaryContent = document.getElementById('summaryContent');
        if (summaryContent) summaryContent.innerHTML = '';
        
        // Reset progress bar
        const progressFill = document.querySelector('.progress-fill');
        if (progressFill) progressFill.style.width = '0%';
    }

    /**
     * Bind summary modal event listeners
     */
    bindSummaryModalEvents() {
        // Close modal button
        const closeBtn = document.getElementById('closeSummaryModal');
        if (closeBtn) {
            closeBtn.onclick = () => this.closeSummaryModal();
        }

        // Cancel button
        const cancelBtn = document.getElementById('cancelSummary');
        if (cancelBtn) {
            cancelBtn.onclick = () => this.closeSummaryModal();
        }

        // Download button
        const downloadBtn = document.getElementById('downloadSummary');
        if (downloadBtn) {
            downloadBtn.onclick = () => this.downloadSummary();
        }
    }

    /**
     * Close summary modal
     */
    closeSummaryModal() {
        const modal = document.getElementById('summaryModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    /**
     * Show/hide summary generation progress
     */
    showSummaryProgress(show) {
        const progressSection = document.getElementById('summaryProgress');
        const progressText = document.querySelector('.progress-text');
        const progressFill = document.querySelector('.progress-fill');
        
        if (!progressSection) return;

        if (show) {
            progressSection.style.display = 'block';
            
            // Animate progress bar
            let progress = 0;
            const progressInterval = setInterval(() => {
                progress += Math.random() * 15;
                if (progress > 90) progress = 90; // Don't complete until actual completion
                
                if (progressFill) {
                    progressFill.style.width = `${progress}%`;
                }
                
                // Update progress text
                if (progressText) {
                    const messages = [
                        'Analyzing comments...',
                        'Processing with LLM...',
                        'Generating insights...',
                        'Organizing sections...',
                        'Finalizing summary...'
                    ];
                    const messageIndex = Math.floor(progress / 20);
                    progressText.textContent = messages[messageIndex] || 'Generating summary...';
                }
                
                if (progress >= 90) {
                    clearInterval(progressInterval);
                }
            }, 200);
            
            // Store interval for cleanup
            this.summaryProgressInterval = progressInterval;
            
        } else {
            // Complete progress and hide
            if (this.summaryProgressInterval) {
                clearInterval(this.summaryProgressInterval);
            }
            
            if (progressFill) {
                progressFill.style.width = '100%';
            }
            
            if (progressText) {
                progressText.textContent = 'Summary generated!';
            }
            
            setTimeout(() => {
                progressSection.style.display = 'none';
            }, 500);
        }
    }

    /**
     * Display summary preview in the modal
     */
    displaySummaryPreview(summaryData) {
        const previewSection = document.getElementById('summaryPreview');
        const summaryContent = document.getElementById('summaryContent');
        const downloadBtn = document.getElementById('downloadSummary');
        
        if (!previewSection || !summaryContent) return;

        // Store summary data for download
        this.currentSummary = summaryData;

        // Build summary HTML
        let summaryHtml = this.buildSummaryHtml(summaryData);
        
        summaryContent.innerHTML = summaryHtml;
        previewSection.style.display = 'block';
        
        if (downloadBtn) {
            downloadBtn.style.display = 'inline-block';
        }
    }

    /**
     * Build HTML representation of the summary
     */
    buildSummaryHtml(summaryData) {
        let html = '';
        
        // Summary header
        html += `
            <div class="summary-header">
                <h6>Summary for: ${this.currentReport.filename}</h6>
                <div class="summary-meta">
                    <span>Generated: ${this.formatDate(summaryData.generated_at)}</span>
                    <span>Total Comments: ${summaryData.total_comments}</span>
                </div>
            </div>
        `;

        // Summary statistics
        if (summaryData.summary_statistics) {
            html += `
                <div class="summary-statistics">
                    <h6>Statistics</h6>
                    <div class="stats-grid">
                        ${summaryData.summary_statistics.most_commented_section ? 
                            `<div class="stat-item">
                                <strong>Most Commented Section:</strong> 
                                ${summaryData.summary_statistics.most_commented_section}
                            </div>` : ''}
                        ${summaryData.summary_statistics.average_comment_length ? 
                            `<div class="stat-item">
                                <strong>Average Comment Length:</strong> 
                                ${summaryData.summary_statistics.average_comment_length} characters
                            </div>` : ''}
                        ${summaryData.summary_statistics.total_review_time ? 
                            `<div class="stat-item">
                                <strong>Total Review Time:</strong> 
                                ${summaryData.summary_statistics.total_review_time}
                            </div>` : ''}
                    </div>
                </div>
            `;
        }

        // Comments by section
        if (summaryData.comments_by_section && summaryData.comments_by_section.length > 0) {
            html += '<div class="summary-sections"><h6>Comments by Section</h6>';
            
            summaryData.comments_by_section.forEach(section => {
                html += `
                    <div class="summary-section">
                        <h7>${section.section_title}</h7>
                        ${section.section_content ? 
                            `<div class="section-context">${this.truncateText(section.section_content, 200)}</div>` : ''}
                        
                        <div class="section-comments">
                            ${section.comments.map(comment => `
                                <div class="summary-comment">
                                    <div class="comment-quote">"${comment.selected_text}"</div>
                                    <div class="comment-content">${this.escapeHtml(comment.comment)}</div>
                                    <div class="comment-meta">
                                        <span>${comment.author}</span>
                                        <span>${this.formatDate(comment.timestamp)}</span>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                        
                        ${section.llm_insights ? `
                            <div class="llm-insights">
                                <strong>AI Insights:</strong>
                                <div class="insights-content">${this.escapeHtml(section.llm_insights)}</div>
                            </div>
                        ` : ''}
                    </div>
                `;
            });
            
            html += '</div>';
        }

        // LLM overall insights
        if (summaryData.llm_summary) {
            html += `
                <div class="llm-summary">
                    <h6>AI-Generated Summary</h6>
                    <div class="llm-content">${this.escapeHtml(summaryData.llm_summary)}</div>
                </div>
            `;
        }

        return html;
    }

    /**
     * Download the generated summary
     */
    async downloadSummary() {
        if (!this.currentSummary || !this.currentReport) {
            this.showToast('No summary available to download', 'error');
            return;
        }

        try {
            // Get formatted text export from API
            const response = await fetch(`${this.apiBaseUrl}/reports/${this.currentReport.id}/summary/export`);
            
            if (!response.ok) {
                throw new Error(`Failed to export summary: ${response.status} ${response.statusText}`);
            }

            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Failed to export summary');
            }

            // Create and download file
            const blob = new Blob([result.data.exported_text], { type: 'text/plain' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            
            a.href = url;
            a.download = `${this.currentReport.filename}_summary_${this.formatDateForFilename(new Date())}.txt`;
            document.body.appendChild(a);
            a.click();
            
            // Cleanup
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            this.showToast('Summary downloaded successfully', 'success');

        } catch (error) {
            console.error('Error downloading summary:', error);
            this.showToast(`Error downloading summary: ${error.message}`, 'error');
        }
    }

    /**
     * Update generate summary button state
     */
    updateGenerateSummaryButton() {
        const generateBtn = document.getElementById('generateSummaryBtn');
        if (generateBtn) {
            const hasReport = this.currentReport !== null;
            const hasComments = this.comments.length > 0;
            
            generateBtn.disabled = !hasReport || !hasComments;
            
            if (!hasReport) {
                generateBtn.title = 'Select a report first';
            } else if (!hasComments) {
                generateBtn.title = 'Add comments to generate summary';
            } else {
                generateBtn.title = 'Generate summary of all comments';
            }
        }
    }

    /**
     * Truncate text to specified length
     */
    truncateText(text, maxLength) {
        if (!text || text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    /**
     * Format date for filename (safe characters only)
     */
    formatDateForFilename(date) {
        return date.toISOString().replace(/[:.]/g, '-').split('T')[0];
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.hitlEditor = new HITLReportEditor();
});