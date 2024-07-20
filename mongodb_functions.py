
from pymongo import MongoClient, ASCENDING
from datetime import datetime

# For a local MongoDB instance
client = MongoClient('localhost', 27017)
db = client['emma']
chat_history_collection = db['chat_history']
chat_note_collection = db['notes']

# Create a new session collection
def create_session_collection(session_id):
    collection_name = f'session_{session_id}'
    if collection_name not in db.list_collection_names():
        db.create_collection(collection_name)
        db[collection_name].create_index([("timestamp", ASCENDING), ("test_name", ASCENDING)], unique=True)
        


# Insert a document into a session collection
def insert_document(session_id, doc_type, content):
    collection_name = f'session_{session_id}'
    document = {
        "type": doc_type,
        "content": content,
        "timestamp": datetime.now()
    }
    db[collection_name].insert_one(document)

# Retrieve documents from a session collection
def get_documents_by_session(session_id):
    collection_name = f'session_{session_id}'
    return list(db[collection_name].find({}).sort("timestamp", ASCENDING))


# Function to save chat message
def save_ai_message(user_id, sender, message):
    chat_document = {
        "type": "ai_input",
        "user_id": user_id,
        "sender": sender,
        "message": message,
        "timestamp": datetime.now(),
        "patient_cc": st.session_state.patient_cc
    }
    db[st.session_state.collection_name].insert_one(chat_document)

def save_user_message(user_id, sender, message):
    chat_document = {
        "type": "user_input",
        "user_id": user_id,
        "sender": sender,
        "message": message,
        "timestamp": datetime.now(),
        }
    db[st.session_state.collection_name].insert_one(chat_document)

def save_case_details(user_id):
    document = {
        "type": "ddx",
        "user_id": user_id,
        "ddx": st.session_state.differential_diagnosis,
        "patient_cc": st.session_state.patient_cc,
        "name": st.session_state.name,
        "timestamp": datetime.now(),
        }
    query = {
        "type": "ddx",
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
                "timestamp": datetime.datetime.now()
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
    return user_sessions

# load data from a selected session.
def load_session_data(user_id, session_id):
    collection_name = f'user_{user_id}_session_{session_id}'
    return list(db[collection_name].find({}).sort("timestamp", ASCENDING))