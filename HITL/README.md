# HITL Report Editor

A Human-in-the-Loop report editing system that allows domain experts to review and comment on text-based reports with AI-powered summary generation.

## Features

- **Interactive Report Viewing**: Load and view text-based reports in a clean, readable interface
- **Collaborative Commenting**: Add contextual comments to specific sections of reports
- **AI-Powered Summaries**: Generate intelligent summaries of comments using LLM integration
- **Session Persistence**: Automatically save and restore your work across sessions
- **Multi-User Support**: Handle multiple users reviewing different reports simultaneously
- **Export Capabilities**: Export comments and summaries for further analysis

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Optional: Ollama for AI summary features

### 1. Install Dependencies
```bash
# Clone or download the HITL system
cd HITL

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your specific settings (optional)
# The system works with default settings
```

### 3. Set Up Sample Data (Optional)
```bash
# Create sample reports for testing
python start.py --setup-data
```

### 4. Start the Application

#### Option A: Simple Start (Recommended for first-time users)
```bash
python run.py
```

#### Option B: Development Mode with Sample Data
```bash
python start.py --config development --setup-data
```

#### Option C: Production Mode
```bash
python start.py --config production --host 0.0.0.0 --port 8000
```

### 5. Access the Application
Open your browser and navigate to: **http://localhost:5000**

You should see the HITL Report Editor interface with available reports to review.

## Configuration Options

### Environment Variables
- `FLASK_CONFIG`: `development` or `production` (default: development)
- `FLASK_DEBUG`: `true` or `false` (default: false)
- `FLASK_HOST`: Host to bind to (default: 0.0.0.0)
- `FLASK_PORT`: Port to bind to (default: 5000)
- `SECRET_KEY`: Flask secret key for sessions
- `OLLAMA_URL`: Ollama server URL (default: http://localhost:11434)
- `OLLAMA_MODEL`: LLM model to use (default: gemma2:27b)

### Configuration Profiles
- **Development**: Debug enabled, verbose logging, CSRF disabled
- **Production**: Debug disabled, secure cookies, error logging, HTTPS preferred

## Directory Structure
```
HITL/
├── backend/           # Flask backend application
├── frontend/          # Static frontend files
├── data/             # Application data
│   ├── reports/      # Text reports to review
│   ├── comments/     # User comments storage
│   └── summaries/    # Generated summaries
├── tests/            # Test suite
├── logs/             # Application logs
├── run.py            # Main application entry point
├── start.py          # Advanced startup script
└── requirements.txt  # Python dependencies
```

## Usage Guide

### Adding Reports
1. Place your text reports (`.txt` files) in the `data/reports/` directory
2. Refresh the application or restart to see new reports
3. Reports appear in the report selector dropdown

### Reviewing Reports
1. **Select a Report**: Choose from the dropdown menu
2. **Read and Navigate**: Scroll through the report content
3. **Add Comments**: 
   - Select any text in the report
   - Click "Add Comment" in the popup
   - Enter your comment and save
4. **View Comments**: Comments appear in the sidebar with context

### Managing Comments
- **Edit Comments**: Click the edit icon next to any comment
- **Delete Comments**: Click the delete icon to remove comments
- **Navigate**: Click on comments in the sidebar to jump to that section

### Generating Summaries
1. Click the "Generate Summary" button
2. Wait for AI processing (requires Ollama setup)
3. View the generated summary in the modal
4. Export or copy the summary as needed

### Session Management
- Your work is automatically saved as you make changes
- Comments persist between browser sessions
- Multiple users can work on different reports simultaneously

## Development

### Running Tests
```bash
python start.py --test
```

### Setting Up Sample Data
```bash
python start.py --setup-data
```

### Development Mode
```bash
python start.py --config development
```

## Troubleshooting

### Common Issues

#### Application Won't Start
- **Port already in use**: Change the port with `--port 8080` or `python start.py --port 8080`
- **Missing dependencies**: Run `pip install -r requirements.txt`
- **Python version**: Ensure Python 3.8+ is installed

#### Reports Not Loading
- **No reports visible**: Check that `.txt` files are in `data/reports/` directory
- **Permission errors**: Ensure read/write access to the `data/` directory
- **File format**: Only `.txt` files are supported currently

#### Comments Not Saving
- **Permission errors**: Ensure write access to `data/comments/` directory
- **Browser issues**: Try refreshing the page or clearing browser cache
- **Session expired**: Restart the application if comments aren't persisting

#### AI Summary Not Working
- **Ollama not accessible**: The app works without LLM features, summaries will be disabled
- **Model not available**: Check that the specified model is installed in Ollama
- **Network issues**: Verify Ollama server is running on the configured URL

#### Performance Issues
- **Large reports**: Break large reports into smaller files for better performance
- **Many comments**: Consider archiving old comments periodically
- **Browser memory**: Refresh the page if the interface becomes slow

### Getting Help

#### Check Logs
- **Development mode**: Check console output for error messages
- **Production mode**: Check `logs/hitl.log` for detailed error information

#### Verify Setup
```bash
# Run the setup verification script
python verify_setup.py
```

#### Test Configuration
```bash
# Test with sample data
python start.py --setup-data --test
```

### Advanced Configuration

#### Environment Variables
Create a `.env` file or set these environment variables:

```bash
# Application Configuration
FLASK_CONFIG=development          # or 'production'
FLASK_DEBUG=true                 # Enable debug mode
FLASK_HOST=0.0.0.0              # Host to bind to
FLASK_PORT=5000                 # Port to use

# Security
SECRET_KEY=your-secret-key-here  # Change in production!

# AI Integration
OLLAMA_URL=http://localhost:11434  # Ollama server URL
OLLAMA_MODEL=gemma3:27b           # Model to use for summaries
OLLAMA_TIMEOUT=30                 # Request timeout in seconds

# File Handling
MAX_CONTENT_LENGTH=16777216       # Max file size (16MB)
```

#### Production Deployment
For production deployment, see the [Deployment Guide](#deployment) section below.

## API Endpoints

- `GET /health` - Health check
- `GET /api/reports` - List reports
- `GET /api/reports/{id}` - Get specific report
- `POST /api/reports/{id}/comments` - Add comment
- `GET /api/reports/{id}/summary` - Generate summary

For more detailed API documentation, see the backend code.