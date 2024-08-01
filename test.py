import streamlit as st
from streamlit_cookies_controller import CookieController

st.set_page_config('Cookie QuickStart', '🍪', layout='wide')

controller = CookieController()

# Set a cookie
controller.set('cookie_name', 'testing')

# Get all cookies
cookies = controller.getAll()

# Get a cookie
cookie = controller.get('cookie_name')

# Remove a cookie
controller.remove('cookie_name')

print(controller)
print(cookies)
print(cookie)