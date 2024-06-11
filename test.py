import streamlit as st
import time
from datetime import datetime



def process_user_question(user_question):
    if user_question is not None and user_question != "":
        current_datetime = datetime.now().strftime("%m-%d %H:%M:%S")
        user_question = user_question + f"""    \n{current_datetime}
        """
        st.markdown(user_question)

user_question = st.chat_input("How may I help you?") 
process_user_question(user_question)