#!/usr/bin/env python3
"""
Simple script to test Gemini API connectivity independently of WebSocket
"""

import os
import sys
import traceback
from dotenv import load_dotenv
import google.genai as genai

# Load environment variables
load_dotenv()

def test_api_connection():
    print("🧪 Testing Gemini API Connection")
    print("=" * 50)
    
    # Check API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        print("❌ No API key found in environment variables")
        print("   Check GEMINI_API_KEY or GOOGLE_API_KEY in .env file")
        return False
    
    print(f"🔑 API Key found: {api_key[:10]}...{api_key[-4:]}")
    
    # Test client initialization
    try:
        client = genai.Client(api_key=api_key)
        print("✅ Gemini client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Gemini client: {e}")
        traceback.print_exc()
        return False
    
    # Test simple API call (non-live)
    try:
        print("🔄 Testing basic API call...")
        
        # Try a simple generate request
        model = client.models.generate_content(
            model="gemini-1.5-flash",
            contents="Say hello in one word"
        )
        
        print("✅ Basic API call successful")
        print(f"   Response: {model.text if hasattr(model, 'text') else 'No text response'}")
        
    except Exception as e:
        print(f"❌ Basic API call failed: {e}")
        print("   This might indicate API key or quota issues")
        traceback.print_exc()
        return False
    
    # Test Live API availability (without full connection)
    try:
        print("🔄 Testing Live API model availability...")
        
        # Check if live models are available
        models = client.models.list()
        live_models = [m for m in models if 'live' in m.name.lower()]
        
        print(f"✅ Found {len(live_models)} live models")
        for model in live_models:
            print(f"   - {model.name}")
            
        # Check specifically for our model
        target_model = "gemini-2.5-flash-live-preview"
        model_found = any(target_model in m.name for m in models)
        
        if model_found:
            print(f"✅ Target model '{target_model}' is available")
        else:
            print(f"⚠️ Target model '{target_model}' not found")
            print("   Available models:")
            for model in models:
                if 'gemini' in model.name.lower():
                    print(f"   - {model.name}")
        
    except Exception as e:
        print(f"⚠️ Could not check model availability: {e}")
        print("   This might not prevent Live API usage")
    
    print("\n🎯 Summary:")
    print("   ✅ API key is valid")
    print("   ✅ Basic API calls work")
    print("   📡 Live API WebSocket connection should be tested separately")
    
    return True

def test_imports():
    print("\n🔧 Testing Module Imports")
    print("=" * 50)
    
    try:
        import travel_mock_data
        print("✅ travel_mock_data imported successfully")
        
        # Test mock data functionality
        result = travel_mock_data.test_travel_system()
        print(f"✅ Travel system test: {result.get('status')}")
        
    except Exception as e:
        print(f"❌ Failed to import travel_mock_data: {e}")
        traceback.print_exc()
        return False
    
    try:
        import gemini_tools
        print("✅ gemini_tools imported successfully")
        print(f"   Travel tool has {len(gemini_tools.travel_tool.function_declarations)} functions")
        
    except Exception as e:
        print(f"❌ Failed to import gemini_tools: {e}")
        traceback.print_exc()
        return False
    
    return True

def test_network_connectivity():
    print("\n🌐 Testing Network Connectivity")
    print("=" * 50)
    
    import socket
    import ssl
    
    # Test basic Google connectivity
    try:
        socket.setdefaulttimeout(10)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("googleapis.com", 443))
        sock.close()
        print("✅ Can connect to googleapis.com:443")
    except Exception as e:
        print(f"❌ Cannot connect to googleapis.com:443: {e}")
        return False
    
    # Test DNS resolution
    try:
        import socket
        ip = socket.gethostbyname("generativelanguage.googleapis.com")
        print(f"✅ DNS resolution works: generativelanguage.googleapis.com -> {ip}")
    except Exception as e:
        print(f"❌ DNS resolution failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Gemini API Diagnostics")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Run all tests
    all_tests_passed &= test_api_connection()
    all_tests_passed &= test_imports()
    all_tests_passed &= test_network_connectivity()
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 All tests passed! The WebSocket timeout might be a different issue.")
        print("   Possible solutions:")
        print("   - Increase WebSocket timeout")
        print("   - Check for firewall blocking WebSocket connections")
        print("   - Verify Google's Live API service status")
    else:
        print("❌ Some tests failed. Fix these issues first.")
    
    print("=" * 60)