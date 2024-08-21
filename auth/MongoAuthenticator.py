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
    sessions_count: int = 0
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
            "sessions_count": self.sessions_count, 
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
        user.sessions_count = data.get("sessions_count", 0)
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

    # def create_or_update_daily_session(self, user_id: str) -> None:
    #     logging.info(f"Checking daily session for user_id: {user_id}")
    #     try:
    #         user_data = self.users.find_one({"_id": ObjectId(user_id)})
    #         if user_data is None:
    #             logging.error(f"No user found with id: {user_id}")
    #             st.error("Session error: User not found. Please log in again.")
    #             self.logout()
    #             st.rerun()
    #             return

    #         today = datetime.datetime.now().date()
    #         last_login = user_data.get('last_login')

    #         if last_login is None or last_login.date() < today:
    #             # It's a new day, increment the session count
    #             result = self.users.update_one(
    #                 {"_id": ObjectId(user_id)},
    #                 {
    #                     "$inc": {"sessions_count": 1},
    #                     "$set": {"last_login": datetime.datetime.now()}
    #                 }
    #             )

    #             if result.modified_count == 1:
    #                 logging.info(f"Incremented daily session count for user: {user_data['username']}")
    #             else:
    #                 logging.warning(f"Failed to increment daily session count for user: {user_data['username']}")
    #         else:
    #             logging.info(f"User {user_data['username']} already has an active session today")

    #     except Exception as e:
    #         logging.error(f"Error updating daily session for user {user_id}: {str(e)}")
    #         st.error("An error occurred while updating your session. Please try again.")

    def update_user_metrics(self, user_id: str) -> None:
        user_obj = User.from_dict(self.users.find_one({"_id": ObjectId(user_id)}))
        user_obj.update_login()
        user_obj.update_activity()

        self.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "last_login": user_obj.last_login,
                    "login_count": user_obj.login_count,
                    "last_active": user_obj.last_active,
                }
            }
        )

    def increment_sessions_count(self) -> None:
            self.sessions_count += 1

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

#################################### MongoAuthenticator Class ########################################
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

            # Update user metrics
            self.update_user_metrics(user_id)

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

    def create_new_session(self, user_id: str) -> None:
        logging.info(f"Creating new chat session for user_id: {user_id}")
        try:
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$inc": {"sessions_count": 1}}
            )

            if result.modified_count == 1:
                logging.info(f"Incremented chat session count for user: {user_id}")
            else:
                logging.warning(f"Failed to increment chat session count for user: {user_id}")

        except Exception as e:
            logging.error(f"Error creating new chat session for user {user_id}: {str(e)}")
            st.error("An error occurred while creating a new chat session. Please try again.")

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

    def authenticate(self):
        logging.info("Authenticating user...")
        
        if st.session_state.get('authentication_status'):
            logging.info("User already authenticated in session state")
            return True
        else:
            logging.info(f"Checking for user_id in cookie: {self.cookie_name}")
            logging.info(f"Cookie value: {self.cookie_manager.get(self.cookie_name)}")
            # time.sleep(1)
            user_id = self.cookie_manager.get(self.cookie_name)
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

    def update_user_details(self, username, field, new_value):
        if field in ['name', 'email']:
            self.users.update_one({"username": username}, {"$set": {field: new_value}})
            return True
        return False

######################################### UI ##########################################################

    def login_page(self):
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
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            st.header("Register")
            with st.form("register_form"):
                username = st.text_input("Username")
                name = st.text_input("Name")
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Register", type='primary')

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

    def forgot_username_page(self):
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

