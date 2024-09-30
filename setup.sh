#!/bin/bash

# Create necessary directories
mkdir -p ~/.streamlit/

# Create Streamlit config with theme settings
cat <<EOL > ~/.streamlit/config.toml
[theme]
base='light'
primaryColor='#04b6ea'

[server]
headless = true
port = $PORT
enableCORS = false
enableXsrfProtection = false

[browser]
serverAddress = "0.0.0.0"
serverPort = $PORT
EOL

# Copy static files
mkdir -p ~/.streamlit/static
cp -r $(pip show streamlit-cookies-controller | grep Location | awk '{print $2}')/streamlit_cookies_controller/frontend/build/* ~/.streamlit/static/

# Add HTTPS redirect script
cat <<EOF > ~/.streamlit/https_redirect.py
import streamlit as st

def check_https():
    if not st.session_state.get('https_redirect'):
        proto = st.request.headers.get('X-Forwarded-Proto')
        if proto and proto == 'http':
            st.session_state['https_redirect'] = True
            st.experimental_rerun()

check_https()
EOF
