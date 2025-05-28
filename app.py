import os
import requests
import base64
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Daraja API credentials (set in Railway variables)
CONSUMER_KEY = os.getenv("CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")
SHORTCODE = os.getenv("SHORTCODE")
PASSKEY = os.getenv("PASSKEY")

# Helper function to get access token
def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    auth_str = f"{CONSUMER_KEY}:{CONSUMER_SECRET}"
    auth_encoded = base64.b64encode(auth_str.encode()).decode()
    headers = {"Authorization": f"Basic {auth_encoded}"}
    response = requests.get(url, headers=headers)
    return response.json().get("access_token")

# Homepage - Booking Form
@app.route('/')
def index():
    return render_template('index.html')

# Initiate M-Pesa Payment
@app.route('/pay', methods=['POST'])
def pay():
    try:
        phone = request.form.get('phone')
        amount = request.form.get('amount')
        
        # Format phone (e.g., 0722... → 254722...)
        if phone.startswith("0"):
            phone = f"254{phone[1:]}"

        # Prepare STK push
        access_token = get_access_token()
        url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(f"{SHORTCODE}{PASSKEY}{timestamp}".encode()).decode()

        payload = {
            "BusinessShortCode": SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": SHORTCODE,
            "PhoneNumber": phone,
            "CallBackURL": "https://ambururu.up.railway.app/callback",  # Railway URL
            "AccountReference": "AmbururuBooking",
            "TransactionDesc": "Booking Payment"
        }

        response = requests.post(url, headers=headers, json=payload)
        if response.json().get("ResponseCode") == "0":
            return redirect(url_for('payment_pending'))
        else:
            return "Payment initiation failed. Please try again."
    except Exception as e:
        return f"Error: {str(e)}"

# Payment Pending Page
@app.route('/payment-pending')
def payment_pending():
    return render_template('payment.html')

# M-Pesa Callback Handler
@app.route('/callback', methods=['POST'])
def callback():
    try:
        data = request.get_json()
        result = data.get("Body", {}).get("stkCallback", {})
        
        if result.get("ResultCode") == 0:
            metadata = result.get("CallbackMetadata", {}).get("Item", [])
            amount = next(item["Value"] for item in metadata if item["Name"] == "Amount")
            mpesa_code = next(item["Value"] for item in metadata if item["Name"] == "MpesaReceiptNumber")
            phone = next(item["Value"] for item in metadata if item["Name"] == "PhoneNumber")
            
            # Save to database (add your logic here)
            print(f"✅ Payment successful! Amount: {amount}, Phone: {phone}, M-Pesa Code: {mpesa_code}")
        else:
            error = result.get("ResultDesc")
            print(f"❌ Payment failed: {error}")

        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})
    except Exception as e:
        print(f"⚠️ Callback error: {str(e)}