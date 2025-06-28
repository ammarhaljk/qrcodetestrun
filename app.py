import streamlit as st
import qrcode
from io import BytesIO
import base64
import json
import datetime
import secrets
import string
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import time

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
    .success-message {
        background: #dcfce7;
        color: #166534;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .error-message {
        background: #fee2e2;
        color: #dc2626;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'user_data' not in st.session_state:
    st.session_state.user_data = {}

if 'scan_stats' not in st.session_state:
    st.session_state.scan_stats = {
        'total_users': 0,
        'total_scans': 0,
        'emails_sent': 0
    }

if 'rate_limiter' not in st.session_state:
    st.session_state.rate_limiter = {}

# Initialize with demo data
if not st.session_state.user_data:
    demo_user = {
        'id': 'demo_user_123',
        'token': 'demo_token_abc456',
        'name': 'John Doe',
        'email': 'john.doe@example.com',
        'phone': '+1 (555) 123-4567',
        'company': 'Tech Solutions Inc.',
        'title': 'Senior Software Engineer',
        'website': 'https://johndoe.dev',
        'created': datetime.datetime.now().isoformat(),
        'scans': 12
    }
    st.session_state.user_data[demo_user['id']] = demo_user
    st.session_state.scan_stats = {
        'total_users': 1,
        'total_scans': 12,
        'emails_sent': 8
    }

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
    """Simulate sending contact email (in production, use actual email service)"""
    # This is a placeholder - in production, you'd use services like:
    # - SendGrid
    # - AWS SES
    # - SMTP server
    
    email_content = f"""
    Subject: Contact Information from {contact_info['name']}
    
    Here's the contact information you requested:
    
    Name: {contact_info['name']}
    Email: {contact_info['email']}
    """
    
    if contact_info.get('phone'):
        email_content += f"Phone: {contact_info['phone']}\n"
    if contact_info.get('company'):
        email_content += f"Company: {contact_info['company']}\n"
    if contact_info.get('title'):
        email_content += f"Title: {contact_info['title']}\n"
    if contact_info.get('website'):
        email_content += f"Website: {contact_info['website']}\n"
    
    email_content += "\nBest regards,\nQR Contact System"
    
    # Log the email (in production, actually send it)
    st.success(f"Email would be sent to: {recipient_email}")
    return True

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
    if 'id' in query_params and 'token' in query_params:
        st.session_state.contact_id = query_params['id'][0]
        st.session_state.contact_token = query_params['token'][0]

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
                
                # Store in session state
                st.session_state.user_data[user_id] = contact_info
                st.session_state.scan_stats['total_users'] = len(st.session_state.user_data)
                
                # Generate QR code URL
                base_url = "https://your-streamlit-app.streamlit.app"  # Replace with your actual URL
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
                    st.code(qr_url, language="text")
                    st.markdown("### Instructions")
                    st.info("💡 Print this QR code and place it wherever you want people to get your contact info!")

# Tab 2: Contact Form
elif tab == "Contact Form":
    st.header("📧 Get Contact Information")
    st.write("Enter your email to receive the contact details")
    
    with st.form("contact_form"):
        recipient_email = st.text_input("Your Email Address *", placeholder="your@email.com")
        
        # Pre-fill if coming from QR code
        contact_id_default = st.session_state.get('contact_id', '')
        contact_token_default = st.session_state.get('contact_token', '')
        
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
                        time.sleep(2)  # Simulate processing delay
                        
                        # Validate contact info
                        if contact_id not in st.session_state.user_data:
                            st.error("❌ Invalid contact ID.")
                        else:
                            contact_info = st.session_state.user_data[contact_id]
                            
                            if contact_info['token'] != contact_token:
                                st.error("❌ Invalid or expired security token.")
                            else:
                                # Update scan count
                                contact_info['scans'] += 1
                                st.session_state.scan_stats['total_scans'] += 1
                                
                                # Send email (simulated)
                                if send_contact_email(recipient_email, contact_info):
                                    st.session_state.scan_stats['emails_sent'] += 1
                                    
                                    st.success(f"✅ Contact information sent to {recipient_email}!")
                                    
                                    # Display contact preview
                                    st.markdown("### Contact Information Preview")
                                    
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
    
    # Statistics
    st.markdown("### 📊 System Statistics")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <h2 style="color: #4f46e5; margin: 0;">{st.session_state.scan_stats['total_users']}</h2>
            <p style="margin: 0;">Total Users</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <h2 style="color: #10b981; margin: 0;">{st.session_state.scan_stats['total_scans']}</h2>
            <p style="margin: 0;">Total Scans</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <h2 style="color: #f59e0b; margin: 0;">{st.session_state.scan_stats['emails_sent']}</h2>
            <p style="margin: 0;">Emails Sent</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # User search
    st.markdown("### 🔍 Search Users")
    search_term = st.text_input("Search by User ID, Email, or Name")
    
    if st.button("Search", type="primary"):
        if search_term:
            matching_users = []
            for user_id, user_data in st.session_state.user_data.items():
                if (search_term.lower() in user_id.lower() or 
                    search_term.lower() in user_data['email'].lower() or 
                    search_term.lower() in user_data['name'].lower()):
                    matching_users.append(user_data)
            
            if matching_users:
                st.success(f"Found {len(matching_users)} user(s)")
                for user in matching_users:
                    with st.expander(f"{user['name']} ({user['id']})"):
                        st.write(f"**Email:** {user['email']}")
                        st.write(f"**Created:** {datetime.datetime.fromisoformat(user['created']).strftime('%Y-%m-%d %H:%M:%S')}")
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
        else:
            st.error("Please enter a search term.")
    
    # All users table
    if st.session_state.user_data:
        st.markdown("### 👥 All Users")
        users_df = pd.DataFrame(st.session_state.user_data.values())
        users_df['created'] = pd.to_datetime(users_df['created']).dt.strftime('%Y-%m-%d %H:%M')
        st.dataframe(users_df[['name', 'email', 'company', 'scans', 'created']], use_container_width=True)

# Footer
st.markdown("---")
st.markdown("Built with ❤️ using Streamlit")