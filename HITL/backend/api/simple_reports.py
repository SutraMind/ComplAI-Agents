"""
Simple report API that works with text files directly.
"""
import os
import uuid
import traceback
from datetime import datetime
from pathlib import Path
from flask import request, jsonify, current_app
from . import api_bp

# Custom exception classes for better error handling
class ReportNotFoundError(Exception):
    """Raised when a report is not found."""
    pass

class CommentNotFoundError(Exception):
    """Raised when a comment is not found."""
    pass

class ValidationError(Exception):
    """Raised when input validation fails."""
    pass

class FileOperationError(Exception):
    """Raised when file operations fail."""
    pass

@api_bp.route('/reports', methods=['GET'])
def list_reports():
    """Get a list of all available reports."""
    operation_id = str(uuid.uuid4())[:8]
    current_app.logger.info(f"[{operation_id}] Starting list_reports operation")
    
    try:
        reports_dir = Path(current_app.config.get('REPORTS_DIR', 'data/reports'))
        current_app.logger.debug(f"[{operation_id}] Scanning reports directory: {reports_dir}")
        
        if not reports_dir.exists():
            current_app.logger.warning(f"[{operation_id}] Reports directory does not exist: {reports_dir}")
            return jsonify({
                'success': True,
                'data': [],
                'count': 0,
                'message': 'Reports directory not found'
            })
        
        reports = []
        processed_files = 0
        error_files = 0
        
        # Scan for text files
        for file_path in reports_dir.glob('*.txt'):
            try:
                current_app.logger.debug(f"[{operation_id}] Processing file: {file_path.name}")
                
                if not file_path.is_file():
                    current_app.logger.warning(f"[{operation_id}] Skipping non-file: {file_path}")
                    continue
                
                stat = file_path.stat()
                content = file_path.read_text(encoding='utf-8')
                
                report = {
                    'id': file_path.stem,
                    'filename': file_path.name,
                    'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'file_size': len(content.encode('utf-8')),
                    'line_count': len(content.split('\n'))
                }
                reports.append(report)
                processed_files += 1
                
            except PermissionError as e:
                current_app.logger.error(f"[{operation_id}] Permission denied reading {file_path}: {e}")
                error_files += 1
            except UnicodeDecodeError as e:
                current_app.logger.error(f"[{operation_id}] Unicode decode error reading {file_path}: {e}")
                error_files += 1
            except Exception as e:
                current_app.logger.error(f"[{operation_id}] Unexpected error reading {file_path}: {e}")
                current_app.logger.debug(f"[{operation_id}] Traceback: {traceback.format_exc()}")
                error_files += 1
        
        current_app.logger.info(f"[{operation_id}] Completed list_reports: {processed_files} processed, {error_files} errors")
        
        response_data = {
            'success': True,
            'data': reports,
            'count': len(reports),
            'metadata': {
                'processed_files': processed_files,
                'error_files': error_files,
                'operation_id': operation_id
            }
        }
        
        if error_files > 0:
            response_data['warnings'] = f"{error_files} files could not be processed"
        
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"[{operation_id}] Critical error in list_reports: {e}")
        current_app.logger.debug(f"[{operation_id}] Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to list reports',
            'details': str(e) if current_app.debug else 'Internal server error',
            'operation_id': operation_id
        }), 500

@api_bp.route('/reports/<report_id>', methods=['GET'])
def get_report(report_id):
    """Get a specific report by ID."""
    operation_id = str(uuid.uuid4())[:8]
    current_app.logger.info(f"[{operation_id}] Starting get_report operation for report_id: {report_id}")
    
    try:
        # Input validation
        if not report_id or not report_id.strip():
            current_app.logger.warning(f"[{operation_id}] Invalid report_id provided: '{report_id}'")
            raise ValidationError("Report ID cannot be empty")
        
        # Sanitize report_id to prevent path traversal
        if '..' in report_id or '/' in report_id or '\\' in report_id:
            current_app.logger.warning(f"[{operation_id}] Potentially malicious report_id: {report_id}")
            raise ValidationError("Invalid report ID format")
        
        reports_dir = Path(current_app.config.get('REPORTS_DIR', 'data/reports'))
        report_file = reports_dir / f"{report_id}.txt"
        
        current_app.logger.debug(f"[{operation_id}] Looking for report file: {report_file}")
        
        if not report_file.exists():
            current_app.logger.warning(f"[{operation_id}] Report file not found: {report_file}")
            raise ReportNotFoundError(f"Report '{report_id}' not found")
        
        if not report_file.is_file():
            current_app.logger.error(f"[{operation_id}] Path exists but is not a file: {report_file}")
            raise FileOperationError("Report path is not a valid file")
        
        try:
            content = report_file.read_text(encoding='utf-8')
            current_app.logger.debug(f"[{operation_id}] Successfully read report content ({len(content)} characters)")
        except UnicodeDecodeError as e:
            current_app.logger.error(f"[{operation_id}] Unicode decode error reading report: {e}")
            raise FileOperationError("Report file contains invalid characters")
        except PermissionError as e:
            current_app.logger.error(f"[{operation_id}] Permission denied reading report: {e}")
            raise FileOperationError("Permission denied accessing report file")
        
        stat = report_file.stat()
        
        # Parse content into sections
        try:
            sections = parse_content_sections(content)
            current_app.logger.debug(f"[{operation_id}] Parsed {len(sections)} sections from content")
        except Exception as e:
            current_app.logger.error(f"[{operation_id}] Error parsing content sections: {e}")
            sections = []  # Continue with empty sections rather than failing
        
        report = {
            'id': report_id,
            'filename': report_file.name,
            'content': content,
            'sections': sections,
            'metadata': {
                'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'file_size': len(content.encode('utf-8')),
                'line_count': len(content.split('\n')),
                'section_count': len(sections)
            }
        }
        
        current_app.logger.info(f"[{operation_id}] Successfully retrieved report: {report_id}")
        
        return jsonify({
            'success': True,
            'data': report,
            'operation_id': operation_id
        })
        
    except (ValidationError, ReportNotFoundError) as e:
        current_app.logger.warning(f"[{operation_id}] Client error in get_report: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'operation_id': operation_id
        }), 404 if isinstance(e, ReportNotFoundError) else 400
        
    except FileOperationError as e:
        current_app.logger.error(f"[{operation_id}] File operation error in get_report: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'operation_id': operation_id
        }), 500
        
    except Exception as e:
        current_app.logger.error(f"[{operation_id}] Unexpected error in get_report: {e}")
        current_app.logger.debug(f"[{operation_id}] Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to get report',
            'details': str(e) if current_app.debug else 'Internal server error',
            'operation_id': operation_id
        }), 500

@api_bp.route('/reports/<report_id>/comments', methods=['GET'])
def get_report_comments(report_id):
    """Get comments for a report."""
    operation_id = str(uuid.uuid4())[:8]
    current_app.logger.info(f"[{operation_id}] Starting get_report_comments for report_id: {report_id}")
    
    try:
        # Input validation
        if not report_id or not report_id.strip():
            current_app.logger.warning(f"[{operation_id}] Invalid report_id provided: '{report_id}'")
            raise ValidationError("Report ID cannot be empty")
        
        # Sanitize report_id
        if '..' in report_id or '/' in report_id or '\\' in report_id:
            current_app.logger.warning(f"[{operation_id}] Potentially malicious report_id: {report_id}")
            raise ValidationError("Invalid report ID format")
        
        comments_dir = Path(current_app.config.get('COMMENTS_DIR', 'data/comments'))
        comments_file = comments_dir / f"{report_id}.json"
        
        current_app.logger.debug(f"[{operation_id}] Looking for comments file: {comments_file}")
        
        if not comments_file.exists():
            current_app.logger.info(f"[{operation_id}] No comments file found for report {report_id}")
            return jsonify({
                'success': True,
                'data': [],
                'count': 0,
                'message': 'No comments found for this report',
                'operation_id': operation_id
            })
        
        try:
            import json
            with open(comments_file, 'r', encoding='utf-8') as f:
                comments = json.load(f)
            
            current_app.logger.debug(f"[{operation_id}] Successfully loaded {len(comments)} comments")
            
            # Validate comments structure
            valid_comments = []
            invalid_count = 0
            
            for i, comment in enumerate(comments):
                if not isinstance(comment, dict):
                    current_app.logger.warning(f"[{operation_id}] Invalid comment structure at index {i}")
                    invalid_count += 1
                    continue
                
                # Check required fields
                required_fields = ['id', 'comment_text', 'author', 'timestamp']
                if not all(field in comment for field in required_fields):
                    current_app.logger.warning(f"[{operation_id}] Comment missing required fields at index {i}")
                    invalid_count += 1
                    continue
                
                valid_comments.append(comment)
            
            if invalid_count > 0:
                current_app.logger.warning(f"[{operation_id}] Found {invalid_count} invalid comments")
            
            current_app.logger.info(f"[{operation_id}] Successfully retrieved {len(valid_comments)} valid comments")
            
            response_data = {
                'success': True,
                'data': valid_comments,
                'count': len(valid_comments),
                'operation_id': operation_id
            }
            
            if invalid_count > 0:
                response_data['warnings'] = f"{invalid_count} invalid comments were filtered out"
            
            return jsonify(response_data)
            
        except json.JSONDecodeError as e:
            current_app.logger.error(f"[{operation_id}] JSON decode error reading comments: {e}")
            raise FileOperationError("Comments file contains invalid JSON")
        except PermissionError as e:
            current_app.logger.error(f"[{operation_id}] Permission denied reading comments: {e}")
            raise FileOperationError("Permission denied accessing comments file")
        
    except ValidationError as e:
        current_app.logger.warning(f"[{operation_id}] Validation error in get_report_comments: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'operation_id': operation_id
        }), 400
        
    except FileOperationError as e:
        current_app.logger.error(f"[{operation_id}] File operation error in get_report_comments: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'operation_id': operation_id
        }), 500
        
    except Exception as e:
        current_app.logger.error(f"[{operation_id}] Unexpected error in get_report_comments: {e}")
        current_app.logger.debug(f"[{operation_id}] Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to get comments',
            'details': str(e) if current_app.debug else 'Internal server error',
            'operation_id': operation_id
        }), 500

@api_bp.route('/reports/<report_id>/comments', methods=['POST'])
def create_comment(report_id):
    """Create a new comment."""
    operation_id = str(uuid.uuid4())[:8]
    current_app.logger.info(f"[{operation_id}] Starting create_comment for report_id: {report_id}")
    
    try:
        # Input validation
        if not report_id or not report_id.strip():
            current_app.logger.warning(f"[{operation_id}] Invalid report_id provided: '{report_id}'")
            raise ValidationError("Report ID cannot be empty")
        
        # Sanitize report_id
        if '..' in report_id or '/' in report_id or '\\' in report_id:
            current_app.logger.warning(f"[{operation_id}] Potentially malicious report_id: {report_id}")
            raise ValidationError("Invalid report ID format")
        
        # Validate request content type
        if not request.is_json:
            current_app.logger.warning(f"[{operation_id}] Invalid content type: {request.content_type}")
            raise ValidationError("Content-Type must be application/json")
        
        data = request.get_json()
        if not data:
            current_app.logger.warning(f"[{operation_id}] No JSON data provided")
            raise ValidationError("No data provided")
        
        current_app.logger.debug(f"[{operation_id}] Received comment data: {data}")
        
        # Validate required fields
        required_fields = ['comment_text']
        missing_fields = [field for field in required_fields if not data.get(field, '').strip()]
        if missing_fields:
            current_app.logger.warning(f"[{operation_id}] Missing required fields: {missing_fields}")
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Validate text selection if provided
        text_selection = data.get('text_selection', {})
        if text_selection:
            start_pos = text_selection.get('start_position', 0)
            end_pos = text_selection.get('end_position', 0)
            if not isinstance(start_pos, int) or not isinstance(end_pos, int):
                raise ValidationError("Text selection positions must be integers")
            if start_pos < 0 or end_pos < 0 or start_pos > end_pos:
                raise ValidationError("Invalid text selection positions")
        
        # Create comment object
        comment = {
            'id': str(uuid.uuid4()),
            'report_id': report_id,
            'text_selection': {
                'start_position': text_selection.get('start_position', 0),
                'end_position': text_selection.get('end_position', 0),
                'selected_text': text_selection.get('selected_text', '')
            },
            'comment_text': data.get('comment_text', '').strip(),
            'author': data.get('author', 'Anonymous').strip() or 'Anonymous',
            'timestamp': datetime.now().isoformat(),
            'section_context': data.get('section_context', '').strip()
        }
        
        current_app.logger.debug(f"[{operation_id}] Created comment object with ID: {comment['id']}")
        
        # Ensure comments directory exists
        comments_dir = Path(current_app.config.get('COMMENTS_DIR', 'data/comments'))
        try:
            comments_dir.mkdir(parents=True, exist_ok=True)
            current_app.logger.debug(f"[{operation_id}] Comments directory ensured: {comments_dir}")
        except PermissionError as e:
            current_app.logger.error(f"[{operation_id}] Permission denied creating comments directory: {e}")
            raise FileOperationError("Permission denied creating comments directory")
        
        comments_file = comments_dir / f"{report_id}.json"
        
        # Load existing comments
        comments = []
        if comments_file.exists():
            try:
                import json
                with open(comments_file, 'r', encoding='utf-8') as f:
                    comments = json.load(f)
                current_app.logger.debug(f"[{operation_id}] Loaded {len(comments)} existing comments")
            except json.JSONDecodeError as e:
                current_app.logger.error(f"[{operation_id}] JSON decode error reading existing comments: {e}")
                # Continue with empty comments list rather than failing
                comments = []
                current_app.logger.warning(f"[{operation_id}] Starting with empty comments list due to corrupted file")
            except PermissionError as e:
                current_app.logger.error(f"[{operation_id}] Permission denied reading comments file: {e}")
                raise FileOperationError("Permission denied reading comments file")
        
        # Add new comment
        comments.append(comment)
        current_app.logger.debug(f"[{operation_id}] Added new comment, total count: {len(comments)}")
        
        # Save comments with backup
        try:
            import json
            
            # Create backup if file exists
            if comments_file.exists():
                backup_file = comments_file.with_suffix('.json.backup')
                comments_file.rename(backup_file)
                current_app.logger.debug(f"[{operation_id}] Created backup: {backup_file}")
            
            # Write new comments file
            with open(comments_file, 'w', encoding='utf-8') as f:
                json.dump(comments, f, indent=2, ensure_ascii=False)
            
            current_app.logger.info(f"[{operation_id}] Successfully saved comment {comment['id']}")
            
            # Remove backup on success
            backup_file = comments_file.with_suffix('.json.backup')
            if backup_file.exists():
                backup_file.unlink()
                current_app.logger.debug(f"[{operation_id}] Removed backup file")
            
        except PermissionError as e:
            current_app.logger.error(f"[{operation_id}] Permission denied writing comments file: {e}")
            raise FileOperationError("Permission denied writing comments file")
        except Exception as e:
            current_app.logger.error(f"[{operation_id}] Error writing comments file: {e}")
            # Try to restore backup
            backup_file = comments_file.with_suffix('.json.backup')
            if backup_file.exists():
                backup_file.rename(comments_file)
                current_app.logger.info(f"[{operation_id}] Restored backup file")
            raise FileOperationError("Failed to save comment")
        
        return jsonify({
            'success': True,
            'data': comment,
            'operation_id': operation_id
        }), 201
        
    except ValidationError as e:
        current_app.logger.warning(f"[{operation_id}] Validation error in create_comment: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'operation_id': operation_id
        }), 400
        
    except FileOperationError as e:
        current_app.logger.error(f"[{operation_id}] File operation error in create_comment: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'operation_id': operation_id
        }), 500
        
    except Exception as e:
        current_app.logger.error(f"[{operation_id}] Unexpected error in create_comment: {e}")
        current_app.logger.debug(f"[{operation_id}] Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to create comment',
            'details': str(e) if current_app.debug else 'Internal server error',
            'operation_id': operation_id
        }), 500

def parse_content_sections(content):
    """Parse content into sections with enhanced error handling."""
    try:
        if not content or not isinstance(content, str):
            current_app.logger.warning("Invalid content provided to parse_content_sections")
            return [{
                'id': str(uuid.uuid4()),
                'title': 'Main Content',
                'content': str(content) if content else '',
                'start_line': 1,
                'end_line': 1
            }]
        
        sections = []
        lines = content.split('\n')
        current_section = None
        section_lines = []
        section_start = 0
        
        current_app.logger.debug(f"Parsing content with {len(lines)} lines")
        
        for i, line in enumerate(lines):
            try:
                stripped = line.strip()
                
                # Check if this is a header line
                is_header = False
                if stripped:
                    # More robust header detection
                    if (stripped.isupper() and len(stripped) > 2 and len(stripped) < 100):
                        is_header = True
                    elif stripped.endswith(':') and len(stripped.split()) <= 6:
                        is_header = True
                    elif stripped.startswith('#'):
                        is_header = True
                    elif (len(stripped.split()) <= 4 and 
                          not any(char.isdigit() for char in stripped) and
                          len(stripped) > 3):
                        is_header = True
                
                if is_header:
                    # Save previous section
                    if current_section and section_lines:
                        section_content = '\n'.join(section_lines).strip()
                        sections.append({
                            'id': str(uuid.uuid4()),
                            'title': current_section[:100],  # Limit title length
                            'content': section_content,
                            'start_line': section_start + 1,
                            'end_line': i,
                            'line_count': len(section_lines)
                        })
                    
                    # Start new section
                    current_section = stripped.lstrip('#').strip()
                    section_lines = []
                    section_start = i
                else:
                    section_lines.append(line)
                    
            except Exception as e:
                current_app.logger.warning(f"Error processing line {i}: {e}")
                # Continue processing other lines
                section_lines.append(line)
                continue
        
        # Add final section
        if current_section and section_lines:
            section_content = '\n'.join(section_lines).strip()
            sections.append({
                'id': str(uuid.uuid4()),
                'title': current_section[:100],
                'content': section_content,
                'start_line': section_start + 1,
                'end_line': len(lines),
                'line_count': len(section_lines)
            })
        
        # If no sections found, create one main section
        if not sections:
            sections.append({
                'id': str(uuid.uuid4()),
                'title': 'Main Content',
                'content': content,
                'start_line': 1,
                'end_line': len(lines),
                'line_count': len(lines)
            })
        
        current_app.logger.debug(f"Successfully parsed {len(sections)} sections")
        return sections
        
    except Exception as e:
        current_app.logger.error(f"Critical error in parse_content_sections: {e}")
        current_app.logger.debug(f"Traceback: {traceback.format_exc()}")
        
        # Return a safe fallback section
        return [{
            'id': str(uuid.uuid4()),
            'title': 'Main Content',
            'content': str(content) if content else '',
            'start_line': 1,
            'end_line': len(content.split('\n')) if content else 1,
            'line_count': len(content.split('\n')) if content else 1,
            'error': 'Failed to parse sections'
        }]

@api_bp.route('/comments/<comment_id>', methods=['PUT'])
def update_comment(comment_id):
    """Update a specific comment."""
    operation_id = str(uuid.uuid4())[:8]
    current_app.logger.info(f"[{operation_id}] Starting update_comment for comment_id: {comment_id}")
    
    try:
        # Input validation
        if not comment_id or not comment_id.strip():
            current_app.logger.warning(f"[{operation_id}] Invalid comment_id provided: '{comment_id}'")
            raise ValidationError("Comment ID cannot be empty")
        
        # Validate request content type
        if not request.is_json:
            current_app.logger.warning(f"[{operation_id}] Invalid content type: {request.content_type}")
            raise ValidationError("Content-Type must be application/json")
        
        data = request.get_json()
        if not data:
            current_app.logger.warning(f"[{operation_id}] No JSON data provided")
            raise ValidationError("No data provided")
        
        if 'comment_text' not in data:
            current_app.logger.warning(f"[{operation_id}] Missing comment_text field")
            raise ValidationError("Missing comment_text field")
        
        new_comment_text = data['comment_text']
        if not new_comment_text or not new_comment_text.strip():
            current_app.logger.warning(f"[{operation_id}] Empty comment text provided")
            raise ValidationError("Comment text cannot be empty")
        
        new_comment_text = new_comment_text.strip()
        current_app.logger.debug(f"[{operation_id}] Updating comment with new text: {new_comment_text[:50]}...")
        
        # Find and update the comment
        comments_dir = Path(current_app.config.get('COMMENTS_DIR', 'data/comments'))
        
        if not comments_dir.exists():
            current_app.logger.warning(f"[{operation_id}] Comments directory does not exist: {comments_dir}")
            raise CommentNotFoundError("Comment not found")
        
        comment_updated = False
        updated_comment = None
        processed_files = 0
        error_files = 0
        
        # Search through all comment files to find and update the comment
        for comments_file in comments_dir.glob('*.json'):
            processed_files += 1
            try:
                current_app.logger.debug(f"[{operation_id}] Searching in file: {comments_file.name}")
                
                import json
                with open(comments_file, 'r', encoding='utf-8') as f:
                    comments = json.load(f)
                
                # Find and update the comment
                for comment in comments:
                    if comment.get('id') == comment_id:
                        current_app.logger.debug(f"[{operation_id}] Found comment in file: {comments_file.name}")
                        
                        # Store original text for logging
                        original_text = comment.get('comment_text', '')
                        
                        # Update comment
                        comment['comment_text'] = new_comment_text
                        comment['modified_at'] = datetime.now().isoformat()
                        updated_comment = comment.copy()
                        comment_updated = True
                        
                        current_app.logger.info(f"[{operation_id}] Updated comment text from '{original_text[:30]}...' to '{new_comment_text[:30]}...'")
                        break
                
                if comment_updated:
                    # Create backup before saving
                    backup_file = comments_file.with_suffix('.json.backup')
                    comments_file.rename(backup_file)
                    current_app.logger.debug(f"[{operation_id}] Created backup: {backup_file}")
                    
                    try:
                        # Save the updated comments
                        with open(comments_file, 'w', encoding='utf-8') as f:
                            json.dump(comments, f, indent=2, ensure_ascii=False)
                        
                        current_app.logger.info(f"[{operation_id}] Successfully updated comment {comment_id}")
                        
                        # Remove backup on success
                        if backup_file.exists():
                            backup_file.unlink()
                            current_app.logger.debug(f"[{operation_id}] Removed backup file")
                        
                    except Exception as e:
                        current_app.logger.error(f"[{operation_id}] Error saving updated comments: {e}")
                        # Restore backup
                        if backup_file.exists():
                            backup_file.rename(comments_file)
                            current_app.logger.info(f"[{operation_id}] Restored backup file")
                        raise FileOperationError("Failed to save updated comment")
                    
                    break
                    
            except json.JSONDecodeError as e:
                current_app.logger.error(f"[{operation_id}] JSON decode error in {comments_file}: {e}")
                error_files += 1
                continue
            except PermissionError as e:
                current_app.logger.error(f"[{operation_id}] Permission denied accessing {comments_file}: {e}")
                error_files += 1
                continue
            except Exception as e:
                current_app.logger.error(f"[{operation_id}] Error processing {comments_file}: {e}")
                current_app.logger.debug(f"[{operation_id}] Traceback: {traceback.format_exc()}")
                error_files += 1
                continue
        
        current_app.logger.debug(f"[{operation_id}] Processed {processed_files} files, {error_files} errors")
        
        if comment_updated:
            return jsonify({
                'success': True,
                'data': updated_comment,
                'operation_id': operation_id
            }), 200
        else:
            current_app.logger.warning(f"[{operation_id}] Comment {comment_id} not found in any file")
            raise CommentNotFoundError("Comment not found")
        
    except ValidationError as e:
        current_app.logger.warning(f"[{operation_id}] Validation error in update_comment: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'operation_id': operation_id
        }), 400
        
    except CommentNotFoundError as e:
        current_app.logger.warning(f"[{operation_id}] Comment not found in update_comment: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'operation_id': operation_id
        }), 404
        
    except FileOperationError as e:
        current_app.logger.error(f"[{operation_id}] File operation error in update_comment: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'operation_id': operation_id
        }), 500
        
    except Exception as e:
        current_app.logger.error(f"[{operation_id}] Unexpected error in update_comment: {e}")
        current_app.logger.debug(f"[{operation_id}] Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to update comment',
            'details': str(e) if current_app.debug else 'Internal server error',
            'operation_id': operation_id
        }), 500


@api_bp.route('/reports/<report_id>/feedback', methods=['POST'])
def save_feedback_file(report_id):
    """
    Save a comprehensive feedback file containing the report and all comments.
    
    Args:
        report_id: Unique identifier of the report
        
    Returns:
        JSON response with feedback file information
    """
    operation_id = str(uuid.uuid4())[:8]
    current_app.logger.info(f"[{operation_id}] Starting save_feedback_file for report_id: {report_id}")
    
    try:
        # Input validation
        if not report_id or not report_id.strip():
            current_app.logger.warning(f"[{operation_id}] Invalid report_id provided: '{report_id}'")
            raise ValidationError("Report ID cannot be empty")
        
        # Sanitize report_id
        if '..' in report_id or '/' in report_id or '\\' in report_id:
            current_app.logger.warning(f"[{operation_id}] Potentially malicious report_id: {report_id}")
            raise ValidationError("Invalid report ID format")
        
        # Get report
        reports_dir = Path(current_app.config.get('REPORTS_DIR', 'data/reports'))
        report_file = reports_dir / f"{report_id}.txt"
        
        if not report_file.exists():
            current_app.logger.warning(f"[{operation_id}] Report file not found: {report_file}")
            raise ReportNotFoundError(f"Report '{report_id}' not found")
        
        try:
            report_content = report_file.read_text(encoding='utf-8')
            current_app.logger.debug(f"[{operation_id}] Successfully read report content ({len(report_content)} characters)")
        except Exception as e:
            current_app.logger.error(f"[{operation_id}] Error reading report: {e}")
            raise FileOperationError("Failed to read report file")
        
        # Get comments
        comments_dir = Path(current_app.config.get('COMMENTS_DIR', 'data/comments'))
        comments_file = comments_dir / f"{report_id}.json"
        
        comments = []
        if comments_file.exists():
            try:
                import json
                with open(comments_file, 'r', encoding='utf-8') as f:
                    comments = json.load(f)
                current_app.logger.debug(f"[{operation_id}] Successfully loaded {len(comments)} comments")
            except Exception as e:
                current_app.logger.error(f"[{operation_id}] Error reading comments: {e}")
                # Continue with empty comments rather than failing
                comments = []
        
        # Generate feedback content
        feedback_content = f"FEEDBACK REPORT\n"
        feedback_content += f"================\n\n"
        feedback_content += f"Report: {report_file.name}\n"
        feedback_content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        feedback_content += f"Total Comments: {len(comments)}\n\n"
        
        feedback_content += f"ORIGINAL REPORT CONTENT\n"
        feedback_content += f"=======================\n\n"
        feedback_content += report_content + '\n\n'
        
        feedback_content += f"EXPERT COMMENTS\n"
        feedback_content += f"===============\n\n"
        
        # Sort comments by position
        sorted_comments = sorted(comments, key=lambda c: c.get('text_selection', {}).get('start_position', 0))
        
        for i, comment in enumerate(sorted_comments, 1):
            feedback_content += f"Comment {i}:\n"
            feedback_content += f"Author: {comment.get('author', 'Unknown')}\n"
            feedback_content += f"Time: {comment.get('timestamp', 'Unknown')}\n"
            
            text_selection = comment.get('text_selection', {})
            selected_text = text_selection.get('selected_text', 'N/A')
            feedback_content += f"Selected Text: \"{selected_text}\"\n"
            feedback_content += f"Comment: {comment.get('comment_text', '')}\n"
            
            section_context = comment.get('section_context', '')
            if section_context:
                feedback_content += f"Section: {section_context}\n"
            feedback_content += f"\n{'=' * 50}\n\n"
        
        # Save feedback file
        feedback_dir = Path(current_app.config.get('FEEDBACK_DIR', 'data/feedback'))
        feedback_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"feedback_{report_id}_{timestamp}.txt"
        feedback_file = feedback_dir / filename
        
        # Write feedback file
        try:
            with open(feedback_file, 'w', encoding='utf-8') as f:
                f.write(feedback_content)
            current_app.logger.info(f"[{operation_id}] Successfully saved feedback file: {feedback_file}")
        except Exception as e:
            current_app.logger.error(f"[{operation_id}] Error writing feedback file: {e}")
            raise FileOperationError("Failed to save feedback file")
        
        return jsonify({
            'success': True,
            'data': {
                'filename': filename,
                'filepath': str(feedback_file),
                'size': len(feedback_content),
                'comments_count': len(comments)
            },
            'operation_id': operation_id
        }), 200
        
    except (ValidationError, ReportNotFoundError) as e:
        current_app.logger.warning(f"[{operation_id}] Client error in save_feedback_file: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'operation_id': operation_id
        }), 404 if isinstance(e, ReportNotFoundError) else 400
        
    except FileOperationError as e:
        current_app.logger.error(f"[{operation_id}] File operation error in save_feedback_file: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'operation_id': operation_id
        }), 500
        
    except Exception as e:
        current_app.logger.error(f"[{operation_id}] Unexpected error in save_feedback_file: {e}")
        current_app.logger.debug(f"[{operation_id}] Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to save feedback file',
            'details': str(e) if current_app.debug else 'Internal server error',
            'operation_id': operation_id
        }), 500

@api_bp.route('/comments/<comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    """Delete a specific comment."""
    operation_id = str(uuid.uuid4())[:8]
    current_app.logger.info(f"[{operation_id}] Starting delete_comment for comment_id: {comment_id}")
    
    try:
        # Validate comment ID
        if not comment_id or not comment_id.strip():
            current_app.logger.warning(f"[{operation_id}] Invalid comment_id provided: '{comment_id}'")
            raise ValidationError("Comment ID cannot be empty")
        
        current_app.logger.debug(f"[{operation_id}] Attempting to delete comment: {comment_id}")
        
        # Find which report this comment belongs to
        comments_dir = Path(current_app.config.get('COMMENTS_DIR', 'data/comments'))
        
        if not comments_dir.exists():
            current_app.logger.warning(f"[{operation_id}] Comments directory does not exist: {comments_dir}")
            raise CommentNotFoundError("Comment not found")
        
        comment_deleted = False
        deleted_from_file = None
        processed_files = 0
        error_files = 0
        
        # Search through all comment files to find and delete the comment
        for comments_file in comments_dir.glob('*.json'):
            processed_files += 1
            try:
                current_app.logger.debug(f"[{operation_id}] Searching in file: {comments_file.name}")
                
                import json
                with open(comments_file, 'r', encoding='utf-8') as f:
                    comments = json.load(f)
                
                # Filter out the comment to delete
                original_count = len(comments)
                comments_before_filter = comments.copy()
                comments = [c for c in comments if c.get('id') != comment_id]
                
                if len(comments) < original_count:
                    current_app.logger.info(f"[{operation_id}] Found comment to delete in file: {comments_file.name}")
                    
                    # Find the deleted comment for logging
                    deleted_comment = next((c for c in comments_before_filter if c.get('id') == comment_id), None)
                    if deleted_comment:
                        current_app.logger.debug(f"[{operation_id}] Deleting comment by {deleted_comment.get('author', 'Unknown')}: {deleted_comment.get('comment_text', '')[:50]}...")
                    
                    # Create backup before saving
                    backup_file = comments_file.with_suffix('.json.backup')
                    comments_file.rename(backup_file)
                    current_app.logger.debug(f"[{operation_id}] Created backup: {backup_file}")
                    
                    try:
                        # Comment was found and removed
                        with open(comments_file, 'w', encoding='utf-8') as f:
                            json.dump(comments, f, indent=2, ensure_ascii=False)
                        
                        comment_deleted = True
                        deleted_from_file = comments_file.name
                        
                        current_app.logger.info(f"[{operation_id}] Successfully deleted comment {comment_id} from {comments_file.name}")
                        
                        # Remove backup on success
                        if backup_file.exists():
                            backup_file.unlink()
                            current_app.logger.debug(f"[{operation_id}] Removed backup file")
                        
                        break
                        
                    except Exception as e:
                        current_app.logger.error(f"[{operation_id}] Error saving after deletion: {e}")
                        # Restore backup
                        if backup_file.exists():
                            backup_file.rename(comments_file)
                            current_app.logger.info(f"[{operation_id}] Restored backup file")
                        raise FileOperationError("Failed to save after comment deletion")
                    
            except json.JSONDecodeError as e:
                current_app.logger.error(f"[{operation_id}] JSON decode error in {comments_file}: {e}")
                error_files += 1
                continue
            except PermissionError as e:
                current_app.logger.error(f"[{operation_id}] Permission denied accessing {comments_file}: {e}")
                error_files += 1
                continue
            except Exception as e:
                current_app.logger.error(f"[{operation_id}] Error processing {comments_file}: {e}")
                current_app.logger.debug(f"[{operation_id}] Traceback: {traceback.format_exc()}")
                error_files += 1
                continue
        
        current_app.logger.debug(f"[{operation_id}] Processed {processed_files} files, {error_files} errors")
        
        if comment_deleted:
            response_data = {
                'success': True,
                'message': 'Comment deleted successfully',
                'operation_id': operation_id,
                'metadata': {
                    'deleted_from_file': deleted_from_file,
                    'processed_files': processed_files
                }
            }
            
            if error_files > 0:
                response_data['warnings'] = f"{error_files} files could not be processed"
            
            return jsonify(response_data), 200
        else:
            current_app.logger.warning(f"[{operation_id}] Comment {comment_id} not found in any file")
            raise CommentNotFoundError("Comment not found")
        
    except ValidationError as e:
        current_app.logger.warning(f"[{operation_id}] Validation error in delete_comment: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'operation_id': operation_id
        }), 400
        
    except CommentNotFoundError as e:
        current_app.logger.warning(f"[{operation_id}] Comment not found in delete_comment: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'operation_id': operation_id
        }), 404
        
    except FileOperationError as e:
        current_app.logger.error(f"[{operation_id}] File operation error in delete_comment: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'operation_id': operation_id
        }), 500
        
    except Exception as e:
        current_app.logger.error(f"[{operation_id}] Unexpected error in delete_comment: {e}")
        current_app.logger.debug(f"[{operation_id}] Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete comment',
            'details': str(e) if current_app.debug else 'Internal server error',
            'operation_id': operation_id
        }), 500