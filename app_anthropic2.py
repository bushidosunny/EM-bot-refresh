import streamlit as st
from anthropic import Anthropic
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv
import os
from prompts import emma_system, note_writer_system, patient_educator_system, critical_system

# Load environment variables
load_dotenv()

# Initialize API keys
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    st.error("API Key not found! Please check your environment variables.")

# Initialize Anthropic client and model
anthropic = Anthropic(api_key=api_key)
model = ChatAnthropic(model="claude-3-5-sonnet-20240620", temperature=0.5, max_tokens=4096)

# Define specialist information
specialist_id_caption = {
    "Emergency Medicine": {
        "assistant_id": "asst_na7TnRA4wkDbflTYKzo9kmca",
        "caption": "👨⚕️EM, Peds EM, ☠️Toxicology, Wilderness",
        "avatar": "https://i.ibb.co/LnrQp8p/Designer-17.jpg",
        "system_instructions": emma_system
    },
    # ... (other specialists)
}

def initialize_session_state():
    default_state = {
        "authentication_status": None,
        "logout": None,
        "name": "",
        "username": "",
        "chat_history": [],
        "user_question": "",
        "legal_question": "",
        "note_input": "",
        "json_data": {},
        "pt_data": {},
        "differential_diagnosis": {},
        "danger_diag_list": {},
        "critical_actions": {},
        "sidebar_state": 1,
        "assistant_response": "",
        "patient_language": "English",
        "specialist_input": "",
        "should_rerun": False,
        "user_question_sidebar": "",
        "old_user_question_sidebar": "",
        "completed_tasks_str": "",
        "follow_up_steps": "",
        "messages": [],
        "system_instructions": emma_system
    }

    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        for key, value in default_state.items():
            if key not in st.session_state:
                st.session_state[key] = value

        primary_specialist = next(iter(specialist_id_caption))
        st.session_state.specialist = primary_specialist
        st.session_state.assistant_id = specialist_id_caption[primary_specialist]["assistant_id"]
        st.session_state.specialist_avatar = specialist_id_caption[primary_specialist]["avatar"]
        st.session_state.system_instructions = specialist_id_caption[primary_specialist]["system_instructions"]

def display_header():
    if st.session_state.pt_data:
        patient = st.session_state.pt_data['patient']
        page_title = f"{patient['age']}{patient['age_unit']}{patient['sex']} {patient['chief_complaint_two_word']}"
    else:
        page_title = "EMMA"
    
    st.set_page_config(page_title=page_title, page_icon="🤖", initial_sidebar_state="collapsed")
    # Add any additional header content here

# Main execution
if __name__ == "__main__":
    initialize_session_state()
    display_header()
    # Add your main application logic here