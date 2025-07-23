"""
Test script to identify the specific import causing the chatbot error
"""

print("Testing individual imports...")

try:
    import streamlit as st
    print("✅ streamlit - OK")
except ImportError as e:
    print(f"❌ streamlit - ERROR: {e}")

try:
    import pandas as pd
    print("✅ pandas - OK")
except ImportError as e:
    print(f"❌ pandas - ERROR: {e}")

try:
    from langchain_experimental.agents import create_pandas_dataframe_agent
    print("✅ langchain_experimental.agents - OK")
except ImportError as e:
    print(f"❌ langchain_experimental.agents - ERROR: {e}")

try:
    from langchain_openai import ChatOpenAI
    print("✅ langchain_openai - OK")
except ImportError as e:
    print(f"❌ langchain_openai - ERROR: {e}")

try:
    from langchain_core.messages import HumanMessage, SystemMessage
    print("✅ langchain_core.messages - OK")
except ImportError as e:
    print(f"❌ langchain_core.messages - ERROR: {e}")

try:
    from langchain_community.callbacks.streamlit import StreamlitCallbackHandler
    print("✅ langchain_community.callbacks.streamlit - OK")
except ImportError as e:
    print(f"❌ langchain_community.callbacks.streamlit - ERROR: {e}")

print("\nNow testing the actual chatbot import...")

try:
    import sys
    sys.path.insert(0, '.')
    from utils.chatbot import BuildingChatbot
    print("✅ utils.chatbot - OK")
    
    # Test creating instance
    chatbot = BuildingChatbot()
    print("✅ BuildingChatbot instance created - OK")
    
except ImportError as e:
    print(f"❌ utils.chatbot - ImportError: {e}")
except Exception as e:
    print(f"❌ utils.chatbot - Other Error: {e}")

print("Done!")
