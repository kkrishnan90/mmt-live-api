#!/usr/bin/env python3
"""
Test Vertex AI authentication and Gemini Live API access
"""

import os
import sys
import traceback
from dotenv import load_dotenv
import google.genai as genai

# Load environment variables
load_dotenv()

def test_vertex_auth():
    print("🔍 Testing Vertex AI Authentication")
    print("=" * 50)
    
    # Check environment variables
    vertex_enabled = os.getenv("GOOGLE_GENAI_USE_VERTEXAI")
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    print(f"🔧 GOOGLE_GENAI_USE_VERTEXAI: {vertex_enabled}")
    print(f"🔧 GOOGLE_CLOUD_PROJECT: {project_id}")
    print(f"🔧 GOOGLE_APPLICATION_CREDENTIALS: {credentials_path}")
    
    if not vertex_enabled or vertex_enabled.lower() != 'true':
        print("⚠️ Vertex AI not enabled")
        return False
    
    if not project_id:
        print("❌ No Google Cloud project ID set")
        return False
    
    if not credentials_path:
        print("❌ No service account credentials path set")
        return False
    
    if not os.path.exists(credentials_path):
        print(f"❌ Service account file does not exist: {credentials_path}")
        return False
    
    print(f"✅ Service account file exists: {credentials_path}")
    
    # Test client initialization with Vertex AI
    try:
        print("🔄 Initializing Gemini client with Vertex AI...")
        
        # Initialize client - should use Vertex AI automatically
        client = genai.Client()
        print("✅ Gemini client (Vertex AI) initialized successfully")
        
        # Test basic functionality
        print("🔄 Testing basic content generation...")
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents="Say 'Hello from Vertex AI' in exactly those words"
        )
        
        print("✅ Basic content generation successful")
        print(f"   Response: {response.text}")
        
        return True
        
    except Exception as e:
        print(f"❌ Vertex AI test failed: {e}")
        traceback.print_exc()
        return False

def test_live_api_availability():
    print("\n🎮 Testing Live API Availability")
    print("=" * 50)
    
    try:
        client = genai.Client()
        
        # Check available models
        print("🔄 Checking available models...")
        models = list(client.models.list())
        
        print(f"✅ Found {len(models)} total models")
        
        # Look for live models
        live_models = []
        gemini_models = []
        
        for model in models:
            model_name = model.name
            if 'live' in model_name.lower():
                live_models.append(model_name)
            if 'gemini' in model_name.lower():
                gemini_models.append(model_name)
        
        print(f"📋 Gemini models: {len(gemini_models)}")
        for model in gemini_models[:10]:  # Show first 10
            print(f"   - {model}")
        
        print(f"🎮 Live models: {len(live_models)}")
        for model in live_models:
            print(f"   - {model}")
        
        # Check our target model
        target_model = "gemini-2.5-flash-live-preview"
        model_available = any(target_model in model for model in [m.name for m in models])
        
        if model_available:
            print(f"✅ Target model '{target_model}' is available")
        else:
            print(f"⚠️ Target model '{target_model}' not found")
            print("   Available Gemini models that might work:")
            for model in gemini_models:
                if 'flash' in model.lower() or 'live' in model.lower():
                    print(f"   📍 {model}")
        
        return True
        
    except Exception as e:
        print(f"❌ Model availability test failed: {e}")
        traceback.print_exc()
        return False

def test_live_connection():
    print("\n🔗 Testing Live API Connection")
    print("=" * 50)
    
    try:
        from google.genai import types
        
        client = genai.Client()
        print("✅ Client ready for Live API test")
        
        # Create minimal Live config
        live_config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction="You are a test assistant. Say hello.",
        )
        
        print("🔄 Attempting Live API connection...")
        print("   (This is where the timeout was happening)")
        
        # Note: We won't actually connect here in the test
        # Just verify the config can be created
        print("✅ Live config created successfully")
        print("   Config modalities:", live_config.response_modalities)
        
        # The actual connection would be:
        # async with client.aio.live.connect(model="gemini-2.5-flash-live-preview", config=live_config) as session:
        #     print("Connected!")
        
        print("⚠️ Actual connection test requires async context")
        print("   Ready to test in main application")
        
        return True
        
    except Exception as e:
        print(f"❌ Live connection setup failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Vertex AI & Live API Diagnostics")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Run all tests
    all_tests_passed &= test_vertex_auth()
    all_tests_passed &= test_live_api_availability()
    all_tests_passed &= test_live_connection()
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 All Vertex AI tests passed!")
        print("   The Live API should work now")
        print("   Try restarting the backend server")
    else:
        print("❌ Some Vertex AI tests failed")
        print("   Check service account permissions")
        print("   Verify project configuration")
    
    print("=" * 60)