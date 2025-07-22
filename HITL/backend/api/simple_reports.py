"""
Simple report API that works with text files directly.
"""
import os
import uuid
from datetime import datetime
from pathlib import Path
from flask import request, jsonify, current_app
from . import api_bp

@api_bp.route('/reports', methods=['GET'])
def list_reports():
    """Get a list of all available reports."""
    try:
        reports_dir = Path(current_app.config.get('REPORTS_DIR', 'data/reports'))
        reports = []
        
        # Scan for text files
        for file_path in reports_dir.glob('*.txt'):
            try:
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
            except Exception as e:
                current_app.logger.warning(f"Error reading {file_path}: {e}")
                continue
        
        return jsonify({
            'success': True,
            'data': reports,
            'count': len(reports)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error listing reports: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to list reports'
        }), 500

@api_bp.route('/reports/<report_id>', methods=['GET'])
def get_report(report_id):
    """Get a specific report by ID."""
    try:
        reports_dir = Path(current_app.config.get('REPORTS_DIR', 'data/reports'))
        report_file = reports_dir / f"{report_id}.txt"
        
        if not report_file.exists():
            return jsonify({
                'success': False,
                'error': 'Report not found'
            }), 404
        
        content = report_file.read_text(encoding='utf-8')
        stat = report_file.stat()
        
        # Parse content into sections
        sections = parse_content_sections(content)
        
        report = {
            'id': report_id,
            'filename': report_file.name,
            'content': content,
            'sections': sections,
            'metadata': {
                'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'file_size': len(content.encode('utf-8')),
                'line_count': len(content.split('\n'))
            }
        }
        
        return jsonify({
            'success': True,
            'data': report
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting report {report_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get report'
        }), 500

@api_bp.route('/reports/<report_id>/comments', methods=['GET'])
def get_report_comments(report_id):
    """Get comments for a report."""
    try:
        comments_dir = Path(current_app.config.get('COMMENTS_DIR', 'data/comments'))
        comments_file = comments_dir / f"{report_id}.json"
        
        if not comments_file.exists():
            return jsonify({
                'success': True,
                'data': [],
                'count': 0
            })
        
        import json
        with open(comments_file, 'r', encoding='utf-8') as f:
            comments = json.load(f)
        
        return jsonify({
            'success': True,
            'data': comments,
            'count': len(comments)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting comments for {report_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get comments'
        }), 500

@api_bp.route('/reports/<report_id>/comments', methods=['POST'])
def create_comment(report_id):
    """Create a new comment."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Create comment object
        comment = {
            'id': str(uuid.uuid4()),
            'report_id': report_id,
            'text_selection': {
                'start_position': data.get('text_selection', {}).get('start_position', 0),
                'end_position': data.get('text_selection', {}).get('end_position', 0),
                'selected_text': data.get('text_selection', {}).get('selected_text', '')
            },
            'comment_text': data.get('comment_text', ''),
            'author': data.get('author', 'Anonymous'),
            'timestamp': datetime.now().isoformat(),
            'section_context': data.get('section_context', '')
        }
        
        # Load existing comments
        comments_dir = Path(current_app.config.get('COMMENTS_DIR', 'data/comments'))
        comments_dir.mkdir(parents=True, exist_ok=True)
        comments_file = comments_dir / f"{report_id}.json"
        
        comments = []
        if comments_file.exists():
            import json
            with open(comments_file, 'r', encoding='utf-8') as f:
                comments = json.load(f)
        
        # Add new comment
        comments.append(comment)
        
        # Save comments
        import json
        with open(comments_file, 'w', encoding='utf-8') as f:
            json.dump(comments, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'success': True,
            'data': comment
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating comment: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to create comment'
        }), 500

def parse_content_sections(content):
    """Parse content into sections."""
    sections = []
    lines = content.split('\n')
    current_section = None
    section_lines = []
    section_start = 0
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Check if this is a header line
        if (stripped and 
            (stripped.isupper() or 
             stripped.endswith(':') or 
             len(stripped.split()) <= 4)):
            
            # Save previous section
            if current_section and section_lines:
                sections.append({
                    'id': str(uuid.uuid4()),
                    'title': current_section,
                    'content': '\n'.join(section_lines).strip(),
                    'start_line': section_start + 1,
                    'end_line': i
                })
            
            # Start new section
            current_section = stripped
            section_lines = []
            section_start = i
        else:
            section_lines.append(line)
    
    # Add final section
    if current_section and section_lines:
        sections.append({
            'id': str(uuid.uuid4()),
            'title': current_section,
            'content': '\n'.join(section_lines).strip(),
            'start_line': section_start + 1,
            'end_line': len(lines)
        })
    
    # If no sections found, create one main section
    if not sections:
        sections.append({
            'id': str(uuid.uuid4()),
            'title': 'Main Content',
            'content': content,
            'start_line': 1,
            'end_line': len(lines)
        })
    
    return sections