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
from extract_json import *
import json
from datetime import datetime, timedelta
import pytz
from pymongo import MongoClient, ASCENDING, TEXT, DESCENDING, UpdateOne
from pymongo.errors import BulkWriteError, ServerSelectionTimeoutError, OperationFailure, ConfigurationError#,DuplicateKeyError, BulkWriteError, InvalidName, 
from bson import ObjectId #, Regex
#from streamlit_searchbox import st_searchbox
from streamlit_mic_recorder import mic_recorder
from deepgram import DeepgramClient, PrerecordedOptions
from streamlit.components.v1 import html
from typing import List, Dict, Any, Optional, Tuple
import logging
import secrets
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from urllib.parse import urljoin
import toml
from streamlit_cookies_controller import CookieController

st.set_page_config(page_title="EMMA", page_icon="🤖", initial_sidebar_state="collapsed", layout="wide")


load_dotenv()
controller = CookieController()
# Constants
DB_NAME = 'emma-dev'
SCOPES = ['https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile', 'openid']
SECRET_KEY = secrets.token_hex(32)

if os.path.exists('/.streamlit/secrets.toml'):
    with open('/.streamlit/secrets.toml', 'r') as f:
        config = toml.load(f)
    # Use the config dictionary to set up your application
    DEEPGRAM_API_KEY = config['DEEPGRAM_API_KEY']
    OPENAI_API_KEY = config['OPENAI_API_KEY']
    ANTHROPIC_API_KEY = config['ANTHROPIC_API_KEY']
    MONGODB_URI = config['MONGODB_ATLAS_URI']
    CLIENT_SECRET_JSON = config['CLIENT_SECRET_JSON']['web']
    ENVIRONMENT = config['ENVIRONMENT']
else:
    # Run as usual, using environment variables or other configuration methods
    DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    MONGODB_URI = os.getenv('MONGODB_ATLAS_URI')
    CLIENT_SECRET_JSON = json.loads(os.getenv('CLIENT_SECRET_JSON'))
    ENVIRONMENT = os.getenv('ENVIRONMENT')

# Initialize Anthropic client
anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)

# Initialize MongoDB connection
@st.cache_resource
def init_mongodb_connection():
    return MongoClient(MONGODB_URI, maxPoolSize=1, connect=False)

try:
    client = init_mongodb_connection()
    db = client[DB_NAME]
    users_collection = db['users']
    sessions_collection = db['sessions']
    custom_buttons_collection = db['custom_buttons']
    layouts_collection = db['layouts']
    themes_collection = db['themes']
    shared_templates_collection = db['shared_templates']
    shared_buttons_collection = db['shared_buttons']
    shared_layouts_collection = db['shared_layouts']
    client.admin.command('ping')
    #print("Successfully connected to MongoDB")
    
except (ServerSelectionTimeoutError, OperationFailure, ConfigurationError) as err:
    st.error(f"Error connecting to MongoDB Atlas: {err}")
    st.stop()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class User:
    def __init__(self, google_id: str, email: str, name: str, family_name: str, picture: Optional[str] = None, _id: Optional[ObjectId] = None):
        self._id = _id or ObjectId()
        self.google_id = google_id
        self.email = email
        self.name = name
        self.family_name = family_name if family_name is not None else ""
        self.picture = picture
        self.created_at = datetime.now()
        self.last_login = datetime.now()
        self.login_count = 0
        self.last_active = datetime.now()
        self.total_session_time = 0
        self.preferences = {"note_templates": []}
        self.recordings_count = 0
        self.transcriptions_count = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self._id,
            "google_id": self.google_id,
            "email": self.email,
            "name": self.name,
            "family_name": self.family_name,
            "picture": self.picture,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "login_count": self.login_count,
            "last_active": self.last_active,
            "total_session_time": self.total_session_time,
            "preferences": self.preferences,
            "recordings_count": self.recordings_count,
            "transcriptions_count": self.transcriptions_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        user = cls(
            google_id=data["google_id"],
            email=data["email"],
            name=data["name"],
            family_name=data["family_name"],
            picture=data.get("picture"),
            _id=data.get("_id")
        )
        user.created_at = data.get("created_at", user.created_at)
        user.last_login = data.get("last_login", user.last_login)
        user.login_count = data.get("login_count", 0)
        user.last_active = data.get("last_active", user.last_active)
        user.total_session_time = data.get("total_session_time", 0)
        user.preferences = data.get("preferences", {"note_templates": []})
        user.recordings_count = data.get("recordings_count", 0)
        user.transcriptions_count = data.get("transcriptions_count", 0)
        return user

    def update_login(self) -> None:
        self.last_login = datetime.now()
        self.login_count += 1
        print(f'DEBUG USER.UPDATE_LOGIN: {self.login_count}')

    def update_activity(self) -> None:
        self.last_active = datetime.now()

    def add_session_time(self, duration: int) -> None:
        self.total_session_time += duration

    def increment_recordings(self) -> None:
        self.recordings_count += 1

    def increment_transcriptions(self) -> None:
        self.transcriptions_count += 1

    def add_note_template(self, title: str, template_type: str, content: str) -> None:
        template = {
            "id": str(ObjectId()),
            "title": title,
            "type": template_type,
            "content": content
        }
        self.preferences["note_templates"].append(template)

    def get_note_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        return next((t for t in self.preferences["note_templates"] if t["id"] == template_id), None)

    def get_note_templates(self) -> List[Dict[str, Any]]:
        return self.preferences.get("note_templates", [])

    def update_note_template(self, template_id: str, title: Optional[str] = None, template_type: Optional[str] = None, content: Optional[str] = None) -> None:
        template = self.get_note_template(template_id)
        if template:
            if title:
                template["title"] = title
            if template_type:
                template["type"] = template_type
            if content:
                template["content"] = content

    def delete_note_template(self, template_id: str) -> None:
        self.preferences["note_templates"] = [t for t in self.preferences["note_templates"] if t["id"] != template_id]

class SessionState:
    def __init__(self):
        self.id = secrets.token_hex(8)
        self._oauth_state = None
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
        self.user_photo_url = ""
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
        self.system_instructions = emma_system
        self.pt_title = ""
        self.patient_cc = ""
        self.clean_chat_history = ""
        self.specialist = list(specialist_data.keys())[0]
        self.assistant_id = specialist_data[self.specialist]["assistant_id"]
        self.specialist_avatar = specialist_data[self.specialist]["avatar"]
        self.session_id = None
        self.auth_state = 'initial'
        self.auth_completed = False
        
    @property
    def oauth_state(self):
        if self._oauth_state is None:
            self._oauth_state = secrets.token_urlsafe(16)
        return self._oauth_state

    @oauth_state.setter
    def oauth_state(self, value):
        self._oauth_state = value
        
    def __repr__(self):
        return f"<SessionState id={self.id}>"
    
specialist_data = {
  "Emergency Medicine": {
    "assistant_id": "asst_na7TnRA4wkDbflTYKzo9kmca",
    "caption": "👨‍⚕️EM, Peds EM, ☠️Toxicology, Wilderness",
    "avatar": "https://i.ibb.co/LnrQp8p/Designer-17.jpg",
    "system_instructions": emma_system
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
    "caption": "Cardiologis in Clinic - Beta testing",
    "avatar": "https://cdn.pixabay.com/photo/2017/02/15/20/58/ekg-2069872_1280.png",
    "system_instructions": emma_doctor_system
  }
  
}


###################### GOOGLE OAUTH ##############################################################

def google_login() -> None:
    if os.getenv('ENVIRONMENT') == 'production':
        REDIRECT_URI = 'https://emmahealth.ai/'
    else:
        REDIRECT_URI = 'http://localhost:8501/'
    

    flow = Flow.from_client_config(
        client_config=CLIENT_SECRET_JSON,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    # Generate and store the state
    oauth_state = st.session_state.session_state.oauth_state
    controller.set('oauth_state', oauth_state)

    authorization_url, _ = flow.authorization_url(
        prompt='consent',
        access_type='offline',
        include_granted_scopes='true',
        state=oauth_state
    )
    # Log the state for debugging
    logging.info(f"Generated OAuth state: {st.session_state.session_state.oauth_state}")

    html = f"""
    <style>
        body {{
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            background-color: #f0f2f5;
            margin: 0;
        }}
        .container {{
            text-align: center;
            font-family: Arial, sans-serif;
        }}
        .title {{
            font-size: 2.5em;
            margin-bottom: 20px;
        }}
        .subtitle {{
            font-size: 1.2em;
            margin-bottom: 40px;
        }}
        .google-btn {{
            display: inline-block;
            width: 191px;
            height: 46px;
            background-image: url('https://developers.google.com/static/identity/images/branding_guideline_sample_lt_rd_lg.svg');
            background-repeat: no-repeat;
            background-size: 191px 46px;
            border: none;
            cursor: pointer;
        }}
        .google-btn:hover {{
            box-shadow: 0 0 8px 4px rgba(4, 182, 234, 0.3);
            border-radius: 20px;
            background-image: url('https://developers.google.com/static/identity/images/branding_guideline_sample_lt_rd_lg.svg');
            
        }}
        .google-btn:active {{
            background-image: url('https://developers.google.com/static/identity/images/branding_guideline_sample_lt_rd_lg.svg');
        }}
    </style>
    <div class="container">
        <img src="https://i.ibb.co/LnrQp8p/Designer-17.jpg" alt="Avatar" style="width:200px;height:200px;border-radius:20%;">
        <div class="title">Welcome to EMMA</div>
        <div class="subtitle">Your Emergency Medicine main assistant</div>
        <a href="{authorization_url}" target="_self">
            <div class="google-btn"></div>
        </a>
    </div>
    """
    # Display the button
    st.markdown(html, unsafe_allow_html=True)
    
        
def google_callback() -> Optional[User]:
    logging.info("Google callback initiated")
    logging.info(f"Query params: {st.query_params}")

    stored_state_session = st.session_state.session_state.oauth_state
    stored_state_cookie = controller.get('oauth_state')

    if 'code' not in st.query_params or 'state' not in st.query_params:
        logging.error("Authorization code or state not found in query parameters")
        st.error("Authorization failed. Please try logging in again.")
        return None

    received_state = st.query_params['state']

    # Check against both session state and cookie
    if received_state != stored_state_session and received_state != stored_state_cookie:
        logging.error(f"State mismatch. Received: {received_state}, Stored (session): {stored_state_session}, Stored (cookie): {stored_state_cookie}")
        st.error("Authentication failed due to state mismatch. Please try again.")
        return None

    # Clear the stored state
    st.session_state.session_state.oauth_state = None
    controller.remove('oauth_state')

    if os.getenv('ENVIRONMENT') == 'production':
        REDIRECT_URI = 'https://emmahealth.ai/'
    else:
        REDIRECT_URI = 'http://localhost:8501/'
    
    logging.info(f"Callback initiated. REDIRECT_URI: {REDIRECT_URI}")
    
    if 'code' not in st.query_params:
        logging.error("Authorization code not found in query parameters")
        st.error("Authorization code not found. Please try logging in again.")
        return None

    try:
        logging.info("Initializing OAuth flow")
        flow = Flow.from_client_config(
            CLIENT_SECRET_JSON,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        auth_code = st.query_params['code']
        logging.info(f"Fetching token with auth code: {auth_code[:10]}...")  # Log first 10 chars for security
        
        flow.fetch_token(code=auth_code)
        logging.info("Token fetched successfully")
        
        credentials = flow.credentials
        logging.info("Credentials obtained")

        user_info_service = build('oauth2', 'v2', credentials=credentials, cache_discovery=False)
        logging.info("User info service built")
        
        google_user_info = user_info_service.userinfo().get().execute()
        logging.info("User info retrieved from Google")
        
        user = get_or_create_user(google_user_info)
        logging.info(f"User retrieved/created: {user.email}")
        logging.info(f"User retrieved/created: {user.picture}")
        
        session_token, expiration = create_session(str(user._id))
        logging.info("Session created")
        
        # controller = CookieController()
        controller.set('session_token', session_token)
        controller.set('session_expiry', expiration.isoformat())
        logging.info("Cookies set")
        
        st.session_state['user'] = user
        
        del st.query_params['code']
        logging.info("Query params cleaned")

        if user:
            # Clear query parameters after successful authentication
            st.query_params.clear()
        
        return user
    except Exception as e:
        logging.error(f"Error during token fetch: {str(e)}", exc_info=True)
        st.error("An error occurred during authentication. Please try again.")
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        return None

def init_db() -> None:
    users_collection.create_index([("google_id", ASCENDING)], unique=True)
    users_collection.create_index([("email", ASCENDING)], unique=True)

def get_or_create_user(google_user_info: Dict[str, Any]) -> User:
    existing_user = users_collection.find_one({"google_id": google_user_info['id']})
    print(f'DEBUG get_or_create_user -------existing_user: {existing_user}')
    if existing_user:
        user = User.from_dict(existing_user)
        user.update_login()
        user.picture = google_user_info.get('picture')
        if "note_templates" not in user.preferences:
            user.preferences["note_templates"] = []
        users_collection.update_one(
            {"_id": user._id},
            {"$set": {
                "last_login": user.last_login,
                "login_count": user.login_count,
                "preferences": user.preferences,
                "picture": user.picture,
                "family_name": google_user_info.get('family_name') or ''
            }}
        )
    else:
        user = User(
            google_id=google_user_info['id'],
            email=google_user_info['email'],
            name=google_user_info['name'],
            family_name=google_user_info.get('family_name') or '',
            picture=google_user_info.get('picture')
        )
        user.update_login()
        result = users_collection.insert_one(user.to_dict())
        user._id = result.inserted_id
    
    # Update session state with user information
    st.session_state.session_state.user = user
    st.session_state.session_state.user_id = user.google_id
    st.session_state.session_state.username = user.name
    st.session_state.session_state.family_name = user.family_name
    st.session_state.session_state.user_photo_url = user.picture
    
    return user


def save_user(user: User) -> None:
    user_dict = user.to_dict()
    print(f'DEBUT SAVE')
    if '_id' in user_dict:
        del user_dict['_id']
    users_collection.update_one(
        {"google_id": user.google_id},
        {"$set": user_dict},
        upsert=True
    )


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

def create_session(user_id: str) -> tuple[str, datetime]:
    session_token = secrets.token_urlsafe(32)
    expiration = datetime.utcnow() + timedelta(days=1)
    sessions_collection.insert_one({
        "token": session_token,
        "user_id": user_id,
        "expires": expiration
    })
    return session_token, expiration



def get_current_user() -> Optional[User]:
    session_token = st.session_state.get('session_token')
    if session_token:
        return get_user_from_session(session_token)
    return None

def clear_session(session_token: str) -> None:
    sessions_collection.delete_one({"token": session_token})

def update_user_session_time(user: User, duration: timedelta) -> None:
    user.add_session_time(duration)
    users_collection.update_one(
        {"_id": user._id},
        {"$set": {"total_session_time": user.total_session_time}}
    )



########################################################################################################


def initialize_session_state():
    
    if "session_state" not in st.session_state:
        st.session_state.session_state = SessionState()
        print(f'DEEBUG INITALIZE SESSIONT STATE SESSIONSTATE: {st.session_state.session_state}')


def create_new_session():
    user_id = st.session_state.session_state.user_id  # Use Google ID instead of username
    session_id = ObjectId()
    st.session_state.session_state.session_id = str(session_id)
    collection_name = f'user_{user_id}_session_{session_id}'
    print(f'CREATE_SESSION_COLLECTION COLLECTION_NAME:{collection_name}')
    st.session_state.session_state.collection_name = collection_name
    
    with client.start_session() as session:
        with session.start_transaction():
            if collection_name not in db.list_collection_names():
                db.create_collection(collection_name)
                db[collection_name].create_index([("timestamp", ASCENDING), ("test_name", ASCENDING)], unique=True)
                initialize_text_indexes(collection_name)
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
    if not st.session_state.session_state.collection_name:
        create_new_session()
    
    collection = db[st.session_state.session_state.collection_name]
    bulk_operations = []
    
    for message in messages:
        chat_document = {
            "type": message['type'],
            "user_id": user_id,
            "sender": message['sender'],
            "message": message['message'],
            "timestamp": datetime.now(),
            "patient_cc": st.session_state.session_state.patient_cc
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
    # print(f'DEBUG SAVE CASE DETAILS -------SESSION STATE CHAT HISTORY: {st.session_state.session_state.chat_history}')
    
    # Convert chat history to serializable format
    serializable_history = []
    for message in st.session_state.session_state.chat_history:
        if isinstance(message, (HumanMessage, AIMessage)):
            serializable_history.append({
                'type': message.__class__.__name__,
                'content': message.content,
                'avatar': message.avatar
            })
    
    # print(f'DEBUG SAVE CASE DETAILS: ---------- serializable history: {serializable_history}')
    document = {
        "type": doc_type,
        "user_id": user_id,
        "ddx": st.session_state.session_state.differential_diagnosis,
        "content": content,
        "session_state_chat_history": serializable_history,
        "patient_cc": st.session_state.session_state.patient_cc,
        "timestamp": datetime.now(),
    }
    query = {
        "type": doc_type,
        "user_id": user_id,
    }
    update = {"$set": document}
    # print(f'DEBUG SAVE CASE DETAILS -------SESSION STATE CHAT HISTORY: {datetime.now()}')
    try:
        result = db[st.session_state.session_state.collection_name].update_one(query, update, upsert=True)
        if result.matched_count > 0:
            print(f"Existing case doc: {doc_type} updated successfully.")
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
        "specialist": st.session_state.session_state.specialist,
        "message": message,
        "timestamp": datetime.now(),
    }
    db[st.session_state.session_state.collection_name].insert_one(chat_document)

def conditional_upsert_test_result(user_id, test_name, result, sequence_number):
    collection = db[st.session_state.session_state.collection_name]
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
                    "timestamp": datetime.now()
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
                "timestamp": datetime.now()
            }
            collection.insert_one(new_doc)
            print(f"New test result inserted for {test_name} with sequence number {sequence_number}.")
    except Exception as e:
        print(f"An error occurred while processing {test_name}: {str(e)}")

def get_user_from_session(session_token: str) -> Optional[User]:
    session = sessions_collection.find_one({
        "token": session_token,
        "expires": {"$gt": datetime.utcnow()}
    })
    if session:
        user_data = users_collection.find_one({"_id": ObjectId(session["user_id"])})
        if user_data:
            return User.from_dict(user_data)
    return None

def update_session_state_with_user(user: User):
    st.session_state.session_state.user = user
    st.session_state.session_state.user_id = user.google_id
    st.session_state.session_state.username = user.name
    st.session_state.session_state.family_name = user.family_name
    st.session_state.session_state.user_photo_url = user.picture

def clear_session(session_token: str) -> None:
    sessions_collection.delete_one({"token": session_token})

@st.cache_data(ttl=60)
def list_user_sessions(user_id: str):
    collections = db.list_collection_names()
    user_sessions = [col for col in collections if col.startswith(f'user_{user_id}')]
    session_details = []
    
    for session in user_sessions:
        session_id = session.split('_')[-1]
        collection_name = f'user_{user_id}_session_{session_id}'
        
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
            return datetime.strptime(date_str, "%Y.%m.%d %H:%M")
        except (ValueError, IndexError):
            return datetime.min
    return sorted(sessions, key=parse_session_date, reverse=True)

@st.cache_data(ttl=60)
def load_session_data_from_db(collection_name):
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

def load_chat_history(collection_name):
    try:
        # Check if we've already loaded the chat history
        st.session_state.session_state.chat_history = []
        st.session_state.session_state.differential_diagnosis = []

        result = db[collection_name].find_one({"type": "chat_history"})
        if result and 'session_state_chat_history' in result:
            serialized_history = result['session_state_chat_history']
            
            # Check if serialized_history is already a list
            if isinstance(serialized_history, list):
                print("Chat history is already a list, no need to parse JSON")
            else:
                try:
                    # If it's a string, try to parse it as JSON
                    serialized_history = json.loads(serialized_history)
                except json.JSONDecodeError:
                    print("Error decoding JSON from database. Chat history might be in old format.")
                    # Optionally, add fallback code here to handle old format
                    return

            for message_data in serialized_history:
                if isinstance(message_data, dict):
                    # If it's a dict, assume it's in the new format
                    if message_data['type'] == 'HumanMessage':
                        message = HumanMessage(content=message_data['content'], avatar=message_data['avatar'])
                    elif message_data['type'] == 'AIMessage':
                        message = AIMessage(content=message_data['content'], avatar=message_data['avatar'])
                    else:
                        continue  # Skip unknown message types
                elif isinstance(message_data, (HumanMessage, AIMessage)):
                    # If it's already a message object, use it directly
                    message = message_data
                else:
                    print(f"Unknown message format: {type(message_data)}")
                    continue

                st.session_state.session_state.chat_history.append(message)
        
        # print(f'DEBUG LOAD CHAT HISTORY ----collection name: {collection_name}-- SESSION STATE CHAT HISTORY: {st.session_state.session_state.chat_history}')
    except Exception as e:
        print(f"Error loading chat history: {e}")
    
    # st.rerun()



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
    
    user_id = st.session_state.session_state.username
    collections = db.list_collection_names()
    user_sessions = [col for col in collections if col.startswith(f'user_{user_id}_session_')]
    
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

    user_sessions = list_user_sessions(st.session_state.session_state.username)
    session_options = {session['session_name']: session['collection_name'] for session in user_sessions}
    session_name = next((name for name, coll in session_options.items() if coll == collection_name), None)
    
    if session_name:
        return session_name
    
    st.error(f"No matching session found for collection: {collection_name}")
    return None

def archive_old_sessions(user_id, days_threshold=30):
    current_time = datetime.now()
    archive_threshold = current_time - timedelta(days=days_threshold)
    
    collections = db.list_collection_names()
    user_sessions = [col for col in collections if col.startswith(f'user_{user_id}_session_')]
    
    for collection_name in user_sessions:
        last_activity = db[collection_name].find_one(sort=[("timestamp", -1)])
        
        if last_activity and last_activity['timestamp'] < archive_threshold:
            archive_collection_name = f"archive_{collection_name}"
            
            with client.start_session() as session:
                with session.start_transaction():
                    db[archive_collection_name].insert_many(db[collection_name].find())
                    db[collection_name].drop()
            
            st.info(f"Archived old session: {collection_name}")



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
            st.session_state.session_state.specialist = specialist

            if "Speaker 1" in transcript:
                prompt = f"{transcript_prompt} '''{transcript}'''"
                return prompt
            else:
                prompt = transcript.replace("Speaker 0:", "").strip()
                return prompt
    return None

# Initialize the model
model = ChatAnthropic(model="claude-3-5-sonnet-20240620", temperature=0.5, max_tokens=4096)



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
    #print(f'DEBUG SS TATE CRITICAL ACTIONS:{st.session_state.session_state.critical_actions}')
    if st.session_state.session_state.critical_actions:
        st.markdown(f"<h5>❗Critical Actions</h5>", unsafe_allow_html=True)
        tasks = st.session_state.session_state.critical_actions.keys() if isinstance(st.session_state.session_state.critical_actions, dict) else st.session_state.session_state.critical_actions
        
        for task in tasks:
            key = f"critical_{task}"
            if st.checkbox(f"❗{task}", key=key):
                if task not in st.session_state.session_state.completed_tasks_str:
                    st.session_state.session_state.completed_tasks_str += f"Completed: {task}. "

def display_follow_up_tasks():
    if st.session_state.session_state.follow_up_steps:
        st.markdown(f"<h5>Possible Follow-Up Steps</h5>", unsafe_allow_html=True)
        tasks = st.session_state.session_state.follow_up_steps.keys() if isinstance(st.session_state.session_state.follow_up_steps, dict) else st.session_state.session_state.follow_up_steps
        
        for task in tasks:
            key = f"follow_up_{task}"
            if st.checkbox(f"- {task}", key=key):
                if task not in st.session_state.session_state.completed_tasks_str:
                    st.session_state.session_state.completed_tasks_str += f"Followed up: {task}. "
        
def update_completed_tasks():
    try:
        completed_tasks = [task for task, status in st.session_state.session_state.items() if task.startswith("critical_") and status]
        st.session_state.session_state.completed_tasks_str = "Tasks Completed: " + '. '.join(completed_tasks) if completed_tasks else ""
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")



def display_ddx():
    ddx_container = st.empty()
    with ddx_container.container():
        if st.session_state.session_state.differential_diagnosis:
            st.markdown("### Differential Diagnosis")
            for i, diagnosis in enumerate(st.session_state.session_state.differential_diagnosis, 1):
                st.markdown(f"**{i}.** **{diagnosis['disease']}** - {diagnosis['probability']}%")  

def display_pt_headline():
    if st.session_state.session_state.pt_data != {}:
        try:
            #print(f'DEBUG DISPLAY HEADER ST.SESSION TATE.PT DATA: {st.session_state.session_state.pt_data}')
            cc = st.session_state.session_state.pt_data["chief_complaint_two_word"]
            age = st.session_state.session_state.pt_data["age"]
            age_units = st.session_state.session_state.pt_data["age_unit"]
            if st.session_state.session_state.pt_data["sex"] == "Unknown":
                sex = ""
            else:
                sex = st.session_state.session_state.pt_data["sex"]
            st.session_state.session_state.patient_cc = f"{age}{age_units} {sex} with {cc}"
            
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

            st.markdown(f"<h5 class='patient-cc'>{st.session_state.session_state.patient_cc}</h5>", unsafe_allow_html=True)



        except KeyError as e:
            st.error(f"Missing key in patient data: {e}")
            st.title("EMMA")


def logout_user():
    #st.write(st.session_state.session_state.user_photo_url)
    colL,colR = st.columns([2,1])
    with colL:
        if st.session_state.session_state.family_name:
            st.markdown(
                f"""
                <div style="text-align: center;">
                    <h4>                  
                        <img src="{st.session_state.session_state.user_photo_url}" style="width:30px;height:30px;border-radius:50%;">
                        Dr. {st.session_state.session_state.family_name}
                    </h4>
                </div>
                """, 
                unsafe_allow_html=True)
        else:
            st.markdown(
                f"""
                <div style="text-align: center;">
                    <h4>                  
                        <img src="{st.session_state.session_state.user_photo_url}" style="width:30px;height:30px;border-radius:50%;">
                        Dr. {st.session_state.session_state.name}
                    </h4>
                </div>
                """, 
                unsafe_allow_html=True)
    with colR:
        # Add a unique key to the logout button
        if st.button("Logout", key="logout_button"):
            # controller = CookieController()
            controller.remove('session_token')
            controller.remove('session_expiry')
            st.session_state.clear()
            st.rerun()

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
            container = st.container()
            container.float(float_css_helper(bottom="10px", border="1px solid #a3a8b4", border_radius= "10px", padding= "10px"))
            with container:
                logout_user() 
        with tab2:
            display_specialist_tab()
        
        with tab4:
            display_variables_tab()

        with tab5:
            display_sessions_tab()

def display_functions_tab():
    # st.subheader('Process Management')
    # col1, col2 = st.columns(2)
    # with col1:
    #     if st.button("🛌Disposition Analysis", use_container_width=True):
    #         st.session_state.session_state.specialist = "Emergency Medicine"
    #         consult_specialist_and_update_ddx("Disposition Analysis", disposition_analysis)
    # with col2:
    #     if st.button("💉Which Procedure", use_container_width=True):
    #         consult_specialist_and_update_ddx("Which Procedure", procedure_checklist)

    st.subheader('📝Clinical Notes')
    col1, col2 = st.columns(2)
    with col1:
        if st.button('Full Medical Note', use_container_width=True):
            st.session_state.session_state.specialist = "Note Writer"
            consult_specialist_and_update_ddx("Full Medical Note", "Write a full medical note on this patient")
            st.session_state.session_state.specialist = "Emergency Medicine"
        if st.button('Full Note except EMR results', use_container_width=True):
            st.session_state.session_state.specialist = "Note Writer"
            consult_specialist_and_update_ddx("Full Note except EMR results", create_full_note_except_results)
            st.session_state.session_state.specialist = "Emergency Medicine"

    with col2:
        if st.button('HPI only', use_container_width=True):
            st.session_state.session_state.specialist = "Note Writer"
            consult_specialist_and_update_ddx("HPI only", create_hpi)
            st.session_state.session_state.specialist = "Emergency Medicine"
        if st.button('A&P only', use_container_width=True):
            st.session_state.session_state.specialist = "Note Writer"
            consult_specialist_and_update_ddx("A&P only", create_ap)
            st.session_state.session_state.specialist = "Emergency Medicine"
    st.subheader('📝Notes for Patients')
    col1, col2 = st.columns(2)
    with col1:

        if st.button("🙍Pt Education Note", use_container_width=True):
            st.session_state.session_state.specialist = "Patient Educator"
            consult_specialist_and_update_ddx("Patient Education Note", f"Write a patient education note for this patient in {st.session_state.session_state.patient_language}")
            st.session_state.session_state.specialist = "Emergency Medicine"
    with col2:
        if st.button('💪Physical Therapy Plan', use_container_width=True):
            st.session_state.session_state.specialist = "Musculoskeletal Systems"
            consult_specialist_and_update_ddx("Physical Therapy Plan", pt_plan)
            st.session_state.session_state.specialist = "Emergency Medicine"
    st.subheader('🧠Critical Thinking')
    col1, col2 = st.columns(2)
    with col1:
        # if st.button("➡️Next Step Recommendation", use_container_width=True):
        #     st.session_state.session_state.specialist = "Emergency Medicine"
        #     consult_specialist_and_update_ddx("Next Step Recommendation", next_step)
        if st.button("🤔Challenge the DDX", use_container_width=True):
            st.session_state.session_state.specialist = "General"
            consult_specialist_and_update_ddx("Challenge the DDX", challenge_ddx)
            st.session_state.session_state.specialist = "Emergency Medicine"
    with col2:
        # if st.button('🛠️Apply Clinical Decision Tools', use_container_width=True):
        #     st.session_state.session_state.specialist = "Clinical Decision Tools"
        #     consult_specialist_and_update_ddx("Apply Clinical Decision Tools", apply_decision_tool)
        #     st.session_state.session_state.specialist = "Emergency Medicine"
        if st.button("🧠Critical Thinking w Bayesian Reasoning", use_container_width=True):
            st.session_state.session_state.specialist = "Bayesian Reasoner"
            consult_specialist_and_update_ddx("Critical Thinking w Bayesian Reasoning", apply_bayesian_reasoning)
            st.session_state.session_state.specialist = "Emergency Medicine"
    st.divider()
    
    start_new_session()

def display_specialist_tab():
    # if st.session_state.session_state.differential_diagnosis:
    #     display_ddx()
    #     st.divider()
    
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

def display_sessions_tab():
    user_id = st.session_state.session_state.user_id  # Use Google ID instead of username
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
                st.success(f"Session Loaded")
                st.write(f'**{session_name}**')
                display_session_data(session_options[session_name])                    
            else:
                st.error(f"Session '{session_name}' not found in options.")
    else:
        st.write("No sessions found for this user.")

def display_session_data(collection_name):
    st.session_state.session_state.session_id = collection_name
    with st.spinner("Loading session..."):
        categorized_data = load_session_data_from_db(collection_name)
    
    # initialize_text_indexes(collection_name)
    
    st.session_state.session_state.collection_name = collection_name
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

    
    if st.button("load the chat history?", on_click=load_chat_history(collection_name)):
        load_chat_history(collection_name)
        st.success(f"Session Loaded")
        # st.rerun()

        
    display_delete_session_button(collection_name)
    
def display_delete_session_button(collection_name):
    # if 'delete_confirmation' not in st.session_state:
    #     st.session_state.delete_confirmation = False

    if st.button("Delete Session Data?"):
        st.error("Are you sure you want to delete session data? This action cannot be undone.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"Yes, delete {collection_name} data", use_container_width=True):
                db.drop_collection(collection_name)  
                st.success(f"Session data {collection_name} deleted successfully.")
                # st.session_state.delete_confirmation = False
                st.rerun()
        with col2:
            if st.button("No, cancel", type='primary', use_container_width=True):
                # st.session_state.delete_confirmation = False
                st.rerun()



def consult_specialist_and_update_ddx(button_name, prompt):
    specialist = st.session_state.session_state.specialist
    button_input(specialist, prompt)

def choose_specialist_radio():
    specialities = list(specialist_data.keys())
    captions = [specialist_data[speciality]["caption"] for speciality in specialities]

    specialist = st.radio("Choose Your Specialty Group", specialities, 
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
    st.session_state.session_state.assistant_id = specialist_data[specialist]["assistant_id"]
    st.session_state.session_state.system_instructions = specialist_data[specialist]["system_instructions"]
 
    user_question = prompt
    if user_question:
        st.session_state.session_state.specialist = specialist
        print(f'DEBUG BUTTON INPUT SPECIALIST CHOSEN: {specialist}')
        specialist_avatar = specialist_data[st.session_state.session_state.specialist]["avatar"]
        st.session_state.session_state.specialist_avatar = specialist_avatar
        timezone = pytz.timezone("America/Los_Angeles")
        current_datetime = datetime.now(timezone).strftime("%H:%M:%S")
        user_question = f"{current_datetime}\n{user_question}\n{st.session_state.session_state.completed_tasks_str}"
        st.session_state.session_state.user_question_sidebar = user_question

        st.session_state.session_state.completed_tasks_str = ''
        st.session_state.session_state.critical_actions = []
        print(f'DEBUG SESSION_STATE CRITCAL ACTIONS SHOULD BE NOTHING AFTER THIS:')
        # st.rerun()

def update_patient_language():
    patient_language = st.text_input("Insert patient language if not English", value=st.session_state.session_state.patient_language)
    if patient_language != st.session_state.session_state.patient_language:
        st.session_state.session_state.patient_language = patient_language

def process_other_queries():
    if st.session_state.session_state.user_question_sidebar != "" and st.session_state.session_state.user_question_sidebar != st.session_state.session_state.old_user_question_sidebar:
        specialist_avatar = specialist_data[st.session_state.session_state.specialist]["avatar"]
        specialist = st.session_state.session_state.specialist
        


        user_question = st.session_state.session_state.user_question_sidebar
        with st.chat_message("user", avatar=st.session_state.session_state.user_photo_url):
            st.markdown(user_question)

        st.session_state.session_state.chat_history.append(HumanMessage(user_question, avatar=st.session_state.session_state.user_photo_url))
        save_user_message(st.session_state.session_state.username, "user", user_question)

        with st.chat_message("AI", avatar=specialist_avatar):
            assistant_response = get_response(user_question)
            if specialist != "Note Writer":
                save_ai_message(st.session_state.session_state.username, specialist, assistant_response, specialist)
            if specialist == "Note Writer":
                save_note_details(st.session_state.session_state.username, assistant_response)
                save_ai_message(st.session_state.session_state.username, specialist, assistant_response, specialist)

        st.session_state.session_state.chat_history.append(AIMessage(assistant_response, avatar=specialist_avatar))
        st.session_state.session_state.old_user_question_sidebar = user_question

        # load previous chat history    
        chat_history = chat_history_string()
        parse_json(chat_history) 

        # Clear completed tasks
        st.session_state.session_state.completed_tasks_str = ""
        st.session_state.session_state.specialist = "Emergency Medicine"
        # st.rerun()
        
def new_thread():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
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
    for message in st.session_state.session_state.chat_history:
        if isinstance(message, HumanMessage):
            print(message.content, file=output)
        else:
            print(message.content, file=output)

    output_string = output.getvalue()
    save_case_details(st.session_state.session_state.username, "chat_history", output_string)
    st.session_state.session_state.clean_chat_history = output_string
    print(f'\nDEBUG chat_history_string ------output_string:{output_string}')
    return output_string

def parse_json(chat_history):
    
    pt_json_dirty = create_json(text=chat_history)
    pt_json = pt_json_dirty.replace('```', '')
    print(f'DEBUG PARSE_JSON PT_JSON_DIRTY: {pt_json_dirty}')
    print(f'DEBUG PARSE_JSON PT_JSON: {pt_json}')
    if not pt_json or pt_json.strip() == '{}':
        print("No data was extracted from the chat history.")
        return
    try:
        data = json.loads(pt_json)
        patient_data = data.get('patient', {})
        # print(f'DEBUG PARSE_JSON patient_data: {patient_data}')
        # Update session state
        st.session_state.session_state.pt_data = patient_data
        st.session_state.session_state.differential_diagnosis = patient_data.get('differential_diagnosis', [])
        st.session_state.session_state.critical_actions = patient_data.get('critical_actions', [])
        st.session_state.session_state.follow_up_steps = patient_data.get('follow_up_steps', [])
        
        print(f'DEBUG PARSE_JSON session_state.differential_diagnosis: {st.session_state.session_state.differential_diagnosis}')
        print(f'DEBUG PARSE_JSON st.session_state.session_state.critical_actionss: {st.session_state.session_state.critical_actions}')
        print(f'DEBUG PARSE_JSON st.session_state.session_state.follow_up_steps: {st.session_state.session_state.follow_up_steps}')

        # Only save case details if there's meaningful data
        if any([st.session_state.session_state.differential_diagnosis, 
                st.session_state.session_state.critical_actions, 
                st.session_state.session_state.follow_up_steps]):
            save_case_details(st.session_state.session_state.username, "ddx")
        
        lab_results = patient_data.get('lab_results', {})
        imaging_results = patient_data.get('imaging_results', {})
        
        sequence_number = 1
        for results in [lab_results, imaging_results]:
            for test_name, test_result in results.items():
                if test_result:  # Only upsert if there's a result
                    conditional_upsert_test_result(st.session_state.session_state.username, test_name, test_result, sequence_number)
                    sequence_number += 1

    except json.JSONDecodeError:
        print("Failed to parse JSON data")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        print(f"Full error details: {repr(e)}")  # This will print more detailed error information

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
        
        col_specialist, col1, col2, col3= st.columns([.5, 3, .5,.5])
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
        with col3:
            if st.button("refresh"):
                return
        
    if user_question:
        process_user_question(user_question, specialist)
        # st.session_state.session_state.should_rerun = True
    elif user_chat:
        process_user_question(user_chat, specialist)
        # st.session_state.session_state.should_rerun = True

    # if st.session_state.session_state.should_rerun:
    #     # st.session_state.session_state.should_rerun = False
    #     st.rerun()

def process_user_question(user_question, specialist):
    if user_question:
        if not st.session_state.session_state.collection_name:
            create_new_session()



        # Save the completed tasks before clearing
        completed_tasks = st.session_state.session_state.completed_tasks_str
        
        timezone = pytz.timezone("America/Los_Angeles")
        current_datetime = datetime.now(timezone).strftime("%H:%M:%S")
        
        # Include the completed tasks in the user l
        full_user_question = f"""{current_datetime}
            \n{user_question}
            \n{completed_tasks}
            """
        
        save_user_message(st.session_state.session_state.username, "user", full_user_question)
        
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
        
        save_ai_message(st.session_state.session_state.username, "ai", assistant_response, specialist)

        # load previous chat history    
        chat_history = chat_history_string()
        print(f'DEBUG PROCESS USER QUESTION ------ st.session_state.session_state.chat_history: {st.session_state.session_state.chat_history}')
        parse_json(chat_history)
        
        # Clear completed tasks
        st.session_state.session_state.completed_tasks_str = ""
        
        # Debug output
        # print("DEBUG: Session State after processing user question")


def main():
    
    if 'session_state' not in st.session_state:
        st.session_state.session_state = SessionState()

    logging.info(f"DEBUG INITIALIZE SESSION STATE SESSIONSTATE: {st.session_state.session_state}")

    # Get the current OAuth state from the session state
    oauth_state = st.session_state.session_state.oauth_state
    logging.info(f"Current OAuth state from session state: {oauth_state}")

    try:
        session_token = controller.get('session_token')
        session_expiry = controller.get('session_expiry')
        
        user = None
        if session_token and session_expiry:
            expiry = datetime.fromisoformat(session_expiry)
            if expiry > datetime.utcnow():
                user = get_user_from_session(session_token)
                if user:
                    update_session_state_with_user(user)
                    st.session_state.session_state.auth_state = 'authenticated'
                else:
                    logging.error("Failed to load user from session token")
                    controller.remove('session_token')
                    controller.remove('session_expiry')
                    st.session_state.session_state.auth_state = 'initial'
            else:
                st.warning("Your session has expired. Please log in again.")
                clear_session(session_token)
                controller.remove('session_token')
                controller.remove('session_expiry')
                st.session_state.session_state.auth_state = 'initial'
        
        # Check for OAuth callback first
        if 'code' in st.query_params:
            user = google_callback()
            if user:
                update_session_state_with_user(user)
                st.session_state.session_state.auth_state = 'authenticated'
                st.session_state.session_state.auth_completed = True
                st.success(f"Welcome, {user.name}!")
                # Clear query params
                st.query_params.clear()
                # Force a rerun to clear the URL
                st.rerun()
            else:
                st.error("Failed to log in. Please try again.")
                st.session_state.session_state.auth_state = 'initial'
                st.query_params.clear()
        
        if st.session_state.session_state.auth_state == 'initial':
            google_login()
        elif st.session_state.session_state.auth_state == 'authenticated':
            try:
                if st.session_state.session_state.differential_diagnosis != []:
                    
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
                            border_radius="10px",  # Rounded edges
                            height="calc(95vh - 80px)",  # Adjust the height as needed
                            overflow_y="auto",  # Enable vertical scrolling
                            padding="10px"  # Add some padding for better appearance
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
                    display_header()
                    display_chat_history()
                    handle_user_input_container()
                    
                process_other_queries()     
                display_sidebar()

                # Periodically archive old sessions
                archive_old_sessions(st.session_state.session_state.username)                    
                    
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                logging.error(f"Unhandled exception in main: {str(e)}", exc_info=True)

    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        logging.error(f"Unhandled exception in main: {str(e)}", exc_info=True)


if __name__ == '__main__':
    main()
