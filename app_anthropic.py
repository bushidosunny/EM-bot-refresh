import streamlit as st
from prompts import *
print("Starting app")

if "page_config_set" not in st.session_state:
    print("About to set page config")
    st.set_page_config(
        page_title="EMMA", page_icon="🤖", initial_sidebar_state="auto", layout="wide", menu_items={
        'Get Help': 'https://www.perplexity.ai/',
        'Report a bug': 'mailto:bushidosunny@gmail.com',
        'About': disclaimer})
    st.session_state.page_config_set = True
    print("Page config set")
import admin
from streamlit_float import float_css_helper
from anthropic import Anthropic
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import os
import io
import time
from dotenv import load_dotenv
# from dataclasses import dataclass, field

from extract_json import *
import json
# from datetime import datetime, timedelta
import datetime
import pytz
from pymongo import MongoClient, ASCENDING, TEXT, DESCENDING, UpdateOne
from pymongo.errors import BulkWriteError, ServerSelectionTimeoutError, OperationFailure, ConfigurationError
from bson import ObjectId
# from streamlit_mic_recorder import mic_recorder
from util.recorder import record_audio
from deepgram import DeepgramClient, PrerecordedOptions
from streamlit.components.v1 import html
from typing import List, Dict, Any, Optional
import logging
import secrets
# import toml
# import yaml
# import bcrypt
# from yaml.loader import SafeLoader
from auth.MongoAuthenticator import *
import extra_streamlit_components as stx
import requests
# # temp
# from streamlit_mic_recorder import mic_recorder
from colorama import Fore, Style, init
# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

def get_note_writer_instructions():
    user = User.from_dict(users_collection.find_one({"username": st.session_state.username}))
    preferred_note_type = user.preferred_note_type if hasattr(user, 'preferred_note_type') else "Emergency Medicine Note"
    return note_type_instructions.get(preferred_note_type, note_writer_system)

specialist_data = {
  EMERGENCY_MEDICINE: {
    "assistant_id": "asst_na7TnRA4wkDbflTYKzo9kmca",
    "caption": "👨‍⚕️EM, Peds EM, ☠️Toxicology, Wilderness",
    "avatar": "https://i.ibb.co/LnrQp8p/Designer-17.jpg",
    "system_instructions": emma_system,
  },
  "Perplexity": {
    "assistant_id": "perplexity_api",
    "caption": "🔍Perplexity AI with web search and citations",
    "avatar": "https://play-lh.googleusercontent.com/6STp0lYx2ctvQ-JZpXA1LeAAZIlq6qN9gpy7swLPlRhmp-hfvZePcBxqwVkqN2BH1g",
    "system_instructions": perplixity_system
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
  "Note Writer": {
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
    "avatar": "https://cdn.pixabay.com/photo/2017/02/15/20/58/ekg-2069872_1280.png",
    "system_instructions": cardiology_clinic_system
  }
  
}

note_type_instructions = {
    EM_NOTE: note_writer_system_em,
    "General Consultation Note": note_writer_system_consult,
    "General Progress Note": note_writer_system_progress,
    "IM Admission Note": note_writer_system_admission,
    "IM Discharge Note": note_writer_system_discharge,
    "IM Progress Note": note_writer_system_IM_progress,
    "Procedure Note": note_writer_system_procedure,
    "Transfer Note": note_writer_system_transfer
}

################################# Initialize Session State #####################################

def initialize_session_state():
    session_state = st.session_state
    if not session_state.get('initialized'):
        session_state.initialized = True
        session_state.count = 0
        session_state.id = secrets.token_hex(8)
        session_state.user_id = None
        session_state.specialty = "Emergency Medicine"
        session_state.authentication_status = None
        session_state.show_registration = False
        session_state.show_forgot_username = False
        session_state.show_change_password = False
        session_state.username = ""
        session_state.user_photo_url = "https://cdn.pixabay.com/photo/2016/12/21/07/36/profession-1922360_1280.png"
        session_state.collection_name = ""
        session_state.name = ""
        session_state.chat_history = []
        session_state.user_question = ""
        session_state.legal_question = ""
        session_state.note_input = ""
        session_state.json_data = {}
        session_state.pt_data = {}
        session_state.differential_diagnosis = []
        session_state.danger_diag_list = {}
        session_state.critical_actions = {}
        session_state.follow_up_steps = {}
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
        session_state.system_instructions = emma_system
        session_state.pt_title = ""
        session_state.patient_cc = ""
        session_state.chief_complaint_two_word = ""
        session_state.clean_chat_history = ""
        session_state.specialist = list(specialist_data.keys())[0]
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
    print(f'CREATE_SESSION_COLLECTION COLLECTION_NAME:{collection_name}')
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
            print(f"Text index created for collection: {collection_name}")
        except Exception as e:
            st.error(f"Error creating text index for collection {collection_name}: {str(e)}")
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
        print(f"Bulk write operation: {result.upserted_count} inserted, {result.modified_count} modified")
    except BulkWriteError as bwe:
        st.warning(f"Bulk write operation partially failed: {bwe.details}")

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
                print(f"New test result inserted for {test_name} with sequence number {new_sequence_number}.")
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
            print(f"New test result inserted for {test_name} with sequence number {sequence_number}.")
    except Exception as e:
        print(f"An error occurred while processing {test_name}: {str(e)}")

@st.cache_data(ttl=60)
def list_user_sessions(username: str):
    collections = db.list_collection_names()
    username = st.session_state.username
    user_sessions = [col for col in collections if col.startswith(f'user_{username}')]
    session_details = []
    
    for session in user_sessions:
        session_id = session.split('_')[-1]
        collection_name = f'user_{username}_session_{session_id}'
        
        pipeline = [
            {"$match": {"type": "ddx"}},
            {"$sort": {"timestamp": -1}},
            {"$limit": 1},
            {"$project": {
                "timestamp": 1,
                "patient_cc": 1,
                "ddx": {"$ifNull": ["$ddx", []]}  # Ensure ddx is always an array
            }},
            {"$project": {
                "timestamp": 1,
                "patient_cc": 1,
                "disease": {"$arrayElemAt": [{"$ifNull": ["$ddx.disease", []]}, 0]}  # Safely get first disease
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
                session_details.append({"collection_name": collection_name, "session_name": session_name})
            else:
                session_details.append({"collection_name": collection_name, "session_name": session_id})
        except Exception as e:
            print(f"Error processing session {session_id}: {str(e)}")
            session_details.append({"collection_name": collection_name, "session_name": session_id})
    
    return session_details

def sort_user_sessions_by_time(sessions):
    def parse_session_date(session):
        try:
            date_str = session['session_name'].split(' - ')[0]
            return datetime.datetime.strptime(date_str, "%Y.%m.%d %H:%M")
        except (ValueError, IndexError):
            return datetime.datetime.min
    return sorted(sessions, key=parse_session_date, reverse=True)

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

#         print(f"Error loading chat history: {e}")

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

        # print(f"Loaded {len(st.session_state.chat_history)} messages and {len(st.session_state.differential_diagnosis)} diagnoses")
    except Exception as e:
        print(f"Error loading chat history: {e}")

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

def button_input(specialist, prompt):
    st.session_state.assistant_id = specialist_data[specialist]["assistant_id"]
    st.session_state.system_instructions = specialist_data[specialist]["system_instructions"]
 
    user_question = prompt
    if user_question:
        st.session_state.specialist = specialist
        print(f'DEBUG BUTTON INPUT SPECIALIST CHOSEN: {specialist}')
        specialist_avatar = specialist_data[st.session_state.specialist]["avatar"]
        st.session_state.specialist_avatar = specialist_avatar
        timezone = pytz.timezone("America/Los_Angeles")
        current_datetime = datetime.datetime.now(timezone).strftime("%H:%M:%S")
        user_question = f"{current_datetime}\n{user_question}\n{st.session_state.completed_tasks_str}"
        st.session_state.user_question_sidebar = user_question

        st.session_state.completed_tasks_str = ''
        st.session_state.critical_actions = []
        st.rerun()

def update_patient_language():
    patient_language = st.text_input("Type patient language if not English", value=st.session_state.patient_language)
    if patient_language != st.session_state.patient_language:
        st.session_state.patient_language = patient_language

def process_other_queries():
    if st.session_state.user_question_sidebar != "" and st.session_state.user_question_sidebar != st.session_state.old_user_question_sidebar:
        specialist_avatar = specialist_data[st.session_state.specialist]["avatar"]
        specialist = st.session_state.specialist
        
        user_question = st.session_state.user_question_sidebar
        with st.chat_message("user", avatar=st.session_state.user_photo_url):
            st.markdown(user_question)

        st.session_state.chat_history.append(HumanMessage(user_question, avatar=st.session_state.user_photo_url))
        save_user_message(st.session_state.username, "user", user_question)

        with st.chat_message("AI", avatar=specialist_avatar):
            assistant_response = get_response(user_question)
            if specialist != "Note Writer":
                save_ai_message(st.session_state.username, specialist, assistant_response, specialist)
            if specialist == "Note Writer":
                save_note_details(st.session_state.username, assistant_response)
                save_ai_message(st.session_state.username, specialist, assistant_response, specialist)

        st.session_state.chat_history.append(AIMessage(assistant_response, avatar=specialist_avatar))
        st.session_state.old_user_question_sidebar = user_question

        chat_history = chat_history_string()
        parse_json(chat_history) 

        # Clear completed tasks
        st.session_state.completed_tasks_str = ""
        st.session_state.specialist = "Emergency Medicine"
        st.rerun()


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
        print("No data was extracted from the chat history.") 
        return
    try:
        data = json.loads(pt_json)
        patient_data = data.get('patient', {})

        # Update session state
        st.session_state.pt_data = patient_data

        # Only update patient_cc if it's not empty
        # new_patient_cc = patient_data.get('chief_complaint_two_word')
        # if new_patient_cc:
        #     st.session_state.patient_cc = new_patient_cc
        
        # Ensure differential_diagnosis, critical_actions, and follow_up_steps are not None
        st.session_state.differential_diagnosis = patient_data.get('differential_diagnosis', [])
        if st.session_state.differential_diagnosis is None:
            st.session_state.differential_diagnosis = []

        st.session_state.critical_actions = patient_data.get('critical_actions', [])
        if st.session_state.critical_actions is None:
            st.session_state.critical_actions = []

        st.session_state.follow_up_steps = patient_data.get('follow_up_steps', [])
        if st.session_state.follow_up_steps is None:
            st.session_state.follow_up_steps = []

        # print(f'DEBUG PARSE_JSON session_state.differential_diagnosis: {st.session_state.differential_diagnosis}')
        # print(f'DEBUG PARSE_JSON st.session_state.critical_actionss: {st.session_state.critical_actions}')
        # print(f'DEBUG PARSE_JSON st.session_state.follow_up_steps: {st.session_state.follow_up_steps}')
        print(f'DEBUG PARSE_JSON st.session_state.patient_cc: {st.session_state.patient_cc}')

        # Only save case details if there's meaningful data
        if any([st.session_state.differential_diagnosis, 
                st.session_state.critical_actions, 
                st.session_state.follow_up_steps]):
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

    except json.JSONDecodeError:
        print("Failed to parse JSON data")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        print(f"Full error details: {repr(e)}")  # This will print more detailed error information

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

# def display_critical_tasks():
#     #print(f'DEBUG SS TATE CRITICAL ACTIONS:{st.session_state.critical_actions}')
#     if st.session_state.critical_actions:
#         st.markdown(f"<h5>❗Critical Actions</h5>", unsafe_allow_html=True)
#         tasks = st.session_state.critical_actions.keys() if isinstance(st.session_state.critical_actions, dict) else st.session_state.critical_actions
        
#         for task in tasks:
#             key = f"critical_{task}"
#             if st.checkbox(f"❗{task}", key=key):
#                 if task not in st.session_state.completed_tasks_str:
#                     st.session_state.completed_tasks_str += f"Completed: {task}. "

def display_critical_tasks():
    if st.session_state.critical_actions:
        st.markdown(f"<h5>❗Critical Actions</h5>", unsafe_allow_html=True)
        for i, task in enumerate(st.session_state.critical_actions):
            key = f"critical_{i}"
            if st.checkbox(f"❗{task}", key=key):
                if task not in st.session_state.completed_tasks_str:
                    st.session_state.completed_tasks_str += f"Completed: {task}. "

def display_follow_up_tasks():
    if st.session_state.follow_up_steps:
        st.markdown(f"<h5>Possible Follow-Up Steps</h5>", unsafe_allow_html=True)
        tasks = st.session_state.follow_up_steps.keys() if isinstance(st.session_state.follow_up_steps, dict) else st.session_state.follow_up_steps
        
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

def display_pt_headline():
    if st.session_state.pt_data != {}:
        try:
            #print(f'DEBUG DISPLAY HEADER ST.SESSION TATE.PT DATA: {st.session_state.pt_data}')
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
            print(f'DEBUG display_pt_headline st.session_state.patient_cc: {st.session_state.patient_cc}')
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
        
        tab1, tab2, tab5 = st.tabs(["Functions", "Specialists","Settings"])
        
        with tab1:
            #display_pt_headline()
            #display_ddx()
            #display_critical_tasks()
            #display_follow_up_tasks()
            #st.divider()
            display_functions_tab()
            
        with tab2:
            display_specialist_tab()
        
        with tab5:
            display_settings_tab()

        # with tab4:
        #     display_sessions_tab()
        # if st.button('🔃New Patient Encounter', type="secondary", use_container_width=True, help=new_session_prompt):
        #     st.session_state.new_session_clicked = True
                    
        # if st.session_state.new_session_clicked:
        #     st.write("Are you sure you want to start a new encounter? This will reset all current data.")
        #     if st.button("Yes, start new encounter", type="primary", use_container_width=True):
        #         new_thread()
        #     if st.button("No, cancel", type="secondary", use_container_width=True):
        #         st.session_state.new_session_clicked = False
        st.divider()
        st.link_button("🔃New Patient Encounter", "https://emmahealth.ai", help="Will create a new session in a new tab", use_container_width=True)
        st.divider()
                
        container = st.container()
        container.float(float_css_helper(bottom="10px", padding= "10px", background_color="#CED6E3", border_radius="10px"))
        with container:
             
            
            c1, c2 = st.columns([1,1])
            feedback_container = st.container()
            with c2:
                handle_feedback(container=feedback_container)
                
            # with c2:
            #     if st.button('🔃New Session', type="secondary", use_container_width=True, help=new_session_prompt):
            #         st.session_state.new_session_clicked = True
                    
            # if st.session_state.new_session_clicked:
            #     st.write("Are you sure you want to start a new encounter? This will reset all current data.")
            #     if st.button("Yes, start new encounter", type="primary", use_container_width=True):
            #         new_thread()
            #     if st.button("No, cancel", type="secondary", use_container_width=True):
            #         st.session_state.new_session_clicked = False
                
                
            c3, c4 = st.columns([1,1])
            with c3:
                st.markdown(f'Welcome {st.session_state.name}!')
            with c4:
                if st.button("Logout", key="logout_button", use_container_width=True):
                    authenticator.logout()
                    st.success("You have been logged out successfully.")
                    time.sleep(1)  # Give user time to see the message
                    st.rerun()



def display_functions_tab():
    # st.subheader('Process Management')
    # col1, col2 = st.columns(2)
    # with col1:
    #     if st.button("🛌Disposition Analysis", use_container_width=True):
    #         st.session_state.specialist = "Emergency Medicine"
    #         consult_specialist_and_update_ddx("Disposition Analysis", disposition_analysis)
    # with col2:
    #     if st.button("💉Which Procedure", use_container_width=True):
    #         consult_specialist_and_update_ddx("Which Procedure", procedure_checklist)
    display_sessions_tab()
    st.divider()
    st.subheader('🧠Diagnostic Tools')
    if st.button("🔍Search Diagnostic CDTs", use_container_width=True, help="Identify, apply, and interpret relevant Clinical Decision Tools"):
        st.session_state.specialist = "Perplexity"
        consult_specialist_and_update_ddx("Search for a Diagnosis", search_CDTs)
    col1, col2 = st.columns(2)
    with col1:
        # if st.button("➡️Next Step Recommendation", use_container_width=True):
        #     st.session_state.specialist = "Emergency Medicine"
        #     consult_specialist_and_update_ddx("Next Step Recommendation", next_step)
        if st.button("🤔Challenge DDX", use_container_width=True, help="Use to broaden and critique the current DDX"):
            st.session_state.specialist = "General Medicine"
            consult_specialist_and_update_ddx("Challenge the DDX", challenge_ddx)
            st.session_state.specialist = "Emergency Medicine"
    with col2:
        # if st.button('🛠️Apply Clinical Decision Tools', use_container_width=True):
        #     st.session_state.specialist = "Clinical Decision Tools"
        #     consult_specialist_and_update_ddx("Apply Clinical Decision Tools", apply_decision_tool)
        #     st.session_state.specialist = "Emergency Medicine"
        if st.button("🧠Refine DDX", use_container_width=True, help="Use Bayesian Reasoning to refine and narrow the DDX"):
            st.session_state.specialist = "Bayesian Reasoner"
            consult_specialist_and_update_ddx("Critical Thinking w Bayesian Reasoning", apply_bayesian_reasoning)
            st.session_state.specialist = "Emergency Medicine"
    st.subheader('💉Treatment Tools')
    if st.button("🔍Search Treatment CDTs/Guidelines", use_container_width=True, help="Applies relevant CDTs, guidelines, or algorithms to guide treatment decisions and management."):
        st.session_state.specialist = "Perplexity"
        consult_specialist_and_update_ddx("Treatment Plan", treatment_plan)
        st.session_state.specialist = "Emergency Medicine"
    
    st.divider()
    st.subheader('📝Clinical Notes')
    col1, col2 = st.columns(2)
    with col1:
        if st.button('Complete Note', use_container_width=True, help="Writes a full medical note on this patient"):
            st.session_state.specialist = "Note Writer"
            consult_specialist_and_update_ddx("Full Medical Note", "Write a note on this patient")
            st.session_state.specialist = "Emergency Medicine"
        if st.button('HPI only', use_container_width=True, help="Writes only the HPI"):
            st.session_state.specialist = "Note Writer"
            consult_specialist_and_update_ddx("HPI only", create_hpi)
            st.session_state.specialist = "Emergency Medicine"
       
    with col2:
        if st.button('Focused Note', use_container_width=True, help="HPI, ROS, PE, A/P, then paste EMR smart data (meds, labs, imaging, etc)"):
            st.session_state.specialist = "Note Writer"
            consult_specialist_and_update_ddx("Full Note except EMR results", create_full_note_except_results)
            st.session_state.specialist = "Emergency Medicine"

        if st.button('A&P only', use_container_width=True, help="Writes only the Assessment and Plan"):
            st.session_state.specialist = "Note Writer"
            consult_specialist_and_update_ddx("A&P only", create_ap)
            st.session_state.specialist = "Emergency Medicine"
    st.subheader('📝Notes for Patients')
    update_patient_language()
    col1, col2 = st.columns(2)
    with col1:

        if st.button("🙍Education Note", use_container_width=True, help="Writes a personalized patient education note"):
            st.session_state.specialist = "Patient Educator"
            consult_specialist_and_update_ddx("Patient Education Note", f"Write a patient education note for this patient in {st.session_state.patient_language}")
            st.session_state.specialist = "Emergency Medicine"
    with col2:
        if st.button('💪Physical Therapy ', use_container_width=True, help="Writes a personalized Physical Therapy plan"):
            st.session_state.specialist = "Musculoskeletal Systems"
            consult_specialist_and_update_ddx("Physical Therapy Plan", pt_plan)
            st.session_state.specialist = "Emergency Medicine"


    
       

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
    st.header("User Settings")
    st.markdown("[View EMMA Help Guide](https://veil-cry-a60.notion.site/EMMA-Help-Page-e681bf1c061041719b6666376cc88386)", unsafe_allow_html=True)
    # Load current user settings
    user = User.from_dict(users_collection.find_one({"username": st.session_state.username}))

    # Default Specialty
    current_specialty = user.specialty if user.specialty else "Emergency Medicine"
    new_specialty = st.selectbox("Default Specialty", 
                                 options=SPECIALTIES, 
                                 index=SPECIALTIES.index(current_specialty))

    # Preferred Note Type
    note_types = list(note_type_instructions.keys())  # Use the keys from our note_type_instructions dictionary
    
    current_note_type = user.preferred_note_type if hasattr(user, 'preferred_note_type') else "Emergency Medicine Note"
    new_note_type = st.selectbox("Preferred Note Type", 
                                 options=note_types, 
                                 index=note_types.index(current_note_type) if current_note_type in note_types else 0)

    # Other settings can be added here as needed

    if st.button("Save Settings"):
        # Update user object
        user.specialty = new_specialty
        user.preferred_note_type = new_note_type

        # Update other settings...
        # Update session state
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
    for message in st.session_state.chat_history:
        if isinstance(message, HumanMessage):
            with st.chat_message("user", avatar=st.session_state.user_photo_url):                
                st.markdown(message.content, unsafe_allow_html=True)
        else:
            with st.chat_message("AI", avatar=message.avatar):
                st.markdown(message.content, unsafe_allow_html=True)

def display_sessions_tab():
    user_id = st.session_state.user_id  # Use Google ID instead of username
    # if st.button("Load Sessions"):
    user_sessions = list_user_sessions(user_id)
    if user_sessions:
        sorted_sessions = sort_user_sessions_by_time(user_sessions)
        session_options = {session['session_name']: session['collection_name'] for session in sorted_sessions}
        
        session_name = st.selectbox("Select a recent session to load:", 
                    options=["Select a session..."] + list(session_options.keys()),
                    index=0,
                    key="session_selectbox")
        
        # selected_session = st_searchbox(
        #     search_sessions_for_searchbox,
        #     key="session_searchbox",
        #     label="Search sessions",
        #     placeholder="Type to search for sessions...",
        #     default_use_searchterm=False,
        #     rerun_on_update=False
        # )

        # if selected_session:
        #     session_name = load_session_from_search(selected_session)

        
        if session_name != "Select a session...":
            if session_name in session_options:
                collection_name = session_options[session_name]
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Load Selected Patient Encounter", type='primary'):
                        st.session_state.load_session = collection_name
                        st.session_state.show_load_success = True
                        # st.success(f"Click 'Refresh' to load the chat history.")
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
                            html("""
                                <script>
                                    window.parent.location.reload();
                                </script>
                            """)
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
                print(f'DEBUG DELETE SESSION DATA COLLECTION NAME: {collection_name}')
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
    if st.button("📝 Give Feedback", use_container_width=True, help="Help make EMMA better"):
        st.session_state.show_feedback = True



############################################# User input processing #############################################
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

def process_user_question(user_question, specialist):
    if user_question:
        if not st.session_state.collection_name:
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
        
        with st.chat_message("user", avatar=st.session_state.user_photo_url):
            st.markdown(full_user_question)
        
        with st.chat_message("AI", avatar=specialist_avatar):
            assistant_response = get_response(full_user_question)
            st.session_state.assistant_response = assistant_response
        
        st.session_state.chat_history.append(AIMessage(st.session_state.assistant_response, avatar=specialist_avatar))
        
        save_ai_message(st.session_state.username, "ai", assistant_response, specialist)

        chat_history = chat_history_string()
        parse_json(chat_history)
        
        # Clear completed tasks
        st.session_state.completed_tasks_str = ""
        
        # Debug output
        print("DEBUG: Session State after processing user question")

def get_response(user_question: str) -> str:
    with st.spinner("Waiting for EMMA's response..."):
        response_placeholder = st.empty()
        
        if st.session_state.specialist == "Perplexity":
            response_text = get_perplexity_response(user_question)
        else:
            # Prepare chat history for context
            chat_context = ""
            for message in st.session_state.chat_history[-20:]:  # Include last 20 messages for context
                if isinstance(message, HumanMessage):
                    chat_context += f"Human: {message.content}\n"
                else:
                    chat_context += f"AI: {message.content}\n"
            
            specialist = st.session_state.specialist
            if specialist == "Note Writer":
                system_instructions = specialist_data[specialist]["system_instructions"]()
            else:
                system_instructions = specialist_data[specialist]["system_instructions"]

            if isinstance(system_instructions, list):
                system_instructions = "\n".join(system_instructions)

            system_prompt = system_instructions.format(
                REQUESTED_SECTIONS='ALL',
                FILL_IN_EXPECTED_FINDINGS='fill in the normal healthy findings and include them in the note accordingly'
            )
            system_message = SystemMessage(content=system_prompt)
            
            user_content = f"Chat History:\n{chat_context}\n\nUser: {user_question}"
            user_message = HumanMessage(content=user_content)
            
            messages = [system_message, user_message]

            # LLM Model Response
            response = anthropic_model.invoke(messages)
            response_text = response.content

        response_placeholder.markdown(response_text)
        
        return response_text

def admin_mode():
    # New power-up check for admins
    if st.session_state.username == "sunny":
        if st.sidebar.button("Enter Admin Mode"):
            admin.admin_dashboard()
            return  # Exit the function if admin dashboard is accessed

def authenticated_user():
    
    try:
        logging.info("Entering authenticated_user function")

        
            
        if 'load_session' in st.session_state:
            collection_name = st.session_state.load_session
            load_chat_history(collection_name)
            st.session_state.collection_name = collection_name
            del st.session_state.load_session  # Clear the flag after loading


        if st.session_state.differential_diagnosis:
            col1, col2 = st.columns([2, 1])
            with col1:
                with st.container():
                    # display_header()
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
                    display_critical_tasks()
                    st.divider()
                    display_follow_up_tasks()
        else:
            # display_header()
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
        admin_mode()
        # Periodically archive old sessions
        archive_old_sessions(st.session_state.username)

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        logging.error(f"Unhandled exception in authenticated_user: {str(e)}", exc_info=True)

# def handle_feedback():
#     if 'show_feedback' not in st.session_state:
#         st.session_state.show_feedback = False
#     if 'feedback_text' not in st.session_state:
#         st.session_state.feedback_text = ""

#     if st.sidebar.button("📝 Give Feedback", key="feedback_button") or st.session_state.show_feedback:
#         st.session_state.show_feedback = True
#         with st.sidebar.expander("Feedback", expanded=True):
#             st.write("Your feedback is crucial to making EMMA better. Please share your thoughts freely. AI will process your thoughts into different catagories:")
            
#             # Display prompts
#             prompts = [
#                 "How easy is it to use EMMA?",
#                 "What performance issues have you encountered?",
#                 "Which features of EMMA do you find most valuable?",
#                 "How has EMMA impacted your efficiency or patient care?",
#                 "Do you have any suggestions for improvements?"
#             ]
#             for prompt in prompts:
#                 st.write(f"• {prompt}")
            
            
#             # Text input
#             st.session_state.feedback_text = st.text_area("Type/Record your feedback here...", value=st.session_state.feedback_text, key="feedback_text_area", height=150)
            
#             # Voice recording
#             col1, col2 = st.columns([3, 1])
#             with col1:
#                 st.write("Or record your feedback:")
#             with col2:
#                 audio_text = record_audio(key="feedback_recorder", width=True)
#                 if audio_text:
#                     st.session_state.feedback_text += " " + audio_text
#                     st.rerun()  # Rerun to update the text area
            
#             col3, col4 = st.columns([1, 1])
#             with col3:
#                 if st.button("Submit Feedback", key="submit_feedback_button", type="primary"):
#                     if st.session_state.feedback_text:
#                         # Process feedback using AI
#                         processed_feedback = process_feedback(st.session_state.feedback_text)
                        
#                         # Save both raw and processed feedback
#                         if authenticator.save_feedback(st.session_state.user_id, st.session_state.feedback_text, processed_feedback):
#                             st.success("Thank you for your feedback! It has been processed and saved.")
#                             st.session_state.show_feedback = False
#                             st.session_state.feedback_text = ""
#                             time.sleep(1)  # Give user time to see the message
#                             st.rerun()
#                         else:
#                             st.error("There was an error saving your feedback. Please try again.")
#                     else:
#                         st.warning("Please provide some feedback before submitting.")
            
#             with col4:
#                 if st.button("Cancel", key="cancel_feedback_button"):
#                     st.session_state.show_feedback = False
#                     st.session_state.feedback_text = ""
#                     time.sleep(1)  # Give user time to see the message
#                     st.rerun()

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
                    "How easy is it to use EMMA?",
                    "What performance issues have you encountered?",
                    "Which features of EMMA do you find most valuable?",
                    "How has EMMA impacted your efficiency or patient care?",
                    "Do you have any suggestions for improvements?",
                    "Any cool cases?"
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
        Analyze the following user feedback for EMMA (Emergency Medicine Management Assistant) and provide a concise report. Only include information directly addressed in the user feedback. Do not infer or add information not explicitly mentioned. Categorize the analysis into three main themes: Good, Bad, and Action Items.

        1. Key Points Summary (1-2 sentences)

        2. Good:
        - Positive feedback
        - Praised features or aspects
        - Performance improvements (if mentioned)
        - Beneficial user experiences

        3. Bad:
        - Main issues or concerns
        - Negative user experiences
        - Underperforming features
        - Comparative disadvantages (if mentioned)

        4. Action Items:
        - Suggestions for improvement
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

############################################# Main Function #############################################

def main():
    
    initialize_session_state()
    
    # Add a small delay to allow cookie to be read
    time.sleep(.3)

    # Check if user is already authenticated
    if authenticator.authenticate():
        
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
    main()
