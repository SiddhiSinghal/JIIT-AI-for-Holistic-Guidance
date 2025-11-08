# JIIT AI for Holistic Guidance

## Overview
A Flask-based web application providing comprehensive career and academic guidance using AI agents. The application offers career exploration, mental health support, skill profiling, elective recommendations, and various assessment tests.

## Current State
The application has been successfully configured to run in the Replit environment with the following adaptations:
- **Database**: Using a JSON-based mock MongoDB adapter (replaces MongoDB requirement)
- **Frontend**: Flask web application running on port 5000
- **Alternative Interface**: Streamlit app available via `main.py` (not configured as default workflow)

## Recent Changes (November 8, 2025)

### Initial Environment Setup
- Installed Python 3.11 and all required dependencies
- Configured Flask to run on 0.0.0.0:5000 for Replit compatibility
- Created mock MongoDB adapter using JSON file storage (db_adapter.py)
- Fixed PyMuPDF import issues
- Created stub for summer_project.rag_chain module
- Fixed chat functionality errors (KeyError and duplicate JavaScript)
- Cleaned up duplicate agent files from root directory

### UI/UX Modernization (November 8, 2025)
Complete redesign of the application interface with JIIT branding:

**Visual Assets**
- Added official JIIT Noida logo to header across all pages
- Created AI education hero banner for landing page
- Implemented consistent JIIT color scheme (primary blue, secondary orange, accent cyan)

**New Design System**
- Created comprehensive CSS stylesheet (`static/css/style.css`) with:
  - JIIT-branded color palette and design tokens
  - Modern typography using Segoe UI font family
  - Responsive grid layouts for all screen sizes
  - Smooth animations and transitions
  - Professional shadows and elevation system

**Redesigned Pages**
1. **Landing Page (index.html)**
   - Hero section with gradient background and hero banner
   - Feature showcase grid with 9 key features
   - Icons for each feature category
   - About section explaining the platform
   - Smooth scroll navigation
   - Mobile-responsive design

2. **Home Dashboard (home.html)**
   - Fixed side panel with all agent features (icons + labels)
   - Quick action cards for major features
   - Welcome section with getting started guide
   - Persistent navigation across all authenticated pages

3. **Chat Interface (chat.html)**
   - Modern chat UI with message bubbles
   - Avatar icons for user and AI
   - Fixed side panel for easy feature switching
   - Professional header with branding
   - Improved message display with animations

4. **Authentication Pages (login.html, signup.html)**
   - Centered card design with gradient background
   - JIIT logo integration
   - Icon-labeled form fields
   - Professional styling with proper validation
   - Consistent branding across both pages

**Navigation Improvements**
- Fixed side panel visible on home and chat pages
- 11 quick-access feature buttons with icons:
  - Career Guidance
  - Mental Health Support
  - Skill Profiling
  - Elective Suggestions
  - Job Recommendations
  - MOOC Courses
  - Market Analysis
  - Aptitude Test
  - Communication Test
  - Creativity Test
  - Coding Test

**Responsive Design**
- Mobile-first approach with breakpoints for tablets and desktop
- Collapsible side panel on mobile devices
- Adaptive grid layouts
- Touch-friendly buttons and controls

### Files Modified
- **app.py**: Updated to use MockMongoClient and bind to 0.0.0.0:5000, fixed chat errors
- **requirements.txt**: Fixed version conflicts (Flask 2.3.3)
- **db_adapter.py**: Created JSON-based MongoDB-compatible database adapter
- **summer_project/rag_chain.py**: Created placeholder mental health response function
- **.gitignore**: Updated with Python-specific patterns
- **static/css/style.css**: New comprehensive stylesheet with JIIT branding
- **static/images/**: Added jiit-logo.jpg and hero-banner.png
- **templates/index.html**: Complete redesign with hero section and features
- **templates/home.html**: Dashboard with side panel and quick actions
- **templates/chat.html**: Modern chat interface with side panel
- **templates/login.html**: Modern authentication design
- **templates/signup.html**: Modern registration design

### Database Structure
The application uses a JSON file (`data.json`) to store:
- User accounts (username, email, password hash)
- Uploaded marksheet data (semester, branch, SGPA, CGPA, subjects with grades)
- Assessment results (aptitude, communication, creativity, coding tests)
- Chat history

## Project Architecture

### Core Components
1. **Flask Web App** (`app.py`): Main application with authentication, chat, tests, and profile management
2. **Streamlit Interface** (`main.py`): Alternative interface for elective and MOOC recommendations
3. **AI Agents** (`agents/`): Various specialized agents for career guidance, job recommendations, skill profiling
4. **Orchestrator** (`orchestrator_cli.py`): Routes user queries to appropriate AI agents
5. **Utils** (`utils/`): Skill mapping, market scoring, and AI utility functions

### Key Features
- User authentication (signup/login)
- Career guidance chat interface
- Mental health support chat
- PDF marksheet upload and parsing
- Assessment tests (Aptitude, Communication, Creativity, Coding)
- Skill profiling based on academic performance
- Elective recommendations
- Job recommendations using ML

### Templates
HTML templates are in `templates/` directory:
- `index.html`, `home.html`: Landing and home pages
- `login.html`, `signup.html`: Authentication
- `chat.html`: Unified chat interface
- `profile.html`: User profile with marksheet upload
- `*_test.html`: Various assessment test pages
- `test_done.html`: Test completion page

## User Preferences

### API Keys
The application supports optional AI features that require API keys:
- `OPENAI_API_KEY`: For OpenAI-powered features
- `GOOGLE_API_KEY`: For Google Generative AI features

These should be added as Replit Secrets if you want to use AI-powered features. The app will work without them but with limited functionality.

## Running the Application

### Main Flask App (Default)
The Flask app runs automatically via the configured workflow:
- Accessible at the Replit webview URL
- Serves the main web interface with all features

### Alternative: Streamlit Interface
To run the Streamlit elective recommendation interface:
```bash
streamlit run main.py --server.port 8501
```

### CLI Orchestrator
For command-line interaction:
```bash
python orchestrator_cli.py
```

## Important Notes

### Database
- Currently uses JSON file storage (data.json) instead of MongoDB
- All data persists in the `data.json` file
- For production use, consider migrating to a proper database

### PDF Processing
- Expects JIIT-format marksheets
- Extracts semester, branch, SGPA, CGPA, and subject grades
- Uploaded files stored in `uploads/` directory

### Testing Features
- Some features require API keys to function fully
- The mental health chat currently uses a placeholder response
- Assessment tests work without external APIs

### Deployment
Configured for Replit Autoscale deployment using Gunicorn WSGI server.

## Next Steps

### For Full Functionality
1. Add API keys (OPENAI_API_KEY, GOOGLE_API_KEY) as Replit Secrets
2. Implement the RAG chain for mental health support (summer_project.rag_chain)
3. Consider migrating to a proper database for production use
4. Test all AI agent features and workflows
5. Customize the AI prompts and responses for your specific use case

### Optional Enhancements
- Add caching for AI responses
- Implement proper session management
- Add more comprehensive error handling
- Create admin dashboard for monitoring
- Add analytics and usage tracking
