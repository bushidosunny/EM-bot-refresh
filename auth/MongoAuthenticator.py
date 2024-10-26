import streamlit as st
import streamlit_authenticator as stauth
import extra_streamlit_components as stx
# from pymongo import MongoClient
import bcrypt
import datetime
from help import *
from typing import Tuple, Optional 
from bson import ObjectId
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import secrets
import logging
import time
import os
from prompts import EULA
from dotenv import load_dotenv

load_dotenv

SUPPORT_EMAIL = "bushidosunny@gmail.com"
PREAUTHORIZED_EMAILS = os.getenv("EMAIL_LIST")

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# @st.cache_resource
def get_cookie_manager():
    return stx.CookieManager(key="mongo_auth_cookie_manager")

cookie_manager = get_cookie_manager()

# UI default discrptions
EM_NOTE = "EM Note"
GENERAL_MEDICINE = "General Medicine"
EMERGENCY_MEDICINE = "Emergency Medicine"
NOTE_WRITER = "Note Writer"


SPECIALTIES = [
    "Emergency Medicine",
    "Internal Medicine",
    "Pediatrics",
    "Surgery",
    "Obstetrics and Gynecology",
    "Psychiatry",
    "Family Medicine",
    "Anesthesiology",
    "Radiology",
    "Neurology",
    "Cardiology",
    "Dermatology",
    "Gastroenterology",
    "Oncology",
    "Orthopedic Surgery",
    "Otolaryngology",
    "Urology",
    "Nephrology",
    "Endocrinology",
    "Rheumatology",
    "Pulmonology",
    "Infectious Disease",
    "Hematology",
    "Allergy and Immunology",
    "Physical Medicine and Rehabilitation",
    "Pathology",
    "Ophthalmology",
    "Neurosurgery",
    "Plastic Surgery",
    "Vascular Surgery",
    "Thoracic Surgery",
    "Critical Care Medicine",
    "Neonatology",
    "Geriatrics",
    "Pain Medicine",
    "Sports Medicine",
    "Medical Genetics",
    "Nuclear Medicine",
    "Preventive Medicine",
    "Occupational Medicine",
    "Aerospace Medicine",
    "Addiction Medicine",
    "Hospice and Palliative Medicine",
    "Sleep Medicine",
    "Interventional Radiology",
    "Veterinary Medicine",
    "emma_system_DDX",
    "Academic Researcher",
    "Emergency Medicine DDX",
    "Other"
]
#################################### User Class ########################################
@dataclass
class User:
    username: str
    email: str
    name: str
    specialty: str = EMERGENCY_MEDICINE
    preferred_templates: Dict[str, str] = field(default_factory=dict)
    _id: ObjectId = field(default_factory=ObjectId)
    password: Optional[bytes] = None
    user_id: str = field(default_factory=lambda: secrets.token_hex(16))
    created_at: datetime = field(default_factory=datetime.datetime.now)
    last_login: datetime = field(default_factory=datetime.datetime.now)
    login_count: int = 0
    sessions_created: int = 0
    last_active: datetime = field(default_factory=datetime.datetime.now)
    total_session_time: int = 0
    preferences: Dict[str, List] = field(default_factory=lambda: {"note_templates": []})
    recordings_count: int = 0
    preferred_note_type: str = EM_NOTE
    transcriptions_count: int = 0
    shared_templates: List[Dict] = field(default_factory=list)
    hospital_name: str = ""
    hospital_contact: str = ""

    def to_dict(self) -> Dict[str, Any]:
        user_dict = {
            "_id": self._id,
            "username": self.username,
            "email": self.email,
            "name": self.name,
            "specialty": self.specialty,
            "preferred_templates": self.preferred_templates,
            "preferred_note_type": self.preferred_note_type,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "login_count": self.login_count,
            "last_active": self.last_active,
            "sessions_created": self.sessions_created, 
            "total_session_time": self.total_session_time,
            "preferences": self.preferences,
            "recordings_count": self.recordings_count,
            "transcriptions_count": self.transcriptions_count,
            "hospital_name": self.hospital_name,
            "hospital_contact": self.hospital_contact
        }
        if self.password:
            user_dict["password"] = self.password
        return user_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        user = cls(
            username=data["username"],
            email=data["email"],
            name=data["name"],
            _id=data.get("_id")
        )
        user.password = data.get("password")
        user.specialty=data.get("specialty", "Other")
        user.preferred_templates = data.get("preferred_templates", {})
        user.preferred_note_type = data.get("preferred_note_type", EM_NOTE)
        user.created_at = data.get("created_at", user.created_at)
        user.last_login = data.get("last_login", user.last_login)
        user.login_count = data.get("login_count", 0)
        user.sessions_created = data.get("sessions_created", 0)
        user.last_active = data.get("last_active", user.last_active)
        user.total_session_time = data.get("total_session_time", 0)
        user.preferences = data.get("preferences", {"note_templates": []})
        user.recordings_count = data.get("recordings_count", 0)
        user.transcriptions_count = data.get("transcriptions_count", 0)
        user.hospital_name = data.get("hospital_name", "")
        user.hospital_contact = data.get("hospital_contact", "")
        return user
    
    def update_user_details(self, field: str, value: str) -> None:
        if field in ['name', 'hospital_name', 'hospital_contact']:
            setattr(self, field, value)
    def update_login(self) -> None:
        self.last_login = datetime.datetime.now()
        self.login_count += 1

    def update_activity(self) -> None:
        self.last_active = datetime.datetime.now()

    def update_user_metrics(self, user_id: str) -> None:
        logging.info(f"Updating user metrics for user_id: {user_id}")
        try:
            user_data = self.users.find_one({"_id": ObjectId(user_id)})
            if user_data is None:
                logging.error(f"No user found with id: {user_id}")
                return

            today = datetime.datetime.now().date()
            last_login = user_data.get('last_login')

            update_fields = {
                "last_active": datetime.datetime.now()
            }

            if last_login is None or last_login.date() < today:
                # It's a new day, update last_login and increment login_count
                update_fields.update({
                    "last_login": datetime.datetime.now(),
                    "login_count": user_data.get('login_count', 0) + 1
                })

            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_fields}
            )

            if result.modified_count == 1:
                logging.info(f"Updated user metrics for user: {user_data['username']}")
            else:
                logging.warning(f"Failed to update user metrics for user: {user_data['username']}")

        except Exception as e:
            logging.error(f"Error updating user metrics for user {user_id}: {str(e)}")


    def increment_sessions_created(self) -> None:
            self.sessions_created += 1

    def add_session_time(self, duration: int) -> None:
        self.total_session_time += duration

    def increment_recordings(self) -> None:
        self.recordings_count += 1

    def increment_transcriptions(self) -> None:
        self.transcriptions_count += 1

    def get_note_templates(self):
        return self.preferences.get("note_templates", [])

    def get_note_template(self, template_id):
        return next((t for t in self.get_note_templates() if t['id'] == template_id), None)

    def get_preferred_template(self, note_type):
        return self.preferred_templates.get(note_type)

    def set_preferred_template(self, note_type, template_id):
        if template_id is None:
            self.preferred_templates.pop(note_type, None)
        else:
            self.preferred_templates[note_type] = template_id

         # Update the user document in MongoDB
        # Update the user document in MongoDB
        self.users.update_one(
            {"username": self.username},
            {"$set": {"preferred_templates": self.preferred_templates}}
        )

    ########## User Template Methods ##########
    def delete_note_template(self, template_id: str) -> bool:
        initial_length = len(self.preferences.get("note_templates", []))
        self.preferences["note_templates"] = [t for t in self.preferences.get("note_templates", []) if t["id"] != template_id]
        return len(self.preferences.get("note_templates", [])) < initial_length

    def add_note_template(self, title: str, note_type: str, content: str):
        """Add a new custom note template."""
        if "note_templates" not in self.preferences:
            self.preferences["note_templates"] = []
        
        new_template = {
            "id": str(ObjectId()),
            "title": title,
            "type": note_type,
            "content": content,
            "use_count": 0,
            "created_at": datetime.datetime.now(),
            "updated_at": datetime.datetime.now()
        }
        self.preferences["note_templates"].append(new_template)


    def rate_custom_note_template(self, template_id: str, rating: int):
        """Rate a custom note template."""
        for template in self.preferences.get("note_templates", []):
            if template["id"] == template_id:
                if "ratings" not in template:
                    template["ratings"] = []
                template["ratings"].append({"rating": rating, "timestamp": datetime.datetime.now()})
                return True
        return False

    def rate_shared_template(self, template_id: str, rating: int, comment: str = ""):
        """Rate and review a shared template."""
        for template in self.shared_templates:
            if template["id"] == template_id:
                if "ratings" not in template:
                    template["ratings"] = []
                if "reviews" not in template:
                    template["reviews"] = []
                
                template["ratings"].append({"rating": rating, "timestamp": datetime.datetime.now()})
                if comment:
                    template["reviews"].append({
                        "user": self.username,
                        "rating": rating,
                        "comment": comment,
                        "timestamp": datetime.datetime.now()
                    })
                return True
        return False

    def get_shared_template_reviews(self, template_id: str):
        """Get all reviews for a shared template."""
        for template in self.shared_templates:
            if template["id"] == template_id:
                return template.get("reviews", [])
        return []

    def rate_shared_template(self, template_id: str, rating: int, comment: str = ""):
        """Rate and review a shared template."""
        for template in self.shared_templates:
            if template["id"] == template_id:
                if "ratings" not in template:
                    template["ratings"] = []
                if "reviews" not in template:
                    template["reviews"] = []
                
                template["ratings"].append({"rating": rating, "timestamp": datetime.datetime.now()})
                if comment:
                    template["reviews"].append({
                        "user": self.username,
                        "rating": rating,
                        "comment": comment,
                        "timestamp": datetime.datetime.now()
                    })
                return True
        return False

    def get_shared_template_rating(self, template_id: str):
        """Get the average rating of a shared template."""
        for template in self.shared_templates:
            if template["id"] == template_id:
                ratings = template.get("ratings", [])
                if ratings:
                    return sum(r["rating"] for r in ratings) / len(ratings)
        return None

    def get_shared_template_reviews(self, template_id: str):
        """Get all reviews for a shared template."""
        for template in self.shared_templates:
            if template["id"] == template_id:
                return template.get("reviews", [])
        return []

    def increment_template_use_count(self, template_id: str):
        """Increment the use count of a template."""
        for template in self.preferences.get("note_templates", []):
            if template["id"] == template_id:
                template["use_count"] = template.get("use_count", 0) + 1
                return True
        return False

    def update_note_template(self, template_id: str, title: str = None, note_type: str = None, content: str = None):
        for template in self.preferences.get("note_templates", []):
            if template["id"] == template_id:
                if title:
                    template["title"] = title
                if note_type:
                    template["type"] = note_type
                if content:
                    template["content"] = content
                template["updated_at"] = datetime.datetime.now()
                break

#################################### MongoAuthenticator Class ########################################
class MongoAuthenticator:
    def __init__(self, users_collection, cookie_name, cookie_expiry_days, cookie_manager):
        self.users = users_collection
        self.cookie_name = cookie_name
        self.cookie_expiry_days = cookie_expiry_days
        self.cookie_manager = cookie_manager
        self.preauthorized_emails = PREAUTHORIZED_EMAILS.split(',') if isinstance(PREAUTHORIZED_EMAILS, str) else PREAUTHORIZED_EMAILS

    def login(self, username: str, password: str) -> Tuple[Optional[str], bool, Optional[str]]:
        user = self.users.find_one({"username": username})
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            user_id = str(user['_id'])
            self.create_cookie(user_id)
            st.session_state.authentication_status = True
            st.session_state.name = user['name']
            st.session_state.username = username
            st.session_state.email = user['email']
            st.session_state.specialty = user.get('specialty', EMERGENCY_MEDICINE)
            st.session_state.preferred_note_type = user.get('preferred_note_type', EM_NOTE)

            # Always increment login_count on manual login
            self.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "last_login": datetime.datetime.now(),
                        "last_active": datetime.datetime.now()
                    },
                    "$inc": {"login_count": 1}
                }
            )

            return user['name'], True, username
        return None, False, None
    
    
    def update_user_metrics(self, user_id: str) -> None:
        logging.info(f"Updating user metrics for user_id: {user_id}")
        try:
            user_data = self.users.find_one({"_id": ObjectId(user_id)})
            if user_data is None:
                logging.error(f"No user found with id: {user_id}")
                return

            today = datetime.datetime.now().date()
            last_login = user_data.get('last_login')

            update_fields = {
                "last_active": datetime.datetime.now()
            }

            if last_login is None or last_login.date() < today:
                # It's a new day, update last_login and increment login_count
                update_fields.update({
                    "last_login": datetime.datetime.now(),
                    "login_count": user_data.get('login_count', 0) + 1
                })

            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_fields}
            )

            if result.modified_count == 1:
                logging.info(f"Updated user metrics for user: {user_data['username']}")
            else:
                logging.warning(f"Failed to update user metrics for user: {user_data['username']}")

        except Exception as e:
            logging.error(f"Error updating user metrics for user {user_id}: {str(e)}")
        



    # def set_preferred_template(self, note_type: str, template_id: str):
    #     self.preferred_templates[note_type] = template_id

    # def get_preferred_template(self, note_type: str) -> Optional[str]:
    #     return self.preferred_templates.get(note_type)     
       
    def create_new_session(self, user_id: str) -> None:
        logging.info(f"Creating new chat session for user_id: {user_id}")
        try:
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$inc": {"sessions_created": 1}}
            )

            if result.modified_count == 1:
                logging.info(f"Incremented chat session count for user: {user_id}")
            else:
                logging.warning(f"Failed to increment chat session count for user: {user_id}")

        except Exception as e:
            logging.error(f"Error creating new chat session for user {user_id}: {str(e)}")
            st.error("An error occurred while creating a new chat session. Please try again.")

    def check_password_strength(self, password):
        if len(password) < 8:
            return "Weak"
        elif len(password) < 12:
            return "Medium"
        else:
            return "Strong"
        
    def create_cookie(self, user_id):
        expiry = datetime.datetime.now() + datetime.timedelta(days=self.cookie_expiry_days)
        self.cookie_manager.set(self.cookie_name, user_id, expires_at=expiry)
        st.session_state.user_id = user_id

    def logout(self):
        # Attempt to get the cookie value
        cookie_value = self.cookie_manager.cookies.get(self.cookie_name)
        
        # If the cookie exists, delete it
        if cookie_value is not None:
            self.cookie_manager.delete(self.cookie_name)
            print(f"Cookie {self.cookie_name} deleted.")
        else:
            print(f"Cookie {self.cookie_name} not found. It may have been already deleted.")
        
        # Set cookie expiration to a past date
        self.cookie_manager.set(self.cookie_name, "", expires_at=datetime.datetime.now() - datetime.timedelta(days=1))
        
        # Clear all session state variables
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Explicitly set authentication status to False
        st.session_state.authentication_status = False
        
        print(f"Cookie {self.cookie_name} should be deleted. Current value: {self.cookie_manager.cookies.get(self.cookie_name)}")

    def is_authenticated(self):
        return self.cookie_manager.cookies.get(self.cookie_name) is not None

    def register_user(self, username, name, password, email, specialty):
        if self.users.find_one({"$or": [{"username": username}, {"email": email}]}):
            return False
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user = User(
            username=username,
            name=name,
            email=email,
            password=hashed_password,
            specialty=specialty,
            _id=ObjectId()  # Explicitly create a new ObjectId
        )
        self.users.insert_one(user.to_dict())
        return True

    def forgot_password(self, username):
        user = self.users.find_one({"username": username})
        if user:
            # Generate a new random password
            new_password = stauth.generate_random_pw()
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            self.users.update_one({"username": username}, {"$set": {"password": hashed_password}})
            return username, user['email'], new_password
        return None, None, None
    
    def get_user_specialty(self, username):
        user = self.users.find_one({"username": username})
        if user:
            return user.get('specialty', EMERGENCY_MEDICINE)
        return EMERGENCY_MEDICINE

    def authenticate(self):
        logging.info("Authenticating user...")
        
        if st.session_state.get('authentication_status'):
            logging.info("User already authenticated in session state")
            return True
        else:
            logging.info(f"Checking for user_id in cookie: {self.cookie_name}")
            logging.info(f"Cookie value: {self.cookie_manager.cookies.get(self.cookie_name)}")
            # time.sleep(1)
            user_id = self.cookie_manager.cookies.get(self.cookie_name)
            logging.info(f"Retrieved user_id from cookie: {user_id}")
            if user_id and user_id != "":
                try:
                    user = self.users.find_one({"_id": ObjectId(user_id)})
                    if user:
                        logging.info(f"Found user: {user['username']}")
                        st.session_state.authentication_status = True
                        st.session_state.name = user['name']
                        st.session_state.username = user['username']
                        st.session_state.user_id = str(user['_id'])
                        st.session_state.email = user['email']
                        st.session_state.hospital_name = user.get('hospital_name', "")
                        st.session_state.hospital_contact = user.get('hospital_contact', "")
                        st.session_state.specialty = user.get('specialty', EMERGENCY_MEDICINE)
                        st.session_state.preferred_note_type = user.get('preferred_note_type', EM_NOTE)

                        print(f'Authenticated user specialty: {st.session_state.specialty}')
                        print(f'Authenticated user preferred_note_type: {st.session_state.preferred_note_type}')
                        
                        # Update user metrics and check/update daily login
                        self.update_user_metrics(user_id)
                        
                        return True
                    else:
                        logging.warning(f"No user found for id: {user_id}")
                except Exception as e:
                    logging.error(f"Error during authentication: {str(e)}")
                
                # User not found or error occurred, clear the invalid cookie
                self.logout()
                st.error("Your session has expired. Please log in again.")
                st.rerun()
            else:
                logging.info("No user_id found in cookie")
            return False
    
    def change_password(self, username, current_password, new_password):
        user = self.users.find_one({"username": username})
        if user and bcrypt.checkpw(current_password.encode('utf-8'), user['password']):
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            self.users.update_one({"username": username}, {"$set": {"password": hashed_password}})
            return True
        return False

    def reset_password(self, username, email):
        user = self.users.find_one({"username": username, "email": email})
        if user:
            new_password = secrets.token_urlsafe(12)
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            self.users.update_one({"username": username}, {"$set": {"password": hashed_password}})
            return new_password
        return None
    def update_user(self, username: str, user_data: dict):
        # Remove the _id field if it exists, as MongoDB doesn't allow updating this field
        user_data.pop('_id', None)
        result = self.users.update_one({"username": username}, {"$set": user_data})
        return result.modified_count > 0
    
    def update_user_details(self, username, field, new_value):
        if field in ['name', 'email']:
            self.users.update_one({"username": username}, {"$set": {field: new_value}})
            return True
        return False

    def save_feedback(self, user_id: str, raw_feedback: str, processed_feedback: str):   
        try:
            feedback_doc = {
            "user_id": st.session_state.username,
            "user_email": st.session_state.email,
            "session_id": st.session_state.session_id,
            "timestamp": datetime.datetime.now(),
            "raw_feedback": raw_feedback,
            "processed_feedback": processed_feedback
        }
            result = self.users.database['feedback'].insert_one(feedback_doc)
            if result.inserted_id:
                logging.info(f"Feedback saved successfully for user {user_id}")
                return True
            else:
                logging.error(f"Failed to save feedback for user {user_id}")
                return False
        except Exception as e:
            logging.error(f"Error saving feedback for user {user_id}: {str(e)}")
            return False
     
    def get_help_content(self, topic):
        help_topics = {
            "Using EMMA": emmma_general_help
            }
        
        return help_topics.get(topic, "Help content not found.")


######################################### UI ##########################################################


    def login_page(self):
        display_header()
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            st.header("Login")
            with st.form("login_form"):
                username = st.text_input("Username").lower() 
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login", type='primary')

            if submit:
                name, authentication_status, username = self.login(username, password)
                if authentication_status:
                    st.success(f"Welcome {name}!")
                    time.sleep(1)
                    st.rerun()
                    # user_data = self.users.find_one({"username": username})
                    # if user_data:
                    #     st.session_state.user = User.from_dict(user_data)
                    #     st.session_state.authentication_status = True
                    #     st.session_state.name = name
                    #     st.session_state.username = username
                    #     st.success(f"Welcome {name}!")
                    #     time.sleep(1)
                    #     st.rerun()
                else:
                    st.error("Incorrect username or password")

            # New buttons for forgot username and change password
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Register Here", key="register_btn"):
                    st.session_state.show_registration = True
                    st.rerun()
                
            with col2:
                if st.button("Change Password", key="change_password_btn"):
                    st.session_state.show_change_password = True
                    st.rerun()
            with col3:
                if st.button("Forgot Username", key="forgot_username_btn"):
                    st.session_state.show_forgot_username = True
                    st.rerun()

            # Handle forgot username
            if st.session_state.get('show_forgot_username', False):
                self.forgot_username_page()

            # Handle change password
            if st.session_state.get('show_change_password', False):
                self.change_password_page()

    def register_page(self):
        display_header()
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            st.title("Register")
        
            if 'eula_agreed' not in st.session_state:
                st.session_state.eula_agreed = False

            if not st.session_state.eula_agreed:
                st.header("End User License Agreement")
                
                st.markdown("""
                <style>
                .big-font {
                    font-size:16px !important;
                    font-family: Arial, sans-serif;
                }
                </style>
                """, unsafe_allow_html=True)
                
                st.markdown(EULA)
                
                agree = st.checkbox("I agree to the terms and conditions")
                
                if agree:
                    if st.button("Proceed to Registration", type="primary"):
                        st.session_state.eula_agreed = True
                        st.rerun()
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Sign In"):
                        st.session_state.show_login = True
                        st.rerun()
                with col2:
                    if st.button("Help"):
                        st.info(f"If you need assistance, please contact {SUPPORT_EMAIL}")
            
            else:
                st.title("Register Your Account")
                
                st.markdown("""
                <style>
                @media (max-width: 600px) {
                    .stTextInput > div > div > input {
                        font-size: 16px;
                    }
                }
                </style>
                """, unsafe_allow_html=True)
                
                with st.form("register_form"):
                    st.markdown('<p style="color: red;">* Required field</p>', unsafe_allow_html=True)
                    username = st.text_input("Username *").lower() 
                    name = st.text_input("Name *").title()
                    email = st.text_input("Email *").lower()
                    password = st.text_input("Password *", type="password")
                    confirm_password = st.text_input("Confirm Password *", type="password")
                    specialty = st.selectbox("Specialty *", options=SPECIALTIES)
                    submit = st.form_submit_button("Register", type='primary')

                if submit:
                    if not all([username, name, email, password, confirm_password, specialty]):
                        st.error("All fields are required.")
                    elif password != confirm_password:
                        st.error("Passwords do not match.")
                    # elif email not in self.preauthorized_emails:
                    #     st.error("Sorry, you are not authorized to register. Please contact the administrator.")
                    else:
                        try:
                            if self.register_user(username, name, password, email, specialty):
                                st.success(f"Registration successful! Welcome {name}!")
                                st.session_state.show_registration = False
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Username or email already exists. Choose a different username or email.")
                        except Exception as e:
                            st.error(f"An error occurred during registration: {str(e)}")

                if st.button("Back to EULA"):
                    st.session_state.eula_agreed = False
                    st.rerun()

    def forgot_username_page(self):
        display_header()
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            st.subheader("Forgot Username")
            email = st.text_input("Enter your email address", key="forgot_username_email")
            if st.button("Retrieve Username", key="retrieve_username_btn", type='primary'):
                user = self.users.find_one({"email": email})
                if user:
                    st.success(f"Your username is: {user['username']}")
                else:
                    st.error("No account found with this email address")
            if st.button("Back to Login", key="forgot_username_back"):
                st.session_state.show_forgot_username = False
                st.rerun()

    def change_password_page(self):
        display_header()
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            st.subheader("Change Password")
            username = st.text_input("Username", key="change_pw_username")
            current_password = st.text_input("Current Password", type="password", key="change_pw_current")
            new_password = st.text_input("New Password", type="password", key="change_pw_new")
            confirm_password = st.text_input("Confirm New Password", type="password", key="change_pw_confirm")
            if st.button("Change Password", key="change_pw_button", type='primary'):
                if new_password != confirm_password:
                    st.error("New passwords do not match")
                elif self.change_password(username, current_password, new_password):
                    st.success("Password changed successfully")
                    st.session_state.show_change_password = False
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid username or current password")
            if st.button("Back to Login", key="change_pw_back"):
                st.session_state.show_change_password = False
                st.rerun()


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
