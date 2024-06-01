import streamlit as st
from streamlit_float import float_css_helper
from openai import OpenAI
import os
from dotenv import load_dotenv
from prompts import *
from extract_json import extract_json
import base64

# Load variables
load_dotenv()
ema_v2 = "asst_na7TnRA4wkDbflTYKzo9kmca"
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("API Key not found! Please check your environment variables.")
legal_attorney = "asst_ZI3rML4v8eG1vhQ3Fis5ikOd"
note_writer = 'asst_Ua6cmp6dpTc33cSpuZxutGsX'

client = OpenAI(api_key=api_key)

# Function to load and encode images as base64
def load_image_as_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

# Define the avatar base64 strings
user_avatar_base64 = load_image_as_base64("avatars/user.jpg")

specialist_id_caption = {
  "Emergency Medicine": {
    "assistant_id": "ema_v2",
    "caption": "EM, Peds EM, Toxicology, Wilderness",
    "avatar": load_image_as_base64("avatars/emergency_medicine.jpg")
  },
  "Neurological": {
    "assistant_id": "asst_caM9P1caoAjFRvSAmT6Y6mIz",
    "caption": "Neurology, Neurosurgery, Psychiatry",
    "avatar": load_image_as_base64("avatars/neurological.jpg")
  },
  "Sensory Systems (Eyes, Ears, Nose, Throat)": {
    "assistant_id": "asst_UB1VTD6NyYbb1xTrUueb3xlI",
    "caption": "Ophthalmology, ENT",
    "avatar": load_image_as_base64("avatars/sensory_systems.jpg")
  },
  "Cardiovascular and Respiratory": {
    "assistant_id": "asst_bH6wKFfCMVBiH3yUkM0DWdFk",
    "caption": "Cardiology, Cardiovascular Surgery, Vascular Surgery, Pulmonology, Thoracic Surgery",
    "avatar": load_image_as_base64("avatars/cardiovascular_respiratory.jpg")
  },
  "Gastrointestinal Systems": {
    "assistant_id": "asst_Z6bVfy6eOZBVdiwoS75eGdG9",
    "caption": "Gastroenterology, Hepatology, Colorectal Surgery, General Surgery",
    "avatar": load_image_as_base64("avatars/gastrointestinal_systems.jpg")
  },
  "Renal and GU Systems": {
    "assistant_id": "asst_SV4dNDe8sX0drryIVhQFeJj3",
    "caption": "Nephrology, Gynecology, Urology, Obstetrics",
    "avatar": load_image_as_base64("avatars/renal_gu_systems.jpg")
  },
  "Dermatology and Plastic Surgery": {
    "assistant_id": "asst_HzMNSMBEDBa3G6ABSISqu08e",
    "caption": "Dermatology, Plastic Surgery",
    "avatar": load_image_as_base64("avatars/dermatology_plastic_surgery.jpg")
  },
  "Musculoskeletal Systems": {
    "assistant_id": "asst_d9cMY1Sxwz0dUsKJXjuZMoiM",
    "caption": "Sports Med, Orthopedics, PM&R, Rheumatology, Physical Therapy",
    "avatar": load_image_as_base64("avatars/musculoskeletal_systems.jpg")
  },
  "General": {
    "assistant_id": "asst_K2QHe4VfHGdyrrfTCiyctzyY",
    "caption": "ICU, Internal Medicine, Infectious Disease, HemOnc, Endocrinology",
    "avatar": load_image_as_base64("avatars/general.jpg")
  },
  "Pediatrics": {
    "assistant_id": "asst_cVQwzy87fwOvTnb66zsvVB5L",
    "caption": "Pediatrics, Neonatology, Pediatric Surgery",
    "avatar": load_image_as_base64("avatars/pediatrics.jpg")
  },
  "Medical Legal": {
    "assistant_id": "asst_ZI3rML4v8eG1vhQ3Fis5ikOd",
    "caption": "Legal Consultant",
    "avatar": load_image_as_base64("avatars/medical_legal.jpg")
  },
  "Note Writer": {
    "assistant_id": "asst_Ua6cmp6dpTc33cSpuZxutGsX",
    "caption": "Medical Note Writer",
    "avatar": load_image_as_base64("avatars/note_writer.jpg")
  },
  "Emergency Medicine beta": {
    "assistant_id": "asst_GeAw2bIhrATHejogynMmP2VB",
    "caption": "EM - Beta testing",
    "avatar": load_image_as_base64("avatars/emergency_medicine_beta.jpg")
  }
}

# Initialize session_state variables
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
        "specialist": "",
        "should_rerun": False
    }
    for key, default in state_keys_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

# Setup the main page display and header
def display_header():
    st.set_page_config(page_title="EMA", page_icon="🤖🩺")
    st.header("EMA - Emergency Medicine Assistant 🤖🩺")

# User input container
def handle_user_input_container():
    input_container = st.container()
    input_container.float(float_css_helper(bottom="50px"))
    with input_container:
        specialist = st.session_state.specialist
        st.markdown(
            f"""
            <div style="text-align: center;">
                <h6>Specialty Group: <span style="color:red;">{specialist}</span></h6>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        user_question = st.chat_input("How may I help you?", key="widget2")
        if user_question:
            handle_userinput(user_question)

# Chat history display
def display_chat_history():
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            avatar_image = user_avatar_base64
            if message["role"] == "assistant":
                # Use the correct avatar base64 for the assistant based on the selected specialist
                specialist = st.session_state.specialist
                avatar_image = specialist_id_caption[specialist]["avatar"]
            # Encapsulate the image data in a way that Streamlit can use for avatars
            avatar_data_url = f"data:image/jpg;base64,{avatar_image}"
            with st.chat_message(message["role"], avatar=avatar_data_url):
                st.markdown(message["content"], unsafe_allow_html=True)

# Sidebar display
def display_sidebar():
    with st.sidebar:
        st.markdown("<h1 style='text-align: center;'>EMA 🤖</h1>", unsafe_allow_html=True)
        tab1, tab2, tab3, tab4 = st.tabs(["Functions", "Note Analysis", "Specialists", "Update Variables"])
        with tab1:
            display_functions_tab()
        with tab2:
            display_note_analysis_tab()
        with tab3:
            choose_specialist_radio()
        with tab4:
            update_patient_language()

# Sidebar tabs and functions
def display_functions_tab():
    st.subheader(":orange[Critical Actions]")
    if st.session_state.critical_actions:
        for action in st.session_state.critical_actions.get('critical_actions', []):
            st.markdown(f":orange[- {action}]")
    else:
        st.markdown("None")

    st.divider()
    st.subheader("Differential Diagnosis")
    if st.session_state.differential_diagnosis:
        for diagnosis_obj in st.session_state.differential_diagnosis.get("differential_diagnosis", []):
            diagnosis = diagnosis_obj.get("diagnosis")
            probability = diagnosis_obj.get("probability")
            st.markdown(f"- {diagnosis} {probability}%")
    else:
        st.markdown("None")

    st.divider()
    st.subheader('Process Management')
    col1, col2 = st.columns(2)
    with col1:
        button1 = st.button("🛌Disposition Analysis")
    with col2:
        button2 = st.button("💉Recommend Procedure")

    st.subheader('Note Management')
    col1, col2 = st.columns(2)
    with col1:
        button3 = st.button('📃Create Medical Note')
    with col2:
        button4 = st.button("📃Pt Education Note")

    st.subheader('AI Guidance')
    col1, col2 = st.columns(2)
    with col1:
        button5 = st.button("🆘Recommend Next Step")
    with col2:
        button6 = st.button('🆗I did that, now what?')

    st.divider()
    col1, col2 = st.columns(2)
    with col2:
        button9 = st.button('NEW THREAD', type="primary")

    # Process button actions
    process_buttons(button1, button2, button3, button4, button5, button6, button9)

# Process the buttons
def process_buttons(button1, button2, button3, button4, button5, button6, button9):
    if button1:
        st.session_state["user_question"] = disposition_analysis
    if button2:
        st.session_state["user_question"] = procedure_checklist
    if button3:
        st.session_state["note_input"] = "Write a medical note"
    if button4:
        st.session_state["user_question"] = pt_education + f"\n the patient's instructions needs to be in {st.session_state.patient_language}"
    if button5:
        st.session_state["user_question"] = "What should i do next here in the emergency department?"
    if button6:
        st.session_state["user_question"] = "Ok i did that. Now what?"
    if button9:
        new_thread()

# Note Analysis for summary and legal analysis
def display_note_analysis_tab():
    st.header("Note Analysis")
    note_check = st.text_area("Paste your note here and hit 'Ctrl+Enter'", height=200)
    if note_check:
        st.write('Note uploaded 👍')
    else:
        st.write('No note uploaded')

    col1, col2 = st.columns(2)
    with col1:
        button7 = st.button("Summarize Note")
    with col2:
        button8 = st.button("Optimize Your Note For Legal Protection")

    # Process buttons
    if button7:
        st.session_state["user_question"] = summarize_note + f' here is the note separated by triple backticks```{note_check}```'
    if button8:
        st.session_state["legal_question"] = optimize_legal_note + f' here is the note separated by triple backticks```{note_check}```'

# Choosing the specialty group
def choose_specialist_radio():
    # Extract the list of specialities
    specialities = list(specialist_id_caption.keys())
    
    # Extract the list of captions
    captions = [specialist_id_caption[speciality]["caption"] for speciality in specialities]

    # Display the radio button with specialities and captions
    specialist = st.radio("**Choose Your Specialty Group**", specialities)
    
    if specialist and specialist != st.session_state.specialist:
        st.session_state.specialist = specialist
        st.session_state.assistant_id = specialist_id_caption[specialist]["assistant_id"]
        st.session_state['should_rerun'] = True
        st.rerun()
    
    return specialist

# Updating the patient language
def update_patient_language():
    patient_language = st.text_input("Insert patient language if not English", value=st.session_state.patient_language)
    if patient_language != st.session_state.patient_language:
        st.session_state.patient_language = patient_language

# Processing queries
def process_queries():
    if st.session_state["user_question"]:
        handle_userinput(st.session_state["user_question"])
    elif st.session_state["legal_question"]:
        handle_user_legal_input(st.session_state["legal_question"])
    elif st.session_state["note_input"]:
        write_note(st.session_state["note_input"])
    elif st.session_state["specialist_input"]:
        consult_specialist(st.session_state["specialist_input"])

# Create a thread where the conversation will happen and keep Streamlit from initiating a new session state
if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id

# Create new thread
def new_thread():
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id
    st.session_state.chat_history = []
    st.rerun()

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
        
    client.beta.threads.messages.create(thread_id=st.session_state.thread_id, role="user", content=user_question)

    with client.beta.threads.runs.stream(thread_id=st.session_state.thread_id, assistant_id=st.session_state.assistant_id) as stream:
        assistant_response = "".join(generate_response_stream(stream))
        st.write_stream(generate_response_stream(stream))
    parse_json(assistant_response)
    st.session_state.chat_history.append({"role": "assistant", "content": st.session_state.assistant_response})  # Add assistant response to chat history
    

@st.cache_data
def handle_user_legal_input(legal_question):    
    # append user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": legal_question})
        
    client.beta.threads.messages.create(thread_id=st.session_state.thread_id, role="user", content=legal_question)

    with client.beta.threads.runs.stream(thread_id=st.session_state.thread_id, assistant_id=legal_attorney) as stream:
        assistant_response = "".join(generate_response_stream(stream))
        st.write_stream(generate_response_stream(stream))
        st.session_state.chat_history.append({"role": "legal consultant", "content": assistant_response})  # Add assistant response to chat history

def parse_json(assistant_response):
    # Call the extract_json function and capture its return values
    differential_diagnosis, critical_actions, modified_text = extract_json(assistant_response)
    
    # Add debugging print statements
    print("Debug: assistnat response: ", assistant_response)
    print("Debug: differential_diagnosis:", differential_diagnosis)
    print("Debug: critical_actions:", critical_actions)
    print("Debug: modified_text:", modified_text)
    
    # Assign the return values to the session state
    st.session_state.differential_diagnosis = differential_diagn