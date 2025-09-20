from twilio.rest import Client
import os

client = Client(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN"))

def send_tracking(to: str, awb: str):
    """Send tracking information via WhatsApp"""
    try:
        message = client.messages.create(
            body=f"आपका ऑर्डर भेज दिया गया है। ट्रैकिंग: {awb}",
            from_="whatsapp:+14155238886",
            to=f"whatsapp:{to}"
        )
        print(f"Tracking sent: {message.sid}")
    except Exception as e:
        print(f"Failed to send tracking: {e}")