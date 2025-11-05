# Quick Start Guide

## Step-by-Step Setup

### 1. Install Dependencies

Open PowerShell/Command Prompt in the project directory and run:

```bash
python -m pip install -r requirements.txt
```

If you encounter issues, install core dependencies first:
```bash
python -m pip install flask pymongo pymupdf werkzeug python-dotenv
```

### 2. Start MongoDB

**Option A: If MongoDB is installed as a Windows Service**
- MongoDB should be running automatically
- Skip to step 3

**Option B: If MongoDB needs to be started manually**
- Open a new terminal
- Navigate to MongoDB bin directory (usually `C:\Program Files\MongoDB\Server\<version>\bin\`)
- Run: `mongod.exe`

**Option C: Install MongoDB if not installed**
- Download from: https://www.mongodb.com/try/download/community
- Or use MongoDB Atlas (cloud): https://www.mongodb.com/cloud/atlas

### 3. Verify MongoDB Connection

Test MongoDB connection:
```bash
python -c "from pymongo import MongoClient; client = MongoClient('mongodb://localhost:27017/'); print('✅ MongoDB connected!' if client.server_info() else '❌ Connection failed')"
```

### 4. Run the Flask Application

**Main Web Application:**
```bash
python app.py
```

Then open your browser and go to: **http://localhost:5000**

### 5. Alternative: Run Streamlit App

**For Elective Recommendations:**
```bash
streamlit run main.py
```

Then open: **http://localhost:8501**

## Troubleshooting

### Issue: "ModuleNotFoundError" when running app.py

**Solution:** Install missing packages:
```bash
python -m pip install <package-name>
```

Common missing packages:
- `pymongo` - for MongoDB
- `pymupdf` - for PDF processing (imported as `fitz`)
- `flask` - web framework

### Issue: "MongoDB connection failed"

**Solutions:**
1. Ensure MongoDB is running: Check Windows Services or run `mongod`
2. Check MongoDB is on default port 27017
3. If using MongoDB Atlas, update connection string in `app.py` line 16

### Issue: "No module named 'summer_project.rag_chain'"

**Solution:** The mental health chat feature requires this module. You can:
1. Temporarily comment out the import in `app.py` line 9
2. Or create the missing module (see agents/requirements.txt for dependencies)

### Issue: Missing template files

**Solution:** Ensure all HTML templates exist in the `templates/` folder:
- `login.html`
- `signup.html`
- `chat.html`
- `dashboard.html`
- `profile.html`
- `layout.html`

## First Run Checklist

- [ ] Python 3.8+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] MongoDB running and accessible
- [ ] All template files present
- [ ] `uploads/` folder exists (created automatically)

## Testing the Application

1. **Sign Up**: Create a new account at http://localhost:5000/signup
2. **Login**: Use your credentials to log in
3. **Upload Marksheet**: Go to Profile and upload a PDF marksheet
4. **Career Chat**: Try asking career-related questions
5. **Dashboard**: View your profile and recommendations

## Next Steps

- Configure API keys in `.env` file if needed (for OpenAI/Google AI features)
- Customize the application settings in `app.py`
- Review agent configurations in `agents/` directory

