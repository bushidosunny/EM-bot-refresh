import streamlit as st
import streamlit_authenticator as stauth
import extra_streamlit_components as stx
# from pymongo import MongoClient
import bcrypt
import datetime
from typing import Tuple, Optional 
from bson import ObjectId
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import secrets
import logging
import time


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# @st.cache_resource
def get_cookie_manager():
    return stx.CookieManager(key="mongo_auth_cookie_manager")

cookie_manager = get_cookie_manager()

#################################### User Class ########################################
@dataclass
class User:
    username: str
    email: str
    name: str
    _id: ObjectId = field(default_factory=ObjectId)
    password: Optional[bytes] = None
    user_id: str = field(default_factory=lambda: secrets.token_hex(16))
    created_at: datetime = field(default_factory=datetime.datetime.now)
    last_login: datetime = field(default_factory=datetime.datetime.now)
    login_count: int = 0
    last_active: datetime = field(default_factory=datetime.datetime.now)
    total_session_time: int = 0
    preferences: Dict[str, List] = field(default_factory=lambda: {"note_templates": []})
    recordings_count: int = 0
    transcriptions_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        user_dict = {
            "_id": self._id,
            "username": self.username,
            "email": self.email,
            "name": self.name,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "login_count": self.login_count,
            "last_active": self.last_active,
            "total_session_time": self.total_session_time,
            "preferences": self.preferences,
            "recordings_count": self.recordings_count,
            "transcriptions_count": self.transcriptions_count
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
        self.last_login = datetime.datetime.now()
        self.login_count += 1

    def update_activity(self) -> None:
        self.last_active = datetime.datetime.now()

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
  
  ################################### MongoAuthenticator Class ##########################################################


class MongoAuthenticator:
    def __init__(self, users_collection, cookie_name, cookie_expiry_days, cookie_manager):
        self.users = users_collection
        self.cookie_name = cookie_name
        self.cookie_expiry_days = cookie_expiry_days
        self.cookie_manager = cookie_manager

    def login(self, username: str, password: str) -> Tuple[Optional[str], bool, Optional[str]]:
        user = self.users.find_one({"username": username})
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            user_id = str(user['_id'])
            self.create_cookie(user_id)
            st.session_state.authentication_status = True
            st.session_state.name = user['name']
            st.session_state.username = username
            return user['name'], True, username
        return None, False, None

    def create_cookie(self, user_id):
        expiry = datetime.datetime.now() + datetime.timedelta(days=self.cookie_expiry_days)
        self.cookie_manager.set(self.cookie_name, user_id, expires_at=expiry)
        st.session_state.user_id = user_id

    def logout(self):
        # Attempt to get the cookie value
        cookie_value = self.cookie_manager.get(self.cookie_name)
        
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
        
        print(f"Cookie {self.cookie_name} should be deleted. Current value: {self.cookie_manager.get(self.cookie_name)}")

    def is_authenticated(self):
        return self.cookie_manager.get(self.cookie_name) is not None

 # Modified: Now creates a User object and inserts it into the database
    def register_user(self, username, name, password, email):
        if self.users.find_one({"$or": [{"username": username}, {"email": email}]}):
            return False
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user = User(
            username=username,
            name=name,
            email=email,
            password=hashed_password,
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

    def login_page(self):
        st.header("Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

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

        if st.button("Don't have an account? Register here"):
            st.session_state.show_registration = True
            st.rerun()

    def register_page(self):
        st.header("Register")
        with st.form("register_form"):
            username = st.text_input("Username")
            name = st.text_input("Name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Register")

        if submit:
            try:
                if self.register_user(username, name, password, email):
                    st.success("Registration successful. Please login.")
                    st.session_state.show_registration = False
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Username or email already exists")
            except Exception as e:
                st.error(f"An error occurred during registration: {str(e)}")

        if st.button("Already have an account? Login here"):
            st.session_state.show_registration = False
            st.rerun()

    def authenticate(self):
        if st.session_state.get('authentication_status'):
            return True
        else:
            user_id = self.cookie_manager.get(self.cookie_name)
            if user_id and user_id != "":
                user = self.users.find_one({"_id": ObjectId(user_id)})
                if user:
                    st.session_state.authentication_status = True
                    st.session_state.name = user['name']
                    st.session_state.username = user['username']
                    return True
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

    def update_user_details(self, username, field, new_value):
        if field in ['name', 'email']:
            self.users.update_one({"username": username}, {"$set": {field: new_value}})
            return True
        return False