#!/bin/bash

# Create necessary directories
mkdir -p ~/.streamlit/

# Create Streamlit config
echo "[server]
headless = true
port = $PORT
enableCORS = false
enableXsrfProtection = false

[browser]
serverAddress = \"0.0.0.0\"
serverPort = $PORT
" > ~/.streamlit/config.toml

# Copy static files
mkdir -p ~/.streamlit/static
cp -r $(pip show streamlit-cookies-controller | grep Location | cut -d ' ' -f 2)/streamlit_cookies_controller/frontend/build/* ~/.streamlit/static/

# Add HTTPS redirect script
echo "
import streamlit as st

def check_https():
    if not st.session_state.get('https_redirect'):
        proto = st.query_params.get('x-forwarded-proto')
        if proto and proto[0] == 'http':
            st.query_params['x-forwarded-proto'] = ['https']
            st.session_state['https_redirect'] = True
            st.rerun()

check_https()
" > ~/.streamlit/https_redirect.py