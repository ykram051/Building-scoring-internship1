# AI Assistant Chatbot Setup Guide

## Overview

The Building Analytics Dashboard now includes an intelligent AI Assistant that can:
- Answer questions about your building datasets
- Explain application features and ML models
- Generate charts and visualizations from natural language queries
- Provide data analysis and insights

## 🚀 Quick Setup

### 1. Install Dependencies

```bash
cd app
pip install openai langchain langchain-openai langchain-experimental pandasai tiktoken
```

### 2. Get OpenAI API Key

1. Visit https://platform.openai.com/api-keys
2. Create a new API key
3. Copy the key (starts with `sk-...`)

### 3. Configure API Key

**Option A: Environment Variable**
```bash
# Add to .env file
OPENAI_API_KEY=your-actual-api-key-here
```

**Option B: Streamlit Secrets**
```toml
# Add to .streamlit/secrets.toml
[openai]
api_key = "your-actual-api-key-here"
```

### 4. Run the Application

```bash
streamlit run main_db.py
```

The "🤖 AI Assistant" tab will now be available!

## 💬 Example Conversations

### Dataset Analysis
```
User: "Show me the top 10 buildings with worst energy efficiency"
Assistant: [Generates bar chart + analysis]

User: "What's the average building age in this dataset?"
Assistant: [Provides statistical summary]

User: "Create a scatter plot of cost vs energy rating"
Assistant: [Generates interactive scatter plot]
```

### Feature Explanations
```
User: "How does PCA work in building analysis?"
Assistant: "PCA reduces dimensionality of building data while preserving key variations..."

User: "Explain the TOPSIS scoring method"
Assistant: "TOPSIS ranks buildings by calculating distance to ideal solutions..."
```

### Smart Queries
```
User: "Which buildings need the most maintenance?"
Assistant: [Analyzes data and provides insights]

User: "Compare energy efficiency across different building types"
Assistant: [Creates comparison visualizations]
```

## 🎯 Features

### Intelligent Data Analysis
- **Pandas Agent**: Uses LangChain to query datasets programmatically
- **Natural Language**: Ask questions in plain English
- **Context Awareness**: Understands your current dataset
- **Error Handling**: Graceful fallbacks for complex queries

### Chart Generation
- **Auto-Detection**: Determines appropriate chart types
- **Interactive Plots**: Generates Plotly visualizations
- **Custom Analysis**: Tailored insights for building data

### Educational Assistant
- **ML Model Explanations**: Learn about PCA, TOPSIS, Mahalanobis, etc.
- **Feature Guidance**: Understand dashboard capabilities
- **Best Practices**: Get recommendations for analysis

## 🔧 Advanced Configuration

### Custom Models
```python
# In chatbot.py, modify the model configuration:
self.llm = ChatOpenAI(
    temperature=0.1,  # Controls creativity (0-1)
    model_name="gpt-4",  # Use GPT-4 for better responses
    max_tokens=1000  # Control response length
)
```

### Response Customization
```python
# Modify system prompts for domain-specific responses
system_prompt = """
You are an expert building analyst assistant.
Focus on energy efficiency, sustainability, and cost optimization.
Always provide actionable insights.
"""
```

## 🛡️ Security & Privacy

### Data Protection
- **Local Processing**: Data analysis happens locally
- **No Data Storage**: OpenAI doesn't store your building data
- **Secure API**: All communications encrypted

### Access Control
- **Role-Based**: Chatbot respects user permissions
- **Audit Logging**: All interactions are logged
- **Session Isolation**: Each user's chat is separate

## 📊 Usage Analytics

The chatbot logs interactions for:
- **Performance Monitoring**: Track response quality
- **Feature Usage**: Understand popular queries
- **Error Analysis**: Improve reliability

## 🚨 Troubleshooting

### Common Issues

**"API key not found"**
- Check `.env` file or `secrets.toml` configuration
- Ensure API key is valid and has credits

**"Module not found"**
- Install missing dependencies: `pip install -r requirements.txt`
- Check Python environment activation

**"Chat not responding"**
- Verify internet connection
- Check OpenAI service status
- Review error logs in terminal

**"Chart generation fails"**
- Ensure dataset has appropriate columns
- Try simpler query first
- Check for data type issues

### Demo Mode
If API key is not configured, the chatbot runs in demo mode with:
- Pre-built responses for common questions
- Basic dataset summaries
- Limited functionality

## 🎮 Tips for Best Results

### Effective Queries
- ✅ "Show me buildings with energy rating below C"
- ✅ "Create a histogram of building ages"
- ✅ "What's the correlation between size and energy efficiency?"
- ❌ "Make it better" (too vague)
- ❌ "Show everything" (too broad)

### Chart Requests
- Be specific about chart type: "bar chart", "scatter plot", "histogram"
- Mention specific columns when possible
- Ask for comparisons: "compare X vs Y"

### Data Analysis
- Ask for summaries: "summarize this dataset"
- Request top/bottom lists: "top 10 best performers"
- Seek insights: "what trends do you see?"

## 🔮 Future Enhancements

### Planned Features
- **Voice Input**: Speech-to-text for hands-free interaction
- **Advanced Analytics**: Predictive modeling suggestions
- **Report Generation**: Automated insight reports
- **Multi-language**: Support for different languages

### Integration Possibilities
- **Export Integration**: Save chat insights to reports
- **Email Alerts**: Automated analysis summaries
- **API Access**: Programmatic chatbot access
- **Custom Models**: Train on your specific data

---

The AI Assistant transforms your Building Analytics Dashboard into an intelligent, conversational analysis tool. Start exploring your data with natural language today!
