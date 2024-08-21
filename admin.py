import streamlit as st
st.set_page_config(page_title="Admin Dashboard", layout="wide")
import os
from pymongo import MongoClient
from dotenv import load_dotenv
# import bcrypt
from bson import ObjectId, json_util
import json
# import re
import time
import logging
import pandas as pd
from datetime import datetime
import extra_streamlit_components as stx
from auth.MongoAuthenticator import MongoAuthenticator, User
# # Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# MongoDB connection
MONGODB_URI = os.getenv('MONGODB_ATLAS_URI')
DB_NAME = 'emma-dev'

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
users_collection = db['users']

# Admin credentials (in a real-world scenario, store these securely)
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD_HASH')

def get_cookie_manager():
    return stx.CookieManager(key="admin_mongo_auth_cookie_manager")

cookie_manager = get_cookie_manager()

authenticator = MongoAuthenticator(
    users_collection=users_collection,
    cookie_name='EMMA_admin_auth_cookie',  # Changed this to be unique for admin
    cookie_expiry_days=30,
    cookie_manager=cookie_manager 
)


# Initialize session state
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False
if 'edit_user' not in st.session_state:
    st.session_state.edit_user = None

def admin_login():
    st.title("Admin Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == ADMIN_USERNAME and ADMIN_PASSWORD_HASH:
            st.session_state.admin_authenticated = True
            st.success("Logged in successfully!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Invalid credentials")

def logout():
    st.session_state.admin_authenticated = False
    st.session_state.edit_user = None
    st.rerun()

def edit_user(user_id):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if user:
        st.subheader(f"Edit User: {user['username']}")
        new_role = st.selectbox("Role", ["user", "admin"], index=0 if user['role'] == "user" else 1)
        if st.button("Update Role"):
            users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": {"role": new_role}})
            st.success("User role updated successfully")
            st.session_state.edit_user = None
            st.rerun()


def user_management():
    st.header("User Management")
    
    # Create user section
    with st.expander("Create New User"):
        create_user()
    
    # User list with inline actions
    list_users()

def create_user():
    st.subheader("Create User")
    with st.form("create_user_form"):
        username = st.text_input("Username")
        name = st.text_input("Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Create User"):
            if authenticator.register_user(username, name, password, email):
                st.success("User created successfully")
                st.rerun()
            else:
                st.error("Username or email already exists")


def list_users():
    st.subheader("User List")
    
    # Fetch all users with the required fields
    users = list(users_collection.find({}, {
        "username": 1, 
        "email": 1, 
        "name": 1, 
        "login_count": 1, 
        "sessions_count": 1, 
        "last_active": 1
    }))
    
    # Prepare data for the table
    user_data = []
    for user in users:
        last_active = user.get('last_active', 'Never')
        if isinstance(last_active, datetime):
            last_active = last_active.strftime('%Y-%m-%d %H:%M:%S')
        
        user_data.append({
            "Name": user['name'],
            "Username": user['username'],
            "Email": user['email'],
            "Logins": user.get('login_count', 0),
            "Sessions": user.get('sessions_count', 0),
            "Last Active": last_active,
            "Change Password": user['_id'],
            "Reset Password": user['_id'],
            "Delete User": user['_id']
        })
    
    # Create a DataFrame
    df = pd.DataFrame(user_data)

    row_spacing = [1.5, 1.5, 2, 1, 1, 1.5, 1, 1, 1]
    # Add a header row
    header_cols = st.columns(row_spacing)
    headers = ["Name", "Username", "Email", "Logins", "Sessions", "Last Active", "Change", "Reset", "Delete"]
    for i, header in enumerate(headers):
        header_cols[i].write(f"**{header}**")
    # Display the table with action buttons
    for index, row in df.iterrows():
        cols = st.columns(row_spacing)
        cols[0].write(row['Name'])
        cols[1].write(row['Username'])
        cols[2].write(row['Email'])
        cols[3].write(row['Logins'])
        cols[4].write(row['Sessions'])
        cols[5].write(row['Last Active'])
        if cols[6].button("Change", key=f"change_{row['Change Password']}"):
            change_password(row['Username'])
        if cols[7].button("Reset", key=f"reset_{row['Reset Password']}"):
            reset_password(row['Username'], row['Email'])
        if cols[8].button("Delete", key=f"delete_{row['Delete User']}"):
            if delete_user(row['Delete User']):
                st.session_state.user_deleted = True
                st.rerun()

    
    

def change_password(username):
    st.subheader(f"Change Password for {username}")
    with st.form(f"change_password_form_{username}"):
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        if st.form_submit_button("Change Password"):
            if authenticator.change_password(username, current_password, new_password):
                st.success("Password changed successfully")
            else:
                st.error("Invalid current password")

def reset_password(username, email):
    if st.button(f"Confirm Reset Password for {username}"):
        new_password = authenticator.reset_password(username, email)
        if new_password:
            st.success(f"Password reset successfully. New password: {new_password}")
            st.warning("Please change this password after logging in.")
        else:
            st.error("Failed to reset password")

def delete_user(user_id):
    try:
        result = users_collection.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count == 1:
            st.success(f"User with ID {user_id} deleted successfully")
            return True
        else:
            st.error(f"No user found with ID {user_id}")
            return False
    except Exception as e:
        st.error(f"An error occurred while deleting the user: {str(e)}")
        return False
def list_sessions():
    st.subheader("Session Management")
    
    # Get all unique usernames from session collections
    collections = db.list_collection_names()
    sessions = [col for col in collections if col.startswith('user_')]
    usernames = list(set([session.split('_')[1] for session in sessions]))
    usernames.sort()
    
    # Filter by user
    selected_user = st.selectbox("Filter by User", ["All Users"] + usernames)
    
    # Filter sessions based on selected user
    if selected_user == "All Users":
        filtered_sessions = sessions
    else:
        filtered_sessions = [session for session in sessions if session.split('_')[1] == selected_user]
    
    # Select all checkbox
    select_all = st.checkbox("Select All", key="select_all_checkbox")
    
    # Create a dictionary to store the state of each session checkbox
    if 'session_checkboxes' not in st.session_state:
        st.session_state.session_checkboxes = {session: False for session in filtered_sessions}
    
    # Update checkbox states if "Select All" is clicked
    if select_all:
        for session in filtered_sessions:
            st.session_state.session_checkboxes[session] = True
    
    # Display sessions with patient CC, checkboxes, and toggle for viewing
    selected_sessions = []
    
    # Create a container for the session list
    session_container = st.container()

    # Create a container for the session list
    session_container = st.container()
    
    with session_container:
        for session in filtered_sessions:
            col1, col2, col3, col4, col5 = st.columns([0.5, 2, 2, .5,.5])
            
            with col1:
                checkbox = st.checkbox(
                    label=f"Select {session}",
                    value=st.session_state.session_checkboxes[session],
                    key=f"checkbox_{session}",
                    label_visibility="collapsed"
                )
                st.session_state.session_checkboxes[session] = checkbox
                if checkbox:
                    selected_sessions.append(session)
            
            with col2:
                st.write(session)
            
            with col3:
                # Fetch and display patient CC
                patient_cc = get_patient_cc(session)
                st.write(patient_cc)
            
            with col4:
                view_toggle = st.toggle(
                    label=f"View {session}",
                    key=f"toggle_{session}",
                    label_visibility="collapsed"
                )
            
            with col5:
                if st.button("Delete", key=f"delete_{session}"):
                    delete_session(session)
            
            # View session details when toggled
            if view_toggle:
                view_session(session)
    
    # Delete selected sessions
    if selected_sessions and st.button("Delete Selected Sessions"):
        st.session_state.confirm_delete = True
        st.session_state.sessions_to_delete = selected_sessions

    # Confirm deletion
    if 'confirm_delete' in st.session_state and st.session_state.confirm_delete:
        st.warning(f"Are you sure you want to delete the following sessions?\n{', '.join(st.session_state.sessions_to_delete)}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirm Delete"):
                delete_sessions(st.session_state.sessions_to_delete)
        with col2:
            if st.button("Cancel"):
                st.session_state.confirm_delete = False
                st.session_state.sessions_to_delete = []
        with col3:
            # Fetch and display patient CC
            patient_cc = get_patient_cc(session)
            st.write(patient_cc)
        
        with col4:
            if f"view_{session}" not in st.session_state:
                st.session_state[f"view_{session}"] = False
            st.session_state[f"view_{session}"] = st.toggle("View", key=f"toggle_{session}")
        
        with col5:
            if st.button("Delete", key=f"delete_{session}"):
                delete_session(session)
        # View session details when toggled
        if st.session_state[f"view_{session}"]:
            view_session(session)

    # Delete selected sessions
    if st.button("Delete Selected Sessions", key="delete_selected_sessions_button"):
        st.session_state.confirm_delete = True
        st.session_state.sessions_to_delete = selected_sessions

    # Confirm deletion
    if 'confirm_delete' in st.session_state and st.session_state.confirm_delete:
        st.warning(f"Are you sure you want to delete the following sessions?\n{', '.join(st.session_state.sessions_to_delete)}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirm Delete", key="confirm_delete_button"):
                delete_sessions(st.session_state.sessions_to_delete)
        with col2:
            if st.button("Cancel", key="cancel_delete_button"):
                st.session_state.confirm_delete = False
                st.session_state.sessions_to_delete = []

def delete_sessions(session_names):
    deleted_sessions = []
    failed_deletions = []
    
    for session_name in session_names:
        try:
            db.drop_collection(session_name)
            deleted_sessions.append(session_name)
            logger.info(f"Deleted session: {session_name}")
        except Exception as e:
            failed_deletions.append(session_name)
            logger.error(f"Failed to delete session {session_name}: {str(e)}")
    
    if deleted_sessions:
        st.success(f"Successfully deleted the following sessions: {', '.join(deleted_sessions)}")
    
    if failed_deletions:
        st.error(f"Failed to delete the following sessions: {', '.join(failed_deletions)}")
    
    # Reset checkbox states for deleted sessions
    for session in deleted_sessions:
        if session in st.session_state.session_checkboxes:
            del st.session_state.session_checkboxes[session]
    
    # Reset confirmation state
    st.session_state.confirm_delete = False
    st.session_state.sessions_to_delete = []
    
    # Rerun the app to refresh the session list
    time.sleep(1)  # Give user time to see the message
    st.rerun()

def view_session(session_name):
    st.subheader(f"Session Details: {session_name}")
    collection = db[session_name]
    
    # Find the most recent chat_history document
    chat_history = collection.find_one({"type": "chat_history"}, sort=[("timestamp", -1)])
    
    if chat_history:
        patient_cc = chat_history.get("patient_cc", "No chief complaint found")
        st.write(f"Patient's Chief Complaint: {patient_cc}")
    
    # Display other session details
    documents = collection.find()
    for doc in documents:
        st.json(doc)
     
def delete_session(session_name):
    try:
        db.drop_collection(session_name)
        return True
    except Exception as e:
        st.error(f"Error deleting session {session_name}: {str(e)}")
        return False

def query_documents():
    st.subheader("Query Documents")
    
    collection_name = st.selectbox("Select Collection", db.list_collection_names())
    
    # Get the first document to extract field names
    sample_doc = db[collection_name].find_one()
    if not sample_doc:
        st.warning("The selected collection is empty.")
        return
    
    fields = list(sample_doc.keys())
    
    # Query builder
    st.subheader("Build Your Query")
    conditions = []
    
    col1, col2, col3 = st.columns(3)
    with col1:
        field = st.selectbox("Field", fields)
    with col2:
        operator = st.selectbox("Operator", ["equals", "not equals", "greater than", "less than", "contains"])
    with col3:
        value = st.text_input("Value")
    
    if st.button("Add Condition"):
        conditions.append((field, operator, value))
    
    # Display current conditions
    if conditions:
        st.subheader("Current Query Conditions")
        for i, (f, o, v) in enumerate(conditions):
            st.write(f"{i+1}. {f} {o} {v}")
        
        if st.button("Clear All Conditions"):
            conditions.clear()
    
    # Sorting
    st.subheader("Sort Results")
    sort_field = st.selectbox("Sort by", [""] + fields)
    sort_order = st.radio("Sort Order", ["Ascending", "Descending"])
    
    # Limit results
    limit = st.number_input("Limit results", min_value=1, max_value=1000, value=10)
    
    if st.button("Execute Query"):
        # Build the query
        query = {}
        for field, operator, value in conditions:
            if operator == "equals":
                query[field] = value
            elif operator == "not equals":
                query[field] = {"$ne": value}
            elif operator == "greater than":
                query[field] = {"$gt": value}
            elif operator == "less than":
                query[field] = {"$lt": value}
            elif operator == "contains":
                query[field] = {"$regex": value, "$options": "i"}
        
        # Execute the query
        try:
            if sort_field:
                sort_dict = {sort_field: 1 if sort_order == "Ascending" else -1}
                results = db[collection_name].find(query).sort(sort_dict).limit(limit)
            else:
                results = db[collection_name].find(query).limit(limit)
            
            # Convert results to a list and use json_util for BSON conversion
            results_list = list(results)
            json_results = json.loads(json_util.dumps(results_list))
            
            # Display results in a more readable format
            st.subheader("Query Results")
            for doc in json_results:
                st.json(doc)
            
            st.info(f"Showing {len(json_results)} results")
            
        except Exception as e:
            st.error(f"Error executing query: {str(e)}")

def update_document():
    st.subheader("Update Document")
    collection_name = st.selectbox("Select Collection", db.list_collection_names())
    doc_id = st.text_input("Enter document ID")
    update_query = st.text_area("Enter update query (JSON format)")
    if st.button("Update Document"):
        try:
            update_dict = json.loads(update_query)
            result = db[collection_name].update_one({"_id": ObjectId(doc_id)}, {"$set": update_dict})
            if result.modified_count > 0:
                st.success("Document updated successfully")
            else:
                st.warning("No document was updated")
        except Exception as e:
            st.error(f"Error updating document: {str(e)}")

def database_operations():
    st.header("Database Operations")
    operation = st.radio("Select Operation", ["Query Documents", "Update Document"])
    
    if operation == "Query Documents":
        query_documents()
    else:
        update_document()

def get_patient_cc(session_name):
    collection = db[session_name]
    chat_history = collection.find_one({"type": "chat_history"}, sort=[("timestamp", -1)])
    
    if chat_history:
        return chat_history.get("patient_cc", "No CC found")
    return "No chat history"

def main():

    
    if not authenticator.is_authenticated():
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            name, authentication_status, username = authenticator.login(username, password)
            if authentication_status:
                st.success(f"Welcome {name}!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    else:
        st.title("Admin Dashboard")
        st.sidebar.title("Navigation")
        page = st.sidebar.radio("Go to", ["User Management", "Session Management", "Database Operations"])
        
        if st.sidebar.button("Logout"):
            authenticator.logout()
            st.rerun()
        
        if page == "User Management":
            user_management()
        elif page == "Session Management":
            list_sessions()
        elif page == "Database Operations":
            database_operations()

if __name__ == "__main__":
    main()
