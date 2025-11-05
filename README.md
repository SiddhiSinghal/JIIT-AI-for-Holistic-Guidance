# JIIT AI for Holistic Guidance

A Flask-based web application for comprehensive career and academic guidance using AI agents.

## Prerequisites

1. **Python 3.8+** installed on your system
2. **MongoDB** installed and running locally (default: `mongodb://localhost:27017/`)
3. **pip** package manager

## Quick Start (TL;DR)

```bash
# 1. Install dependencies
python -m pip install -r requirements.txt

# 2. Ensure MongoDB is running (see MongoDB setup below)

# 3. Run the Flask app
python app.py

# 4. Open browser to http://localhost:5000
```

For detailed instructions, see [QUICK_START.md](QUICK_START.md)

## Setup Instructions

### 1. Install Python Dependencies

```bash
python -m pip install -r requirements.txt
```

**Note:** If you encounter any issues, you may also need to install core packages:
```bash
python -m pip install flask pymongo pymupdf werkzeug python-dotenv
```

### 2. Start MongoDB

Make sure MongoDB is running on your system:

**Windows:**
```bash
# If MongoDB is installed as a service, it should start automatically
# Otherwise, navigate to MongoDB bin directory and run:
mongod
```

**Linux/Mac:**
```bash
sudo systemctl start mongod  # Linux
# or
brew services start mongodb-community  # Mac
```

### 3. Verify MongoDB Connection

The application connects to MongoDB at `mongodb://localhost:27017/` by default. Make sure MongoDB is accessible.

## Running the Application

### Option 1: Flask Web Application (Main App)

This is the primary web interface for the holistic guidance system:

```bash
python app.py
```

The application will start on `http://127.0.0.1:5000` (or `http://localhost:5000`)

**Features:**
- User authentication (signup/login)
- Career chat interface
- Mental health chat
- Profile management with marksheet upload (PDF)
- Dashboard interface

### Option 2: Streamlit Elective Recommendations (Alternative Interface)

This provides a Streamlit-based interface for elective and MOOC recommendations:

```bash
streamlit run main.py
```

The application will start on `http://localhost:8501`

**Features:**
- Skill profile building
- Elective recommendations based on strengths
- Market trend analysis
- MOOC suggestions

### Option 3: CLI Orchestrator

For command-line interaction with the AI agents:

```bash
python orchestrator_cli.py
```

## Project Structure

```
JIIT-AI-for-Holistic-Guidance/
├── app.py                 # Main Flask web application
├── main.py                # Streamlit elective advisor
├── orchestrator_cli.py    # CLI orchestrator for agents
├── agents/                # Various AI agents
│   ├── career_exploration.py
│   ├── mooc.py
│   ├── job_recommendation.py
│   └── ...
├── templates/             # HTML templates for Flask
├── static/                # Static files
├── uploads/               # User uploaded files (PDFs)
├── data/                  # Data files (subjects.xlsx)
└── requirements.txt      # Python dependencies
```

## Key Features

1. **Career Guidance**: AI-powered career exploration and recommendations
2. **Skill Profiling**: Analyze student skills based on academic performance
3. **MOOC Recommendations**: Suggest relevant online courses based on subjects
4. **Job Recommendations**: ML-based job recommendations
5. **Market Analysis**: Industry demand scoring for skills/subjects
6. **Mental Health Support**: Chat interface for mental health guidance

## Troubleshooting

### MongoDB Connection Issues

If you see MongoDB connection errors:
- Ensure MongoDB is installed and running
- Check if MongoDB is accessible at `mongodb://localhost:27017/`
- Verify MongoDB service is running: `mongosh` or `mongo` command should work

### Missing Dependencies

If you encounter import errors:
```bash
pip install --upgrade -r requirements.txt
```

### PDF Processing Issues

If PDF extraction fails:
- Ensure `PyMuPDF` (fitz) is installed: `pip install pymupdf`
- Check that uploaded PDFs are in the correct format (JIIT marksheet format)

## Environment Variables

Some agents may require API keys. Check `orchestrator_cli.py` and agent files for any required environment variables. Create a `.env` file in the root directory if needed:

```
OPENAI_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
```

## Default Access

- **Flask App**: http://localhost:5000
- **Streamlit App**: http://localhost:8501

## Notes

- The application uses MongoDB for user data storage
- Uploaded PDFs are stored in the `uploads/` directory
- Cache files are stored in the `cache/` directory
- The application runs in debug mode by default (change in `app.py` for production)

