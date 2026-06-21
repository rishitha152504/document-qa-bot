# Deployment Guide

Follow these steps to push to GitHub and deploy on Streamlit Community Cloud.

## Step 1: Get a Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Click **Create API Key**
4. Copy the key

## Step 2: Configure Locally

```powershell
cd C:\Users\dines\OneDrive\Desktop\QAbot
copy .env.example .env
```

Edit `.env` and paste your key:

```
GEMINI_API_KEY=AIza...your_key_here
```

## Step 3: Index Documents

```powershell
.\venv\Scripts\activate
python -m src.ingest
```

This creates the `db/` vector database. For cloud deployment, commit it:

```powershell
git add db/
git commit -m "Add pre-indexed vector database for cloud deployment"
```

## Step 4: Push to GitHub

### Option A — GitHub CLI (recommended)

```powershell
gh auth login
gh repo create document-qa-bot --public --source=. --remote=origin --push
```

### Option B — Manual

1. Go to [github.com/new](https://github.com/new)
2. Repository name: `document-qa-bot`
3. Set to **Public**
4. Do NOT initialize with README (already exists locally)
5. Run:

```powershell
git remote add origin https://github.com/rishitha152504/document-qa-bot.git
git branch -M main
git push -u origin main
```

**Your GitHub repo URL will be:**
`https://github.com/rishitha152504/document-qa-bot`

## Step 5: Deploy on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click **New app**
4. Configure:
   - **Repository:** `rishitha152504/document-qa-bot`
   - **Branch:** `main`
   - **Main file path:** `app.py`
5. Click **Advanced settings** → **Secrets** and add:

```toml
GEMINI_API_KEY = "AIza...your_key_here"
```

6. Click **Deploy**

**Your live app URL will be:**
`https://document-qa-bot-rishitha152504.streamlit.app`
(or similar — Streamlit assigns the URL on deploy)

## Step 6: Verify Deployment

1. Open the Streamlit app URL
2. If the database wasn't committed, click **Re-index Documents** in the sidebar
3. Ask: *What was Acme Corporation's net revenue growth in FY2026?*
4. Expected answer: **14%** with citation from `business_doc.pdf`

## Submission Checklist

| Item | Link |
|------|------|
| GitHub Repository | `https://github.com/rishitha152504/document-qa-bot` |
| Live Deployed App | Your Streamlit Cloud URL |
| Screen Recording | Record 3–5 min walkthrough, upload to Drive/Loom/YouTube |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `GEMINI_API_KEY is not set` | Add key to `.env` locally or Streamlit secrets |
| `Database not indexed` | Run `python -m src.ingest` or click Re-index in sidebar |
| `Repository not found` | Create the GitHub repo first (Step 4) |
| ChromaDB errors on cloud | Commit pre-built `db/` folder after local indexing |
