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
            button2 = st.button("Create Procedure Checklist")

        with col3:  
            button3 = st.button('Create Medical note')            

        with col4:
            button4 = st.button("Patient Eductation Handout")
              
        # process buttons
        if button3:
            # create medical note from this case when Button 1 is clicked
            user_question = """Write a structured clinical note of THIS PATIENT discussed. Do not provide a generic example note. Include good medical decision making.
            fill in any missing "Physical Examination" information with most likley information. Do not put in laboratory results or imaging results unless they were provided. Any missing information needed, place triple asteriks (***) in the location. structure the note based on the specified format provided by triple backticks.

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

        if button1: 
            # Disposition decision helper, safer for home? 
            user_question = f"Analyze the patient's current condition. Assess for safe discharge or if the patient should be admitted. Provide reasons for or against. If it is not clear provide things to consider. Be concise with structured short bullet points"

        if button2:
            # Create Procedure Checklis
            user_question = f"Create a procedure checklist of the mostlikly procedure that will be done in the emergency department for this patient. T2. Clear procedural instructions. 3. Possible patient complications to look out for. 4. highlight education points for the patient. Use the following format ```1. Supplies   2. Precedure Instructions  3. Possible Complications 4. Patient Education of the Procedure"

        if button4:
            # create Patient Eductation Handout
            user_question = """You are an emergency medicine specialist tasked with providing patient education materials. Based on the clinical details provided, generate an easy-to-understand patient education note in the specified language. covering the following:
            ```Diagnoses: List the key medical conditions discussed with the patient

            Treatment Plan: Explain the treatments or interventions recommended 

            Discharge Instructions: Outline any instructions for care after discharge

            Topics Covered: Summarize the major concepts you reviewed with the patient, such as:
            - Diagnosis details and pathophysiology
            - Medication instructions (dosage, route, side effects)
            - Warning signs/symptoms to watch for  
            - Activity modifications or precautions
            - Follow-up care instructions

            Plan Outline: 
            - Describe any plans for reinforcing or following up on the education provided
            - Note if family members or interpreters were involved 
            - Indicate any barriers addressed (e.g. health literacy, language)

            Structure the patient education note using the following template format:

            Diagnoses:
            [List diagnoses discussed]

            Treatment Plan:  
            [Explain treatments/interventions]

            Discharge Instructions:
            [Outline post-discharge care instructions]

            Topics Covered:
            [Summarize key concepts reviewed]

            Plan Outline:
            [Note reinforcement plans, barriers addressed, interpreters used]

            Please provide the education note only in the specified patient language. If any critical information is missing to comprehensively create the note, please let me know.```""" + f"\n the patient's instructions needs to be in {st.session_state.patient_language}"
            

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
        st.header("Other Stuff")

           
  
        # Patient Education
        st.session_state.patient_language = "English"
        #st.subheader(f"Patient's Language")   
        patient_language = st.text_input("Input Patient's language if not English", key="widget4", on_change=clear_text)
        if patient_language:
            st.write(f"Patient's language is now {patient_language}")
            st.session_state.patient_language = patient_language
        #note_check = st.text_input("Maximize you note for legal defensibility. Paste your note here and hit 'Enter'", key="widget3", on_change=clear_text)
        st.subheader("Optimize Your Note For Legal Protection")
        note_check = st.text_area("Paste your note here and hit 'Ctrl+Enter'", height=200)
        if note_check:
            with st.spinner("Processing"):
                user_question = f"Check the following medical note separated by triple backticks.  1. Evaluate on its ability to be legally defensible. 2. Suggest what else can be done for the patient before disposition. Separate the importance of the improvement from critical to mild. 3. Rewrite the note with the avialable information. Explain any changes. Be complete and accurate. < >Utizilze the following guidlines: Document all relevant aspects of the patient encounter thoroughly, including chief complaint, history of present illness, review of systems, physical exam findings, diagnostic test results, assessment/differential diagnosis, and treatment plan. Leaving out important details can be problematic legally. Write legibly and clearly. Illegible or ambiguous notes open the door for misinterpretation. Use standard medical terminology and accepted abbreviations. If using an EMR, avoid copy/paste errors. Record in real-time. Chart contemporaneously while details are fresh in your mind rather than waiting until the end of your shift. Late entries raise suspicions. Date, time and sign every entry. This establishes a clear timeline of events. Sign with your full name and credentials.Explain your medical decision making. Articulate your thought process and rationale for diagnosis and treatment decisions. This demonstrates you met the standard of care. Avoid speculation or subjective comments. Stick to objective facts and medical information. Editorializing can be used against you. Make addendums if needed. If you later remember an important detail, it's okay to go back and add it with the current date/time. Never alter original notes. Ensure informed consent is documented. Record that risks, benefits and alternatives were discussed and the patient agreed to the plan. Keep personal notes separate.< > ```{note_check}'''"
                handle_userinput(user_question)


if __name__ == '__main__':
    main()
