"""
API module for the HITL Report Editor.
"""

from flask import Blueprint

# Create API blueprint
api_bp = Blueprint('api', __name__)

# Import routes to register them with the blueprint
from . import simple_reports