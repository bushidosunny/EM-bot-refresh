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


def delete_user_none_sessions(db):
    # Get all collection names
    collection_names = db.list_collection_names()
    
    # Filter collections that start with "user_None_session"
    target_collections = [name for name in collection_names if name.startswith("user_None_session")]
    
    # Delete each matching collection
    for collection_name in target_collections:
        db.drop_collection(collection_name)
        print(f"Deleted collection: {collection_name}")

# Call the function after establishing the MongoDB connection
try:
    client = init_mongodb_connection()
    db = client[DB_NAME]
    
    # Other collection initializations...
    
    client.admin.command('ping')
    print("Successfully connected to MongoDB")
    
    # Delete user_None_session collections
    delete_user_none_sessions(db)
    
except (ServerSelectionTimeoutError, OperationFailure, ConfigurationError) as err:
    st.error(f"Error connecting to MongoDB Atlas: {err}")
    st.stop()