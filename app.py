# ==================== PWA SETUP - UHOUES BRANDING ====================
import streamlit as st

st.markdown("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    
    <!-- UHOUES BRANDING - REPLACES STREAMLIT -->
    <meta name="application-name" content="Uhoues">
    <meta name="apple-mobile-web-app-title" content="Uhoues">
    <meta name="msapplication-tooltip" content="Uhoues Property Listings">
    
    <!-- THEME -->
    <meta name="theme-color" content="#0d6efd">
    <meta name="msapplication-navbutton-color" content="#0d6efd">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    
    <!-- DESCRIPTION -->
    <meta name="description" content="Uhoues - Direct owner property listings in Zambia. No agents, K250 fee only.">
    <meta name="keywords" content="property, real estate, Zambia, rent, buy, house, apartment, Lusaka">
    
    <!-- MANIFEST -->
    <link rel="manifest" href="/manifest.json" crossorigin="use-credentials">
    
    <!-- ICONS - UHOUES LOGO -->
    <link rel="icon" type="image/png" sizes="192x192" href="https://img.icons8.com/color/192/000000/home--v1.png">
    <link rel="icon" type="image/png" sizes="512x512" href="https://img.icons8.com/color/512/000000/home--v1.png">
    <link rel="apple-touch-icon" sizes="180x180" href="https://img.icons8.com/color/180/000000/home--v1.png">
    
    <!-- MICROSOFT TILES -->
    <meta name="msapplication-TileColor" content="#0d6efd">
    <meta name="msapplication-TileImage" content="https://img.icons8.com/color/144/000000/home--v1.png">
    <meta name="msapplication-square70x70logo" content="https://img.icons8.com/color/70/000000/home--v1.png">
    <meta name="msapplication-square150x150logo" content="https://img.icons8.com/color/150/000000/home--v1.png">
    
    <!-- PWA CAPABILITIES -->
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    
    <!-- OPEN GRAPH (for social sharing) -->
    <meta property="og:title" content="Uhoues Property Listings">
    <meta property="og:description" content="Direct owner property listings in Zambia">
    <meta property="og:image" content="https://img.icons8.com/color/512/000000/home--v1.png">
    <meta property="og:url" content="https://uhoues.streamlit.app/">
    <meta property="og:type" content="website">
    
    <!-- TWITTER CARD -->
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="Uhoues Property">
    <meta name="twitter:description" content="Direct owner property listings">
    <meta name="twitter:image" content="https://img.icons8.com/color/512/000000/home--v1.png">
    
    <!-- PWA INSTALL PROMPT -->
    <script>
    // Detect if app is installed
    window.addEventListener('DOMContentLoaded', () => {
        if (window.matchMedia('(display-mode: standalone)').matches) {
            console.log('Uhoues app is installed and running in standalone mode');
        }
    });
    
    // Handle install prompt
    let deferredPrompt;
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        
        // Show custom install button (optional)
        setTimeout(() => {
            if (deferredPrompt) {
                const installBtn = document.createElement('button');
                installBtn.innerHTML = '📱 Install Uhoues App';
                installBtn.style.cssText = `
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    background: #0d6efd;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 25px;
                    z-index: 9999;
                    cursor: pointer;
                    box-shadow: 0 4px 12px rgba(13, 110, 253, 0.3);
                `;
                installBtn.onclick = () => {
                    deferredPrompt.prompt();
                    deferredPrompt.userChoice.then(() => {
                        document.body.removeChild(installBtn);
                        deferredPrompt = null;
                    });
                };
                document.body.appendChild(installBtn);
            }
        }, 3000);
    });
    
    // Service Worker for offline capability
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/service-worker.js')
                .then(reg => console.log('Uhoues Service Worker registered:', reg))
                .catch(err => console.log('Uhoues Service Worker registration failed:', err));
        });
    }
    </script>
    
    <!-- STYLES FOR INSTALLED APP -->
    <style>
    /* Custom styles when app is installed */
    @media (display-mode: standalone) {
        /* Remove Streamlit branding */
        section[data-testid="stSidebar"] > div:first-child {
            background: linear-gradient(180deg, #0d6efd 0%, #0a58ca 100%) !important;
        }
        
        /* Custom header for installed app */
        .installed-app-header::before {
            content: "🏠 Uhoues";
            font-size: 1.5em;
            font-weight: bold;
            color: white;
        }
    }
    
    /* Hide Streamlit branding */
    .stApp > header {
        display: none !important;
    }
    
    /* Custom install button style */
    .uhoues-install-btn {
        background: #0d6efd !important;
        color: white !important;
        border-radius: 25px !important;
        padding: 10px 20px !important;
        border: none !important;
        font-weight: bold !important;
    }
    </style>
    
    <!-- TITLE -->
    <title>Uhoues Property Listings</title>
</head>
<body>
""", unsafe_allow_html=True)
