import streamlit as st
import streamlit_authenticator as stauth
from streamlit_float import float_css_helper
from pymongo import MongoClient
import bcrypt
import secrets
import os
import toml
import logging

# Constants
DB_NAME = 'emma-dev'
SECRET_KEY = secrets.token_hex(32)

# Load configuration
if os.path.exists('/.streamlit/secrets.toml'):
    with open('/.streamlit/secrets.toml', 'r') as f:
        config = toml.load(f)
    MONGODB_URI = config['MONGODB_ATLAS_URI']
    ENVIRONMENT = config['ENVIRONMENT']
else:
    MONGODB_URI = os.getenv('MONGODB_ATLAS_URI')
    ENVIRONMENT = os.getenv('ENVIRONMENT')

# Initialize MongoDB connection
@st.cache_resource
def init_mongodb_connection():
    logging.info("Initializing MongoDB connection")
    return MongoClient(MONGODB_URI, maxPoolSize=1, connect=False)

try:
    logging.info("Attempting to connect to MongoDB")
    client = init_mongodb_connection()
    db = client[DB_NAME]
    users_collection = db['users']
    client.admin.command('ping')
    logging.info("Successfully connected to MongoDB")
except Exception as e:
    st.error(f"Failed to connect to MongoDB: {str(e)}")
    st.stop()

# Custom authentication functions

def verify_password(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)


def get_user_credentials():
    users = list(users_collection.find({}, {'_id': 0, 'name': 1, 'username': 1, 'password': 1}))
    credentials = {"usernames": {}}
    for user in users:
        credentials["usernames"][user['username']] = {
            "name": user['name'],
            "password": user['password']
        }
    return credentials


# Streamlit Authenticator setup
authenticator = stauth.Authenticate(
    get_user_credentials(),
    cookie_name='emma_auth',
    cookie_key=SECRET_KEY,
    cookie_expiry_days=30
)

def main():
    name, authentication_status, username = authenticator.login('main')
    if st.button('Register new user', type='secondary'):
        register_new_user()
    if authentication_status:
        # User is authenticated, show the app content
        st.header("EMA - Emergency Medicine Assistant 🤖🩺")
        
        with st.sidebar:
            st.title("Top Section")
            container = st.container()
            container.float(float_css_helper(bottom="10px"))
            with container:
                authenticate_user()
        
        import time
        
        if st.button('Three cheers', type='primary'):
            st.toast('Hip!')
            time.sleep(.5)
            st.toast('Hip!')
            time.sleep(.5)
            st.toast('Hooray!', icon='🎉')
    
    elif authentication_status is False:
        # Authentication failed
        st.error('Username/password is incorrect')
    
    else:
        # Authentication status is None, show login form
        st.warning('Please enter your username and password')

def authenticate_user():
    if st.session_state["authentication_status"]:
        col1, col2 = st.columns([2,1])
        with col1:
            st.write(f'Welcome *{st.session_state["name"]}*')
        with col2:
            authenticator.logout('Logout', 'main')
    elif st.session_state["authentication_status"] is False:
        st.error('Username/password is incorrect')
    elif st.session_state["authentication_status"] is None:
        st.warning('Please enter your username and password')

def register_new_user():
    try:
        email, username, name = authenticator.register_user(pre_authorization=False)
        if email:
            st.success('User registered successfully')
            new_user = {
                'username': st.session_state.username,
                'name': st.session_state.name,
                'password': bcrypt.hashpw(st.session_state.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                'email': st.session_state.email
            }
            users_collection.insert_one(new_user)
    except Exception as e:
        st.error(e)

        
def reset_password():
    if authenticator.reset_password(st.session_state["username"]):
        st.success('Password modified successfully')
        # Update the password in MongoDB
        users_collection.update_one(
            {'username': st.session_state["username"]},
            {'$set': {'password': authenticator.credentials['passwords'][st.session_state["username"]]}}
        )

def forgot_password():
    username_of_forgotten_password, email_of_forgotten_password, new_random_password = authenticator.forgot_password()
    if username_of_forgotten_password:
        st.success('New password to be sent securely')
        # Update the password in MongoDB
        users_collection.update_one(
            {'username': username_of_forgotten_password},
            {'$set': {'password': authenticator.credentials['passwords'][username_of_forgotten_password]}}
        )
    elif username_of_forgotten_password == False:
        st.error('Username not found')

def forgot_username():
    username_of_forgotten_username, email_of_forgotten_username = authenticator.forgot_username()
    if username_of_forgotten_username:
        st.success('Username to be sent securely')
    elif username_of_forgotten_username == False:
        st.error('Email not found')

def update_user_details():
    if authenticator.update_user_details(st.session_state["username"]):
        st.success('Entries updated successfully')
        # Update user details in MongoDB
        users_collection.update_one(
            {'username': st.session_state["username"]},
            {'$set': {
                'name': authenticator.credentials['names'][st.session_state["username"]],
                'email': authenticator.credentials['emails'][st.session_state["username"]]
            }}
        )

def setup_initial_passwords():
    users = list(users_collection.find({}))
    for user in users:
        if 'password' not in user:
            # Generate a random password (in a real scenario, you'd want to let users set their own)
            password = secrets.token_urlsafe(12)
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            users_collection.update_one(
                {'_id': user['_id']},
                {'$set': {'password': hashed_password}}
            )
            print(f"Set initial password for user {user['username']}: {password}")


# Path: add_user_to_mongodb.py
import bcrypt

def add_user_to_mongodb(username, name, email, password):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = {
        'username': username,
        'name': name,
        'email': email,
        'password': hashed_password
    }
    users_collection.insert_one(user)




if __name__ == '__main__':
    main()

#######################################################################################

# import streamlit as st
# import streamlit_authenticator as stauth
# from pymongo import MongoClient

# # MongoDB connection
# client = MongoClient('your_mongodb_connection_string')
# db = client['your_database_name']
# users_collection = db['users']

# # Load initial config (you might want to replace this with loading from MongoDB)
# config = {
#     'credentials': {
#         'usernames': {}
#     },
#     'cookie': {
#         'name': 'your_cookie_name',
#         'key': 'your_cookie_key',
#         'expiry_days': 30
#     },
#     'pre-authorized': []
# }

# # Initialize authenticator
# authenticator = stauth.Authenticate(
#     config['credentials'],
#     config['cookie']['name'],
#     config['cookie']['key'],
#     config['cookie']['expiry_days'],
#     config['pre-authorized']
# )

# def update_user_config_file():
#     # Instead of updating a file, update MongoDB
#     for username, user_data in config['credentials']['usernames'].items():
#         users_collection.update_one(
#             {'username': username},
#             {'$set': user_data},
#             upsert=True
#         )

# def register_new_user():
#     try:
#         email_of_registered_user, username_of_registered_user, name_of_registered_user = authenticator.register_user(pre_authorization=False)
#         if email_of_registered_user:
#             st.success('User registered successfully')
#             update_user_config_file()
#     except Exception as e:
#         st.error(e)

# # Load users from MongoDB into config
# users = users_collection.find()
# for user in users:
#     config['credentials']['usernames'][user['username']] = {
#         'email': user['email'],
#         'name': user['name'],
#         'password': user['password']
#     }