"""
AI Chatbot Assistant for Building Analytics Dashboard
Provides intelligent assistance for dataset analysis, feature explanations, and chart generation
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, Optional, List
import json
import re
from datetime import datetime

# LangChain imports
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler

# Local imports
from utils.logger import log_security_event
from utils.auth_db import get_user_role


class BuildingChatbot:
    """AI Assistant for Building Analytics Dashboard"""
    
    def __init__(self):
        """Initialize the chatbot with OpenAI configuration"""
        self.setup_openai()
        self.initialize_session_state()
        
    def setup_openai(self):
        """Setup OpenAI configuration"""
        try:
            # Get API key from secrets or environment
            api_key = "demo-mode"  # Default fallback
            
            try:
                if hasattr(st, 'secrets') and "openai" in st.secrets and "api_key" in st.secrets["openai"]:
                    api_key = st.secrets["openai"]["api_key"]
                    if api_key and api_key.strip() and api_key != "demo-mode":
                        # Initialize LangChain models with real API key
                        self.llm = ChatOpenAI(
                            temperature=0.1,
                            model_name="gpt-3.5-turbo",
                            openai_api_key=api_key
                        )
                        self.api_available = True
                    else:
                        # No valid API key, use demo mode
                        self.llm = None
                        self.api_available = False
                else:
                    # No secrets found, use demo mode
                    self.llm = None
                    self.api_available = False
            except Exception as secrets_error:
                # Secrets file not found or invalid, use demo mode
                self.llm = None
                self.api_available = False
                
            self.pandas_agent = None
            
        except Exception as e:
            # Fallback to demo mode on any error
            self.llm = None
            self.pandas_agent = None
            self.api_available = False
            
    def initialize_session_state(self):
        """Initialize session state variables"""
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []
        if "current_dataset" not in st.session_state:
            st.session_state.current_dataset = None
        if "chat_mode" not in st.session_state:
            st.session_state.chat_mode = "general"
            
    def get_app_context(self) -> str:
        """Get context about the application features"""
        return """
        Building Analytics Dashboard Features:
        
        1. **Machine Learning Models**:
           - Mahalanobis Distance: Statistical distance-based classification
           - PCA: Principal Component Analysis for dimensionality reduction
           - Weighted Scoring: Customizable weighted criteria evaluation
           - Tree Classifier: Decision tree-based classification
           - Cosine Similarity: Vector-based similarity analysis
           - TOPSIS: Technique for Order Preference by Similarity to Ideal Solution
           
        2. **Data Management**:
           - Multi-city datasets (Auch, Ciry-le-Noble, Lille)
           - Custom dataset upload and validation
           - User-specific data ownership
           
        3. **Visualization**:
           - Interactive charts and maps
           - Model-specific visualizations
           - Export capabilities
           
        4. **User Roles**:
           - Admin: Full system access, user management
           - Analyst: Data analysis, reporting, advanced features
           - User: Basic analysis, dataset upload
        """
        
    def create_pandas_agent_for_data(self, df: pd.DataFrame):
        """Create a pandas agent for the current dataset"""
        if not self.api_available:
            return None
            
        try:
            self.pandas_agent = create_pandas_dataframe_agent(
                self.llm,
                df,
                verbose=True,
                return_intermediate_steps=True,
                handle_parsing_errors=True
            )
            return self.pandas_agent
        except Exception as e:
            st.error(f"Error creating pandas agent: {e}")
            return None
            
    def generate_chart_from_query(self, df: pd.DataFrame, query: str) -> Optional[go.Figure]:
        """Generate charts based on natural language queries"""
        query_lower = query.lower()
        
        # Chart type detection patterns
        chart_patterns = {
            'bar': ['bar', 'compare', 'top', 'worst', 'best', 'ranking'],
            'scatter': ['scatter', 'correlation', 'relationship', 'vs'],
            'line': ['trend', 'over time', 'timeline', 'progression'],
            'histogram': ['distribution', 'histogram', 'frequency'],
            'box': ['box plot', 'outliers', 'quartiles'],
            'pie': ['pie', 'proportion', 'percentage', 'share']
        }
        
        # Detect chart type
        chart_type = 'bar'  # default
        for ctype, patterns in chart_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                chart_type = ctype
                break
                
        # Extract column mentions
        columns = [col for col in df.columns if col.lower() in query_lower]
        
        try:
            if chart_type == 'bar' and len(columns) >= 1:
                # Top/worst buildings analysis
                if 'top' in query_lower or 'best' in query_lower:
                    sorted_df = df.nlargest(10, columns[0])
                elif 'worst' in query_lower or 'bottom' in query_lower:
                    sorted_df = df.nsmallest(10, columns[0])
                else:
                    sorted_df = df.head(10)
                    
                fig = px.bar(
                    sorted_df, 
                    x=sorted_df.index, 
                    y=columns[0],
                    title=f"Building Analysis: {columns[0]}"
                )
                return fig
                
            elif chart_type == 'scatter' and len(columns) >= 2:
                fig = px.scatter(
                    df, 
                    x=columns[0], 
                    y=columns[1],
                    title=f"Correlation: {columns[0]} vs {columns[1]}"
                )
                return fig
                
            elif chart_type == 'histogram' and len(columns) >= 1:
                fig = px.histogram(
                    df, 
                    x=columns[0],
                    title=f"Distribution of {columns[0]}"
                )
                return fig
                
        except Exception as e:
            st.error(f"Error generating chart: {e}")
            
        return None
        
    def get_dataset_summary(self, df: pd.DataFrame) -> str:
        """Generate a summary of the dataset"""
        summary = f"""
        Dataset Summary:
        - Shape: {df.shape[0]} rows, {df.shape[1]} columns
        - Columns: {', '.join(df.columns.tolist())}
        - Data Types: {df.dtypes.to_dict()}
        - Missing Values: {df.isnull().sum().to_dict()}
        
        Sample Data:
        {df.head(3).to_string()}
        """
        return summary
        
    def process_chat_message(self, user_input: str, df: Optional[pd.DataFrame] = None) -> str:
        """Process user chat message and generate response"""
        
        if not self.api_available:
            return self.get_demo_response(user_input, df)
            
        try:
            # Determine if this is a data query or general query
            data_keywords = ['dataset', 'data', 'buildings', 'show me', 'chart', 'plot', 'analysis']
            is_data_query = any(keyword in user_input.lower() for keyword in data_keywords)
            
            if is_data_query and df is not None:
                return self.handle_data_query(user_input, df)
            else:
                return self.handle_general_query(user_input)
                
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}"
            
    def handle_data_query(self, query: str, df: pd.DataFrame) -> str:
        """Handle queries about the dataset"""
        try:
            # Create pandas agent if not exists
            if self.pandas_agent is None:
                self.create_pandas_agent_for_data(df)
                
            if self.pandas_agent:
                # Use pandas agent for complex queries
                result = self.pandas_agent.run(query)
                return result
            else:
                # Fallback to manual analysis
                return self.manual_data_analysis(query, df)
                
        except Exception as e:
            return f"Error analyzing data: {str(e)}"
            
    def manual_data_analysis(self, query: str, df: pd.DataFrame) -> str:
        """Manual data analysis for queries"""
        query_lower = query.lower()
        
        if 'summary' in query_lower or 'describe' in query_lower:
            return self.get_dataset_summary(df)
            
        elif 'top' in query_lower or 'best' in query_lower:
            # Find the first numeric column
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                col = numeric_cols[0]
                top_buildings = df.nlargest(5, col)
                return f"Top 5 buildings by {col}:\n{top_buildings[[col]].to_string()}"
                
        elif 'worst' in query_lower or 'bottom' in query_lower:
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                col = numeric_cols[0]
                worst_buildings = df.nsmallest(5, col)
                return f"Bottom 5 buildings by {col}:\n{worst_buildings[[col]].to_string()}"
                
        return "I can help you analyze your data. Try asking about summaries, top buildings, or specific columns."
        
    def handle_general_query(self, query: str) -> str:
        """Handle general queries about the application"""
        try:
            messages = [
                SystemMessage(content=f"You are a helpful assistant for a Building Analytics Dashboard. {self.get_app_context()}"),
                HumanMessage(content=query)
            ]
            
            response = self.llm(messages)
            return response.content
            
        except Exception as e:
            return self.get_demo_response(query, None)
            
    def get_demo_response(self, query: str, df: Optional[pd.DataFrame] = None) -> str:
        """Provide demo responses when API is not available"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['pca', 'principal']):
            return """**PCA (Principal Component Analysis)** reduces the dimensionality of your building data while preserving the most important variations. 

**How it works:**
- Finds the main patterns in your building data
- Reduces complex multi-dimensional data to fewer dimensions
- Helps identify which building features are most important
- Great for visualizing building clusters and detecting patterns

**Use case:** Perfect when you have many building features and want to understand which ones matter most for classification."""
            
        elif any(word in query_lower for word in ['mahalanobis']):
            return """**Mahalanobis Distance** measures how unusual a building is compared to the typical building in your dataset.

**How it works:**
- Calculates statistical distance accounting for correlations between variables
- Identifies outlier buildings that don't fit normal patterns
- Considers how building features relate to each other
- Excellent for detecting unusual or problematic buildings

**Use case:** Ideal for finding buildings that need special attention or have unusual consumption patterns."""
            
        elif any(word in query_lower for word in ['topsis']):
            return """**TOPSIS (Technique for Order Preference by Similarity to Ideal Solution)** ranks buildings by comparing them to ideal and worst-case scenarios.

**How it works:**
- Defines an ideal building (best in all criteria)
- Defines a worst building (worst in all criteria)  
- Ranks buildings by how close they are to ideal vs worst
- Provides clear ranking from best to worst buildings

**Use case:** Perfect when you need to rank buildings for investment, renovation priority, or performance comparison."""
            
        elif any(word in query_lower for word in ['weighted']):
            return """**Weighted Scoring** allows you to assign custom importance to different building criteria based on your priorities.

**How it works:**
- You define importance weights (e.g., 40% energy efficiency, 30% cost, 30% location)
- Each building gets scored based on your custom weights
- Buildings that excel in your priority areas score higher
- Fully customizable to match your specific needs

**Use case:** Ideal when you have specific priorities and want results tailored to your criteria."""
            
        elif any(word in query_lower for word in ['cosine', 'similarity']):
            return """**Cosine Similarity** measures how similar buildings are based on their feature patterns.

**How it works:**
- Treats each building as a vector in multi-dimensional space
- Calculates the angle between building vectors
- Similar buildings have small angles (high cosine similarity)
- Different buildings have large angles (low cosine similarity)

**Use case:** Great for finding buildings with similar characteristics or grouping buildings by similarity."""
            
        elif any(word in query_lower for word in ['tree', 'decision']):
            return """**Tree Classifier** uses decision tree logic to classify buildings into performance categories.

**How it works:**
- Creates a series of yes/no questions about building features
- Follows decision paths to classify each building
- Easy to understand and interpret the classification logic
- Handles both numerical and categorical building data

**Use case:** Perfect when you need explainable classifications and want to understand the decision process."""
            
        elif any(word in query_lower for word in ['help', 'what can', 'capabilities']):
            return """**I can help you with:**

🏢 **Building Analysis Models:**
- PCA, TOPSIS, Mahalanobis Distance, Weighted Scoring
- Cosine Similarity, Tree Classification
- Model comparisons and recommendations

📊 **Data Analysis:**
- Dataset summaries and statistics
- Feature explanations and relationships
- Building performance insights

🎓 **Learning:**
- Machine learning concept explanations
- Building analytics best practices
- Feature interpretation guidance

**Try asking me:** "Explain PCA", "What's the best model for ranking buildings?", "Summarize my dataset", or "How does TOPSIS work?"
"""
            
        elif df is not None and any(word in query_lower for word in ['data', 'dataset', 'summary']):
            return self.get_dataset_summary(df)
            
        elif any(word in query_lower for word in ['best', 'recommend', 'which model']):
            return """**Model Recommendations by Use Case:**

🏆 **Ranking Buildings:** TOPSIS or Weighted Scoring
- Clear rankings from best to worst
- Customizable to your priorities

🔍 **Finding Outliers:** Mahalanobis Distance
- Identifies unusual buildings that need attention
- Great for quality control

📊 **Understanding Patterns:** PCA
- Reveals hidden patterns in your data
- Shows which features matter most

⚖️ **Custom Priorities:** Weighted Scoring
- Tailor results to your specific criteria
- Perfect for decision-making

🔗 **Finding Similar Buildings:** Cosine Similarity
- Groups buildings by similarity
- Good for benchmarking

**What's your main goal?** I can provide more specific guidance!"""
            
        else:
            return """**Welcome to the Building Analytics Assistant!** 🏢

I'm here to help you understand building performance analysis and machine learning models.

**Popular topics:**
- "Explain PCA" - Learn about dimensionality reduction
- "What's TOPSIS?" - Understand ranking methodology  
- "How does Mahalanobis work?" - Discover outlier detection
- "Which model should I use?" - Get personalized recommendations
- "Summarize my dataset" - Get data insights

**Ask me anything about building analytics, ML models, or your data!**"""
            
    def render_chat_interface(self, df: Optional[pd.DataFrame] = None):
        """Render the chat interface"""
        st.subheader("🤖 Building Analytics Assistant")
        
        if not self.api_available:
            st.info("💡 **Demo Mode**: The chatbot is running with limited functionality. To enable full AI capabilities:")
            with st.expander("How to enable full AI functionality"):
                st.markdown("""
                1. Get an OpenAI API key from [platform.openai.com](https://platform.openai.com/api-keys)
                2. Edit the `.streamlit/secrets.toml` file in the app directory
                3. Replace `api_key = "demo-mode"` with your actual API key
                4. Restart the application
                
                **Current capabilities in demo mode:**
                - Basic explanations of ML models (PCA, TOPSIS, Mahalanobis, etc.)
                - Dataset summaries and basic analysis
                - Feature explanations
                """)
        else:
            st.success("🚀 **Full AI Mode**: Advanced chatbot functionality enabled!")
            
        # Dataset status
        if df is not None:
            st.success(f"📊 Dataset loaded: {df.shape[0]} buildings, {df.shape[1]} attributes")
            st.session_state.current_dataset = df
        else:
            st.info("📋 No dataset loaded. Upload data for dataset-specific analysis.")
            
        # Chat mode selector
        col1, col2 = st.columns(2)
        with col1:
            chat_mode = st.selectbox(
                "Chat Mode",
                ["general", "data_analysis", "feature_explanation"],
                format_func=lambda x: {
                    "general": "🗣️ General Questions",
                    "data_analysis": "📊 Data Analysis", 
                    "feature_explanation": "🎓 Feature Explanation"
                }[x]
            )
            st.session_state.chat_mode = chat_mode
            
        with col2:
            if st.button("🗑️ Clear Chat"):
                st.session_state.chat_messages = []
                st.rerun()
        
        # Display chat history
        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Display chart if present
                if "chart" in message:
                    st.plotly_chart(message["chart"], use_container_width=True)
        
        # Chat input
        if prompt := st.chat_input("Ask me anything about the dashboard or your data..."):
            # Add user message
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Generate response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = self.process_chat_message(prompt, df)
                    st.markdown(response)
                    
                    # Try to generate chart if requested
                    if df is not None and any(word in prompt.lower() for word in ['chart', 'plot', 'show', 'visualize']):
                        chart = self.generate_chart_from_query(df, prompt)
                        if chart:
                            st.plotly_chart(chart, use_container_width=True)
                            st.session_state.chat_messages.append({
                                "role": "assistant", 
                                "content": response,
                                "chart": chart
                            })
                        else:
                            st.session_state.chat_messages.append({"role": "assistant", "content": response})
                    else:
                        st.session_state.chat_messages.append({"role": "assistant", "content": response})
            
            # Log chat interaction
            if "username" in st.session_state:
                log_security_event(
                    event_type="chatbot_interaction",
                    username=st.session_state.username,
                    details={"query": prompt, "mode": chat_mode},
                    success=True
                )


def render_chatbot_tab(current_df: Optional[pd.DataFrame] = None):
    """Render the chatbot as a tab in the main application"""
    chatbot = BuildingChatbot()
    chatbot.render_chat_interface(current_df)


# Example usage suggestions
def show_chat_examples():
    """Show example questions users can ask"""
    st.sidebar.markdown("### 💡 Example Questions")
    
    examples = [
        "What can you help me with?",
        "Which model should I use for ranking buildings?",
        "Explain PCA in simple terms",
        "How does TOPSIS work?",
        "What's Mahalanobis distance?",
        "Compare all the machine learning models",
        "Summarize my dataset",
        "Find buildings with unusual patterns",
        "Show me the top 10 most efficient buildings",
        "What are the key features in my data?"
    ]
    
    for i, example in enumerate(examples):
        if st.sidebar.button(f"💬 {example}", key=f"example_{i}"):
            # Add to chat
            st.session_state.chat_messages.append({"role": "user", "content": example})
            st.rerun()
