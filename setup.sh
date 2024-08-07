#!/bin/bash

# Create necessary directories
mkdir -p ~/.streamlit/

# Create Streamlit config
echo "[server]
headless = true
port = $PORT
enableCORS = false
enableXsrfProtection = false
" > ~/.streamlit/config.toml

# Copy static files
mkdir -p ~/.streamlit/static
cp -r $(pip show streamlit-cookies-controller | grep Location | cut -d ' ' -f 2)/streamlit_cookies_controller/frontend/build/* ~/.streamlit/static/