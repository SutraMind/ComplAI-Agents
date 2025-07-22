"""
Comment management API endpoints for the HITL Report Editor.
"""

from flask import request, jsonify, current_app
from . import api_bp
from ..services.comment_service import CommentService


# Initialize comment service
comment_service = CommentService()


@api_bp.route('/comments', methods=['POST'])
def create_comment():
    """
    Create a new comment on a report.
    
    Expected JSON payload:
    {
        "report_id": "uuid",
        "start_position": 100,
        "end_position": 150,
        "selected_text": "Selected text content",
        "comment_text": "This is my comment",
        "author": "John Doe",
        "section_context": "Optional section context"
    }
    
    Returns:
        JSON response with created comment data
    """
    try:
        # Validate request data
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Content-Type must be application/json'
            }), 400
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['report_id', 'start_position', 'end_position', 
                          'selected_text', 'comment_text', 'author']
        
        if not data or not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(required_fields)}'
            }), 400
        
        # Extract and validate data
        report_id = data['report_id']
        start_position = data['start_position']
        end_position = data['end_position']
        selected_text = data['selected_text']
        comment_text = data['comment_text']
        author = data['author']
        section_context = data.get('section_context', '')
        
        # Validate data types
        if not isinstance(start_position, int) or not isinstance(end_position, int):
            return jsonify({
                'success': False,
                'error': 'start_position and end_position must be integers'
            }), 400
        
        # Create comment using service
        comment = comment_service.create_comment(
            report_id=report_id,
            start_position=start_position,
            end_position=end_position,
            selected_text=selected_text,
            comment_text=comment_text,
            author=author,
            section_context=section_context
        )
        
        if not comment:
            return jsonify({
                'success': False,
                'error': 'Failed to create comment'
            }), 500
        
        # Return created comment data
        return jsonify({
            'success': True,
            'data': comment.to_dict()
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating comment: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create comment'
        }), 500


@api_bp.route('/comments/<comment_id>', methods=['GET'])
def get_comment(comment_id):
    """
    Get a specific comment by ID.
    
    Args:
        comment_id: Unique identifier of the comment
        
    Returns:
        JSON response with comment data
    """
    try:
        # Validate comment ID
        if not comment_id or not comment_id.strip():
            return jsonify({
                'success': False,
                'error': 'Invalid comment ID'
            }), 400
        
        # Get comment using service
        comment = comment_service.get_comment(comment_id)
        
        if not comment:
            return jsonify({
                'success': False,
                'error': 'Comment not found'
            }), 404
        
        # Return comment data
        return jsonify({
            'success': True,
            'data': comment.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving comment {comment_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve comment'
        }), 500


@api_bp.route('/comments/<comment_id>', methods=['PUT'])
def update_comment(comment_id):
    """
    Update an existing comment's text.
    
    Args:
        comment_id: Unique identifier of the comment
        
    Expected JSON payload:
    {
        "comment_text": "Updated comment text"
    }
    
    Returns:
        JSON response with updated comment data
    """
    try:
        # Validate comment ID
        if not comment_id or not comment_id.strip():
            return jsonify({
                'success': False,
                'error': 'Invalid comment ID'
            }), 400
        
        # Validate request data
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Content-Type must be application/json'
            }), 400
        
        data = request.get_json()
        
        # Validate required fields
        if not data or 'comment_text' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: comment_text'
            }), 400
        
        comment_text = data['comment_text']
        
        # Update comment using service
        updated_comment = comment_service.update_comment(comment_id, comment_text)
        
        if not updated_comment:
            return jsonify({
                'success': False,
                'error': 'Failed to update comment or comment not found'
            }), 404
        
        # Return updated comment data
        return jsonify({
            'success': True,
            'data': updated_comment.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error updating comment {comment_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update comment'
        }), 500


@api_bp.route('/comments/<comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    """
    Delete a specific comment.
    
    Args:
        comment_id: Unique identifier of the comment
        
    Returns:
        JSON response confirming deletion
    """
    try:
        # Validate comment ID
        if not comment_id or not comment_id.strip():
            return jsonify({
                'success': False,
                'error': 'Invalid comment ID'
            }), 400
        
        # Delete comment using service
        success = comment_service.delete_comment(comment_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Comment not found or failed to delete'
            }), 404
        
        # Return success response
        return jsonify({
            'success': True,
            'message': 'Comment deleted successfully'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error deleting comment {comment_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete comment'
        }), 500


@api_bp.route('/reports/<report_id>/comments', methods=['GET'])
def get_comments_for_report(report_id):
    """
    Get all comments for a specific report.
    
    Args:
        report_id: Unique identifier of the report
        
    Returns:
        JSON response with list of comments
    """
    try:
        # Validate report ID
        if not report_id or not report_id.strip():
            return jsonify({
                'success': False,
                'error': 'Invalid report ID'
            }), 400
        
        # Get comments using service
        comments = comment_service.get_comments_for_report(report_id)
        
        # Convert comments to dictionaries
        comments_data = [comment.to_dict() for comment in comments]
        
        return jsonify({
            'success': True,
            'data': comments_data,
            'count': len(comments_data)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting comments for report {report_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve comments'
        }), 500


@api_bp.route('/comments/author/<author>', methods=['GET'])
def get_comments_by_author(author):
    """
    Get all comments by a specific author.
    
    Args:
        author: Author name to filter by
        
    Returns:
        JSON response with list of comments
    """
    try:
        # Validate author
        if not author or not author.strip():
            return jsonify({
                'success': False,
                'error': 'Invalid author name'
            }), 400
        
        # Get comments using service
        comments = comment_service.get_comments_by_author(author)
        
        # Convert comments to dictionaries
        comments_data = [comment.to_dict() for comment in comments]
        
        return jsonify({
            'success': True,
            'data': comments_data,
            'count': len(comments_data)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting comments by author {author}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve comments'
        }), 500


@api_bp.route('/reports/<report_id>/comments/range', methods=['GET'])
def get_comments_in_range(report_id):
    """
    Get comments that overlap with a specific text range.
    
    Args:
        report_id: Unique identifier of the report
        
    Query parameters:
        start_position: Start character position
        end_position: End character position
        
    Returns:
        JSON response with list of overlapping comments
    """
    try:
        # Validate report ID
        if not report_id or not report_id.strip():
            return jsonify({
                'success': False,
                'error': 'Invalid report ID'
            }), 400
        
        # Get query parameters
        start_position = request.args.get('start_position', type=int)
        end_position = request.args.get('end_position', type=int)
        
        if start_position is None or end_position is None:
            return jsonify({
                'success': False,
                'error': 'Missing required query parameters: start_position and end_position'
            }), 400
        
        # Get comments using service
        comments = comment_service.get_comments_in_range(report_id, start_position, end_position)
        
        # Convert comments to dictionaries
        comments_data = [comment.to_dict() for comment in comments]
        
        return jsonify({
            'success': True,
            'data': comments_data,
            'count': len(comments_data)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting comments in range for report {report_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve comments'
        }), 500


@api_bp.route('/comments/recent', methods=['GET'])
def get_recent_comments():
    """
    Get comments created within the specified time period.
    
    Query parameters:
        hours: Number of hours to look back (default: 24)
        
    Returns:
        JSON response with list of recent comments
    """
    try:
        # Get query parameter
        hours = request.args.get('hours', default=24, type=int)
        
        if hours <= 0:
            return jsonify({
                'success': False,
                'error': 'Hours parameter must be positive'
            }), 400
        
        # Get comments using service
        comments = comment_service.get_recent_comments(hours)
        
        # Convert comments to dictionaries
        comments_data = [comment.to_dict() for comment in comments]
        
        return jsonify({
            'success': True,
            'data': comments_data,
            'count': len(comments_data),
            'hours': hours
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting recent comments: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve recent comments'
        }), 500


@api_bp.route('/reports/<report_id>/comments/statistics', methods=['GET'])
def get_comment_statistics(report_id):
    """
    Get statistics about comments for a report.
    
    Args:
        report_id: Unique identifier of the report
        
    Returns:
        JSON response with comment statistics
    """
    try:
        # Validate report ID
        if not report_id or not report_id.strip():
            return jsonify({
                'success': False,
                'error': 'Invalid report ID'
            }), 400
        
        # Get statistics using service
        statistics = comment_service.get_comment_statistics(report_id)
        
        return jsonify({
            'success': True,
            'data': statistics
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting comment statistics for report {report_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve comment statistics'
        }), 500