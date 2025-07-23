# AI Chatbot Configuration Guide

## Overview
The Building Analytics Dashboard includes an AI-powered chatbot assistant that can help users understand machine learning models, analyze datasets, and get insights from their building data.

## Configuration

### Basic Setup (Demo Mode)
The chatbot works in demo mode by default with pre-programmed responses for common questions about:
- Machine learning models (PCA, TOPSIS, Mahalanobis, etc.)
- Building analytics concepts
- Dataset summaries
- Feature explanations

### Full AI Mode (OpenAI Integration)
To enable advanced AI capabilities:

1. **Get an OpenAI API Key**
   - Visit [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
   - Create an account and generate an API key
   - Note: This requires a paid OpenAI account

2. **Configure the API Key**
   - Edit the file: `app/.streamlit/secrets.toml`
   - Replace `api_key = "demo-mode"` with your actual API key:
     ```toml
     [openai]
     api_key = "sk-your-actual-api-key-here"
     ```

3. **Restart the Application**
   - Stop and restart the Streamlit application
   - The chatbot will now have full AI capabilities

## Features

### Demo Mode Features
- ✅ Model explanations (PCA, TOPSIS, Mahalanobis, Weighted, Cosine, Tree)
- ✅ Dataset summaries and basic statistics
- ✅ Feature relationship explanations
- ✅ Building analytics guidance
- ✅ Use case recommendations

### Full AI Mode Features (Requires OpenAI API Key)
- ✅ All demo mode features
- ✅ Natural language data analysis
- ✅ Advanced dataset queries
- ✅ Dynamic chart generation
- ✅ Contextual building insights
- ✅ Interactive data exploration

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
- Monitor your OpenAI usage and costs

## Troubleshooting

**"Demo Mode" message appears:**
- Check that your API key is properly configured in secrets.toml
- Ensure the API key is valid and active
- Restart the application after making changes

**Import errors:**
- Ensure all required packages are installed: `pip install -r requirements.txt`
- Check that langchain and openai packages are available

**Chat not responding:**
- Check your internet connection
- Verify your OpenAI account has available credits
- Look for error messages in the application logs
