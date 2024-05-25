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
    
    
    #process input container
    if user_question:
        handle_userinput(user_question)
    #if st.session_state["user_question"]:
        #handle_userinput(st.session_state["user_question"])

    


    with st.sidebar:
        st.subheader("Functions")
        pdf_docs = st.file_uploader("Upload only PDF documents here and click on 'Process'", accept_multiple_files=True)
        if st.button("Create Medical note"):
            with st.spinner("Processing"):
                # create medical note from this cased
                user_question = """Write an actual emergency medicine medical note for this patient based on the information we discussed, include good medical decision making.
                fill in any missing "Physical Examination" information with most likley information. Do not put in laboratory results or imaging results unless they were provided. Any missing information needed, place triple asteriks (***) in the location. structure the note based on the structure provided by triple backticks.

                ```
                Chief Complaint:
                History of Present Illness:
                Past Medical History:
                Medications:
                Physical Examination:
                Laboratory Results:
                Imaging:
                Assessment:
                Differential Diagnoses:
                Plan:
                Disposition:
                ```"""    
                
                handle_userinput(user_question)
        if st.button("help"):
            st.write("I got you!")

        user_name = st.text_input("Dr. Name", key="widget2", on_change=clear_text)
        if user_name:
            user_name_cap = user_name.title()
            st.write(user_name_cap)

        note_check = st.text_input("Note Check, Paste your note her and hit 'Enter'", key="widget3", on_change=clear_text)
        if note_check:
            user_question = f"Check the following medical note separated by triple backticks.  Clean up the note for any errors seen. Make sure the note can pass legal investigation. Explain any changes. Be complete and accurate. Document all relevant aspects of the patient encounter thoroughly, including chief complaint, history of present illness, review of systems, physical exam findings, diagnostic test results, assessment/differential diagnosis, and treatment plan. Leaving out important details can be problematic legally. Write legibly and clearly. Illegible or ambiguous notes open the door for misinterpretation. Use standard medical terminology and accepted abbreviations. If using an EMR, avoid copy/paste errors. Record in real-time. Chart contemporaneously while details are fresh in your mind rather than waiting until the end of your shift. Late entries raise suspicions. Date, time and sign every entry. This establishes a clear timeline of events. Sign with your full name and credentials.Explain your medical decision making. Articulate your thought process and rationale for diagnosis and treatment decisions. This demonstrates you met the standard of care. Avoid speculation or subjective comments. Stick to objective facts and medical information. Editorializing can be used against you. Make addendums if needed. If you later remember an important detail, it's okay to go back and add it with the current date/time. Never alter original notes. Ensure informed consent is documented. Record that risks, benefits and alternatives were discussed and the patient agreed to the plan. Keep personal notes separate. ```{note_check}'''"
            handle_userinput(user_question)
                

if __name__ == '__main__':
    main()
