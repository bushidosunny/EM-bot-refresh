import streamlit as st
from streamlit_float import float_css_helper

from openai import OpenAI
from langchain_core.messages import HumanMessage, AIMessage
import os
import io
from dotenv import load_dotenv
from prompts import *
import json
from extract_json import extract_json, create_json
from datetime import datetime
import pytz
from login import *

# Load variables
load_dotenv()
ema_v2 = "asst_na7TnRA4wkDbflTYKzo9kmca"
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("API Key not found! Please check your environment variables.")
legal_attorney = "asst_ZI3rML4v8eG1vhQ3Fis5ikOd"
note_writer = 'asst_Ua6cmp6dpTc33cSpuZxutGsX'

client = OpenAI(api_key=api_key)

# Define the avatar URLs
user_avatar_url = "https://cdn.pixabay.com/photo/2016/12/21/07/36/profession-1922360_1280.png"

specialist_id_caption = {
  "Emergency Medicine": {
    "assistant_id": "asst_na7TnRA4wkDbflTYKzo9kmca",
    "caption": "EM, Peds EM, Toxicology, Wilderness",
    "avatar": "https://cdn.pixabay.com/photo/2017/03/31/23/11/robot-2192617_1280.png"
  },
  "Neurological": {
    "assistant_id": "asst_caM9P1caoAjFRvSAmT6Y6mIz",
    "caption": "Neurology, Neurosurgery, Psychiatry",
    "avatar": "https://cdn.pixabay.com/photo/2018/11/21/02/04/graphic-3828723_1280.png"
  },
  "Sensory Systems (Eyes, Ears, Nose, Throat)": {
    "assistant_id": "asst_UB1VTD6NyYbb1xTrUueb3xlI",
    "caption": "Ophthalmology, ENT",
    "avatar": "https://cdn.imgbin.com/17/1/11/imgbin-mr-potato-head-toy-child-infant-computer-icons-toy-GdJDP1cicFXdWJHbgSanRhnFQ.jpg"
  },
  "Cardiovascular and Respiratory": {
    "assistant_id": "asst_bH6wKFfCMVBiH3yUkM0DWdFk",
    "caption": "Cardiology, Cardiovascular Surgery, Vascular Surgery, Pulmonology, Thoracic Surgery",
    "avatar": "https://cdn.pixabay.com/photo/2017/02/15/20/58/ekg-2069872_1280.png"
  },
  "Gastrointestinal Systems": {
    "assistant_id": "asst_Z6bVfy6eOZBVdiwoS75eGdG9",
    "caption": "Gastroenterology, Hepatology, Colorectal Surgery, General Surgery",
    "avatar": "https://cdn.pixabay.com/photo/2017/03/27/03/08/stomach-2177194_1280.png"
  },
  "Renal and GU Systems": {
    "assistant_id": "asst_SV4dNDe8sX0drryIVhQFeJj3",
    "caption": "Nephrology, Gynecology, Urology, Obstetrics",
    "avatar": "https://cdn.pixabay.com/photo/2022/09/20/10/27/urology-7467570_960_720.png"
  },
  "Dermatology and Plastic Surgery": {
    "assistant_id": "asst_HzMNSMBEDBa3G6ABSISqu08e",
    "caption": "Dermatology, Plastic Surgery",
    "avatar": "https://media.istockphoto.com/id/1325453968/vector/skin-layers-structure-anatomy-diagram-human-skin-infographic-anatomical-background.jpg?s=2048x2048&w=is&k=20&c=gr7MHjhjyVZgjQhh4TyabN1gZWnxF1WlB33Ul-mr6b4="
  },
  "Musculoskeletal Systems": {
    "assistant_id": "asst_d9cMY1Sxwz0dUsKJXjuZMoiM",
    "caption": "Sports Med, Orthopedics, PM&R, Rheumatology, Physical Therapy",
    "avatar": "https://cdn.pixabay.com/photo/2015/12/09/22/19/muscle-1085672_1280.png"
  },
  "General": {
    "assistant_id": "asst_K2QHe4VfHGdyrrfTCiyctzyY",
    "caption": "ICU, Internal Medicine, HemOnc, Endocrinology",
    "avatar": "https://cdn.pixabay.com/photo/2013/07/12/18/59/doctor-154130_1280.png"
  },
  "Pediatrics": {
    "assistant_id": "asst_cVQwzy87fwOvTnb66zsvVB5L",
    "caption": "Pediatrics, Neonatology, Pediatric Surgery",
    "avatar": "https://cdn.pixabay.com/photo/2013/07/12/14/15/man-148077_1280.png"
  },
  "Infectious Disease": {
    "assistant_id": "asst_40hUiBxEhoylT6dCEqhssCiI",
    "caption": "Infectious Disease, Epidemiology",
    "avatar": "https://cdn.pixabay.com/photo/2020/04/18/08/33/coronavirus-5058247_1280.png"
  }, 
  "Medical Legal": {
    "assistant_id": "asst_ZI3rML4v8eG1vhQ3Fis5ikOd",
    "caption": "Legal Consultant",
    "avatar": "https://cdn.pixabay.com/photo/2017/01/31/17/34/comic-characters-2025788_1280.png"
  },
  "Note Writer": {
    "assistant_id": "asst_Ua6cmp6dpTc33cSpuZxutGsX",
    "caption": "Medical Note Writer",
    "avatar": "https://cdn.pixabay.com/photo/2012/04/25/00/26/writing-41354_960_720.png"
  },  
  "Note Summarizer": {
    "assistant_id": "asst_c2lPEtkLRILNyl5K7aJ0R38o",
    "caption": "Medical Note Summarizer",
    "avatar": "https://cdn.pixabay.com/photo/2012/04/25/00/26/writing-41354_960_720.png"
  },
  "Patient Educator": {
    "assistant_id": "asst_twf42nzGoYLtrHAZeENLcI5d",
    "caption": "Pt education Note Writer",
    "avatar": "https://cdn.pixabay.com/photo/2012/04/25/00/26/writing-41354_960_720.png"
  },
  "Bayesian Reasoner": {
    "assistant_id": "asst_GeAw2bIhrATHejogynMmP2VB",
    "caption": "EM - Beta testing",
    "avatar": "https://cdn.pixabay.com/photo/2013/07/12/14/33/carrot-148456_960_720.png"
  },
  "Clinical Decision Tools": {
    "assistant_id": "asst_Pau6T5mMH3cZBnEePso5kFuJ",
    "caption": "Goes Deep",
    "avatar": "https://cdn.pixabay.com/photo/2019/07/02/05/54/tool-4311573_1280.png"
  }
}

# Initialize session_state variables
def initialize_session_state():
    state_keys_defaults = {
        "authentication_status": None,
        "logout": None,
        "name": "",
        "username": "",
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
        "completed_tasks_str": ""

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
        print(f'DEBUG: Initial specialist set to {primary_specialist}')

# Setup the main page display and header
def display_header():
    if st.session_state.pt_data != {}:
        cc = st.session_state.pt_data['patient']["chief_complaint_two_word"]
        age = st.session_state.pt_data['patient']["age"]
        age_units = st.session_state.pt_data['patient']["age_unit"]
        sex = st.session_state.pt_data['patient']["sex"]
        st.set_page_config(page_title=f"{age}{age_units}{sex} {cc}", page_icon="🤖")
    else:
        st.set_page_config(page_title=f"EMA", page_icon="🤖")
    st.header("EMA - Emergency Medicine Assistant 🤖🩺")

def display_critical_tasks():
    if st.session_state.critical_actions:
        st.subheader(":orange[Critical Actions]")
        # Create a dictionary to hold the status of each task
        task_status = {task: False for task in st.session_state.critical_actions}

        # Display the tasks with checkboxes
        for task in st.session_state.critical_actions:
            task_status[task] = st.checkbox(f"- :orange[{task}]", value=task_status[task])

        # Check which tasks are completed and save to a string variable
        completed_tasks = [task for task, status in task_status.items() if status]
        print (f'DEBUG COMPLETGED TASKS: {completed_tasks}')
        if completed_tasks != []:
            st.session_state.completed_tasks_str = "Tasks Completed:" + '.\n'.join(completed_tasks)



# Sidebar display
def display_sidebar():
    with st.sidebar:
        st.markdown("<h1 style='margin-top: -60px;text-align: center;'>EMA 🤖</h1>", unsafe_allow_html=True)
        
        tab1, tab2, tab3, tab4 = st.tabs(["Functions", "Specialists", "Note Analysis", "Update Variables"])
        
        with tab1:
            display_critical_tasks()
            
            if st.session_state.differential_diagnosis:
                st.subheader("Differential Diagnosis")
                for diagnosis in st.session_state.differential_diagnosis:
                    disease = diagnosis['disease']
                    probability = diagnosis['probability']
                    st.markdown(f"- {disease} - {probability}%")
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
        container = st.container()
        container.float(float_css_helper(bottom="10px"))
        with container:
            authenticate_user()
def consult_specialist_and_update_ddx(button_name, prompt):
    # Consult the specific specialist
    specialist = st.session_state.specialist
    button_input(specialist, prompt)

    # If necessary, temporarily switch to an EM agent
    if needs_em_update_for(button_name):
        temp_specialist = "Emergency Medicine"
        st.session_state.specialist = temp_specialist
        st.session_state.assistant_id = specialist_id_caption[temp_specialist]["assistant_id"]

        # Update ddx and plan with new information
        button_input(temp_specialist, integrate_consultation)

    # Resetting the specialist back if it was changed
    if st.session_state.specialist == temp_specialist:
        st.session_state.specialist = specialist

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
        button4 = st.button("Pt Education Note")
    with col2:
        button11 = st.button('HPI only')
        button12 = st.button('A&P only')
        button13 = st.button('Physical Therapy Plan')
        

    st.subheader('🏃‍♂️Flow')
    col1, col2 = st.columns(2)
    with col1:
        button5 = st.button("➡️Next Step Recommendation")
        button7 = st.button("DDX w Bayesian Reasoning")
    with col2:
        button6 = st.button('➡️➡️I did that, now what?')
        button8 = st.button('🛠️Apply Clinical Decision Tools')

    st.divider()
    col1, col2, col3 = st.columns([1,3,1])
    with col2:
        button9 = st.button('NEW THREAD', type="primary")
        #button10 = st.button('TEST')

    # Process button actions
    process_buttons(button1, button2, button3, button4, button5, button6, button7, button8, button9, button11, button12, button13, button14)

# Process the buttons
def process_buttons(button1, button2, button3, button4, button5, button6, button7, button8, button9, button11, button12, button13, button14):
    if button1:
        st.session_state["user_question"] = disposition_analysis
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
        prompt = "What should i do next here in the emergency department?"
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button6:
        specialist = 'Emergency Medicine'
        prompt = "Ok i did that. Now what?"
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
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
    specialist = st.radio("**:red[Choose Your Specialty Group]**", specialities, 
                          captions=captions, 
                          index=specialities.index(selected_specialist),
                          key="choose_specialist_radio")

    if 'button_clicked' not in st.session_state:
        st.session_state.button_clicked = False

    # Only update if the selected specialist is different
    if specialist and specialist != st.session_state.specialist:
    #if specialist and specialist != st.session_state.specialist and not st.session_state.button_clicked:
        print(f'DEBUG: Radio button changed specialist to {specialist}')
        st.session_state.specialist = specialist
        st.session_state.assistant_id = specialist_id_caption[specialist]["assistant_id"]
        st.session_state.specialist_avatar = specialist_id_caption[specialist]["avatar"]
        # No need to call st.rerun() here
        st.rerun()

# process button inputs for quick bot responses
def button_input(specialist, prompt):
    st.session_state.button_clicked = True
    #call the specialist
    st.session_state.assistant_id = specialist_id_caption[specialist]["assistant_id"]
 
    # set st.sesssion_state.user_question_sidebar for process_other_queries() 
    user_question = prompt
    if user_question is not None and user_question != "":
        st.session_state.specialist = specialist
        print(f'DEBUG: button input - ST-SESSION SPECIALIST : {st.session_state.specialist}')
        specialist_avatar = specialist_id_caption[st.session_state.specialist]["avatar"]
        st.session_state.specialist_avatar = specialist_avatar
        timezone = pytz.timezone("America/Los_Angeles")
        current_datetime = datetime.now(timezone).strftime("%H:%M:%S")
        user_question = current_datetime + f"""    \n{user_question}. 
        \n{st.session_state.completed_tasks_str}
        """
        st.session_state.user_question_sidebar = user_question
        print(f'DEBUG user_question: {user_question}')
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

        # set specialist_avatar for chat history
        specialist_avatar = specialist_id_caption[st.session_state.specialist]["avatar"]
        
        # set user_question to sidebar user_question
        user_question = st.session_state.user_question_sidebar
        with st.chat_message("user", avatar=user_avatar_url):
            st.markdown(user_question)

        # add querry to the chat history as human user
        st.session_state.chat_history.append(HumanMessage(user_question, avatar=user_avatar_url))

        #get ai response
        with st.chat_message("AI", avatar=specialist_avatar):
            assistant_response = get_response(user_question=user_question)
            #st.session_state.assistant_response = assistant_response

        #append ai response to chat_history
        st.session_state.chat_history.append(AIMessage(assistant_response, avatar=specialist_avatar))

        # session_state variable to make sure user_question is not repeated.
        st.session_state.old_user_question_sidebar = user_question

        chat_history = chat_history_string()
        print(f'DEBUG CHAT HISTORY: {chat_history}')
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

@st.cache_data
def handle_user_legal_input(legal_question):    
    # Append user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": legal_question, "avatar": user_avatar_url})
        
    client.beta.threads.messages.create(thread_id=st.session_state.thread_id, role="user", content=legal_question)

    with client.beta.threads.runs.stream(thread_id=st.session_state.thread_id, assistant_id=legal_attorney) as stream:
        assistant_response = "".join(generate_response_stream(stream))
        st.write_stream(generate_response_stream(stream))
    st.session_state.chat_history.append({"role": "legal consultant", "content": assistant_response, "avatar": "https://avatars.dicebear.com/api/avataaars/legal_consultant.svg"})  # Add assistant response to chat history

def chat_history_string():
    output = io.StringIO()

    for message in st.session_state.chat_history:
        if isinstance(message, HumanMessage):
            print(message.content, file=output)
        else:
            print(message.content, file=output)

    output_string = output.getvalue()
    return output_string

def parse_json(chat_history):
    pt_json = create_json(text=chat_history)
    try:
        data = json.loads(pt_json)
        st.session_state.pt_data = data
        print(f'DEBUG pt_json: {data}')
        st.session_state.differential_diagnosis = data['patient']['differential_diagnosis']
        st.session_state.critical_actions = data['patient']['critical_actions']
    except:
        return


#@st.cache_data
def write_note(note_input):    
    # Append user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": note_input, "avatar": user_avatar_url})
        
    client.beta.threads.messages.create(thread_id=st.session_state.thread_id, role="user", content=note_input)

    with client.beta.threads.runs.stream(thread_id=st.session_state.thread_id, assistant_id=note_writer) as stream:
        assistant_response = "".join(generate_response_stream(stream))
        st.write_stream(generate_response_stream(stream))
# Function to generate the response stream
def generate_response_stream(stream):
    for response in stream:
        if response.event == 'thread.message.delta':
            for delta in response.data.delta.content:
                if delta.type == 'text':
                    yield delta.text.value

def get_response(user_question):
    print(f'DEBUG get_response --- user_question: {user_question}')
    client.beta.threads.messages.create(thread_id=st.session_state.thread_id, role="user", content=user_question)
    response_placeholder = st.empty()  # Placeholder for streaming response text
    response_text = ""  # To accumulate response text

    # Stream response from the assistant
    with client.beta.threads.runs.stream(thread_id=st.session_state.thread_id, assistant_id=st.session_state.assistant_id) as stream:
        for chunk in stream:
            if chunk.event == 'thread.message.delta':  # Check if it is the delta message
                for delta in chunk.data.delta.content:
                    if delta.type == 'text':
                        response_text += delta.text.value  # Append new text fragment to response text
                        response_placeholder.markdown(response_text)  # Update the placeholder with new response text as markdown

    return response_text

def display_chat_history():    
    st.empty()  # Clear existing chat messages
    for message in st.session_state.chat_history:
        if isinstance(message, HumanMessage):
            avatar_url = message.avatar
            with st.chat_message("user", avatar=user_avatar_url):                
                st.markdown(message.content, unsafe_allow_html=True)
        else:
            avatar_url = message.avatar
            with st.chat_message("AI", avatar=avatar_url):
                st.markdown(message.content, unsafe_allow_html=True)


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
                    <span style="color:red;">{specialist}</span>
                </h6>
            </div>
            """, 
            unsafe_allow_html=True
        )
        user_question = st.chat_input("How may I help you?") 
    process_user_question(user_question, specialist)
def process_user_question(user_question, specialist):
    if user_question is not None and user_question != "":
        timezone = pytz.timezone("America/Los_Angeles")
        current_datetime = datetime.now(timezone).strftime("%H:%M:%S")
        user_question = current_datetime + f"""    \n{user_question}. 
        \n{st.session_state.completed_tasks_str}
        """
        st.session_state.completed_tasks_str = ''
        st.session_state.critical_actions  = []
        st.session_state.specialist = specialist
        specialist_avatar = specialist_id_caption[st.session_state.specialist]["avatar"]
        st.session_state.specialist_avatar = specialist_avatar
        
        st.session_state.chat_history.append(HumanMessage(user_question, avatar=user_avatar_url))

        with st.chat_message("user", avatar=user_avatar_url):
            st.markdown(user_question)
        
        with st.chat_message("AI", avatar=specialist_avatar):
            assistant_response = get_response(user_question)
            st.session_state.assistant_response = assistant_response
            


        #print(f'DEBUG ASSISTANT RESPONSE: {assistant_response}')


        st.session_state.chat_history.append(AIMessage(st.session_state.assistant_response, avatar=specialist_avatar))
        #print(f'DEBUG st.session_state.chat_history: {st.session_state.chat_history}')
        # extract json information from AI response   
        chat_history = chat_history_string()
        print(f'DEBUG CHAT HISTORY: {chat_history}')
        parse_json(chat_history)   



def main():
    initialize_session_state()
    display_header()
    
    name, authentication_status, username = authenticator.login('main')
    print(f'DEBUG AUTH STATUS: {authentication_status}')
    
    if authentication_status == True:
        # User is authenticated, show the app content# Create a thread where the conversation will happen and keep Streamlit from initiating a new session state
        if "thread_id" not in st.session_state:
            thread = client.beta.threads.create()
            st.session_state.thread_id = thread.id
        #update_user_config_file()
    
        display_chat_history() 
        handle_user_input_container()   
        process_other_queries() 

        display_sidebar()
    else:
        authenticate_user()
  

if __name__ == '__main__':
    main()