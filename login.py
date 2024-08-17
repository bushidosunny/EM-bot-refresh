import os
import secrets
import logging
import datetime
from typing import List, Dict, Any, Optional

import streamlit as st
import extra_streamlit_components as stx
import pandas as pd
from pymongo import MongoClient
import bcrypt
from bson import ObjectId
from dataclasses import dataclass, field

from auth.MongoAuthenticator import MongoAuthenticator

########################## Constants and Configuration ##############################
DB_NAME = 'emma-dev'
MONGODB_URI = os.getenv('MONGODB_ATLAS_URI')
PREAUTHORIZED_EMAILS = ['user1@example.com', 'user2@example.com', 'bushidosunny@gmail.com']

logging.basicConfig(level=logging.INFO)
# st.set_page_config(page_title="Login Page", page_icon="🔑", layout="centered")

#################################### User Class ########################################
@dataclass
class User:
    username: str
    email: str
    name: str
    _id: Optional[ObjectId] = None
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
        return {
            "_id": self._id,
            "username": self.username,
            "password": self.password,
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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        user = cls(
            username=data["username"],
            email=data["email"],
            name=data["name"],
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
  
  #############################################################################################

############################# Initialize MongoDB connection #################################
# @st.cache_resource
def init_mongodb_connection():
    logging.info("Initializing MongoDB connection")
    return MongoClient(MONGODB_URI, maxPoolSize=10, connect=False)

try:
    client = init_mongodb_connection()
    db = client[DB_NAME]
    users_collection = db['users']
    client.admin.command('ping')
    logging.info("Successfully connected to MongoDB")
except Exception as e:
    st.error(f"Failed to connect to MongoDB: {str(e)}")
    st.stop()

# def get_users_from_db(users_collection):
#     users_cursor = users_collection.find()
#     return list(users_cursor)


################################# Authentication Functions #################################
# @st.cache_resource
def get_cookie_manager():
    return stx.CookieManager(key="login_cookie_manager")

cookie_manager = get_cookie_manager()


# Initialize the authenticator
authenticator = MongoAuthenticator(
    users_collection=users_collection,
    cookie_name='EMMA_auth_cookie',
    cookie_expiry_days=30,
    cookie_manager=cookie_manager 
)




def register_user(username, name, password, email, users_collection):
    if email not in PREAUTHORIZED_EMAILS:
        return False, "Email not preauthorized"
    
    if users_collection.find_one({"$or": [{"username": username}, {"email": email}]}):
        return False, "Username or email already exists"
    
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    user = User(email=email, username=username, name=name, password=hashed_password)
    user.update_login()
    result = users_collection.insert_one(user.to_dict())
    user._id = result.inserted_id
    
    st.session_state.user = user
    st.session_state.username = user.name
    return True, "Registration successful"

def register_page():
    st.header("Register")
    with st.form("register_form"):
        username = st.text_input("Username")
        name = st.text_input("Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Register")

    if submit:
        if authenticator.register_user(username, name, password, email):
            st.success("Registration successful. Please login.")
        else:
            st.error("Username or email already exists")


def login_page(authenticator):
    st.header("Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

    if submit:
        name, authentication_status, username = authenticator.login(username, password)
        if authentication_status:
            st.success(f"Welcome {name}!")
            st.rerun()
        else:
            st.error("Incorrect username or password")

    st.markdown("Don't have an account? [Register here](#)")

# def main_page():
#     st.success(f"Welcome {st.session_state.name}")
#     st.title("Main Page")

#     with st.sidebar:
#         st.write(f"Welcome {st.session_state.name}")

#     if st.sidebar.button("Logout", key="logout_button_login"):        
#         authenticator.logout()
#         st.rerun()
        


################################## Main App Function ########################################
# def main():
#     if 'authentication_status' not in st.session_state:
#         st.session_state.authentication_status = False

#     if st.session_state.authentication_status:
#         main_page()
#     else:
#         tab1, tab2 = st.tabs(["Login", "Register"])
#         with tab1:
#             login_page()
#         with tab2:
#             register_page()

# if __name__ == "__main__":
#     main()
