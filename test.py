import streamlit as st
from streamlit.web.server.websocket_headers import _get_websocket_headers

headers = _get_websocket_headers()
print(headers)
st.write(headers)