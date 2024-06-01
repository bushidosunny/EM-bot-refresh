import streamlit as st
from streamlit_float import float_css_helper
from openai import OpenAI
import os
from dotenv import load_dotenv
from prompts import *
from extract_json import extract_json

# Load variables
load_dotenv()
ema_v2 = "asst_na7TnRA4wkDbflTYKzo9kmca"
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("API Key not found! Please check your environment variables.")
legal_attorney = "asst_ZI3rML4v8eG1vhQ3Fis5ikOd"
note_writer = 'asst_Ua6cmp6dpTc33cSpuZxutGsX'

client = OpenAI(api_key=api_key)

# Specialist to Assistant ID mapping
specialist_to_assistant_id = {
    "Acute Care": ema_v2,
    "Neurological": "asst_caM9P1caoAjFRvSAmT6Y6mIz",
    "Dermatology and Plastic Surgery": "asst_HzMNSMBEDBa3G6ABSISqu08e",
    "Sensory Systems (Eyes, Ears, Nose, Throat)": "asst_UB1VTD6NyYbb1xTrUueb3xlI",
    "Cardiovascular and Respiratory": "asst_bH6wKFfCMVBiH3yUkM0DWdFk",
    "Gastrointestinal Systems": "asst_Z6bVfy6eOZBVdiwoS75eGdG9",
    "Renal and GU Systems": "asst_SV4dNDe8sX0drryIVhQFeJj3",
    "Musculoskeletal Systems": "asst_d9cMY1Sxwz0dUsKJXjuZMoiM",
    "General": "asst_K2QHe4VfHGdyrrfTCiyctzyY",
    "Pediatrics": "asst_cVQwzy87fwOvTnb66zsvVB5L",
    "Medical Legal": "asst_ZI3rML4v8eG1vhQ3Fis5ikOd"
}

# Create a thread where the conversation will happen and keep streamlit form initiating a new session state
if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id

def choose_specialist(specialist):
    st.session_state.assistant_id = specialist_to_assistant_id.get(specialist, ema_v2)
    #print(f'\n your specialist is {specialist} id = {st.session_state.assistant_id}')
    
# Create new thread
def new_thread():
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id
    st.session_state.chat_history = []


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
        assistant_id=st.session_state.assistant_id
    ) as stream:
        assistant_response = "".join(generate_response_stream(stream))
        
        st.write_stream(generate_response_stream(stream))
    parse_json(assistant_response)
    st.session_state.chat_history.append({"role": "assistant", "content": st.session_state.assistant_response})  # Add assistant response to chat history
    user_input_counter = 0
    user_input_counter += 1
    print(user_input_counter)

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
        st.write_stream(generate_response_stream(stream))
    st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})  # Add assistant response to chat history

def parse_json(assistant_response):
    # Call the extract_json function and capture its return values
    differential_diagnosis, critical_actions, modified_text = extract_json(assistant_response)
    
    # Add debugging print statements
    print("Debug: assistnat response: ", assistant_response)
    print("Debug: differential_diagnosis:", differential_diagnosis)
    print("Debug: critical_actions:", critical_actions)
    print("Debug: modified_text:", modified_text)
    
    # Assign the return values to the session state
    st.session_state.differential_diagnosis = differential_diagnosis
    st.session_state.critical_actions = critical_actions
    st.session_state.assistant_response = modified_text

def consult_specialist(specialist_input):
    if st.session_state.specialist == "sports_medicine":
        dr_sports_medicine(specialist_input)
    if st.session_state.specialist == "ICU":
        dr_icu(specialist_input)

@st.cache_data
def write_note(note_input):    

    # append user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": note_input})
        
    message = client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=note_input
    )

    with client.beta.threads.runs.stream(
        thread_id=st.session_state.thread_id,
        assistant_id=note_writer
    ) as stream:
        assistant_response = "".join(generate_response_stream(stream))
        st.write_stream(generate_response_stream(stream))
    st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})  # Add assistant response to chat history
    
#Initialization of Session States
def initialize_session_state():
    state_keys_defaults = {
        "chat_history": [],
        "user_question": "",
        "legal_question": "",
        "note_input": "",
        "json_data": {},
        "differential_diagnosis": {},
        "danger_diag_list": {},
        "critical_actions": {},
        "sidebar_state": 1,
        "assistant_response": "",
        "patient_language": "English",
        "specialist_input": "",
        "specialist": ""
    }
    for key, default in state_keys_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

def main():
    st.set_page_config(page_title="EMA", page_icon="🤖🩺")
    
    # Initialize session state
    if "chat_history" not in st.session_state: #keep conversation variable from refreshing (keep consistant), as Streamlit likes to refreashthe entire code otherwise during use.
        st.session_state.chat_history = []
    if "user_question" not in st.session_state:
        st.session_state["user_question"] = ""
    if "legal_question" not in st.session_state:
        st.session_state["legal_question"] = ""
    if "note_input" not in st.session_state:
        st.session_state["note_input"] = ""
    if "json_data" not in st.session_state:
        st.session_state.json_data = {}
    if "differential_diagnosis" not in st.session_state:
        st.session_state.differential_diagnosis = {}
    if "danger_diag_list" not in st.session_state:
        st.session_state.danger_diag_list = {}
    if "critical_actions" not in st.session_state:
        st.session_state.critical_actions = {}
    if "sidebar_state" not in st.session_state:
        st.session_state.sidebar_state = 1 
    if "assistant_response" not in st.session_state:
        st.session_state.assistant_response = ""
    if "patient_language" not in st.session_state:
        st.session_state.patient_language = "English"
    if "specialist_input" not in st.session_state:
        st.session_state["specialist_input"] = ""
    if "specialist" not in st.session_state:
        st.session_state.specialist = ""
    

    st.header("EMA - Emergency Medicine Assistant 🤖🩺")

    # Display input container
    input_container = st.container()
    input_container.float(float_css_helper(bottom="50px"))
    with input_container:
        user_question = st.chat_input("How may I help you?", key="widget2")
        if user_question:
            handle_userinput(user_question)

            

    #process user input
    #if user_question:
        #handle_userinput(user_question)
    if st.session_state["user_question"]:
        handle_userinput(st.session_state["user_question"])
    if st.session_state["legal_question"]:
        handle_user_legal_input(st.session_state["legal_question"])

    # Side bar
    with st.sidebar:
        st.markdown("<h1 style='text-align: center;'>EMA 🤖</h1>", unsafe_allow_html=True)


        tab1, tab2, tab3, tab4= st.tabs(["Functions", "Note Analysis", "Specialists", "Update Variables"])
        with tab1:
            st.subheader(":orange[Critical Actions]")
            print("Debug: Critical actions:", st.session_state.critical_actions)
            if st.session_state.critical_actions: 
                for action in st.session_state.critical_actions['critical_actions']:
                    st.markdown(f":orange[- {action}]")
            else:
                st.markdown("None")


            st.divider()

            st.subheader("Differential Diagnosis")
            
            # Debugging statements to verify the session state
            print("Debug: Session state differential_diagnosis:", st.session_state.differential_diagnosis)  # Debug

            
            # Iterate through the list of diagnosis dictionaries
            if st.session_state.differential_diagnosis:
                for diagnosis_obj in st.session_state.differential_diagnosis.get("differential_diagnosis", []):
                    diagnosis = diagnosis_obj.get("diagnosis")
                    probability = diagnosis_obj.get("probability")
                    st.markdown(f"- {diagnosis} {probability}%")
            else:
                st.markdown("None")
            

            #st.subheader("Dangerous Diagnoses")
            #st.text(st.session_state.danger_diag_list)

            st.divider()

            st.subheader('Process Management')

            

            #function buttons
            col1, col2, = st.columns(2)
            with col1:
                button1 = st.button("🛌Disposition Analysis")
            with col2:
                button2 = st.button("💉Recommend Procedure")
            
            

            st.subheader('Note Management')

            col1, col2, = st.columns(2)
            with col1:
                button3 = st.button('📃Create Medical Note')
            with col2:
                button4 = st.button("📃Pt Education Note")
 
                
            

            st.subheader('AI Guidance')

            col1, col2, = st.columns(2)
            with col1:  
                button5 = st.button("🆘Recommend Next Step")  
            with col2:
                button6 = st.button('🆗I did that, now what?')

            st.divider()

            col1, col2, = st.columns(2)
            with col2:
                button9 = st.button('NEW THREAD', type="primary")
                
            # process buttons 
            if button1: 
                # Disposition decision helper, safer for home? 
                st.session_state["user_question"] = disposition_analysis
            if button2:
                # Create Procedure Checklis
                st.session_state["user_question"] = procedure_checklist
            if button3:
                # create medical note from this case when Button 1 is clicked
                st.session_state["note_input"] = "Write a medical note"
            if button4: 
                # Patient enducation instructions? 
                st.session_state["user_question"] = pt_education + f"\n the patient's instructions needs to be in {st.session_state.patient_language}"
            if button5:
                # Create Procedure Checklis
                st.session_state["user_question"] = "What should i do next here in the emergency department?"
            if button6:
                # create medical note from this case when Button 1 is clicked
                st.session_state["user_question"] = "Ok i did that. Now what?" 
            if button9:
                # Refresh button
                new_thread()

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
        
        with tab3:
            # Chose specialty group
            specialist = st.radio("**Choose Your Specialty Group**", [
            "Acute Care",
            "Neurological",
            "Sensory Systems (Eyes, Ears, Nose, Throat)",
            "Cardiovascular and Respiratory",
            "Gastrointestinal Systems",
            "Renal and GU Systems",
            "Dermatology and Plastic Surgery",
            "Musculoskeletal Systems",
            "General",
            "Pediatrics",
            "Medical Legal"
            ],captions = ["EM, Peds EM, Toxicology, Wildnerness", 
                        "Neurology, Neurosurgery, Psychiatry", 
                        "Ophthalmology, ENT",
                        "Cardiology, Cardiovascular Surgery, Vascular Surgery, Pulmonology, Thoracic Surgery",
                        "Gastroenterology, Hepatology, Colorectal Surgery, Gen Surg",
                        "Nephrology, Gynecology, Urology, Obstetrics",
                        "",
                        "Sports Med, Orthopedics, PM&R, Rheumatology, Physical Therapy",
                        "ICU, Internal Medicine, Infectious Disease, HemOnc, Endo",
                        "Pediatrics, Neonatology, Pediatric Surgery",
                        "",     
                        ])
            if specialist:
                st.session_state.specialist = specialist
                st.subheader(f'Your Group is :red[{st.session_state.specialist}]')
                choose_specialist(specialist)
            
                

            
            
        with tab4:
            patient_language = st.text_input("Type language if not English")
            if patient_language:
                st.session_state.patient_language = patient_language
                st.write(f'Patient language is {st.session_state.patient_language}')


    #querry asissitants        
    if st.session_state["user_question"]:
        handle_userinput(st.session_state["user_question"])
    if st.session_state["legal_question"]:
        handle_user_legal_input(st.session_state["legal_question"])
    if st.session_state["note_input"]:
        write_note(st.session_state["note_input"])
    if st.session_state["specialist_input"]:
        consult_specialist(st.session_state["specialist_input"])


    # Display chat history in the chat_container
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"], unsafe_allow_html=True)

                       
if __name__ == '__main__':
    main()
