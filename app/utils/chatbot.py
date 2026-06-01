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
try:
    from utils.logger import log_security_event
    from utils.auth_db import get_user_role
except ImportError:
    # Fallback mode - some functions may not be available
    log_security_event = None
    get_user_role = None

from utils.memory_backends import EnhancedConversationMemory, get_memory_status_info


class BuildingChatbot:
    """AI Assistant for Building Analytics Dashboard - Powered by Google Gemini"""
    
    def __init__(self):
        """Initialize the chatbot with Google Gemini configuration"""
        self.setup_gemini()
        self.initialize_session_state()
        
        # Initialize production-ready memory system
        self.setup_memory_system()
        
    def get_user_owned_datasets(self) -> List[str]:
        """Get list of datasets owned by the current user"""
        try:
            username = st.session_state.get("username")
            if not username:
                return []
            
            # Load dataset ownership data
            dataset_ownership = st.session_state.get("dataset_ownership", {})
            if not dataset_ownership:
                # Try to load from file
                import json
                import os
                ownership_file = "data/ownership.json"
                if os.path.exists(ownership_file):
                    try:
                        with open(ownership_file, 'r') as f:
                            dataset_ownership = json.load(f)
                        st.session_state["dataset_ownership"] = dataset_ownership
                    except:
                        dataset_ownership = {}
            
            # Filter datasets owned by current user
            owned_datasets = []
            for dataset_name, dataset_info in dataset_ownership.items():
                if dataset_info.get("owner") == username:
                    owned_datasets.append(dataset_name)
            
            return owned_datasets
            
        except Exception as e:
            return []
    
    def get_available_datasets(self) -> List[str]:
        """Get list of datasets available to the user (owned + public)"""
        owned_datasets = self.get_user_owned_datasets()
        
        # Add default public datasets if user has no owned datasets
        public_datasets = ["Auch", "Lille", "Ciry-le-Noble", "Gordes"]
        
        # For admin users, show all. For regular users, show owned + public if no owned datasets
        user_role = st.session_state.get("user_role", "user")
        if user_role == "admin":
            return public_datasets + owned_datasets
        elif owned_datasets:
            return owned_datasets  # Only show owned datasets
        else:
            return public_datasets  # Show public datasets if no owned ones
        
    def setup_gemini(self):
        """Setup Google Gemini configuration"""
        try:
            if not GEMINI_AVAILABLE:
                print("❌ Gemini dependencies not available")
                self.llm = None
                self.pandas_agent = None
                self.api_available = False
                return
                
            # Get API key from secrets
            api_key = "demo-mode"  # Default fallback
            
            try:
                if hasattr(st, 'secrets') and "gemini" in st.secrets and "api_key" in st.secrets["gemini"]:
                    api_key = st.secrets["gemini"]["api_key"]
                    print(f"🔑 Found API key: {api_key[:20]}...")
                    if api_key and api_key.strip() and api_key != "demo-mode":
                        # Configure Gemini
                        genai.configure(api_key=api_key)
                        print("✅ Gemini API key configured")
                        
                        # Initialize LangChain with Gemini
                        self.llm = ChatGoogleGenerativeAI(
                            model="gemini-2.5-flash",  # Use latest available model
                            temperature=0.1,
                            google_api_key=api_key
                        )
                        # Set as available even if there might be rate limits later
                        self.api_available = True
                        print(f"✅ Gemini LLM initialized successfully")
                    else:
                        # No valid API key, use demo mode
                        self.llm = None
                        self.api_available = False
                        print(f"❌ Invalid API key: {api_key[:10]}...")
                else:
                    # No secrets found, use demo mode
                    self.llm = None
                    self.api_available = False
                    print("❌ No Gemini secrets found")
            except Exception as secrets_error:
                # Secrets file not found or invalid, but still try to create LLM
                print(f"⚠️ Secrets error: {secrets_error}")
                self.llm = None
                self.api_available = False
                
            self.pandas_agent = None
            
        except Exception as e:
            # Fallback to demo mode on any error
            self.llm = None
            self.pandas_agent = None
            self.api_available = False
            
    def setup_memory_system(self):
        """Initialize production-ready memory system"""
        try:
            # Get database manager if available
            db_manager = None
            try:
                from utils.db_manager import get_database_manager
                db_manager, _, db_available = get_database_manager()
                if not db_available:
                    db_manager = None
            except:
                db_manager = None
            
            # Initialize memory with auto-detection
            self.memory = EnhancedConversationMemory(
                storage_type="auto",  # Auto-detect best storage
                db_manager=db_manager,
                memory_size=10
            )
            
            # Store memory info for UI display
            self.memory_status = get_memory_status_info()
            
        except Exception as e:
            # Fallback to simple session state if memory setup fails
            self.memory = None
            self.memory_status = {
                "available_backends": {"session": True},
                "recommended": "session", 
                "current_storage": "fallback"
            }
            
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
        """Process user chat message using AI-powered intent analysis with memory"""
        
        # Add user message to memory
        if self.memory:
            self.memory.add_message(user_input, "human")
        
        try:
            # ALWAYS TRY AI FIRST, regardless of api_available flag
            if self.llm is not None:
                # Use AI to analyze the query intent with conversation context
                intent_data = self.analyze_query_intent_with_context(user_input)
                
                # Use corrected query if available
                processed_query = intent_data.get('spelling_corrected', user_input)
                
                # Route based on intent - but prioritize general AI responses for model questions
                if df is not None and intent_data['intent'] in ['total_count', 'class_count', 'summary', 'model_results']:
                    response = self.handle_data_query_with_intent(processed_query, df, intent_data)
                elif intent_data['intent'] in ['upload_help', 'dataset_guidance']:
                    response = self.handle_upload_guidance(processed_query, intent_data)
                else:
                    # Use AI for general queries (including model explanations)
                    response = self.handle_general_query_with_context(processed_query)
            else:
                # Only fall back to demo responses if AI is truly unavailable
                response = self.get_demo_response_with_memory(user_input, df)
            
            # Add response to memory
            if self.memory:
                self.memory.add_message(response, "ai")
                
            return response
            
        except Exception as e:
            # Even in error cases, try AI one more time before complete fallback
            try:
                if self.llm is not None:
                    fallback_response = self.handle_general_query_with_context(user_input)
                else:
                    fallback_response = self.get_demo_response_with_memory(user_input, df)
            except:
                fallback_response = f"⚠️ **Technical Issue**: I encountered an error processing your question about: '{user_input}'. Please try rephrasing your question or check if the AI service is available."
            
            if self.memory:
                self.memory.add_message(fallback_response, "ai")
            return fallback_response
            
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
            try:
                from utils.auth_db import get_user_role
                from utils.secure_auth import secure_auth
            except ImportError:
                # Fallback mode - auth functions not available
                pass
            
            username = st.session_state.get('username', 'Unknown')
            user_role = st.session_state.get('user_role', 'user')
            upload_context = intent_data.get('upload_context', 'general')
            
            # Check if user has upload permission - everyone can upload
            has_upload_permission = True  # Everyone can upload datasets now
            
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

✅ **Everyone can upload datasets!** 

**Available Options:**
- 📤 Upload your own custom building datasets
- 📊 Analyze your uploaded datasets with all ML models
- 📈 Generate reports and comparisons from your data

**To upload**: Look for "Upload Custom Dataset" in the dataset selection dropdown.

**File Requirements**: CSV format, building data with coordinates and attributes."""
                    
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
            # Create a comprehensive system message for building analytics context
            system_content = f"""You are an expert AI assistant for a Building Analytics Dashboard. {self.get_app_context()}

You specialize in:
- Building performance analysis and energy efficiency
- Multi-criteria decision analysis (TOPSIS, PCA, Mahalanobis distance, etc.)
- Data science and machine learning for building analytics
- Sustainability metrics and environmental impact assessment
- Building renovation and investment decision support

Provide detailed, accurate, and helpful responses. When discussing technical concepts like TOPSIS, PCA, or other algorithms, explain them thoroughly with mathematical details when requested."""

            messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=query)
            ]
            
            response = self.llm.invoke(messages)
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
        
        # For any model explanation questions, redirect to AI or provide notice
        model_keywords = ['pca', 'principal', 'mahalanobis', 'topsis', 'tree', 'decision', 'cosine', 'similarity', 'weighted', 'scoring']
        if any(keyword in query_lower for keyword in model_keywords):
            return f"""⚠️ **Enhanced AI Response Needed**

I've detected you're asking about machine learning models. For detailed, comprehensive explanations, the system needs AI capability.

**Your Question**: {query}

**To get detailed AI-generated responses:**
1. The system will attempt to use AI if properly configured
2. If AI is unavailable, you'll see this message

**What you'll get with AI:**
- Detailed mathematical explanations
- Step-by-step algorithms  
- Practical examples for building analytics
- Customized responses to your specific questions

💡 **This is much better than predefined static responses!**"""
        
        # For general questions, provide basic help
        return """👋 **Hello! I'm your Building Analytics Assistant**

I can help you with:
- **Building performance analysis** and energy efficiency insights
- **Machine learning models** for classification and ranking  
- **Dataset analysis** and statistical summaries
- **Upload guidance** for custom datasets

**Popular topics:**
- "What's TOPSIS?" or "Explain PCA math"
- "How many buildings are in this dataset?"
- "Can I upload my own data?"
- "Compare different ranking methods"

Ask me anything about building analytics! 🏢📊"""

    def render_chat_interface(self, df: Optional[pd.DataFrame] = None):
        """Render the chat interface with improved layout"""
        # Set a flag to indicate we're in the chatbot (but don't interfere with auth)
        # st.session_state._chatbot_active = True  # Removed to prevent session interference
        
        st.markdown("### 🤖 Building Analytics Assistant")
        st.markdown("*Powered by Google Gemini 2.5 Flash* ⚡")
        
        # Status indicators
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if not GEMINI_AVAILABLE:
                st.error("❌ **Missing Dependencies**: Please install Google Gemini dependencies:")
                st.code("pip install google-generativeai langchain-google-genai", language="bash")
                st.info("After installation, restart the application.")
                return
            elif not self.api_available:
                st.warning("⚠️ **Demo Mode**: Configure API key for full AI capabilities")
            else:
                st.success("🚀 **AI Mode Active**: Real-time intelligent responses enabled!")
        
        with col2:
            # Dataset status
            if df is not None:
                st.metric("📊 Dataset", f"{df.shape[0]} buildings")
                st.session_state.chatbot_dataset = df
            else:
                st.info("📋 No dataset loaded")
                
        with col3:
            # Clear chat button
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.chatbot_messages = []
                st.rerun()
        
        # Chat mode selector with better styling
        st.markdown("---")
        chat_mode = st.selectbox(
            "💬 **Choose Chat Mode**",
            ["general", "data_analysis", "feature_explanation"],
            format_func=lambda x: {
                "general": "🗣️ General Questions & Model Explanations",
                "data_analysis": "📊 Data Analysis & Insights", 
                "feature_explanation": "🎓 Feature & Algorithm Details"
            }[x],
            help="Select the type of assistance you need"
        )
        st.session_state.chatbot_mode = chat_mode
        
        # Chat container with better styling
        st.markdown("---")
        
        # Initialize chat history
        if "chatbot_messages" not in st.session_state:
            st.session_state.chatbot_messages = []
            # Add welcome message
            welcome_msg = """👋 **Welcome to the Building Analytics Assistant!**

I'm here to help you understand:
• **Machine Learning Models** (TOPSIS, PCA, Mahalanobis, etc.)
• **Building Performance Analysis** 
• **Dataset Insights & Statistics**
• **Feature Explanations**

**Try asking:**
• "What's TOPSIS and how does it work?"
• "Explain PCA mathematics"
• "How does Mahalanobis distance detect outliers?"
• "Show me dataset summary"

**What would you like to know?** 🤔"""
            
            st.session_state.chatbot_messages.append({
                "role": "assistant", 
                "content": welcome_msg
            })

        # Chat messages container with improved styling
        chat_container = st.container()
        
        with chat_container:
            # Display chat history with better formatting
            for i, message in enumerate(st.session_state.chatbot_messages):
                if message["role"] == "user":
                    # User question with distinctive styling
                    st.markdown(
                        f"""<div style="background-color: #e3f2fd; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid #2196f3;">
                        <strong>🙋‍♂️ Your Question:</strong><br>
                        {message["content"]}
                        </div>""", 
                        unsafe_allow_html=True
                    )
                else:
                    # Assistant answer with distinctive styling
                    st.markdown(
                        f"""<div style="background-color: #f1f8e9; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid #4caf50;">
                        <strong>🤖 AI Assistant:</strong>
                        </div>""", 
                        unsafe_allow_html=True
                    )
                    st.markdown(message["content"])
                    
                    # Display chart if present
                    if "chart" in message:
                        st.plotly_chart(message["chart"], use_container_width=True)
                    
                    # Add a subtle separator after each answer
                    if i < len(st.session_state.chatbot_messages) - 1:
                        st.markdown("---")
        
        # Chat input section with better styling
        st.markdown("---")
        st.markdown("### 💭 Ask Your Question")
        
        # Quick example buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🎯 What's TOPSIS?", use_container_width=True):
                st.session_state.pending_chat_message = "What is TOPSIS and how does it work mathematically?"
        
        with col2:
            if st.button("📊 Explain PCA", use_container_width=True):
                st.session_state.pending_chat_message = "Explain Principal Component Analysis (PCA) with mathematical details"
        
        with col3:
            if st.button("🔍 Mahalanobis Distance", use_container_width=True):
                st.session_state.pending_chat_message = "How does Mahalanobis distance work for outlier detection?"
        
        # Check for pending message from example buttons
        if st.session_state.get('pending_chat_message'):
            prompt = st.session_state.pending_chat_message
            del st.session_state['pending_chat_message']  # Clear the pending message
            
            # Process the example question immediately
            self._process_user_message(prompt, df, chat_mode)
        
        # Main chat input with enhanced styling
        st.markdown("### ✍️ Type your question here:")
        
        if prompt := st.chat_input(
            "💡 Ask me anything about building analytics, ML models, or your data...", 
            key="ai_assistant_chat_input"
        ):
            # Process the user's message
            self._process_user_message(prompt, df, chat_mode)

    def _process_user_message(self, prompt: str, df: Optional[pd.DataFrame], chat_mode: str):
        """Process a user message and generate response"""
        # Add user message with styling
        st.session_state.chatbot_messages.append({"role": "user", "content": prompt})
        
        # Show user message immediately
        st.markdown(
            f"""<div style="background-color: #e3f2fd; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid #2196f3;">
            <strong>🙋‍♂️ Your Question:</strong><br>
            {prompt}
            </div>""", 
            unsafe_allow_html=True
        )
        
        # Generate and show response
        with st.spinner("🤖 AI is thinking..."):
            response = self.process_chat_message(prompt, df)
        
        # Show assistant response with styling
        st.markdown(
            f"""<div style="background-color: #f1f8e9; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid #4caf50;">
            <strong>🤖 AI Assistant:</strong>
            </div>""", 
            unsafe_allow_html=True
        )
        st.markdown(response)
        
        # Try to generate chart if requested
        chart = None
        if df is not None and any(word in prompt.lower() for word in ['chart', 'plot', 'show', 'visualize']):
            chart = self.generate_chart_from_query(df, prompt)
            if chart:
                st.plotly_chart(chart, use_container_width=True)
        
        # Add response to chat history
        if chart:
            st.session_state.chatbot_messages.append({
                "role": "assistant", 
                "content": response,
                "chart": chart
            })
        else:
            st.session_state.chatbot_messages.append({"role": "assistant", "content": response})
        
        # Add separator
        st.markdown("---")
        
        # Log chat interaction
        if "username" in st.session_state and log_security_event:
            try:
                log_security_event(
                    event_type="chatbot_interaction",
                    username=st.session_state.username,
                    details={"query": prompt, "mode": chat_mode},
                    success=True
                )
            except (NameError, ImportError):
                # log_security_event not available in fallback mode
                pass
        
        # Rerun to update the interface
        st.rerun()

    def analyze_query_intent_with_context(self, user_input: str) -> Dict[str, Any]:
        """Analyze query intent with conversation context"""
        if not self.memory:
            return self.analyze_query_intent(user_input)
        
        try:
            # Get conversation context
            context = self.memory.get_context_summary()
            recent_messages = self.memory.get_conversation_history()[-4:]  # Last 4 messages
            
            # Build context for the AI
            context_prompt = f"""
            Previous conversation context: {context}
            
            Recent messages:
            """
            
            for msg in recent_messages:
                role = "User" if msg["type"] == "human" else "Assistant"
                context_prompt += f"{role}: {msg['content'][:100]}...\n"
            
            enhanced_prompt = f"""
            {context_prompt}
            
            Current user query: "{user_input}"
            
            Analyze this query considering the conversation context above.
            """
            
            return self.analyze_query_intent(enhanced_prompt)
            
        except Exception:
            # Fallback to basic analysis
            return self.analyze_query_intent(user_input)
    
    def perform_data_analysis(self, query: str, city_name: str) -> str:
        """Perform actual data analysis for specific queries"""
        try:
            # Import data processing here to avoid circular imports
            from data.data_processing import get_data_for_city
            
            query_lower = query.lower()
            
            # Load the actual data
            data = get_data_for_city(city_name)
            if data is None or data.empty:
                return f"❌ **No data available for {city_name}**\n\nPlease check if the dataset is properly loaded."
            
            # Perform specific analysis based on query
            if any(keyword in query_lower for keyword in ["average", "mean"]) and any(keyword in query_lower for keyword in ["co2", "carbon", "emission"]):
                # Calculate average CO2 usage
                co2_columns = [col for col in data.columns if 'co2' in col.lower() or 'carbon' in col.lower() or 'emission' in col.lower()]
                if co2_columns:
                    avg_co2 = data[co2_columns[0]].mean()
                    return f"""📊 **CO2 Analysis for {city_name}**
                    
**Average CO2 Usage:** {avg_co2:.1f} kg/year
**Total Buildings Analyzed:** {len(data)}
**CO2 Range:** {data[co2_columns[0]].min():.1f} - {data[co2_columns[0]].max():.1f} kg/year

💡 **Insights:**
- Buildings with lowest CO2: {data[co2_columns[0]].min():.1f} kg/year
- Buildings with highest CO2: {data[co2_columns[0]].max():.1f} kg/year
- Standard deviation: {data[co2_columns[0]].std():.1f} kg/year"""
                
            elif any(keyword in query_lower for keyword in ["average", "mean"]) and any(keyword in query_lower for keyword in ["energy", "consumption"]):
                # Calculate average energy usage
                energy_columns = [col for col in data.columns if 'energy' in col.lower() or 'consumption' in col.lower()]
                if energy_columns:
                    avg_energy = data[energy_columns[0]].mean()
                    return f"""⚡ **Energy Analysis for {city_name}**
                    
**Average Energy Usage:** {avg_energy:.1f} kWh/year
**Total Buildings Analyzed:** {len(data)}
**Energy Range:** {data[energy_columns[0]].min():.1f} - {data[energy_columns[0]].max():.1f} kWh/year"""
                
            elif any(keyword in query_lower for keyword in ["how many", "count", "number"]) and "class" in query_lower:
                # Count buildings by energy class
                class_columns = [col for col in data.columns if 'class' in col.lower() or 'label' in col.lower()]
                if class_columns:
                    class_counts = data[class_columns[0]].value_counts()
                    result = f"🏗️ **Building Classification for {city_name}**\n\n"
                    for class_name, count in class_counts.items():
                        result += f"**Class {class_name}:** {count} buildings\n"
                    result += f"\n**Total Buildings:** {len(data)}"
                    return result
                    
            elif any(keyword in query_lower for keyword in ["distribution", "breakdown"]):
                # Show distribution analysis
                class_columns = [col for col in data.columns if 'class' in col.lower() or 'label' in col.lower()]
                if class_columns:
                    class_counts = data[class_columns[0]].value_counts()
                    total = len(data)
                    result = f"📊 **Distribution Analysis for {city_name}**\n\n"
                    for class_name, count in class_counts.items():
                        percentage = (count / total) * 100
                        result += f"**Class {class_name}:** {count} buildings ({percentage:.1f}%)\n"
                    return result
                    
            # If no specific analysis matched, provide general stats
            return f"""📈 **General Statistics for {city_name}**
            
**Total Buildings:** {len(data)}
**Dataset Columns:** {len(data.columns)}
**Data Shape:** {len(data)} rows × {len(data.columns)} columns

💡 **Available Analysis:**
- Energy consumption statistics
- CO2 emissions analysis  
- Building classification breakdown
- Water usage insights

**Try asking:** "What's the average CO2 usage?" or "Show me the energy distribution"
"""
            
        except Exception as e:
            return f"❌ **Analysis Error**\n\nSorry, I couldn't analyze the data for {city_name}. Error: {str(e)}"
    
    def handle_general_query_with_context(self, query: str) -> str:
        """Handle general queries with conversation memory"""
        if not self.memory:
            return self.handle_general_query(query)
        
        # Get conversation context
        context = self.memory.get_context_summary()
        recent_history = self.memory.get_conversation_history()[-4:]
        
        query_lower = query.lower()
        
        # Handle specific city requests
        if any(city in query_lower for city in ["auch", "lille", "ciry", "gordes"]):
            city_name = None
            if "auch" in query_lower:
                city_name = "Auch"
            elif "lille" in query_lower:
                city_name = "Lille"
            elif "ciry" in query_lower:
                city_name = "Ciry-le-Noble"
            elif "gordes" in query_lower:
                city_name = "Gordes"
                
            if city_name:
                # Check if user has access to this dataset
                available_datasets = self.get_available_datasets()
                
                if city_name in available_datasets:
                    # Check if this is an analytical query that needs actual data processing
                    analytical_keywords = ["average", "mean", "how many", "count", "total", "distribution", "breakdown", "analyze", "statistics", "stats"]
                    
                    if any(keyword in query_lower for keyword in analytical_keywords):
                        # Perform actual data analysis instead of showing template
                        return self.perform_data_analysis(query, city_name)
                    
                    # Otherwise show the template for general city requests
                    context_intro = ""
                    if recent_history:
                        context_intro = f"Based on our conversation, let me help you with {city_name}. "
                    
                    return f"""{context_intro}🏢 **{city_name} Dataset Analysis**

I can help you analyze the {city_name} building dataset. Here's what I can do:

📊 **Available Analysis:**
- Building count and distribution by energy class
- Energy consumption patterns and statistics  
- CO2 emissions analysis
- Water usage insights
- Performance comparisons and rankings

🔍 **Example Questions for {city_name}:**
- "How many buildings are in {city_name}?"
- "Show me the energy distribution for {city_name}"
- "What's the average CO2 usage in {city_name}?"
- "Find the most efficient buildings in {city_name}"
- "Compare {city_name} building classes"

**What specific analysis would you like me to perform on the {city_name} dataset?**"""
                
                else:
                    # User doesn't have access to this dataset
                    owned_datasets = self.get_user_owned_datasets()
                    if owned_datasets:
                        datasets_list = ', '.join(owned_datasets)
                        return f"""❌ **{city_name} Dataset Not Available**

You don't currently have access to the {city_name} dataset.

**Your Available Datasets:** {datasets_list}

**Options:**
- Analyze your uploaded datasets
- Upload a new dataset with {city_name} buildings
- Ask an administrator for access to public datasets

**Would you like to analyze one of your available datasets instead?**"""
                    else:
                        return f"""❌ **{city_name} Dataset Not Available**

You don't currently have access to the {city_name} dataset.

**To analyze building data:**
1. **Upload your own dataset** using "Upload Custom Dataset"
2. **Contact administrator** for access to public datasets

**Would you like help uploading your own building data?**"""
        
        # Handle dataset summary requests
        if any(phrase in query_lower for phrase in ["summarize", "summary", "overview", "describe", "analyze"]):
            if any(phrase in query_lower for phrase in ["dataset", "data", "buildings"]):
                context_intro = ""
                if recent_history:
                    context_intro = "Continuing our data analysis discussion, "
                
                # Get user's available datasets
                available_datasets = self.get_available_datasets()
                owned_datasets = self.get_user_owned_datasets()
                
                datasets_text = ""
                if owned_datasets:
                    datasets_text = f"**Your Datasets:** {', '.join(owned_datasets)}"
                    if len(available_datasets) > len(owned_datasets):
                        public_datasets = [d for d in available_datasets if d not in owned_datasets]
                        datasets_text += f"\n**Public Datasets:** {', '.join(public_datasets)}"
                else:
                    datasets_text = f"**Available Datasets:** {', '.join(available_datasets)}"
                
                return f"""{context_intro}📊 **Dataset Summary Request**

I can provide detailed summaries of your available building datasets including:

🏗️ **Building Statistics:**
- Total building count and distribution
- Energy efficiency class breakdown (A-F)
- Performance statistics and ranges

📈 **Analysis Options:**
- Energy consumption patterns
- CO2 emissions analysis
- Water usage insights
- Efficiency comparisons

{datasets_text}

**To get a summary:**
1. **Select a dataset** from the sidebar dropdown
2. **Then ask:** "Summarize this dataset" or "Tell me about these buildings"

**Which dataset would you like me to analyze?**"""
        
        # Check for follow-up questions
        if any(phrase in query_lower for phrase in ["more about", "tell me more", "explain further", "continue"]):
            # This is likely a follow-up question
            for msg in reversed(recent_history):
                if msg["type"] == "ai":
                    last_topic = msg["content"][:200].lower()
                    if "energy" in last_topic:
                        return "I can provide more details about energy analysis. What specific aspect would you like to explore?"
                    elif "classification" in last_topic:
                        return "I can explain more about building classification methods. Which model interests you most?"
                    elif "co2" in last_topic:
                        return "I can dive deeper into CO2 emissions analysis. Would you like to see correlations or reduction strategies?"
                    break
        
        # Regular handling - but don't add redundant context intro
        base_response = self.handle_general_query(query)
        
        # Only add context if it's not the default welcome message
        if "Welcome to the Building Analytics Assistant" not in base_response and context != "No previous conversation context.":
            # Don't add context intro if the base response already handles the query well
            return base_response
        
        return base_response
    
    def get_demo_response_with_memory(self, user_input: str, df: Optional[pd.DataFrame] = None) -> str:
        """Get demo response with conversation memory"""
        if not self.memory:
            return self.get_demo_response(user_input, df)
        
        query_lower = user_input.lower()
        
        # Handle specific city requests with memory context
        if any(city in query_lower for city in ["auch", "lille", "ciry", "gordes"]):
            city_name = None
            if "auch" in query_lower:
                city_name = "Auch"
            elif "lille" in query_lower:
                city_name = "Lille"
            elif "ciry" in query_lower:
                city_name = "Ciry-le-Noble"
            elif "gordes" in query_lower:
                city_name = "Gordes"
                
            if city_name:
                # Check if user has access to this dataset
                available_datasets = self.get_available_datasets()
                
                if city_name in available_datasets:
                    # Check if this is an analytical query that needs actual data processing
                    analytical_keywords = ["average", "mean", "how many", "count", "total", "distribution", "breakdown", "analyze", "statistics", "stats"]
                    
                    if any(keyword in query_lower for keyword in analytical_keywords):
                        # Perform actual data analysis instead of showing template
                        return self.perform_data_analysis(user_input, city_name)
                    
                    # Otherwise show the template for general city requests
                    return f"""🏢 **{city_name} Dataset Analysis**

I can help you analyze the {city_name} building dataset! Here's what I can show you:

📊 **Available for {city_name}:**
- Building energy efficiency classes (A, B, C, D, E, F)
- Energy consumption statistics and patterns
- CO2 emissions analysis and trends
- Water usage insights and comparisons
- Building performance rankings

🔍 **Try asking:**
- "How many buildings are in {city_name}?"
- "Show me the energy classes for {city_name}"
- "What's the average energy consumption in {city_name}?"
- "Find the most efficient buildings in {city_name}"

**First, make sure to select "{city_name}" from the dataset dropdown in the sidebar, then ask your specific question!**"""
                
                else:
                    # User doesn't have access
                    owned_datasets = self.get_user_owned_datasets()
                    if owned_datasets:
                        return f"""❌ **{city_name} Not Available to You**

You don't have access to the {city_name} dataset.

**Your Available Datasets:** {', '.join(owned_datasets)}

**To analyze {city_name} data:**
- Upload your own {city_name} building dataset
- Contact administrator for public dataset access

**Would you like to work with your available datasets instead?**"""
                    else:
                        return f"""❌ **{city_name} Not Available**

You don't have access to the {city_name} dataset.

**To analyze building data:**
1. Upload your own dataset with building information
2. Contact administrator for access to public datasets

**Would you like help uploading your own data?**"""
        
        # Handle dataset summary with memory
        if any(phrase in query_lower for phrase in ["summarize", "summary", "dataset"]):
            # Get user's available datasets
            available_datasets = self.get_available_datasets()
            owned_datasets = self.get_user_owned_datasets()
            
            datasets_info = ""
            if owned_datasets:
                datasets_info = f"\n\n**Your Uploaded Datasets:** {', '.join(owned_datasets)}"
                if len(available_datasets) > len(owned_datasets):
                    public_datasets = [d for d in available_datasets if d not in owned_datasets]
                    datasets_info += f"\n**Available Public Datasets:** {', '.join(public_datasets)}"
            else:
                datasets_info = f"\n\n**Available Datasets:** {', '.join(available_datasets)}"
            
            return f"""📊 **Dataset Summary Available**

I can provide comprehensive dataset summaries including:

🏗️ **Building Metrics:**
- Total building count and distribution
- Energy efficiency class breakdown (A-F)
- Performance statistics and ranges

📈 **Analysis Options:**
- Energy consumption patterns
- CO2 emissions distribution  
- Water usage insights
- Efficiency comparisons

{datasets_info}

**To get a summary:**
1. Select a dataset from the sidebar dropdown
2. Ask: "Summarize this dataset" or "Tell me about these buildings"

**Which dataset would you like me to analyze?**"""
        
        # Get base response but avoid adding redundant context
        base_response = self.get_demo_response(user_input, df)
        
        # Only add memory context if it's useful
        context = self.memory.get_context_summary()
        if (context != "No previous conversation context." and 
            "Welcome to the Building Analytics Assistant" not in base_response):
            return f"Building on our conversation, {base_response[0].lower()}{base_response[1:]}"
        
        return base_response
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get memory system information for UI display"""
        if not self.memory:
            return {"status": "disabled", "backend": "none"}
        
        history_count = len(self.memory.get_conversation_history())
        
        return {
            "status": "enabled",
            "backend": self.memory_status.get("current_storage", "unknown"),
            "message_count": history_count,
            "context": self.memory.get_context_summary(),
            "available_backends": self.memory_status.get("available_backends", {}),
            "recommended": self.memory_status.get("recommended", "session")
        }
    
    def clear_conversation_memory(self):
        """Clear conversation memory"""
        if self.memory:
            self.memory.clear_conversation()
        
        # Also clear session state messages
        if "chatbot_messages" in st.session_state:
            st.session_state.chatbot_messages = []


def render_chatbot_tab(current_df: Optional[pd.DataFrame] = None):
    """Render the chatbot as a tab in the main application with enhanced memory"""
    # Mark that we're in the AI Assistant tab
    st.session_state['current_tab'] = 'ai_assistant'
    
    chatbot = BuildingChatbot()
    
    # Display memory status
    memory_info = chatbot.get_memory_info()
    
    # Memory status header
    st.header("🤖 AI Building Analytics Assistant")
    
    # Memory status display
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        if memory_info["status"] == "enabled":
            st.success("🧠 **Memory Enabled** - I remember our conversation!")
        else:
            st.info("💭 **Session Only** - Memory resets each session")
    
    with col2:
        st.metric("Backend", memory_info.get("backend", "unknown").title())
    
    with col3:
        st.metric("Messages", memory_info.get("message_count", 0))
    
    with col4:
        if st.button("🗑️ Clear Memory"):
            chatbot.clear_conversation_memory()
            st.success("Memory cleared!")
            st.rerun()
    
    # Show memory context if available
    if memory_info["status"] == "enabled" and memory_info.get("message_count", 0) > 0:
        with st.expander("🧠 Conversation Context", expanded=False):
            st.write(f"**Context:** {memory_info.get('context', 'No context available')}")
            
            # Show available backends info
            backends = memory_info.get("available_backends", {})
            st.write("**Available Storage Options:**")
            for backend, available in backends.items():
                icon = "✅" if available else "❌"
                st.write(f"{icon} {backend.title()}")
    
    # Render chat interface
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
