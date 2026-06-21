@echo off
REM One-click setup script for Document Q&A Bot
echo ========================================
echo   Document Q&A Bot - Setup Script
echo ========================================
echo.

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

if not exist .env (
    echo.
    echo WARNING: .env file not found!
    echo Copy .env.example to .env and add your GEMINI_API_KEY
    copy .env.example .env
    echo Created .env from template - please edit it with your API key.
    pause
)

if not exist data\business_doc.pdf (
    echo Generating sample documents...
    python scripts\generate_sample_docs.py
)

echo.
echo Indexing documents into vector database...
python -m src.ingest

echo.
echo ========================================
echo   Setup complete! Run the app with:
echo   streamlit run app.py
echo ========================================
pause
