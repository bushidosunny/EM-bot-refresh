import streamlit as st
from streamlit_float import float_init, float_css_helper
from openai import OpenAI
import os
from dotenv import load_dotenv
from prompts import *

# Load variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
resident_assistant ="asst_Pau6T5mMH3cZBnEePso5kFuJ"
legal_attorney = "asst_ZI3rML4v8eG1vhQ3Fis5ikOd"
patient_language = "english"

client = OpenAI(api_key=api_key)

# Create a thread where the conversation will happen and keep streamlit form initiating a new session state
if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id

# Function to generate the response stream
def generate_response_stream(stream):
    for response in stream:
        if response.event == 'thread.message.delta':
            for delta in response.data.delta.content:
                if delta.type == 'text':
                    yield delta.text.value

@st.cache_data
def handle_userinput(user_question):    

    # append user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": user_question})
        
    message = client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=user_question
    )

    with client.beta.threads.runs.stream(
        thread_id=st.session_state.thread_id,
        assistant_id=resident_assistant
    ) as stream:
        assistant_response = "".join(generate_response_stream(stream))
        st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})  # Add assistant response to chat history
        st.write_stream(generate_response_stream(stream))

@st.cache_data
def handle_user_legal_input(legal_question):    

    # append user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": legal_question})
        
    message = client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=legal_question
    )

    with client.beta.threads.runs.stream(
        thread_id=st.session_state.thread_id,
        assistant_id=legal_attorney
    ) as stream:
        assistant_response = "".join(generate_response_stream(stream))
        st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})  # Add assistant response to chat history
        st.write_stream(generate_response_stream(stream))
   
    
def main():
    st.set_page_config(page_title="EMA", page_icon="🤖🩺")
    
    # Initialize session state
    if "chat_history" not in st.session_state: #keep conversation variable from refreshing (keep consistant), as Streamlit likes to refreashthe entire code otherwise during use.
        st.session_state.chat_history = []
    if "user_question" not in st.session_state:
        st.session_state["user_question"] = ""
    if "legal_question" not in st.session_state:
        st.session_state["legal_question"] = ""
    

    st.header("EMA - Emergency Medicine Assistant 🤖🩺")

    # Side bar
    with st.sidebar:
        st.markdown("<h1 style='text-align: center;'>EMA 🤖</h1>", unsafe_allow_html=True)
        tab1, tab2,= st.tabs(["Functions", "Note Analysis"])
        with tab1:
            st.subheader('Process Management')

            #function buttons
            col1, col2, = st.columns(2)
            with col1:
                button1 = st.button("🛌Disposition Analysis")
            with col2:
                button2 = st.button("💉Recommended Procedure")
            
            st.divider()

            st.subheader('Note Management')

            col1, col2, = st.columns(2)
            with col1:
                button3 = st.button('📃Create Medical Note')
            with col2:
                button4 = st.button("📃Patient Education Note")
                patient_language = st.text_input('')
                if patient_language:
                    st.write(f'Patient language is in {patient_language}')
                else:
                    st.write(f'Patient language is currently English')
            
            st.divider()

            st.subheader('AI Guidance')

            col1, col2, = st.columns(2)
            with col1:  
                button5 = st.button("🆘Recommended Next Step")  
            with col2:
                button6 = st.button('🆗I did that, now what?')
                
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
                # Disposition decision helper, safer for home? 
                st.session_state["user_question"] = pt_education + f"\n the patient's instructions needs to be in {patient_language}"
            if button5:
                # Create Procedure Checklis
                st.session_state["user_question"] = "What should i do next here in the emergency department?"
            if button6:
                # create medical note from this case when Button 1 is clicked
                st.session_state["user_question"] = "Ok i did that. Now what?" 

        with tab2: 
            st.header("Note Analysis")
            
            # paste in note
            note_check = st.text_area("Paste your note here and hit 'Ctrl+Enter'", height=200)
            if note_check:
                st.write('Note uploaded 👍')            
            else:
                st.write('no note uploaded')
            
            # display buttons
            col1, col2, = st.columns(2)
            with col1:
                button7 = st.button("Summarize Note")
            with col2:
                button8 = st.button("Optimize Your Note For Legal Protection")
            
            # process buttons 
            if button7: 
                # Disposition decision helper, safer for home? 
                st.session_state["user_question"] = summarize_note + f' here is the note separated by triple backticks```{note_check}```'           
            if button8:
                # Create Procedure Checklis
                st.session_state["legal_question"] = optimize_legal_note + f' here is the note separated by triple backticks```{note_check}```'
            

    # Display input container
    input_container = st.container()
    input_container.float(float_css_helper(bottom="5px"))
    with input_container:
        with st.form("my_form", clear_on_submit=True):
            user_question = st.text_input("How may I help you?", key="widget2")
            submitted = st.form_submit_button("Submit")

            if submitted:
                handle_userinput(user_question)
    
    #process user input
    #if user_question:
        #handle_userinput(user_question)
    if st.session_state["user_question"]:
        handle_userinput(st.session_state["user_question"])
    if st.session_state["legal_question"]:
        handle_user_legal_input(st.session_state["legal_question"])

    # Display chat history in the chat_container
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"], unsafe_allow_html=True)
                       
if __name__ == '__main__':
    main()
