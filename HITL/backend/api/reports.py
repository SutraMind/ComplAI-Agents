"""
Report management API endpoints for the HITL Report Editor.
"""

from flask import request, jsonify, current_app
from werkzeug.utils import secure_filename
from . import api_bp
from ..services.report_service import ReportService


# Report service will be instantiated in route handlers


@api_bp.route('/reports', methods=['GET'])
def list_reports():
    """
    Get a list of all reports.
    
    Returns:
        JSON response with list of reports and metadata
    """
    try:
        report_service = ReportService()
        reports = report_service.list_reports()
        return jsonify({
            'success': True,
            'data': reports,
            'count': len(reports)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error listing reports: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve reports'
        }), 500


@api_bp.route('/reports', methods=['POST'])
def create_report():
    """
    Create a new report from uploaded content.
    
    Expected JSON payload:
    {
        "filename": "report.txt",
        "content": "Report content here..."
    }
    
    Returns:
        JSON response with created report data
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
        if not data or 'filename' not in data or 'content' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: filename and content'
            }), 400
        
        filename = data['filename']
        content = data['content']
        
        # Validate filename
        if not filename or not filename.strip():
            return jsonify({
                'success': False,
                'error': 'Filename cannot be empty'
            }), 400
        
        # Secure the filename
        filename = secure_filename(filename)
        
        # Validate content
        if not content or not content.strip():
            return jsonify({
                'success': False,
                'error': 'Content cannot be empty'
            }), 400
        
        # Create report using service
        report_service = ReportService()
        report = report_service.create_report(filename, content)
        
        if not report:
            return jsonify({
                'success': False,
                'error': 'Failed to create report'
            }), 500
        
        # Return created report data
        return jsonify({
            'success': True,
            'data': report.to_dict()
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating report: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to create report'
        }), 500


@api_bp.route('/reports/<report_id>', methods=['GET'])
def get_report(report_id):
    """
    Get a specific report by ID.
    
    Args:
        report_id: Unique identifier of the report
        
    Returns:
        JSON response with report data
    """
    try:
        # Validate report ID
        if not report_id or not report_id.strip():
            return jsonify({
                'success': False,
                'error': 'Invalid report ID'
            }), 400
        
        # Get report using service
        report_service = ReportService()
        report = report_service.get_report(report_id)
        
        if not report:
            return jsonify({
                'success': False,
                'error': 'Report not found'
            }), 404
        
        # Return report data
        return jsonify({
            'success': True,
            'data': report.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving report {report_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve report'
        }), 500


@api_bp.route('/reports/<report_id>', methods=['PUT'])
def update_report(report_id):
    """
    Update an existing report's content.
    
    Args:
        report_id: Unique identifier of the report
        
    Expected JSON payload:
    {
        "content": "Updated report content here..."
    }
    
    Returns:
        JSON response with updated report data
    """
    try:
        # Validate report ID
        if not report_id or not report_id.strip():
            return jsonify({
                'success': False,
                'error': 'Invalid report ID'
            }), 400
        
        # Validate request data
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Content-Type must be application/json'
            }), 400
        
        data = request.get_json()
        
        # Validate required fields
        if not data or 'content' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: content'
            }), 400
        
        content = data['content']
        
        # Validate content
        if not content or not content.strip():
            return jsonify({
                'success': False,
                'error': 'Content cannot be empty'
            }), 400
        
        # Update report using service
        report_service = ReportService()
        updated_report = report_service.update_report(report_id, content)
        
        if not updated_report:
            return jsonify({
                'success': False,
                'error': 'Failed to update report or report not found'
            }), 404
        
        # Return updated report data
        return jsonify({
            'success': True,
            'data': updated_report.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error updating report {report_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update report'
        }), 500


@api_bp.route('/reports/<report_id>', methods=['DELETE'])
def delete_report(report_id):
    """
    Delete a specific report.
    
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
        
        # Delete report using service
        report_service = ReportService()
        success = report_service.delete_report(report_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Report not found or failed to delete'
            }), 404
        
        # Return success response
        return jsonify({
            'success': True,
            'message': 'Report deleted successfully'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error deleting report {report_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete report'
        }), 500


@api_bp.route('/reports/<report_id>/sections', methods=['GET'])
def get_report_sections(report_id):
    """
    Get all sections for a specific report.
    
    Args:
        report_id: Unique identifier of the report
        
    Returns:
        JSON response with list of report sections
    """
    try:
        # Validate report ID
        if not report_id or not report_id.strip():
            return jsonify({
                'success': False,
                'error': 'Invalid report ID'
            }), 400
        
        # Get report sections using service
        report_service = ReportService()
        sections = report_service.get_report_sections(report_id)
        
        # Convert sections to dictionaries
        sections_data = [section.to_dict() for section in sections]
        
        return jsonify({
            'success': True,
            'data': sections_data,
            'count': len(sections_data)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting sections for report {report_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve report sections'
        }), 500


@api_bp.route('/reports/<report_id>/sections/<section_id>', methods=['GET'])
def get_report_section(report_id, section_id):
    """
    Get a specific section from a report.
    
    Args:
        report_id: Unique identifier of the report
        section_id: Unique identifier of the section
        
    Returns:
        JSON response with section data
    """
    try:
        # Validate IDs
        if not report_id or not report_id.strip():
            return jsonify({
                'success': False,
                'error': 'Invalid report ID'
            }), 400
        
        if not section_id or not section_id.strip():
            return jsonify({
                'success': False,
                'error': 'Invalid section ID'
            }), 400
        
        # Get report section using service
        report_service = ReportService()
        section = report_service.get_report_section(report_id, section_id)
        
        if not section:
            return jsonify({
                'success': False,
                'error': 'Section not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': section.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting section {section_id} from report {report_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve report section'
        }), 500