"""
Summary management API endpoints for the HITL Report Editor.
"""

from flask import request, jsonify, current_app
from . import api_bp
from ..services.summary_service import SummaryService
from ..services.report_service import ReportService
from ..services.comment_service import CommentService


# Services will be instantiated in route handlers


@api_bp.route('/reports/<report_id>/summary', methods=['POST'])
def generate_summary(report_id):
    """
    Generate a comprehensive summary for a report and its comments.
    
    Args:
        report_id: Unique identifier of the report
        
    Returns:
        JSON response with generated summary data
    """
    try:
        # Validate report ID
        if not report_id or not report_id.strip():
            return jsonify({
                'success': False,
                'error': 'Invalid report ID'
            }), 400
        
        # Get report
        report_service = ReportService()
        report = report_service.get_report(report_id)
        if not report:
            return jsonify({
                'success': False,
                'error': 'Report not found'
            }), 404
        
        # Get comments for the report
        comment_service = CommentService()
        comments = comment_service.get_comments_for_report(report_id)
        
        # Generate summary using service
        summary_service = SummaryService()
        summary = summary_service.generate_summary(report, comments)
        
        if not summary:
            return jsonify({
                'success': False,
                'error': 'Failed to generate summary'
            }), 500
        
        # Return generated summary data
        return jsonify({
            'success': True,
            'data': summary.to_dict()
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error generating summary for report {report_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate summary'
        }), 500


@api_bp.route('/reports/<report_id>/summary', methods=['GET'])
def get_summary(report_id):
    """
    Get the summary for a specific report.
    
    Args:
        report_id: Unique identifier of the report
        
    Returns:
        JSON response with summary data
    """
    try:
        # Validate report ID
        if not report_id or not report_id.strip():
            return jsonify({
                'success': False,
                'error': 'Invalid report ID'
            }), 400
        
        # Get summary using service
        summary_service = SummaryService()
        summary = summary_service.get_summary(report_id)
        
        if not summary:
            return jsonify({
                'success': False,
                'error': 'Summary not found'
            }), 404
        
        # Return summary data
        return jsonify({
            'success': True,
            'data': summary.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving summary for report {report_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve summary'
        }), 500


@api_bp.route('/reports/<report_id>/summary', methods=['PUT'])
def update_summary(report_id):
    """
    Update/regenerate the summary for a report.
    
    Args:
        report_id: Unique identifier of the report
        
    Returns:
        JSON response with updated summary data
    """
    try:
        # Validate report ID
        if not report_id or not report_id.strip():
            return jsonify({
                'success': False,
                'error': 'Invalid report ID'
            }), 400
        
        # Get report
        report_service = ReportService()
        report = report_service.get_report(report_id)
        if not report:
            return jsonify({
                'success': False,
                'error': 'Report not found'
            }), 404
        
        # Get updated comments for the report
        comment_service = CommentService()
        comments = comment_service.get_comments_for_report(report_id)
        
        # Update summary using service
        summary_service = SummaryService()
        updated_summary = summary_service.update_summary(report, comments)
        
        if not updated_summary:
            return jsonify({
                'success': False,
                'error': 'Failed to update summary'
            }), 500
        
        # Return updated summary data
        return jsonify({
            'success': True,
            'data': updated_summary.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error updating summary for report {report_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update summary'
        }), 500


@api_bp.route('/reports/<report_id>/summary', methods=['DELETE'])
def delete_summary(report_id):
    """
    Delete the summary for a specific report.
    
    Args:
        report_id: Unique identifier of the report
        
    Returns:
        JSON response confirming deletion
    """
    try:
        # Validate report ID
        if not report_id or not report_id.strip():
            return jsonify({
                'success': False,
                'error': 'Invalid report ID'
            }), 400
        
        # Delete summary using service
        summary_service = SummaryService()
        success = summary_service.delete_summary(report_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Summary not found or failed to delete'
            }), 404
        
        # Return success response
        return jsonify({
            'success': True,
            'message': 'Summary deleted successfully'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error deleting summary for report {report_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete summary'
        }), 500


@api_bp.route('/reports/<report_id>/summary/export', methods=['GET'])
def export_summary(report_id):
    """
    Export summary to formatted text.
    
    Args:
        report_id: Unique identifier of the report
        
    Returns:
        JSON response with formatted text export
    """
    try:
        # Validate report ID
        if not report_id or not report_id.strip():
            return jsonify({
                'success': False,
                'error': 'Invalid report ID'
            }), 400
        
        # Export summary using service
        summary_service = SummaryService()
        exported_text = summary_service.export_summary_to_text(report_id)
        
        if not exported_text:
            return jsonify({
                'success': False,
                'error': 'Summary not found or failed to export'
            }), 404
        
        # Return exported text
        return jsonify({
            'success': True,
            'data': {
                'exported_text': exported_text,
                'format': 'text'
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error exporting summary for report {report_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to export summary'
        }), 500


@api_bp.route('/reports/<report_id>/summary/insights', methods=['GET'])
def get_summary_insights(report_id):
    """
    Get LLM-powered insights about the summary.
    
    Args:
        report_id: Unique identifier of the report
        
    Returns:
        JSON response with insights and analysis
    """
    try:
        # Validate report ID
        if not report_id or not report_id.strip():
            return jsonify({
                'success': False,
                'error': 'Invalid report ID'
            }), 400
        
        # Get insights using service
        summary_service = SummaryService()
        insights = summary_service.get_summary_insights(report_id)
        
        if insights.get('status') == 'error':
            return jsonify({
                'success': False,
                'error': insights.get('message', 'Failed to get insights')
            }), 404 if 'not found' in insights.get('message', '').lower() else 500
        
        # Return insights data
        return jsonify({
            'success': True,
            'data': insights
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting summary insights for report {report_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get summary insights'
        }), 500


@api_bp.route('/reports/<report_id>/summary/preview', methods=['GET'])
def get_summary_preview(report_id):
    """
    Generate a quick preview of what the summary would contain.
    
    Args:
        report_id: Unique identifier of the report
        
    Returns:
        JSON response with preview information
    """
    try:
        # Validate report ID
        if not report_id or not report_id.strip():
            return jsonify({
                'success': False,
                'error': 'Invalid report ID'
            }), 400
        
        # Get report
        report_service = ReportService()
        report = report_service.get_report(report_id)
        if not report:
            return jsonify({
                'success': False,
                'error': 'Report not found'
            }), 404
        
        # Get comments for the report
        comment_service = CommentService()
        comments = comment_service.get_comments_for_report(report_id)
        
        # Generate preview using service
        summary_service = SummaryService()
        preview = summary_service.generate_summary_preview(report, comments)
        
        if preview.get('status') == 'error':
            return jsonify({
                'success': False,
                'error': preview.get('message', 'Failed to generate preview')
            }), 500
        
        # Return preview data
        return jsonify({
            'success': True,
            'data': preview.get('preview', {})
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error generating summary preview for report {report_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate summary preview'
        }), 500