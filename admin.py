import streamlit as st
import os
from pymongo import MongoClient
from dotenv import load_dotenv
import bcrypt
from bson import ObjectId, json_util
import json
import re
import time
import logging
import extra_streamlit_components as stx
from auth.MongoAuthenticator import MongoAuthenticator, User
# # Set up logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
st.set_page_config(page_title="Admin Dashboard", layout="wide")
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
    return stx.CookieManager(key="mongo_auth_cookie_manager")

cookie_manager = get_cookie_manager()

authenticator = MongoAuthenticator(
    users_collection=users_collection,
    cookie_name='EMMA_auth_cookie',
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
    users = users_collection.find({}, {"username": 1, "email": 1, "name": 1})
    
    for user in users:
        with st.expander(f"{user['name']} ({user['username']})"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Email:** {user['email']}")
            with col2:
                st.write(f"**Username:** {user['username']}")
            
            action_col1, action_col2, action_col3 = st.columns(3)
            
            with action_col1:
                if st.button("Change Password", key=f"change_pwd_{user['_id']}"):
                    change_password(user['username'])
            
            with action_col2:
                if st.button("Reset Password", key=f"reset_pwd_{user['_id']}"):
                    reset_password(user['username'], user['email'])
            
            with action_col3:
                if st.button("Delete User", key=f"delete_{user['_id']}"):
                    delete_user(user['_id'])

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
    if st.button(f"Confirm Delete User"):
        users_collection.delete_one({"_id": user_id})
        st.success("User deleted successfully")
        st.rerun()

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
    select_all = st.checkbox("Select All")
    
    # Create a dictionary to store the state of each session checkbox
    if 'session_checkboxes' not in st.session_state:
        st.session_state.session_checkboxes = {session: False for session in filtered_sessions}
    
    # Update checkbox states if "Select All" is clicked
    if select_all:
        for session in filtered_sessions:
            st.session_state.session_checkboxes[session] = True
    
    # Display sessions with checkboxes
    selected_sessions = []
    for session in filtered_sessions:
        col1, col2 = st.columns([3, 1])
        with col1:
            checkbox = st.checkbox(session, value=st.session_state.session_checkboxes[session], key=f"checkbox_{session}")
            st.session_state.session_checkboxes[session] = checkbox
            if checkbox:
                selected_sessions.append(session)
        with col2:
            if st.button("View", key=f"view_{session}"):
                view_session(session)
    
    # Delete selected sessions
    if st.button("Delete Selected Sessions"):
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
    documents = collection.find()
    for doc in documents:
        st.json(doc)
     
def delete_session(session_name):
    if st.button("Confirm Delete Session"):
        db.drop_collection(session_name)
        st.success(f"Session {session_name} deleted successfully")
        time.sleep(1)
        st.rerun()

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



    if st.button(f"Confirm Delete User"):
        users_collection.delete_one({"_id": user_id})
        st.success("User deleted successfully")
        st.rerun()