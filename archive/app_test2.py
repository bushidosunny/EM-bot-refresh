import streamlit as st
from streamlit_float import float_init, float_css_helper
from htmlTemplates import css
from openai import OpenAI
import os
from dotenv import load_dotenv

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
        
        #function buttons
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            button1 = st.button("Disposition Analysis")

        with col2:
            button2 = st.button("Procedure Checklist")

        with col3:  
            button3 = st.button('Create Medical Note')            

        with col4:
            button4 = st.button("Patient Eductation Handout")
              
 
        if button1: 
            # Disposition decision helper, safer for home? 
            st.session_state["user_question"] = f"Analyze the patient's current condition. Assess for safe discharge or if the patient should be admitted. Provide reasons for or against. If it is not clear provide things to consider. Be concise with structured short bullet points"
        if button2:
            # Create Procedure Checklis
            st.session_state["user_question"] = f"Create a procedure checklist of the mostlikly procedure that will be done in the emergency department for this patient. T2. Clear procedural instructions. 3. Possible patient complications to look out for. 4. highlight education points for the patient. Use the following format ```1. Supplies   2. Precedure Instructions  3. Possible Complications 4. Patient Education of the Procedure"

    #process input container
    if st.session_state["user_question"]:
        handle_userinput(st.session_state["user_question"])
    else:
        if user_question:
            handle_userinput(user_question)
    

    # Display chat history in the chat_container
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"], unsafe_allow_html=True)

    st.write(st.session_state.chat_history)    


if __name__ == '__main__':
    main()
