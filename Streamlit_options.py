import streamlit as st
from streamlit_option_menu import option_menu

st.write("selectbox")
option = st.selectbox('Select an option', ['Option 1', 'Option 2', 'Option 3'])

st.write("multiselect")
selected = st.multiselect('Select options', ['Option A', 'Option B', 'Option C'])

st.write("selectbox")
options = {
    'List 1': [1,2,3], 
    'List 2': ['a','b','c']
}
selected = st.selectbox('Choose a list', list(options.keys()))
choice = options[selected]

option = st.radio("Pick an option", ['Option A', 'Option B', 'Option C'])

import streamlit as st
from streamlit_option_menu import option_menu

selected = option_menu(
    menu_title="Specialty Group",
    options=["Home", "Settings"],
    icons=['house', 'gear'],
    default_index=0
)

html = """
<select>
  <option value="option1">Option 1</option>
  <option value="option2">Option 2</option>
  <option value="option3">Option 3</option>
</select>
"""
st.markdown(html, unsafe_allow_html=True)