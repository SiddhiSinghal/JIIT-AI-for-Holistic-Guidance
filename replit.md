# Overview

JIIT AI for Holistic Guidance is a Flask-based web application designed to provide comprehensive career and academic guidance for students at Jaypee Institute of Information Technology (JIIT). The platform leverages AI agents to deliver personalized recommendations, skill profiling, career exploration, mental health support, and academic planning. Students can upload their academic marksheets, take assessment tests, interact with intelligent chatbots, and receive data-driven insights to guide their educational and professional journey.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Web Framework
- **Flask** serves as the core web framework, handling routing, session management, and template rendering
- Uses Jinja2 templating engine for dynamic HTML generation
- Session-based authentication with secure password hashing via Werkzeug

## Database Layer
- **MongoDB** for persistent data storage (user accounts, marksheets, assessment scores)
- Custom `MockMongoClient` in `db_adapter.py` provides a fallback JSON file-based storage mechanism when MongoDB is unavailable
- User data model includes: username, email, password hash, uploaded marksheets, and assessment history
- Collections: `holistic_guidance.users` stores all user-related data

## AI Agent System
The application implements a multi-agent architecture where specialized agents handle different types of user queries:

### LLM-Powered Agents (require API keys)
1. **Career Exploration Agent** - Provides detailed job role information using OpenAI GPT-4 API
2. **Roadmap Agent** - Generates personalized learning roadmaps with weekly breakdowns
3. **LinkedIn Post Generator** - Creates professional LinkedIn content using Ollama/local LLM
4. **Web Researcher Agent** - Performs web searches and Wikipedia lookups using SerpAPI and LangChain
5. **Fact Checker Agent** - Verifies claims using search results and LLM reasoning
6. **MOOC Agent** - Uses NVIDIA DeepSeek with RAG (Retrieval-Augmented Generation) to extract course information from PDF documents

### Non-LLM Agents (local processing)
1. **Job Recommendation Agent** - Uses pre-trained RandomForest classifier to predict suitable job roles based on academic performance
2. **Skill Profiler Agent** - Analyzes uploaded marksheets to build student skill profiles across 50+ technical competencies
3. **Market Score Agent** - Evaluates market demand for subjects using local keyword-based scoring
4. **Subject Recommendation Agent** - Suggests elective courses using skill alignment and prerequisite analysis

## Orchestrator & Prompt Classification
- `orchestrator_cli.py` routes user prompts to appropriate agents based on keyword classification
- Supports test invocation (aptitude, communication, creativity, coding) via natural language commands
- Falls back to unified chat interface for unrecognized intents

## Academic Analysis Pipeline
1. **PDF Processing** - PyMuPDF (fitz) extracts text from uploaded marksheets
2. **Grade Extraction** - Regex patterns identify subject-grade pairs (A+, A, B+, etc.)
3. **Skill Mapping** - `LocalPredictionModel` maps subjects to 80+ skill labels using keyword matching
4. **Profile Building** - Aggregates grades into weighted skill competency scores
5. **Recommendation Scoring** - Combines student profile, market demand, and prerequisite fulfillment

## Mental Health Support
- RAG-based mental health chatbot provides empathetic responses to student emotional concerns
- Uses LangChain with ChromaDB for context-aware conversation
- Keyword-triggered support responses for common emotional states (stress, anxiety, depression)

## Assessment System
- JSON-based question banks for aptitude (50 questions), communication, creativity, and coding tests
- Browser-based test delivery with timed sessions
- Scores stored in MongoDB assessments array
- Results feed into job recommendation model as feature inputs

## Caching Strategy
- File-based cache (JSON) for market scores to reduce redundant computations
- Subject-to-skills mappings cached in `data/cache/subject_skills.json`
- Uses MD5 hashing of subject names as cache keys

## External Service Integrations
- **OpenAI API** (GPT-4) for career guidance and roadmap generation
- **SerpAPI** for web search capabilities in research and fact-checking agents
- **Wikipedia API** via LangChain for knowledge retrieval
- **Ollama** for local LLM inference (Mistral model)
- **NVIDIA AI Endpoints** for DeepSeek model access in MOOC agent
- **HuggingFace Embeddings** (sentence-transformers) for RAG vector search

## Alternative Interfaces
- **Streamlit app** (`main.py`) provides interactive elective recommendation interface
- Uses Plotly for skill profile visualizations
- Reads from Excel/CSV master subject database (`data/subjects.xlsx`)

## Key Design Decisions

**Hybrid LLM Strategy**: The system gracefully degrades when API keys are unavailable, using local models and rule-based fallbacks to maintain functionality.

**Mock Database Adapter**: Enables development and testing without requiring MongoDB installation - automatically persists data to `data.json`.

**Agent Specialization**: Separates concerns by domain (career, mental health, academics) rather than building a monolithic AI, improving maintainability and response quality.

**Skill-Label Taxonomy**: Uses a comprehensive 80+ skill ontology to bridge academic subjects and career requirements, enabling transferable skill analysis.

**Progressive Enhancement**: Core features (profile, uploads, basic recommendations) work without AI; advanced features (chat, roadmaps) require API access.

# External Dependencies

## Core Services
- **MongoDB** (localhost:27017) - Primary data persistence layer
- **OpenAI API** - GPT-4 model for career guidance (requires `OPENAI_API_KEY`)
- **SerpAPI** - Web search functionality (requires `SERPAPI_API_KEY`)
- **Ollama** - Local LLM inference server running Mistral model
- **NVIDIA AI Endpoints** - DeepSeek model access (API key hardcoded in `mooc.py`)

## Python Packages
- **Flask ecosystem**: Flask, Flask-Login, Flask-SQLAlchemy, Werkzeug
- **Database**: pymongo, psycopg2-binary
- **AI/ML**: openai, google-generativeai, langchain, langchain-community, langchain-nvidia-ai-endpoints, langchain-huggingface
- **Data processing**: pandas, numpy, scikit-learn, openpyxl
- **PDF handling**: pymupdf (fitz)
- **Visualization**: streamlit, plotly
- **Vector store**: chromadb, FAISS
- **Utilities**: python-dotenv, requests, markupsafe

## Data Files
- `data/subjects.xlsx` - Master database of elective courses with metadata
- `aptitude_questions.json` - Question bank for aptitude assessments
- `agents/job_model.pkl` - Trained RandomForest classifier for job prediction
- `agents/label_encoder.pkl` - Label encoder for job categories
- `agents/uu.pdf` - MOOC course catalog for RAG-based queries
- `static/2024.json`, `static/2025.json` - Placement statistics and company visit data

## Environment Variables
- `OPENAI_API_KEY` - OpenAI API authentication
- `SERPAPI_API_KEY` - SerpAPI authentication
- `LLM_MODEL` - Local LLM model name (default: "mistral")
- Flask `secret_key` - Currently hardcoded, should be moved to environment variable for production

## Notes
- The application currently uses hardcoded database connection strings and should be migrated to environment variables
- NVIDIA API key is embedded in source code and should be externalized
- Some agents reference both local and cloud LLM services, requiring configuration management for deployment flexibility