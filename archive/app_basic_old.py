import streamlit as st
from streamlit_float import float_init, float_css_helper
from htmlTemplates import css
from openai import OpenAI
import os
from dotenv import load_dotenv
from prompts import *

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)
# Create a thread where the conversation will happen
thread = client.beta.threads.create()


# clears user input box
def clear_text():
    st.session_state["user_question"] = st.session_state["widget"]
    st.session_state["widget"] = ""

@st.cache_data
def handle_userinput(user_question):
        
    # append user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": user_question})

    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_question,
    )
    # Create the Run, passing in the thread and the assistant 
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id="asst_Pau6T5mMH3cZBnEePso5kFuJ"
    )
    # Periodically retrieve the Run to check status until it completes
    while run.status != "completed":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id, 
            run_id=run.id
        )
        if run.status == "completed":
            break
    # Retrieve assistant's response messages from the thread
    response_messages = client.beta.threads.messages.list(thread_id=thread.id)

    # Append assistant response to chat history
    for message in response_messages:
        if message.role == "assistant":
            st.session_state.chat_history.append({"role": "assistant", "content": message.content[0].text.value})
    
    
def main():

    st.set_page_config(page_title="Resident Assistant", page_icon="🤖🩺")

    st.write(css, unsafe_allow_html=True)
    float_init()

    if "conversation" not in st.session_state: #keep conversation variable from refreshing (keep consistant), as Streamlit likes to refreashthe entire code otherwise during use.
        st.session_state.conversation = None
    if "chat_history" not in st.session_state: #keep conversation variable from refreshing (keep consistant), as Streamlit likes to refreashthe entire code otherwise during use.
        st.session_state.chat_history = []
    if "user_question" not in st.session_state:
        st.session_state["user_question"] = ""

    st.header("EM Resident Assistant 🤖")

    chat_container = st.container()
    
    # Display input container
    input_container = st.container()
    input_container.float(float_css_helper(bottom="50px"))
    with input_container:
        user_question = st.text_input("How may I help you?", key="widget", on_change=clear_text)
            
    
    #process input container
    if user_question:
        handle_userinput(user_question)
    if st.session_state["user_question"]:
        handle_userinput(st.session_state["user_question"])

    # Display chat history in the chat_container
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"], unsafe_allow_html=True)
        

    with st.sidebar:
        st.header("FUNCTIONS")

        # Procedure Checklist
        if st.button(f"Procedure Checklist"):
            user_question = procedure_checklist
        
        # Disposition Help
        if st.button(f"Disposition Analysis"):
            user_question = disposition_analysis

        # Create Medical Note        
        if st.button("Create Medical Note"):
            user_question = create_med_note    
                
            #handle_userinput(user_question)   
  
        # Patient Education
        st.subheader("Patient Eductation Handout")   
        
        patient_language = st.text_input(f"Patient's Instructions are in {patient_language}, type a different language below", key="widget4", on_change=clear_text)
        if st.button(f"Create {patient_language} Eductation Handout"):
            user_question = pt_education




        #note_check = st.text_input("Maximize you note for legal defensibility. Paste your note here and hit 'Enter'", key="widget3", on_change=clear_text)
        st.subheader("Optimize Your Note For Legal Protection")
        note_check = st.text_area("Paste your note here and hit 'Ctrl+Enter'", height=200)
        if note_check:
            user_question = optimize_legal_note
        if user_question:
            handle_userinput(user_question)

if __name__ == '__main__':
    main()
