import streamlit as st

from streamlit.web.server.websocket_headers import _get_websocket_headers
# from admin import admin_dashboard, user_management, list_sessions, database_operations, feedback_management


from prompts import *
import sentry_sdk
import os

SENTRY_DSN = os.getenv('SENTRY_DSN')

sentry_sdk.init(
    dsn=SENTRY_DSN,
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)

if hasattr(st.session_state, 'patient_cc') and st.session_state.patient_cc != "":
    st.set_page_config(
        page_title=f"{st.session_state.patient_cc}", page_icon="🤖", initial_sidebar_state="auto", layout="wide", menu_items={
        'Get Help': 'https://www.perplexity.ai/',
        'Report a bug': 'mailto:bushidosunny@gmail.com',
        'About': disclaimer})
else:
    st.set_page_config(
        page_title="EMMA", page_icon="🤖", initial_sidebar_state="auto", layout="wide", menu_items={
        'Get Help': 'https://www.perplexity.ai/',
        'Report a bug': 'mailto:bushidosunny@gmail.com',
        'About': disclaimer})
        # st.session_state.page_config_set = True
        # # print("Page config set")

from streamlit_float import float_css_helper
from streamlit_js_eval import streamlit_js_eval
from anthropic import Anthropic
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import io
import time
from dotenv import load_dotenv
from extract_json import *
import json
import datetime
import pytz
from pymongo import MongoClient, ASCENDING, TEXT, DESCENDING, UpdateOne
from pymongo.errors import BulkWriteError, ServerSelectionTimeoutError, OperationFailure, ConfigurationError
from bson import ObjectId
from util.recorder import record_audio
from deepgram import DeepgramClient, PrerecordedOptions
from streamlit.components.v1 import html
from typing import List, Dict, Any, Optional
import logging
import secrets
from user_agents import parse
from auth.MongoAuthenticator import *
import extra_streamlit_components as stx
import requests
# from colorama import Fore, Style, init
from mobile import render_mobile

headers = _get_websocket_headers()

if headers.get("X-Forwarded-Proto") == "http":
    # Use JavaScript to redirect to an external URL
    st.markdown(f'<meta http-equiv="refresh" content="0;url={"https://emmahealth.ai"}">', unsafe_allow_html=True)
    st.stop()


# logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

load_dotenv()

# Constants
DB_NAME = 'emma-dev'
SECRET_KEY = secrets.token_hex(32)
PREAUTHORIZED_EMAILS = os.getenv("EMAIL_LIST")
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
MONGODB_URI = os.getenv('MONGODB_ATLAS_URI')
ENVIRONMENT = os.getenv('ENVIRONMENT')
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')

# Initialize Anthropic client
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Initialize the model
anthropic_model = ChatAnthropic(model="claude-3-5-sonnet-20240620", temperature=0.5, max_tokens=4096)

# Initialize MongoDB connection
@st.cache_resource
def init_mongodb_connection():
    logging.info("Initializing MongoDB connection")
    return MongoClient(MONGODB_URI, maxPoolSize=1, connect=False)

try:
    logging.info("Attempting to connect to MongoDB")
    mongo_client = init_mongodb_connection()
    db = mongo_client[DB_NAME]
    users_collection = db['users']
    mongo_client.admin.command('ping')
    sessions_collection = db['sessions']
    custom_buttons_collection = db['custom_buttons']
    layouts_collection = db['layouts']
    themes_collection = db['themes']
    shared_templates_collection = db['shared_templates']
    shared_buttons_collection = db['shared_buttons']
    shared_layouts_collection = db['shared_layouts']
    mongo_client.admin.command('ping')
    
    logging.info("Successfully connected to MongoDB")
except (ServerSelectionTimeoutError, OperationFailure, ConfigurationError) as err:
    logging.error(f"Error connecting to MongoDB Atlas: {err}")
    st.error(f"Error connecting to MongoDB Atlas: {err}")
    sentry_sdk.capture_exception(err)



def get_note_writer_instructions():
    user = User.from_dict(users_collection.find_one({"username": st.session_state.username}))
    note_type = st.session_state.preferred_note_type

    # Check if there's a preferred custom template for this note type
    preferred_template_id = user.preferred_templates.get(note_type)
    if preferred_template_id:
        template = next((t for t in user.get_note_templates() if t['id'] == preferred_template_id), None)
        if template:
            base_instructions = note_type_instructions.get(note_type, note_writer_system)
            # print(f"Using preferred custom template for {note_type}")
            # print(f"DEBUG Base Instructions: {base_instructions}\n\nAdditional Custom Instructions:\n{template['content']}")
            return f"{base_instructions}\n\nYOU MUST FOLLOW THE USER'S CUSTOM INSTRUCTIONS BELOW:\n{template['content']}"
    
    # If no preferred custom template, use the default instructions
    # print(f"Using default instructions for {note_type}")
    return note_type_instructions.get(note_type, note_writer_system)

specialist_data = {
  EMERGENCY_MEDICINE: {
    "assistant_id": "asst_na7TnRA4wkDbflTYKzo9kmca",
    "caption": "👨‍⚕️EM, Peds EM, ☠️Toxicology, Wilderness",
    "avatar": "https://i.ibb.co/LnrQp8p/Designer-17.jpg",
    "system_instructions": emma_system_DDX,
  },
  "Perplexity": {
    "assistant_id": "perplexity_api",
    "caption": "🔍Perplexity AI with web search and citations",
    "avatar": "https://play-lh.googleusercontent.com/6STp0lYx2ctvQ-JZpXA1LeAAZIlq6qN9gpy7swLPlRhmp-hfvZePcBxqwVkqN2BH1g",
    "system_instructions": perplixity_system
  },
  "Clinical Decision Tools": {
    "assistant_id": "asst_Pau6T5mMH3cZBnEePso5kFuJ",
    "caption": "Most Common Clinical Decision Tools used in the ED",
    "avatar": "https://cdn.pixabay.com/photo/2019/07/02/05/54/tool-4311573_1280.png",
    "system_instructions": perplexity_clinical_decision_tools_system
  },
  "Neurological": {
    "assistant_id": "asst_caM9P1caoAjFRvSAmT6Y6mIz",
    "caption": "🧠Neurology, Neurosurgery, Psychiatry",
    "avatar": "https://cdn.pixabay.com/photo/2018/11/21/02/04/graphic-3828723_1280.png",
    "system_instructions": neurological_system
  },
  "Sensory Systems (Eyes, Ears, Nose, Throat)": {
    "assistant_id": "asst_UB1VTD6NyYbb1xTrUueb3xlI",
    "caption": "👁️Ophthalmology, ENT",
    "avatar": "https://cdn.imgbin.com/17/1/11/imgbin-mr-potato-head-toy-child-infant-computer-icons-toy-GdJDP1cicFXdWJHbgSanRhnFQ.jpg",
    "system_instructions": sensory_system
  },
  "Cardiovascular and Respiratory": {
    "assistant_id": "asst_bH6wKFfCMVBiH3yUkM0DWdFk",
    "caption": "❤️Cardiology, Cardiovascular Surgery, Vascular Surgery, 🫁Pulmonology, Thoracic Surgery",
    "avatar": "https://cdn.pixabay.com/photo/2017/02/15/20/58/ekg-2069872_1280.png"
  },
  "Gastrointestinal Systems": {
    "assistant_id": "asst_Z6bVfy6eOZBVdiwoS75eGdG9",
    "caption": "💩Gastroenterology, Hepatology, Colorectal Surgery, General Surgery",
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
  GENERAL_MEDICINE: {
    "assistant_id": "asst_K2QHe4VfHGdyrrfTCiyctzyY",
    "caption": "ICU, Internal Medicine, HemOnc, Endocrinology",
    "avatar": "https://i.ibb.co/HCdc0Hx/0b0c6b4f-048c-43f9-a913-6711c4fe3ddf.jpg",
    "system_instructions": general_medicine_system,
    "subgroups": [
      "Critical Care Medicine",
      "Internal Medicine",
      "Endocrinology",
      "Geriatrics",
      "Hematology",
      "Oncology",
      "Family Medicine"
    ]
  },
  "Pediatrics": {
    "assistant_id": "asst_cVQwzy87fwOvTnb66zsvVB5L",
    "caption": "👶Pediatrics, Neonatology, Pediatric Surgery",
    "avatar": "https://cdn.pixabay.com/photo/2013/07/12/14/15/man-148077_1280.png",
    "system_instructions": pediatric_system
  },
  "Infectious Disease": {
    "assistant_id": "asst_40hUiBxEhoylT6dCEqhssCiI",
    "caption": "🦠Infectious Disease, Epidemiology",
    "avatar": "https://cdn.pixabay.com/photo/2020/04/18/08/33/coronavirus-5058247_1280.png",
    "system_instructions": infectious_disease_system
  }, 
  "Medical Legal": {
    "assistant_id": "asst_ZI3rML4v8eG1vhQ3Fis5ikOd",
    "caption": "⚖️Legal Consultant",
    "avatar": "https://cdn.pixabay.com/photo/2017/01/31/17/34/comic-characters-2025788_1280.png",
    "system_instructions": legal_system
  },
  NOTE_WRITER: {
    "assistant_id": "asst_Ua6cmp6dpTc33cSpuZxutGsX",
    "caption": "📝Medical Note Writer",
    "avatar": "https://cdn.pixabay.com/photo/2012/04/25/00/26/writing-41354_960_720.png",
    "system_instructions": get_note_writer_instructions
  },  
  "Note Summarizer": {
    "assistant_id": "asst_c2lPEtkLRILNyl5K7aJ0R38o",
    "caption": "Medical Note Summarizer",
    "avatar": "https://cdn.pixabay.com/photo/2012/04/25/00/26/writing-41354_960_720.png",
    "system_instructions": note_summarizer_system
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
    "avatar": "https://cdn.pixabay.com/photo/2019/07/02/05/54/tool-4311573_1280.png",
    "system_instructions": longevity_system
  },
  "Bayesian Reasoner": {
    "assistant_id": "asst_Ffad1oXsVwaa6R3sp012H9bx",
    "caption": "EM - Beta testing",
    "avatar": "https://cdn.pixabay.com/photo/2013/07/12/14/33/carrot-148456_960_720.png",
    "system_instructions": critical_system
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
    "avatar": "https://cdn.pixabay.com/photo/2017/02/15/20/58/ekg-2069872_1280.png",
    "system_instructions": cardiology_clinic_system
  },
  "Veterinary Medicine": {
    "assistant_id": "asst_na7TnRA4wkDbflTYKzo9kmca",
    "caption": "👨‍⚕️EM, Peds EM, ☠️Toxicology, Wilderness",
    "avatar": "https://i.postimg.cc/1R6K0vYF/OIG4.jpg",
    "system_instructions": eva_system,
  },
  "emma_system_DDX": {
    "assistant_id": "asst_na7TnRA4wkDbflTYKzo9kmca",
    "caption": "👨‍⚕️EM, Peds EM, ☠️Toxicology, Wilderness",
    "avatar": "https://i.ibb.co/LnrQp8p/Designer-17.jpg",
    "system_instructions": emma_system_DDX,
  }
}

note_type_instructions = {
    EM_NOTE: note_writer_system_em,
    "Family Medicine Note": note_writer_system_family_medicine_clinic_note,
    "General Consultation Note": note_writer_system_consult,
    "General Progress Note": note_writer_system_progress,
    "IM Admission Note": note_writer_system_admission,
    "IM Discharge Note": note_writer_system_discharge,
    "IM Progress Note": note_writer_system_IM_progress,
    "Pediatric Clinic Note": note_writer_system_pediatric_clinic_note,
    "Procedure Note": note_writer_system_procedure,
    "Transfer Note": note_writer_system_transfer,
    "All Purpose Notes": note_writer_system_document_processing,
    "Surgery Clinic Note": note_writer_system_surgery_clinic_note,
    "Veterinary Medicine Note": note_writer_vet_system,
}

################################# Initialize Session State #####################################

def initialize_session_state():
    session_state = st.session_state
    if not session_state.get('initialized'):
        session_state.initialized = True
        session_state.count = 0
        session_state.id = secrets.token_hex(8)
        session_state.user_id = None
        session_state.hospital_name = None
        session_state.hospital_contact = None
        session_state.specialty = "Emergency Medicine"
        session_state.preferred_note_type = None
        session_state.authentication_status = None
        session_state.show_registration = False
        session_state.show_forgot_username = False
        session_state.show_change_password = False
        session_state.username = ""
        session_state.user_photo_url = "https://cdn.pixabay.com/photo/2016/12/21/07/36/profession-1922360_1280.png"
        session_state.collection_name = ""
        session_state.name = ""
        session_state.timezone = 'America/Los_Angeles'
        session_state.chat_history = []
        session_state.user_question = ""
        session_state.legal_question = ""
        session_state.additional_clinic_note_input = ""
        session_state.additional_pt_note_input = ""
        session_state.json_data = {}
        session_state.pt_data = {}
        session_state.additional_instructions = ""
        session_state.differential_diagnosis = []
        session_state.danger_diag_list = []
        session_state.critical_actions = {}
        session_state.follow_up_questions = []
        session_state.physical_exam_suggestions = []
        session_state.lab_tests = []
        session_state.imaging_studies = []
        session_state.clinical_decision_tools = []
        session_state.medications = []
        session_state.completed_tasks_str = ""
        session_state.sidebar_state = 1
        session_state.assistant_response = ""
        session_state.patient_language = "English"
        session_state.specialist_input = ""
        session_state.should_rerun = False
        session_state.user_question_sidebar = ""
        session_state.old_user_question_sidebar = ""
        session_state.new_session_clicked = False
        session_state.messages = []
        session_state.pt_title = ""
        session_state.patient_cc = ""
        session_state.chief_complaint_two_word = ""
        session_state.clean_chat_history = ""
        session_state.specialist = list(specialist_data.keys())[0]
        session_state.default_specialist = ""
        session_state.system_instructions = specialist_data[session_state.specialist]["system_instructions"]
        session_state.assistant_id = specialist_data[session_state.specialist]["assistant_id"]
        session_state.specialist_avatar = specialist_data[session_state.specialist]["avatar"]
        session_state.session_id = None
        logging.info(f'Initializing Session state with initialize_session_state')

################################## AUTHENTICATION #############################################

# # Initialize Cookies
def get_cookie_manager():
    return stx.CookieManager(key="main_cookie_manager")

cookie_manager = get_cookie_manager()

authenticator = MongoAuthenticator(
    users_collection=users_collection,
    cookie_name='EMMA_auth_cookie',
    cookie_expiry_days=30,
    cookie_manager=cookie_manager 
)


def logout_user():
    st.write(st.session_state.user_photo_url)
    colL,colR = st.columns([2,1])
    with colL:
        st.markdown(
            f"""
            <div style="text-align: center;">
                <h4>                  
                    Dr. {st.session_state.name}
                </h4>
            </div>
            """, 
            unsafe_allow_html=True)
    with colR:
        # Add a unique key to the logout button
        if st.button("Logout", key="logout_button"):
            authenticator.logout()
            st.success("You have been logged out successfully.")
            time.sleep(1)  # Give user time to see the message
            # html("""
            #     <script>
            #         window.parent.location.reload();
            #     </script>
            # """)
            st.rerun()

############################## Mongo DB ##################################################

def init_db() -> None:
    users_collection.create_index([("google_id", ASCENDING)], unique=True)
    users_collection.create_index([("email", ASCENDING)], unique=True)

def update_user_activity(user: User) -> None:
    user.update_activity()
    users_collection.update_one(
        {"_id": user._id},
        {"$set": {"last_active": user.last_active}}
    )

def save_user_preferences(user: User) -> None:
    users_collection.update_one(
        {"_id": user._id},
        {"$set": {"preferences": user.preferences}}
    )

def add_note_template(user: User, title: str, template_type: str, content: str) -> None:
    user.add_note_template(title, template_type, content)
    save_user_preferences(user)

def get_user_note_templates(user: User) -> List[Dict[str, Any]]:
    return user.get_note_templates()

def update_note_template(user: User, template_id: str, title: Optional[str] = None, template_type: Optional[str] = None, content: Optional[str] = None) -> None:
    user.update_note_template(template_id, title, template_type, content)
    save_user_preferences(user)

def delete_note_template(user: User, template_id: str) -> None:
    user.delete_note_template(template_id)
    save_user_preferences(user)

def create_session(user_id: str) -> tuple[str, datetime.datetime]:
    session_token = secrets.token_urlsafe(32)
    expiration = datetime.datetime.utcnow() + datetime.timedelta(days=1)
    sessions_collection.insert_one({
        "token": session_token,
        "user_id": user_id,
        "expires": expiration
    })
    return session_token, expiration

def clear_session(session_token: str) -> None:
    sessions_collection.delete_one({"token": session_token})

def update_user_session_time(user: User, duration: datetime.timedelta) -> None:
    user.add_session_time(duration)
    users_collection.update_one(
        {"_id": user._id},
        {"$set": {"total_session_time": user.total_session_time}}
    )

def create_new_session():
    username = st.session_state.username 
    session_id = ObjectId()
    st.session_state.session_id = str(session_id)
    collection_name = f'user_{username}_session_{session_id}'
    # # print(f'CREATE_SESSION_COLLECTION COLLECTION_NAME:{collection_name}')
    st.session_state.collection_name = collection_name
    
    with mongo_client.start_session() as session:
        with session.start_transaction():
            if collection_name not in db.list_collection_names():
                db.create_collection(collection_name)
                db[collection_name].create_index([("timestamp", ASCENDING), ("test_name", ASCENDING)], unique=True)
                initialize_text_indexes(collection_name)
    
    # Increment the chat session count
    authenticator.create_new_session(st.session_state.user_id)

    return collection_name

def initialize_text_indexes(collection_name):
    existing_indexes = db[collection_name].index_information()
    text_index_exists = any('text' in str(index.get('key')) for index in existing_indexes.values())
    
    if not text_index_exists:
        try:
            db[collection_name].create_index([
                ("type", ASCENDING),
                ("content", TEXT),
                ("patient_cc", TEXT),
                ("ddx", TEXT),
                ("sender", ASCENDING),
                ("timestamp", DESCENDING)
            ], background=True, name="content_patient_cc_ddx_text_index")
            # print(f"Text index created for collection: {collection_name}")
        except Exception as e:
            st.error(f"Error creating text index for collection {collection_name}: {str(e)}")
            sentry_sdk.capture_exception(e)
    else:
        print(f"Text index already exists for collection: {collection_name}")

def validate_chat_document(document):
    required_fields = ['type', 'user_id', 'sender', 'message', 'timestamp']
    for field in required_fields:
        if field not in document:
            raise ValueError(f"Missing required field: {field}")
    
    if not isinstance(document['timestamp'], datetime):
        raise ValueError("Timestamp must be a datetime object")
    
    if document['type'] not in ['user_input', 'ai_input']:
        raise ValueError("Invalid document type")

def save_messages(user_id, messages):
    if not st.session_state.collection_name:
        create_new_session()
    
    collection = db[st.session_state.collection_name]
    bulk_operations = []
    
    for message in messages:
        chat_document = {
            "type": message['type'],
            "user_id": user_id,
            "sender": message['sender'],
            "message": message['message'],
            "timestamp": datetime.datetime.now(),
            "patient_cc": st.session_state.patient_cc
        }
        if 'specialist' in message:
            chat_document["specialist"] = message['specialist']
        
        bulk_operations.append(UpdateOne(
            {"timestamp": chat_document["timestamp"], "test_name": chat_document.get("test_name")},
            {"$set": chat_document},
            upsert=True
        ))
    
    try:
        result = collection.bulk_write(bulk_operations, ordered=False)
        # print(f"Bulk write operation: {result.upserted_count} inserted, {result.modified_count} modified")
    except BulkWriteError as bwe:
        st.warning(f"Bulk write operation partially failed: {bwe.details}")
        sentry_sdk.capture_exception(bwe)

def save_user_message(user_id, sender, message):
    save_messages(user_id, [{
        'type': 'user_input',
        'sender': sender,
        'message': message
    }])

def save_ai_message(user_id, sender, message, specialist="ai"):
    save_messages(user_id, [{
        'type': 'ai_input',
        'sender': sender,
        'message': message,
        'specialist': specialist
    }])

def save_case_details(user_id, doc_type, content=None):
    document = {
        "type": doc_type,
        "user_id": user_id,
        "ddx": st.session_state.differential_diagnosis,
        "critical_actions": st.session_state.critical_actions,
        "content": content,
        "patient_cc": st.session_state.patient_cc,
        "timestamp": datetime.datetime.now(),
    }
    query = {
        "type": doc_type,
        "user_id": user_id,
    }
    update = {"$set": document}
    try:
        result = db[st.session_state.collection_name].update_one(query, update, upsert=True)
        if result.matched_count > 0:
            print("Existing ddx document updated successfully.")
        elif result.upserted_id:
            print("New ddx document inserted successfully.")
        else:
            print("No changes made to the database.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        sentry_sdk.capture_exception(e)

def save_note_details(user_id, message):
    chat_document = {
        "type": "clinical_note",
        "user_id": user_id,
        "specialist": st.session_state.specialist,
        "message": message,
        "timestamp": datetime.datetime.now(),
    }
    db[st.session_state.collection_name].insert_one(chat_document)

def conditional_upsert_test_result(user_id, test_name, result, sequence_number):
    collection = db[st.session_state.collection_name]
    query = {"test_name": test_name, "sequence_number": sequence_number}
    try:
        existing_doc = collection.find_one(query)
        if existing_doc:
            existing_result = existing_doc.get("result", "").lower()
            if existing_result in ["not provided", "not performed yet", "not specified"] or existing_result != result.lower():
                new_sequence_number = existing_doc.get("sequence_number", 0) + 1
                new_doc = {
                    "type": "test_result",
                    "user_id": user_id,
                    "test_name": test_name,
                    "result": result,
                    "sequence_number": new_sequence_number,
                    "timestamp": datetime.datetime.now()
                }
                collection.insert_one(new_doc)
                # print(f"New test result inserted for {test_name} with sequence number {new_sequence_number}.")
            else:
                print(f"Test result for {test_name} is unchanged. No update needed.")
        else:
            new_doc = {
                "type": "test_result",
                "user_id": user_id,
                "test_name": test_name,
                "result": result,
                "sequence_number": sequence_number,
                "timestamp": datetime.datetime.now()
            }
            collection.insert_one(new_doc)
            # print(f"New test result inserted for {test_name} with sequence number {sequence_number}.")
    except Exception as e:
        print(f"An error occurred while processing {test_name}: {str(e)}")
        sentry_sdk.capture_exception(e)

@st.cache_data(ttl=60)
def list_user_sessions(username: str):
    collections = db.list_collection_names()
    username = st.session_state.username
    user_sessions = [col for col in collections if col.startswith(f'user_{username}')]
    session_details = []
    
    for session in user_sessions:
        session_id = session.split('_')[-1]
        collection_name = f'user_{username}_session_{session_id}'
        
        # Get the original timestamp
        original_timestamp = None
        latest_doc = db[collection_name].find_one(sort=[("timestamp", -1)])
        if latest_doc:
            original_timestamp = latest_doc.get("timestamp")
        else:
            collection_info = db.command("collstats", collection_name)
            original_timestamp = collection_info.get("creationTime", datetime.datetime.now())
        
        # Check for pt_encounter_name
        pt_encounter_doc = db[collection_name].find_one({"type": "pt_encounter_name"})
        if pt_encounter_doc and 'name' in pt_encounter_doc:
            session_name = pt_encounter_doc['name']
        else:
            # Use the existing logic to generate a session name
            pipeline = [
                {"$match": {"type": "ddx"}},
                {"$sort": {"timestamp": -1}},
                {"$limit": 1},
                {"$project": {
                    "timestamp": 1,
                    "patient_cc": 1,
                    "ddx": {"$ifNull": ["$ddx", []]}
                }},
                {"$project": {
                    "timestamp": 1,
                    "patient_cc": 1,
                    "disease": {"$arrayElemAt": [{"$ifNull": ["$ddx.disease", []]}, 0]}
                }}
            ]
            
            try:
                result = list(db[collection_name].aggregate(pipeline))
                
                if result:
                    doc = result[0]
                    timestamp = doc.get("timestamp")
                    date_str = timestamp.strftime("%Y.%m.%d %H:%M") if timestamp else "Unknown Date"
                    patient_cc = doc.get("patient_cc", "Unknown CC")
                    disease_name = doc.get("disease", "Unknown Disease")
                    session_name = f"{date_str} - {patient_cc} - {disease_name}"
                else:
                    if latest_doc:
                        timestamp = latest_doc.get("timestamp")
                        date_str = timestamp.strftime("%Y.%m.%d %H:%M") if timestamp else "Unknown Date"
                        session_name = f"{date_str} - No DDX - {latest_doc.get('type', 'Unknown Type')}"
                    else:
                        date_str = original_timestamp.strftime("%Y.%m.%d %H:%M")
                        session_name = f"{date_str} - Empty Session"
            except Exception as e:
                print(f"Error processing session {session_id}: {str(e)}")
                date_str = datetime.datetime.now().strftime("%Y.%m.%d %H:%M")
                session_name = f"{date_str} - Error Processing Session"
        
        session_details.append({
            "collection_name": collection_name, 
            "session_name": session_name,
            "original_timestamp": original_timestamp
        })
    
    return session_details


def sort_user_sessions_by_time(sessions):
    return sorted(sessions, key=lambda x: x['original_timestamp'], reverse=True)

@st.cache_data(ttl=60)
def load_session_data(collection_name):
    documents = list(db[collection_name].find({}).sort("timestamp", ASCENDING))
    categorized_data = {
        "ddx": [],
        "test_result": [],
        "clinical_note": [],
        "chat_history": []
    }
    for doc in documents:
        doc_type = doc.get('type')
        if doc_type == "ddx":
            categorized_data["ddx"].append(doc)
        elif doc_type == "test_result":
            categorized_data["test_result"].append(doc)
        elif doc_type == "clinical_note":
            categorized_data["clinical_note"].append(doc)
        elif doc_type in ["user_input", "ai_input"]:
            categorized_data["chat_history"].append(doc)
    return categorized_data

def delete_session_data(collection_name):
    db.drop_collection(collection_name)

def save_feedback(feedback_type, feedback_text):
    feedback_doc = {
        "user_id": st.session_state.username,
        "user_email": st.session_state.email,
        "session_id": st.session_state.session_id,
        "timestamp": datetime.datetime.now(),
        "feedback_type": feedback_type,
        "feedback_text": feedback_text
    }
    db['feedback'].insert_one(feedback_doc)

############################### Logic ###############################################################

#         # print(f"Error loading chat history: {e}")

def load_chat_history(collection_name):
    try:
        # Clear existing data
        st.session_state.chat_history = []
        st.session_state.differential_diagnosis = []
        st.session_state.critical_actions = []
        st.session_state.pt_data = {}

        # Fetch chat documents, sorted oldest to newest
        chat_documents = db[collection_name].find({"type": {"$in": ["user_input", "ai_input"]}}).sort("timestamp", 1)
        
        # Create message objects and add to chat history
        for doc in chat_documents:
            content = doc.get('message', '')
            if doc['type'] == 'user_input':
                message = HumanMessage(content=content, avatar=st.session_state.user_photo_url)
            else:
                specialist = doc.get('specialist', 'Emergency Medicine')
                avatar = specialist_data[specialist]["avatar"]
                message = AIMessage(content=content, avatar=avatar)
            
            st.session_state.chat_history.append(message)

        

        # Load most recent differential diagnosis
        ddx_doc = db[collection_name].find_one({"type": "ddx"}, sort=[("timestamp", -1)])
        if ddx_doc:
            st.session_state.differential_diagnosis = ddx_doc.get('ddx', [])
            st.session_state.critical_actions = ddx_doc.get('critical_actions', [])

        # Set other session state variables
        st.session_state.patient_cc = ddx_doc.get('patient_cc', '') if ddx_doc else ''
        st.session_state.specialist = 'Emergency Medicine'

        # # print(f"Loaded {len(st.session_state.chat_history)} messages and {len(st.session_state.differential_diagnosis)} diagnoses")
    except Exception as e:
        # print(f"Error loading chat history: {e}")
        sentry_sdk.capture_exception(e)

def search_sessions(user_id, keywords):
    collections = db.list_collection_names()
    user_sessions = [col for col in collections if col.startswith(f'user_{user_id}_session_')]
    results = []
    
    if not keywords.strip():
        return results
    
    for collection_name in user_sessions:
        pipeline = [
            {"$match": {
                "$and": [
                    {"type": "chat_history"},
                    {"$text": {"$search": keywords}}
                ]
            }},
            {"$project": {
                "collection_name": {"$literal": collection_name},
                "timestamp": 1,
                "content": 1,
                "patient_cc": 1,
                "ddx": 1,
                "sender": 1,
                "score": {"$meta": "textScore"}
            }},
            {"$sort": {"score": -1}},
            {"$limit": 10}
        ]
        
        try:
            collection_results = list(db[collection_name].aggregate(pipeline))
            results.extend(collection_results)
        except Exception as e:
            st.error(f"Error searching collection {collection_name}: {str(e)}")
            sentry_sdk.capture_exception(e)
    
    results.sort(key=lambda x: x['timestamp'], reverse=True)
    return results[:20]

def search_sessions_for_searchbox(search_term):
    if not search_term.strip():
        return []
    
    user_id = st.session_state.username
    collections = db.list_collection_names()
    user_sessions = [col for col in collections if col.startswith(f'user_{user_id}')]
    
    results = []
    for collection_name in user_sessions:
        pipeline = [
            {"$match": {
                "$and": [
                    {"type": "chat_history"},
                    {"$text": {"$search": search_term}}
                ]
            }},
            {"$project": {
                "collection_name": {"$literal": collection_name},
                "timestamp": 1,
                "patient_cc": 1,
                "ddx": 1,
                "score": {"$meta": "textScore"}
            }},
            {"$sort": {"score": -1}},
            {"$limit": 10}
        ]
        
        try:
            collection_results = list(db[collection_name].aggregate(pipeline))
            results.extend(collection_results)
        except Exception as e:
            st.error(f"Error searching collection {collection_name}: {str(e)}")
            sentry_sdk.capture_exception(e)
    
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return [
        (f"{r['timestamp'].strftime('%Y.%m.%d %H:%M')} - {r['patient_cc']} - {r['ddx'][0]['disease']}", r)
        for r in results if 'timestamp' in r and 'patient_cc' in r and 'ddx' in r and r['ddx']
    ]

def load_session_from_search(result):
    if not result:
        return None
    
    # Check if result is a tuple (as returned by search_sessions_for_searchbox)
    if isinstance(result, tuple) and len(result) == 2:
        collection_name = result[1].get('collection_name')
    # If it's a dictionary (direct result from search_sessions)
    elif isinstance(result, dict):
        collection_name = result.get('collection_name')
    else:
        st.error(f"Unexpected result format: {result}")
        return None

    if not collection_name:
        st.error(f"No collection name found in result: {result}")
        return None

    user_sessions = list_user_sessions(st.session_state.username)
    session_options = {session['session_name']: session['collection_name'] for session in user_sessions}
    session_name = next((name for name, coll in session_options.items() if coll == collection_name), None)
    
    if session_name:
        return session_name
    
    st.error(f"No matching session found for collection: {collection_name}")
    return None

def archive_old_sessions(user_id, days_threshold=30):
    current_time = datetime.datetime.now()
    archive_threshold = current_time - datetime.timedelta(days=days_threshold)
    
    collections = db.list_collection_names()
    user_sessions = [col for col in collections if col.startswith(f'user_{user_id}_session_')]
    
    for collection_name in user_sessions:
        last_activity = db[collection_name].find_one(sort=[("timestamp", -1)])
        
        if last_activity and last_activity['timestamp'] < archive_threshold:
            archive_collection_name = f"archive_{collection_name}"
            
            with mongo_client.start_session() as session:
                with session.start_transaction():
                    db[archive_collection_name].insert_many(db[collection_name].find())
                    db[collection_name].drop()
            st.info(f"Archived old session: {collection_name}")
  
def update_completed_tasks():
    completed_tasks = [task for task, status in st.session_state.items() if task.startswith("critical_") and status]
    st.session_state.completed_tasks_str = "Tasks Completed: " + '. '.join(completed_tasks) if completed_tasks else ""

def consult_specialist_and_update_ddx(button_name, prompt):
    specialist = st.session_state.specialist
    button_input(specialist, prompt)

def button_input(specialist, prompt):
    st.session_state.assistant_id = specialist_data[specialist]["assistant_id"]
    st.session_state.system_instructions = specialist_data[specialist]["system_instructions"]
    
    if specialist == NOTE_WRITER:
        st.session_state.system_instructions = get_note_writer_instructions()
    else:
        st.session_state.system_instructions = specialist_data[specialist]["system_instructions"]
 
    user_question = prompt
    if user_question:
        st.session_state.specialist = specialist
        specialist_avatar = specialist_data[st.session_state.specialist]["avatar"]
        st.session_state.specialist_avatar = specialist_avatar
        timezone = pytz.timezone(st.session_state.timezone)    
        current_datetime = datetime.datetime.now(timezone).strftime("%H:%M:%S")
        user_question = f"{current_datetime}\n{user_question}\n{st.session_state.completed_tasks_str}"
        st.session_state.user_question_sidebar = user_question

        st.session_state.completed_tasks_str = ''
        st.session_state.critical_actions = []


def choose_specialist_radio():
    specialities = list(specialist_data.keys())
    captions = [specialist_data[speciality]["caption"] for speciality in specialities]

    # Define a mapping of specific specialties to "General Medicine"
    general_medicine_specialties = [
        "Critical Care Medicine", "Internal Medicine", "HemOnc", "Endocrinology",
        "Geriatrics", "Hematology", "Oncology", "Family Medicine"
    ]

    # Map user's specialty to "General Medicine" if it's in the list
    user_specialty = st.session_state.specialty
    default_specialty = "Emergency Medicine"
    for specialty, data in specialist_data.items():
        if user_specialty == specialty or (user_specialty in data.get("subgroups", [])):
            default_specialty = specialty
            break

    default_index = specialities.index(default_specialty)

    specialist = st.radio("**:black[Choose Your Specialty Group]**", specialities, 
                          captions=captions, 
                          index=default_index,
                          key="choose_specialist_radio")

    if specialist and specialist != st.session_state.specialist:
        st.session_state.specialist = specialist
        st.session_state.assistant_id = specialist_data[specialist]["assistant_id"]
        st.session_state.specialist_avatar = specialist_data[specialist]["avatar"]
        st.session_state.system_instructions = specialist_data[specialist]["system_instructions"]
        
        # Display subgroup if available
        if "subgroups" in specialist_data[specialist]:
            subgroup = st.selectbox("Select your specific specialty:", 
                                    ["General"] + specialist_data[specialist]["subgroups"],
                                    index=0 if user_specialty not in specialist_data[specialist]["subgroups"] else 
                                    specialist_data[specialist]["subgroups"].index(user_specialty) + 1)
            if subgroup != "General":
                st.session_state.subgroup_specialty = subgroup
            else:
                st.session_state.subgroup_specialty = specialist
        else:
            st.session_state.subgroup_specialty = specialist
        
        st.rerun()

    # Display current specialty information
    # st.write(f"Current Specialty Group: **{st.session_state.specialist}**")
    # if hasattr(st.session_state, 'subgroup_specialty') and st.session_state.subgroup_specialty != st.session_state.specialist:
    #     st.write(f"Specific Specialty: **{st.session_state.subgroup_specialty}**")

def match_specialty_to_specialist(user_specialty):
    for specialist, data in specialist_data.items():
        if user_specialty.lower() == specialist.lower():
            # print(f'DEBUG MATCH SPECIALTY TO SPECIALIST1: {specialist}')
            return specialist
        if "subgroups" in data and user_specialty.lower() in [sg.lower() for sg in data["subgroups"]]:
            # print(f'DEBUG MATCH SPECIALTY TO SPECIALIST2: {specialist}')
            return specialist
    # print(f'DEBUG MATCH SPECIALTY TO SPECIALIST3: {specialist}')
    return "Emergency Medicine"  # Default to Emergency Medicine if no match found

def process_other_queries():
    if st.session_state.user_question_sidebar != "" and st.session_state.user_question_sidebar != st.session_state.old_user_question_sidebar:
        specialist_avatar = specialist_data[st.session_state.specialist]["avatar"]
        specialist = st.session_state.specialist
        # print(f'DEBUG PROCESS OTHER QUERIES SPECIALIST CHOSEN: {specialist}')
        
        user_question = st.session_state.user_question_sidebar
        with st.chat_message("user", avatar=st.session_state.user_photo_url):
            st.markdown(user_question)

        st.session_state.chat_history.append(HumanMessage(user_question, avatar=st.session_state.user_photo_url))
        save_user_message(st.session_state.username, "user", user_question)

        with st.chat_message("AI", avatar=specialist_avatar):
            assistant_response = get_response(user_question)
            if specialist == NOTE_WRITER:
                save_note_details(st.session_state.username, assistant_response)
            save_ai_message(st.session_state.username, specialist, assistant_response, specialist)

        st.session_state.chat_history.append(AIMessage(assistant_response, avatar=specialist_avatar))
        st.session_state.old_user_question_sidebar = user_question
        st.session_state.assistant_response = assistant_response  # Store the response for display in write_medical_note

        chat_history = chat_history_string()
        parse_json(chat_history) 

        # Clear completed tasks
        st.session_state.completed_tasks_str = ""

        #return to original specialist
        st.session_state.specialist = st.session_state.default_specialist
        st.rerun()

def update_patient_language(key):
    patient_language = st.text_input("Desired Language", value=st.session_state.patient_language, autocomplete="on", label_visibility="visible",
        key=key # Add this unique key
    )
    if patient_language != st.session_state.patient_language:
        st.session_state.patient_language = patient_language

def additional_pt_note_instructions():
    note_instructions = st.text_input("Additional Note Instructions", value=st.session_state.additional_pt_note_input, autocomplete="on", label_visibility="visible", key="additional_pt_note_input")
    if note_instructions != st.session_state.additional_pt_note_input:
        st.session_state.additional_pt_note_input = note_instructions
        # print(f'DEBUG ADDITIONAL PT NOTE INSTRUCTIONS: {st.session_state.additional_pt_note_input}')

def addiitional_clinic_note_instructions():
    note_instructions = st.text_input("Additional Note Instructions", value=st.session_state.additional_clinic_note_input, autocomplete="on", label_visibility="visible", key="additional_clinic_note_input")
    if note_instructions != st.session_state.additional_clinic_note_input:
        st.session_state.additional_clinic_note_input = note_instructions

def new_thread():
    # Clear all session state variables
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    initialize_session_state()
    html("""
        <script>
            window.parent.location.reload();
        </script>
    """)
    # st.rerun()


def chat_history_string():
    output = io.StringIO()

    for message in st.session_state.chat_history:
        if isinstance(message, HumanMessage):
            print(message.content, file=output)
        else:
            print(message.content, file=output)

    output_string = output.getvalue()
    save_case_details(st.session_state.username, "chat_history", output_string)
    st.session_state.clean_chat_history = output_string
    return output_string

def parse_json(chat_history):
    
    pt_json_dirty = create_json(text=chat_history)
    pt_json = pt_json_dirty.replace('```', '')

    if not pt_json or pt_json.strip() == '{}':
        # print("No data was extracted from the chat history.") 
        return
    try:
        data = json.loads(pt_json)
        patient_data = data.get('patient', {})

        # print(f'DEBUG PARSE_JSON patient_data: {patient_data}') 
        # print(f'DEBUG PARSE_JSON data: {data}')
        # Update session state
        st.session_state.pt_data = patient_data

        # Only update patient_cc if it's not empty
        # new_patient_cc = patient_data.get('chief_complaint_two_word')
        # if new_patient_cc:
        #     st.session_state.patient_cc = new_patient_cc
        
        # Ensure differential_diagnosis, critical_actions, and follow_up_questions are not None
        st.session_state.differential_diagnosis = patient_data.get('differential_diagnosis', [])
        if st.session_state.differential_diagnosis is None:
            st.session_state.differential_diagnosis = []

        st.session_state.critical_actions = patient_data.get('critical_actions', [])
        if st.session_state.critical_actions is None:
            st.session_state.critical_actions = []

        st.session_state.follow_up_questions = patient_data.get('follow_up_questions', [])
        if st.session_state.follow_up_questions is None:
            st.session_state.follow_up_questions = []

        st.session_state.physical_exam_suggestions = patient_data.get('physical_exam_suggestions', [])
        if st.session_state.physical_exam_suggestions is None:
            st.session_state.physical_exam_suggestions = []

        st.session_state.lab_tests = patient_data.get('lab_tests', [])
        if st.session_state.lab_tests is None:
            st.session_state.lab_tests = []
        
        st.session_state.imaging_studies = patient_data.get('imaging_studies', [])
        if st.session_state.imaging_studies is None:
            st.session_state.imaging_studies = []

        st.session_state.clinical_decision_tools = patient_data.get('clinical_decision_tools', [])
        if st.session_state.clinical_decision_tools is None:
            st.session_state.clinical_decision_tools = []
        
        st.session_state.medications = patient_data.get('medications', [])
        if st.session_state.medications is None:
            st.session_state.medications = []

        # # print(f'DEBUG PARSE_JSON session_state.differential_diagnosis: {st.session_state.differential_diagnosis}')
        # # print(f'DEBUG PARSE_JSON st.session_state.critical_actionss: {st.session_state.critical_actions}')
        # # print(f'DEBUG PARSE_JSON st.session_state.follow_up_questions: {st.session_state.follow_up_questions}')
        # print(f'DEBUG PARSE_JSON st.session_state.patient_cc: {st.session_state.patient_cc}')

        # Only save case details if there's meaningful data
        if any([st.session_state.differential_diagnosis, 
                st.session_state.critical_actions, 
                st.session_state.follow_up_questions]):
            save_case_details(st.session_state.username, "ddx")
        
        # Ensure lab_results and imaging_results are not None
        lab_results = patient_data.get('lab_results', {})
        if lab_results is None:
            lab_results = {}

        imaging_results = patient_data.get('imaging_results', {})
        if imaging_results is None:
            imaging_results = {}
        
        sequence_number = 1
        for results in [lab_results, imaging_results]:
            for test_name, test_result in results.items():
                if test_result:  # Only upsert if there's a result
                    conditional_upsert_test_result(st.session_state.username, test_name, test_result, sequence_number)
                    sequence_number += 1

    except Exception as e:
        # print(f"An unexpected error occurred: {str(e)}")
        # print(f"Full error details: {repr(e)}")  # This will # print more detailed error information
        sentry_sdk.capture_exception(e)


####################################### UI #########################################
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
        st.markdown(f"<h5>❗Critical Actions</h5>", unsafe_allow_html=True)
        for i, task in enumerate(st.session_state.critical_actions):
            key = f"critical_{i}"
            if st.checkbox(f"❗{task}", key=key):
                if task not in st.session_state.completed_tasks_str:
                    st.session_state.completed_tasks_str += f"Completed: {task}. "

def display_follow_up_tasks():
    if st.session_state.follow_up_questions:
        st.markdown(f"<h5>Possible Follow Questions</h5>", unsafe_allow_html=True)
        for i, task in enumerate(st.session_state.follow_up_questions):
            key = f"followupQ_{i}"
            if st.checkbox(f"{task}", key=key):
                if task not in st.session_state.completed_tasks_str:
                    st.session_state.completed_tasks_str += f"Completed: {task}. "
    
    # print(f'DEBUG DISPLAY FOLLOW UP QUESTIONS: {st.session_state.follow_up_questions}')


    exam_container = st.empty()
    with exam_container.container():
        if st.session_state.physical_exam_suggestions:
            st.markdown("<h5>Physical Exam Suggestions</h5>", unsafe_allow_html=True)
            for i, exam in enumerate(st.session_state.physical_exam_suggestions, 1):
                key = f"exam{i}"
                if st.checkbox(f"**{exam['system']}** - {exam['physical_exam_suggestion']}"):
                    if exam['physical_exam_suggestion'] not in st.session_state.completed_tasks_str:
                        st.session_state.completed_tasks_str += f"Completed: {exam['physical_exam_suggestion']}. "
    
    # print(f'DEBUG DISPLAY physical_exam_suggestion: {st.session_state.physical_exam_suggestions}')
    

    if st.session_state.lab_tests:
        st.markdown(f"<h5>Lab Tests</h5>", unsafe_allow_html=True)
        tasks = st.session_state.lab_tests.keys() if isinstance(st.session_state.lab_tests, dict) else st.session_state.lab_tests
        
        for task in tasks:
            key = f"follow_up_{task}"
            if st.checkbox(f"- :yellow[{task}]", key=key):
                if task not in st.session_state.completed_tasks_str:
                    st.session_state.completed_tasks_str += f"Followed up: {task}. "
    
    if st.session_state.imaging_studies:
        st.markdown(f"<h5>Imaging Tests</h5>", unsafe_allow_html=True)
        tasks = st.session_state.imaging_studies.keys() if isinstance(st.session_state.imaging_studies, dict) else st.session_state.imaging_studies
        
        for task in tasks:
            key = f"follow_up_{task}"
            if st.checkbox(f"- :yellow[{task}]", key=key):
                if task not in st.session_state.completed_tasks_str:
                    st.session_state.completed_tasks_str += f"Followed up: {task}. "

    if st.session_state.clinical_decision_tools:
        st.markdown(f"<h5>Clinical Decision Tools</h5>", unsafe_allow_html=True)
        tasks = st.session_state.clinical_decision_tools.keys() if isinstance(st.session_state.clinical_decision_tools, dict) else st.session_state.clinical_decision_tools
        
        for task in tasks:
            key = f"follow_up_{task}"
            if st.checkbox(f"- :yellow[{task}]", key=key):
                if task not in st.session_state.completed_tasks_str:
                    st.session_state.completed_tasks_str += f"Followed up: {task}. "

    if st.session_state.medications:
        st.markdown(f"<h5>Medications</h5>", unsafe_allow_html=True)
        tasks = st.session_state.medications.keys() if isinstance(st.session_state.medications, dict) else st.session_state.medications
        
        for task in tasks:
            key = f"follow_up_{task}"
            if st.checkbox(f"- :yellow[{task}]", key=key):
                if task not in st.session_state.completed_tasks_str:
                    st.session_state.completed_tasks_str += f"Followed up: {task}. "
    

def display_ddx():
    ddx_container = st.empty()
    with ddx_container.container():
        if st.session_state.differential_diagnosis:
            st.markdown("### Differential Diagnosis")
            for i, diagnosis in enumerate(st.session_state.differential_diagnosis, 1):
                st.markdown(f"**{i}.** **{diagnosis['disease']}** - {diagnosis['probability']}%")  

def display_mobile_ddx_follow_up():
    display_ddx()
    if st.session_state.follow_up_questions:
        st.markdown(f"<h5>Possible Follow Questions</h5>", unsafe_allow_html=True)
        for i, task in enumerate(st.session_state.follow_up_questions):
            st.markdown(f"{task}")

    
    # print(f'DEBUG DISPLAY FOLLOW UP QUESTIONS: {st.session_state.follow_up_questions}')


    exam_container = st.empty()
    with exam_container.container():
        if st.session_state.physical_exam_suggestions:
            st.markdown("<h5>Physical Exam Suggestions</h5>", unsafe_allow_html=True)
            for i, exam in enumerate(st.session_state.physical_exam_suggestions, 1):
                st.markdown(f"**{exam['system']}** - {exam['physical_exam_suggestion']}")
               
def display_pt_headline():
    
    if st.session_state.pt_data != {}:
        try:
            ## print(f'DEBUG DISPLAY HEADER ST.SESSION TATE.PT DATA: {st.session_state.pt_data}')
            cc = st.session_state.pt_data.get("chief_complaint_two_word", "")
            age = st.session_state.pt_data.get("age", "")
            age_units = st.session_state.pt_data.get("age_unit", "")
            sex = st.session_state.pt_data.get("sex", "")
            

            # Only update patient_cc if all required fields are non-empty
            if cc and age and age_units:
                sex_info = f" {sex}" if sex and sex != "Unknown" else ""
                new_patient_cc = f"{age}{age_units}{sex_info} with {cc}"
                
                # Update patient_cc only if the new value is different and non-empty
                if new_patient_cc != st.session_state.patient_cc:
                    st.session_state.patient_cc = new_patient_cc
            # print(f'DEBUG display_pt_headline st.session_state.patient_cc: {st.session_state.patient_cc}')
            st.markdown("""
            <style>
            .patient-cc {
                text-align: center;
                font-size: 25px;
                font-weight: none;
                font-style: normal;
                color: #048DEA;
                background-color: none;
                border-radius: 10px;
                padding: 0px;
                border: none;
                box-shadow: none;
                text-shadow: none;
                letter-spacing: none;
                line-height: 1.5;
                word-spacing: 5px;
                text-transform: none;
                text-decoration: none;
                }
                </style>
                """, unsafe_allow_html=True)

            st.markdown(f"<h5 class='patient-cc'>{st.session_state.patient_cc}</h5>", unsafe_allow_html=True)

        except KeyError as e:
            st.error(f"Missing key in patient data: {e}")
            st.title("EMMA")
            sentry_sdk.capture_exception(e)

    elif st.session_state.pt_data == {} and st.session_state.patient_cc != "":
        try:
            st.markdown("""
            <style>
            .patient-cc {
                text-align: center;
                font-size: 25px;
                font-weight: none;
                font-style: normal;
                color: #048DEA;
                background-color: none;
                border-radius: 10px;
                padding: 0px;
                border: none;
                box-shadow: none;
                text-shadow: none;
                letter-spacing: none;
                line-height: 1.5;
                word-spacing: 5px;
                text-transform: none;
                text-decoration: none;
                }
                </style>
                """, unsafe_allow_html=True)
            st.markdown(f"<h5 class='patient-cc'>{st.session_state.patient_cc}</h5>", unsafe_allow_html=True)

        except KeyError as e:
            st.error(f"Missing key in patient data: {e}")
            st.title("EMMA")
            sentry_sdk.capture_exception(e)

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
        
        tab1, tab5 = st.tabs(["Functions", "Settings"])
        
        with tab1:
            display_functions_tab()

        with tab5:
            display_settings_tab()
            st.divider()
            st.markdown("<br><br><br><br>", unsafe_allow_html=True)
            handle_feedback()  
   
        st.divider()
        st.markdown("<br><br><br><br>", unsafe_allow_html=True)
        # handle_feedback()        
        container = st.container()
        with container:
             
            
            c1, c2 = st.columns([1,1])
            feedback_container = st.container()
            with c1:
                st.markdown(f'Welcome {st.session_state.name}!')
            with c2:
                
                if st.button("Logout", key="logout_button", use_container_width=True):
                    authenticator.logout()
                    st.success("You have been logged out successfully.")
                    time.sleep(1)  # Give user time to see the message
                    st.rerun()
                
            # c3, c4 = st.columns([1,1])
            # # with c3:
            # #     st.markdown(f'Welcome {st.session_state.name}!')
            # with c4:
                

def display_functions_tab():
    # st.link_button("🔃New Patient Encounter", "https://emmahealth.ai", help="Will create a new session in a new tab", use_container_width=True)
    display_sessions_tab()
    
    st.divider()
    st.subheader('QUICK ACTION BUTTONS')
    
    additional_instructions = st.text_input(
        "Additional Instructions (applied to all action buttons)", 
        value=st.session_state.get('additional_instructions', ''),
        key="additional_instructions_input"
    )
    if additional_instructions != st.session_state.get('additional_instructions', ''):
        st.session_state.additional_instructions = additional_instructions


    # Function to clear instructions
    def clear_instructions():
        if 'additional_instructions' in st.session_state:
            del st.session_state.additional_instructions


    def generate_selected_notes(note_types):
        selected_notes = [note for note, selected in note_types.items() if selected]
        
        if not selected_notes:
            st.warning("Please select at least one note type.")
            return

        # Combine prompts for selected notes
        combined_prompt = f"Generate the following notes for this patient in {st.session_state.patient_language}:\n"
        for note in selected_notes:
            combined_prompt += f"- {note}\n"

        # Call the function to generate notes
        button_action("Patient Educator", combined_prompt, "Combined Patient Notes")

    def button_action(specialist, prompt_template, action_name):
        st.session_state.specialist = specialist
        additional_instructions = st.session_state.get('additional_instructions', '')
        if additional_instructions:
            prompt = f"{prompt_template}\n\nAdditional Instructions: {additional_instructions}"
        else:
            prompt = prompt_template
        consult_specialist_and_update_ddx(action_name, prompt)
        clear_instructions()
        st.rerun()

    with st.expander("Diagnostic/Treatment Tools"):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🤔Challenge DDX", use_container_width=True, help="Use to broaden and critique the current DDX"):
                button_action("General Medicine", challenge_ddx, "Challenge the DDX")
            if st.button("🌎Web Search", use_container_width=True, help="Use Perplexity Web Search"):
                button_action("Perplexity", "", "Search the Web")
        with col2:
            if st.button("🧠Refine DDX", use_container_width=True, help="Use Bayesian Reasoning to refine and narrow the DDX"):
                button_action("Bayesian Reasoner", apply_bayesian_reasoning, "Critical Thinking w Bayesian Reasoning")

            if st.button("🔍Search for CDTs/Guidelines", use_container_width=True, help="Apply Clinical Decision Tools or Known Guidelines"):
                button_action("Clinical Decision Tools", search_CDTs, "Treatment Plan")

    # Check if the specialty is Internal Medicine
    if st.session_state.get('specialty') == "Internal Medicine":
        document_processing()
        st.subheader('📝Clinical Notes')
        
        col1, col2 = st.columns(2)
        with col1:
            user = User.from_dict(users_collection.find_one({"username": st.session_state.username}))
            note_types = list(note_type_instructions.keys())
            current_note_type = user.preferred_note_type if hasattr(user, 'preferred_note_type') else "Emergency Medicine Note"
            new_note_type = st.selectbox("Preferred Note Type", 
                                        options=note_types, 
                                        index=note_types.index(current_note_type) if current_note_type in note_types else 0,
                                        key="IM_preferred_note_type")
            if new_note_type != current_note_type:
                user.preferred_note_type = new_note_type
                users_collection.update_one({"username": st.session_state.username}, {"$set": user.to_dict()})
                st.session_state.preferred_note_type = new_note_type


                custom_template = user.get_preferred_template(new_note_type)
                # st.success(f"Preferred note type updated to {new_note_type} with style {custom_template}")

        st.empty()

        col3, col4 = st.columns(2)
        with col3:
            if st.button('Complete Note', use_container_width=True, help=f"Writes a full {current_note_type} on this patient"):
                button_action(NOTE_WRITER, "Write a note on this patient.", "Full Medical Note")
            # if st.button('HPI only', use_container_width=True, help="Writes only the HPI"):
                # button_action(NOTE_WRITER, create_hpi, "HPI only")
        
        with col4:
            if st.button('Note in Parts', use_container_width=True, help="HPI, ROS, PE, A/P in copy boxes"):
                button_action(NOTE_WRITER, create_full_note_in_parts_IM, "Full Note except EMR results")

            # if st.button('A&P only', use_container_width=True, help="Writes only the Assessment and Plan"):
            #     button_action(NOTE_WRITER, create_ap, "A&P only")
        

    
    # other specialties
    else:
        # st.markdown("<br>", unsafe_allow_html=True)
        # st.subheader('📝Clinical Notes')
        with st.expander("Clinical Notes"):
            col1, col2 = st.columns(2)
            with col1:
                if st.button('Complete Note', use_container_width=True, help="Writes a full medical note on this patient"):
                    button_action(NOTE_WRITER, "Write a note on this patient.", "Full Medical Note")
                # if st.button('HPI only', use_container_width=True, help="Writes only the HPI"):
                #     button_action(NOTE_WRITER, create_hpi, "HPI only")
            
            with col2:
                if st.button('Note in Parts', use_container_width=True, help="HPI, ROS, PE, A/P in copy boxes"):
                    button_action(NOTE_WRITER, create_full_note_except_results, "Full Note except EMR results")
                # if st.button('A&P only', use_container_width=True, help="Writes only the Assessment and Plan"):
                #     button_action(NOTE_WRITER, create_ap, "A&P only")

    # st.subheader('📝Notes for Patients in specified language')
    
    
    # col1, col2 = st.columns(2)
    # with col1:
    #     update_patient_language(key="patient_language_input1")
    #     if st.button("🏢Work Note", use_container_width=True, help="Writes a personalized patient work note"):
    #         button_action("Patient Educator", f"Write a patient work note for this patient in {st.session_state.patient_language}.", "Patient Work Note")

    #     if st.button("🏫School Note", use_container_width=True, help="Writes a personalized patient school note"):
    #         button_action("Patient Educator", f"Write a patient school note for this patient in {st.session_state.patient_language}.", "Patient School Note")
        
    # with col2:
    #     if st.button("🙍Education Note", use_container_width=True, help="Writes a personalized patient education note"):
    #         button_action("Patient Educator", f"Write a patient education note for this patient in {st.session_state.patient_language}.", "Patient Education Note")

    #     if st.button('💪Physical Therapy ', use_container_width=True, help="Writes a personalized Physical Therapy plan"):
    #         button_action("Musculoskeletal Systems", pt_plan, "Physical Therapy Plan")

    #     if st.button("🏈Sports/Gym", use_container_width=True, help="Writes a personalized patient Sports/Gym note"):
    #         button_action("Patient Educator", f"Write a patient Sports/Gym note for this patient in {st.session_state.patient_language}.", "Patient Sports/Gym Note")
    # st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📝Notes for Patients"):
        # st.subheader('📝Notes for Patients')
        
        col1, col2 = st.columns(2)
        with col1:
            # Create checkboxes for each note type
            note_types = {
                "Education Note": st.checkbox("🙍Education Note", key="education_note_checkbox"),
                "Work Note": st.checkbox("🏢Work Note", key="work_note_checkbox"),
                "Physical Therapy": st.checkbox("💪Physical Therapy", key="physical_therapy_checkbox"),
                "School Note": st.checkbox("🏫School Note", key="school_note_checkbox"),
                "Sports/Gym": st.checkbox("🏈Sports/Gym", key="sports_gym_checkbox")
            }
        
        with col2:
            update_patient_language(key="patient_language_input2")
            # Button to generate selected notes
            if st.button("Generate Selected Notes", use_container_width=True):
                generate_selected_notes(note_types)


def display_specialist_tab():
    
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
    st.markdown("---")
    st.text("")
    st.text("")
    st.text("")
    st.text("")
    st.text("")
    st.text("")

def display_settings_tab():
    st.header("Help Section")
    st.markdown("[View EMMA Help Guide](https://veil-cry-a60.notion.site/EMMA-Help-Page-e681bf1c061041719b6666376cc88386)", unsafe_allow_html=True)

    # Create the embeddable link
    embed_link = f"https://drive.google.com/file/d/19Zi9WqmX_2A2XkMNVwWHIglJOkNFA3gD/view"

    # Display the video in Streamlit

    # Read the base64 string from the file
    with open("video_screenshot_encoded", "r") as file:
        encoded_image = file.read()

    # Create the data URI for the image
    data_uri = f"data:image/png;base64,{encoded_image}"

    # # Create the HTML for the clickable image
    # html_code = f'''
    # <a href="{embed_link}" target="_blank">
    #     <img src="{data_uri}" alt="Video Thumbnail" width="250" style="cursor: pointer;">
    # </a>
    # '''
    

    html_code = f'''
    <div style="text-align: center;">
        <div style="position: relative; display: inline-block;">
            <a href="{embed_link}" target="_blank">
                <img src="{data_uri}" alt="Quick How-To Video" width="250" style="cursor: pointer;">
                <div style="
                    position: absolute;
                    bottom: 10px;
                    left: 50%;
                    transform: translateX(-50%);
                    color: white;
                    background-color: rgba(0, 0, 0, 0.6);
                    padding: 5px;
                    font-size: 16px;
                    border-radius: 3px;
                ">
                    Click to Watch Video
                </div>
            </a>
        </div>
        <p style="font-size:16px;"><em>Need help? Watch our Quick How-To Video.</em></p>
    </div>
    '''
    # Render the HTML in Streamlit
    st.markdown(html_code, unsafe_allow_html=True)
    st.divider()
    # Load current user settings
    user = User.from_dict(users_collection.find_one({"username": st.session_state.username}))

    # User Details Section
    st.subheader("User Details")
    new_name = st.text_input("Name", value=user.name)
    new_hospital_name = st.text_input("Hospital/Clinic Name", value=user.hospital_name)
    new_hospital_contact = st.text_input("Hospital Contact Information", value=user.hospital_contact)

    # Default Specialty
    current_specialty = user.specialty if user.specialty else "Emergency Medicine"
    new_specialty = st.selectbox("Default Specialty", 
                                 options=SPECIALTIES, 
                                 index=SPECIALTIES.index(current_specialty),
                                 key="settings_specialty")

    # Preferred Note Type
    note_types = list(note_type_instructions.keys())
    current_note_type = user.preferred_note_type if hasattr(user, 'preferred_note_type') else "Emergency Medicine Note"
    new_note_type = st.selectbox("Preferred Note Type", 
                                 options=note_types, 
                                 index=note_types.index(current_note_type) if current_note_type in note_types else 0,
                                 key="settings_preferred_note_type")  # Changed key here

    # Note Templates Management
    # st.subheader("Note Templates")
    # template_management_option = st.radio(
    #     "Choose an action:",
    #     ["View Templates", "Create Template from Example", "Edit Template"]
    # )

    # if template_management_option == "View Templates":
    #     display_templates(user)
    # elif template_management_option == "Create Template from Example":
    #     create_template_from_example(user)
    # elif template_management_option == "Edit Template":
    #     edit_template(user)

    if st.button("Save Settings"):
        # Update user object
        user.name = new_name
        user.hospital_name = new_hospital_name
        user.hospital_contact = new_hospital_contact
        user.specialty = new_specialty
        user.preferred_note_type = new_note_type

        # Update session state
        st.session_state.name = new_name
        st.session_state.hospital_name = new_hospital_name
        st.session_state.hospital_contact = new_hospital_contact
        st.session_state.specialty = new_specialty
        st.session_state.preferred_note_type = new_note_type

        # Save to database
        users_collection.update_one(
            {"username": st.session_state.username},
            {"$set": user.to_dict()}
        )

        st.success("Settings saved successfully!")
        time.sleep(1)
        st.rerun()  # Rerun the app to apply changes

def display_chat_history():
    for i, message in enumerate(st.session_state.chat_history):
        if isinstance(message, HumanMessage):
            with st.chat_message("user", avatar=st.session_state.user_photo_url):
                col1, col2 = st.columns([0.97, 0.03])
                with col1:
                    st.markdown(message.content, unsafe_allow_html=True)
                with col2:
                    # Custom CSS for the delete button
                    st.markdown("""
                    <style>
                    .delete-button {
                        background-color: transparent;
                        border: none;
                        color: transparent;
                        cursor: pointer;
                        font-size: 18px;
                        transition: color 0.3s ease;
                        padding: 0;
                    }
                    .delete-button:hover {
                        color: #FF4B4B;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    # Create a unique key for each delete button
                    if st.button("🗑️", key=f"delete_user_{i}", help="Delete this message", 
                                 on_click=delete_message, args=(i,),
                                 kwargs={"message_type": "user_input"},
                                 use_container_width=True):
                        st.rerun()
        else:
            with st.chat_message("AI", avatar=message.avatar):
                col1, col2 = st.columns([0.97, 0.03])
                with col1:
                    st.markdown(message.content, unsafe_allow_html=True)
                with col2:
                    if st.button("🗑️", key=f"delete_ai_{i}", help="Delete this message", 
                                 on_click=delete_message, args=(i,),
                                 kwargs={"message_type": "ai_input"},
                                 use_container_width=True):
                        st.rerun()

# Add this to your Streamlit app
st.markdown("""
<script>
window.getMessage = function() {
    return new Promise(function(resolve) {
        window.addEventListener('message', function(e) {
            resolve(JSON.stringify(e.data));
        });
    });
}
</script>
""", unsafe_allow_html=True)

def display_sessions_tab():
    user_id = st.session_state.user_id
    user_sessions = list_user_sessions(user_id)
    
    if 'renaming_session' not in st.session_state:
        st.session_state.renaming_session = None
    if 'new_session_name' not in st.session_state:
        st.session_state.new_session_name = ""

    if user_sessions:
        sorted_sessions = sort_user_sessions_by_time(user_sessions)
        session_options = {session['session_name']: session['collection_name'] for session in sorted_sessions}
        
        session_name = st.selectbox("Select a recent session to load:", 
                        label_visibility="collapsed",
                        options=["Select a patient encounter"] + list(session_options.keys()),
                        index=0,
                        key="session_selectbox")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            rename_button = st.button("Rename", key="rename_session_button", use_container_width=True)
        with col2:
            st.link_button("🔃New Pt Encounter", "https://emmahealth.ai", help="Will create a new session in a new tab", use_container_width=True)
        
        if session_name != "Select a patient encounter":
            if session_name in session_options:
                collection_name = session_options[session_name]
                
                if rename_button:
                    st.session_state.renaming_session = collection_name
                    st.session_state.new_session_name = session_name

                if st.session_state.renaming_session == collection_name:
                    new_name = st.text_input("Enter new name for the session:", value=st.session_state.new_session_name, key="new_session_name_input")
                    if st.button("Save New Name", key="save_new_name_button"):
                        # Save the new name to MongoDB
                        db[collection_name].update_one(
                            {"type": "pt_encounter_name"},
                            {"$set": {"name": new_name}},
                            upsert=True
                        )
                        st.success(f"Session renamed to '{new_name}'")
                        st.session_state.renaming_session = None
                        st.session_state.new_session_name = ""
                        # Clear the cache to force a refresh of the session list
                        list_user_sessions.clear()
                        time.sleep(1)
                        st.rerun()
                    
                    if st.button("Cancel", key="cancel_rename_button"):
                        st.session_state.renaming_session = None
                        st.session_state.new_session_name = ""
                        st.rerun()
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Load Selected Patient Encounter", type='primary'):
                        st.session_state.load_session = collection_name
                        st.session_state.show_load_success = True
                with col2:
                    if st.button("Delete Selected Patient Encounter"):
                        if 'delete_confirmation' not in st.session_state:
                            st.session_state.delete_confirmation = False
                        st.session_state.delete_confirmation = True
                        st.session_state.delete_session_name = session_name
                        st.session_state.delete_collection_name = collection_name
                
                # Display success message outside of columns
                if st.session_state.get('show_load_success', False):
                    st.success(f"Session '{session_name}' selected.")
                    st.session_state.show_load_success = False  # Reset the flag
                    time.sleep(1)  # Give user time to see the message
                    st.rerun()

                if st.session_state.get('delete_confirmation', False):
                    st.warning(f"Are you sure you want to delete the session '{st.session_state.delete_session_name}'? This action cannot be undone.")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Yes, delete"):
                            delete_session_data(st.session_state.delete_collection_name)
                            st.success(f"Session '{st.session_state.delete_session_name}' deleted successfully.")
                            del st.session_state.delete_confirmation
                            del st.session_state.delete_session_name
                            del st.session_state.delete_collection_name
                            # Clear the cache to force a refresh of the session list
                            list_user_sessions.clear()
                            time.sleep(1)
                            st.rerun()
                    with col2:
                        if st.button("No, cancel"):
                            del st.session_state.delete_confirmation
                            del st.session_state.delete_session_name
                            del st.session_state.delete_collection_name
                            st.rerun()
            else:
                st.error(f"Session '{session_name}' not found in options.")
    else:
        st.write("No sessions found for this user.")

def display_session_data(collection_name):
    st.session_state.session_id = collection_name
    categorized_data = load_session_data(collection_name)
    
    
    st.session_state.collection_name = collection_name
    #st.write(f"**Data of session: {collection_name}**")
    
    with st.expander("Differential Diagnosis (ddx)"):
        for doc in categorized_data["ddx"]:
            ddx_list = doc.get('ddx', [])
            if ddx_list:
                for diagnosis in ddx_list:
                    disease = diagnosis.get('disease', 'Unknown')
                    probability = diagnosis.get('probability', 'N/A')
                    st.write(f"- {disease}: {probability}%")
    
    with st.expander("Test Results"):
        for doc in categorized_data["test_result"]:
            st.write(f"**{doc.get('test_name', 'N/A')}:** {doc.get('result', 'N/A')}")
            st.write(f"{doc.get('timestamp', 'N/A')}")
    
    with st.expander("Clinical Notes"):
        for doc in categorized_data["clinical_note"]:
            st.write(f"Specialist: {doc.get('specialist', 'N/A')}")
            st.markdown(f"Message: {doc.get('message', 'N/A')}")
            st.write(f"Timestamp: {doc.get('timestamp', 'N/A')}")
            st.write("---")
    
    with st.expander("Chat History"):
        for doc in categorized_data["chat_history"]:
            st.write(f"**Sender: {doc.get('sender', 'N/A')}**")
            st.write(f"Message: {doc.get('message', 'N/A')}")
            st.write(f"Timestamp: {doc.get('timestamp', 'N/A')}")
            st.write("---")
    
    # initialize_text_indexes(collection_name)
    
    # load_chat_history(collection_name)
    if st.button("load the chat history?", on_click=load_chat_history(collection_name)):
        # load_chat_history(collection_name)
        st.success(f"Patient Encounter Loaded")
        st.rerun()
    display_delete_session_button(collection_name)
    
def display_delete_session_button(collection_name):
    if 'delete_confirmation' not in st.session_state:
        st.session_state.delete_confirmation = False

    if st.button("Delete Patient Encounter Data?"):
        st.session_state.delete_confirmation = True

    if st.session_state.delete_confirmation:
        st.error("Are you sure you want to delete session data? This action cannot be undone.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"Yes, delete {collection_name} data", type='primary', use_container_width=True):
                # # print(f'DEBUG DELETE SESSION DATA COLLECTION NAME: {collection_name}')
                delete_session_data(collection_name)
                st.success(f"Patient Encounter data {collection_name} deleted successfully.")
                st.session_state.delete_confirmation = False
                load_session_data.clear()
                time.sleep(1)  # Give user time to see the message
                st.rerun()
        with col2:
            if st.button("No, cancel", use_container_width=True):
                st.session_state.delete_confirmation = False
                st.rerun()

def display_feedback_button():
    if st.button("📝 Feedback", use_container_width=True, help="Help make EMMA better"):
        st.session_state.show_feedback = True

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
                    background="inherit"  
        ))
    with input_container:

        col_specialist, col1, col2= st.columns([1.5, 6, 1])
        with col_specialist:
            specialist = st.session_state.specialist
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

########################################### Template Functions ###########################################

def share_template(template_id: str, shared_with: List[str]):
    user = User.from_dict(users_collection.find_one({"username": st.session_state.username}))
    shared_template = user.share_template(template_id, shared_with)
    
    if shared_template:
        shared_templates_collection.insert_one(shared_template)
        for username in shared_with:
            recipient = User.from_dict(users_collection.find_one({"username": username}))
            if recipient:
                recipient.add_shared_template(shared_template)
                users_collection.update_one(
                    {"username": username},
                    {"$set": {"shared_templates": recipient.shared_templates}}
                )
        return True
    return False

def get_shareable_users():
    current_user = st.session_state.username
    return [user['username'] for user in users_collection.find({"username": {"$ne": current_user}})]

def update_shared_template_rating(template_id: str, username: str, rating: int, comment: str = ""):
    shared_templates_collection.update_one(
        {"id": template_id},
        {
            "$push": {
                "ratings": {"user": username, "rating": rating},
                "reviews": {"user": username, "rating": rating, "comment": comment, "timestamp": datetime.datetime.now()}
            }
        }
    )

def get_featured_templates():
    return list(shared_templates_collection.find().sort([("ratings.rating", -1)]).limit(5))

def manage_custom_templates():
    st.subheader("Manage Custom Note Templates")

    user = User.from_dict(users_collection.find_one({"username": st.session_state.username}))
    custom_templates = user.get_note_templates()
    shared_templates = user.shared_templates

    # Featured Templates Section
    st.subheader("Featured Templates")
    featured_templates = get_featured_templates()
    for template in featured_templates:
        avg_rating = sum(r["rating"] for r in template.get("ratings", [])) / len(template.get("ratings", [1])) if template.get("ratings") else 0
        st.write(f"⭐ {template['name']} (Avg Rating: {avg_rating:.1f}/5)")

    # Filtering and Sorting Options
    st.subheader("All Shared Templates")
    sort_option = st.selectbox("Sort by:", ["Rating", "Use Count", "Recency"])
    filter_option = st.multiselect("Filter by Note Type:", list(set(t["note_type"] for t in shared_templates)))

    # Sort and filter shared templates
    filtered_templates = [t for t in shared_templates if not filter_option or t["note_type"] in filter_option]
    if sort_option == "Rating":
        filtered_templates.sort(key=lambda t: sum(r["rating"] for r in t.get("ratings", [])) / len(t.get("ratings", [1])) if t.get("ratings") else 0, reverse=True)
    elif sort_option == "Use Count":
        filtered_templates.sort(key=lambda t: t.get("use_count", 0), reverse=True)
    else:  # Recency
        filtered_templates.sort(key=lambda t: max((r["timestamp"] for r in t.get("reviews", [])), default=datetime.datetime.min), reverse=True)

    for template in filtered_templates:
        avg_rating = user.get_shared_template_rating(template['id'])
        with st.expander(f"{template['name']} - Shared by: {template['original_author']} (Avg Rating: {avg_rating:.1f if avg_rating else 0}/5)"):
            st.write(f"Note Type: {template['note_type']}")
            st.text_area("System Prompt", value=template['system_prompt'], height=150, key=f"shared_prompt_{template['id']}")
            
            # Add rating and review functionality
            user_rating = st.slider("Rate this template", 1, 5, key=f"rate_shared_{template['id']}")
            user_comment = st.text_area("Leave a comment (optional)", key=f"comment_shared_{template['id']}")
            if st.button("Submit Review", key=f"submit_review_{template['id']}"):
                if user.rate_shared_template(template['id'], user_rating, user_comment):
                    update_shared_template_rating(template['id'], user.username, user_rating, user_comment)
                    users_collection.update_one(
                        {"username": st.session_state.username},
                        {"$set": {"shared_templates": user.shared_templates}}
                    )
                    st.success("Review submitted successfully!")
                    st.rerun()
            
            # Display existing reviews
            st.subheader("Reviews")
            reviews = user.get_shared_template_reviews(template['id'])
            for review in reviews:
                st.write(f"User: {review['user']}")
                st.write(f"Rating: {'⭐' * review['rating']}")
                st.write(f"Comment: {review['comment']}")
                st.write(f"Date: {review['timestamp'].strftime('%Y-%m-%d %H:%M')}")
                st.write("---")

    # Custom Templates Section
    st.subheader("Your Custom Templates")
    for template in custom_templates:
        with st.expander(f"{template['name']} ({template['note_type']})"):
            st.write(f"Use Count: {template.get('use_count', 0)}")
            st.text_area("System Prompt", value=template['system_prompt'], height=150, key=f"custom_prompt_{template['id']}")
            
            if st.button("Share", key=f"share_{template['id']}"):
                shareable_users = get_shareable_users()
                shared_with = st.multiselect("Share with:", shareable_users)
                if st.button("Confirm Share"):
                    if share_template(template['id'], shared_with):
                        st.success(f"Template '{template['name']}' shared successfully!")
                    else:
                        st.error("Failed to share template. Please try again.")

            if st.button("Edit", key=f"edit_{template['id']}"):
                st.session_state.editing_template = template['id']
            
            if st.button("Delete", key=f"delete_{template['id']}"):
                user.delete_note_template(template['id'])
                users_collection.update_one(
                    {"username": st.session_state.username},
                    {"$set": {"preferences": user.preferences}}
                )
                st.success(f"Template '{template['name']}' deleted successfully!")
                st.rerun()

    # ... (rest of the function for creating/editing templates)

def check_new_shared_templates():
    user = User.from_dict(users_collection.find_one({"username": st.session_state.username}))
    new_templates = [t for t in user.shared_templates if t.get('new', True)]
    
    if new_templates:
        st.sidebar.warning(f"You have {len(new_templates)} new shared template(s)!")
        if st.sidebar.button("View Shared Templates"):
            st.session_state.show_shared_templates = True

def mark_shared_templates_as_seen():
    user = User.from_dict(users_collection.find_one({"username": st.session_state.username}))
    for template in user.shared_templates:
        template['new'] = False
    users_collection.update_one(
        {"username": st.session_state.username},
        {"$set": {"shared_templates": user.shared_templates}}
    )

def manage_custom_templates():
    st.subheader("Manage Note Templates")

    user = User.from_dict(users_collection.find_one({"username": st.session_state.username}))
    custom_templates = user.get_note_templates()
    shared_templates = user.shared_templates

    # Featured Templates Section
    st.subheader("Featured Templates")
    featured_templates = get_featured_templates()
    for template in featured_templates:
        avg_rating = sum(r["rating"] for r in template.get("ratings", [])) / len(template.get("ratings", [1])) if template.get("ratings") else 0
        st.write(f"⭐ {template['name']} (Avg Rating: {avg_rating:.1f}/5)")

    # Shared Templates Section
    st.subheader("Shared Templates")
    
    # Filtering and Sorting Options
    col1, col2 = st.columns(2)
    with col1:
        sort_option = st.selectbox("Sort by:", ["Rating", "Use Count", "Recency"])
    with col2:
        filter_option = st.multiselect("Filter by Note Type:", list(set(t["note_type"] for t in shared_templates)))

    # Sort and filter shared templates
    filtered_templates = [t for t in shared_templates if not filter_option or t["note_type"] in filter_option]
    if sort_option == "Rating":
        filtered_templates.sort(key=lambda t: sum(r["rating"] for r in t.get("ratings", [])) / len(t.get("ratings", [1])) if t.get("ratings") else 0, reverse=True)
    elif sort_option == "Use Count":
        filtered_templates.sort(key=lambda t: t.get("use_count", 0), reverse=True)
    else:  # Recency
        filtered_templates.sort(key=lambda t: max((r["timestamp"] for r in t.get("reviews", [])), default=datetime.datetime.min), reverse=True)

    for template in filtered_templates:
        avg_rating = user.get_shared_template_rating(template['id'])
        with st.expander(f"{template['name']} - Shared by: {template['original_author']} (Avg Rating: {avg_rating:.1f if avg_rating else 0}/5)"):
            st.write(f"Note Type: {template['note_type']}")
            st.text_area("System Prompt", value=template['system_prompt'], height=150, key=f"shared_prompt_{template['id']}")
            
            # Rating and review functionality
            col1, col2 = st.columns(2)
            with col1:
                user_rating = st.slider("Rate this template", 1, 5, key=f"rate_shared_{template['id']}")
            with col2:
                user_comment = st.text_area("Leave a comment (optional)", key=f"comment_shared_{template['id']}")
            if st.button("Submit Review", key=f"submit_review_{template['id']}"):
                if user.rate_shared_template(template['id'], user_rating, user_comment):
                    update_shared_template_rating(template['id'], user.username, user_rating, user_comment)
                    users_collection.update_one(
                        {"username": st.session_state.username},
                        {"$set": {"shared_templates": user.shared_templates}}
                    )
                    st.success("Review submitted successfully!")
                    st.rerun()
            
            # Display existing reviews
            st.subheader("Reviews")
            reviews = user.get_shared_template_reviews(template['id'])
            for review in reviews:
                st.write(f"User: {review['user']}")
                st.write(f"Rating: {'⭐' * review['rating']}")
                st.write(f"Comment: {review['comment']}")
                st.write(f"Date: {review['timestamp'].strftime('%Y-%m-%d %H:%M')}")
                st.write("---")

            # Accept or reject shared template
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Accept", key=f"accept_{template['id']}"):
                    user.add_note_template(template['name'], template['note_type'], template['system_prompt'])
                    users_collection.update_one(
                        {"username": st.session_state.username},
                        {"$set": {"preferences": user.preferences}}
                    )
                    st.success(f"Template '{template['name']}' added to your custom templates!")
                    st.rerun()
            with col2:
                if st.button("Reject", key=f"reject_{template['id']}"):
                    user.shared_templates = [t for t in user.shared_templates if t['id'] != template['id']]
                    users_collection.update_one(
                        {"username": st.session_state.username},
                        {"$set": {"shared_templates": user.shared_templates}}
                    )
                    st.success(f"Template '{template['name']}' removed from shared templates.")
                    st.rerun()

    # Custom Templates Section
    st.subheader("Your Custom Templates")
    for template in custom_templates:
        with st.expander(f"{template['name']} ({template['note_type']})"):
            st.write(f"Use Count: {template.get('use_count', 0)}")
            st.text_area("System Prompt", value=template['system_prompt'], height=150, key=f"custom_prompt_{template['id']}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Share", key=f"share_{template['id']}"):
                    shareable_users = get_shareable_users()
                    shared_with = st.multiselect("Share with:", shareable_users)
                    if st.button("Confirm Share"):
                        if share_template(template['id'], shared_with):
                            st.success(f"Template '{template['name']}' shared successfully!")
                        else:
                            st.error("Failed to share template. Please try again.")
            with col2:
                if st.button("Edit", key=f"edit_{template['id']}"):
                    st.session_state.editing_template = template['id']
            with col3:
                if st.button("Delete", key=f"delete_{template['id']}"):
                    user.delete_note_template(template['id'])
                    users_collection.update_one(
                        {"username": st.session_state.username},
                        {"$set": {"preferences": user.preferences}}
                    )
                    st.success(f"Template '{template['name']}' deleted successfully!")
                    st.rerun()

    # Create New Template Section
    st.subheader("Create New Template")
    new_template_name = st.text_input("New Template Name")
    new_template_type = st.selectbox("Note Type", list(note_type_instructions.keys()))
    new_template_prompt = st.text_area("System Prompt", height=150)
    if st.button("Create Template"):
        if new_template_name and new_template_prompt:
            user.add_note_template(new_template_name, new_template_type, new_template_prompt)
            users_collection.update_one(
                {"username": st.session_state.username},
                {"$set": {"preferences": user.preferences}}
            )
            st.success(f"New template '{new_template_name}' created successfully!")
            st.rerun()
        else:
            st.error("Please provide both a name and a prompt for the new template.")

    # Edit Template Section
    if 'editing_template' in st.session_state:
        template = user.get_note_template(st.session_state.editing_template)
        if template:
            st.subheader(f"Editing Template: {template['name']}")
            edited_name = st.text_input("Template Name", value=template['name'])
            edited_type = st.selectbox("Note Type", list(note_type_instructions.keys()), index=list(note_type_instructions.keys()).index(template['note_type']))
            edited_prompt = st.text_area("System Prompt", value=template['system_prompt'], height=150)
            if st.button("Save Changes"):
                user.update_note_template(template['id'], edited_name, edited_type, edited_prompt)
                users_collection.update_one(
                    {"username": st.session_state.username},
                    {"$set": {"preferences": user.preferences}}
                )
                st.success("Template updated successfully!")
                del st.session_state.editing_template
                st.rerun()
            if st.button("Cancel Editing"):
                del st.session_state.editing_template
                st.rerun()

def analyze_note_format(example_note: str, note_type: str):
    system_prompt = f"""
    Analyze the following {note_type} and create detailed system instructions for generating similar notes. Focus on:

    1. Overall structure and sections
    2. Level of detail in each section
    3. Use of medical terminology, abbreviations, and specialized language
    4. Temporal organization of information
    5. Presentation of patient demographics and identifiers
    6. Structure of assessment and treatment plan
    7. Integration of objective data (lab results, vital signs, etc.)
    8. Documentation of patient-provider interactions
    9. Follow-up and continuity of care elements
    10. Any unique formatting or style elements, including:
        - Use of bullet points, numbered lists, or other formatting
        - Emphasis techniques (bold, italics, underlining)
        - Use of templates or standardized sections
    11. Compliance and regulatory elements
 

    Your output should be in the form of clear, concise instructions that could be given to an AI to reproduce this note style, capturing the unique preferences and requirements of the healthcare provider.

    Example Note:
    {example_note}

    Based on this analysis, provide only the system instructions for generating similar notes. Provide an outline with format instructions of the desired note for easy reference. Do not include any commentary before or after the instructions.
    """

    system_message = SystemMessage(content=system_prompt)
    user_message = HumanMessage(content="Please analyze the note and provide system instructions.")

    messages = [system_message, user_message]

    # LLM Model Response
    response = anthropic_model.invoke(messages)
    response_text = response.content

    return response_text

def create_template_from_example(user):
    st.subheader("Create Template from Example")
    
    if 'template_creation_stage' not in st.session_state:
        st.session_state.template_creation_stage = 'initial'

    if st.session_state.template_creation_stage == 'initial':
        new_template_title = st.text_input("Template Title")
        new_template_type = st.selectbox("Note Type", list(note_type_instructions.keys()))
        example_note = st.text_area("Paste your example note here", height=300)
        
        if st.button("Analyze Note"):
            if example_note and new_template_title and new_template_type:
                with st.spinner("Analyzing note format..."):
                    analyzed_instructions = analyze_note_format(example_note, new_template_type)
                st.session_state.analyzed_instructions = analyzed_instructions
                st.session_state.new_template_title = new_template_title
                st.session_state.new_template_type = new_template_type
                st.session_state.template_creation_stage = 'edit_instructions'
                st.rerun()
            else:
                st.error("Please provide a title, note type, and an example note to analyze.")

    elif st.session_state.template_creation_stage == 'edit_instructions':
        st.subheader(f"Editing Template: {st.session_state.new_template_title}")
        st.write(f"Note Type: {st.session_state.new_template_type}")
        
        edited_instructions = st.text_area("System Instructions (you can edit these)", 
                                           value=st.session_state.analyzed_instructions, 
                                           height=300)
        
        if st.button("Generate Sample Note"):
            with st.spinner("Generating sample note..."):
                sample_note = generate_sample_note(edited_instructions, st.session_state.new_template_type)
            st.session_state.sample_note = sample_note
            st.session_state.template_creation_stage = 'review_sample'
            st.rerun()

    elif st.session_state.template_creation_stage == 'review_sample':
        st.subheader(f"Review Sample Note: {st.session_state.new_template_title}")
        st.write(f"Note Type: {st.session_state.new_template_type}")
        
        st.text_area("Sample Note", value=st.session_state.sample_note, height=300, disabled=True)
        
        feedback = st.text_area("Provide feedback or suggestions for improvement", height=150)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Refine Instructions"):
                if feedback:
                    with st.spinner("Refining instructions..."):
                        refined_instructions = refine_instructions(st.session_state.analyzed_instructions, feedback)
                    st.session_state.analyzed_instructions = refined_instructions
                    st.session_state.template_creation_stage = 'edit_instructions'
                    st.rerun()
                else:
                    st.error("Please provide feedback for refinement.")
        
        with col2:
            if st.button("Save Template"):
                set_as_preferred = st.checkbox("Set as preferred template for this note type")
                template_id = user.add_note_template(st.session_state.new_template_title, 
                                                     st.session_state.new_template_type, 
                                                     st.session_state.analyzed_instructions)
                if set_as_preferred:
                    user.set_preferred_template(st.session_state.new_template_type, template_id)
                
                users_collection.update_one(
                    {"username": st.session_state.username},
                    {"$set": user.to_dict()}
                )
                st.success(f"New template '{st.session_state.new_template_title}' created successfully!")
                reset_template_creation_state()
                time.sleep(30)
                st.rerun()
        
        with col3:
            if st.button("Start Over"):
                reset_template_creation_state()
                st.rerun()

def reset_template_creation_state():
    if 'template_creation_stage' in st.session_state:
        del st.session_state.template_creation_stage
    if 'analyzed_instructions' in st.session_state:
        del st.session_state.analyzed_instructions
    if 'new_template_title' in st.session_state:
        del st.session_state.new_template_title
    if 'new_template_type' in st.session_state:
        del st.session_state.new_template_type
    if 'sample_note' in st.session_state:
        del st.session_state.sample_note

def refine_instructions(current_instructions: str, feedback: str):
    system_prompt = f"""
    You are an AI assistant specialized in refining medical note generation instructions. 
    Given the current instructions and user feedback, improve the instructions to better meet the user's needs.

    Current Instructions:
    {current_instructions}

    User Feedback:
    {feedback}

    Please provide only the refined instructions that address the user's feedback while maintaining the overall structure and purpose of the note. Do not include any commentary.
    """

    system_message = SystemMessage(content=system_prompt)
    user_message = HumanMessage(content="Please refine the instructions based on the given feedback.")

    messages = [system_message, user_message]

    # LLM Model Response
    response = anthropic_model.invoke(messages)
    response_text = response.content

    return response_text

def generate_sample_note(system_instructions: str, note_type: str):
    system_prompt = f"""
    You are an AI assistant specialized in generating medical notes. Use the following system instructions to create a sample {note_type}. 
    Generate a realistic but fictional patient scenario.

    System Instructions:
    {system_instructions}

    Now, generate a sample {note_type} based on these instructions.
    """

    system_message = SystemMessage(content=system_prompt)
    user_message = HumanMessage(content="Please generate a sample note based on the given instructions.")

    messages = [system_message, user_message]

    # LLM Model Response
    response = anthropic_model.invoke(messages)
    response_text = response.content

    return response_text    


def write_medical_note():
    user = User.from_dict(users_collection.find_one({"username": st.session_state.username}))
    custom_templates = user.get_note_templates()
    
    # Combine default and custom templates
    all_templates = [{"title": "Default", "type": st.session_state.preferred_note_type, "content": note_type_instructions[st.session_state.preferred_note_type]}] + custom_templates
    
    # Sort templates by use count (if available)
    all_templates.sort(key=lambda x: x.get('use_count', 0), reverse=True)
    
    # Create options for selectbox
    template_options = [f"{t['title']} ({t['type']}) - Uses: {t.get('use_count', 0)}" for t in all_templates]
    
    selected_template = st.selectbox("Choose Note Template", template_options)
    
    # Extract the template title from the selected option
    selected_title = selected_template.split(" (")[0]
    
    # Find the selected template
    template = next((t for t in all_templates if t['title'] == selected_title), None)
    
    if not template:
        st.error("Selected template not found. Using default template.")
        template = all_templates[0]  # Use the default template

    # Note generation code
    st.subheader("Patient Information")
    patient_info = st.text_area("Enter patient information", height=150)

    prompt = f"Generate a {template['type']} based on the following patient information:\n\n{patient_info}\n\nUse the following system instructions for the note format:\n\n{template['content']}"
    
    # Set the specialist to NOTE_WRITER
    original_specialist = st.session_state.specialist
    st.session_state.specialist = NOTE_WRITER
    
    # Generate the note
    with st.spinner("Generating medical note..."):
        generated_note = get_response(prompt)
    
    # Reset the specialist
    st.session_state.specialist = original_specialist
    
    # Display the generated note
    st.subheader("Generated Medical Note")
    st.text_area("Generated Note", value=generated_note, height=300)
    
    # Save the note
    save_note_details(st.session_state.username, generated_note)
    
    # Increment use count for custom templates
    if template['title'] != "Default":
        user.increment_template_use_count(template['id'])
        users_collection.update_one(
            {"username": st.session_state.username},
            {"$set": {"preferences": user.preferences}}
        )
    
    # After generating the note, ask for feedback
    if template['title'] != "Default":
        st.write("How satisfied are you with this note?")
        rating = st.slider("Rate this template", 1, 5, 3)
        feedback = st.text_area("Provide feedback (optional)")
        if st.button("Submit Feedback"):
            user.rate_custom_note_template(template['id'], rating)
            if feedback:
                # You might want to store this feedback for future improvements
                pass
            users_collection.update_one(
                {"username": st.session_state.username},
                {"$set": {"preferences": user.preferences}}
            )
            st.success("Thank you for your feedback!")


################################ template UI ################################
def display_templates(user):
    st.subheader("View and Manage Templates")
    
    # Get all templates
    templates = user.get_note_templates()
    if not templates:
        st.write("You don't have any custom templates yet.")
        return

    # Group templates by note type
    templates_by_type = {}
    for template in templates:
        if template['type'] not in templates_by_type:
            templates_by_type[template['type']] = []
        templates_by_type[template['type']].append(template)

    # Display templates grouped by note type
    for note_type, type_templates in templates_by_type.items():
        st.write(f"### {note_type}")
        
        # Get the current preferred template for this note type
        current_preferred_id = user.get_preferred_template(note_type)
        
        # Create a selectbox for choosing the preferred template
        template_options = ["None"] + [t['title'] for t in type_templates]
        preferred_index = 0
        if current_preferred_id:
            preferred_index = next((i for i, t in enumerate(type_templates) if t['id'] == current_preferred_id), 0) + 1

        new_preferred = st.selectbox(
            f"Preferred template for {note_type}:",
            options=template_options,
            index=preferred_index,
            key=f"preferred_{note_type}"
        )

        # Update the preferred template if changed
        if new_preferred != "None":
            new_preferred_id = next(t['id'] for t in type_templates if t['title'] == new_preferred)
            if new_preferred_id != current_preferred_id:
                user.set_preferred_template(note_type, new_preferred_id)
                st.success(f"Updated preferred template for {note_type}")
        elif current_preferred_id:
            user.set_preferred_template(note_type, None)
            st.success(f"Removed preferred template for {note_type}")

        # Display each template
        for template in type_templates:
            with st.expander(f"{template['title']} ({'Preferred' if template['id'] == current_preferred_id else 'Custom'})"):
                st.write(f"Use Count: {template.get('use_count', 0)}")
                st.text_area("System Prompt", value=template['content'], height=150, key=f"view_prompt_{template['id']}", disabled=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Edit", key=f"edit_{template['id']}"):
                        st.session_state.editing_template = template['id']
                        st.rerun()
                with col2:
                    delete_key = f"delete_{template['id']}"
                    
                    if st.button("Delete", key=delete_key):
                        st.session_state.template_to_delete = template['id']
                        st.session_state.show_delete_confirmation = True
                        st.rerun()
                # Handle template deletion confirmation
                if hasattr(st.session_state, 'show_delete_confirmation') and st.session_state.show_delete_confirmation:
                    st.warning("Are you sure you want to delete this template?")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Yes, delete", key=f"confirm_delete_{template['id']}"):
                            template_id = st.session_state.template_to_delete
                            if user.delete_note_template(template_id):
                                st.success(f"Template deleted successfully!")
                                # Update the user in the database
                                if authenticator.update_user(st.session_state.username, user.to_dict()):
                                    st.success("User data updated in database.")
                                else:
                                    st.error("Failed to update user data in database.")
                                # Clear the deletion state
                                del st.session_state.template_to_delete
                                del st.session_state.show_delete_confirmation
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"Failed to delete template")
                    with col2:
                        if st.button("No, cancel", key=f"cancel_delete_{template['id']}"):
                            # Clear the deletion state
                            del st.session_state.template_to_delete
                            del st.session_state.show_delete_confirmation
                            st.rerun()
    

    # Handle template editing
    if hasattr(st.session_state, 'editing_template'):
        edit_template(user, st.session_state.editing_template)

def edit_template(user):
    templates = user.get_note_templates()
    if not templates:
        st.write("You don't have any custom templates to edit.")
        return

    template_to_edit = st.selectbox("Select template to edit", [t['title'] for t in templates])
    template = next((t for t in templates if t['title'] == template_to_edit), None)

    if template:
        st.subheader(f"Editing Template: {template['title']}")
        new_title = st.text_input("Template Title", value=template['title'])
        new_type = st.selectbox("Note Type", list(note_type_instructions.keys()), index=list(note_type_instructions.keys()).index(template['type']))
        new_content = st.text_area("System Prompt", value=template['content'], height=300)
        
        if st.button("Save Changes"):
            user.update_note_template(template['id'], new_title, new_type, new_content)
            users_collection.update_one(
                {"username": st.session_state.username},
                {"$set": user.to_dict()}
            )
            st.success("Template updated successfully!")
            time.sleep(2)
            st.rerun()

def create_new_template(user):
    st.subheader("Create New Template")
    new_template_title = st.text_input("Template Title")
    new_template_type = st.selectbox("Note Type", list(note_type_instructions.keys()))
    
    use_example = st.checkbox("Use an example note to generate instructions")
    
    if use_example:
        example_note = st.text_area("Paste your example note here", height=300)
        if st.button("Analyze Note"):
            if example_note:
                with st.spinner("Analyzing note format..."):
                    analyzed_instructions = analyze_note_format(example_note, new_template_type)
                st.session_state.analyzed_instructions = analyzed_instructions
                st.success("Note analyzed! You can now edit the generated instructions.")
            else:
                st.error("Please provide an example note to analyze.")
    
    if 'analyzed_instructions' in st.session_state:
        new_template_content = st.text_area("System Instructions (you can edit these)", 
                                            value=st.session_state.analyzed_instructions, 
                                            height=300)
    else:
        new_template_content = st.text_area("System Instructions", height=300)
    
    if st.button("Create Template"):
        if new_template_title and new_template_content:
            user.add_note_template(new_template_title, new_template_type, new_template_content)
            users_collection.update_one(
                {"username": st.session_state.username},
                {"$set": {"preferences": user.preferences}}
            )
            st.success(f"New template '{new_template_title}' created successfully!")
            if 'analyzed_instructions' in st.session_state:
                del st.session_state.analyzed_instructions
            time.sleep(2)
            st.rerun()
        else:
            st.error("Please provide both a title and instructions for the new template.")

def delete_template(user):
    templates = user.get_note_templates()
    if not templates:
        st.write("You don't have any custom templates to delete.")
        return

    template_to_delete = st.selectbox("Select template to delete", [t['title'] for t in templates])
    template = next((t for t in templates if t['title'] == template_to_delete), None)

    if template:
        st.write(f"Are you sure you want to delete the template '{template['title']}'?")
        if st.button("Confirm Delete"):
            user.delete_note_template(template['id'])
            users_collection.update_one(
                {"username": st.session_state.username},
                {"$set": {"preferences": user.preferences}}
            )
            st.success(f"Template '{template['title']}' deleted successfully!")
            time.sleep(2)
            st.rerun()



############################################# User input processing #############################################

def process_user_question(user_question, specialist, mobile=False):
    if user_question:
        if not "collection_name" in st.session_state:
            create_new_session()
        
        # Save the completed tasks before clearing
        completed_tasks = st.session_state.completed_tasks_str
        
        timezone = pytz.timezone("America/Los_Angeles")
        current_datetime = datetime.datetime.now(timezone).strftime("%H:%M:%S")
        
        # Include the completed tasks in the user question
        full_user_question = f"""{current_datetime}
            \n{user_question}
            \n{completed_tasks}
            """
        
        save_user_message(st.session_state.username, "user", full_user_question)
        
        st.session_state.specialist = specialist
        specialist_avatar = specialist_data[specialist]["avatar"]
        st.session_state.specialist_avatar = specialist_avatar
        
        # Update chat history before getting response
        st.session_state.chat_history.append(HumanMessage(full_user_question, avatar=st.session_state.user_photo_url))
        
        if not mobile:
            with st.chat_message("user", avatar=st.session_state.user_photo_url):
                st.markdown(full_user_question)
        
        with st.chat_message("AI", avatar=specialist_avatar):
            assistant_response = get_response(full_user_question, mobile)
            st.session_state.assistant_response = assistant_response
        
        st.session_state.chat_history.append(AIMessage(st.session_state.assistant_response, avatar=specialist_avatar))
        
        save_ai_message(st.session_state.username, "ai", assistant_response, specialist)

        chat_history = chat_history_string()
        parse_json(chat_history)
        
        # Clear completed tasks
        st.session_state.completed_tasks_str = ""
        
        # Debug output
        # print("DEBUG: Session State after processing user question")

def get_response(user_question: str, mobile=False) -> str:
    loading_message = "Waiting for EMMA's response..."
    if mobile:
        loading_message = "EMMA is thinking..."

    with st.spinner(loading_message):
        response_placeholder = st.empty()
        # print(f"DEBUG get_response: specialist: {st.session_state.specialist}")
        if st.session_state.specialist == "Perplexity" or st.session_state.specialist == "Clinical Decision Tools":
            # print(f"DEBUG get_response: Perplixity Specialist: {st.session_state.specialist}")
            response_text = get_perplexity_response(user_question)
        else:
            # Prepare chat history for context
            # print(f"DEBUG get_response: else Specialist: {st.session_state.specialist}")

            chat_context = ""
            for message in st.session_state.chat_history[-20:]:  # Include last 20 messages for context
                if isinstance(message, HumanMessage):
                    chat_context += f"Human: {message.content}\n"
                else:
                    chat_context += f"AI: {message.content}\n"
            
            specialist = st.session_state.specialist
            system_instructions = specialist_data[specialist]["system_instructions"]
            
            # Handle callable system_instructions (including NOTE_WRITER and Patient Educator)
            if callable(system_instructions):
                system_instructions = system_instructions()
            
            # Ensure system_instructions is a string
            if isinstance(system_instructions, list):
                system_instructions = "\n".join(system_instructions)
            elif not isinstance(system_instructions, str):
                system_instructions = str(system_instructions)

            # Only format if it contains placeholders
            if "{" in system_instructions and "}" in system_instructions:
                system_prompt = system_instructions.format(
                    REQUESTED_SECTIONS='ALL',
                    FILL_IN_EXPECTED_FINDINGS='fill in the normal healthy findings and include them in the note accordingly'
                )
            else:
                user_info = f"""
                REFERENCE INFORMATION OF THE USER:
                Date and time of visit: {datetime.datetime.now(pytz.timezone(st.session_state.timezone)).strftime("%Y-%B-%d %I:%M:%S %p")}
                User's name: {st.session_state.name} 
                Specialty: {st.session_state.specialty}
                Work: {st.session_state.hospital_name}
                Contact info: {st.session_state.hospital_contact}
                """
                
                system_prompt = system_instructions + user_info
                # print(f"Get_response System Prompt: {system_prompt}")

            system_message = SystemMessage(content=system_prompt)
            
            user_content = f"Chat History:\n{chat_context}\n\nUser: {user_question}"
            user_message = HumanMessage(content=user_content)
            
            messages = [system_message, user_message]

            # LLM Model Response
            response = anthropic_model.invoke(messages)
            response_text = response.content

        if mobile:
            response_placeholder.write("EMMA has analyzed this Pt encounter. You may update more information for this encounter by hitting record again. To start an additional Pt encounter hit the button below.")
            # response_placeholder.write("To refresh the page, swipe down and release.")
            st.link_button("🔃New Patient Encounter", "https://emmahealth.ai", help="Will create a new session in a new tab", use_container_width=True)
            
            
        else:
            response_placeholder.markdown(response_text)
        
        return response_text

def admin_mode():
    # New power-up check for admins
    if st.session_state.username == "sunny":
        if st.sidebar.button("User Dashboard"):
            admin_dashboard()
        # if st.sidebar.button("List Sessions"):
        #     list_sessions()
            # return  # Exit the function if admin dashboard is accessed
        # if st.sidebar.button("Throw an Error"):
            # raise Exception("This is a test error message")

CSS_SELECTOR = 'section > [data-testid="stAppViewBlockContainer"] > [data-testid="stVerticalBlockBorderWrapper"]'

def css_hack():
    st.markdown(f"""
    <style>
    {CSS_SELECTOR} {{
        max-height: calc(100vh - 260px);
        overflow-y: auto;
        padding: 15px;
        border-radius: 5px;
        overflow-x: hidden;
    }}
    pre code {{
        white-space: pre-wrap !important;
    }}
    </style>
""", unsafe_allow_html=True)

def authenticated_user():
    
    try:
        logging.info("Entering authenticated_user function")
        sentry_sdk.set_user({"email": st.session_state.email})
        css_hack()
        
        # Match user's specialty to a specialist every time
        matched_specialist = match_specialty_to_specialist(st.session_state.specialty)
        # print(f"Matched Specialist: {matched_specialist}")
        
        # Only update if the matched specialist is different from the current one
        if 'specialist' not in st.session_state or st.session_state.default_specialist == "":
            # print("Specialist not in session state or default specialist is empty")
            st.session_state.specialist = matched_specialist
            st.session_state.default_specialist = matched_specialist
            st.session_state.assistant_id = specialist_data[matched_specialist]["assistant_id"]
            st.session_state.specialist_avatar = specialist_data[matched_specialist]["avatar"]
            st.session_state.system_instructions = specialist_data[matched_specialist]["system_instructions"]

        # print(f'Current specialist: {st.session_state.specialist}')
        # print(f'User specialty: {st.session_state.specialty}')
            
        if 'load_session' in st.session_state:
            collection_name = st.session_state.load_session
            load_chat_history(collection_name)
            st.session_state.collection_name = collection_name
            del st.session_state.load_session  # Clear the flag after loading

        if st.session_state.get('show_shared_templates', False):
            manage_custom_templates()
            mark_shared_templates_as_seen()
            st.session_state.show_shared_templates = False

        if st.session_state.differential_diagnosis:
            col1, col2 = st.columns([2, 1])
            with col1:
                with st.container():
                    display_header()
                    display_chat_history()
                    handle_user_input_container() 
            
            with col2:
                
                input_container = st.container()
                input_container.float(float_css_helper(
                    shadow=1,
                    bottom="50px",
                    border="1px #262730",
                    border_radius="10px",
                    height="calc(95vh - 80px)",
                    overflow_y="auto",
                    padding="10px"
                ))
                with input_container:
                    display_pt_headline()
                    st.divider()
                    display_ddx()
                    st.divider()
                    display_follow_up_tasks()
        else:
            display_header()
            display_chat_history()
            handle_user_input_container() 
            
            st.markdown(
                """
                <script>
                setTimeout(function(){
                    var mic = document.querySelector('div[data-testid="stAudioRecorder"]');
                    if(mic) mic.remove();
                }, 1000);
                </script>
                """,
                unsafe_allow_html=True
            )

        process_other_queries() 
        display_sidebar()
        # admin_mode()
        # Periodically archive old sessions
        archive_old_sessions(st.session_state.username)

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        logging.error(f"Unhandled exception in authenticated_user: {str(e)}", exc_info=True)
        sentry_sdk.capture_exception(e)

def handle_feedback(container=None):
    if 'show_feedback' not in st.session_state:
        st.session_state.show_feedback = False
    if 'feedback_text' not in st.session_state:
        st.session_state.feedback_text = ""
    if 'processed_feedback' not in st.session_state:
        st.session_state.processed_feedback = ""
    if 'show_processed_feedback' not in st.session_state:
        st.session_state.show_processed_feedback = False

    if st.button("📝 Give Feedback", key="feedback_button", use_container_width=True, help="Help make EMMA better") or st.session_state.show_feedback:
        st.session_state.show_feedback = True
        with container:
            with st.expander("Feedback", expanded=True):
                st.write("Your feedback is crucial to making EMMA better. Please share your thoughts freely. Don't worry about formatting; EMMA will process your feedback into different categories.")
                
                # Display prompts
                prompts = [
                    "Any problems with Diagnosis, Treatment, or Documentation?",
                    "How easy is it to use EMMA?",
                    "What performance issues have you encountered?",
                    "Which features of EMMA do you find most valuable?",
                    "How has EMMA impacted your efficiency or patient care?",
                    "Do you have any suggestions for improvements?",
                    "Is there anything you would like to see added to EMMA?",
                    "Any cool cases to share?"
                ]
                for prompt in prompts:
                    st.write(f"• {prompt}")

                # Text input
                st.session_state.feedback_text = st.text_area("Type your feedback here...", value=st.session_state.feedback_text, key="feedback_text_area", height=150)
                
                # Voice recording
                col1, col2 = st.columns([3, 1])
                feedback_container = st.container()
                with col1:
                    st.write("Or record your feedback:")
                with col2:
                    audio_text = record_audio(key="feedback_recorder", width=True, container_name=feedback_container)
                    if audio_text:
                        st.session_state.feedback_text += " " + audio_text
                        st.rerun()  # Rerun to update the text area
                
                col3, col4, col5 = st.columns([1, 1, 1])
                container2 = st.container()
                with col3:
                    if st.button("Preview Processed Feedback", key="preview_feedback_button"):
                        if st.session_state.feedback_text:
                            with st.spinner("Processing feedback..."):
                                st.session_state.processed_feedback = process_feedback(st.session_state.feedback_text)
                            st.session_state.show_processed_feedback = True
                            st.rerun()
                        else:
                            st.warning("Please provide some feedback before previewing.")
                
                with col4:
                    if st.button("Submit Feedback", key="submit_feedback_button", type="primary"):
                        if st.session_state.feedback_text:
                            if not st.session_state.processed_feedback:
                                with st.spinner("Processing feedback..."):
                                    st.session_state.processed_feedback = process_feedback(st.session_state.feedback_text)
                            
                            # Save both raw and processed feedback
                            if authenticator.save_feedback(st.session_state.user_id, st.session_state.feedback_text, st.session_state.processed_feedback):
                                with container2:
                                    st.image("thankyou_dog.gif", use_column_width=True)
                                    st.success("Thank you for your feedback! It has been processed and saved.")
                                st.session_state.show_feedback = False
                                st.session_state.feedback_text = ""
                                st.session_state.processed_feedback = ""
                                st.session_state.show_processed_feedback = False
                                time.sleep(3)  # Give user time to see the message
                                st.rerun()
                            else:
                                st.error("There was an error saving your feedback. Please try again.")
                        else:
                            st.warning("Please provide some feedback before submitting.")
                
                with col5:
                    if st.button("Cancel", key="cancel_feedback_button"):
                        st.session_state.show_feedback = False
                        st.session_state.feedback_text = ""
                        st.session_state.processed_feedback = ""
                        st.session_state.show_processed_feedback = False
                        time.sleep(1)  # Give user time to see the message
                        st.rerun()
                
                # Display processed feedback if available
                if st.session_state.show_processed_feedback and st.session_state.processed_feedback:
                    st.write("Processed Feedback:")
                    st.write(st.session_state.processed_feedback)

def process_feedback(text: str) -> str:
    clean_feedback_prompt = """
        Analyze the following user feedback for EMMA (Emergency Medicine Management Assistant) and provide a concise report. 
        Only include information directly addressed in the user feedback. 
        Do not infer or add information not explicitly mentioned. 
        Categorize the analysis into three main themes: Good, Bad, and Action Items. 
        Our main priorities to solve involve items related to usability, diagnosis, treatment, and documentation.

        1. Key Points Summary (1-2 sentences)

        2. Good:
        - Positive feedback
        - are the user's requirements met?
        - Praised features or aspects
        - Performance improvements (if mentioned)
        - Beneficial user experiences

        3. Bad:
        - Any requiremnts not met?
        - Other issues or concerns
        - Underperforming features
        - Comparative disadvantages (if mentioned)

        4. Action Items:
        - Suggestions for improvement. 
        - Actionable solutions to reported issues
        - Feature requests or modifications
        - Areas needing further investigation or feedback

        Additional Guidelines:
        - Include sentiment analysis only if clear sentiment is expressed
        - Mention specific metrics or case studies only if provided in the feedback
        - Use bullet points for clarity and brevity
        - Quantify information when numbers are given in the feedback
        - Omit any sections not directly addressed in the user feedback
        - Do not speculate or expand beyond what is explicitly stated

        User Feedback:
        """
    
    response = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": clean_feedback_prompt + "```" + text + "```" ,
            }
        ],
        model="gpt-4o-mini",  
        temperature=0.0
    )
    
    return response.choices[0].message.content

def document_processing():
    
    st.markdown("---")
    st.subheader("📄Document Processing")
    
    with st.expander("Document Processing"):
        # Document paste area
        doc_text = st.text_area("Paste your document here:", height=200)
        
        # Instructions for the chatbot
        instructions = st.text_area("Instructions for document analysis:", 
                                    value="Please evaluate these documents",
                                    height=50)
        
        if st.button("Process Document"):
            if doc_text:
                # Prepare the message for the chatbot
                analysis_request = f"""
                Documents to analyze:
                {doc_text}
                
                Instructions:
                {instructions}
                """
                
                # Add the analysis request to the chat history
                st.session_state.specialist = NOTE_WRITER
                st.session_state.preferred_note_type = "All Purpose Notes"
                # # print(f'DEBUG DOCUMETN PROCESSING SPECIALIST: {st.session_state.specialist} and preferred_note_type: {st.session_state.preferred_note_type}')
                consult_specialist_and_update_ddx("Analyze Document", analysis_request)
                
                # Get the chatbot's response (you'll need to implement this part based on your chatbot setup)
                # For example:
                # response = get_chatbot_response(analysis_request)
                # st.session_state.messages.append({"role": "assistant", "content": response})
                
                st.success("Document analyzed. Please check the chat for the analysis results.")
                st.rerun()
            else:
                st.warning("Please paste a document to analyze.")

def delete_message(index: int, message_type: str):
    #because this is called in a click handler, we need to catch any errors and send them to sentry
    try:
        if 0 <= index < len(st.session_state.chat_history):
            # Remove from chat history
            deleted_message = st.session_state.chat_history.pop(index)
            
            # Remove from MongoDB
            delete_message_from_mongodb(deleted_message, message_type)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise e
    

def delete_message_from_mongodb(message, message_type: str):
    collection = db[st.session_state.collection_name]
    
    # Delete the message from MongoDB
    result = collection.delete_one({
        "type": message_type,
        "message": message.content,
        "user_id": st.session_state.username
    })
    
    if result.deleted_count == 0:
        st.warning("Message not found in the database. It may have been already deleted.")
############################################# Perplexity Model #############################################

def get_perplexity_response(user_question: str) -> str:
    PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {PERPLEXITY_API_KEY}"
    }

    # Prepare chat history for context
    chat_context = ""
    for message in st.session_state.chat_history[-5:]:  # Include last 5 messages for context
        if isinstance(message, HumanMessage):
            chat_context += f"Human: {message.content}\n"
        else:
            chat_context += f"AI: {message.content}\n"


    user_input = f'<CHAT HISTORY>\n{chat_context}\n</CHAT HISTORY>\n{user_question}'

    payload = {
        "model": "llama-3.1-sonar-large-128k-online",
        "messages": [
            {
                "role": "system",
                "content": st.session_state.system_instructions,
            },
            {
                "role": "user",
                "content": user_input
            }
        ],
        "max_tokens": 0,
        "temperature": 0.5,
        "top_p": 0.9,
        "return_citations": True,
        "return_images": False,
        "return_related_questions": True,
        "top_k": 0,
        "stream": False,
        "presence_penalty": 0,
        "frequency_penalty": 1
    }

    response = requests.post(PERPLEXITY_URL, json=payload, headers=headers)
    data = response.json()
    return data['choices'][0]['message']['content']

def is_mobile():
    headers = _get_websocket_headers()
    user_agent_string = headers.get("User-Agent")
    if user_agent_string:
        user_agent = parse(user_agent_string)
        return user_agent.is_mobile
    return False

def mobile_user():
    text = render_mobile()
    loading_message = "EMMA is creating follow up Questions and Examinations..."
    if text is not None:
        process_user_question(text, st.session_state.specialist, mobile=True)
        with st.spinner(loading_message):
            display_mobile_ddx_follow_up()

############################################# Main Function #############################################

def main():
    
    initialize_session_state()
    
    # Add a small delay to allow cookie to be read
    time.sleep(.3)
    



    # Check if user is already authenticated
    if authenticator.authenticate():
        if is_mobile():
            mobile_user()
        else:
            authenticated_user()

    else:
        if st.session_state.show_registration:
            authenticator.register_page()
        elif st.session_state.show_forgot_username:
            authenticator.forgot_username_page()
        elif st.session_state.show_change_password:
            authenticator.change_password_page()
        else:
            authenticator.login_page()

        
if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise e
