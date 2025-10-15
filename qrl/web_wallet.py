#!/usr/bin/env python3

import os
import qrcode
import io
import base64
import json
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from time import time
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, make_response, g
from flask_cors import CORS  # Add this import
import jwt
from functools import wraps
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, validators, PasswordField
from web3 import Web3
from eth_account.messages import encode_defunct, _hash_eip191_message
from eth_account import Account
import secrets
from markupsafe import Markup
import markdown
import re
import html as html_lib

# Quantum-resistant cryptography
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()
from qrl.services.node_service import NodeService
from qrl.core.transaction import Transaction
from qrl.config import VERSION, TARGET_BLOCK_TIME, INITIAL_MINING_REWARD
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf

# Configure dedicated data directory for web wallet
WEB_WALLET_DATA_DIR = os.getenv('WEB_WALLET_DATA_DIR')
if not WEB_WALLET_DATA_DIR:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    WEB_WALLET_DATA_DIR = os.path.join(project_root, '.web_wallet_data')
WEB_WALLET_DATA_DIR = os.path.abspath(WEB_WALLET_DATA_DIR)
os.makedirs(WEB_WALLET_DATA_DIR, exist_ok=True)

# Initialize Flask app
app = Flask(__name__)
app.config.setdefault('WTF_CSRF_TIME_LIMIT', 3600)
app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Strict')
app.config.setdefault('SESSION_COOKIE_SECURE', False)
app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)

csrf = CSRFProtect()
csrf.init_app(app)

# Configure CORS to allow credentials
CORS(app, 
     resources={
         r"/web3/*": {
             "origins": ["http://localhost:5001", "http://127.0.0.1:5001"],
             "supports_credentials": True
         }
     })

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("qrl.web_wallet")

RATE_LIMIT_SETTINGS = {
    'web3_init': (10, 60),
    'web3_verify': (10, 60),
    'mine': (5, 60),
}
_rate_limit_buckets: dict[tuple[str, str], deque] = defaultdict(deque)

def is_rate_limited(bucket_key: str, identifier: str) -> bool:
    limit, window = RATE_LIMIT_SETTINGS.get(bucket_key, (20, 60))
    now = time()
    bucket = _rate_limit_buckets[(bucket_key, identifier)]
    while bucket and bucket[0] <= now - window:
        bucket.popleft()
    if len(bucket) >= limit:
        return True
    bucket.append(now)
    return False

def client_identifier() -> str:
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote_addr or 'unknown'

def enforce_rate_limit(bucket_key: str):
    identifier = client_identifier()
    if is_rate_limited(bucket_key, identifier):
        logger.warning("Rate limit exceeded for %s by %s", bucket_key, identifier)
        return jsonify({'error': 'Too many requests, please slow down.'}), 429
    return None

@app.context_processor
def inject_security_context():
    return {'csp_nonce': getattr(g, 'csp_nonce', '')}

@app.before_request
def assign_security_nonce():
    g.csp_nonce = secrets.token_urlsafe(16)


def is_secure_request() -> bool:
    """Detect if the current request should be treated as secure (HTTPS)."""
    if request.is_secure:
        return True
    forwarded_proto = (request.headers.get('X-Forwarded-Proto') or '').lower()
    if forwarded_proto.startswith('https'):
        return True
    forwarded_ssl = (request.headers.get('X-Forwarded-Ssl') or '').lower()
    if forwarded_ssl == 'on':
        return True
    return False


@app.after_request
def apply_security_headers(response):
    csrf_token = generate_csrf()
    response.set_cookie(
        'XSRF-TOKEN',
        csrf_token,
        secure=is_secure_request(),
        samesite='Strict',
        httponly=False,
        path='/'
    )
    nonce = getattr(g, 'csp_nonce', secrets.token_urlsafe(16))
    csp = (
        "default-src 'self'; "
        f"script-src 'self' https://cdn.jsdelivr.net 'nonce-{nonce}'; "
        "style-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "font-src 'self' https://cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    response.headers['Content-Security-Policy'] = csp
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin'
    return response

# Generate a fixed secret key if not set in environment
DEFAULT_SECRET_KEY = 'qrl-wallet-secret-key-123'  # In production, always set SECRET_KEY in environment
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', DEFAULT_SECRET_KEY)

# Configure session cookie
app.config.update(
    SESSION_COOKIE_SAMESITE='Strict',
    SESSION_COOKIE_SECURE=False,  # Set True behind HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_DURATION=timedelta(hours=12)
)

# Quantum-resistant password hashing
ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16)

# JWT Configuration - Use the same secret key as Flask's secret key for consistency
JWT_SECRET_KEY = app.config['SECRET_KEY']
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DELTA = timedelta(hours=6)
JWT_AUDIENCE = 'qrl-web'
JWT_ISSUER = 'qrl-wallet'

print(f"Using JWT secret key: {JWT_SECRET_KEY[:5]}...")  # Log first 5 chars for debugging

# Demo balance store for simulated purchases
demo_balances = {}

# In-memory user store (needed for Web3 callbacks)
users_db = {}

# Web3 Configuration
WEB3_NETWORK = os.getenv('WEB3_NETWORK', 'http://localhost:8545')
w3 = Web3(Web3.HTTPProvider(WEB3_NETWORK))

# Nonce store for Web3 login
web3_nonces = {}

# Auto-mine and seed balance configuration
AUTO_MINE_ON_SEND = os.getenv('AUTO_MINE_ON_SEND', 'true').lower() in ('1', 'true', 'yes')
SEED_BALANCE_QRL = float(os.getenv('SEED_BALANCE_QRL', '0'))

# Message template for Web3 login
WEB3_LOGIN_MESSAGE = """Welcome to QRL Web Wallet!

Sign this message to login to your account.

Nonce: {nonce}"""

@app.context_processor
def inject_auth_context():
    """Inject auth details into all templates for UI logic in base.html."""
    try:
        token = request.cookies.get('auth_token')
        is_logged_in = False
        username = None
        wallet_address = None
        if token:
            payload = verify_jwt_token(token)
            if payload:
                is_logged_in = True
                username = payload.get('username')
                wallet_address = payload.get('wallet_address')
        return dict(is_logged_in=is_logged_in, username=username, wallet_address=wallet_address)
    except Exception:
        # Fail-safe: don't break template rendering
        return dict(is_logged_in=False, username=None, wallet_address=None)

class User:
    def __init__(self, username: str, password_hash: str = None, wallet_address: str = None, is_web3: bool = False):
        self.username = username
        self.password_hash = password_hash
        self.wallet_address = wallet_address
        self.is_web3 = is_web3
        self.created_at = datetime.now(timezone.utc)
        self.last_login = None
        
    def set_password(self, password):
        if self.is_web3:
            raise ValueError("Cannot set password for Web3 user")
        self.password_hash = ph.hash(password)
        
    def check_password(self, password):
        if self.is_web3:
            raise ValueError("Web3 users authenticate with wallet signature")
        try:
            return ph.verify(self.password_hash, password)
        except VerifyMismatchError:
            return False

def create_jwt_token(user):
    now = datetime.now(timezone.utc)
    payload = {
        'username': user.username,
        'wallet_address': user.wallet_address,
        'is_web3': user.is_web3,
        'exp': now + JWT_EXPIRATION_DELTA,
        'iat': now,
        'nbf': now - timedelta(seconds=5),
        'aud': JWT_AUDIENCE,
        'iss': JWT_ISSUER,
        'sub': user.username
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token):
    try:
        if not token:
            print("No token provided")
            return None
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER
        )
        print(f"Token verified for user: {payload.get('username')}")
        return payload
    except jwt.ExpiredSignatureError as e:
        print(f"Token expired: {str(e)}")
        return None
    except jwt.InvalidTokenError as e:
        print(f"Invalid token: {str(e)}")
        return None
    except Exception as e:
        print(f"Error verifying token: {str(e)}")
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('auth_token')
        if not token or not verify_jwt_token(token):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Initialize node service with isolated data directory
QRL_LIVE_MODE = os.getenv('QRL_LIVE_MODE', 'false').lower() in ('1', 'true', 'yes')
node_service = NodeService(data_dir=WEB_WALLET_DATA_DIR, live_mode=QRL_LIVE_MODE)

# Forms
class LoginForm(FlaskForm):
    username = StringField('Username', [validators.DataRequired()])
    password = PasswordField('Password', [validators.DataRequired()])

class RegistrationForm(FlaskForm):
    username = StringField('Username', [validators.DataRequired(), validators.Length(min=4, max=25)])
    password = PasswordField('New Password', [validators.DataRequired(), validators.EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password')

class TransferForm(FlaskForm):
    recipient = StringField('Recipient Address', [validators.DataRequired()])
    amount = FloatField('Amount (QRL)', [validators.NumberRange(min=0.000001), validators.DataRequired()])

    def validate_recipient(self, field):
        addr = (field.data or '').strip()
        def is_eth(s: str) -> bool:
            return isinstance(s, str) and s.lower().startswith('0x') and len(s) == 42 and all(c in '0123456789abcdef' for c in s[2:].lower())
        def is_qrl(s: str) -> bool:
            return isinstance(s, str) and s.startswith('Q') and 40 <= len(s) <= 70
        if not (is_eth(addr) or is_qrl(addr)):
            raise validators.ValidationError('Invalid address format. Enter a QRL address or 0x-address.')

@app.template_filter('datetime')
def format_datetime(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

@app.route('/')
def index():
    blockchain_info = node_service.get_blockchain_info()

    # Derive QRL-specific metrics
    chain = node_service.blockchain.chain if node_service.blockchain else []
    chain_height = max(len(chain) - 1, 0)

    total_supply = 0.0
    chart_points = []
    for block in chain:
        reward = 0.0
        for tx in getattr(block, 'transactions', []):
            if getattr(tx, 'sender', None) == "0":
                reward += float(getattr(tx, 'amount', 0.0) or 0.0)
        total_supply += reward
        chart_points.append({
            'label': f"#{block.index}",
            'height': block.index,
            'reward': reward,
            'supply': total_supply,
            'timestamp': block.timestamp
        })

    current_reward = float(blockchain_info.get('mining_reward', node_service.blockchain.mining_reward if node_service.blockchain else 0.0))
    difficulty = blockchain_info.get('difficulty', node_service.blockchain.difficulty if node_service.blockchain else 0)
    pending_txs = blockchain_info.get('pending_transactions', len(node_service.blockchain.pending_transactions) if node_service.blockchain else 0)
    halving_interval = blockchain_info.get('halving_interval', node_service.blockchain.halving_interval if node_service.blockchain else 0)

    if halving_interval and halving_interval > 0:
        next_halving = ((chain_height // halving_interval) + 1) * halving_interval
        blocks_until_halving = max(next_halving - chain_height, 0)
    else:
        next_halving = None
        blocks_until_halving = None

    last_block_time = None
    if chain:
        last_block_time = datetime.fromtimestamp(chain[-1].timestamp).strftime('%Y-%m-%d %H:%M:%S')

    recent_points = chart_points[-20:] if chart_points else []
    chart_labels = [point['label'] for point in recent_points]
    chart_rewards = [round(point['reward'], 8) for point in recent_points]
    chart_supply = [round(point['supply'], 8) for point in recent_points]

    if not chart_labels:
        chart_labels = ["Genesis"]
        chart_rewards = [0.0]
        chart_supply = [0.0]

    market_stats = [
        {"label": "Network", "value": "QRL Mainnet" if QRL_LIVE_MODE else "QRL Local Devnet"},
        {"label": "Chain Height", "value": f"{chain_height:,}"},
        {"label": "Total Supply", "value": f"{total_supply:,.8f} QRL"},
        {"label": "Current Mining Reward", "value": f"{current_reward:,.8f} QRL"},
        {"label": "Initial Mining Reward", "value": f"{INITIAL_MINING_REWARD:,.2f} QRL"},
        {"label": "Difficulty", "value": str(difficulty)},
        {"label": "Pending Transactions", "value": str(pending_txs)},
        {"label": "Halving Interval", "value": f"{halving_interval:,}" if halving_interval else "Disabled"},
        {"label": "Blocks Until Halving", "value": f"{blocks_until_halving:,}" if blocks_until_halving is not None else "N/A"},
        {"label": "Next Halving Block", "value": f"{next_halving:,}" if next_halving is not None else "N/A"},
        {"label": "Target Block Time", "value": f"{TARGET_BLOCK_TIME}s"},
        {"label": "Last Block Time", "value": last_block_time or "Not yet mined"},
        {"label": "Algorithm", "value": "Proof-of-Work (XMSS)"},
        {"label": "Node Version", "value": VERSION},
    ]

    # Get wallet balance if logged in
    balance = 0.0
    address = None
    is_logged_in = False
    username = None
    sent_count = 0
    received_count = 0
    pending_sent_count = 0
    pending_received_count = 0
    recent_activity = []

    # Check for JWT token
    token = request.cookies.get('auth_token')
    if token:
        payload = verify_jwt_token(token)
        if payload:
            is_logged_in = True
            username = payload.get('username')
            address = payload.get('wallet_address')
            if address:
                balance = node_service.get_balance(address) or 0.0
                # Add demo balance if available
                if address in demo_balances:
                    balance += demo_balances[address]

                def is_eth(addr: str) -> bool:
                    return isinstance(addr, str) and addr.lower().startswith('0x') and len(addr) == 42 and all(c in '0123456789abcdef' for c in addr[2:].lower())

                def addr_eq(a: str, b: str) -> bool:
                    if is_eth(a) and is_eth(b):
                        return a.lower() == b.lower()
                    return a == b

                history = []
                for block in reversed(chain[-100:] if len(chain) > 100 else chain):
                    confirmations = len(chain) - block.index
                    for tx in getattr(block, 'transactions', []):
                        if not hasattr(tx, 'sender') or not hasattr(tx, 'recipient'):
                            continue
                        if addr_eq(tx.sender, address):
                            sent_count += 1
                            history.append({
                                'type': 'sent',
                                'tx_hash': tx.transaction_hash,
                                'amount': getattr(tx, 'amount', 0) or 0,
                                'fee': getattr(tx, 'fee', 0) or 0,
                                'timestamp': getattr(tx, 'timestamp', None),
                                'status': 'confirmed',
                                'confirmations': confirmations,
                                'counterparty': tx.recipient
                            })
                        elif addr_eq(tx.recipient, address):
                            received_count += 1
                            history.append({
                                'type': 'received',
                                'tx_hash': tx.transaction_hash,
                                'amount': getattr(tx, 'amount', 0) or 0,
                                'fee': getattr(tx, 'fee', 0) or 0,
                                'timestamp': getattr(tx, 'timestamp', None),
                                'status': 'confirmed',
                                'confirmations': confirmations,
                                'counterparty': tx.sender
                            })

                for pending_tx in node_service.mempool.get_pending_transactions():
                    if not hasattr(pending_tx, 'sender') or not hasattr(pending_tx, 'recipient'):
                        continue
                    if addr_eq(pending_tx.sender, address):
                        pending_sent_count += 1
                        history.append({
                            'type': 'sent',
                            'tx_hash': pending_tx.transaction_hash,
                            'amount': getattr(pending_tx, 'amount', 0) or 0,
                            'fee': getattr(pending_tx, 'fee', 0) or 0,
                            'timestamp': getattr(pending_tx, 'timestamp', None),
                            'status': 'pending',
                            'confirmations': 0,
                            'counterparty': pending_tx.recipient
                        })
                    elif addr_eq(pending_tx.recipient, address):
                        pending_received_count += 1
                        history.append({
                            'type': 'received',
                            'tx_hash': pending_tx.transaction_hash,
                            'amount': getattr(pending_tx, 'amount', 0) or 0,
                            'fee': getattr(pending_tx, 'fee', 0) or 0,
                            'timestamp': getattr(pending_tx, 'timestamp', None),
                            'status': 'pending',
                            'confirmations': 0,
                            'counterparty': pending_tx.sender
                        })

                history.sort(key=lambda item: item['timestamp'] or 0, reverse=True)
                recent_activity = history[:6]

    # Generate QR code for receiving
    # Prefer the logged-in Web3 wallet address if available; otherwise use local node wallet
    qr_address = address or node_service.get_wallet_address()
    
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(qr_address)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_code = base64.b64encode(buffered.getvalue()).decode()
    
    form = TransferForm()
    return render_template('index.html', 
                           address=address, 
                           balance=balance, 
                           qr_code=qr_code,
                           blockchain_info=blockchain_info,
                           market_stats=market_stats,
                           chart_labels=chart_labels,
                           chart_rewards=chart_rewards,
                           chart_supply=chart_supply,
                           is_logged_in=is_logged_in,
                           username=username,
                           wallet_address=address,
                           form=form,
                           sent_count=sent_count,
                           received_count=received_count,
                           pending_sent_count=pending_sent_count,
                           pending_received_count=pending_received_count,
                           recent_activity=recent_activity)

@app.route('/healthz')
def healthz():
    return jsonify({
        'status': 'ok',
        'timestamp': int(time())
    }), 200

@app.route('/whitepaper')
def whitepaper():
    try:
        md_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'WHITEPAPER.md')
        with open(md_path, 'r', encoding='utf-8') as f:
            md_text = f.read()
    except Exception:
        return make_response("WHITEPAPER.md not found", 404)

    html = markdown.markdown(md_text, extensions=['fenced_code', 'tables', 'toc'])
    # Convert ```mermaid code fences (rendered as <pre><code class="language-mermaid">)</code></pre>
    # into <div class="mermaid"> blocks so MermaidJS can render them.
    html = re.sub(
        r'<pre><code class="language-mermaid">(.*?)</code></pre>',
        lambda m: f'<div class="mermaid">{html_lib.unescape(m.group(1))}</div>',
        html,
        flags=re.DOTALL,
    )
    return render_template('whitepaper.html', content=Markup(html))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('login'))

    return render_template('login.html', web3_available=True)

@app.route('/web3/init-login', methods=['POST'])
def web3_init_login():
    try:
        rate_response = enforce_rate_limit('web3_init')
        if rate_response:
            return rate_response
        print("\n=== Web3 Init Login ===")
        print(f"Request data: {request.json}")
        
        wallet_address = request.json.get('wallet_address')
        if not wallet_address or not w3.is_address(wallet_address):
            print(f"Invalid wallet address: {wallet_address}")
            return jsonify({'error': 'Invalid wallet address'}), 400
        
        # Generate a secure random nonce
        nonce = secrets.token_hex(16)
        wallet_lower = wallet_address.lower()
        web3_nonces[wallet_lower] = nonce
        
        # Create signable message - ensure this matches what Phantom Wallet expects
        message = f"Sign this message to login to QRL Wallet.\n\nNonce: {nonce}"
        
        response_data = {
            'message': message,
            'nonce': nonce,
            'wallet_address': wallet_address
        }
        
        logger.info("Generated Web3 login nonce for %s", wallet_lower)
        
        return jsonify(response_data)
    except Exception as e:
        print(f"Error in web3_init_login: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/web3/verify', methods=['POST'])
def web3_verify():
    try:
        rate_response = enforce_rate_limit('web3_verify')
        if rate_response:
            return rate_response
        print("\n=== Web3 Verify Request ===")
        print(f"Request data: {request.json}")
        
        wallet_address = request.json.get('wallet_address')
        signature = request.json.get('signature')
        
        if not all([wallet_address, signature]):
            print("Error: Missing required parameters")
            return jsonify({'error': 'Missing required parameters'}), 400
        
        wallet_lower = wallet_address.lower()
        nonce = web3_nonces.get(wallet_lower)
        
        if not nonce:
            print(f"Error: No nonce found for wallet: {wallet_lower}")
            print(f"Current nonces: {web3_nonces}")
            return jsonify({'error': 'Login attempt expired or invalid. Please try again.'}), 400
        
        # Get the original message that was signed
        original_message = f"Sign this message to login to QRL Wallet.\n\nNonce: {nonce}"
        print(f"Original message: {original_message}")
        print(f"Signature: {signature}")
        
        try:
            # Standard EIP-191 (personal_sign) flow
            print("\nTrying standard EIP-191 recovery...")
            signable_message = encode_defunct(text=original_message)
            print("Prepared signable message for recovery")

            # Handle different signature formats
            if isinstance(signature, dict) and all(k in signature for k in ['r', 's', 'v']):
                print("Detected v,r,s signature format")
                v_hex = hex(signature['v'])[2:].rjust(2, '0')
                r_hex = signature['r'].hex()
                s_hex = signature['s'].hex()
                signature_hex = '0x' + r_hex + s_hex + v_hex
                print("Converted signature to hex")
                recovered_address = Account.recover_message(signable_message, signature=signature_hex)
            else:
                print("Using signature as-is")
                recovered_address = Account.recover_message(signable_message, signature=signature)

            recovered_lower = recovered_address.lower()
            print(f"Recovered address: {recovered_lower}, Expected: {wallet_lower}")

            if recovered_lower != wallet_lower:
                print("Address mismatch after recovery")
                return jsonify({'error': 'Signature verification failed (address mismatch)'}), 401

        except Exception as e:
            print(f"\nSignature verification error: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Invalid signature format: {str(e)}'}), 400
        
        # Clean up used nonce
        web3_nonces.pop(wallet_lower, None)
        
        # Find or create user
        username = f"web3_{wallet_address[:10]}"
        if username not in users_db:
            print(f"\nCreating new Web3 user: {username}")
            users_db[username] = User(
                username=username,
                wallet_address=wallet_address,
                is_web3=True
            )
            if SEED_BALANCE_QRL > 0:
                demo_balances[wallet_address] = demo_balances.get(wallet_address, 0.0) + SEED_BALANCE_QRL
                logger.info("Seeded %.6f QRL to new user %s", SEED_BALANCE_QRL, wallet_address)
        
        user = users_db[username]
        user.last_login = datetime.now(timezone.utc)
        
        # Create JWT token
        token = create_jwt_token(user)
        print(f"\nGenerated JWT token: {token}")
        
        # Create response
        response_data = {
            'success': True,
            'token': token,  # also return token so frontend can set fallback cookie if needed
            'username': user.username,
            'wallet_address': user.wallet_address,
            'redirect': url_for('index')
        }
        logger.info("Web3 login success for %s", user.username)
        
        # Create response with HTTP-only cookie
        response = make_response(jsonify(response_data))
        expires = datetime.now(timezone.utc) + JWT_EXPIRATION_DELTA

        # Set the auth token cookie
        response.set_cookie(
            key='auth_token',
            value=token,
            httponly=True,
            secure=is_secure_request(),
            samesite='Lax',
            expires=expires,
            path='/',
            domain=None
        )

        # Add CORS headers for mobile browsers
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')

        # Also add a fallback header for mobile clients that can't access HTTP-only cookies
        response.headers.add('X-Auth-Token', token)

        return response
        
    except Exception as e:
        print(f"\n!!! Error in web3_verify: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/web3/verify-callback', methods=['GET'])
def web3_verify_callback():
    """Web3 verify via browser navigation for reliable cookie set."""
    try:
        print("\n=== Web3 Verify Callback (GET) ===")
        wallet_address = request.args.get('wallet_address')
        signature = request.args.get('signature')
        print(f"Params wallet_address={wallet_address}, signature length={len(signature) if signature else 0}")

        if not all([wallet_address, signature]):
            flash('Missing required parameters for Web3 login. Please try again.', 'danger')
            return redirect(url_for('login'))

        wallet_lower = wallet_address.lower()
        nonce = web3_nonces.get(wallet_lower)
        if not nonce:
            flash('Login attempt expired or invalid. Please try again.', 'warning')
            return redirect(url_for('login'))

        # Recover address
        original_message = f"Sign this message to login to QRL Wallet.\n\nNonce: {nonce}"
        try:
            message_hash = encode_defunct(text=original_message)
            recovered_address = Account.recover_message(message_hash, signature=signature)
            recovered_lower = recovered_address.lower()
            if recovered_lower != wallet_lower:
                # Try alternative param/prefix handling
                prefixed_message = f"\x19Ethereum Signed Message:\n{len(original_message)}{original_message}"
                message_hash = encode_defunct(text=prefixed_message)
                recovered_address = Account.recover_message(message_hash, signature=signature)
                recovered_lower = recovered_address.lower()
                if recovered_lower != wallet_lower:
                    flash('Signature verification failed (address mismatch).', 'danger')
                    return redirect(url_for('login'))
        except Exception as e:
            print(f"Verify-callback recovery error: {e}")
            flash('Invalid signature format.', 'danger')
            return redirect(url_for('login'))

        # Clean nonce
        web3_nonces.pop(wallet_lower, None)

        # Find or create user
        username = f"web3_{wallet_address[:10]}"
        if username not in users_db:
            users_db[username] = User(
                username=username,
                wallet_address=wallet_address,
                is_web3=True
            )
            if SEED_BALANCE_QRL > 0:
                demo_balances[wallet_address] = demo_balances.get(wallet_address, 0.0) + SEED_BALANCE_QRL
                logger.info("Seeded %.6f QRL to new user %s", SEED_BALANCE_QRL, wallet_address)

        user = users_db[username]
        user.last_login = datetime.now(timezone.utc)

        # JWT and redirect response
        token = create_jwt_token(user)
        resp = make_response(redirect(url_for('index')))
        expires = datetime.now(timezone.utc) + JWT_EXPIRATION_DELTA
        resp.set_cookie(
            key='auth_token',
            value=token,
            httponly=True,
            secure=is_secure_request(),
            samesite='Lax',
            expires=expires,
            path='/'
        )
        flash('Logged in with Web3 wallet successfully.', 'success')

        # Add debug logging for mobile troubleshooting
        print(f"Web3 callback: Setting cookie and redirecting to {url_for('index')}")
        print(f"User agent: {request.headers.get('User-Agent', 'Unknown')}")

        # For mobile browsers, add a meta refresh as fallback
        user_agent = request.headers.get('User-Agent', '').lower()
        is_mobile = any(mobile in user_agent for mobile in ['mobile', 'android', 'iphone', 'ipad'])
        if is_mobile:
            print("Mobile browser detected, adding meta refresh fallback")
            # Create a simple HTML response with meta refresh for mobile
            redirect_url = url_for('index')
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta http-equiv="refresh" content="2;url={redirect_url}">
                <title>Redirecting...</title>
            </head>
            <body>
                <p>Login successful! Redirecting to wallet...</p>
                <p><a href="{redirect_url}">Click here if not redirected automatically</a></p>
            </body>
            </html>
            """
            return html_content

        return resp
    except Exception as e:
        print(f"\n!!! Error in web3_verify_callback: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('Internal server error during Web3 login.', 'danger')
        return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    response = make_response(redirect(url_for('index')))
    response.delete_cookie('auth_token', path='/', secure=is_secure_request(), samesite='Lax')
    session.clear()
    flash('You have been logged out.', 'info')
    return response

@app.route('/debug/whoami')
def whoami():
    """Debug endpoint to check current auth status."""
    token = request.cookies.get('auth_token')
    info = {
        'has_cookie': bool(token),
        'cookie_length': len(token) if token else 0,
    }
    payload = verify_jwt_token(token) if token else None
    return jsonify({
        'token_present': bool(token),
        'payload_valid': bool(payload),
        'payload': payload,
        'info': info
    }), 200

@app.route('/mine', methods=['POST'])
@login_required
def mine():
    try:
        # Get the current user's address from the JWT token
        token = request.cookies.get('auth_token')
        if not token:
            return jsonify({'error': 'Not authenticated'}), 401
            
        payload = verify_jwt_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
            
        miner_address = payload.get('wallet_address')
        if not miner_address:
            return jsonify({'error': 'No wallet address found'}), 400
        
        # Mine a new block
        blockchain = node_service.blockchain
        if not blockchain:
            return jsonify({'error': 'Blockchain not initialized'}), 500
        
        # Mine the block
        new_block = blockchain.mine_pending_transactions(miner_address)

        # Persist blockchain state so rewards survive logout/restart
        try:
            node_service._save_blockchain()
        except Exception as persist_err:
            print(f"Warning: failed to persist blockchain after mining: {persist_err}")
        
        # Get the current mining reward
        current_reward = blockchain.mining_reward
        
        # Get the block height
        block_height = len(blockchain.chain)
        
        return jsonify({
            'status': 'success',
            'message': 'New block mined successfully',
            'block_hash': new_block.hash,
            'block_height': block_height,
            'mining_reward': current_reward,
            'transactions': len(new_block.transactions) - 1,  # Subtract 1 for the coinbase transaction
            'difficulty': blockchain.difficulty
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/buy', methods=['GET'])
@login_required
def buy():
    return render_template('buy.html')

@app.route('/simulate-purchase', methods=['POST'])
@login_required
def simulate_purchase():
    try:
        amount = float(request.form.get('amount', 0))
        method = request.form.get('payment_method')
        
        if amount <= 0:
            flash('Invalid purchase amount', 'danger')
            return redirect(url_for('buy'))
        
        # Get user address from token
        token = request.cookies.get('auth_token')
        payload = verify_jwt_token(token)
        if not payload or not payload.get('wallet_address'):
            flash('User not authenticated', 'danger')
            return redirect(url_for('login'))
        
        user_address = payload['wallet_address']
        
        # Demo: Add purchased amount to balance
        current_balance = node_service.get_balance(user_address) or 0.0
        if user_address not in demo_balances:
            demo_balances[user_address] = 0.0
        demo_balances[user_address] += amount
        logger.info(f"Demo purchase: Added {amount} QRL to {user_address}. Demo balance: {demo_balances[user_address]}")
        
        flash(f'Purchase simulated: {amount} QRL via {method}. Balance updated!', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Purchase error: {str(e)}', 'danger')
        return redirect(url_for('buy'))

@app.route('/send', methods=['POST'])
@login_required
def send():
    form = TransferForm()
    if form.validate_on_submit():
        try:
            # Get the current user's address from the JWT token
            token = request.cookies.get('auth_token')
            if not token:
                return jsonify({'error': 'Not authenticated'}), 401
                
            payload = verify_jwt_token(token)
            if not payload:
                return jsonify({'error': 'Invalid token'}), 401
                
            sender_address = payload.get('wallet_address')
            if not sender_address:
                return jsonify({'error': 'No wallet address found'}), 400
                
            recipient = form.recipient.data
            amount = form.amount.data

            # Create a Web3-backed transaction for our local chain
            # Note: Transaction.is_valid() only requires a non-empty signature at present
            fee = 0.01  # Flat fee to satisfy mempool min fee/byte
            tx = Transaction(sender=sender_address, recipient=recipient, amount=float(amount), fee=fee,
                             signature=f"web3:{datetime.now(timezone.utc).isoformat()}")

            added = node_service.mempool.add_transaction(tx)
            if not added:
                # Fall back message; mempool logs contain details
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': 'Failed to add transaction to mempool'}), 400
                flash('Failed to add transaction to mempool', 'danger')
                return redirect(url_for('index'))

            # Auto-mine to confirm the transaction immediately (configurable)
            auto_mine_success = False
            if AUTO_MINE_ON_SEND:
                try:
                    if not node_service.wallet:
                        node_service.create_wallet()
                    auto_mine_success = node_service.mine_block()
                    if not auto_mine_success:
                        logger.warning("Auto-mine after send did not produce a block; transaction remains pending")
                except Exception as mine_err:
                    logger.warning("Auto-mine after send failed: %s", mine_err)
                    auto_mine_success = False

            # If this was an AJAX request, return JSON for the UI
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'status': 'success',
                    'message': f'Submitted {amount} QRL to {recipient}',
                    'tx_hash': tx.transaction_hash,
                    'tx_url': url_for('transaction_details', tx_hash=tx.transaction_hash)
                })

            # Otherwise, redirect with a flash message
            flash(f'Transaction submitted: {amount} QRL to {recipient}', 'success')
            return redirect(url_for('transaction_details', tx_hash=tx.transaction_hash))
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        # Handle both AJAX and standard form posts
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Invalid form data', 'errors': form.errors}), 400
        for field, errs in form.errors.items():
            for err in errs:
                flash(f"{field}: {err}", 'danger')
        return redirect(url_for('index'))

@app.route('/explorer')
def explorer():
    """Block explorer main page - simplified version"""
    try:
        print("🔍 EXPLORER: Starting...")
        
        # Get blockchain info
        blockchain_info = node_service.get_blockchain_info()
        print(f"🔍 EXPLORER: Got blockchain info with keys: {list(blockchain_info.keys()) if isinstance(blockchain_info, dict) else 'Not a dict'}")
        
        # Get recent blocks (simplified)
        recent_blocks = []
        try:
            if 'chain' in blockchain_info and blockchain_info['chain']:
                chain_length = len(blockchain_info['chain'])
                start_idx = max(0, chain_length - 3)  # Last 3 blocks
                recent_blocks = blockchain_info['chain'][start_idx:]
                print(f"🔍 EXPLORER: Got {len(recent_blocks)} recent blocks")
            else:
                print("🔍 EXPLORER: No chain data available")
        except (KeyError, IndexError, TypeError) as e:
            print(f"🔍 EXPLORER: Error getting recent blocks: {e}")
            recent_blocks = []
        
        print("🔍 EXPLORER: Rendering template...")
        # Pass login info if available for template logic
        is_logged_in = False
        username = None
        try:
            token = request.cookies.get('auth_token')
            if token:
                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM], audience=JWT_AUDIENCE)
                username = payload['sub']
                is_logged_in = True
        except Exception:
            is_logged_in = False

        return render_template('explorer.html', 
                             blockchain_info=blockchain_info, 
                             recent_blocks=recent_blocks,
                             is_logged_in=is_logged_in,
                             username=username)
                             
    except Exception as e:
        print(f"❌ EXPLORER ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"<h1>Explorer Error</h1><p>Error: {str(e)}</p><p><a href='/'>Go Home</a></p>", 500

# API Endpoints for user statistics
@app.route('/api/users/count', methods=['GET'])
def get_user_count():
    user_count = len(users_db)
    return jsonify({
        'user_count': user_count,
        'users': list(users_db.keys()) if user_count <= 10 else f"{user_count} users"
    })

@app.route('/api/wallet/<address>', methods=['GET'])
def api_wallet(address):
    try:
        balance = node_service.get_balance(address) or 0.0
        pending_in = 0.0
        pending_out = 0.0

        def is_eth(addr: str) -> bool:
            return isinstance(addr, str) and addr.lower().startswith('0x') and len(addr) == 42 and all(c in '0123456789abcdef' for c in addr[2:].lower())

        def addr_eq(a: str, b: str) -> bool:
            if is_eth(a) and is_eth(b):
                return a.lower() == b.lower()
            return a == b

        for tx in node_service.mempool.get_pending_transactions():
            if addr_eq(tx.recipient, address):
                pending_in += getattr(tx, 'amount', 0.0) or 0.0
            if addr_eq(tx.sender, address):
                pending_out += getattr(tx, 'amount', 0.0) or 0.0

        return jsonify({
            'address': address,
            'balance': balance,
            'pending_in': pending_in,
            'pending_out': pending_out
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/blocks', methods=['GET'])
def api_blocks():
    try:
        count = int(request.args.get('count', 10))
        blockchain = node_service.blockchain
        chain = blockchain.chain
        start_index = max(len(chain) - count, 0)
        blocks = chain[start_index:]
        return jsonify({
            'blocks': [block.to_dict() for block in blocks],
            'count': len(blocks)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/block/<block_hash>', methods=['GET'])
def api_block_detail(block_hash):
    try:
        blockchain = node_service.blockchain
        for block in blockchain.chain:
            if block.hash == block_hash:
                return jsonify(block.to_dict())
        return jsonify({'error': 'Block not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions', methods=['GET'])
def api_transactions():
    try:
        limit = int(request.args.get('limit', 20))
        include_pending = request.args.get('pending', 'true').lower() in ('1', 'true', 'yes')
        blockchain = node_service.blockchain
        transactions = []

        for block in reversed(blockchain.chain):
            for tx in block.transactions:
                tx_dict = tx.to_dict()
                tx_dict['block_hash'] = block.hash
                tx_dict['confirmations'] = len(blockchain.chain) - block.index
                transactions.append(tx_dict)
                if len(transactions) >= limit:
                    break
            if len(transactions) >= limit:
                break

        if include_pending:
            for pending_tx in node_service.mempool.get_pending_transactions():
                tx_dict = pending_tx.to_dict()
                tx_dict['block_hash'] = None
                tx_dict['confirmations'] = 0
                transactions.append(tx_dict)
                if len(transactions) >= limit:
                    break

        return jsonify({'transactions': transactions[:limit]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/clear-users', methods=['POST'])
def clear_all_users():
    try:
        user_count = len(users_db)
        users_db.clear()
        print(f"🔐 ADMIN: Cleared {user_count} user accounts")
        return jsonify({'message': f'Successfully cleared {user_count} user accounts', 'user_count': 0})
    except Exception as e:
        return jsonify({'error': f'Failed to clear users: {str(e)}'}), 500

# Create templates directory if it doesn't exist
os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'), exist_ok=True)

# Run the app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

@app.route('/explorer/search')
def search():
    """Search for blocks, transactions, or addresses"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            flash('Please enter a search term', 'warning')
            return redirect(url_for('explorer'))
        
        # Simple search implementation
        # Detect QRL-style (starts with 'Q') or EVM-style (0x...) addresses
        def is_eth_address(s: str) -> bool:
            s = s.strip()
            return s.lower().startswith('0x') and len(s) == 42 and all(c in '0123456789abcdef' for c in s[2:].lower())

        if query.startswith('Q') or is_eth_address(query):  # Address search
            return redirect(url_for('address_details', address=query))
        elif query.isdigit():  # Block index
            try:
                block_index = int(query)
                blockchain = node_service.blockchain
                if 0 <= block_index < len(blockchain.chain):
                    return redirect(url_for('block_details', block_hash=blockchain.chain[block_index].hash))
            except:
                pass
        
        flash('No results found', 'warning')
        return redirect(url_for('explorer'))
        
    except Exception as e:
        flash(f'Search error: {str(e)}', 'danger')
        return redirect(url_for('explorer'))

@app.route('/explorer/address/<address>')
def address_details(address):
    """Show address details and transaction history"""
    try:
        # Validate address format: allow QRL-style and EVM-style addresses
        addr = address.strip()
        is_qrl = addr.startswith('Q') and (40 <= len(addr) <= 70)
        is_eth = addr.lower().startswith('0x') and len(addr) == 42 and all(c in '0123456789abcdef' for c in addr[2:].lower())
        if not (is_qrl or is_eth):
            flash('Invalid address format', 'danger')
            return redirect(url_for('explorer'))

        # Get balance
        balance = node_service.get_balance(address) or 0.0

        # Helper comparison to match EVM addresses case-insensitively
        def is_eth(addr: str) -> bool:
            return isinstance(addr, str) and addr.lower().startswith('0x') and len(addr) == 42 \
                and all(c in '0123456789abcdef' for c in addr[2:].lower())

        def addr_eq(a: str, b: str) -> bool:
            if is_eth(a) and is_eth(b):
                return a.lower() == b.lower()
            return a == b
        
        # Initialize transaction tracking
        transactions = []
        sent_count = 0
        received_count = 0
        total_sent = 0.0
        total_received = 0.0
        total_fees = 0.0
        
        # Get transaction history
        try:
            blockchain = node_service.blockchain
            for block in blockchain.chain[-100:]:  # Last 100 blocks for better history
                for tx in block.transactions:
                    if hasattr(tx, 'sender') and hasattr(tx, 'recipient'):
                        if addr_eq(tx.sender, address) or addr_eq(tx.recipient, address):
                            is_sent = addr_eq(tx.sender, address)
                            tx_type = 'sent' if is_sent else 'received'
                            
                            # Track transaction counts and totals
                            if is_sent:
                                sent_count += 1
                                tx_fee = getattr(tx, 'fee', 0) or 0
                                total_fees += tx_fee
                                total_sent += (getattr(tx, 'amount', 0) or 0) + tx_fee
                            else:
                                received_count += 1
                                total_received += getattr(tx, 'amount', 0) or 0
                            
                            transactions.append({
                                'tx': tx,
                                'block': block,
                                'type': tx_type
                            })
        except Exception as e:
            print(f"Error processing transactions: {e}")
            transactions = []
        
        # Calculate first seen time
        first_seen = transactions[-1]['block'].timestamp if transactions else None
        
        return render_template('address_details.html',
                             address=address,
                             balance=balance,
                             transactions=transactions,
                             sent_count=sent_count,
                             received_count=received_count,
                             total_sent=total_sent,
                             total_received=total_received,
                             total_fees=total_fees,
                             first_seen=first_seen)
                             
    except Exception as e:
        print(f"Error in address_details: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Error loading address details: {str(e)}', 'danger')
        return redirect(url_for('explorer'))

@app.route('/explorer/block/<block_hash>')
def block_details(block_hash):
    """Show block details"""
    try:
        blockchain = node_service.blockchain
        
        # Find block by hash
        block = None
        for b in blockchain.chain:
            if b.hash == block_hash:
                block = b
                break
        
        if not block:
            flash('Block not found', 'danger')
            return redirect(url_for('explorer'))
        
        # Calculate block statistics
        total_transactions = len(block.transactions)
        total_volume = sum(tx.amount for tx in block.transactions)
        mining_reward = sum(tx.amount for tx in block.transactions if tx.sender == "0")
        total_fees = sum(tx.fee for tx in block.transactions)
        
        return render_template('block_details.html',
                             block=block,
                             total_transactions=total_transactions,
                             total_volume=total_volume,
                             mining_reward=mining_reward,
                             total_fees=total_fees,
                             blockchain=blockchain)
                             
    except Exception as e:
        flash(f'Block details error: {str(e)}', 'danger')
        return redirect(url_for('explorer'))

@app.route('/explorer/transaction/<tx_hash>')
def transaction_details(tx_hash):
    """Show transaction details"""
    try:
        blockchain = node_service.blockchain
        
        # Find transaction in blockchain
        transaction = None
        block_hash = None
        confirmations = 0
        
        for block in blockchain.chain:
            for tx in block.transactions:
                if tx.transaction_hash == tx_hash:
                    transaction = tx
                    block_hash = block.hash
                    confirmations = len(blockchain.chain) - block.index
                    break
            if transaction:
                break
        
        if not transaction:
            mempool_tx = node_service.mempool.get_transaction(tx_hash)
            if mempool_tx:
                transaction = mempool_tx
                block_hash = "Unconfirmed"
                confirmations = 0
            else:
                flash('Transaction not found', 'danger')
                return redirect(url_for('explorer'))
        
        return render_template('transaction_details.html',
                             transaction=transaction,
                             block_hash=block_hash,
                             confirmations=confirmations)
                             
    except Exception as e:
        flash(f'Transaction details error: {str(e)}', 'danger')
        return redirect(url_for('explorer'))
