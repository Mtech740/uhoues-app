import streamlit as st
import pandas as pd
from PIL import Image
import json
import datetime

# App Configuration
st.set_page_config(
    page_title="Uhoues - Direct Owner Property Listings",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'listings' not in st.session_state:
    st.session_state.listings = []
if 'users' not in st.session_state:
    st.session_state.users = {}
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# Main App
st.title("🏠 Uhoues - Direct Owner Property Listings")
st.markdown("### No Agents Allowed • K250 Listing Fee • Payment by Mobile Money")

# Sidebar navigation
st.sidebar.title("Navigation")
menu = st.sidebar.radio("Go to", ["🏠 Browse Listings", "📝 Post Listing", "👤 My Account"])

# Simple authentication
st.sidebar.markdown("---")
if st.session_state.current_user:
    st.sidebar.success(f"👋 Welcome, {st.session_state.current_user}")
    if st.sidebar.button("Logout"):
        st.session_state.current_user = None
        st.rerun()
else:
    st.sidebar.write("**Login/Register**")
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Login"):
            if email and password:
                st.session_state.current_user = email
                st.session_state.users[email] = {
                    'name': email.split('@')[0],
                    'email': email,
                    'created_at': datetime.datetime.now().isoformat()
                }
                st.success("Logged in!")
                st.rerun()
    with col2:
        if st.button("Register"):
            if email and password:
                st.session_state.current_user = email
                st.session_state.users[email] = {
                    'name': email.split('@')[0],
                    'email': email,
                    'created_at': datetime.datetime.now().isoformat()
                }
                st.success("Registered!")
                st.rerun()

# Main content based on menu
if menu == "🏠 Browse Listings":
    st.header("Browse Properties")
    st.info("Listings will appear here. Currently in development.")
    
    # Sample listing
    with st.container(border=True):
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image("https://via.placeholder.com/300x200?text=Property+Image", use_column_width=True)
        with col2:
            st.subheader("Modern 3 Bedroom House")
            st.write("📍 Kabulonga, Lusaka")
            st.write("🏠 House • For Rent")
            st.write("🛏️ 3 bed • 🛁 2 bath")
            st.write("**K2,500/month**")
            if st.button("View Details", key="sample"):
                st.info("Details feature coming soon!")

elif menu == "📝 Post Listing":
    st.header("Post Your Property")
    
    if not st.session_state.current_user:
        st.warning("Please login to post a listing")
    else:
        with st.form("listing_form"):
            st.subheader("Property Details")
            
            title = st.text_input("Property Title")
            location = st.text_input("Location")
            price = st.number_input("Price (K)", min_value=0, value=2000)
            bedrooms = st.number_input("Bedrooms", min_value=0, value=3)
            
            listing_type = st.selectbox("Listing Type", ["For Rent", "For Sale"])
            property_type = st.selectbox("Property Type", ["House", "Apartment", "Townhouse"])
            
            description = st.text_area("Description")
            
            # Payment instructions
            st.markdown("---")
            st.subheader("💰 Listing Fee: K250")
            st.write("**Payment Methods:**")
            st.write("- MTN Mobile Money: 0769 939 546 or 0960 168 307")
            st.write("- Airtel Money: 0772 566 084")
            st.write("**Reference:** UHOUSE_[YOUR_EMAIL]")
            
            agree = st.checkbox("I agree to pay K250 listing fee")
            
            if st.form_submit_button("Submit Listing"):
                if agree and title and location:
                    # Create simple listing
                    listing = {
                        'title': title,
                        'location': location,
                        'price': price,
                        'bedrooms': bedrooms,
                        'type': 'rent' if listing_type == "For Rent" else 'sale',
                        'property_type': property_type,
                        'description': description,
                        'owner': st.session_state.current_user,
                        'created_at': datetime.datetime.now().isoformat(),
                        'status': 'pending_payment'
                    }
                    st.session_state.listings.append(listing)
                    st.success("✅ Listing created! Please send K250 to activate.")
                    st.info("Upload payment screenshot in 'My Account' after payment")
                else:
                    st.error("Please fill all required fields and agree to terms")

elif menu == "👤 My Account":
    st.header("My Account")
    
    if not st.session_state.current_user:
        st.warning("Please login")
    else:
        user = st.session_state.users.get(st.session_state.current_user, {})
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Profile")
            st.write(f"**Email:** {st.session_state.current_user}")
            st.write(f"**Name:** {user.get('name', 'Not set')}")
            st.write(f"**Member since:** {user.get('created_at', 'Today')[:10]}")
        
        with col2:
            st.subheader("My Listings")
            user_listings = [l for l in st.session_state.listings if l.get('owner') == st.session_state.current_user]
            
            if user_listings:
                for listing in user_listings:
                    st.write(f"🏠 **{listing['title']}** - K{listing['price']} - {listing['status']}")
            else:
                st.info("No listings yet")
                if st.button("Create First Listing"):
                    st.session_state.menu = "📝 Post Listing"
                    st.rerun()
        
        # Payment proof upload
        st.markdown("---")
        st.subheader("📸 Upload Payment Proof")
        st.write("After sending K250, upload screenshot here:")
        
        payment_proof = st.file_uploader("Upload payment screenshot", type=['jpg', 'jpeg', 'png'])
        if payment_proof and st.button("Submit Proof"):
            st.success("Payment proof submitted! We'll verify within 24 hours.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>🏠 <strong>Uhoues</strong> &copy; 2024 • Direct Owner Property Listings</p>
        <p>📍 Zambian Owned • K250 Listing Fee • Payment via Mobile Money</p>
        <p>📞 Support: +260 76 993 9546</p>
    </div>
    """,
    unsafe_allow_html=True
              )
