from flask import Flask, request, Response, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os
import logging
import requests
from requests.auth import HTTPBasicAuth
import json
import uuid
import random
from datetime import datetime
import traceback
from threading import Thread
import time



# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Store Twilio credentials in app context for background threads
app.twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
app.twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")

logger.info(f"Twilio SID configured: {bool(app.twilio_sid)}")
logger.info(f"Twilio Token configured: {bool(app.twilio_token)}")

# Thread-safe function to get Twilio client
def get_twilio_client():
    """Get a fresh Twilio client with current credentials"""
    twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")
    if twilio_sid and twilio_token:
        return Client(twilio_sid, twilio_token)
    return None

# Import our modules with fallbacks
try:
    from gemini_helper import describe_image, analyze_product_description, extract_price_from_description, extract_title_from_description, extract_category_from_description
    GEMINI_AVAILABLE = True
    logger.info("Gemini helper loaded successfully")
except Exception as e:
    logger.error(f"Gemini helper not available: {e}")
    GEMINI_AVAILABLE = False
    def describe_image(image_path): return "Beautiful handmade craft with traditional artistry."
    def analyze_product_description(prompt): return '{"enhanced_description": "Handmade with care", "price_suggestions": [299,499,799]}'
    def extract_price_from_description(desc): return 350
    def extract_title_from_description(desc): return "Beautiful Handmade Craft"
    def extract_category_from_description(desc): return "handmade"

try:
    from imagen_helper import remove_bg_and_upload, upload_video
    IMAGEN_AVAILABLE = True
    logger.info("Imagen helper loaded successfully")
except Exception as e:
    logger.error(f"Imagen helper not available: {e}")
    IMAGEN_AVAILABLE = False
    def remove_bg_and_upload(path): return [f"https://storage.googleapis.com/craftlink-images/fallback{i}.jpg" for i in range(1,5)]
    def upload_video(path): return f"https://storage.googleapis.com/craftlink-videos/fallback.mp4"

try:
    from deploy_shop import build_and_host, update_products_json, get_all_products, get_product_by_id, update_seller_profile, get_seller_profile, add_reel, get_all_reels, create_shop_index, deploy_to_firebase
    DEPLOY_AVAILABLE = True
    logger.info("Deploy shop loaded successfully")
except Exception as e:
    logger.error(f"Deploy shop not available: {e}")
    DEPLOY_AVAILABLE = False
    def build_and_host(product_id, description, images, title, price): return f"https://neethi-saarathi-ids.web.app/product/{product_id}.html"
    def update_products_json(data): pass
    def get_all_products(): return []
    def get_product_by_id(product_id): return None
    def update_seller_profile(phone, profile_data): pass
    def get_seller_profile(phone): return None
    def add_reel(reel_data): pass
    def get_all_reels(): return []
    def create_shop_index(): pass
    def deploy_to_firebase(): return True

try:
    from ship import create_label
    SHIPPING_AVAILABLE = True
    logger.info("Shipping helper loaded successfully")
except Exception as e:
    logger.error(f"Shipping helper not available: {e}")
    SHIPPING_AVAILABLE = False
    def create_label(buyer_name, buyer_addr): return {
        "awb": f"DL{os.urandom(4).hex().upper()}",
        "label_url": "https://demo.delhivery.com/label/sample",
        "tracking_url": "https://demo.delhivery.com/track/"
    }

try:
    from sms import send_tracking
    SMS_AVAILABLE = True
    logger.info("SMS helper loaded successfully")
except Exception as e:
    logger.error(f"SMS helper not available: {e}")
    SMS_AVAILABLE = False
    def send_tracking(to, awb): print(f"Tracking sent to {to}: {awb}")

# Utility functions
def download_twilio_media(media_url):
    """Download media from Twilio (thread-safe with better error handling)"""
    try:
        twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")
        
        logger.info(f"Twilio SID available: {bool(twilio_sid)}")
        logger.info(f"Twilio Token available: {bool(twilio_token)}")
        
        if not twilio_sid or not twilio_token:
            logger.error("Twilio credentials missing from environment variables")
            # Try to get from app context as fallback
            try:
                twilio_sid = getattr(app, 'twilio_sid', None)
                twilio_token = getattr(app, 'twilio_token', None)
                logger.info(f"Fallback SID: {bool(twilio_sid)}, Token: {bool(twilio_token)}")
            except:
                pass
            
            if not twilio_sid or not twilio_token:
                raise Exception("Twilio credentials not configured in environment variables")
        
        response = requests.get(media_url, auth=HTTPBasicAuth(twilio_sid, twilio_token))
        response.raise_for_status()
        return response.content
        
    except Exception as e:
        logger.error(f"Twilio media download failed: {str(e)}")
        raise Exception(f"Failed to download media: {str(e)}")

def save_image(content, filename):
    """Save image to temporary file"""
    os.makedirs("temp_images", exist_ok=True)
    filepath = f"temp_images/{filename}"
    with open(filepath, "wb") as f:
        f.write(content)
    return filepath

def save_video(content, filename):
    """Save video to temporary file"""
    os.makedirs("temp_videos", exist_ok=True)
    filepath = f"temp_videos/{filename}"
    with open(filepath, "wb") as f:
        f.write(content)
    return filepath

def get_product(product_id):
    """Get product data from products.json"""
    try:
        if DEPLOY_AVAILABLE:
            return get_product_by_id(product_id)
        
        # FIXED: Change from "../shop/out/products.json" to "out/products.json"
        products_file = "out/products.json"
        if os.path.exists(products_file):
            with open(products_file, "r") as f:
                data = json.load(f)
                for product in data.get("products", []):
                    if product.get("id") == product_id:
                        return product
        return None
    except:
        return None

def update_product(product_id, field, value):
    """Update product in products.json"""
    try:
        # FIXED: Change from "../shop/out/products.json" to "out/products.json"
        products_file = "out/products.json"
        
        # Ensure directory exists
        os.makedirs("out", exist_ok=True)
        
        # Read existing products or create empty array
        if os.path.exists(products_file):
            try:
                with open(products_file, "r") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = {"products": []}
        else:
            data = {"products": []}
        
        # Find and update product
        updated = False
        for product in data.get("products", []):
            if product.get("id") == product_id:
                product[field] = value
                updated = True
                break
        
        if updated:
            with open(products_file, "w") as f:
                json.dump(data, f, indent=2)
            return True
        return False
        
    except Exception as e:
        logger.error(f"Update product error: {e}")
        return False

# Command handlers
def handle_edit_command(phone_number, message, media_url=None):
    """Handle edit commands from WhatsApp"""
    try:
        parts = message.strip().split()
        if len(parts) < 4 and not media_url:
            return "Usage: edit PRODUCT_ID FIELD VALUE\nExample: edit abc123 price 500\n\nFields: price, description, image, title, category"
        
        product_id = parts[1]
        field = parts[2].lower() if len(parts) > 2 else "image"
        value = " ".join(parts[3:]) if len(parts) > 3 else ""
        
        # Handle different field types
        if field == "price":
            if not value.isdigit():
                return "❌ Price must be a number. Example: edit abc123 price 500"
            success = update_product(product_id, "price", int(value))
            
        elif field == "description":
            success = update_product(product_id, "description", value)
            
        elif field == "title":
            success = update_product(product_id, "title", value)
            
        elif field == "category":
            success = update_product(product_id, "category", value)
            
        elif field == "image" and media_url:
            # Download and process new image
            image_content = download_twilio_media(media_url)
            image_filename = f"{uuid.uuid4().hex}.jpg"
            image_path = save_image(image_content, image_filename)
            
            if IMAGEN_AVAILABLE:
                image_urls = remove_bg_and_upload(image_path)
            else:
                image_urls = [f"https://storage.googleapis.com/craftlink-images/fallback{i}.jpg" for i in range(1,5)]
                
            success = update_product(product_id, "images", image_urls)
            
        elif field == "image":
            return "❌ Please send an image with the edit command: edit PRODUCT_ID image"
            
        else:
            return "❌ Invalid field. Use: price, description, title, category, or image"
        
        if success:
            # Redeploy the shop with updated product
            product_data = get_product(product_id)
            if product_data:
                if DEPLOY_AVAILABLE:
                    build_and_host(product_id, product_data.get('description', ''), product_data.get('images', []), product_data.get('title', ''), product_data.get('price', 350))
                    # Auto-deploy to Firebase
                    deploy_to_firebase()
                else:
                    build_and_host(product_id, product_data.get('description', ''), product_data.get('images', []), product_data.get('title', ''), product_data.get('price', 350))
            return f"✅ Updated {field} for product {product_id[:8]}"
        else:
            return "❌ Product not found. Check the product ID."
            
    except Exception as e:
        logger.error(f"Edit command error: {e}")
        return f"❌ Error: {str(e)}"

def handle_myproducts_command(phone_number):
    """Send user their product list"""
    try:
        products_file = "products.json"
        if not os.path.exists(products_file):
            return "You don't have any products yet. Send a photo to create your first shop!"
        
        with open(products_file, "r") as f:
            data = json.load(f)
        
        user_products = []
        user_phone = phone_number.replace("whatsapp:", "")
        
        for product in data.get("products", []):
            # Simple user matching by phone number pattern
            if user_phone in product.get("id", "") or user_phone in product.get("user_phone", ""):
                user_products.append(product)
        
        if not user_products:
            return "You don't have any products yet. Send a photo to create your first shop!"
        
        response = "📋 Your Products:\n\n"
        for product in user_products[-5:]:  # Show last 5 products
            response += f"🆔 {product['id'][:8]}...\n"
            response += f"📦 {product.get('title', 'Handmade Craft')}\n"
            response += f"💰 ₹{product.get('price', 350)}\n"
            response += f"📂 {product.get('category', 'handmade').title()}\n"
            response += f"🔗 https://neethi-saarathi-ids.web.app/product/{product['id']}.html\n"
            response += "━━━━━━━━━━━━━━━━━━━━\n"
        
        response += "\nTo edit: 'edit PRODUCT_ID field value'\nExample: 'edit abc123 price 500'"
        return response
        
    except Exception as e:
        logger.error(f"MyProducts error: {e}")
        return "❌ Error fetching your products. Please try again later."

def handle_profile_command(phone_number, message):
    """Handle profile setup and updates"""
    try:
        parts = message.strip().split()
        user_phone = phone_number.replace("whatsapp:", "")
        
        if len(parts) < 2:
            # Show current profile
            profile = get_seller_profile(user_phone)
            if profile:
                response = "👤 Your Profile:\n\n"
                response += f"Name: {profile.get('name', 'Not set')}\n"
                response += f"Region: {profile.get('region', 'Not set')}\n"
                response += f"Bio: {profile.get('bio', 'Not set')}\n"
                response += f"Skills: {', '.join(profile.get('skills', []))}\n"
                response += "\nTo update: profile set name Your Name"
            else:
                response = "You don't have a profile yet. Set up your profile with:\n\n"
                response += "profile set name Your Name\n"
                response += "profile set region Your Region\n"
                response += "profile set bio Your Bio\n"
                response += "profile set skills skill1, skill2, skill3"
            return response
        
        if parts[1] == "set" and len(parts) >= 4:
            field = parts[2].lower()
            value = " ".join(parts[3:])
            
            profile = get_seller_profile(user_phone) or {}
            
            if field == "name":
                profile["name"] = value
            elif field == "region":
                profile["region"] = value
            elif field == "bio":
                profile["bio"] = value
            elif field == "skills":
                profile["skills"] = [skill.strip() for skill in value.split(",")]
            else:
                return "❌ Invalid field. Use: name, region, bio, or skills"
            
            update_seller_profile(user_phone, profile)
            return f"✅ Profile {field} updated successfully!"
        
        return "❌ Invalid profile command. Use: profile or profile set FIELD VALUE"
            
    except Exception as e:
        logger.error(f"Profile command error: {e}")
        return f"❌ Error: {str(e)}"

def process_image_background(media_url, phone_number):
    """Process image in background thread with proper app context"""
    with app.app_context():
        try:
            logger.info(f"Background processing started for {phone_number}")
            
            # Get Twilio credentials
            twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
            twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")
            
            if not twilio_sid or not twilio_token:
                logger.error("Twilio credentials not available in app context")
                # Try to send error message
                try:
                    temp_client = Client(os.environ.get("TWILIO_ACCOUNT_SID"), os.environ.get("TWILIO_AUTH_TOKEN"))
                    if temp_client:
                        temp_client.messages.create(
                            body="⚠️ Server configuration error. Please contact support.",
                            from_="whatsapp:+14155238886",
                            to=phone_number
                        )
                except:
                    pass
                return
            
            twilio_client = Client(twilio_sid, twilio_token)
            
            # Download the image
            image_content = download_twilio_media(media_url)
            image_filename = f"{uuid.uuid4().hex}.jpg"
            image_path = save_image(image_content, image_filename)
            logger.info(f"Image saved to: {image_path}")
            
            # Step 1: Analyze with Gemini
            try:
                if GEMINI_AVAILABLE:
                    analysis = describe_image(image_path)
                    # Extract title, price and category from analysis
                    title = extract_title_from_description(analysis)
                    price = extract_price_from_description(analysis)
                    category = extract_category_from_description(analysis)
                else:
                    analysis = "Beautiful handmade craft with traditional artistry. Price band: ₹250-400 #handmade #craft #artisan"
                    title = "Beautiful Handmade Craft"
                    price = 350
                    category = "handmade"
                logger.info(f"Analysis complete: {analysis[:100]}...")
                
                # Send analysis first
                twilio_client.messages.create(
                    body=analysis,
                    from_="whatsapp:+14155238886",
                    to=phone_number
                )
            except Exception as e:
                logger.error(f"Analysis error: {e}")
                analysis = "Beautiful handmade craft with traditional artistry. Price band: ₹250-400 #handmade #craft #artisan"
                title = "Beautiful Handmade Craft"
                price = 350
                category = "handmade"
                twilio_client.messages.create(
                    body=analysis,
                    from_="whatsapp:+14155238886",
                    to=phone_number
                )
            
            # Step 2: Process image
            try:
                if IMAGEN_AVAILABLE:
                    image_urls = remove_bg_and_upload(image_path)
                else:
                    image_urls = [f"https://storage.googleapis.com/craftlink-images/fallback{i}.jpg" for i in range(1,5)]
                logger.info(f"Image processing complete: {len(image_urls)} URLs")
            except Exception as e:
                logger.error(f"Image processing failed: {e}")
                image_urls = [f"https://storage.googleapis.com/craftlink-images/fallback{i}.jpg" for i in range(1,5)]
            
            # Step 3: Generate shop URL
            product_id = str(uuid.uuid4())
            try:
                if DEPLOY_AVAILABLE:
                    shop_url = build_and_host(product_id, analysis, image_urls, title, price)
                else:
                    shop_url = f"https://neethi-saarathi-ids.web.app/product/{product_id}.html"
                logger.info(f"Shop URL generated: {shop_url}")
            except Exception as e:
                logger.error(f"Deployment failed: {e}")
                shop_url = f"https://neethi-saarathi-ids.web.app/product/{product_id}.html"
            
            # Get seller profile
            user_phone = phone_number.replace("whatsapp:", "")
            seller_profile = get_seller_profile(user_phone) or {}
            
            # Update products.json with user reference
            product_data = {
                "id": product_id,
                "title": title,
                "description": analysis,
                "price": price,
                "images": image_urls,
                "category": category,
                "artisan_name": seller_profile.get("name", "Local Artisan"),
                "artisan_region": seller_profile.get("region", "India"),
                "artisan_phone": user_phone,
                "created_at": datetime.now().isoformat(),
                "user_phone": user_phone,
                "rating": round(4.5 + (uuid.uuid4().int % 5) / 10, 1),
                "reviews_count": uuid.uuid4().int % 25,
                "orders_completed": uuid.uuid4().int % 50,
                "in_stock": True
            }
            update_products_json(product_data)
            
            # Update shop index to include new product
            if DEPLOY_AVAILABLE:
                create_shop_index()
                # Auto-deploy to Firebase
                deploy_to_firebase()
            
            # Send shop link
            twilio_client.messages.create(
                body=f"🛍️ Your shop is ready: {shop_url}",
                from_="whatsapp:+14155238886",
                to=phone_number
            )
            
            # Send final message with edit instructions
            twilio_client.messages.create(
                body=f"📦 We'll help you with shipping and payments!\n\nTo edit this product later:\n• edit {product_id[:8]} price NEW_PRICE\n• edit {product_id[:8]} description \"NEW_DESCRIPTION\"\n• edit {product_id[:8]} title \"NEW_TITLE\"\n• edit {product_id[:8]} category NEW_CATEGORY\n• edit {product_id[:8]} image + send new photo\n• Type 'myproducts' to see all your items\n• Type 'profile' to manage your seller profile",
                from_="whatsapp:+14155238886",
                to=phone_number
            )
            
            logger.info(f"Background processing completed for {phone_number}")
            
        except Exception as e:
            logger.error(f"Background processing error: {e}")
            logger.error(traceback.format_exc())
            # Send error message
            try:
                # Try to create a new client for error message
                error_client = Client(os.environ.get("TWILIO_ACCOUNT_SID"), os.environ.get("TWILIO_AUTH_TOKEN"))
                if error_client:
                    error_client.messages.create(
                        body="⚠️ Sorry, I encountered an error processing your image. Please try again.",
                        from_="whatsapp:+14155238886",
                        to=phone_number
                    )
            except Exception as send_error:
                logger.error(f"Failed to send error message: {send_error}")

def process_video_background(media_url, phone_number, caption=""):
    """Process video in background for reels"""
    try:
        logger.info(f"Background video processing started for {phone_number}")
        
        # Get fresh Twilio client for this thread
        twilio_client = get_twilio_client()
        
        # Download the video
        video_content = download_twilio_media(media_url)
        video_filename = f"{uuid.uuid4().hex}.mp4"
        video_path = save_video(video_content, video_filename)
        logger.info(f"Video saved to: {video_path}")
        
        # Upload video
        try:
            if IMAGEN_AVAILABLE:
                video_url = upload_video(video_path)
            else:
                video_url = "https://storage.googleapis.com/craftlink-videos/fallback.mp4"
            logger.info(f"Video uploaded: {video_url}")
        except Exception as e:
            logger.error(f"Video upload failed: {e}")
            video_url = "https://storage.googleapis.com/craftlink-videos/fallback.mp4"
        
        # Get seller profile
        user_phone = phone_number.replace("whatsapp:", "")
        seller_profile = get_seller_profile(user_phone) or {}
        
        # Create reel data
        reel_id = str(uuid.uuid4())
        reel_data = {
            "id": reel_id,
            "video_url": video_url,
            "caption": caption,
            "seller_name": seller_profile.get("name", "Local Artisan"),
            "seller_region": seller_profile.get("region", "India"),
            "seller_phone": user_phone,
            "created_at": datetime.now().isoformat(),
            "likes": random.randint(5, 100),
            "comments": random.randint(0, 20)
        }
        
        # Add to reels
        add_reel(reel_data)
        
        # Update shop index to include new reel
        if DEPLOY_AVAILABLE:
            create_shop_index()
            # Auto-deploy to Firebase
            deploy_to_firebase()
        
        # Send confirmation
        if twilio_client:
            twilio_client.messages.create(
                body=f"🎥 Your video has been added to our reels section! View it on the website.",
                from_="whatsapp:+14155238886",
                to=phone_number
            )
        
        logger.info(f"Background video processing completed for {phone_number}")
        
    except Exception as e:
        logger.error(f"Background video processing error: {e}")
        logger.error(traceback.format_exc())
        # Send error message
        try:
            twilio_client = get_twilio_client()
            if twilio_client:
                twilio_client.messages.create(
                    body="⚠️ Sorry, I encountered an error processing your video. Please try again.",
                    from_="whatsapp:+14155238886",
                    to=phone_number
                )
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")

# Flask Routes
@app.route('/whatsapp', methods=['POST'])
def whatsapp_reply():
    try:
        # Get form data
        Body = request.form.get('Body', '')
        NumMedia = request.form.get('NumMedia', '0')
        MediaUrl0 = request.form.get('MediaUrl0')
        MediaContentType0 = request.form.get('MediaContentType0')
        From = request.form.get('From', '')
        
        logger.info(f"Message from {From}: Body='{Body}', MediaCount={NumMedia}")
        
        resp = MessagingResponse()
        phone_number = From
        message_body = Body.strip().lower()
        
        # Handle commands
        if message_body.startswith("edit"):
            logger.info(f"Processing edit command: {Body}")
            if NumMedia != "0" and MediaUrl0:
                response_text = handle_edit_command(phone_number, Body, MediaUrl0)
            else:
                response_text = handle_edit_command(phone_number, Body)
            resp.message(response_text)
            
        elif message_body in ["myproducts", "mylist", "my items", "myproducts"]:
            logger.info(f"Processing myproducts command: {Body}")
            response_text = handle_myproducts_command(From)
            resp.message(response_text)
            
        elif message_body.startswith("profile"):
            logger.info(f"Processing profile command: {Body}")
            response_text = handle_profile_command(From, Body)
            resp.message(response_text)
            
        elif message_body.startswith("reel"):
            logger.info(f"Processing reel command: {Body}")
            if NumMedia != "0" and MediaUrl0 and MediaContentType0 and "video" in MediaContentType0:
                caption = Body[4:].strip() if len(Body) > 4 else ""
                # Send immediate response
                resp.message("🎥 Processing your video for reels...")
                # Process video in background
                thread = Thread(target=process_video_background, args=(MediaUrl0, From, caption))
                thread.daemon = True
                thread.start()
            else:
                resp.message("❌ Please send a video with the reel command. Example: reel Check out my new craft!")
            
        elif message_body in ["categories", "category", "filter"]:
            logger.info(f"Processing categories command: {Body}")
            response_text = "🏷️ Available Categories:\n\n• pottery\n• textiles\n• jewelry\n• paintings\n• wooden\n• metalwork\n• leather\n• papercraft\n• home-decor\n• accessories\n\nUse: edit PRODUCT_ID category CATEGORY_NAME"
            resp.message(response_text)
            
        elif NumMedia != "0" and MediaUrl0:
            # Check if it's a video
            if MediaContentType0 and "video" in MediaContentType0:
                logger.info(f"Processing video: {MediaUrl0}")
                resp.message("🎥 Got your video! Would you like to add it to reels? Reply 'reel' followed by a caption to add it.")
            else:
                logger.info(f"Processing image: {MediaUrl0}")
                # Send immediate response to prevent timeout
                resp.message("📸 Got your image! Processing it now with AI... I'll send the analysis and shop link in a moment.")
                # Process image in background
                thread = Thread(target=process_image_background, args=(MediaUrl0, From))
                thread.daemon = True
                thread.start()
            
        else:
            if message_body in ["hi", "hello", "hey", "start", "नमस्ते"]:
                welcome_msg = """👋 नमस्ते! Welcome to KalaaSaarathi!

Send me a photo of your handmade craft and I'll:
1. 📸 Analyze it with AI
2. 🛍️ Create an online shop
3. 📊 Suggest a fair price
4. 📦 Help with shipping

Commands:
• myproducts - List your items
• categories - Show available categories
• profile - View/update your seller profile
• reel CAPTION + video - Add to reels
• edit PRODUCT_ID price 500 - Change price
• edit PRODUCT_ID description "New text" - Update description
• edit PRODUCT_ID title "New title" - Update title
• edit PRODUCT_ID category pottery - Change category
• edit PRODUCT_ID image + send photo - Change image

Just send a photo to get started!"""
                resp.message(welcome_msg)
            else:
                resp.message("📸 Please send a photo of your craft to get started! I'll analyze it and create a shop for you.\n\nType 'help' for commands.")

        return Response(str(resp), mimetype='text/xml')
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        logger.error(traceback.format_exc())
        resp = MessagingResponse()
        resp.message("⚠️ Sorry, I encountered an error. Please try sending the photo again.")
        return Response(str(resp), mimetype='text/xml')

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy", 
        "service": "KalaaSaarathi WhatsApp API",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "gemini": GEMINI_AVAILABLE,
            "image_processing": IMAGEN_AVAILABLE,
            "deployment": DEPLOY_AVAILABLE,
            "shipping": SHIPPING_AVAILABLE,
            "sms": SMS_AVAILABLE
        }
    })

@app.route('/')
def home():
    return "✅ KalaaSaarathi Server is Running! Visit /whatsapp for WhatsApp webhook"

# Additional API endpoints
@app.route('/api/products', methods=['GET'])
def get_products():
    category = request.args.get('category')
    artisan = request.args.get('artisan')
    search = request.args.get('search')
    
    try:
        if DEPLOY_AVAILABLE:
            products = get_all_products()
        else:
            products_file = "products.json"
            if os.path.exists(products_file):
                with open(products_file, "r") as f:
                    data = json.load(f)
                    products = data.get("products", [])
            else:
                products = []
        
        # Filter by category if provided
        if category:
            products = [p for p in products if p.get("category") == category]
        
        # Filter by artisan if provided
        if artisan:
            products = [p for p in products if p.get("artisan_phone") == artisan]
        
        # Search by title or description
        if search:
            search_lower = search.lower()
            products = [p for p in products 
                       if search_lower in p.get("title", "").lower() 
                       or search_lower in p.get("description", "").lower()]
        
        return jsonify({"products": products})
    except Exception as e:
        logger.error(f"Error loading products: {e}")
        return jsonify({"products": []})

@app.route('/api/products/<product_id>', methods=['GET'])
def get_product_api(product_id):
    try:
        product = get_product(product_id)
        if product:
            return jsonify({
                "success": True,
                "product": product
            })
        else:
            return jsonify({"success": False, "error": "Product not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": f"Error fetching product: {str(e)}"}), 500

@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = [
        "pottery", "textiles", "jewelry", "paintings", "wooden",
        "metalwork", "leather", "papercraft", "home-decor", "accessories"
    ]
    return jsonify({"categories": categories})

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    return jsonify({"message": "API is working!", "timestamp": datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)