import streamlit as st
from streamlit_float import float_css_helper
from anthropic import Anthropic
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import os
import io
import time
from dotenv import load_dotenv
from prompts import *
import json
from extract_json import create_json
from datetime import datetime
import pytz
# from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, PatternRecognizer, Pattern
# from presidio_anonymizer import AnonymizerEngine
# from presidio_analyzer.predefined_recognizers import SpacyRecognizer, EmailRecognizer, PhoneRecognizer, UsLicenseRecognizer, UsSsnRecognizer
from pymongo import MongoClient, ASCENDING, TEXT, DESCENDING
from pymongo.errors import DuplicateKeyError
from bson import ObjectId, Regex
from streamlit_searchbox import st_searchbox
from streamlit_mic_recorder import mic_recorder
from deepgram import DeepgramClient, PrerecordedOptions
from streamlit.components.v1 import html
# from typing import List, Dict, Any, Optional, Tuple

import streamlit as st

st.set_page_config(
    page_title="Alpha Medical Test App",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': 'https://www.perplexity.ai/',
        'Report a bug': 'mailto:bushidosunny@gmail.com',
        'About': "# Alpha Medical Test App\n\nThis is an alpha product in testing. All medical information is for testing and educational purposes only. Do not make any medical decisions based on this information."
    }
)

#login_username = "Sunny"
# Load environment variables
load_dotenv()
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
MONGODB_URI = os.getenv('MONGODB_ATLAS_URI')
CLIENT_SECRET_JSON = json.loads(os.getenv('CLIENT_SECRET_JSON'))
ENVIRONMENT = os.getenv('ENVIRONMENT')

 

emma_system2 = """ # AI Doctor Specialist Diagnostic Process

        ## Initial Assessment

        [Read the patient's chat history and current information to create an initial differential diagnosis (DDx).]

        ### Differential Diagnosis with Initial Probabilities

        * **Diagnosis 1** - [Probability]%
            + Evidence for:
            + Evidence against:
            + Reasoning:
        * **Diagnosis 2** - [Probability]%
            + Evidence for:
            + Evidence against:
            + Reasoning:
        * ... (Continue for all potential diagnoses)

        ## Follow-up Question

        [Ask ONE follow-up question to gather more information and differentiate between potential diagnoses.]

        ### [Your question here]

        After receiving an answer to the follow-up question, update the differential diagnosis. Adjust probabilities, add or remove diagnoses as necessary, and provide reasoning for the changes.

        ### Updated Potential Diagnoses with Probabilities

        * **Diagnosis 1** - [Updated Probability]%
            + Evidence for:
            + Evidence against:
            + Reasoning:
        * **Diagnosis 2** - [Updated Probability]%
            + Evidence for:
            + Evidence against:
            + Reasoning:
        * ... (Continue for all updated potential diagnoses)

        ## Iterative Diagnostic Process

        Continue asking ONE question at a time and updating the differential diagnosis until one of the following conditions is met:

        * The probability of one diagnosis exceeds 90%
        * New answers do not change the most likely diagnosis by more than 1%

        ## Final Diagnosis

        Present the final diagnosis with a detailed explanation, including:

        ### Final Diagnosis

        * **Diagnosis:** [Final diagnosis]
        * **Probability:** [Probability]%

        ### Evidence Supporting the Diagnosis

        * **Strong evidence points:**
            1. [Strong evidence point 1]
            2. [Strong evidence point 2]
            ... (Continue as needed)
        * **Weak evidence points:**
            1. [Weak evidence point 1]
            2. [Weak evidence point 2]
            ... (Continue as needed)

        ### Contradictory Factors

        * **Contradictory factors:**
            1. [Contradictory factor 1]
            2. [Contradictory factor 2]
            ... (Continue as needed)

        ### Reasoning

        [Provide a detailed explanation of your diagnostic reasoning]

        ### Recommended Next Steps

        [Suggest any additional tests, treatments, or referrals if necessary]

    """
 

# Initialize Anthropic client
anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)
  
 

specialist_data = {
  "Emergency Medicine": {
    "assistant_id": "asst_na7TnRA4wkDbflTYKzo9kmca",
    "caption": "👨‍⚕️EM, Peds EM, ☠️Toxicology, Wilderness",
    "avatar": "https://i.ibb.co/LnrQp8p/Designer-17.jpg",
    "system_instructions": emma_system2
  },
  "Neurological": {
    "assistant_id": "asst_caM9P1caoAjFRvSAmT6Y6mIz",
    "caption": "🧠Neurology, Neurosurgery, Psychiatry",
    "avatar": "https://cdn.pixabay.com/photo/2018/11/21/02/04/graphic-3828723_1280.png"
  },
  "Sensory Systems (Eyes, Ears, Nose, Throat)": {
    "assistant_id": "asst_UB1VTD6NyYbb1xTrUueb3xlI",
    "caption": "👁️Ophthalmology, ENT",
    "avatar": "https://cdn.imgbin.com/17/1/11/imgbin-mr-potato-head-toy-child-infant-computer-icons-toy-GdJDP1cicFXdWJHbgSanRhnFQ.jpg"
  },
  "Cardiovascular and Respiratory": {
    "assistant_id": "asst_bH6wKFfCMVBiH3yUkM0DWdFk",
    "caption": "❤️Cardiology, Cardiovascular Surgery, Vascular Surgery, 🫁Pulmonology, Thoracic Surgery",
    "avatar": "https://cdn.pixabay.com/photo/2017/02/15/20/58/ekg-2069872_1280.png"
  },
  "Gastrointestinal Systems": {
    "assistant_id": "asst_Z6bVfy6eOZBVdiwoS75eGdG9",
    "caption": "Gastroenterology, Hepatology, Colorectal Surgery, General Surgery",
    "avatar": "https://cdn.pixabay.com/photo/2017/03/27/03/08/stomach-2177194_1280.png"
  },
  "Renal and GU Systems": {
    "assistant_id": "asst_SV4dNDe8sX0drryIVhQFeJj3",
    "caption": "🫘Nephrology, Gynecology, Urology, 🤰Obstetrics",
    "avatar": "https://cdn.pixabay.com/photo/2022/09/20/10/27/urology-7467570_960_720.png"
  },
  "Dermatology and Plastic Surgery": {
    "assistant_id": "asst_HzMNSMBEDBa3G6ABSISqu08e",
    "caption": "Dermatology, Plastic Surgery",
    "avatar": "https://media.istockphoto.com/id/1325453968/vector/skin-layers-structure-anatomy-diagram-human-skin-infographic-anatomical-background.jpg?s=2048x2048&w=is&k=20&c=gr7MHjhjyVZgjQhh4TyabN1gZWnxF1WlB33Ul-mr6b4="
  },
  "Musculoskeletal Systems": {
    "assistant_id": "asst_d9cMY1Sxwz0dUsKJXjuZMoiM",
    "caption": "🏈Sports Med, 🦴Orthopedics, PM&R, Rheumatology, 💪Physical Therapy",
    "avatar": "https://cdn.pixabay.com/photo/2015/12/09/22/19/muscle-1085672_1280.png",
    "system_instructions": musculoskeletal_system
  },
  "General": {
    "assistant_id": "asst_K2QHe4VfHGdyrrfTCiyctzyY",
    "caption": "ICU, Internal Medicine, HemOnc, Endocrinology",
    "avatar": "https://cdn.pixabay.com/photo/2013/07/12/18/59/doctor-154130_1280.png",
    "system_instructions": general_medicine_system
  },
  "Pediatrics": {
    "assistant_id": "asst_cVQwzy87fwOvTnb66zsvVB5L",
    "caption": "👶Pediatrics, Neonatology, Pediatric Surgery",
    "avatar": "https://cdn.pixabay.com/photo/2013/07/12/14/15/man-148077_1280.png"
  },
  "Infectious Disease": {
    "assistant_id": "asst_40hUiBxEhoylT6dCEqhssCiI",
    "caption": "🦠Infectious Disease, Epidemiology",
    "avatar": "https://cdn.pixabay.com/photo/2020/04/18/08/33/coronavirus-5058247_1280.png"
  }, 
  "Medical Legal": {
    "assistant_id": "asst_ZI3rML4v8eG1vhQ3Fis5ikOd",
    "caption": "⚖️Legal Consultant",
    "avatar": "https://cdn.pixabay.com/photo/2017/01/31/17/34/comic-characters-2025788_1280.png"
  },
  "Note Writer": {
    "assistant_id": "asst_Ua6cmp6dpTc33cSpuZxutGsX",
    "caption": "📝Medical Note Writer",
    "avatar": "https://cdn.pixabay.com/photo/2012/04/25/00/26/writing-41354_960_720.png",
    "system_instructions": note_writer_system
  },  
  "Note Summarizer": {
    "assistant_id": "asst_c2lPEtkLRILNyl5K7aJ0R38o",
    "caption": "Medical Note Summarizer",
    "avatar": "https://cdn.pixabay.com/photo/2012/04/25/00/26/writing-41354_960_720.png"
  },
  "Patient Educator": {
    "assistant_id": "asst_twf42nzGoYLtrHAZeENLcI5d",
    "caption": "Pt education Note Writer",
    "avatar": "https://cdn.pixabay.com/photo/2012/04/25/00/26/writing-41354_960_720.png",
    "system_instructions": patient_educator_system
  },
  "Dr. Longevity": {
    "assistant_id": "asst_sRjFUQFCD0dNOl7513qb4gGv",
    "caption": "Cutting edge on Longevity and Healthspan Focused",
    "avatar": "https://cdn.pixabay.com/photo/2019/07/02/05/54/tool-4311573_1280.png"
  },
  "Bayesian Reasoner": {
    "assistant_id": "asst_Ffad1oXsVwaa6R3sp012H9bx",
    "caption": "EM - Beta testing",
    "avatar": "https://cdn.pixabay.com/photo/2013/07/12/14/33/carrot-148456_960_720.png",
    "system_instructions": critical_system
  },
  "Clinical Decision Tools": {
    "assistant_id": "asst_Pau6T5mMH3cZBnEePso5kFuJ",
    "caption": "Most Common Clinical Decision Tools used in the ED",
    "avatar": "https://cdn.pixabay.com/photo/2019/07/02/05/54/tool-4311573_1280.png"
  },
  "DDX Beta A": {
    "assistant_id": "asst_8Ib5ndZJivEOhwvfx4Gqzjc3",
    "caption": "EM - Beta testing",
    "avatar": "https://cdn.pixabay.com/photo/2013/07/12/14/33/carrot-148456_960_720.png",
    "system_instructions": critical_system
  },
  "DDX Beta B": {
    "assistant_id": "asst_L74hbYKMs4OsKy0EA30mmY1s",
    "caption": "EM - Beta testing",
    "avatar": "https://cdn.pixabay.com/photo/2013/07/12/14/33/carrot-148456_960_720.png",
    "system_instructions": ddx_emma_v2
  },
  "Cardiology Clinic": {
    "assistant_id": "asst_m4Yispc9GIdwGFsyz2KNT8c5",
    "caption": "Cardiologis in Clinic - Beta testing",
    "avatar": "https://cdn.pixabay.com/photo/2017/02/15/20/58/ekg-2069872_1280.png"
  },
  "EMMA Doctor": {
    "assistant_id": "asst_m4Yispc9GIdwGFsyz2KNT8c5",
    "caption": "patient centered ai doctor",
    "avatar": "https://cdn.pixabay.com/photo/2017/02/15/20/58/ekg-2069872_1280.png",
    "system_instructions": emma_system2
  }
  
}


def load_chat_history(collection_name):
    query = {"type": {"$in": ["user_input", "ai_input"]}}
    projection = {"message": 1, "sender": 1, "timestamp": 1, "_id": 0}
    chat_history = list(db[collection_name].find(query, projection).sort("timestamp", 1))
    formatted_chat_history = []
    for entry in chat_history:
        role = "Human" if entry['sender'] == "Human" else "AI"
        formatted_entry = f"{role}: {entry['message']}"
        formatted_chat_history.append(formatted_entry)
    chat_history_string = "\n\n".join(formatted_chat_history)
    st.session_state.clean_chat_history = chat_history_string
    return chat_history_string

def search_sessions(user_id, keywords):
    collections = db.list_collection_names()
    user_sessions = [col for col in collections if col.startswith(f'user_{user_id}_session_')]
    results = []
    if not keywords.strip():
        return results
    for collection_name in user_sessions:
        existing_indexes = db[collection_name].index_information()
        text_index = next((index for index in existing_indexes.values() if any('text' in field for field in index['key'])), None)
        content_query = {"content": Regex(f".*{keywords}.*", "i")}
        combined_query = {"$and": [{"type": "chat_history"}, content_query]}
        projection = {
            "collection_name": {"$literal": collection_name},
            "timestamp": 1,
            "content": 1,
            "patient_cc": 1,
            "ddx": 1,
            "sender": 1,
        }
        collection_results = list(db[collection_name].find(combined_query, projection)
                                  .sort("timestamp", DESCENDING)
                                  .limit(10))
        if text_index:
            text_query = {"$text": {"$search": keywords}}
            text_results = list(db[collection_name].find({"$and": [{"type": "chat_history"}, text_query]}, projection)
                                .sort([("score", {"$meta": "textScore"})])
                                .limit(10))
            collection_results = list({r["_id"]: r for r in collection_results + text_results}.values())
        results.extend(collection_results)
    results.sort(key=lambda x: x['timestamp'], reverse=True)
    return results[:20]

def update_indexes(collection_name):
    db[collection_name].drop_index("message_text_patient_cc_text_content_text_test_name_text_result_text")
    db[collection_name].create_index([("content", TEXT), ("patient_cc", TEXT), ("ddx", TEXT)])

def load_session_from_search(result):
    collection_name = result['collection_name']
    user_sessions = list_user_sessions(st.session_state.username)
    session_options = {session['session_name']: session['collection_name'] for session in user_sessions}
    session_name = next((name for name, coll in session_options.items() if coll == collection_name), None)
    if session_name:
        return session_name

def initialize_text_indexes():
    collections = db.list_collection_names()
    for collection_name in collections:
        if collection_name.startswith('user_'):
            existing_indexes = db[collection_name].index_information()
            text_index = next((index for index in existing_indexes.values() if any('text' in field for field in index['key'])), None)
            if not text_index:
                try:
                    db[collection_name].create_index([
                        ("type", ASCENDING),
                        ("content", TEXT),
                        ("patient_cc", TEXT),
                        ("ddx", TEXT),
                        ("sender", ASCENDING),
                        ("timestamp", DESCENDING)
                    ], background=True, name="content_patient_cc_ddx_text_index")
                    print(f"Text index created for collection: {collection_name}")
                except Exception as e:
                    print(f"Error creating index for collection {collection_name}: {str(e)}")
            else:
                print(f"Text index already exists for collection: {collection_name}")

def display_search_results(results):
    for i, result in enumerate(results):
        st.write(f"**Date:** {result['timestamp'].strftime('%Y-%m-%d %H:%M')}")
        try:
            if st.button(f"{result['patient_cc']} - **{result['ddx'][0]['disease']}**",
                        help="click to load session",
                        type='primary'):
                session_name = load_session_from_search(result)
                return session_name
        except:
            st.write("no info")
        with st.expander("See Details..."):
            st.write(f"{result['content']}")
        st.write("---")

def search_sessions_for_searchbox(search_term):
    if not search_term.strip():
        return []
    results = search_sessions(st.session_state.username, search_term)
    scored_results = []
    for r in results:
        score = fuzz.partial_ratio(search_term.lower(), r['patient_cc'].lower())
        scored_results.append((score, r))
    sorted_results = sorted(scored_results, key=lambda x: (-x[0], -x[1]['timestamp'].timestamp()))
    return [
        (f"{r['timestamp'].strftime('%Y.%m.%d %H:%M')} - {r['patient_cc']} - {r['ddx'][0]['disease']}", r)
        for score, r in sorted_results if 'timestamp' in r and 'patient_cc' in r and 'ddx' in r and r['ddx']
    ]

def transcribe_audio(audio_file):
    try:
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        options = PrerecordedOptions(
            model="nova-2-medical",
            language="en",
            intents=False, 
            smart_format=True, 
            punctuate=True, 
            paragraphs=True, 
            diarize=True, 
            filler_words=True, 
            sentiment=False, 
        )
        source = {'buffer': audio_file, 'mimetype': 'audio/wav'}
        response = deepgram.listen.rest.v("1").transcribe_file(source, options)
        return response
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

def record_audio():
    audio_data = mic_recorder(
        start_prompt="🔵Record",
        stop_prompt="🔴Stop",
        just_once=True,
        callback=None
    )
    if audio_data:
        audio_bytes = io.BytesIO(audio_data['bytes'])
        audio_bytes.seek(0)
        with st.spinner("transcribing audio...."):
            raw_transcript = transcribe_audio(audio_bytes)
        if raw_transcript:
            transcript = raw_transcript['results']['channels'][0]['alternatives'][0]['paragraphs']['transcript']
            specialist = 'Emergency Medicine'
            # st.session_state.session_state.specialist = specialist

            if "Speaker 1" in transcript:
                prompt = f"{transcript_prompt} '''{transcript}'''"
                return prompt
            else:
                prompt = transcript.replace("Speaker 0:", "").strip()
                return prompt
    return None

# Initialize the model
model = ChatAnthropic(model="claude-3-5-sonnet-20240620", temperature=0.5, max_tokens=4096)

# Define the avatar URLs
user_avatar_url = "https://cdn.pixabay.com/photo/2016/12/21/07/36/profession-1922360_1280.png"

def initialize_session_state():
    
    if "session_state" not in st.session_state:
        st.session_state.session_state = SessionState()
        print(f'DEEBUG INITALIZE SESSIONT STATE SESSIONSTATE: {st.session_state.session_state}')
class SessionState:
    def __init__(self):
        self.user_id = None
        self.authentication_status = None
        self.logout = None
        self.collection_name = ""
        self.name = ""
        self.username = ""
        self.family_name = ""
        self.chat_history = []
        self.user_question = ""
        self.legal_question = ""
        self.note_input = ""
        self.json_data = {}
        self.pt_data = {}
        self.user_photo_url = user_avatar_url
        self.differential_diagnosis = []
        self.danger_diag_list = {}
        self.critical_actions = {}
        self.follow_up_steps = {}
        self.completed_tasks_str = ""
        self.sidebar_state = 1
        self.assistant_response = ""
        self.patient_language = "English"
        self.specialist_input = ""
        self.should_rerun = False
        self.user_question_sidebar = ""
        self.old_user_question_sidebar = ""
        self.messages = []
        self.system_instructions = emma_system2
        self.pt_title = ""
        self.patient_cc = ""
        self.clean_chat_history = ""
        self.specialist = list(specialist_data.keys())[0]
        self.assistant_id = specialist_data[self.specialist]["assistant_id"]
        self.specialist_avatar = specialist_data[self.specialist]["avatar"]
        self.session_id = None


def display_header():


    st.markdown(
        f"""
        <div style="text-align: center;">
            <h2>
                <span style="color: #04B6EA;">Emergency Medicine </span>                    
                <img src="https://i.ibb.co/LnrQp8p/Designer-17.jpg" alt="Avatar" style="width:80px;height:80px;border-radius:20%;">
                Main Assistant
            </h2>
        </div>
        """, 
        unsafe_allow_html=True)


def display_critical_tasks():
    if st.session_state.critical_actions:
        st.subheader(":blue[Critical Actions]")
        task_status = {task: False for task in st.session_state.critical_actions}
        for task in st.session_state.critical_actions:
            key = f"critical_{task}"
            task_status[task] = st.checkbox(f"- :blue[{task}]", value=task_status[task], key=key)
        completed_tasks = [task for task, status in task_status.items() if status]
        if completed_tasks:
            st.session_state.completed_tasks_str = "Tasks Completed: " + '. '.join(completed_tasks)

def display_follow_up_tasks():
    if st.session_state.follow_up_steps:
        st.subheader(":yellow[Possible Follow-Up Steps]")
        task_status = {task: False for task in st.session_state.follow_up_steps}
        for task in st.session_state.follow_up_steps:
            key = f"follow_up_{task}"
            task_status[task] = st.checkbox(f"- :yellow[{task}]", value=task_status[task], key=key)
        completed_tasks = [task for task, status in task_status.items() if status]
        if completed_tasks:
            st.session_state.completed_tasks_str = "Tasks Completed: " + '. '.join(completed_tasks)

def display_ddx():
    if st.session_state.differential_diagnosis:
        st.subheader("Differential Diagnosis")
        for diagnosis in st.session_state.differential_diagnosis:
            disease = diagnosis['disease']
            probability = diagnosis['probability']
            st.markdown(f"- {disease} - {probability}%")    

def consult_specialist_and_update_ddx(button_name, prompt):
    specialist = st.session_state.specialist
    button_input(specialist, prompt)


def display_functions_tab():
    st.subheader('Process Management')
    col1, col2 = st.columns(2)
    with col1:
        button1 = st.button("🛌Disposition Analysis", use_container_width=True)
    with col2:
        button2 = st.button("💉Which Procedure", use_container_width=True)

    st.subheader('📝Note Writer')
    col1, col2 = st.columns(2)
    with col1:
        button3 = st.button('Full Medical Note', use_container_width=True)
        button14 = st.button('Full Note except EMR results', use_container_width=True)
        button4 = st.button("🙍Pt Education Note", use_container_width=True)
    with col2:
        button11 = st.button('HPI only', use_container_width=True)
        button12 = st.button('A&P only', use_container_width=True)
        button13 = st.button('💪Physical Therapy Plan', use_container_width=True)

    st.subheader('🏃‍♂️Flow')
    col1, col2 = st.columns(2)
    with col1:
        button5 = st.button("➡️Next Step Recommendation", use_container_width=True)
        button10 = st.button("🤔Challenge the DDX", use_container_width=True)
    with col2:
        button8 = st.button('🛠️Apply Clinical Decision Tools', use_container_width=True)
        button7 = st.button("🧠Critical Thinking w Bayesian Reasoning", use_container_width=True)
    st.divider()
    col1, col2, col3 = st.columns([1,3,1])
    
    button9 = None
    start_new_session()

    process_buttons(button1, button2, button3, button4, button5, button7, button8, button9, button10, button11, button12, button13, button14)

def process_buttons(button1, button2, button3, button4, button5, button7, button8, button9, button10, button11, button12, button13, button14):
    if button1:
        specialist = 'Emergency Medicine'
        prompt = disposition_analysis
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button2:
        specialist = 'Emergency Medicine'
        prompt = procedure_checklist
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button3:
        specialist = 'Note Writer'
        prompt = "Write a full medical note on this patient"
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button4:
        specialist = 'Patient Educator'
        prompt = f"Write a patient education note for this patient in {st.session_state.patient_language}"
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button5:
        specialist = 'Emergency Medicine'
        prompt = next_step
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button7:
        specialist = 'Bayesian Reasoner'
        prompt = apply_bayesian_reasoning
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button8:
        specialist = 'Clinical Decision Tools'
        prompt = apply_decision_tool
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button9:
        new_thread()
    if button11:
        specialist = 'Note Writer'
        prompt = create_hpi
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button12:
        specialist = 'Note Writer'
        prompt = create_ap
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button13:
        specialist = 'Musculoskeletal Systems'
        prompt = pt_plan
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button14:
        specialist = 'Note Writer'
        prompt = create_full_note_except_results
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button10:
        specialist = 'General'
        prompt = challenge_ddx
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)

def choose_specialist_radio():
    specialities = list(specialist_data.keys())
    captions = [specialist_data[speciality]["caption"] for speciality in specialities]

    specialist = st.radio("**:black[Choose Your Specialty Group]**", specialities, 
                          captions=captions, 
                          index=specialities.index(st.session_state.session_state.specialist),
                          key="choose_specialist_radio")

    if specialist and specialist != st.session_state.session_state.specialist:
        st.session_state.session_state.specialist = specialist
        st.session_state.session_state.assistant_id = specialist_data[specialist]["assistant_id"]
        st.session_state.session_state.specialist_avatar = specialist_data[specialist]["avatar"]
        st.session_state.session_state.system_instructions = specialist_data[specialist]["system_instructions"]
        st.rerun()


def button_input(specialist, prompt):
    st.session_state.button_clicked = True
    st.session_state.assistant_id = specialist_id_caption[specialist]["assistant_id"]
    st.session_state.system_instructions = specialist_id_caption[specialist]["system_instructions"]
 
    user_question = prompt
    if user_question is not None and user_question != "":
        st.session_state.specialist = specialist

        specialist_avatar = specialist_id_caption[st.session_state.specialist]["avatar"]
        st.session_state.specialist_avatar = specialist_avatar
        timezone = pytz.timezone("America/Los_Angeles")
        current_datetime = datetime.now(timezone).strftime("%H:%M:%S")
        user_question = current_datetime + f"""   \n{user_question}. 
        \n{st.session_state.completed_tasks_str}
        """
        st.session_state.user_question_sidebar = user_question

        st.session_state.completed_tasks_str = ''
        st.session_state.critical_actions  = []
        st.rerun()
    st.session_state.button_clicked = False

def update_patient_language():
    patient_language = st.text_input("Insert patient language if not English", value=st.session_state.session_state.patient_language)
    if patient_language != st.session_state.session_state.patient_language:
        st.session_state.session_state.patient_language = patient_language

def process_other_queries():
    if st.session_state.session_state.user_question_sidebar != "" and st.session_state.session_state.user_question_sidebar != st.session_state.session_state.old_user_question_sidebar:
        specialist_avatar = specialist_data[st.session_state.session_state.specialist]["avatar"]
        specialist = st.session_state.session_state.specialist
        
        # load previous chat history    
        chat_history = chat_history_string()

        user_question = st.session_state.session_state.user_question_sidebar
        with st.chat_message("user", avatar=st.session_state.session_state.user_photo_url):
            st.markdown(user_question)

        st.session_state.session_state.chat_history.append(HumanMessage(user_question, avatar=st.session_state.session_state.user_photo_url))
        # save_user_message(st.session_state.session_state.username, "user", user_question)

        with st.chat_message("AI", avatar=specialist_avatar):
            assistant_response = get_response(user_question)
            # if specialist != "Note Writer":
            #     save_ai_message(st.session_state.session_state.username, specialist, assistant_response, specialist)
            # if specialist == "Note Writer":
            #     save_note_details(st.session_state.session_state.username, assistant_response)
            #     save_ai_message(st.session_state.session_state.username, specialist, assistant_response, specialist)

        st.session_state.session_state.chat_history.append(AIMessage(assistant_response, avatar=specialist_avatar))
        st.session_state.session_state.old_user_question_sidebar = user_question


        parse_json(chat_history) 

        # Clear completed tasks
        st.session_state.session_state.completed_tasks_str = ""
        st.session_state.session_state.specialist = "Emergency Medicine"
        st.rerun()


def new_thread():
    for key in list(st.session_state.keys()):
        try:
            del st.session_state[key]
        except:
            print(f"DEBUG, COULDN'T DELETE SS.KEY: {key}")
    
    html("""
        <script>
            window.parent.location.reload();
        </script>
    """)
    st.rerun()

def start_new_session():
    if 'new_session_clicked' not in st.session_state:
        st.session_state.new_session_clicked = False

    if st.button('New Session Encounter', type="secondary", use_container_width=True):
        st.session_state.new_session_clicked = True

    if st.session_state.new_session_clicked:
        st.write("Are you sure you want to start a new encounter? This will reset all current data.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, start new encounter", type="primary", use_container_width=True):
                new_thread()
        with col2:
            if st.button("No, cancel", type="secondary", use_container_width=True):
                st.session_state.new_session_clicked = False

def chat_history_string():
    output = io.StringIO()
    # print(f'\nDEBUG chat_history_string ------st.session_state.session_state.chat_history:{st.session_state.session_state.chat_history}')
    for message in st.session_state.session_state.chat_history:
        if isinstance(message, HumanMessage):
            print(message.content, file=output)
        else:
            print(message.content, file=output)

    output_string = output.getvalue()
    # save_case_details(st.session_state.session_state.username, "chat_history", output_string)
    st.session_state.session_state.clean_chat_history = output_string
    print(f'\nDEBUG chat_history_string ------output_string:{output_string}')
    return output_string


def parse_json(chat_history):
    pt_json = create_json(text=chat_history)
    try:
        data = json.loads(pt_json)
        st.session_state.pt_data = data
        st.session_state.differential_diagnosis = data['patient']['differential_diagnosis']
        st.session_state.critical_actions = data['patient']['critical_actions']
        st.session_state.follow_up_steps = data['patient']['follow_up_steps']
        
        save_case_details(st.session_state.username, "ddx")
        
        lab_results = data['patient']['lab_results']
        sequence_number = 1
        for test_name, test_result in lab_results.items():
            conditional_upsert_test_result(st.session_state.username, test_name, test_result, sequence_number)
        imaging_results = data['patient']['imaging_results']
        for test_name, test_result in imaging_results.items():
            conditional_upsert_test_result(st.session_state.username, test_name, test_result, sequence_number)
    except:
        return


def get_response(user_question: str) -> str:
    with st.spinner("Waiting for EMMA's response..."):
        response_placeholder = st.empty()
        
        chat_history = st.session_state.session_state.clean_chat_history
        system_instructions = st.session_state.session_state.system_instructions

        if isinstance(system_instructions, list):
            system_instructions = "\n".join(system_instructions)

        system_prompt = system_instructions.format(
            REQUESTED_SECTIONS='ALL',
            FILL_IN_EXPECTED_FINDINGS='fill in the normal healthy findings and include them in the note accordingly'
        )
        system_message = SystemMessage(content=system_prompt)
        
        user_content = f"Chat History:\n{chat_history} \n\n User:{user_question}"
        user_message = HumanMessage(content=user_content)
        
        messages = [system_message, user_message]

        # LLM Model Response
        response = model.invoke(messages)
        response_text = response.content

        response_placeholder.markdown(response_text)
        
        return response_text




def display_chat_history():    
    messages_per_page = 20
    page = st.session_state.get('chat_page', 0)
    # print(f'DEBUG display_chat_history ------ type: {type(st.session_state.session_state.chat_history)} --- SESSION STATE CHAT HISTORY:{st.session_state.session_state.chat_history}')
    total_messages = len(st.session_state.session_state.chat_history)
    start_idx = max(0, total_messages - (page + 1) * messages_per_page)
    end_idx = total_messages - page * messages_per_page
    
    for message in st.session_state.session_state.chat_history[start_idx:end_idx][::1]:
        if isinstance(message, HumanMessage):
            with st.chat_message("user", avatar=st.session_state.session_state.user_photo_url):                
                st.markdown(message.content, unsafe_allow_html=True)
        else:
            with st.chat_message("AI", avatar=message.avatar):
                st.markdown(message.content, unsafe_allow_html=True)
    if start_idx > 0:
        if st.button("Load More"):
            st.session_state.chat_page = page + 1
            st.rerun()

def handle_user_input_container():
    input_container = st.container()
    input_container.float(float_css_helper(
                    bottom="50px",
                    shadow=1,
                    border="1px #262730",
                    border_radius="10px",  # Rounded edges
                    height=None,  # Adjust the height as needed
                    overflow_y=None,  # Enable vertical scrolling
                    padding="20px",  # Add some padding for better appearance))
                    background="white"  
        ))
    with input_container:
        
        col_specialist, col1, col2= st.columns([1, 3, 1])
        with col_specialist:
            specialist = st.session_state.session_state.specialist
            specialist_avatar = specialist_data[specialist]["avatar"]
            st.markdown(
                f"""
                <div style="text-align: right; display: flex; justify-content: flex-end; align-items: center;">
    <div style="display: flex; align-items: center; border: ; padding: 5px; border-radius: 5px;">
        <span style="color:#048DEA; max-width: 100px; line-height: 1.2; display: inline-block; text-align: right; margin-right: 5px;">{specialist}</span>
        <img src="{specialist_avatar}" alt="Avatar" style="width:30px;height:30px;border-radius:50%;">
    </div>
</div>
                """, 
                unsafe_allow_html=True
            )

        with col1:
            user_question = st.chat_input("How may I help you?") 
        with col2:
            user_chat = record_audio()
        
    if user_question:
        process_user_question(user_question, specialist)
        st.rerun()
    elif user_chat:
        process_user_question(user_chat, specialist)
        st.rerun()

def process_user_question(user_question, specialist):
    if user_question:
        # if not st.session_state.session_state.collection_name:
        #     create_new_session()

        # load previous chat history    
        chat_history = chat_history_string()

        # Save the completed tasks before clearing
        completed_tasks = st.session_state.session_state.completed_tasks_str
        
        timezone = pytz.timezone("America/Los_Angeles")
        current_datetime = datetime.now(timezone).strftime("%H:%M:%S")
        
        # Include the completed tasks in the user l
        full_user_question = f"""{current_datetime}
            \n{user_question}
            \n{completed_tasks}
            """
        
        # save_user_message(st.session_state.session_state.username, "user", full_user_question)
        
        st.session_state.session_state.specialist = specialist
        specialist_avatar = specialist_data[specialist]["avatar"]
        st.session_state.session_state.specialist_avatar = specialist_avatar
        
        st.session_state.session_state.messages.append({"role": "user", "content": full_user_question})
        st.session_state.session_state.chat_history.append(HumanMessage(full_user_question, avatar=st.session_state.session_state.user_photo_url))
        
        with st.chat_message("user", avatar=st.session_state.session_state.user_photo_url):
            st.markdown(full_user_question)
        
        with st.chat_message("AI", avatar=specialist_avatar):
            assistant_response = get_response(full_user_question)
            st.session_state.session_state.assistant_response = assistant_response
        
        st.session_state.session_state.messages.append({"role": "assistant", "content": assistant_response})
        st.session_state.session_state.chat_history.append(AIMessage(st.session_state.session_state.assistant_response, avatar=specialist_avatar))
        
        # save_ai_message(st.session_state.session_state.username, "ai", assistant_response, specialist)

        
        parse_json(chat_history)
        
        # Clear completed tasks
        st.session_state.session_state.completed_tasks_str = ""
        
        # Debug output
        print("DEBUG: Session State after processing user question")
 
 

def display_specialist_tab():
    if st.session_state.session_state.differential_diagnosis:
        display_ddx()
        st.divider()
    
    choose_specialist_radio()
    
    st.subheader(':orange[Consult Recommendations]')
    if st.button("General Recommendations"):
        consult_specialist_and_update_ddx("General Recommendations", consult_specialist)
    if st.button("Diagnosis"):
        consult_specialist_and_update_ddx("Diagnosis consult", consult_diagnosis)
    if st.button("Treatment Plan"):
        consult_specialist_and_update_ddx("Treatment consult", consult_treatment)
    if st.button("Disposition Plan"):
        consult_specialist_and_update_ddx("Disposition consult", consult_disposition)

def display_variables_tab():
    update_patient_language()
    if st.button("Update Indexes"):
        initialize_text_indexes(st.session_state.session_state.collection_name)

def display_sidebar():
    with st.sidebar:
        st.markdown(
            f"""
            <div style="text-align: center;">
                <h1>
                    <span style="color:deepskyblue;"> </span>                    
                    <img src="https://i.ibb.co/LnrQp8p/Designer-17.jpg" alt="Avatar" style="width:50px;height:50px;border-radius:20%;">
                    EMMA
                </h1>
            </div>
            """, 
            unsafe_allow_html=True)
        
        tab1, tab2, tab4, tab5 = st.tabs(["Functions", "Specialists", "Variables", "Sessions"])
        
        with tab1:
            #display_pt_headline()
            #display_ddx()
            #display_critical_tasks()
            #display_follow_up_tasks()
            #st.divider()
            display_functions_tab()
            # container = st.container()
            # container.float(float_css_helper(bottom="10px", border="1px solid #a3a8b4", border_radius= "10px", padding= "10px"))
            # with container:
            #     logout_user() 
        with tab2:
            display_specialist_tab()
        
        with tab4:
            display_variables_tab()

          
  
def main():
    initialize_session_state()
    display_header()
    display_chat_history() 
    handle_user_input_container()   
    process_other_queries() 
    display_sidebar()
if __name__ == '__main__':
    main()