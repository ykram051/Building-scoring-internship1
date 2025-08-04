"""
AI Chatbot Assistant for Building Analytics Dashboard
Provides intelligent assistance for dataset analysis, feature explanations, and chart generation
Now powered by Google Gemini (FREE!)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, Optional, List
import json
import re
from datetime import datetime

# Google Gemini imports
try:
    import google.generativeai as genai
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_experimental.agents import create_pandas_dataframe_agent
    from langchain_core.messages import HumanMessage, SystemMessage
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Local imports
from utils.logger import log_security_event
from utils.auth_db import get_user_role


class BuildingChatbot:
    """AI Assistant for Building Analytics Dashboard - Powered by Google Gemini"""
    
    def __init__(self):
        """Initialize the chatbot with Google Gemini configuration"""
        self.setup_gemini()
        self.initialize_session_state()
        
    def setup_gemini(self):
        """Setup Google Gemini configuration"""
        try:
            if not GEMINI_AVAILABLE:
                self.llm = None
                self.pandas_agent = None
                self.api_available = False
                return
                
            # Get API key from secrets
            api_key = "demo-mode"  # Default fallback
            
            try:
                if hasattr(st, 'secrets') and "gemini" in st.secrets and "api_key" in st.secrets["gemini"]:
                    api_key = st.secrets["gemini"]["api_key"]
                    if api_key and api_key.strip() and api_key != "demo-mode":
                        # Configure Gemini
                        genai.configure(api_key=api_key)
                        
                        # Initialize LangChain with Gemini
                        self.llm = ChatGoogleGenerativeAI(
                            model="gemini-1.5-flash",
                            temperature=0.1,
                            google_api_key=api_key
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
        """Initialize session state variables for chatbot"""
        if "chatbot_messages" not in st.session_state:
            st.session_state.chatbot_messages = []
        if "chatbot_dataset" not in st.session_state:
            st.session_state.chatbot_dataset = None
        if "chatbot_mode" not in st.session_state:
            st.session_state.chatbot_mode = "general"
            
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
                verbose=False,  # Reduced verbosity
                return_intermediate_steps=False,  # Don't return intermediate steps
                handle_parsing_errors=True,
                allow_dangerous_code=False,  # More secure
                agent_type="openai-tools"  # More stable agent type
            )
            return self.pandas_agent
        except Exception as e:
            # If agent creation fails, disable it
            self.pandas_agent = None
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
        
    def transform_query(self, user_input: str) -> str:
        """Transform natural language queries to more processable forms"""
        query = user_input.lower().strip()
        
        # Common transformations for better detection
        transformations = {
            # Total building queries
            r'\b(how many|count|number of)\s+buildings\s+(are\s+)?(in\s+)?total\b': 'how many buildings total',
            r'\btotal\s+buildings?\b': 'total buildings',
            r'\bhow many\s+buildings?\s+are\s+there\b': 'how many buildings total',
            r'\bnumber\s+of\s+buildings?\b': 'how many buildings total',
            
            # Class-specific queries
            r'\bhow many\s+buildings?\s+(are\s+)?in\s+class\s+([a-g])\b': r'how many class \2',
            r'\bcount\s+of\s+class\s+([a-g])\s+buildings?\b': r'how many class \1',
            r'\bnumber\s+of\s+class\s+([a-g])\s+buildings?\b': r'how many class \1',
            
            # Dataset references
            r'\b(in\s+)?(the\s+)?auch\s+dataset\b': ' in auch',
            r'\b(in\s+)?(the\s+)?lille\s+dataset\b': ' in lille',
            r'\b(in\s+)?(the\s+)?ciry\s+dataset\b': ' in ciry',
        }
        
        import re
        transformed_query = query
        for pattern, replacement in transformations.items():
            transformed_query = re.sub(pattern, replacement, transformed_query)
        
        return transformed_query.strip()

    def analyze_query_intent(self, user_input: str) -> Dict[str, Any]:
        """Use Gemini AI to analyze user query intent and extract key information"""
        if not self.api_available:
            # Fallback to basic pattern matching if AI not available
            return self.basic_intent_analysis(user_input)
        
        try:
            intent_prompt = f"""
            Analyze this user query about building data and extract the intent and parameters:
            
            Query: "{user_input}"
            
            Please classify the query and extract information in this JSON format:
            {{
                "intent": "total_count|class_count|summary|comparison|chart|general|model_results|upload_help|dataset_guidance",
                "subject": "buildings|data|models|upload|dataset",
                "class_mentioned": "A|B|C|D|E|F|G|null",
                "dataset_mentioned": "auch|lille|ciry|null",
                "count_type": "total|specific_class|all_classes|null",
                "action": "count|explain|compare|show|analyze|upload|guide",
                "model_mentioned": "mahalanobis|pca|topsis|weighted|cosine|tree|null",
                "classification_context": "energy_label|model_result|null",
                "upload_context": "how_to|permissions|requirements|null",
                "spelling_corrected": "corrected query if needed"
            }}
            
            Intent definitions:
            - total_count: User wants total number of buildings
            - class_count: User wants count of specific class or all classes
            - model_results: User wants results from a specific ML model classification
            - summary: User wants dataset overview/summary
            - comparison: User wants to compare models or data
            - chart: User wants visualization
            - upload_help: User wants help with uploading datasets
            - dataset_guidance: User wants guidance on dataset requirements
            - general: General questions about models/features
            
            Examples:
            "how many buildings in total" -> {{"intent": "total_count", "subject": "buildings", "count_type": "total"}}
            "how many class A buildings" -> {{"intent": "class_count", "class_mentioned": "A", "count_type": "specific_class", "classification_context": "energy_label"}}
            "how many in class A mahalanobis" -> {{"intent": "model_results", "class_mentioned": "A", "model_mentioned": "mahalanobis", "count_type": "specific_class"}}
            "class A in classification mahalanobis" -> {{"intent": "model_results", "class_mentioned": "A", "model_mentioned": "mahalanobis"}}
            "how to upload dataset" -> {{"intent": "upload_help", "subject": "dataset", "action": "upload", "upload_context": "how_to"}}
            "can I upload my data" -> {{"intent": "upload_help", "subject": "data", "action": "upload", "upload_context": "permissions"}}
            "dataset requirements" -> {{"intent": "dataset_guidance", "subject": "dataset", "upload_context": "requirements"}}
            "sumary of data" -> {{"intent": "summary", "subject": "data", "spelling_corrected": "summary of data"}}
            """
            
            messages = [
                SystemMessage(content="You are an expert at understanding user intent for building analytics queries. Always respond with valid JSON."),
                HumanMessage(content=intent_prompt)
            ]
            
            response = self.llm(messages)
            
            # Parse the JSON response
            import json
            try:
                intent_data = json.loads(response.content.strip())
                return intent_data
            except json.JSONDecodeError:
                # If JSON parsing fails, extract key info manually
                content = response.content.lower()
                return {
                    "intent": "total_count" if "total" in content else "general",
                    "subject": "buildings" if "building" in content else "data",
                    "class_mentioned": None,
                    "dataset_mentioned": None,
                    "count_type": "total" if "total" in content else None,
                    "action": "count" if "count" in content or "how many" in content else "explain"
                }
                
        except Exception as e:
            # Fallback to basic analysis
            return self.basic_intent_analysis(user_input)
    
    def basic_intent_analysis(self, user_input: str) -> Dict[str, Any]:
        """Basic pattern matching fallback when AI is not available"""
        query_lower = user_input.lower()
        
        # Extract class mentioned
        class_mentioned = None
        for char in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
            if f'class {char.lower()}' in query_lower or char.lower() in query_lower.split():
                class_mentioned = char
                break
        
        # Extract model mentioned
        model_mentioned = None
        models = ['mahalanobis', 'pca', 'topsis', 'weighted', 'cosine', 'tree']
        for model in models:
            if model in query_lower:
                model_mentioned = model
                break
        
        # Extract dataset
        dataset_mentioned = None
        if 'auch' in query_lower:
            dataset_mentioned = 'auch'
        elif 'lille' in query_lower:
            dataset_mentioned = 'lille'
        elif 'ciry' in query_lower:
            dataset_mentioned = 'ciry'
        
        # Determine intent
        upload_keywords = ['upload', 'import', 'add data', 'custom data', 'my data', 'own data']
        upload_context = None
        
        # Check for upload-related queries
        if any(keyword in query_lower for keyword in upload_keywords):
            if any(word in query_lower for word in ['how', 'how to', 'can i', 'able to']):
                upload_context = 'how_to'
            elif any(word in query_lower for word in ['permission', 'access', 'allowed', 'privilege']):
                upload_context = 'permissions'
            elif any(word in query_lower for word in ['format', 'requirement', 'structure']):
                upload_context = 'requirements'
        
        # Enhanced model results detection
        model_class_patterns = [
            # Direct patterns like "class B mahalanobis", "class B with mahalanobis", "mahalanobis class B"
            any(f'class {char.lower()}' in query_lower for char in ['A', 'B', 'C', 'D', 'E', 'F', 'G']) and model_mentioned,
            # Patterns like "how many buildings are in class B with mahalanobis"
            any(word in query_lower for word in ['how many', 'count']) and model_mentioned and class_mentioned,
            # Patterns like "buildings in class B mahalanobis classification"
            'classification' in query_lower and model_mentioned and class_mentioned
        ]
        
        if any(keyword in query_lower for keyword in upload_keywords):
            intent = "upload_help"
            count_type = None
        elif any(word in query_lower for word in ['requirement', 'format', 'structure']) and any(word in query_lower for word in ['dataset', 'data']):
            intent = "dataset_guidance"
            count_type = None
        elif any(model_class_patterns) or (model_mentioned and class_mentioned):
            intent = "model_results"
            count_type = "specific_class"
        elif any(word in query_lower for word in ['total', 'how many buildings', 'number of buildings']) and not class_mentioned:
            intent = "total_count"
            count_type = "total"
        elif class_mentioned and any(word in query_lower for word in ['how many', 'count']):
            intent = "class_count"
            count_type = "specific_class"
        elif any(word in query_lower for word in ['summary', 'describe', 'overview']):
            intent = "summary"
            count_type = None
        else:
            intent = "general"
            count_type = None
        
        return {
            "intent": intent,
            "subject": "dataset" if "upload" in intent or "dataset_guidance" in intent else ("buildings" if "building" in query_lower else "data"),
            "class_mentioned": class_mentioned,
            "model_mentioned": model_mentioned,
            "dataset_mentioned": dataset_mentioned,
            "count_type": count_type,
            "classification_context": "model_result" if model_mentioned else "energy_label",
            "action": "upload" if "upload" in intent else ("count" if "count" in query_lower or "how many" in query_lower else "explain"),
            "upload_context": upload_context
        }

    def process_chat_message(self, user_input: str, df: Optional[pd.DataFrame] = None) -> str:
        """Process user chat message using AI-powered intent analysis"""
        
        if not self.api_available:
            return self.get_demo_response(user_input, df)
            
        try:
            # Use AI to analyze the query intent
            intent_data = self.analyze_query_intent(user_input)
            
            # Use corrected query if available
            processed_query = intent_data.get('spelling_corrected', user_input)
            
            # Route based on intent
            if df is not None and intent_data['intent'] in ['total_count', 'class_count', 'summary', 'model_results']:
                return self.handle_data_query_with_intent(processed_query, df, intent_data)
            elif intent_data['intent'] in ['upload_help', 'dataset_guidance']:
                return self.handle_upload_guidance(processed_query, intent_data)
            else:
                return self.handle_general_query(processed_query)
                
        except Exception as e:
            # Fallback to original method
            return self.handle_general_query(user_input)
            
    def handle_data_query_with_intent(self, query: str, df: pd.DataFrame, intent_data: Dict[str, Any]) -> str:
        """Handle data queries using AI-analyzed intent"""
        try:
            intent = intent_data.get('intent')
            class_mentioned = intent_data.get('class_mentioned')
            model_mentioned = intent_data.get('model_mentioned')
            dataset_name = intent_data.get('dataset_mentioned', 'current')
            classification_context = intent_data.get('classification_context', 'energy_label')
            
            if intent == 'total_count':
                dataset_display = f"{dataset_name.title()} dataset" if dataset_name != 'current' else "Current dataset"
                return f"""📊 **Total Buildings Count:**

**Total Buildings**: {len(df):,}
**Dataset Shape**: {df.shape[0]:,} rows × {df.shape[1]} columns
**Dataset**: {dataset_display}"""
            
            elif intent == 'model_results':
                if model_mentioned and class_mentioned:
                    # First, try to find actual classification results in the dataset
                    potential_columns = []
                    
                    # Look for columns that might contain model results
                    for col in df.columns:
                        col_lower = col.lower()
                        if any([
                            model_mentioned in col_lower,
                            'classification' in col_lower and model_mentioned in col_lower,
                            f'{model_mentioned}_class' in col_lower,
                            f'{model_mentioned}_result' in col_lower,
                            col_lower.startswith(model_mentioned),
                            col_lower.endswith(model_mentioned)
                        ]):
                            potential_columns.append(col)
                    
                    # If we found potential columns, try to get the count
                    if potential_columns:
                        for col in potential_columns:
                            try:
                                if class_mentioned in df[col].values:
                                    count = len(df[df[col] == class_mentioned])
                                    total_count = len(df)
                                    percentage = (count / total_count * 100) if total_count > 0 else 0
                                    
                                    # Get distribution of all classes in this column
                                    class_distribution = df[col].value_counts().sort_index()
                                    distribution_text = "\n".join([f"**{cls}**: {cnt} buildings ({cnt/total_count*100:.1f}%)" 
                                                                 for cls, cnt in class_distribution.items()])
                                    
                                    return f"""📊 **{model_mentioned.title()} Classification Results:**

**Class {class_mentioned}**: {count} buildings ({percentage:.1f}%)

**Complete {model_mentioned.title()} Distribution:**
{distribution_text}

**Total Buildings**: {total_count}
**Classification Column**: {col}
**Model Used**: {model_mentioned.title()}"""
                            except Exception:
                                continue
                    
                    # If no specific column found, look for any classification columns
                    class_columns = [col for col in df.columns if any(term in col.lower() for term in ['class', 'grade', 'category', 'label'])]
                    
                    if class_columns:
                        # Try to find the class in any classification column
                        for col in class_columns:
                            try:
                                if class_mentioned in df[col].values:
                                    count = len(df[df[col] == class_mentioned])
                                    total_count = len(df)
                                    percentage = (count / total_count * 100) if total_count > 0 else 0
                                    
                                    # Check if this might be the model result we're looking for
                                    if model_mentioned.lower() in col.lower():
                                        class_distribution = df[col].value_counts().sort_index()
                                        distribution_text = "\n".join([f"**{cls}**: {cnt} buildings ({cnt/total_count*100:.1f}%)" 
                                                                     for cls, cnt in class_distribution.items()])
                                        
                                        return f"""📊 **{model_mentioned.title()} Classification Results Found:**

**Class {class_mentioned}**: {count} buildings ({percentage:.1f}%)

**Complete Distribution:**
{distribution_text}

**Total Buildings**: {total_count}
**Classification Column**: {col}"""
                            except Exception:
                                continue
                    
                    # Fallback: provide guidance on how to get the results
                    available_columns = ", ".join(df.columns.tolist()[:10])  # Show first 10 columns
                    if len(df.columns) > 10:
                        available_columns += f"... (and {len(df.columns) - 10} more)"
                    
                    return f"""🔍 **{model_mentioned.title()} Classification Results:**

I'm looking for **Class {class_mentioned}** from the **{model_mentioned.title()}** model, but I couldn't find a specific {model_mentioned} classification column in your current dataset.

**To get the results you need:**

1. **Run the {model_mentioned.title()} Model**: 
   - Go to the **{model_mentioned.title()}** tab in the dashboard
   - Run the model on your current dataset
   - This will generate classification results

2. **Check Existing Classifications**:
   - Your dataset has these columns: {available_columns}
   - If you see a column with {model_mentioned} results, let me know its exact name

3. **Alternative**: If you've already run the model, the results might be in a column with a different name. Try asking: "How many class {class_mentioned} buildings in [column_name]?"

**Current Dataset**: {len(df)} buildings loaded"""
                else:
                    return f"I need both a class (A, B, C, etc.) and a model name (Mahalanobis, PCA, TOPSIS, etc.) to provide model classification results."
            
            elif intent == 'class_count':
                # Look for class columns
                class_columns = [col for col in df.columns if any(term in col.lower() for term in ['class', 'grade', 'category', 'label'])]
                
                if class_columns:
                    class_col = class_columns[0]
                    
                    if class_mentioned:
                        # Specific class count
                        count = len(df[df[class_col] == class_mentioned])
                        
                        # Also show full distribution for context
                        class_counts = df[class_col].value_counts().sort_index()
                        distribution = "\n".join([f"**{cls}**: {count} buildings" for cls, count in class_counts.items()])
                        
                        return f"""📊 **Building Classification Results:**

**Class {class_mentioned}**: {count} buildings

**Complete Distribution:**
{distribution}

**Total Buildings**: {len(df)}
**Classification Column**: {class_col}"""
                    else:
                        # All class counts
                        class_counts = df[class_col].value_counts().sort_index()
                        distribution = "\n".join([f"**{cls}**: {count} buildings" for cls, count in class_counts.items()])
                        
                        return f"""📊 **Building Classification Distribution:**

{distribution}

**Total Buildings**: {len(df)}
**Classification Column**: {class_col}"""
                else:
                    return "I couldn't find any classification columns in your dataset. Available columns: " + ", ".join(df.columns.tolist())
            
            elif intent == 'summary':
                return self.get_dataset_summary(df)
            
            else:
                # For other intents, use the original manual analysis
                return self.manual_data_analysis(query, df)
                
        except Exception as e:
            # Fallback to manual analysis
            return self.manual_data_analysis(query, df)
            
    def handle_data_query_original(self, query: str, df: pd.DataFrame) -> str:
        """Handle queries about the dataset"""
        try:
            # For classification/counting queries (FIRST - more specific), always use manual analysis as it's more accurate
            if any(word in query.lower() for word in ['class', 'classification', 'grade', 'label', 'category']) and any(word in query.lower() for word in ['how many', 'count', 'number of', 'distribution']):
                return self.manual_data_analysis(query, df)
            
            # For total building count queries (SECOND - more general), use manual analysis
            # Only match if it's explicitly asking for totals WITHOUT class references
            elif (('how many' in query.lower() and 'buildings' in query.lower()) or 
                  'total buildings' in query.lower() or 
                  'number of buildings' in query.lower() or 
                  'buildings in total' in query.lower() or 
                  ('total' in query.lower() and 'buildings' in query.lower())) and not any(word in query.lower() for word in ['class', 'classification', 'grade', 'label', 'category']):
                return self.manual_data_analysis(query, df)
            
            # For summary queries, use manual analysis
            if any(word in query.lower() for word in ['summary', 'describe', 'overview', 'info']):
                return self.manual_data_analysis(query, df)
                
            # Create pandas agent if not exists for other queries
            if self.pandas_agent is None:
                self.create_pandas_agent_for_data(df)
                
            if self.pandas_agent:
                try:
                    # Use pandas agent for complex queries
                    result = self.pandas_agent.invoke({"input": query})
                    # Handle different return formats
                    if isinstance(result, dict):
                        if 'output' in result:
                            return result['output']
                        elif 'result' in result:
                            return result['result']
                        else:
                            return str(result)
                    else:
                        return str(result)
                except Exception as agent_error:
                    # If pandas agent fails, fall back to manual analysis
                    return self.manual_data_analysis(query, df)
            else:
                # Fallback to manual analysis
                return self.manual_data_analysis(query, df)
                
        except Exception as e:
            # If all else fails, try manual analysis
            return self.manual_data_analysis(query, df)
            
    def manual_data_analysis(self, query: str, df: pd.DataFrame) -> str:
        """Manual data analysis for queries"""
        query_lower = query.lower()
        
        # Handle summary queries
        if 'summary' in query_lower or 'describe' in query_lower:
            return self.get_dataset_summary(df)
        
        # Handle total building count queries - improved pattern matching
        total_patterns = [
            'how many' in query_lower and 'buildings' in query_lower,
            'total buildings' in query_lower,
            'number of buildings' in query_lower,
            'buildings in total' in query_lower,
            'total' in query_lower and 'buildings' in query_lower
        ]
        has_class_words = any(word in query_lower for word in ['class', 'grade', 'category', 'label'])
        
        if any(total_patterns) and not has_class_words:
            dataset_name = "Auch dataset" if 'auch' in query_lower else "Current dataset"
            return f"""📊 **Total Buildings Count:**

**Total Buildings**: {len(df):,}
**Dataset Shape**: {df.shape[0]:,} rows × {df.shape[1]} columns
**Dataset**: {dataset_name}"""
        
        # Handle class/grade counting queries
        elif any(word in query_lower for word in ['how many', 'count', 'number of']) and any(word in query_lower for word in ['class', 'grade', 'category']):
            # Look for class columns
            class_columns = [col for col in df.columns if any(term in col.lower() for term in ['class', 'grade', 'category', 'label'])]
            
            if class_columns:
                class_col = class_columns[0]  # Use the first class column found
                
                # Extract the specific class mentioned (A, B, C, etc.) - enhanced detection
                classes_mentioned = []
                query_words = query_lower.split()
                
                for char in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
                    char_lower = char.lower()
                    
                    # Check if the class letter appears in the query
                    if any([
                        f'class {char_lower}' in query_lower,
                        f'grade {char_lower}' in query_lower,
                        f'category {char_lower}' in query_lower,
                        f'in {char_lower}' in query_lower,
                        char_lower in query_words,  # Check if it's a separate word
                        f'{char_lower}.' in query_lower,
                        f'{char_lower}?' in query_lower,
                        f'{char_lower}!' in query_lower
                    ]):
                        classes_mentioned.append(char)
                
                if classes_mentioned:
                    results = []
                    for class_name in classes_mentioned:
                        count = len(df[df[class_col] == class_name])
                        results.append(f"**Class {class_name}**: {count} buildings")
                    
                    # Also show the full distribution
                    class_counts = df[class_col].value_counts().sort_index()
                    distribution = "\n".join([f"**{cls}**: {count} buildings" for cls, count in class_counts.items()])
                    
                    return f"""📊 **Building Classification Results:**

{chr(10).join(results)}

**Complete Distribution:**
{distribution}

**Total Buildings**: {len(df)}
**Classification Column**: {class_col}"""
                else:
                    # Show all class counts
                    class_counts = df[class_col].value_counts().sort_index()
                    distribution = "\n".join([f"**{cls}**: {count} buildings" for cls, count in class_counts.items()])
                    
                    return f"""📊 **Building Classification Distribution:**

{distribution}

**Total Buildings**: {len(df)}
**Classification Column**: {class_col}"""
            else:
                return "I couldn't find any classification columns in your dataset. Available columns: " + ", ".join(df.columns.tolist())
            
        elif 'top' in query_lower or 'best' in query_lower:
            # Find the first numeric column
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                col = numeric_cols[0]
                top_buildings = df.nlargest(5, col)
                return f"**Top 5 buildings by {col}:**\n{top_buildings[[col]].to_string()}"
                
        elif 'worst' in query_lower or 'bottom' in query_lower:
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                col = numeric_cols[0]
                worst_buildings = df.nsmallest(5, col)
                return f"**Bottom 5 buildings by {col}:**\n{worst_buildings[[col]].to_string()}"
                
        return "I can help you analyze your data. Try asking about:\n- Building classifications (how many class A buildings?)\n- Dataset summaries\n- Top/worst performing buildings\n- Specific columns"
        
    def handle_upload_guidance(self, query: str, intent_data: Dict[str, Any]) -> str:
        """Handle queries about uploading datasets and user permissions"""
        try:
            # Import auth functions to check user permissions
            from utils.auth_db import get_user_role
            from utils.secure_auth import secure_auth
            
            username = st.session_state.get('username', 'Unknown')
            user_role = st.session_state.get('user_role', 'user')
            upload_context = intent_data.get('upload_context', 'general')
            
            # Check if user has upload permission
            has_upload_permission = secure_auth.check_permission('upload_datasets')
            
            if upload_context == 'permissions':
                if has_upload_permission:
                    return f"""✅ **Upload Permissions for {username}**

**Role**: {user_role.title()}
**Upload Access**: ✅ **Allowed**

You have permission to upload custom datasets! Your role allows you to:
- 📤 Upload CSV files containing building data
- 💾 Save datasets with custom names  
- 📊 Analyze your uploaded data with all available models
- 📈 Generate reports and visualizations

**Next Step**: Look for "Upload Custom Dataset" in the dataset selection dropdown."""
                else:
                    return f"""❌ **Upload Permissions for {username}**

**Role**: {user_role.title()}
**Upload Access**: ❌ **Restricted**

Your current role doesn't include dataset upload privileges. Contact your administrator to request analyst or admin permissions for uploading custom datasets.

**Current capabilities**: You can still analyze existing datasets (Auch, Lille, Ciry-le-Noble)."""
                    
            elif upload_context == 'requirements':
                return """📋 **Dataset Upload Requirements**

**File Format**: CSV (.csv files only)
**Size Limit**: 50MB maximum
**Required Columns**: Your dataset should include building data with:
- Geographic coordinates (latitude/longitude)
- Building attributes (area, energy consumption, etc.)
- Any classification columns you want to analyze

**Optional Columns**:
- City name
- Year
- Building ID or address
- Energy efficiency ratings

**Data Quality Tips**:
- Remove empty rows and invalid data
- Use consistent units and formats
- Include column headers
- Ensure numeric data is properly formatted

**Supported Analysis**: Once uploaded, you can use all ML models (PCA, TOPSIS, Mahalanobis, etc.) on your data."""

            elif upload_context == 'how_to':
                if has_upload_permission:
                    return """📤 **How to Upload Your Dataset**

**Step 1**: Navigate to Dataset Selection
- In the main dashboard, find the dataset dropdown
- Select "Upload Custom Dataset" option

**Step 2**: Upload Your File
- Click "Upload CSV file" button
- Select your building data file (.csv format)
- File will be validated automatically

**Step 3**: Name Your Dataset
- Provide a descriptive name for your dataset
- This name will be used for future access

**Step 4**: Processing
- The system will automatically process your data
- Add any missing classifications
- Validate data quality

**Step 5**: Analysis
- Once processed, you can immediately start analyzing
- All ML models will be available
- Your data is saved for future sessions

**Security**: Your uploaded datasets are private and linked to your account."""
                else:
                    return f"""❌ **Upload Not Available**

Your current role ({user_role}) doesn't have upload permissions. Contact your administrator to request analyst or admin access.

**What you can do now**:
- Analyze existing datasets (Auch, Lille, Ciry-le-Noble)
- Use all machine learning models on available data
- Generate reports and visualizations"""
            
            else:
                # General upload guidance
                if has_upload_permission:
                    return """📤 **Custom Dataset Upload**

**You can upload your own building datasets!**

**Quick Start**:
1. Select "Upload Custom Dataset" from the dataset dropdown
2. Upload your CSV file (max 50MB)
3. Name your dataset
4. Start analyzing immediately

**What You Get**:
- Full access to all ML models (PCA, TOPSIS, Mahalanobis, etc.)
- Private dataset linked to your account
- Export and reporting capabilities
- Data validation and preprocessing

**Need help?** Ask me:
- "What are the upload requirements?"
- "How do I upload my dataset?"
- "Do I have upload permissions?"

**File format**: CSV files with building data including coordinates and attributes."""
                else:
                    return """ℹ️ **Dataset Upload Information**

Dataset upload is available for users with analyst or admin roles. Your current role doesn't include upload permissions.

**Available Options**:
- Analyze existing city datasets (Auch, Lille, Ciry-le-Noble)
- Use all machine learning models
- Generate reports and comparisons

**To get upload access**: Contact your administrator to upgrade your role to analyst or admin."""
                    
        except Exception as e:
            # Fallback response if auth checking fails
            return """📤 **Dataset Upload Feature**

The dashboard supports uploading custom building datasets in CSV format.

**General Information**:
- Upload CSV files with building data
- Maximum file size: 50MB
- Automatic data validation and preprocessing
- Support for all ML models and analysis tools

**Requirements**:
- CSV format with proper headers
- Building coordinates (latitude/longitude recommended)
- Building attributes for analysis

**Access**: Upload permissions depend on your user role. Contact your administrator if you need upload access.

For detailed guidance, please specify what you'd like to know:
- Upload requirements
- Step-by-step process
- Permission details"""
        
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
        # Use basic intent analysis even in demo mode
        intent_data = self.basic_intent_analysis(query)
        
        # Handle data-specific queries first if we have a dataset
        if df is not None:
            if intent_data['intent'] == 'total_count':
                dataset_name = intent_data.get('dataset_mentioned', 'current')
                dataset_display = f"{dataset_name.title()} dataset" if dataset_name != 'current' else "Current dataset"
                return f"""📊 **Total Buildings Count:**

**Total Buildings**: {len(df):,}
**Dataset Shape**: {df.shape[0]:,} rows × {df.shape[1]} columns
**Dataset**: {dataset_display}"""
            
            elif intent_data['intent'] == 'model_results':
                model_mentioned = intent_data.get('model_mentioned')
                class_mentioned = intent_data.get('class_mentioned')
                if model_mentioned and class_mentioned:
                    # Try to find actual classification results in the dataset
                    potential_columns = []
                    
                    # Look for columns that might contain model results
                    for col in df.columns:
                        col_lower = col.lower()
                        if any([
                            model_mentioned in col_lower,
                            'classification' in col_lower and model_mentioned in col_lower,
                            f'{model_mentioned}_class' in col_lower,
                            f'{model_mentioned}_result' in col_lower,
                            col_lower.startswith(model_mentioned),
                            col_lower.endswith(model_mentioned)
                        ]):
                            potential_columns.append(col)
                    
                    # If we found potential columns, try to get the count
                    if potential_columns:
                        for col in potential_columns:
                            try:
                                if class_mentioned in df[col].values:
                                    count = len(df[df[col] == class_mentioned])
                                    total_count = len(df)
                                    percentage = (count / total_count * 100) if total_count > 0 else 0
                                    
                                    # Get distribution of all classes in this column
                                    class_distribution = df[col].value_counts().sort_index()
                                    distribution_text = "\n".join([f"**{cls}**: {cnt} buildings ({cnt/total_count*100:.1f}%)" 
                                                                 for cls, cnt in class_distribution.items()])
                                    
                                    return f"""📊 **{model_mentioned.title()} Classification Results:**

**Class {class_mentioned}**: {count} buildings ({percentage:.1f}%)

**Complete {model_mentioned.title()} Distribution:**
{distribution_text}

**Total Buildings**: {total_count}
**Classification Column**: {col}
**Model Used**: {model_mentioned.title()}"""
                            except Exception:
                                continue
                    
                    # If no specific column found, look for any classification columns that might contain the class
                    class_columns = [col for col in df.columns if any(term in col.lower() for term in ['class', 'grade', 'category', 'label'])]
                    
                    if class_columns:
                        # Try to find the class in any classification column
                        for col in class_columns:
                            try:
                                if class_mentioned in df[col].values:
                                    count = len(df[df[col] == class_mentioned])
                                    total_count = len(df)
                                    percentage = (count / total_count * 100) if total_count > 0 else 0
                                    
                                    class_distribution = df[col].value_counts().sort_index()
                                    distribution_text = "\n".join([f"**{cls}**: {cnt} buildings ({cnt/total_count*100:.1f}%)" 
                                                                 for cls, cnt in class_distribution.items()])
                                    
                                    # Note: this might not be the specific model result, but it's a classification with the requested class
                                    return f"""📊 **Classification Results Found (Class {class_mentioned}):**

**Class {class_mentioned}**: {count} buildings ({percentage:.1f}%)

**Complete Distribution in {col}:**
{distribution_text}

**Total Buildings**: {total_count}
**Note**: Found Class {class_mentioned} in column "{col}". If this isn't the {model_mentioned.title()} result you're looking for, please run the {model_mentioned.title()} model first or specify the exact column name."""
                            except Exception:
                                continue
                    
                    # Fallback response
                    return f"""🔍 **{model_mentioned.title()} Classification Search:**

I'm looking for **Class {class_mentioned}** from **{model_mentioned.title()}** classification, but couldn't find specific results in your current dataset.

**Available columns**: {', '.join(df.columns.tolist()[:8])}{'...' if len(df.columns) > 8 else ''}

**To get the results:**
1. Run the {model_mentioned.title()} model on your dataset
2. Or tell me the exact column name that contains the {model_mentioned.title()} results
3. Or ask about available classifications: "what classes are available?"

**Current dataset**: {len(df)} buildings loaded"""
                
            elif intent_data['intent'] == 'class_count':
                class_mentioned = intent_data.get('class_mentioned')
                # Look for class columns
                class_columns = [col for col in df.columns if any(term in col.lower() for term in ['class', 'grade', 'category', 'label'])]
                
                if class_columns:
                    class_col = class_columns[0]
                    
                    if class_mentioned:
                        # Specific class count
                        count = len(df[df[class_col] == class_mentioned])
                        
                        # Also show full distribution for context
                        class_counts = df[class_col].value_counts().sort_index()
                        distribution = "\n".join([f"**{cls}**: {count} buildings" for cls, count in class_counts.items()])
                        
                        return f"""📊 **Building Classification Results:**

**Class {class_mentioned}**: {count} buildings

**Complete Distribution:**
{distribution}

**Total Buildings**: {len(df)}
**Classification Column**: {class_col}"""
                    else:
                        # All class counts
                        class_counts = df[class_col].value_counts().sort_index()
                        distribution = "\n".join([f"**{cls}**: {count} buildings" for cls, count in class_counts.items()])
                        
                        return f"""📊 **Building Classification Distribution:**

{distribution}

**Total Buildings**: {len(df)}
**Classification Column**: {class_col}"""
                        
            elif intent_data['intent'] == 'summary' or any(word in query.lower() for word in ['data', 'dataset', 'summary']):
                return self.get_dataset_summary(df)
        
        # Handle upload queries even without dataset
        if intent_data['intent'] in ['upload_help', 'dataset_guidance']:
            return self.handle_upload_guidance(query, intent_data)
        
        query_lower = query.lower()
        
        # General ML model explanations
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

📤 **Dataset Upload:**
- Upload guidance and requirements
- Permission checking
- Step-by-step instructions

🎓 **Learning:**
- Machine learning concept explanations
- Building analytics best practices
- Feature interpretation guidance

**Try asking me:** "Explain PCA", "What's the best model for ranking buildings?", "How do I upload my dataset?", "Summarize my dataset", or "Do I have upload permissions?"
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
- "How do I upload my dataset?" - Learn about custom data upload
- "Explain PCA" - Learn about dimensionality reduction
- "What's TOPSIS?" - Understand ranking methodology  
- "How does Mahalanobis work?" - Discover outlier detection
- "Which model should I use?" - Get personalized recommendations
- "Summarize my dataset" - Get data insights

**Ask me anything about building analytics, ML models, data upload, or your data!**"""
            
    def render_chat_interface(self, df: Optional[pd.DataFrame] = None):
        """Render the chat interface"""
        # Set a flag to indicate we're in the chatbot
        st.session_state._chatbot_active = True
        
        st.subheader("🤖 Building Analytics Assistant")
        st.caption("Powered by Google Gemini 🚀")
        
        if not GEMINI_AVAILABLE:
            st.error("❌ **Missing Dependencies**: Please install Google Gemini dependencies:")
            st.code("pip install google-generativeai langchain-google-genai", language="bash")
            st.info("After installation, restart the application.")
            return
        
        if not self.api_available:
            st.info("💡 **Demo Mode**: The chatbot is running with limited functionality. To enable full AI capabilities:")
            with st.expander("How to enable FREE Google Gemini AI functionality"):
                st.markdown("""
                1. **Get a FREE Google Gemini API key** from [Google AI Studio](https://aistudio.google.com/app/apikey)
                   - No credit card required!
                   - Generous free tier with high rate limits
                   
                2. **Configure the API key**:
                   - Edit the `.streamlit/secrets.toml` file in the app directory
                   - Replace `api_key = "demo-mode"` with your actual API key:
                   ```toml
                   [gemini]
                   api_key = "your-gemini-api-key-here"
                   ```
                   
                3. **Restart the application**
                
                **Current capabilities in demo mode:**
                - Basic explanations of ML models (PCA, TOPSIS, Mahalanobis, etc.)
                - Dataset summaries and basic analysis
                - Feature explanations
                """)
        else:
            st.success("🚀 **Full AI Mode**: Advanced chatbot functionality enabled with Google Gemini!")
            
        # Dataset status
        if df is not None:
            st.success(f"📊 Dataset loaded: {df.shape[0]} buildings, {df.shape[1]} attributes")
            st.session_state.chatbot_dataset = df
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
            st.session_state.chatbot_mode = chat_mode
            
        with col2:
            if st.button("🗑️ Clear Chat"):
                st.session_state.chatbot_messages = []
                # Don't use st.rerun() to avoid tab switching
        
        # Display chat history
        for message in st.session_state.chatbot_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Display chart if present
                if "chart" in message:
                    st.plotly_chart(message["chart"], use_container_width=True)
        
        # Check for pending message from example buttons
        if st.session_state.get('pending_chat_message'):
            prompt = st.session_state.pending_chat_message
            del st.session_state['pending_chat_message']  # Clear the pending message
            
            # Process the example question
            st.session_state.chatbot_messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = self.process_chat_message(prompt, df)
                    st.markdown(response)
                    st.session_state.chatbot_messages.append({"role": "assistant", "content": response})
                    
            # Log the interaction
            if "username" in st.session_state:
                log_security_event(
                    event_type="chatbot_interaction",
                    username=st.session_state.username,
                    details={"query": prompt, "mode": st.session_state.get('chatbot_mode', 'general')},
                    success=True
                )
        
        # Chat input
        if prompt := st.chat_input("Ask me anything about the dashboard or your data...", key="ai_assistant_chat_input"):
            # Add user message
            st.session_state.chatbot_messages.append({"role": "user", "content": prompt})
            
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
                            st.session_state.chatbot_messages.append({
                                "role": "assistant", 
                                "content": response,
                                "chart": chart
                            })
                        else:
                            st.session_state.chatbot_messages.append({"role": "assistant", "content": response})
                    else:
                        st.session_state.chatbot_messages.append({"role": "assistant", "content": response})
            
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
    # Mark that we're in the AI Assistant tab
    st.session_state['current_tab'] = 'ai_assistant'
    
    chatbot = BuildingChatbot()
    chatbot.render_chat_interface(current_df)


# Example usage suggestions
def show_chat_examples():
    """Show example questions users can ask"""
    st.sidebar.markdown("### 💡 Example Questions")
    
    examples = [
        "What can you help me with?",
        "How do I upload my dataset?",
        "Do I have upload permissions?",
        "What are the upload requirements?",
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
            # Set the example question to be processed in the main chat
            st.session_state['pending_chat_message'] = example
