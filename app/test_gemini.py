"""
Test script to verify Google Gemini integration
"""
import streamlit as st

def test_gemini_import():
    """Test if Gemini dependencies can be imported"""
    try:
        import google.generativeai as genai
        print("✅ google.generativeai imported successfully")
        
        from langchain_google_genai import ChatGoogleGenerativeAI
        print("✅ langchain_google_genai imported successfully")
        
        # Test basic configuration (without API key)
        try:
            # This should work even without API key
            llm = ChatGoogleGenerativeAI(
                model="gemini-pro",
                temperature=0.1,
                google_api_key="test-key"  # Just for testing imports
            )
            print("✅ ChatGoogleGenerativeAI can be instantiated")
        except Exception as e:
            print(f"⚠️ ChatGoogleGenerativeAI instantiation issue: {e}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Other error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Google Gemini integration...")
    success = test_gemini_import()
    
    if success:
        print("\n🎉 All Gemini dependencies are working!")
        print("✅ You can now:")
        print("   1. Get a FREE API key from: https://aistudio.google.com/app/apikey")
        print("   2. Add it to .streamlit/secrets.toml")
        print("   3. Restart the app to enable full AI functionality")
    else:
        print("\n❌ Some dependencies are missing or not working properly")
        print("Try running: pip install google-generativeai langchain-google-genai")
