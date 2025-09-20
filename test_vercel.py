# test_vercel.py - Test if it works locally
import os
os.environ['VERCEL'] = '1'

# Test Google credentials setup
google_creds = os.environ.get('GOOGLE_CREDENTIALS_BASE64')
if google_creds:
    import base64
    key_json = base64.b64decode(google_creds).decode('utf-8')
    with open('key.json', 'w') as f:
        f.write(key_json)
    print("✅ Google credentials test passed")

# Test main app import
try:
    from main import app
    print("✅ Main app import successful")
except Exception as e:
    print(f"❌ Main app import failed: {e}")
    import traceback
    traceback.print_exc()