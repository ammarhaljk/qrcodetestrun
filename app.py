import streamlit as st
import qrcode
from io import BytesIO
import base64
import json
import datetime
import secrets
import string
import pandas as pd
import time
import sqlite3
import os

# Configure page
st.set_page_config(
    page_title="QR Contact System",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .contact-card {
        background: #f8fafc;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #4f46e5;
        margin: 1rem 0;
    }
    .stat-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        border: 1px solid #e5e7eb;
    }
    .url-display {
        background: #f1f5f9;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #cbd5e1;
        font-family: monospace;
        font-size: 0.9rem;
        word-break: break-all;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Database setup
DB_FILE = "qr_contacts.db"

def init_db():
    """Initialize the database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            token TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            company TEXT,
            title TEXT,
            website TEXT,
            created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            scans INTEGER DEFAULT 0
        )
    ''')
    
    # Create stats table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY,
            total_users INTEGER DEFAULT 0,
            total_scans INTEGER DEFAULT 0,
            emails_sent INTEGER DEFAULT 0
        )
    ''')
    
    # Initialize stats if empty
    cursor.execute('SELECT COUNT(*) FROM stats')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO stats (total_users, total_scans, emails_sent) VALUES (0, 0, 0)')
    
    conn.commit()
    conn.close()

def get_stats():
    """Get current statistics"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT total_users, total_scans, emails_sent FROM stats ORDER BY id DESC LIMIT 1')
    result = cursor.fetchone()
    conn.close()
    return result if result else (0, 0, 0)

def update_stats(total_users=None, total_scans=None, emails_sent=None):
    """Update statistics"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    current_stats = get_stats()
    new_total_users = total_users if total_users is not None else current_stats[0]
    new_total_scans = total_scans if total_scans is not None else current_stats[1]
    new_emails_sent = emails_sent if emails_sent is not None else current_stats[2]
    
    cursor.execute('''
        UPDATE stats SET total_users=?, total_scans=?, emails_sent=? 
        WHERE id=(SELECT MAX(id) FROM stats)
    ''', (new_total_users, new_total_scans, new_emails_sent))
    
    conn.commit()
    conn.close()

def save_user(user_data):
    """Save user data to database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (id, token, name, email, phone, company, title, website, created, scans)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_data['id'], user_data['token'], user_data['name'], user_data['email'],
        user_data.get('phone', ''), user_data.get('company', ''), 
        user_data.get('title', ''), user_data.get('website', ''),
        user_data['created'], user_data.get('scans', 0)
    ))
    
    conn.commit()
    conn.close()
    
    # Update total users count
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    conn.close()
    
    current_stats = get_stats()
    update_stats(total_users=total_users, total_scans=current_stats[1], emails_sent=current_stats[2])

def get_user(user_id):
    """Get user data from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id=?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'id': result[0],
            'token': result[1],
            'name': result[2],
            'email': result[3],
            'phone': result[4],
            'company': result[5],
            'title': result[6],
            'website': result[7],
            'created': result[8],
            'scans': result[9]
        }
    return None

def increment_scan_count(user_id):
    """Increment scan count for user"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET scans = scans + 1 WHERE id=?', (user_id,))
    conn.commit()
    conn.close()
    
    # Update total scans
    current_stats = get_stats()
    update_stats(total_users=current_stats[0], total_scans=current_stats[1] + 1, emails_sent=current_stats[2])

def search_users(search_term):
    """Search users by ID, name, or email"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM users 
        WHERE id LIKE ? OR name LIKE ? OR email LIKE ?
    ''', (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
    results = cursor.fetchall()
    conn.close()
    
    users = []
    for result in results:
        users.append({
            'id': result[0],
            'token': result[1],
            'name': result[2],
            'email': result[3],
            'phone': result[4],
            'company': result[5],
            'title': result[6],
            'website': result[7],
            'created': result[8],
            'scans': result[9]
        })
    
    return users

def get_all_users():
    """Get all users"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users ORDER BY created DESC')
    results = cursor.fetchall()
    conn.close()
    
    users = []
    for result in results:
        users.append({
            'id': result[0],
            'name': result[2],
            'email': result[3],
            'company': result[5],
            'scans': result[9],
            'created': result[8]
        })
    
    return users

# Initialize database
init_db()

# Initialize session state for rate limiting
if 'rate_limiter' not in st.session_state:
    st.session_state.rate_limiter = {}

def generate_token():
    """Generate a secure random token"""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))

def generate_user_id():
    """Generate a unique user ID"""
    return f"user_{''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))}"

def create_qr_code(data):
    """Create QR code and return as base64 image"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="#4f46e5", back_color="white")
    
    # Convert to base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return img_str

def check_rate_limit(client_ip, limit=5, window=3600):
    """Check if client has exceeded rate limit"""
    now = time.time()
    if client_ip not in st.session_state.rate_limiter:
        st.session_state.rate_limiter[client_ip] = {'count': 0, 'reset_time': now + window}
    
    client_data = st.session_state.rate_limiter[client_ip]
    
    if now > client_data['reset_time']:
        client_data['count'] = 0
        client_data['reset_time'] = now + window
    
    if client_data['count'] >= limit:
        return False
    
    client_data['count'] += 1
    return True

def send_contact_email(recipient_email, contact_info):
    """Simulate sending contact email"""
    # In production, integrate with SendGrid, AWS SES, etc.
    current_stats = get_stats()
    update_stats(total_users=current_stats[0], total_scans=current_stats[1], emails_sent=current_stats[2] + 1)
    
    st.success(f"📧 Contact information sent to {recipient_email}")
    return True

def get_current_url():
    """Get the current app URL"""
    # Try to detect if we're on Streamlit Cloud
    try:
        # Check if we have query params that might indicate the current URL
        query_params = st.experimental_get_query_params()
        
        # For Streamlit Cloud, use this pattern
        # Replace 'your-app-name' with your actual app name
        if 'streamlit.app' in st.experimental_get_query_params().get('_', [''])[0]:
            return "https://qrcodetestrun.streamlit.app"
        else:
            # You need to manually set this to your deployed URL
            return "https://qrcodetestrun.streamlit.app"  # UPDATE THIS!
    except:
        return "http://localhost:8501"  # Local development

# Header
st.markdown("""
<div class="main-header">
    <h1>📱 QR Contact System</h1>
    <p>Share your contact information with printed QR codes</p>
</div>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("Navigation")
tab = st.sidebar.selectbox(
    "Select Action",
    ["Generate QR Code", "Contact Form", "Admin Panel"]
)

# Handle URL parameters for direct access
query_params = st.experimental_get_query_params()
if 'tab' in query_params and query_params['tab'][0] == 'scanner':
    tab = "Contact Form"

# Tab 1: QR Code Generator
if tab == "Generate QR Code":
    st.header("🎯 Create Your QR Code")
    
    with st.form("qr_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            user_id = st.text_input("User ID (optional)", help="Leave blank for auto-generation")
            name = st.text_input("Full Name *", placeholder="John Doe")
            email = st.text_input("Email *", placeholder="john@example.com")
            phone = st.text_input("Phone", placeholder="+1 (555) 123-4567")
        
        with col2:
            company = st.text_input("Company", placeholder="Acme Corp")
            title = st.text_input("Job Title", placeholder="Software Engineer")
            website = st.text_input("Website", placeholder="https://example.com")
        
        submitted = st.form_submit_button("Generate QR Code", type="primary")
        
        if submitted:
            if not name or not email:
                st.error("Name and Email are required fields!")
            else:
                # Generate user data
                if not user_id:
                    user_id = generate_user_id()
                
                token = generate_token()
                
                contact_info = {
                    'id': user_id,
                    'token': token,
                    'name': name,
                    'email': email,
                    'phone': phone or '',
                    'company': company or '',
                    'title': title or '',
                    'website': website or '',
                    'created': datetime.datetime.now().isoformat(),
                    'scans': 0
                }
                
                # Save to database
                save_user(contact_info)
                
                # Generate QR code URL
                base_url = get_current_url()
                qr_url = f"{base_url}?tab=scanner&id={user_id}&token={token}"
                
                # Create and display QR code
                qr_img = create_qr_code(qr_url)
                
                st.success("✅ QR code generated successfully!")
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.markdown("### Your QR Code")
                    st.markdown(f'<img src="data:image/png;base64,{qr_img}" width="300">', unsafe_allow_html=True)
                
                with col2:
                    st.markdown("### QR Code URL")
                    st.markdown(f'<div class="url-display">{qr_url}</div>', unsafe_allow_html=True)
                    st.markdown("### Instructions")
                    st.info("💡 Print this QR code and place it wherever you want people to get your contact info!")
                    
                    # Download QR code
                    qr_bytes = base64.b64decode(qr_img)
                    st.download_button(
                        label="📥 Download QR Code",
                        data=qr_bytes,
                        file_name=f"qr_code_{user_id}.png",
                        mime="image/png"
                    )

# Tab 2: Contact Form
elif tab == "Contact Form":
    st.header("📧 Get Contact Information")
    
    # Auto-fill from URL parameters
    contact_id_default = query_params.get('id', [''])[0] if 'id' in query_params else ''
    contact_token_default = query_params.get('token', [''])[0] if 'token' in query_params else ''
    
    # Show preview if we have valid params
    if contact_id_default and contact_token_default:
        user_data = get_user(contact_id_default)
        if user_data and user_data['token'] == contact_token_default:
            st.markdown("### 👤 Contact Preview")
            st.markdown(f"**Name:** {user_data['name']}")
            st.markdown(f"**Company:** {user_data.get('company', 'N/A')}")
            st.markdown("---")
    
    st.write("Enter your email to receive the contact details")
    
    with st.form("contact_form"):
        recipient_email = st.text_input("Your Email Address *", placeholder="your@email.com")
        contact_id = st.text_input("Contact ID *", value=contact_id_default, placeholder="From QR code URL")
        contact_token = st.text_input("Security Token *", value=contact_token_default, placeholder="From QR code URL")
        
        submitted = st.form_submit_button("Send Contact Info", type="primary")
        
        if submitted:
            if not recipient_email or not contact_id or not contact_token:
                st.error("All fields are required!")
            else:
                # Rate limiting check
                client_ip = "demo_ip"  # In production, get real client IP
                if not check_rate_limit(client_ip):
                    st.error("⚠️ Too many requests. Please try again later.")
                else:
                    # Show loading
                    with st.spinner("Sending contact information..."):
                        time.sleep(1)  # Simulate processing delay
                        
                        # Get contact info from database
                        contact_info = get_user(contact_id)
                        
                        if not contact_info:
                            st.error("❌ Invalid contact ID.")
                        elif contact_info['token'] != contact_token:
                            st.error("❌ Invalid or expired security token.")
                        else:
                            # Update scan count
                            increment_scan_count(contact_id)
                            
                            # Send email (simulated)
                            if send_contact_email(recipient_email, contact_info):
                                # Display contact preview
                                st.markdown("### 📇 Contact Information")
                                
                                contact_card = f"""
                                <div class="contact-card">
                                    <h4>👤 {contact_info['name']}</h4>
                                    <p><strong>📧 Email:</strong> {contact_info['email']}</p>
                                """
                                
                                if contact_info['phone']:
                                    contact_card += f"<p><strong>📞 Phone:</strong> {contact_info['phone']}</p>"
                                if contact_info['company']:
                                    contact_card += f"<p><strong>🏢 Company:</strong> {contact_info['company']}</p>"
                                if contact_info['title']:
                                    contact_card += f"<p><strong>💼 Title:</strong> {contact_info['title']}</p>"
                                if contact_info['website']:
                                    contact_card += f"<p><strong>🌐 Website:</strong> <a href='{contact_info['website']}'>{contact_info['website']}</a></p>"
                                
                                contact_card += "</div>"
                                
                                st.markdown(contact_card, unsafe_allow_html=True)

# Tab 3: Admin Panel
elif tab == "Admin Panel":
    st.header("🔧 System Administration")
    
    # Get current statistics
    total_users, total_scans, emails_sent = get_stats()
    
    # Statistics
    st.markdown("### 📊 System Statistics")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <h2 style="color: #4f46e5; margin: 0;">{total_users}</h2>
            <p style="margin: 0;">Total Users</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <h2 style="color: #10b981; margin: 0;">{total_scans}</h2>
            <p style="margin: 0;">Total Scans</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <h2 style="color: #f59e0b; margin: 0;">{emails_sent}</h2>
            <p style="margin: 0;">Emails Sent</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # User search
    st.markdown("### 🔍 Search Users")
    search_term = st.text_input("Search by User ID, Email, or Name")
    
    if st.button("Search", type="primary") and search_term:
        matching_users = search_users(search_term)
        
        if matching_users:
            st.success(f"Found {len(matching_users)} user(s)")
            for user in matching_users:
                with st.expander(f"{user['name']} ({user['id']})"):
                    st.write(f"**Email:** {user['email']}")
                    st.write(f"**Created:** {user['created']}")
                    st.write(f"**Scans:** {user['scans']}")
                    if user['phone']:
                        st.write(f"**Phone:** {user['phone']}")
                    if user['company']:
                        st.write(f"**Company:** {user['company']}")
                    if user['title']:
                        st.write(f"**Title:** {user['title']}")
                    if user['website']:
                        st.write(f"**Website:** {user['website']}")
        else:
            st.warning("No users found matching your search.")
    
    # All users table
    all_users = get_all_users()
    if all_users:
        st.markdown("### 👥 All Users")
        users_df = pd.DataFrame(all_users)
        st.dataframe(users_df, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("Built with ❤️ using Streamlit")

# Add refresh button for real-time updates
if st.sidebar.button("🔄 Refresh Data"):
    st.experimental_rerun()
