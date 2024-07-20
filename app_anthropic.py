import streamlit as st
from streamlit_float import float_css_helper
from anthropic import Anthropic
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import os
import io
from dotenv import load_dotenv
from prompts import *
import json
from extract_json import create_json
from datetime import datetime
import pytz
from login import *
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine
from presidio_analyzer.predefined_recognizers import SpacyRecognizer, EmailRecognizer, PhoneRecognizer, UsLicenseRecognizer, UsSsnRecognizer
from pymongo import MongoClient, ASCENDING, TEXT, DESCENDING
from pymongo.errors import DuplicateKeyError
from bson import ObjectId, Regex
from streamlit_searchbox import st_searchbox
from fuzzywuzzy import fuzz


#def generate_session_id():
    #return secrets.token_urlsafe(16)



# Load variables
load_dotenv()
ema_v2 = "asst_na7TnRA4wkDbflTYKzo9kmca"
open_ai_api_key = os.getenv("OPENAI_API_KEY")
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    st.error("API Key not found! Please check your environment variables.")
#legal_attorney = "asst_ZI3rML4v8eG1vhQ3Fis5ikOd"
#note_writer = 'asst_Ua6cmp6dpTc33cSpuZxutGsX'

anthropic = Anthropic(api_key=api_key)

#############################################################################
                          ### Mongo DB section ###

# Initialize MongoDB connection
#@st.cache_resource
def init_connection():
    return MongoClient('mongodb://localhost:27017/')

client = init_connection()
db = client['emma']

# Create a new session collection
def create_session_collection():
    user_id = st.session_state.username
    # print(f'DEBUG USER-ID: {user_id}')
    session_id = ObjectId()
    st.session_state.session_id = session_id
    collection_name = f'user_{user_id}_session_{session_id}'
    st.session_state.collection_name = collection_name
    if collection_name not in db.list_collection_names():
        db.create_collection(collection_name)
        db[collection_name].create_index([("timestamp", ASCENDING), ("test_name", ASCENDING)], unique=True)

        # Initialize text indexes for the new collection
        initialize_text_indexes()
        st.session_state.collection_name = collection_name




# Retrieve documents from a session collection
def get_documents_by_session(session_id):
    collection_name = st.session_state.collection_name
    return list(db[collection_name].find({}).sort("timestamp", ASCENDING))


# Function to save chat message
def save_ai_message(user_id, sender, message, specialist="ai"):
    chat_document = {
        "type": "ai_input",
        "specialist": specialist,
        "user_id": user_id,
        "sender": sender,
        "message": message,
        "timestamp": datetime.now(),
        "patient_cc": st.session_state.patient_cc
    }
    try:
        db[st.session_state.collection_name].insert_one(chat_document)
    except DuplicateKeyError:
        #update the existing document instead:
        db[st.session_state.collection_name].update_one(
            {"timestamp": chat_document["timestamp"], "test_name": chat_document["test_name"]},
            {"$set": chat_document},
            upsert=True
        )

def save_user_message(user_id, sender, message):
    chat_document = {
        "type": "user_input",
        "user_id": user_id,
        "sender": sender,
        "message": message,
        "timestamp": datetime.now(),
        }
    try:
        db[st.session_state.collection_name].insert_one(chat_document)
    except DuplicateKeyError:
        #update the existing document instead:
        db[st.session_state.collection_name].update_one(
            {"timestamp": chat_document["timestamp"], "test_name": chat_document["test_name"]},
            {"$set": chat_document},
            upsert=True
        )

def save_case_details(user_id, doc_type, content=None):
    document = {
        "type": doc_type,
        "user_id": user_id,
        "ddx": st.session_state.differential_diagnosis,
        "content": content,
        "patient_cc": st.session_state.patient_cc,
        "timestamp": datetime.now(),
        }
    query = {
        "type": doc_type,
        "user_id": user_id,
    }
    
    update = {
        "$set": document
    }
    
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
        "timestamp": datetime.now(),
        }
    db[st.session_state.collection_name].insert_one(chat_document)

# Function to perform conditional upsert
def conditional_upsert_test_result(user_id, test_name, result, sequence_number):
    collection = db[st.session_state.collection_name]
    query = {"test_name": test_name, "sequence_number": sequence_number}
    try:
        existing_doc = collection.find_one(query)
        
        if existing_doc:
            existing_result = existing_doc.get("result", "").lower()
            if existing_result in ["not provided", "not performed yet", "not specified"] or existing_result != result.lower():
                # Update if the existing result is one of the special cases or if it's different
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
            # If no existing document, insert a new one
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

# Insert a test result
def insert_test_result(user_id, test_name, result):
    document = {
        "type": "test_result",
        "user_id": user_id,
        "test_name": test_name,
        "result": result,
        "timestamp": datetime.now()
    }
    try:
        db[st.session_state.collection_name].insert_one(document)
        print("Test result inserted successfully.")
    except DuplicateKeyError:
        print("Duplicate test result detected. Insertion skipped.")

# list all sessions for a specific user.
def list_user_sessions(user_id):
    collections = db.list_collection_names()
    user_sessions = [col for col in collections if col.startswith(f'user_{user_id}_session_')]
    session_details = []
    
    for session in user_sessions:
        session_id = session.split('_')[-1]
        collection_name = f'user_{user_id}_session_{session_id}'
        ddx_doc = db[collection_name].find_one({"type": "ddx"})
        
        if ddx_doc:
            timestamp = ddx_doc.get("timestamp", None)
            date_str = timestamp.strftime("%Y.%m.%d %H:%M") if timestamp else "Unknown Date"
            patient_cc = ddx_doc.get("patient_cc", "Unknown CC")
            ddx_array = ddx_doc.get("ddx", [])
            disease_name = ddx_array[0]["disease"] if ddx_array else "Unknown Disease"
            session_name = f"{date_str} - {patient_cc} - {disease_name}"
            session_details.append({"collection_name": collection_name, "session_name": session_name})
        else:
            session_details.append({"collection_name": collection_name, "session_name": session_id})
    
    return session_details

def sort_user_sessions_by_time(sessions):
    def parse_session_date(session):
        try:
            # Try to parse the date from the session name
            date_str = session['session_name'].split(' - ')[0]
            return datetime.strptime(date_str, "%Y.%m.%d %H:%M")
        except (ValueError, IndexError):
            # If parsing fails, return a minimum datetime value
            return datetime.min

    return sorted(sessions, key=parse_session_date, reverse=True)

# load data from a selected session.
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

# load chat_history after selecting a session
def load_chat_history(collection_name):
    print(f'DEBUG LOAD_CHAT_HISTORY WAS RAN!!!!')
    query = {"type": {"$in": ["user_input", "ai_input"]}}
    projection = {"message": 1, "sender": 1, "timestamp": 1, "_id": 0}

    # Execute the query and store results in a list
    chat_history = list(db[collection_name].find(query, projection).sort("timestamp", 1))

    # Format the chat history as a string
    formatted_chat_history = []
    for entry in chat_history:
        role = "Human" if entry['sender'] == "Human" else "AI"
        formatted_entry = f"{role}: {entry['message']}"
        formatted_chat_history.append(formatted_entry)

    # Join the formatted entries into a single string
    chat_history_string = "\n\n".join(formatted_chat_history)

    # Store the formatted chat history in the session state
    st.session_state.clean_chat_history = chat_history_string
    print(f'DEBUG LOAD_CHAT_HISTORY CLEAN_CHAT_HISTORY result: {chat_history_string}')
    return chat_history_string

# search sessions via keywords    

def search_sessions(user_id, keywords):
    collections = db.list_collection_names()
    user_sessions = [col for col in collections if col.startswith(f'user_{user_id}_session_')]
    results = []

    if not keywords.strip():
        return results

    for collection_name in user_sessions:
        # Check existing indexes
        existing_indexes = db[collection_name].index_information()
        text_index = next((index for index in existing_indexes.values() if any('text' in field for field in index['key'])), None)

        # Prepare the query
        content_query = {"content": Regex(f".*{keywords}.*", "i")}

        # Combine queries
        combined_query = {"$and": [{"type": "chat_history"}, content_query]}

        projection = {
            "collection_name": {"$literal": collection_name},
            "timestamp": 1,
            "content": 1,
            "patient_cc": 1,
            "ddx": 1,
            "sender": 1,
        }

        # Execute the query
        collection_results = list(db[collection_name].find(combined_query, projection)
                                  .sort("timestamp", DESCENDING)
                                  .limit(10))  # Limit results per collection

        # If text index exists, perform text search separately and merge results
        if text_index:
            text_query = {"$text": {"$search": keywords}}
            text_results = list(db[collection_name].find({"$and": [{"type": "chat_history"}, text_query]}, projection)
                                .sort([("score", {"$meta": "textScore"})])
                                .limit(10))

            # Merge results, removing duplicates
            collection_results = list({r["_id"]: r for r in collection_results + text_results}.values())

        results.extend(collection_results)

    # Sort all results by timestamp
    results.sort(key=lambda x: x['timestamp'], reverse=True)

    return results[:20]  # Return top 20 overall results

def update_indexes(collection_name):
    # Drop the existing text index
    db[collection_name].drop_index("message_text_patient_cc_text_content_text_test_name_text_result_text")

    # Create a new text index with the desired fields
    db[collection_name].create_index([("content", TEXT), ("patient_cc", TEXT), ("ddx", TEXT)])

def load_session_from_search(result):
    collection_name = result['collection_name']
    user_sessions = list_user_sessions(st.session_state.username)
    session_options = {session['session_name']: session['collection_name'] for session in user_sessions}
    
    # Find the session name that corresponds to the collection name
    session_name = next((name for name, coll in session_options.items() if coll == collection_name), None)
    
    if session_name:
        return session_name

def initialize_text_indexes():
    collections = db.list_collection_names()
    for collection_name in collections:
        if collection_name.startswith('user_'):
            # Check if a text index already exists
            existing_indexes = db[collection_name].index_information()
            text_index = next((index for index in existing_indexes.values() if any('text' in field for field in index['key'])), None)
            
            if not text_index:
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
                    print(f"Error creating index for collection {collection_name}: {str(e)}")
            else:
                print(f"Text index already exists for collection: {collection_name}")


def display_search_results(results):
    #print(f'DEBUG DISPLAY_SEARCH_RESULTS: {results}')
    for i, result in enumerate(results):
        # st.write(f"**Session:** {result['collection_name']}")
        st.write(f"**Date:** {result['timestamp'].strftime('%Y-%m-%d %H:%M')}")
        try:
            if st.button(f"{result['patient_cc']} - **{result['ddx'][0]['disease']}**",
                        help="click to load session",
                        type='primary'):
                session_name = load_session_from_search(result)
                print(f'DEBUG DISPLAY_SEARCH_RESULTS - YOU NEED THIS FORMAT TO LOAD SESSION CORRECTLY: {session_name}')
                return session_name
        except:
            st.write("no info")
        #try:
            #st.write(f"{result['patient_cc']} - **{result['ddx'][0]['disease']}**")
        #except:
            #st.write('no DDX available')
        
        with st.expander("See Details..."):
            st.write(f"{result['content']}")
        #st.write(f"**Relevance Score:** {result['score']:.2f}")
        
        
            
        
        st.write("---")


def search_sessions_for_searchbox(search_term):
    if not search_term.strip():
        return []
    
    results = search_sessions(st.session_state.username, search_term)
    
    # Calculate relevance scores
    scored_results = []
    for r in results:
        score = fuzz.partial_ratio(search_term.lower(), r['patient_cc'].lower())
        scored_results.append((score, r))
    
    # Sort by score, then by original order (assuming timestamp indicates importance)
    sorted_results = sorted(scored_results, key=lambda x: (-x[0], -x[1]['timestamp'].timestamp()))
    
    return [
        (f"{r['timestamp'].strftime('%Y.%m.%d %H:%M')} - {r['patient_cc']} - {r['ddx'][0]['disease']}", r)
        for score, r in sorted_results if 'timestamp' in r and 'patient_cc' in r and 'ddx' in r and r['ddx']
    ]


#############################################################################





# Initialize the model
model = ChatAnthropic(model="claude-3-5-sonnet-20240620", temperature=0.5, max_tokens=4096)

# Define the avatar URLs
user_avatar_url = "https://cdn.pixabay.com/photo/2016/12/21/07/36/profession-1922360_1280.png"

specialist_id_caption = {
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
    "avatar": "https://cdn.pixabay.com/photo/2015/12/09/22/19/muscle-1085672_1280.png"
  },
  "General": {
    "assistant_id": "asst_K2QHe4VfHGdyrrfTCiyctzyY",
    "caption": "ICU, Internal Medicine, HemOnc, Endocrinology",
    "avatar": "https://cdn.pixabay.com/photo/2013/07/12/18/59/doctor-154130_1280.png"
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
    "avatar": "https://cdn.pixabay.com/photo/2013/07/12/14/33/carrot-148456_960_720.png"
  },
  "DDX Beta B": {
    "assistant_id": "asst_L74hbYKMs4OsKy0EA30mmY1s",
    "caption": "EM - Beta testing",
    "avatar": "https://cdn.pixabay.com/photo/2013/07/12/14/33/carrot-148456_960_720.png"
  },
  "Cardiology Clinic": {
    "assistant_id": "asst_m4Yispc9GIdwGFsyz2KNT8c5",
    "caption": "Cardiologis in Clinic - Beta testing",
    "avatar": "https://cdn.pixabay.com/photo/2017/02/15/20/58/ekg-2069872_1280.png"
  }
  
}

# Initialize session_state variables
def initialize_session_state():
    state_keys_defaults = {
        "authentication_status": None,
        "logout": None,
        "collection_name" :"",
        "name": "",
        "username": "Sunny",
        "chat_history": [],
        "user_question": "",
        "legal_question": "",
        "note_input": "",
        "json_data": {},
        "pt_data": {},
        "differential_diagnosis": {},
        "danger_diag_list": {},
        "critical_actions": {},
        "sidebar_state": 1,
        "assistant_response": "",
        "patient_language": "English",
        "specialist_input": "",
        "should_rerun": False,
        "user_question_sidebar": "",
        "old_user_question_sidebar": "",
        "completed_tasks_str": "",
        "follow_up_steps":"",
        "messages":[],
        "system_instructions": emma_system,
        "pt_title": "",
        "patient_cc":"",
        "clean_chat_history":""
    }

    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        for key, default in state_keys_defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default

        primary_specialist = list(specialist_id_caption.keys())[0]
        st.session_state.specialist = primary_specialist
        st.session_state.assistant_id = specialist_id_caption[primary_specialist]["assistant_id"]
        st.session_state.specialist_avatar = specialist_id_caption[primary_specialist]["avatar"]
        st.session_state.system_instructions = specialist_id_caption[primary_specialist]["system_instructions"]


# Setup the main page display and header
def display_header():
    if st.session_state.pt_data != {}:
        cc = st.session_state.pt_data['patient']["chief_complaint_two_word"]
        age = st.session_state.pt_data['patient']["age"]
        age_units = st.session_state.pt_data['patient']["age_unit"]
        sex = st.session_state.pt_data['patient']["sex"]
        st.session_state.patient_cc = f"{age}{age_units}{sex} {cc}"
        st.set_page_config(page_title=f"{st.session_state.patient_cc}", page_icon="🤖", initial_sidebar_state="collapsed")
    else:
        st.set_page_config(page_title=f"EMMA", page_icon="🤖", initial_sidebar_state="collapsed")
    st.markdown(
            f"""
            <div style="text-align: center;">
                <h2>
                    <span style="color:deepskyblue;">Emergency Medicine </span>                    
                    <img src="https://i.ibb.co/LnrQp8p/Designer-17.jpg" alt="Avatar" style="width:80px;height:80px;border-radius:20%;">
                    Main Assistant
                </h2>
            </div>
            """, 
            unsafe_allow_html=True)

def display_critical_tasks():
    if st.session_state.critical_actions:
        st.subheader(":blue[Critical Actions]")
        # Create a dictionary to hold the status of each task
        task_status = {task: False for task in st.session_state.critical_actions}

        # Display the tasks with checkboxes
        for task in st.session_state.critical_actions:
            key = f"critical_{task}"  # Create a unique key for each checkbox
            task_status[task] = st.checkbox(f"- :blue[{task}]", value=task_status[task], key=key)

        # Check which tasks are completed and save to a string variable
        completed_tasks = [task for task, status in task_status.items() if status]

        if completed_tasks:
            st.session_state.completed_tasks_str = "Tasks Completed: " + '. '.join(completed_tasks)

def display_follow_up_tasks():
    if st.session_state.follow_up_steps:
        st.subheader(":yellow[Possible Follow-Up Steps]")
        # Create a dictionary to hold the status of each task
        task_status = {task: False for task in st.session_state.follow_up_steps}

        # Display the tasks with checkboxes
        for task in st.session_state.follow_up_steps:
            key = f"follow_up_{task}"  # Create a unique key for each checkbox
            task_status[task] = st.checkbox(f"- :yellow[{task}]", value=task_status[task], key=key)

        # Check which tasks are completed and save to a string variable
        completed_tasks = [task for task, status in task_status.items() if status]

        if completed_tasks:
            st.session_state.completed_tasks_str = "Tasks Completed: " + '. '.join(completed_tasks)

def display_ddx():
    if st.session_state.differential_diagnosis:
        st.subheader("Differential Diagnosis")
        #save_case_details(st.session_state.username)
        for diagnosis in st.session_state.differential_diagnosis:
            disease = diagnosis['disease']
            probability = diagnosis['probability']
            st.markdown(f"- {disease} - {probability}%")    

# Sidebar display
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
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Functions", "Specialists", "Note Analysis", "Update Variables", "Sessions"])
        
        with tab1:
            display_ddx()
            display_critical_tasks()
            display_follow_up_tasks()
            st.divider()
            display_functions_tab()

        with tab2:
            #display_critical_tasks(2)

            
            if st.session_state.differential_diagnosis:
                st.subheader("Differential Diagnosis")
                for diagnosis in st.session_state.differential_diagnosis:
                    disease = diagnosis['disease']
                    probability = diagnosis['probability']
                    st.markdown(f"- {disease} - {probability}%")
                st.divider()
            
            choose_specialist_radio()
            
            st.subheader(':orange[Consult Recommnedations]')
            button1 = st.button("General Reccommendations")
            button2 = st.button("Diagnosis")
            button3 = st.button("Treatment Plan")
            button4 = st.button("Disposition Plan")
            
            if button1: 
                consult_specialist_and_update_ddx("General Reccommendations", consult_specialist)
            if button2: 
                consult_specialist_and_update_ddx("Diagnosis consult", consult_diagnosis)
            if button3: 
                consult_specialist_and_update_ddx("Treatment consult", consult_treatment)
            if button4: 
                consult_specialist_and_update_ddx("Disposition consult", consult_disposition)

            # Ensure choose_specialist_radio is called here with a unique key
            
            
        with tab3:
            display_note_analysis_tab()
            
        with tab4:
            update_patient_language()
            buttoni = st.button("Update Indexes")

            if buttoni:
                update_indexes(st.session_state.session_id)

        container = st.container()
        container.float(float_css_helper(bottom="10px"))
        #with container:
            #authenticate_user()
        
        with tab5:
            user_id = st.session_state.username
            user_sessions = list_user_sessions(user_id)
            # print(f'DEBUG USER SESSIONS: name: {user_id} user session:{user_sessions}')
            #if 'should_rerun' in st.session_state and st.session_state.should_rerun:
                #st.session_state.should_rerun = False
                #st.rerun()
            if user_sessions:
                # Sort sessions by timestamp, newest first
                sorted_sessions = sort_user_sessions_by_time(user_sessions)
                session_options = {session['session_name']: session['collection_name'] for session in sorted_sessions}
                
                
                
                session_name = st.selectbox("Select a recent session to load:", 
                            options=["Select a session..."] + list(session_options.keys()),
                            index=0,
                            key="session_selectbox") # Set index to 0 to select the placeholder by default
                
                # Check if a session was selected from search results
                if 'selected_session' in st.session_state:
                    selected_session = st.session_state.selected_session
                    del st.session_state.selected_session  # Clear the selection after using it

                # Search function

                ######## basic search ########
                #search_query = st.text_input("Search sessions:")

                #if search_query:
                    ##results = search_sessions(st.session_state.username, search_query)
                   # session_name = display_search_results(results)
                   # print(f'DEBUG BASIC SEARCH SESSION_NAME: {session_name}')

                ####### streamlit-searchbox versions #########
                
                selected_session = st_searchbox(
                    search_sessions_for_searchbox,
                    key="session_searchbox",
                    label="Search sessions",
                    placeholder="Type to search for sessions...",
                    default_use_searchterm=False,
                    rerun_on_update=False,
                    style_overrides = {
                                    "dropdown": {
                                        "width": "100%",
                                        "max-height": "400px",
                                        "overflow-y": "auto"
                                    },
                                    "searchbox": {
                                        "menuList": {
                                            "maxHeight": "1000px"
                                        }
                                    }
                                }
                )
                print(f'DEBUG STREMLIT SEARCHBOX SEARCH_RESULTS: {selected_session}')
                

                if selected_session:
                    session_name = load_session_from_search(selected_session)
                    if session_name:
                        st.success(f"Session Loaded")
                        # Add any additional logic you need when a session is selected
                    else:
                        st.error("Failed to load the selected session.")
                    print(f'DEBUG STREMLIT SEARCHBOX SESSION_NAME: {session_name}')             


                # Check if a real session is selected (not the placeholder)
                if session_name != "Select a session..." and session_name:
                    #st.success(f"Loaded session: {session_name}")
                    collection_name = session_options[session_name]
                    st.session_state.session_id = collection_name
                    print(f'DEBUG SESSSION ID FROM SESSTION STATE: {collection_name}')
                    categorized_data = load_session_data(collection_name)
                    
                    # Initialize text indexes for the loaded collection
                    initialize_text_indexes()
                    
                    # load chat history from Mongo DB
                    load_chat_history(collection_name)
                    print(f'DEBUG CLEAN_CHAT_HISTORY: {st.session_state.clean_chat_history}')
                    # Load mongo DB collection after selection
                    st.session_state.collection_name = collection_name

                    st.write(f"**Data of session: {session_name}**")
                    
                    # Display Differential Diagnosis (ddx)
                    with st.expander("Differential Diagnosis (ddx)"):
                        for doc in categorized_data["ddx"]:
                            ddx_list = doc.get('ddx', [])
                            if ddx_list:
                                for diagnosis in ddx_list:
                                    disease = diagnosis.get('disease', 'Unknown')
                                    probability = diagnosis.get('probability', 'N/A')
                                    st.write(f"- {disease}: {probability}%")
                            
                    
                    # Display Test Results
                    with st.expander("Test Results"):
                        for doc in categorized_data["test_result"]:
                            st.write(f"**{doc.get('test_name', 'N/A')}:** {doc.get('result', 'N/A')}")
                            st.write(f"{doc.get('timestamp', 'N/A')}")
                            #st.write("---")
                    
                    # Display Clinical Notes
                    with st.expander("Clinical Notes"):
                        for doc in categorized_data["clinical_note"]:
                            st.write(f"Specialist: {doc.get('specialist', 'N/A')}")
                            st.markdown(f"Message: {doc.get('message', 'N/A')}")
                            st.write(f"Timestamp: {doc.get('timestamp', 'N/A')}")
                            st.write("---")
                    
                    # Display Chat History
                    with st.expander("Chat History"):
                        for doc in categorized_data["chat_history"]:
                            st.write(f"**Sender: {doc.get('sender', 'N/A')}**")
                            st.write(f"Message: {doc.get('message', 'N/A')}")
                            st.write(f"Timestamp: {doc.get('timestamp', 'N/A')}")
                            st.write("---")
            else:
                st.write("No sessions found for this user.")
                    
                   
def consult_specialist_and_update_ddx(button_name, prompt):
    # Consult the specific specialist
    specialist = st.session_state.specialist
    button_input(specialist, prompt)

    """# If necessary, temporarily switch to an EM agent
    if needs_em_update_for(button_name):
        temp_specialist = "Emergency Medicine"
        st.session_state.specialist = temp_specialist
        st.session_state.assistant_id = specialist_id_caption[temp_specialist]["assistant_id"]

        # Update ddx and plan with new information
        button_input(temp_specialist, integrate_consultation)

    # Resetting the specialist back if it was changed
    if st.session_state.specialist == temp_specialist:
        st.session_state.specialist = specialist"""

# Sidebar tabs and functions
def display_functions_tab():
    
    st.subheader('Process Management')
    col1, col2 = st.columns(2)
    with col1:
        button1 = st.button("🛌Disposition Analysis")
    with col2:
        button2 = st.button("💉Which Procedure")

    st.subheader('📝Note Writer')
    col1, col2 = st.columns(2)
    with col1:
        button3 = st.button('Full Medical Note')
        button14 = st.button('Full Note except EMR results')
        button4 = st.button("🙍Pt Education Note")
    with col2:
        button11 = st.button('HPI only')
        button12 = st.button('A&P only')
        button13 = st.button('💪Physical Therapy Plan')
        

    st.subheader('🏃‍♂️Flow')
    col1, col2 = st.columns(2)
    with col1:
        button5 = st.button("➡️Next Step Recommendation")
        
        button10 = st.button("🤔Challenge the DDX")
    with col2:
        #button6 = st.button('➡️➡️I did that, now what?')
        button8 = st.button('🛠️Apply Clinical Decision Tools')
        button7 = st.button("🧠Critical Thinking w Bayesian Reasoning")
    st.divider()
    col1, col2, col3 = st.columns([1,3,1])
    with col2:
        button9 = st.button('NEW THREAD', type="primary")
        #button10 = st.button('TEST')

    # Process button actions
    process_buttons(button1, button2, button3, button4, button5, button7, button8, button9, button10, button11, button12, button13, button14)

# Process the buttons
def process_buttons(button1, button2, button3, button4, button5, button7, button8, button9, button10, button11, button12, button13, button14):
    if button1:
        specialist = 'Emergency Medicine'
        prompt = disposition_analysis
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button2:
        specialist = 'Emergency Medicine'
        prompt = procedure_checklist
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button3:
        specialist = 'Note Writer'
        prompt = "Write a full medical note on this patient"
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button4:
        specialist = 'Patient Educator'
        prompt = f"Write a patient education note for this patient in {st.session_state.patient_language}"
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
        
    if button5:
        specialist = 'Emergency Medicine'
        prompt = next_step
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    #if button6:
        #specialist = 'Emergency Medicine'
        #prompt = "Ok i did that. Now what?"
        #st.session_state["specialist"] = specialist
        #button_input(specialist, prompt)
    if button7:
        specialist = 'Bayesian Reasoner'
        prompt = apply_bayesian_reasoning
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button8:
        specialist = 'Clinical Decision Tools'
        prompt = apply_decision_tool
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button9:
        new_thread()
    if button11:
        specialist = 'Note Writer'
        prompt = create_hpi
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button12:
        specialist = 'Note Writer'
        prompt = create_ap
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button13:
        specialist = 'Musculoskeletal Systems'
        prompt = pt_plan
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button14:
        specialist = 'Note Writer'
        prompt = create_full_note_except_results
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button10:
        specialist = 'General'
        prompt = challenge_ddx
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    
# Note Analysis for summary and legal analysis
def display_note_analysis_tab():
    st.header("Note Analysis")
    note_check = st.text_area("Paste your note here and hit 'Ctrl+Enter'", height=200)
    if note_check:
        st.write('Note uploaded 👍')
    else:
        st.write('No note uploaded')

    col1, col2 = st.columns(2)
    with col1:
        button7 = st.button("Summarize Note(s)")
    with col2:
        button8 = st.button("Optimize Your Note For Legal Protection")

    # Process buttons
    if button7:
        specialist = 'Note Summarizer'
        prompt = f'Summarize this: ```{note_check}```'
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button8:
        specialist = 'Medical Legal'
        prompt = optimize_legal_note + f' here is the note separated by triple backticks```{note_check}```'
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)


# Choosing the specialty group
def choose_specialist_radio():
    specialities = list(specialist_id_caption.keys())
    captions = [specialist_id_caption[speciality]["caption"] for speciality in specialities]

    if 'specialist' in st.session_state:
        selected_specialist = st.session_state.specialist
    else:
        selected_specialist = specialities[0]

    # Assign a unique key to the st.radio widget
    specialist = st.radio("**:black[Choose Your Specialty Group]**", specialities, 
                          captions=captions, 
                          index=specialities.index(selected_specialist),
                          key="choose_specialist_radio")

    if 'button_clicked' not in st.session_state:
        st.session_state.button_clicked = False

    # Only update if the selected specialist is different
    if specialist and specialist != st.session_state.specialist:
    #if specialist and specialist != st.session_state.specialist and not st.session_state.button_clicked:

        st.session_state.specialist = specialist
        st.session_state.assistant_id = specialist_id_caption[specialist]["assistant_id"]
        st.session_state.specialist_avatar = specialist_id_caption[specialist]["avatar"]
        st.session_state.system_instructions = specialist_id_caption[specialist]["system_instructions"]
        # No need to call st.rerun() here
        st.rerun()

# process button inputs for quick bot responses
def button_input(specialist, prompt):
    st.session_state.button_clicked = True
    #call the specialist
    st.session_state.assistant_id = specialist_id_caption[specialist]["assistant_id"]
    st.session_state.system_instructions = specialist_id_caption[specialist]["system_instructions"]
 
    # set st.sesssion_state.user_question_sidebar for process_other_queries() 
    user_question = prompt
    if user_question is not None and user_question != "":
        st.session_state.specialist = specialist

        specialist_avatar = specialist_id_caption[st.session_state.specialist]["avatar"]
        st.session_state.specialist_avatar = specialist_avatar
        timezone = pytz.timezone("America/Los_Angeles")
        current_datetime = datetime.now(timezone).strftime("%H:%M:%S")
        user_question = current_datetime + f"""    \n{user_question}. 
        \n{st.session_state.completed_tasks_str}
        """
        st.session_state.user_question_sidebar = user_question

        st.session_state.completed_tasks_str = ''
        st.session_state.critical_actions  = []
        #refresh page
        st.rerun()
    st.session_state.button_clicked = False

# Updating the patient language
def update_patient_language():
    patient_language = st.text_input("Insert patient language if not English", value=st.session_state.patient_language)
    if patient_language != st.session_state.patient_language:
        st.session_state.patient_language = patient_language

# Processing queries
def process_other_queries():
    if st.session_state.user_question_sidebar != "" and st.session_state.user_question_sidebar != st.session_state.old_user_question_sidebar:

        # set specialist and avatar for chat history
        specialist_avatar = specialist_id_caption[st.session_state.specialist]["avatar"]
        specialist = st.session_state.specialist
        
        
        # set user_question to sidebar user_question
        user_question = st.session_state.user_question_sidebar
        with st.chat_message("user", avatar=user_avatar_url):
            st.markdown(user_question)

        # add querry to the chat history as human user
        st.session_state.chat_history.append(HumanMessage(user_question, avatar=user_avatar_url))
        # add to MongoDB
        save_user_message(st.session_state.username, "user", user_question)

        #get ai response
        with st.chat_message("AI", avatar=specialist_avatar):
            assistant_response = get_response(user_question, st.session_state.messages)
            #st.session_state.assistant_response = assistant_response
            if specialist != "Note Writer":
                save_ai_message(st.session_state.username, specialist, assistant_response, specialist)
            if specialist == "Note Writer":
                save_note_details(st.session_state.username, assistant_response)
                save_ai_message(st.session_state.username, specialist, assistant_response, specialist)
            print(f'DEBUG SPECIALIST: {specialist}')

        #append ai response to chat_history
        st.session_state.chat_history.append(AIMessage(assistant_response, avatar=specialist_avatar))

        # session_state variable to make sure user_question is not repeated.
        st.session_state.old_user_question_sidebar = user_question

        # store to mongoDB conditions
        #if specialist != "Emergency Medicine":



        chat_history = chat_history_string()
        parse_json(chat_history) 

    elif st.session_state["legal_question"]:
        handle_user_legal_input(st.session_state["legal_question"])
    elif st.session_state["note_input"]:
        write_note(st.session_state["note_input"])

# Create new thread
def new_thread():
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id
    st.session_state.chat_history = []
    st.rerun()


def chat_history_string():
    output = io.StringIO()

    for message in st.session_state.chat_history:
        if isinstance(message, HumanMessage):
            print(message.content, file=output)
        else:
            print(message.content, file=output)

    output_string = output.getvalue()
    print(f'DEBUG CHAT_HISTORY_STRING - OUTPUT STRING: {output_string}')

    #store chat history to MongoDB
    save_case_details(st.session_state.username, "chat_history", output_string)
    st.session_state.clean_chat_history = output_string
    return output_string

def parse_json(chat_history):
    pt_json = create_json(text=chat_history)
    #print(f'DEBUG PT JSON: {pt_json}')
    try:
        data = json.loads(pt_json)
        st.session_state.pt_data = data
        st.session_state.differential_diagnosis = data['patient']['differential_diagnosis']
        st.session_state.critical_actions = data['patient']['critical_actions']
        st.session_state.follow_up_steps = data['patient']['follow_up_steps']
        
        # Store DDX
        save_case_details(st.session_state.username, "ddx")
        
        # Extract  test names and results and store in MongoDB
        lab_results = data['patient']['lab_results']
        #print(f'DEBUG LAB RESULTS: {lab_results}')
        sequence_number = 1
        for test_name, test_result in lab_results.items():
            
            #print(f'DEBUG TEST NAME AND RESULT: test name: {test_name}, test result: {test_result}')
            #insert_test_result(st.session_state.username, test_name, test_result)
            conditional_upsert_test_result(st.session_state.username, test_name, test_result, sequence_number)
        imaging_results = data['patient']['imaging_results']
        for test_name, test_result in imaging_results.items():
            
            #insert_test_result(st.session_state.username, test_name, test_result)
            conditional_upsert_test_result(st.session_state.username, test_name, test_result, sequence_number)
        #print(f'DEBUG JSON DATA: {data}')
    except:
        return



# Function to generate the response stream
def generate_response_stream(response):
    for content in response.content:
        if content.type == 'text':
            yield content.text
            
def chat_message_history():
    chat = ''
    for index, message in enumerate(st.session_state.chat_history, start=1):
        if isinstance(message, dict) and 'content' in message:
            content = message['content']
        elif hasattr(message, 'content'):
            content = message.content
        else:
            content = str(message)
        
        prefix = 'User: ' if index % 2 != 0 else 'Assistant: '
        chat += f"{prefix}{content}\n"

def get_response(user_question, message_history):
    response_placeholder = st.empty()
    response_text = ""
    chat_history = st.session_state.clean_chat_history
    print(f'DEBUG GET_RESPONSE CHAT_HISTORY: {chat_history}')
    
    #chat_mess_history = chat_message_history()
    #print(f'\nDEBUG CHAT MESS HISTORY: {chat_mess_history}')
    #message = HumanMessage(system=st.session_state.system_instructions,
             #content=user_question)
    
    # Create system message
    system_message = SystemMessage(content=st.session_state.system_instructions)
    

    # Create user message
    user_message = HumanMessage(content=user_question + "```" + chat_history + "```")

    # Combine messages
    messages = [system_message, user_message]

    # Get the response
    response = model.invoke(messages)
    response_text = response.content

    # Print the response
    response_placeholder.markdown(response_text)

    
    return response_text

def display_chat_history():    
    #st.empty()  # Clear existing chat messages
    print(f'DEBUG DISPLAY_CHAT_HISTORY ST.SS.CHAT_HISOTR: {st.session_state.chat_history}')
    for message in st.session_state.chat_history:
        if isinstance(message, HumanMessage):
            avatar_url = message.avatar
            with st.chat_message("user", avatar=user_avatar_url):                
                st.markdown(message.content, unsafe_allow_html=True)
        else:
            avatar_url = message.avatar
            with st.chat_message("AI", avatar=avatar_url):
                st.markdown(message.content, unsafe_allow_html=True)
    #print(f'\nDEBUG st.session_state.chat_history: {st.session_state.chat_history}')

# User input container
def handle_user_input_container():
    input_container = st.container()
    input_container.float(float_css_helper(bottom="50px"))
    with input_container:
        
        specialist = st.session_state.specialist
        #obtain specialist avatar
        specialist_avatar = specialist_id_caption[st.session_state.specialist]["avatar"]
            # Replace with your avatar URL
        st.markdown(
            f"""
            <div style="text-align: center;">
                <h6>
                    Specialty Group: 
                    <img src="{specialist_avatar}" alt="Avatar" style="width:30px;height:30px;border-radius:50%;">
                    <span style="color:deepskyblue;">{specialist}</span>
                </h6>
            </div>
            """, 
            unsafe_allow_html=True
        )
        user_question = st.chat_input("How may I help you?") 
        if user_question:
            if 'session_id' not in st.session_state:
                create_session_collection()
        
    process_user_question(user_question, specialist)
def process_user_question(user_question, specialist):
    if user_question is not None and user_question != "":
        #add to mongoDB
        print(F'DEBUG USERNAME IS: {st.session_state.username}')
        save_user_message(st.session_state.username, "user", user_question)
        
        timezone = pytz.timezone("America/Los_Angeles")
        current_datetime = datetime.now(timezone).strftime("%H:%M:%S")
        user_question = current_datetime + f"""\n{user_question} 
        \n{st.session_state.completed_tasks_str}
        """
        
        st.session_state.completed_tasks_str = ''
        st.session_state.critical_actions  = []
        st.session_state.specialist = specialist
        specialist_avatar = specialist_id_caption[st.session_state.specialist]["avatar"]
        st.session_state.specialist_avatar = specialist_avatar
        
        # Add user message to the session state
        st.session_state.messages.append({"role": "user", "content": user_question})
        st.session_state.chat_history.append(HumanMessage(user_question, avatar=user_avatar_url))

        
        
        with st.chat_message("user", avatar=user_avatar_url):
            st.markdown(user_question)
        
        with st.chat_message("AI", avatar=specialist_avatar):
            assistant_response = get_response(user_question, st.session_state.messages)
            st.session_state.assistant_response = assistant_response
            

        # Add assistant response to the session state
        st.session_state.messages.append({"role": "assistant", "content": assistant_response})
        st.session_state.chat_history.append(AIMessage(st.session_state.assistant_response, avatar=specialist_avatar))

        #add to mongoDB
        
        save_ai_message(st.session_state.username, "ai", assistant_response, specialist)

        chat_history = chat_history_string()
        parse_json(chat_history)    



def main():
    initialize_session_state()
    
    display_header()
    
    # Authentication with streamlit authenticator 
    # name, authentication_status, username = authenticator.login('main')
    # if authentication_status == True:
        # User is authenticated, show the app content# Create a thread where the conversation will happen and keep Streamlit from initiating a new session state
        #if "thread_id" not in st.session_state:
            #thread = client.beta.threads.create()
            #st.session_state.thread_id = thread.id
    
    display_chat_history() 
    handle_user_input_container()   
    process_other_queries() 

    display_sidebar()
    #else:
        #authenticate_user()
  

if __name__ == '__main__':
    main()
