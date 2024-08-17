import streamlit as st
import streamlit_authenticator as stauth
import extra_streamlit_components as stx
# from pymongo import MongoClient
import bcrypt
from datetime import datetime, timedelta
from typing import Tuple, Optional 

# @st.cache_resource
def get_cookie_manager():
    return stx.CookieManager(key="mongo_auth_cookie_manager")

cookie_manager = get_cookie_manager()

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
            return user['name'], True, username
        return None, False, None

    def create_cookie(self, user_id):
        print("Creating cookie")
        expiry = datetime.now() + timedelta(days=self.cookie_expiry_days)
        self.cookie_manager.set(self.cookie_name, user_id, expires_at=expiry)
        print("Cookie created")
        print(f'Cookie value: {self.cookie_manager.get(self.cookie_name)}')
        st.session_state.user_id = user_id
        # st.rerun()  # Add this line

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
        self.cookie_manager.set(self.cookie_name, "", expires_at=datetime.now() - timedelta(days=1))
        
        # Clear all session state variables
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Explicitly set authentication status to False
        st.session_state.authentication_status = False
        
        print(f"Cookie {self.cookie_name} should be deleted. Current value: {self.cookie_manager.get(self.cookie_name)}")

    def is_authenticated(self):
        return self.cookie_manager.get(self.cookie_name) is not None

    def reset_password(self, username, current_password, new_password):
        user = self.users.find_one({"username": username})
        if user and bcrypt.checkpw(current_password.encode('utf-8'), user['password']):
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            self.users.update_one({"username": username}, {"$set": {"password": hashed_password}})
            return True
        return False

    def register_user(self, username, name, password, email):
        if self.users.find_one({"$or": [{"username": username}, {"email": email}]}):
            return False
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user = {
            "username": username,
            "name": name,
            "password": hashed_password,
            "email": email
        }
        self.users.insert_one(user)
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

    def update_user_details(self, username, field, new_value):
        if field in ['name', 'email']:
            self.users.update_one({"username": username}, {"$set": {field: new_value}})
            return True
        return False