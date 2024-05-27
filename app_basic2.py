import streamlit as st
from streamlit_float import float_init, float_css_helper
from openai import OpenAI
import os
from dotenv import load_dotenv
from prompts import *

# Load variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
resident_assitant ="asst_Pau6T5mMH3cZBnEePso5kFuJ"

client = OpenAI(api_key=api_key)

# Create a thread where the conversation will happen and keep streamlit form initiating a new session state
if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id
    print(f"Thread ID: {st.session_state.thread_id}")

@st.cache_data
def handle_userinput(user_question):    

    # append user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": user_question})
        
    # Send user message to OpenAI API
    client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=user_question,
    )

    # Get assistant response
    run = client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=resident_assitant
    )
    # Periodically retrieve the Run to check status until it completes
    while run.status != "completed":
        run = client.beta.threads.runs.retrieve(
            thread_id=st.session_state.thread_id, 
            run_id=run.id
        )
        if run.status == "completed":
            break

    # Retrieve assistant's response messages from the thread
    response_messages = client.beta.threads.messages.list(thread_id=st.session_state.thread_id)

    # Append assistant response to chat history
    for message in response_messages:
        if message.role == "assistant":
            assistant_response = message.content[0].text.value
            st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})
    
    
def main():
    st.set_page_config(page_title="EM Assistant Basic", page_icon="🤖🩺")
    
    # Initialize session state
    
    if "chat_history" not in st.session_state: #keep conversation variable from refreshing (keep consistant), as Streamlit likes to refreashthe entire code otherwise during use.
        st.session_state.chat_history = []
    if "user_question" not in st.session_state:
        st.session_state["user_question"] = ""

    st.header("EM Assistant Basic 🤖🩺")

    # Side bar
    with st.sidebar:
        st.header("FUNCTIONS")
        st.subheader("Optimize Your Note For Legal Protection")
        note_check = st.text_area("Paste your note here and hit 'Ctrl+Enter'", height=200)
        if note_check:
            with st.spinner("Processing"):
                user_question = optimize_legal_note
                handle_userinput(user_question)
    
    # Display input container
    input_container = st.container()
    input_container.float(float_css_helper(bottom="50px"))
    with input_container:
        with st.form("my_form", clear_on_submit=True):
            user_question = st.text_input("How may I help you?", key="widget2")
            submitted = st.form_submit_button("Submit")

            if submitted:
                handle_userinput(user_question)

        #function buttons
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            button1 = st.button("Disposition Analysis")

        with col2:
            button2 = st.button("Recommended Procedure Checklist")

        with col3:  
            button3 = st.button('Create Medical Note')            

        with col4:
            button4 = st.button("Patient Eductation Handout")
        
        # process buttons
          

        if button1: 
            # Disposition decision helper, safer for home? 
            st.session_state["user_question"] = disposition_analysis
        if button2:
            # Create Procedure Checklis
            st.session_state["user_question"] = procedure_checklist
        if button3:
            # create medical note from this case when Button 1 is clicked
            st.session_state["user_question"] = create_med_note  
        if button4:
            # create Patient Eductation Handout
            st.session_state["user_question"] = pt_education
    #process user input
    #if user_question:
        #handle_userinput(user_question)
    if st.session_state["user_question"]:
        handle_userinput(st.session_state["user_question"])

    # Display chat history in the chat_container
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"], unsafe_allow_html=True)
                

if __name__ == '__main__':
    main()
