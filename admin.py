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
import datetime
import extra_streamlit_components as stx
from auth.MongoAuthenticator import MongoAuthenticator, User

# Configure logger
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

def admin_dashboard():
    st.title("Admin Dashboard")
    
    page = st.sidebar.radio("Go to", ["User Management", "Session Management", "Database Operations", "Feedback Management"])
    
    if page == "User Management":
        user_management()
    elif page == "Session Management":
        list_sessions()
    elif page == "Database Operations":
        database_operations()
    elif page == "Feedback Management":
        feedback_management()
    
    if st.sidebar.button("Delete Old Sessions"):
        if st.session_state.get('confirm_delete_old', False):
            delete_old_sessions()
            st.session_state.confirm_delete_old = False
        else:
            st.session_state.confirm_delete_old = True
            st.warning("Are you sure you want to delete all sessions older than 2 weeks? This action cannot be undone.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Confirm Delete Old Sessions"):
                    delete_old_sessions()
                    st.session_state.confirm_delete_old = False
            with col2:
                if st.button("Cancel Delete Old Sessions"):
                    st.session_state.confirm_delete_old = False
            time.sleep(1)  # Give user time to see the message
            st.rerun()


    if st.sidebar.button("Exit Admin Mode", key="exit_admin_mode"):
        st.rerun()  # This will refresh the page and exit admin mode

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
        "sessions_created": 1, 
        "last_active": 1
    }))
    
    # Prepare data for the table
    user_data = []
    for user in users:
        last_active = user.get('last_active', 'Never')
        if isinstance(last_active, datetime.datetime):
            last_active = last_active.strftime('%Y-%m-%d %H:%M:%S')
        
        user_data.append({
            "Name": user['name'],
            "Username": user['username'],
            "Email": user['email'],
            "Logins": user.get('login_count', 0),
            "Sessions": user.get('sessions_created', 0),
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
    
    # Date filter
    st.subheader("Filter by Date")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date")
    with col2:
        end_date = st.date_input("End Date")
    
    # Document count filter
    st.subheader("Filter by Document Count")
    col1, col2 = st.columns(2)
    with col1:
        min_docs = st.number_input("Minimum Documents", min_value=0, value=0)
    with col2:
        max_docs = st.number_input("Maximum Documents", min_value=0, value=1000)
    
    # Filter sessions based on selected user, date range, and document count
    filtered_sessions = []
    for session in sessions:
        if selected_user == "All Users" or session.split('_')[1] == selected_user:
            doc_count = db[session].count_documents({})
            if min_docs <= doc_count <= max_docs:
                latest_doc = db[session].find_one(sort=[("timestamp", -1)])
                if latest_doc and 'timestamp' in latest_doc:
                    session_date = latest_doc['timestamp'].date()
                    if start_date <= session_date <= end_date:
                        filtered_sessions.append((session, doc_count, session_date))
    
    # Sort sessions by date (newest first)
    filtered_sessions.sort(key=lambda x: x[2], reverse=True)
    
    # Initialize session state for checkboxes if not exists
    if 'session_checkboxes' not in st.session_state:
        st.session_state.session_checkboxes = {}
    
    # Select All checkbox
    select_all = st.checkbox("Select All", key="select_all_checkbox")
    
    

    # Display sessions
    st.subheader("Sessions")
    for i, (session, doc_count, session_date) in enumerate(filtered_sessions):
        col1, col2, col3, col4, col5, col6 = st.columns([0.5, 2, 2, 1, 1, 1])
        
        with col1:
            # Use select_all value if it's checked, otherwise use the existing checkbox state
            checkbox_value = select_all or st.session_state.session_checkboxes.get(session, False)
            checkbox = st.checkbox("", key=f"checkbox_{i}", value=checkbox_value)
            st.session_state.session_checkboxes[session] = checkbox
        
        with col2:
            st.write(session)
        
        with col3:
            st.write(f"Date: {session_date}")
        
        with col4:
            st.write(f"Documents: {doc_count}")
        
        with col5:
            if st.button("View", key=f"view_{i}"):
                st.session_state.viewing_session = session
        
        with col6:
            if st.button("Delete", key=f"delete_{i}"):
                if delete_session(session):
                    st.success(f"Deleted session: {session}")
                    time.sleep(1)
                    st.rerun()
    
    # View session details
    if 'viewing_session' in st.session_state:
        view_session(st.session_state.viewing_session)
        if st.button("Close View"):
            del st.session_state.viewing_session
    
    # Delete selected sessions
    selected_sessions = [session for session, checked in st.session_state.session_checkboxes.items() if checked]
    if selected_sessions:
        if st.button("Delete Selected Sessions"):
            st.session_state.confirm_delete = True
            st.session_state.sessions_to_delete = selected_sessions

    # Confirm deletion
    if st.session_state.get('confirm_delete', False):
        st.warning(f"Are you sure you want to delete the following sessions?\n{', '.join(st.session_state.sessions_to_delete)}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirm Delete"):
                delete_sessions(st.session_state.sessions_to_delete)
                st.session_state.confirm_delete = False
                st.session_state.sessions_to_delete = []
                # Clear checkboxes for deleted sessions
                for session in selected_sessions:
                    if session in st.session_state.session_checkboxes:
                        del st.session_state.session_checkboxes[session]
                st.success("Selected sessions deleted successfully.")
                time.sleep(1)
                st.rerun()
        with col2:
            if st.button("Cancel"):
                st.session_state.confirm_delete = False
                st.session_state.sessions_to_delete = []
                st.rerun()


def delete_old_sessions(weeks=1):
    two_weeks_ago = datetime.datetime.now() - datetime.timedelta(weeks=weeks)
    eligible_sessions = []
    
    collections = db.list_collection_names()
    for collection_name in collections:
        if collection_name.startswith('user_'):
            latest_doc = db[collection_name].find_one(sort=[("timestamp", -1)])
            if latest_doc and 'timestamp' in latest_doc:
                if latest_doc['timestamp'] < two_weeks_ago:
                    eligible_sessions.append(collection_name)
    
    if eligible_sessions:
        st.warning(f"The following sessions are eligible for deletion: {', '.join(eligible_sessions)}")
        if st.button("Confirm Delete Old Sessions"):
            deleted_sessions = []
            failed_deletions = []
            for collection_name in eligible_sessions:
                try:
                    db.drop_collection(collection_name)
                    deleted_sessions.append(collection_name)
                    logger.info(f"Deleted old session: {collection_name}")
                except Exception as e:
                    failed_deletions.append(collection_name)
                    logger.error(f"Failed to delete old session {collection_name}: {str(e)}")
            
            if deleted_sessions:
                st.success(f"Successfully deleted {len(deleted_sessions)} old sessions.")
            if failed_deletions:
                st.error(f"Failed to delete {len(failed_deletions)} old sessions.")
            
            st.rerun()
    else:
        st.info("No sessions eligible for deletion.")

def delete_small_old_sessions(days=5, min_docs=5):
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
    eligible_sessions = []
    
    collections = db.list_collection_names()
    for collection_name in collections:
        if collection_name.startswith('user_'):
            latest_doc = db[collection_name].find_one(sort=[("timestamp", -1)])
            doc_count = db[collection_name].count_documents({})
            if latest_doc and 'timestamp' in latest_doc:
                if latest_doc['timestamp'] < cutoff_date and doc_count < min_docs:
                    eligible_sessions.append((collection_name, doc_count, latest_doc['timestamp']))
    
    if eligible_sessions:
        st.warning("The following sessions are eligible for deletion:")
        for session, doc_count, last_active in eligible_sessions:
            st.write(f"Session: {session}, Documents: {doc_count}, Last Active: {last_active}")
        
        if st.button("Confirm Delete Small Old Sessions"):
            deleted_sessions = []
            failed_deletions = []
            for session, _, _ in eligible_sessions:
                try:
                    db.drop_collection(session)
                    deleted_sessions.append(session)
                    logger.info(f"Deleted old session: {session}")
                except Exception as e:
                    failed_deletions.append(session)
                    logger.error(f"Failed to delete old session {session}: {str(e)}")
            
            if deleted_sessions:
                st.success(f"Successfully deleted {len(deleted_sessions)} old sessions.")
            if failed_deletions:
                st.error(f"Failed to delete {len(failed_deletions)} old sessions.")
            
            st.rerun()
    else:
        st.info("No sessions eligible for deletion.")


def view_session(session_name):
    st.subheader(f"Session Details: {session_name}")
    collection = db[session_name]
    
    # Find the most recent chat_history document
    chat_history = collection.find_one({"type": "chat_history"}, sort=[("timestamp", -1)])
    
    if chat_history:
        st.write("Chat History:")
        st.json(chat_history)
    
    # Find the most recent ddx document
    ddx = collection.find_one({"type": "ddx"}, sort=[("timestamp", -1)])
    
    if ddx:
        st.write("Differential Diagnosis:")
        st.json(ddx)
    
    # Find notes by the Note Writer
    notes = list(collection.find({"specialist": "Note Writer"}))
    
    if notes:
        st.write("Notes by Note Writer:")
        for note in notes:
            st.json(note)
    
    if st.button("Close Session View"):
        del st.session_state.viewing_session
        st.rerun()

def delete_session(session_name):
    try:
        db.drop_collection(session_name)
        return True
    except Exception as e:
        st.error(f"Error deleting session {session_name}: {str(e)}")
        return False

def delete_sessions(session_names):
    deleted_sessions = []
    failed_deletions = []
    
    for session_name in session_names:
        try:
            db.drop_collection(session_name)
            deleted_sessions.append(session_name)
            # Remove the deleted session from session_checkboxes
            if session_name in st.session_state.session_checkboxes:
                del st.session_state.session_checkboxes[session_name]
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

def feedback_management():
    st.header("Feedback Management")
    
    # Fetch all feedback from the database
    feedback_collection = db['feedback']
    all_feedback = list(feedback_collection.find().sort("timestamp", -1))
    
    # Filter options
    st.subheader("Filter Feedback")
    col1, col2 = st.columns(2)
    with col1:
        filter_date = st.date_input("Filter by date", value=None)
    with col2:
        filter_type = st.selectbox("Filter by feedback type", ["All", "😃 Great", "😐 Okay", "☹️ Poor"])
    
    # Apply filters
    filtered_feedback = all_feedback
    if filter_date:
        filtered_feedback = [f for f in filtered_feedback if f['timestamp'].date() == filter_date]
    if filter_type != "All":
        filtered_feedback = [f for f in filtered_feedback if f['feedback_type'] == filter_type]
    
    # Display feedback
    st.subheader("Feedback List")
    for feedback in filtered_feedback:
        try:
            timestamp = feedback.get('timestamp', 'Unknown Date')
            user_id = feedback.get('user_id', 'Unknown User')
            
            if isinstance(timestamp, datetime.datetime):
                timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            else:
                timestamp_str = str(timestamp)
            
            with st.expander(f"Feedback from {user_id} on {timestamp_str}"):
                
                if 'raw_feedback' in feedback:
                    st.subheader("Raw Feedback:")
                    st.write(feedback['raw_feedback'])
                elif 'feedback_text' in feedback:
                    st.write("Feedback Text:")
                    st.write(feedback['feedback_text'])
                else:
                    st.write("No raw feedback available")
                st.divider()
                if 'processed_feedback' in feedback:
                    st.subheader("Processed Feedback:")
                    st.write(feedback['processed_feedback'])
                else:
                    st.write("No processed feedback available")
                
                # Option to delete feedback
                if st.button("Delete Feedback", key=f"delete_{feedback['_id']}"):
                    if delete_feedback(feedback['_id']):
                        st.success("Feedback deleted successfully")
                        time.sleep(1)
                        st.rerun()
        except Exception as e:
            st.error(f"Error displaying feedback: {str(e)}")
    
    # Export feedback
    if st.button("Export Feedback to CSV"):
        export_feedback_to_csv(filtered_feedback)

def delete_feedback(feedback_id):
    try:
        result = db['feedback'].delete_one({"_id": feedback_id})
        return result.deleted_count > 0
    except Exception as e:
        st.error(f"Error deleting feedback: {str(e)}")
        return False

def export_feedback_to_csv(feedback_data):
    df = pd.DataFrame(feedback_data)
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="feedback_export.csv",
        mime="text/csv",
    )

def delete_feedback(feedback_id):
    try:
        result = db['feedback'].delete_one({"_id": feedback_id})
        return result.deleted_count > 0
    except Exception as e:
        st.error(f"Error deleting feedback: {str(e)}")
        return False

def export_feedback_to_csv(feedback_data):
    df = pd.DataFrame(feedback_data)
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="feedback_export.csv",
        mime="text/csv",
    )

def main():
    # Check if the function has been run today
    if 'last_cleanup' not in st.session_state or st.session_state.last_cleanup.date() < datetime.datetime.now().date():
        delete_small_old_sessions(days=5, min_docs=3)
        st.session_state.last_cleanup = datetime.datetime.now()

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
    # This allows the admin.py to be run standalone for testing
    # if st.sidebar.button("Exit Admin Mode"):
    #     st.rerun()  # This will refresh the page and exit admin mode
    admin_dashboard()
    # delete_old_sessions(weeks=1)
    main()
