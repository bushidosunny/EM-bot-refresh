import streamlit as st

with st.sidebar:

    long_text = "This is a very long string of text " * 10

    st.text("Using st.text: " + long_text)
    st.markdown("Using st.markdown: " + long_text) 
    st.sidebar.write("Using st.write: " + long_text)

st.sidebar.text("Using st.text: " + long_text)
st.sidebar.markdown("Using st.markdown: " + long_text) 
st.sidebar.write("Using st.write: " + long_text)