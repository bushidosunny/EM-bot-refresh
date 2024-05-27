import streamlit as st
tab1, tab2, tab3 = st.tabs(["Cat", "Dog", "Owl"])
with tab1:
    st.header("A cat")
    st.image("cat.jpg", width=200)

with tab2: 
    st.header("A dog")
    st.image("dog.jpg", width=200)

tab3.header("An owl") 
tab3.image("owl.jpg", width=200)

with st.sidebar:
    tab1, tab2, tab3 = st.tabs(["Cat", "Dog", "Owl"])
    with tab1:
        st.header("A cat")
        st.image("cat.jpg", width=200)

    with tab2: 
        st.header("A dog")
        st.image("dog.jpg", width=200)

    tab3.header("An owl") 
    tab3.image("owl.jpg", width=200)



