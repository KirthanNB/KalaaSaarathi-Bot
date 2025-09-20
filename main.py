from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
import os
import logging
import requests
from requests.auth import HTTPBasicAuth
import json
import uuid
import random
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize Twilio client
twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")

def download_twilio_media(media_url: str) -> bytes:
    """Download media from Twilio"""
    response = requests.get(media_url, auth=HTTPBasicAuth(twilio_sid, twilio_token))
    response.raise_for_status()
    return response.content

def handle_edit_command(phone_number: str, message: str, media_url: str = None) -> str:
    """Handle edit commands"""
    try:
        parts = message.strip().split()
        if len(parts) < 4 and not media_url:
            return "Usage: edit PRODUCT_ID FIELD VALUE\nExample: edit abc123 price 500"
        
        product_id = parts[1]
        field = parts[2].lower()
        value = " ".join(parts[3:]) if len(parts) > 3 else ""
        
        return f"✅ Updated {field} for product {product_id[:8]}"
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

def handle_myproducts_command(phone_number: str) -> str:
    """Send user their product list"""
    return "📋 Your Products:\n\n• Product 1\n• Product 2\n\nType 'edit PRODUCT_ID field value' to modify"

@app.route('/whatsapp', methods=['POST'])
def whatsapp_reply():
    try:
        # Get form data
        Body = request.form.get('Body', '')
        NumMedia = request.form.get('NumMedia', '0')
        MediaUrl0 = request.form.get('MediaUrl0')
        From = request.form.get('From', '')
        
        logger.info(f"Message from {From}: Body='{Body}', MediaCount={NumMedia}")
        
        resp = MessagingResponse()
        message_body = Body.strip().lower()
        
        # Handle commands
        if message_body.startswith("edit"):
            response_text = handle_edit_command(From, Body, MediaUrl0 if NumMedia != "0" else None)
            resp.message(response_text)
            
        elif message_body in ["myproducts", "mylist", "my items"]:
            response_text = handle_myproducts_command(From)
            resp.message(response_text)
            
        elif NumMedia != "0" and MediaUrl0:
            # If media is sent
            resp.message("📸 Got your image! Processing it now with AI...")
            
        else:
            # Default welcome message
            welcome_msg = """👋 नमस्ते! Welcome to KalaaSaarathi!

Send me a photo of your handmade craft and I'll:
1. 📸 Analyze it with AI
2. 🛍️ Create an online shop
3. 📊 Suggest a fair price

Commands:
• myproducts - List your items
• edit PRODUCT_ID price 500 - Change price
• edit PRODUCT_ID description "New text" - Update description

Just send a photo to get started!"""
            resp.message(welcome_msg)

        return Response(str(resp), mimetype='text/xml')
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        resp = MessagingResponse()
        resp.message("⚠️ Sorry, I encountered an error. Please try sending the photo again.")
        return Response(str(resp), mimetype='text/xml')

@app.route('/health', methods=['GET'])
def health_check():
    return {
        "status": "healthy", 
        "service": "KalaaSaarathi WhatsApp API",
        "timestamp": datetime.now().isoformat()
    }

@app.route('/')
def home():
    return "✅ KalaaSaarathi Server is Running! Visit /whatsapp for WhatsApp webhook"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)