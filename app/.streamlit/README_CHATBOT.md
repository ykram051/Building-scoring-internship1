# AI Chatbot Configuration Guide

## Overview
The Building Analytics Dashboard includes an AI-powered chatbot assistant powered by **Google Gemini (FREE!)** that can help users understand machine learning models, analyze datasets, and get insights from their building data.

## Configuration

### Basic Setup (Demo Mode)
The chatbot works in demo mode by default with pre-programmed responses for common questions about:
- Machine learning models (PCA, TOPSIS, Mahalanobis, etc.)
- Building analytics concepts
- Dataset summaries
- Feature explanations

### Full AI Mode (Google Gemini Integration - FREE!)
To enable advanced AI capabilities:

1. **Get a FREE Google Gemini API Key**
   - Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Sign in with your Google account
   - Click "Create API Key" - **No credit card required!**
   - Copy your API key

2. **Configure the API Key**
   - Edit the file: `app/.streamlit/secrets.toml`
   - Replace `api_key = "demo-mode"` with your actual API key:
     ```toml
     [gemini]
     api_key = "your-actual-gemini-api-key-here"
     ```

3. **Install Dependencies (if needed)**
   ```bash
   pip install google-generativeai langchain-google-genai
   ```

4. **Restart the Application**
   - Stop and restart the Streamlit application
   - The chatbot will now have full AI capabilities powered by Gemini!

## Why Google Gemini?

✅ **Completely FREE** - No credit card required  
✅ **High performance** - Comparable to GPT-3.5/4  
✅ **Generous limits** - High rate limits for free tier  
✅ **Easy setup** - Simple API key generation  
✅ **Google ecosystem** - Reliable and well-supported  

## Features

### Demo Mode Features
- ✅ Model explanations (PCA, TOPSIS, Mahalanobis, Weighted, Cosine, Tree)
- ✅ Dataset summaries and basic statistics
- ✅ Feature relationship explanations
- ✅ Building analytics guidance
- ✅ Use case recommendations

### Full AI Mode Features (FREE with Gemini API Key)
- ✅ All demo mode features
- ✅ Natural language data analysis
- ✅ Advanced dataset queries
- ✅ Dynamic chart generation
- ✅ Contextual building insights
- ✅ Interactive data exploration
- ✅ **Powered by Google Gemini Pro model**

## Usage Examples

**Ask about models:**
- "What does PCA do?"
- "Which model should I use for ranking buildings?"
- "Explain TOPSIS in simple terms"

**Analyze your data:**
- "Summarize my dataset"
- "Show me the top 10 most efficient buildings"
- "Find buildings with unusual patterns"

**Get guidance:**
- "What can you help me with?"
- "How do I choose the right model?"

## Security Notes
- API keys are stored securely in the secrets.toml file
- The file is excluded from version control
- Never share your API key publicly
- Google Gemini is free - no cost monitoring needed!

## Troubleshooting

**"Demo Mode" message appears:**
- Check that your Gemini API key is properly configured in secrets.toml
- Ensure the API key is valid and active
- Restart the application after making changes

**"Missing Dependencies" error:**
- Install required packages: `pip install google-generativeai langchain-google-genai`
- Restart the application after installation

**Import errors:**
- Ensure all required packages are installed: `pip install -r requirements.txt`
- Check that google-generativeai and langchain-google-genai packages are available

**Chat not responding:**
- Check your internet connection
- Verify your Gemini API key is valid
- Check if you've exceeded the rate limit (very generous on free tier)
- Look for error messages in the application logs

## Getting Your FREE Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated key
5. Paste it in your secrets.toml file

**That's it! No credit card, no payment required!**
