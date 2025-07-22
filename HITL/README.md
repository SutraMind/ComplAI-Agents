# HITL Report Editor

A Human-in-the-Loop report editing system that allows domain experts to review and comment on text-based reports.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
```bash
cp .env.example .env
# Edit .env with your specific settings
```

### 3. Start the Application

#### Option A: Simple Start
```bash
python run.py
```

#### Option B: Advanced Start with Options
```bash
python start.py --config development --setup-data
```

#### Option C: Production Start
```bash
python start.py --config production --host 0.0.0.0 --port 8000
```

### 4. Access the Application
Open your browser and navigate to: http://localhost:5000

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

## Usage

1. **Load a Report**: Place `.txt` files in the `data/reports/` directory
2. **Add Comments**: Select text in the web interface and add comments
3. **Generate Summary**: Use the summary feature to export all comments
4. **Session Persistence**: Your work is automatically saved and restored

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
1. **Port already in use**: Change the port with `--port 8080`
2. **Ollama not accessible**: The app works without LLM features
3. **Permission errors**: Ensure write access to the `data/` directory

### Logs
- Development: Console output
- Production: `logs/hitl.log`

## API Endpoints

- `GET /health` - Health check
- `GET /api/reports` - List reports
- `GET /api/reports/{id}` - Get specific report
- `POST /api/reports/{id}/comments` - Add comment
- `GET /api/reports/{id}/summary` - Generate summary

For more detailed API documentation, see the backend code.