# 🤖 AI Assistant User Guide

## Overview
The Building Analytics Dashboard now includes an intelligent AI Assistant that helps you explore and understand your building data through natural language conversations.

## Features

### 🔍 **Data Analysis & Insights**
- Ask questions about your dataset in plain English
- Get summaries and statistical insights
- Explore patterns and trends in your data

### 📊 **Chart Generation**
- Request custom visualizations: "Show me a scatter plot of energy vs CO2"
- Generate histograms, bar charts, and distribution plots
- Create comparative visualizations between building classes

### 💡 **Feature Explanations**
- Learn about classification methods (PCA, TOPSIS, Mahalanobis, etc.)
- Understand building energy efficiency metrics
- Get explanations of scoring algorithms

### 📈 **Interactive Data Exploration**
- Query specific buildings or ranges
- Compare building performance
- Find patterns in your data

## How to Use

### 1. **Access the AI Assistant**
- Open the Building Analytics Dashboard
- Navigate to the **"🤖 AI Assistant"** tab
- The chat interface will load automatically

### 2. **Start Chatting**
- Type your questions in the chat input box
- Press Enter or click Send
- The AI will respond with insights and analysis

### 3. **Example Questions**
```
📊 Data Analysis
• "What's the average energy consumption by building class?"
• "Show me the distribution of CO2 emissions"
• "Summarize my dataset"

🔍 Specific Queries  
• "Find the top 10 most energy-efficient buildings"
• "Which buildings are in class A?"
• "Show me buildings with high water usage"

📈 Visualizations
• "Create a scatter plot of energy vs CO2 usage"
• "Show me a histogram of building ages"
• "Compare energy consumption across classes"

💡 Learning
• "How does PCA classification work?"
• "Explain the TOPSIS scoring method"
• "What does energy intensity mean?"
```

## Configuration

### OpenAI API Setup (Optional)
For full AI functionality, configure your OpenAI API key:

1. Edit `.streamlit/secrets.toml`
2. Add your API key:
```toml
[openai]
api_key = "your-actual-openai-api-key"
```

### Demo Mode
If no API key is configured, the assistant runs in demo mode with:
- Pre-written helpful responses
- Basic data analysis capabilities
- Chart generation functionality
- Feature explanations

## Tips for Best Results

### 🎯 **Be Specific**
- Instead of "analyze my data", try "show me the correlation between energy and CO2"
- Specify chart types: "bar chart", "scatter plot", "histogram"

### 📊 **Request Visualizations**
- Ask for specific chart types to get visual insights
- The AI can generate interactive Plotly charts

### 🔄 **Follow Up Questions**
- Build on previous responses
- Ask for clarification or deeper analysis

### 📋 **Use Examples**
- Click on example questions in the sidebar for inspiration
- Modify examples to fit your specific needs

## Troubleshooting

### Common Issues

**Issue**: "Chatbot module not available"
**Solution**: Install required packages:
```bash
pip install openai langchain langchain-openai langchain-experimental tiktoken
```

**Issue**: Limited AI responses
**Solution**: Configure OpenAI API key in secrets.toml

**Issue**: No chart generation
**Solution**: Ensure plotly is installed and your question specifies chart type

## Privacy & Security

- Your data is processed locally in the dashboard
- If using OpenAI API, follow their data usage policies
- No data is stored permanently by the AI assistant
- All interactions are logged for security (admin feature)

## Support

For technical support or feature requests:
- Contact your system administrator
- Check the dashboard logs for error details
- Refer to the main application documentation

---

**Happy chatting with your AI Assistant! 🤖✨**
