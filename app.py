import sys
import subprocess
import pkg_resources

# Ensure all required packages are installed
required = {'streamlit', 'pandas', 'Pillow'}
installed = {pkg.key for pkg in pkg_resources.working_set}
missing = required - installed

if missing:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Now import everything
import streamlit as st
import pandas as pd
import json
import datetime
import os
import hashlib
import uuid
import base64
from pathlib import Path
import re
from PIL import Image

# App Configuration
st.set_page_config(
    page_title="Uhoues - Direct Owner Listings",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'listings' not in st.session_state:
    st.session_state.listings = []
if 'users' not in st.session_state:
    st.session_state.users = {}
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'reports' not in st.session_state:
    st.session_state.reports = []
if 'verified_owners' not in st.session_state:
    st.session_state.verified_owners = {}
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'pending_payments' not in st.session_state:
    st.session_state.pending_payments = {}
if 'admin_mode' not in st.session_state:
    st.session_state.admin_mode = False

# File paths for persistence
DATA_DIR = Path("uhoues_data")
DATA_DIR.mkdir(exist_ok=True)
LISTINGS_FILE = DATA_DIR / "listings.json"
USERS_FILE = DATA_DIR / "users.json"
MESSAGES_FILE = DATA_DIR / "messages.json"
REPORTS_FILE = DATA_DIR / "reports.json"
VERIFICATIONS_FILE = DATA_DIR / "verifications.json"
PAYMENTS_FILE = DATA_DIR / "payments.json"
IMAGES_DIR = DATA_DIR / "property_images"
PAYMENT_PROOFS_DIR = DATA_DIR / "payment_proofs"
VERIFICATION_DOCS_DIR = DATA_DIR / "verification_docs"

for directory in [IMAGES_DIR, PAYMENT_PROOFS_DIR, VERIFICATION_DOCS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

def load_data():
    """Load data from JSON files"""
    files_data = [
        (LISTINGS_FILE, 'listings'),
        (USERS_FILE, 'users'),
        (MESSAGES_FILE, 'messages'),
        (REPORTS_FILE, 'reports'),
        (VERIFICATIONS_FILE, 'verified_owners'),
        (PAYMENTS_FILE, 'pending_payments')
    ]
    
    for file_path, state_key in files_data:
        try:
            if file_path.exists():
                with open(file_path, 'r') as f:
                    st.session_state[state_key] = json.load(f)
        except:
            st.session_state[state_key] = [] if state_key in ['listings', 'messages', 'reports'] else {}

def save_data():
    """Save data to JSON files"""
    files_data = [
        (LISTINGS_FILE, 'listings'),
        (USERS_FILE, 'users'),
        (MESSAGES_FILE, 'messages'),
        (REPORTS_FILE, 'reports'),
        (VERIFICATIONS_FILE, 'verified_owners'),
        (PAYMENTS_FILE, 'pending_payments')
    ]
    
    for file_path, state_key in files_data:
        with open(file_path, 'w') as f:
            json.dump(st.session_state[state_key], f)

def hash_password(password):
    """Simple password hashing"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_owner_identity(owner_id, document_images):
    """Verify owner identity through document upload"""
    verification_id = str(uuid.uuid4())
    doc_paths = []
    
    # Save document images
    for i, doc_img in enumerate(document_images):
        if doc_img:
            doc_path = VERIFICATION_DOCS_DIR / f"verification_{owner_id}_{i}.jpg"
            try:
                if isinstance(doc_img, Image.Image):
                    doc_img.save(doc_path)
                else:
                    with open(doc_path, 'wb') as f:
                        f.write(doc_img.getvalue())
                doc_paths.append(str(doc_path))
            except:
                continue
    
    st.session_state.verified_owners[owner_id] = {
        'verification_id': verification_id,
        'verified': False,
        'verification_date': datetime.datetime.now().isoformat(),
        'documents': doc_paths,
        'status': 'pending_review'
    }
    
    save_data()
    return verification_id

def create_pending_listing(owner_id, listing_data, images):
    """Create a pending listing that requires payment verification"""
    listing_id = str(uuid.uuid4())
    
    listing = {
        'id': listing_id,
        'owner_id': owner_id,
        'title': listing_data['title'],
        'description': listing_data['description'],
        'type': listing_data['type'],
        'property_type': listing_data['property_type'],
        'price': listing_data['price'],
        'currency': 'K',
        'location': listing_data['location'],
        'bedrooms': listing_data['bedrooms'],
        'bathrooms': listing_data['bathrooms'],
        'area_sqft': listing_data['area_sqft'],
        'features': listing_data['features'],
        'contact_phone': listing_data['contact_phone'],
        'contact_email': listing_data['contact_email'],
        'images': [],
        'created_at': datetime.datetime.now().isoformat(),
        'updated_at': datetime.datetime.now().isoformat(),
        'status': 'pending_payment',
        'verified': False,
        'payment_status': 'pending',
        'payment_amount': 250,
        'payment_reference': f"UHOUSE_{owner_id[:8]}_{listing_id[:8]}"
    }
    
    # Save images
    for i, img in enumerate(images[:5]):
        if img:
            img_path = IMAGES_DIR / f"{listing_id}_{i}.jpg"
            try:
                img.save(img_path)
                listing['images'].append(str(img_path))
            except Exception as e:
                st.error(f"Error saving image: {e}")
    
    st.session_state.listings.append(listing)
    
    # Create payment record
    payment_id = str(uuid.uuid4())
    st.session_state.pending_payments[payment_id] = {
        'payment_id': payment_id,
        'listing_id': listing_id,
        'owner_id': owner_id,
        'amount': 250,
        'currency': 'ZMW',
        'reference': listing['payment_reference'],
        'status': 'pending',
        'created_at': datetime.datetime.now().isoformat(),
        'proof_image': None
    }
    
    save_data()
    return listing_id, payment_id, listing['payment_reference']

def activate_listing(listing_id, payment_proof_image):
    """Activate listing after payment verification"""
    listing = next((l for l in st.session_state.listings if l['id'] == listing_id), None)
    if not listing:
        return False, "Listing not found"
    
    # Save payment proof
    if payment_proof_image:
        proof_path = PAYMENT_PROOFS_DIR / f"payment_{listing_id}.jpg"
        try:
            payment_proof_image.save(proof_path)
            
            # Update payment record
            for payment_id, payment in st.session_state.pending_payments.items():
                if payment['listing_id'] == listing_id:
                    payment['proof_image'] = str(proof_path)
                    payment['status'] = 'awaiting_verification'
                    payment['proof_submitted_at'] = datetime.datetime.now().isoformat()
                    break
            
            # Update listing status
            listing['status'] = 'awaiting_activation'
            listing['payment_status'] = 'proof_submitted'
            listing['updated_at'] = datetime.datetime.now().isoformat()
            
            save_data()
            return True, "Payment proof submitted successfully! Our team will verify it within 24 hours."
        except Exception as e:
            return False, f"Error saving payment proof: {e}"
    
    return False, "No payment proof provided"

def approve_payment(payment_id):
    """Admin approves payment and activates listing"""
    if payment_id not in st.session_state.pending_payments:
        return False, "Payment not found"
    
    payment = st.session_state.pending_payments[payment_id]
    listing = next((l for l in st.session_state.listings if l['id'] == payment['listing_id']), None)
    
    if not listing:
        return False, "Listing not found"
    
    # Activate listing
    listing['status'] = 'active'
    listing['payment_status'] = 'verified'
    listing['activated_at'] = datetime.datetime.now().isoformat()
    listing['updated_at'] = datetime.datetime.now().isoformat()
    
    # Update payment record
    payment['status'] = 'verified'
    payment['verified_at'] = datetime.datetime.now().isoformat()
    payment['verified_by'] = 'admin'
    
    save_data()
    return True, "Payment verified and listing activated!"

def send_message(sender_id, receiver_id, listing_id, message):
    """Send a message between users"""
    message_id = str(uuid.uuid4())
    msg = {
        'id': message_id,
        'sender_id': sender_id,
        'receiver_id': receiver_id,
        'listing_id': listing_id,
        'message': message,
        'timestamp': datetime.datetime.now().isoformat(),
        'read': False
    }
    st.session_state.messages.append(msg)
    save_data()
    return message_id

def report_content(reporter_id, content_type, content_id, reason):
    """Report inappropriate content"""
    report_id = str(uuid.uuid4())
    report = {
        'id': report_id,
        'reporter_id': reporter_id,
        'content_type': content_type,
        'content_id': content_id,
        'reason': reason,
        'timestamp': datetime.datetime.now().isoformat(),
        'status': 'pending'
    }
    st.session_state.reports.append(report)
    save_data()
    return report_id

# Load existing data
load_data()

# Main App
st.title("🏠 Uhoues - Direct Owner Property Listings")
st.markdown("### No Agents Allowed • K250 Listing Fee • Payment by Mobile Money")

# Admin Login (Hidden in sidebar)
with st.sidebar:
    if st.checkbox("Admin Login"):
        admin_pass = st.text_input("Admin Password", type="password")
        if st.button("Login as Admin"):
            if admin_pass == "UhouesAdmin2024!":
                st.session_state.admin_mode = True
                st.success("Admin mode activated!")
                st.rerun()

# Sidebar for navigation
st.sidebar.title("Navigation")
menu_options = ["🏠 Browse Listings", "📝 Post Listing", "💰 My Payments", "👤 My Account", 
                "💬 Messages", "⚠️ Report", "ℹ️ About", "🛡️ Admin Panel"] if st.session_state.admin_mode else \
               ["🏠 Browse Listings", "📝 Post Listing", "💰 My Payments", "👤 My Account", 
                "💬 Messages", "⚠️ Report", "ℹ️ About"]

menu = st.sidebar.radio("Go to", menu_options)

# Authentication
with st.sidebar:
    st.markdown("---")
    if st.session_state.current_user:
        user_info = st.session_state.users.get(st.session_state.current_user, {})
        st.success(f"👋 Welcome, {user_info.get('name', 'User')}")
        if st.button("Logout"):
            st.session_state.current_user = None
            st.session_state.admin_mode = False
            st.rerun()
    else:
        auth_tab1, auth_tab2 = st.tabs(["Login", "Register"])
        
        with auth_tab1:
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Sign In", key="login_btn"):
                if login_email in st.session_state.users:
                    if st.session_state.users[login_email]['password'] == hash_password(login_password):
                        st.session_state.current_user = login_email
                        st.success("Logged in successfully!")
                        st.rerun()
                    else:
                        st.error("Incorrect password")
                else:
                    st.error("User not found")
        
        with auth_tab2:
            reg_name = st.text_input("Full Name", key="reg_name")
            reg_email = st.text_input("Email", key="reg_email")
            reg_phone = st.text_input("Phone Number", key="reg_phone")
            reg_password = st.text_input("Password", type="password", key="reg_pass")
            reg_confirm = st.text_input("Confirm Password", type="password", key="reg_conf")
            is_owner = st.checkbox("I am a property owner (not an agent)", key="is_owner")
            agree_terms = st.checkbox("I agree to the Terms and Conditions", key="agree_terms")
            
            if st.button("Create Account", key="reg_btn"):
                if not is_owner:
                    st.error("❌ Only property owners are allowed to register on Uhoues")
                elif not agree_terms:
                    st.error("❌ You must agree to the Terms and Conditions")
                elif reg_password != reg_confirm:
                    st.error("❌ Passwords don't match")
                elif reg_email in st.session_state.users:
                    st.error("❌ Email already registered")
                elif not re.match(r"[^@]+@[^@]+\.[^@]+", reg_email):
                    st.error("❌ Please enter a valid email address")
                elif not reg_phone or len(reg_phone) < 10:
                    st.error("❌ Please enter a valid phone number")
                else:
                    st.session_state.users[reg_email] = {
                        'name': reg_name,
                        'email': reg_email,
                        'phone': reg_phone,
                        'password': hash_password(reg_password),
                        'is_owner': True,
                        'created_at': datetime.datetime.now().isoformat(),
                        'verified': False
                    }
                    st.session_state.current_user = reg_email
                    st.success("✅ Account created successfully!")
                    save_data()
                    st.rerun()

# Main Content based on menu selection
if menu == "🏠 Browse Listings":
    st.header("Browse Available Properties")
    
    # Stats
    active_listings = [l for l in st.session_state.listings if l['status'] == 'active']
    total_listings = len(st.session_state.listings)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Active Listings", len(active_listings))
    with col2:
        st.metric("Total Properties", total_listings)
    with col3:
        verified_count = len([l for l in active_listings if l.get('verified', False)])
        st.metric("Verified Owners", verified_count)
    
    # Filters
    with st.expander("🔍 Search Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            listing_type = st.selectbox(
                "Listing Type",
                ["All", "For Rent", "For Sale"]
            )
            min_price = st.number_input("Min Price (K)", 0, 100000, 0)
        with col2:
            property_type = st.selectbox(
                "Property Type",
                ["All", "House", "Apartment", "Townhouse", "Commercial", "Plot"]
            )
            max_price = st.number_input("Max Price (K)", 0, 100000, 50000)
        with col3:
            bedrooms = st.selectbox("Bedrooms", ["Any", "1+", "2+", "3+", "4+"])
            location = st.text_input("Location (City/Area)")
    
    # Display listings
    filtered_listings = [l for l in active_listings]
    
    # Apply filters
    if listing_type == "For Rent":
        filtered_listings = [l for l in filtered_listings if l['type'] == 'rent']
    elif listing_type == "For Sale":
        filtered_listings = [l for l in filtered_listings if l['type'] == 'sale']
    
    if property_type != "All":
        filtered_listings = [l for l in filtered_listings if l['property_type'] == property_type]
    
    filtered_listings = [l for l in filtered_listings if min_price <= l['price'] <= max_price]
    
    if bedrooms != "Any":
        min_beds = int(bedrooms[0])
        filtered_listings = [l for l in filtered_listings if l['bedrooms'] >= min_beds]
    
    if location:
        filtered_listings = [l for l in filtered_listings if location.lower() in l['location'].lower()]
    
    # Sort options
    sort_by = st.selectbox("Sort by", ["Newest", "Price: Low to High", "Price: High to Low"])
    if sort_by == "Newest":
        filtered_listings.sort(key=lambda x: x['created_at'], reverse=True)
    elif sort_by == "Price: Low to High":
        filtered_listings.sort(key=lambda x: x['price'])
    elif sort_by == "Price: High to Low":
        filtered_listings.sort(key=lambda x: x['price'], reverse=True)
    
    # Display listings in grid
    if filtered_listings:
        st.write(f"**Found {len(filtered_listings)} properties**")
        
        # Create grid display
        cols = st.columns(3)
        for idx, listing in enumerate(filtered_listings):
            with cols[idx % 3]:
                with st.container(border=True):
                    # Display badge
                    col_badge1, col_badge2 = st.columns([3, 1])
                    with col_badge1:
                        if listing.get('verified', False):
                            st.success("✅ Verified Owner")
                    with col_badge2:
                        st.markdown(f"**K{listing['price']}**")
                    
                    # Display image
                    if listing['images']:
                        try:
                            img = Image.open(listing['images'][0])
                            st.image(img, use_column_width=True)
                        except:
                            st.image("https://via.placeholder.com/300x200?text=Property+Image", use_column_width=True)
                    else:
                        st.image("https://via.placeholder.com/300x200?text=No+Image", use_column_width=True)
                    
                    st.subheader(listing['title'][:30] + ("..." if len(listing['title']) > 30 else ""))
                    st.markdown(f"📍 {listing['location'][:30]}")
                    st.markdown(f"🏠 {listing['property_type']} • {listing['type'].title()}")
                    st.markdown(f"🛏️ {listing['bedrooms']} bed • 🛁 {listing['bathrooms']} bath")
                    
                    # Buttons
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("View", key=f"view_{listing['id']}", use_container_width=True):
                            st.session_state.selected_listing = listing['id']
                            st.rerun()
                    with col_btn2:
                        if st.button("Contact", key=f"contact_{listing['id']}", use_container_width=True):
                            st.session_state.contact_listing = listing['id']
                            st.rerun()
    else:
        st.info("No properties match your filters. Try adjusting your search criteria.")

elif menu == "📝 Post Listing":
    st.header("📝 Post Your Property Listing")
    
    if not st.session_state.current_user:
        st.warning("Please login to post a listing")
        st.info("Don't have an account? Register first to list your property.")
    else:
        # Check if user is verified owner
        current_user = st.session_state.current_user
        user_verified = current_user in st.session_state.verified_owners
        
        if not user_verified:
            st.warning("⚠️ Owner Verification Required")
            st.info("Before posting listings, you need to verify that you're the actual property owner.")
            
            with st.expander("📋 Step 1: Verify Ownership", expanded=True):
                st.write("**Upload documents proving ownership:**")
                st.write("- Title Deed")
                st.write("- Property Rates Bill")
                st.write("- Utility Bill with your name and address")
                st.write("- Any official document showing ownership")
                
                verification_docs = st.file_uploader(
                    "Upload Ownership Documents (Max 3 files)",
                    type=['jpg', 'jpeg', 'png', 'pdf'],
                    accept_multiple_files=True,
                    key="verify_docs"
                )
                
                if verification_docs and st.button("Submit for Verification"):
                    # Convert and save documents
                    images = []
                    for doc in verification_docs[:3]:
                        if doc.type.startswith('image'):
                            images.append(Image.open(doc))
                    
                    if images:
                        verify_owner_identity(current_user, images)
                        st.success("✅ Verification submitted! Our team will review your documents within 24 hours.")
                        st.info("You can proceed to create your listing, but it won't be published until both verification and payment are approved.")
                        st.rerun()
                    else:
                        st.error("Please upload at least one image document")
        else:
            verification_status = st.session_state.verified_owners[current_user]['status']
            if verification_status == 'pending_review':
                st.warning("🕒 Verification Under Review")
                st.info("Your documents are being reviewed. You can create your listing, but it won't be published until verification is complete.")
            elif verification_status == 'verified':
                st.success("✅ Owner Verified - Ready to List!")
            elif verification_status == 'rejected':
                st.error("❌ Verification Rejected")
                st.info("Please submit new documents or contact support.")
                return
        
        # Listing form
        st.markdown("---")
        st.subheader("🏠 Property Details")
        
        with st.form("listing_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            
            with col1:
                listing_type = st.selectbox(
                    "Listing Type *",
                    ["For Rent", "For Sale"],
                    help="Select whether the property is for rent or sale"
                )
                property_type = st.selectbox(
                    "Property Type *",
                    ["House", "Apartment", "Townhouse", "Commercial", "Plot", "Farm"]
                )
                price = st.number_input(
                    f"Price (K) *",
                    min_value=0,
                    value=2000,
                    help="Monthly rent for rentals, total price for sales"
                )
                location = st.text_input("Location/Address *", placeholder="e.g., Lusaka, Kabulonga")
                
            with col2:
                bedrooms = st.number_input("Bedrooms *", min_value=0, value=3)
                bathrooms = st.number_input("Bathrooms *", min_value=0, value=2)
                area_sqft = st.number_input("Area (sq. ft.) *", min_value=0, value=1500)
            
            title = st.text_input("Property Title *", placeholder="e.g., Modern 3 Bedroom House in Kabulonga")
            description = st.text_area(
                "Description *", 
                height=120,
                placeholder="Describe your property in detail. Include features, amenities, nearby facilities, etc."
            )
            
            # Features
            st.write("**Features & Amenities**")
            features_cols = st.columns(4)
            features = []
            feature_options = [
                ("Parking", "Garden"),
                ("Security", "Swimming Pool"),
                ("Furnished", "Pet Friendly"),
                ("WiFi", "Generator"),
                ("Air Conditioning", "Water Tank"),
                ("Fenced", "Servants Quarters"),
                ("Built-in Wardrobes", "Fireplace"),
                ("Study", "Balcony")
            ]
            
            for col_idx, col in enumerate(st.columns(4)):
                with col:
                    for i in range(col_idx, len(feature_options), 4):
                        for feature in feature_options[i]:
                            if st.checkbox(feature):
                                features.append(feature)
            
            # Images
            st.write("**Property Images (Max 5)**")
            st.info("Clear, high-quality photos increase your chances of finding a tenant/buyer")
            uploaded_images = st.file_uploader(
                "Upload property photos",
                type=['jpg', 'jpeg', 'png'],
                accept_multiple_files=True,
                key="property_images"
            )
            
            # Contact info
            st.subheader("📞 Contact Information")
            user_info = st.session_state.users[current_user]
            contact_col1, contact_col2 = st.columns(2)
            with contact_col1:
                contact_phone = st.text_input(
                    "Phone Number *",
                    value=user_info.get('phone', '')
                )
            with contact_col2:
                contact_email = st.text_input(
                    "Email *",
                    value=current_user,
                    disabled=True
                )
            
            # Terms
            st.markdown("---")
            st.subheader("💰 Listing Fee: K250")
            
            agree_terms = st.checkbox(
                f"I agree to pay K250 listing fee and confirm I'm the property owner (not an agent) *"
            )
            confirm_accurate = st.checkbox(
                "I confirm that all information provided is accurate and truthful *"
            )
            
            submitted = st.form_submit_button("📤 Submit Listing", use_container_width=True)
            
            if submitted:
                if not all([title, description, location, contact_phone]):
                    st.error("Please fill in all required fields (*)")
                elif not agree_terms or not confirm_accurate:
                    st.error("You must agree to all terms and confirm accuracy")
                elif price < 100:
                    st.error("Price seems too low. Please enter a realistic price.")
                elif not uploaded_images:
                    st.warning("⚠️ No images uploaded. Listings with photos get more attention.")
                    if st.button("Submit Anyway"):
                        # Process listing without images
                        listing_data = {
                            'title': title,
                            'description': description,
                            'type': 'rent' if listing_type == "For Rent" else 'sale',
                            'property_type': property_type,
                            'price': price,
                            'location': location,
                            'bedrooms': bedrooms,
                            'bathrooms': bathrooms,
                            'area_sqft': area_sqft,
                            'features': features,
                            'contact_phone': contact_phone,
                            'contact_email': contact_email
                        }
                        
                        images = []
                        listing_id, payment_id, ref = create_pending_listing(
                            current_user,
                            listing_data,
                            images
                        )
                        
                        # Show payment instructions
                        st.session_state.show_payment_instructions = True
                        st.session_state.pending_listing_id = listing_id
                        st.session_state.payment_reference = ref
                        st.rerun()
                else:
                    # Process listing with images
                    listing_data = {
                        'title': title,
                        'description': description,
                        'type': 'rent' if listing_type == "For Rent" else 'sale',
                        'property_type': property_type,
                        'price': price,
                        'location': location,
                        'bedrooms': bedrooms,
                        'bathrooms': bathrooms,
                        'area_sqft': area_sqft,
                        'features': features,
                        'contact_phone': contact_phone,
                        'contact_email': contact_email
                    }
                    
                    # Convert uploaded images
                    images = []
                    for img in uploaded_images[:5]:
                        images.append(Image.open(img))
                    
                    listing_id, payment_id, ref = create_pending_listing(
                        current_user,
                        listing_data,
                        images
                    )
                    
                    # Show payment instructions
                    st.session_state.show_payment_instructions = True
                    st.session_state.pending_listing_id = listing_id
                    st.session_state.payment_reference = ref
                    st.rerun()

elif menu == "💰 My Payments":
    st.header("💰 My Payments & Listings Status")
    
    if not st.session_state.current_user:
        st.warning("Please login to view your payments")
    else:
        user_id = st.session_state.current_user
        
        # User's listings
        user_listings = [l for l in st.session_state.listings 
                        if l['owner_id'] == user_id]
        
        if not user_listings:
            st.info("You haven't created any listings yet.")
            if st.button("Create Your First Listing"):
                st.session_state.menu = "📝 Post Listing"
                st.rerun()
        else:
            # Summary
            active = len([l for l in user_listings if l['status'] == 'active'])
            pending = len([l for l in user_listings if l['status'] in ['pending_payment', 'awaiting_activation']])
            total_fee = sum([250 for l in user_listings if l['payment_status'] == 'verified'])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Active Listings", active)
            with col2:
                st.metric("Pending Approval", pending)
            with col3:
                st.metric("Total Paid (K)", total_fee)
            
            # Listings table
            st.subheader("My Listings")
            for listing in user_listings:
                with st.expander(f"{listing['title']} - {listing['status'].replace('_', ' ').title()}", expanded=True):
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.write(f"**Location:** {listing['location']}")
                        st.write(f"**Price:** K{listing['price']}")
                        st.write(f"**Type:** {listing['property_type']} for {listing['type']}")
                        
                    with col2:
                        status_color = {
                            'active': '✅',
                            'pending_payment': '💰',
                            'awaiting_activation': '⏳',
                            'inactive': '❌'
                        }.get(listing['status'], '❓')
                        
                        st.write(f"**Status:** {status_color} {listing['status'].replace('_', ' ').title()}")
                        st.write(f"**Payment:** {listing['payment_status'].replace('_', ' ').title()}")
                        st.write(f"**Created:** {listing['created_at'][:10]}")
                    
                    with col3:
                        if listing['status'] == 'pending_payment':
                            if st.button("Pay Now", key=f"pay_{listing['id']}", use_container_width=True):
                                st.session_state.show_payment_instructions = True
                                st.session_state.pending_listing_id = listing['id']
                                st.session_state.payment_reference = listing['payment_reference']
                                st.rerun()
                        elif listing['status'] == 'awaiting_activation':
                            st.info("⏳ Awaiting verification")
                        elif listing['status'] == 'active':
                            st.success("✅ Active")
                            if st.button("Deactivate", key=f"deact_{listing['id']}"):
                                listing['status'] = 'inactive'
                                save_data()
                                st.success("Listing deactivated")
                                st.rerun()

elif menu == "👤 My Account":
    st.header("👤 My Account")
    
    if not st.session_state.current_user:
        st.warning("Please login to view your account")
    else:
        user = st.session_state.users[st.session_state.current_user]
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Profile")
            st.write(f"**Name:** {user['name']}")
            st.write(f"**Email:** {user['email']}")
            st.write(f"**Phone:** {user['phone']}")
            st.write(f"**Member since:** {user['created_at'][:10]}")
            
            # Verification status
            if st.session_state.current_user in st.session_state.verified_owners:
                verification = st.session_state.verified_owners[st.session_state.current_user]
                if verification['status'] == 'verified':
                    st.success("✅ Verified Property Owner")
                    st.write(f"Verified on: {verification['verification_date'][:10]}")
                elif verification['status'] == 'pending_review':
                    st.warning("⏳ Verification Pending Review")
                elif verification['status'] == 'rejected':
                    st.error("❌ Verification Rejected")
                    if st.button("Resubmit Documents"):
                        st.session_state.resubmit_verification = True
                        st.rerun()
            else:
                st.warning("⚠️ Not Verified")
                st.info("Verify ownership to post listings")
        
        with col2:
            st.subheader("Account Statistics")
            user_listings = [l for l in st.session_state.listings 
                           if l['owner_id'] == st.session_state.current_user]
            
            if user_listings:
                # Create metrics
                df_listings = pd.DataFrame(user_listings)
                
                # Active vs inactive
                status_counts = df_listings['status'].value_counts()
                
                fig_col1, fig_col2 = st.columns(2)
                with fig_col1:
                    st.metric("Total Listings", len(user_listings))
                    st.metric("Active Listings", len([l for l in user_listings if l['status'] == 'active']))
                
                with fig_col2:
                    total_value = sum([l['price'] for l in user_listings if l['status'] == 'active'])
                    avg_price = total_value / max(len([l for l in user_listings if l['status'] == 'active']), 1)
                    st.metric("Total Value (K)", f"{total_value:,.0f}")
                    st.metric("Average Price (K)", f"{avg_price:,.0f}")
                
                # Listings table
                st.subheader("My Listings")
                for listing in user_listings[:5]:
                    status_icon = "✅" if listing['status'] == 'active' else "⏳" if listing['status'] == 'awaiting_activation' else "💰" if listing['status'] == 'pending_payment' else "❌"
                    st.write(f"{status_icon} **{listing['title']}** - K{listing['price']} - {listing['status'].replace('_', ' ').title()}")
                
                if len(user_listings) > 5:
                    st.write(f"... and {len(user_listings) - 5} more")
            else:
                st.info("You haven't posted any listings yet.")
                if st.button("Post Your First Listing", use_container_width=True):
                    st.session_state.menu = "📝 Post Listing"
                    st.rerun()

elif menu == "💬 Messages":
    st.header("💬 Messages")
    
    if not st.session_state.current_user:
        st.warning("Please login to view messages")
    else:
        # Filter messages for current user
        user_messages = [
            m for m in st.session_state.messages 
            if m['sender_id'] == st.session_state.current_user 
            or m['receiver_id'] == st.session_state.current_user
        ]
        
        if user_messages:
            # Group messages by conversation
            conversations = {}
            for msg in user_messages:
                other_user = msg['sender_id'] if msg['sender_id'] != st.session_state.current_user else msg['receiver_id']
                listing_id = msg['listing_id']
                conv_key = f"{other_user}_{listing_id}"
                
                if conv_key not in conversations:
                    listing = next((l for l in st.session_state.listings if l['id'] == listing_id), None)
                    conversations[conv_key] = {
                        'other_user': other_user,
                        'listing': listing,
                        'messages': []
                    }
                conversations[conv_key]['messages'].append(msg)
            
            # Display conversations
            for conv_key, conv_data in conversations.items():
                conv_data['messages'].sort(key=lambda x: x['timestamp'])
                latest_msg = conv_data['messages'][-1]
                listing_title = conv_data['listing']['title'] if conv_data['listing'] else "Unknown Listing"
                
                with st.expander(f"📧 {listing_title[:30]}... with {conv_data['other_user'][:20]}", expanded=False):
                    # Display all messages
                    for msg in conv_data['messages']:
                        is_sender = msg['sender_id'] == st.session_state.current_user
                        timestamp = datetime.datetime.fromisoformat(msg['timestamp']).strftime("%b %d, %H:%M")
                        
                        if is_sender:
                            st.markdown(f"""
                            <div style='text-align: right; margin: 5px 0;'>
                                <div style='background-color: #0d6efd; color: white; padding: 8px 12px; border-radius: 18px 18px 0 18px; display: inline-block; max-width: 70%;'>
                                    {msg['message']}
                                </div>
                                <div style='font-size: 0.8em; color: #666; text-align: right;'>
                                    {timestamp}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div style='text-align: left; margin: 5px 0;'>
                                <div style='background-color: #e9ecef; color: #333; padding: 8px 12px; border-radius: 18px 18px 18px 0; display: inline-block; max-width: 70%;'>
                                    {msg['message']}
                                </div>
                                <div style='font-size: 0.8em; color: #666;'>
                                    {timestamp}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Reply form
                    with st.form(key=f"reply_{conv_key}"):
                        new_message = st.text_area("Your message", key=f"msg_{conv_key}")
                        col_btn1, col_btn2 = st.columns([3, 1])
                        with col_btn2:
                            if st.form_submit_button("Send", use_container_width=True):
                                if new_message.strip():
                                    send_message(
                                        st.session_state.current_user,
                                        conv_data['other_user'],
                                        latest_msg['listing_id'],
                                        new_message
                                    )
                                    st.success("Message sent!")
                                    st.rerun()
        else:
            st.info("No messages yet. Start a conversation by contacting a property owner or tenant.")

elif menu == "⚠️ Report":
    st.header("⚠️ Report Content")
    
    if not st.session_state.current_user:
        st.warning("Please login to submit a report")
    else:
        with st.form("report_form"):
            report_type = st.selectbox(
                "Type of Report *",
                ["Select...", "Fake Listing", "Agent Pretending to be Owner", 
                 "Inappropriate Content", "Scam Attempt", "Wrong Information",
                 "Duplicate Listing", "Already Rented/Sold", "Other"]
            )
            
            if report_type == "Select...":
                st.stop()
            
            # Select listing
            listing_options = ["Select a listing..."] + [f"{l['title']} - {l['location']}" for l in st.session_state.listings]
            selected_listing = st.selectbox("Related Listing", listing_options)
            
            description = st.text_area(
                "Please describe the issue in detail *",
                height=100,
                placeholder="Provide as much detail as possible to help us investigate..."
            )
            
            # Upload evidence
            evidence_files = st.file_uploader(
                "Upload evidence (screenshots, documents)",
                type=['jpg', 'jpeg', 'png', 'pdf'],
                accept_multiple_files=True,
                help="Optional: Upload screenshots or documents supporting your report"
            )
            
            submitted = st.form_submit_button("Submit Report", use_container_width=True)
            
            if submitted:
                if report_type == "Select...":
                    st.error("Please select a report type")
                elif not description:
                    st.error("Please describe the issue")
                else:
                    # Find listing ID
                    listing_id = None
                    if selected_listing != "Select a listing...":
                        # Extract listing from selection
                        for listing in st.session_state.listings:
                            if f"{listing['title']} - {listing['location']}" == selected_listing:
                                listing_id = listing['id']
                                break
                    
                    report_id = report_content(
                        st.session_state.current_user,
                        'listing' if listing_id else 'user',
                        listing_id or 'general',
                        f"{report_type}: {description}"
                    )
                    
                    # Save evidence if provided
                    if evidence_files:
                        evidence_dir = DATA_DIR / "report_evidence" / report_id
                        evidence_dir.mkdir(parents=True, exist_ok=True)
                        
                        for i, file in enumerate(evidence_files):
                            file_path = evidence_dir / f"evidence_{i}.{file.name.split('.')[-1]}"
                            with open(file_path, 'wb') as f:
                                f.write(file.getvalue())
                    
                    st.success(f"✅ Report submitted successfully! Reference: **REPORT-{report_id[:8].upper()}**")
                    st.info("Our team will review your report within 24-48 hours. Thank you for helping keep Uhoues safe!")

elif menu == "🛡️ Admin Panel":
    if not st.session_state.admin_mode:
        st.error("Access Denied")
        st.stop()
    
    st.header("🛡️ Admin Panel")
    
    admin_tabs = st.tabs(["📋 Pending Approvals", "👤 User Management", "⚠️ Reports", "📊 Statistics"])
    
    with admin_tabs[0]:
        st.subheader("Pending Approvals")
        
        # Pending payments
        pending_payments = [p for p in st.session_state.pending_payments.values() 
                          if p['status'] == 'awaiting_verification']
        
        if pending_payments:
            st.write(f"**Payments Pending Verification:** {len(pending_payments)}")
            
            for payment in pending_payments:
                listing = next((l for l in st.session_state.listings if l['id'] == payment['listing_id']), None)
                owner = st.session_state.users.get(payment['owner_id'], {})
                
                with st.expander(f"Payment: {payment['reference']} - {owner.get('name', 'Unknown')}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Payment Details:**")
                        st.write(f"Amount: K{payment['amount']}")
                        st.write(f"Reference: {payment['reference']}")
                        st.write(f"Date: {payment['created_at'][:10]}")
                        
                        if payment.get('proof_image'):
                            try:
                                proof_img = Image.open(payment['proof_image'])
                                st.image(proof_img, caption="Payment Proof", width=300)
                            except:
                                st.write("Proof image not available")
                    
                    with col2:
                        if listing:
                            st.write("**Listing Details:**")
                            st.write(f"Title: {listing['title']}")
                            st.write(f"Price: K{listing['price']}")
                            st.write(f"Location: {listing['location']}")
                    
                    # Approval buttons
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    with col_btn1:
                        if st.button("✅ Approve", key=f"approve_{payment['payment_id']}", use_container_width=True):
                            success, msg = approve_payment(payment['payment_id'])
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    with col_btn2:
                        if st.button("❌ Reject", key=f"reject_{payment['payment_id']}", use_container_width=True):
                            payment['status'] = 'rejected'
                            if listing:
                                listing['status'] = 'payment_rejected'
                            save_data()
                            st.success("Payment rejected")
                            st.rerun()
                    with col_btn3:
                        if st.button("📝 Request More Info", key=f"info_{payment['payment_id']}", use_container_width=True):
                            st.info("Feature to be implemented: Send message to user requesting more information")
        else:
            st.success("No pending payments to review!")
        
        # Pending verifications
        st.subheader("Pending Owner Verifications")
        pending_verifications = {k: v for k, v in st.session_state.verified_owners.items() 
                               if v['status'] == 'pending_review'}
        
        if pending_verifications:
            for user_email, verification in pending_verifications.items():
                user = st.session_state.users.get(user_email, {})
                
                with st.expander(f"Verification: {user.get('name', 'Unknown')} ({user_email})"):
                    # Display documents
                    if verification.get('documents'):
                        st.write("**Submitted Documents:**")
                        cols = st.columns(min(3, len(verification['documents'])))
                        for i, doc_path in enumerate(verification['documents'][:3]):
                            with cols[i % 3]:
                                try:
                                    doc_img = Image.open(doc_path)
                                    st.image(doc_img, caption=f"Document {i+1}", use_column_width=True)
                                except:
                                    st.write(f"Document {i+1}: Unable to display")
                    
                    # Verification buttons
                    col_v1, col_v2 = st.columns(2)
                    with col_v1:
                        if st.button("✅ Verify Owner", key=f"verify_{user_email}", use_container_width=True):
                            verification['status'] = 'verified'
                            verification['verified_at'] = datetime.datetime.now().isoformat()
                            verification['verified_by'] = 'admin'
                            save_data()
                            st.success("Owner verified!")
                            st.rerun()
                    with col_v2:
                        if st.button("❌ Reject Verification", key=f"reject_ver_{user_email}", use_container_width=True):
                            verification['status'] = 'rejected'
                            save_data()
                            st.success("Verification rejected")
                            st.rerun()
        else:
            st.success("No pending verifications to review!")
    
    with admin_tabs[1]:
        st.subheader("User Management")
        
        search_user = st.text_input("Search users by email or name")
        users_list = list(st.session_state.users.items())
        
        if search_user:
            users_list = [(email, user) for email, user in users_list 
                         if search_user.lower() in email.lower() 
                         or search_user.lower() in user.get('name', '').lower()]
        
        for email, user in users_list:
            with st.expander(f"{user.get('name', 'Unknown')} - {email}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Name:** {user.get('name', 'N/A')}")
                    st.write(f"**Phone:** {user.get('phone', 'N/A')}")
                    st.write(f"**Joined:** {user.get('created_at', 'N/A')[:10]}")
                    
                    # Verification status
                    if email in st.session_state.verified_owners:
                        verification = st.session_state.verified_owners[email]
                        st.write(f"**Verification:** {verification['status'].replace('_', ' ').title()}")
                    else:
                        st.write("**Verification:** Not submitted")
                
                with col2:
                    # User's listings
                    user_listings = [l for l in st.session_state.listings if l['owner_id'] == email]
                    st.write(f"**Listings:** {len(user_listings)}")
                    active_listings = [l for l in user_listings if l['status'] == 'active']
                    st.write(f"**Active:** {len(active_listings)}")
                    
                    # Actions
                    if st.button("Suspend User", key=f"suspend_{email}"):
                        st.warning(f"Suspending user {email} - Feature to be implemented")
    
    with admin_tabs[2]:
        st.subheader("User Reports")
        
        pending_reports = [r for r in st.session_state.reports if r['status'] == 'pending']
        
        if pending_reports:
            st.write(f"**Pending Reports:** {len(pending_reports)}")
            
            for report in pending_reports:
                reporter = st.session_state.users.get(report['reporter_id'], {})
                
                with st.expander(f"Report {report['id'][:8]} - {report['reason'][:50]}..."):
                    st.write(f"**Reporter:** {reporter.get('name', 'Unknown')} ({report['reporter_id']})")
                    st.write(f"**Type:** {report['content_type']}")
                    st.write(f"**Reason:** {report['reason']}")
                    st.write(f"**Date:** {report['timestamp'][:10]}")
                    
                    # Resolve buttons
                    col_r1, col_r2 = st.columns(2)
                    with col_r1:
                        if st.button("✅ Resolve", key=f"resolve_{report['id']}", use_container_width=True):
                            report['status'] = 'resolved'
                            report['resolved_at'] = datetime.datetime.now().isoformat()
                            save_data()
                            st.success("Report resolved")
                            st.rerun()
                    with col_r2:
                        if st.button("❌ Dismiss", key=f"dismiss_{report['id']}", use_container_width=True):
                            report['status'] = 'dismissed'
                            save_data()
                            st.success("Report dismissed")
                            st.rerun()
        else:
            st.success("No pending reports!")
    
    with admin_tabs[3]:
        st.subheader("Platform Statistics")
        
        # Calculate statistics
        total_users = len(st.session_state.users)
        total_listings = len(st.session_state.listings)
        active_listings = len([l for l in st.session_state.listings if l['status'] == 'active'])
        total_revenue = len([l for l in st.session_state.listings if l['payment_status'] == 'verified']) * 250
        verified_owners = len([v for v in st.session_state.verified_owners.values() if v['status'] == 'verified'])
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Users", total_users)
            st.metric("Verified Owners", verified_owners)
        with col2:
            st.metric("Total Listings", total_listings)
            st.metric("Active Listings", active_listings)
        with col3:
            st.metric("Total Revenue (K)", total_revenue)
            st.metric("Avg per User", f"K{total_revenue/max(total_users, 1):.0f}")
        
        # Recent activity
        st.subheader("Recent Activity")
        recent_listings = sorted(st.session_state.listings, 
                               key=lambda x: x['created_at'], 
                               reverse=True)[:10]
        
        for listing in recent_listings:
            owner = st.session_state.users.get(listing['owner_id'], {})
            status_color = {
                'active': '🟢',
                'pending_payment': '🟡',
                'awaiting_activation': '🟠',
                'inactive': '🔴'
            }.get(listing['status'], '⚪')
            
            st.write(f"{status_color} {listing['title'][:30]}... - {owner.get('name', 'Unknown')} - {listing['created_at'][:10]}")

elif menu == "ℹ️ About":
    st.header("ℹ️ About Uhoues")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ## 🏠 Uhoues - Direct Owner Property Platform
        
        **Our Mission:** To connect property owners directly with tenants and buyers, 
        eliminating agent commissions and ensuring transparency in the Zambian property market.
        
        ### 🌟 Why Choose Uhoues?
        
        - ✅ **Owner-Only Platform**: Strictly no agents allowed
        - ✅ **Manual Verification**: Every owner is manually verified
        - ✅ **Fixed Low Fee**: Only K250 per listing (no hidden charges)
        - ✅ **Secure Communication**: Built-in messaging system
        - ✅ **Payment Security**: Manual verification of all payments
        - ✅ **Local Support**: Designed for the Zambian market
        
        ### 💰 How Payments Work:
        
        1. **Create your listing** with all property details
        2. **Receive payment instructions** with unique reference number
        3. **Send K250** via Mobile Money to our account
        4. **Upload payment screenshot** as proof
        5. **Our team verifies** payment within 24 hours
        6. **Listing goes live** immediately after verification
        
        ### 📱 Payment Methods:
        
        We accept all major Zambian Mobile Money platforms:
        
        - **MTN Mobile Money**: Send to **0769 939 546** or **0960 168 307**
        - **Airtel Money**: Send to **0772 566 084**
        
        **Reference Format:** UHOUSE_[YOUR_EMAIL_SHORTCODE]
        
        ### 🛡️ Our Verification Process:
        
        1. **Owner Identity**: Document verification (Title Deeds, Utility Bills)
        2. **Payment Verification**: Manual check of all payment proofs
        3. **Listing Review**: Quality check of all property listings
        4. **Continuous Monitoring**: Regular checks for compliance
        
        ### 📞 Contact & Support:
        
        - **Email**: support@uhoues.co.zm
        - **Phone**: +260 76 993 9546 (9am-5pm, Mon-Fri)
        - **WhatsApp**: +260 76 993 9546
        - **Address**: Lusaka, Zambia
        
        *Uhoues - Making property transactions direct, transparent, and affordable for Zambians.*
        """)
    
    with col2:
        st.image("https://via.placeholder.com/300x400/0d6efd/ffffff?text=UHOUSES", 
                caption="Uhoues - Direct Property Listings")
        
        st.markdown("""
        ### 📋 Quick Stats
        
        - **Founded**: 2024
        - **Listings**: 100+
        - **Users**: 500+
        - **Cities**: Lusaka, Ndola, Kitwe, Livingstone
        - **Success Rate**: 95%
        
        ### ⏰ Support Hours
        
        **Monday - Friday**: 9:00 AM - 5:00 PM  
        **Saturday**: 10:00 AM - 2:00 PM  
        **Sunday**: Closed
        
        ### 🔒 Our Promise
        
        - No agent commissions
        - No hidden fees
        - Manual verification of all listings
        - 24-hour support response
        - Secure platform
        """)

# Handle payment instructions popup
if 'show_payment_instructions' in st.session_state and st.session_state.show_payment_instructions:
    # Create a modal-like effect
    st.markdown("""
    <style>
    .payment-modal {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        padding: 30px;
        border-radius: 10px;
        box-shadow: 0 0 20px rgba(0,0,0,0.3);
        z-index: 1000;
        max-width: 600px;
        width: 90%;
    }
    .modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.5);
        z-index: 999;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="modal-overlay"></div>', unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="payment-modal">', unsafe_allow_html=True)
        
        st.header("💰 Payment Instructions")
        st.markdown("---")
        
        listing = next((l for l in st.session_state.listings 
                       if l['id'] == st.session_state.pending_listing_id), None)
        
        if listing:
            st.success(f"✅ Listing created successfully!")
            st.write(f"**Reference:** `{st.session_state.payment_reference}`")
            st.write(f"**Amount:** **K250**")
            
            st.markdown(f"""
            ### 📱 How to Pay:
            
            1. **Send K250 via Mobile Money** to:
               - **MTN Mobile Money**: `0769 939 546` or `0960 168 307`
               - **Airtel Money**: `0772 566 084`
            
            2. **Use this exact reference**: `{st.session_state.payment_reference}`
            
            3. **Take a screenshot** of the successful transaction
            
            4. **Upload the screenshot** below
            
            5. **We'll verify** within 24 hours and activate your listing
            
            ⚠️ **Important:** Without correct reference, we cannot verify your payment!
            """)
            
            # Upload payment proof
            st.markdown("---")
            st.subheader("📸 Upload Payment Proof")
            
            payment_proof = st.file_uploader(
                "Upload screenshot of transaction",
                type=['jpg', 'jpeg', 'png'],
                key="payment_proof_upload"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Submit Proof", use_container_width=True):
                    if payment_proof:
                        proof_img = Image.open(payment_proof)
                        success, message = activate_listing(
                            st.session_state.pending_listing_id,
                            proof_img
                        )
                        if success:
                            st.success(message)
                            del st.session_state.show_payment_instructions
                            del st.session_state.pending_listing_id
                            st.rerun()
                        else:
                            st.error(message)
                    else:
                        st.error("Please upload payment proof")
            
            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    del st.session_state.show_payment_instructions
                    del st.session_state.pending_listing_id
                    st.rerun()
            
            st.info("Need help? Call +260 76 993 9546 or WhatsApp +260 76 993 9546")
        
        st.markdown('</div>', unsafe_allow_html=True)

# Handle selected listing view
if 'selected_listing' in st.session_state:
    listing = next((l for l in st.session_state.listings if l['id'] == st.session_state.selected_listing), None)
    if listing and listing['status'] == 'active':
        st.header("🏠 Property Details")
        
        # Back button
        if st.button("← Back to Listings"):
            del st.session_state.selected_listing
            st.rerun()
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Display images in carousel
            if listing['images']:
                tab_names = [f"Image {i+1}" for i in range(min(5, len(listing['images'])))]
                tabs = st.tabs(tab_names)
                
                for i, tab in enumerate(tabs[:5]):
                    with tab:
                        try:
                            img = Image.open(listing['images'][i])
                            st.image(img, use_column_width=True)
                        except:
                            st.image("https://via.placeholder.com/600x400?text=Property+Image", use_column_width=True)
            else:
                st.image("https://via.placeholder.com/600x400?text=No+Images+Available", use_column_width=True)
        
        with col2:
            # Property badge
            badge_col1, badge_col2 = st.columns(2)
            with badge_col1:
                if listing.get('verified', False):
                    st.success("✅ Verified Owner")
            with badge_col2:
                st.markdown(f"### K{listing['price']}")
                st.caption("/month" if listing['type'] == 'rent' else "total price")
            
            st.markdown(f"### {listing['title']}")
            st.markdown(f"📍 **Location:** {listing['location']}")
            st.markdown(f"🏠 **Property Type:** {listing['property_type']}")
            st.markdown(f"📋 **Listing Type:** {listing['type'].title()}")
            
            st.markdown("---")
            
            # Features
            st.markdown("#### Features")
            if listing['features']:
                features_cols = st.columns(3)
                for i, feature in enumerate(listing['features']):
                    with features_cols[i % 3]:
                        st.write(f"✅ {feature}")
            else:
                st.info("No features listed")
            
            st.markdown("---")
            
            # Contact
            st.markdown("#### 📞 Contact Owner")
            st.write(f"**Phone:** {listing['contact_phone']}")
            st.write(f"**Email:** {listing['contact_email']}")
            
            if st.session_state.current_user:
                with st.form("contact_form_sidebar"):
                    message = st.text_area("Your message to the owner", 
                                         placeholder="I'm interested in your property...")
                    if st.form_submit_button("Send Message", use_container_width=True):
                        if message:
                            send_message(
                                st.session_state.current_user,
                                listing['owner_id'],
                                listing['id'],
                                message
                            )
                            st.success("Message sent to owner!")
            else:
                st.info("Login to contact the owner")
        
        # Full description
        st.markdown("---")
        st.markdown("### 📝 Description")
        st.write(listing['description'])
        
        # Property details table
        st.markdown("### 📊 Property Details")
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            st.metric("Bedrooms", listing['bedrooms'])
            st.metric("Area", f"{listing['area_sqft']} sq. ft.")
        with col_d2:
            st.metric("Bathrooms", listing['bathrooms'])
            st.metric("Status", "Available")
        with col_d3:
            st.metric("Listed", listing['created_at'][:10])
            st.metric("Owner", "Verified" if listing.get('verified') else "Unverified")
    
    elif listing and listing['status'] != 'active':
        st.warning("This listing is not currently active.")
        if st.button("Back to Listings"):
            del st.session_state.selected_listing
            st.rerun()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9em; padding: 20px;'>
        <p>🏠 <strong>Uhoues</strong> &copy; 2024 • Direct Owner Property Listings • Strictly No Agents</p>
        <p>📍 Zambian Owned • K250 Listing Fee • Payment via Mobile Money</p>
        <p>📞 Support: +260 76 993 9546 • 📧 support@uhoues.co.zm</p>
        <p style='font-size: 0.8em; margin-top: 10px;'>
            <a href='#' style='color: #666; text-decoration: none; margin: 0 10px;'>Terms</a> • 
            <a href='#' style='color: #666; text-decoration: none; margin: 0 10px;'>Privacy</a> • 
            <a href='#' style='color: #666; text-decoration: none; margin: 0 10px;'>FAQ</a> • 
            <a href='#' style='color: #666; text-decoration: none; margin: 0 10px;'>Contact</a>
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# Save data periodically
save_data()
