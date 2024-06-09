import streamlit as st
from streamlit_float import float_css_helper
from openai import OpenAI
from langchain_core.messages import HumanMessage, AIMessage
import os
from dotenv import load_dotenv
from prompts import *
from extract_json import extract_json

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
  "Emergency Medicine beta": {
    "assistant_id": "asst_GeAw2bIhrATHejogynMmP2VB",
    "caption": "EM - Beta testing",
    "avatar": "https://cdn.pixabay.com/photo/2013/07/12/14/33/carrot-148456_960_720.png"
  },
  "Mindfulness Teacher": {
    "assistant_id": "asst_bnFm27eqedaYK9Ulekh8Yjd9",
    "caption": "Goes Deep",
    "avatar": "https://cdn.pixabay.com/photo/2013/07/12/19/30/enlightenment-154910_1280.png"
  }
}

# Initialize session_state variables
def initialize_session_state():
    state_keys_defaults = {
        "chat_history": [],
        "user_question": "",
        "legal_question": "",
        "note_input": "",
        "json_data": {},
        "differential_diagnosis": {},
        "danger_diag_list": {},
        "critical_actions": {},
        "sidebar_state": 1,
        "assistant_response": "",
        "patient_language": "English",
        "specialist_input": "",
        "should_rerun": False,
        "user_question_sidebar": "",
        "old_user_question_sidebar": ""

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
        #print(f'DEBUG: Initial specialist set to {primary_specialist}')

# Setup the main page display and header
def display_header():
    st.set_page_config(page_title="EMA", page_icon="🤖🩺")
    st.header("EMA - Emergency Medicine Assistant 🤖🩺")

# Sidebar display
def display_sidebar():
    with st.sidebar:
        st.markdown("<h1 style='margin-top: -60px;text-align: center;'>EMA 🤖</h1>", unsafe_allow_html=True)
        
        tab1, tab2, tab3, tab4 = st.tabs(["Functions", "Specialists", "Note Analysis", "Update Variables"])
        
        with tab1:
            if st.session_state.critical_actions:
                st.subheader(":orange[Critical Actions]")
                for action in st.session_state.critical_actions.get('critical_actions', []):
                    st.markdown(f"- :orange[{action}]")
            
            if st.session_state.differential_diagnosis:
                st.subheader("Differential Diagnosis")
                for diagnosis_obj in st.session_state.differential_diagnosis.get("differential_diagnosis", []):
                    diagnosis = diagnosis_obj.get("diagnosis")
                    probability = diagnosis_obj.get("probability")
                    st.markdown(f"- {diagnosis} {probability}%")
                st.divider()
            display_functions_tab()

        with tab2:
            if st.session_state.critical_actions:
                st.subheader(":orange[Critical Actions]")
                for action in st.session_state.critical_actions.get('critical_actions', []):
                    st.markdown(f"- :orange[{action}]")
            
            if st.session_state.differential_diagnosis:
                st.subheader("Differential Diagnosis")
                for diagnosis_obj in st.session_state.differential_diagnosis.get("differential_diagnosis", []):
                    diagnosis = diagnosis_obj.get("diagnosis")
                    probability = diagnosis_obj.get("probability")
                    st.markdown(f"- {diagnosis} {probability}%")
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
        button4 = st.button("Pt Education Note")
    with col2:
        button11 = st.button('HPI only')
        button12 = st.button('A&P only')
        button13 = st.button('PT Plan')
        

    st.subheader('🏃‍♂️Flow')
    col1, col2 = st.columns(2)
    with col1:
        button5 = st.button("➡️Next Step Recommendation")
        button7 = st.button("📞Consult specialist🧑‍⚕️")
    with col2:
        button6 = st.button('➡️➡️I did that, now what?')

    st.divider()
    col1, col2, col3 = st.columns([1,3,1])
    with col2:
        button9 = st.button('NEW THREAD', type="primary")
        button10 = st.button('TEST')

    # Process button actions
    process_buttons(button1, button2, button3, button4, button5, button6, button7, button9, button10, button11, button12, button13)

# Process the buttons
def process_buttons(button1, button2, button3, button4, button5, button6, button7, button9, button10, button11, button12, button13):
    if button1:
        st.session_state["user_question"] = disposition_analysis
    if button2:
        st.session_state["user_question"] = procedure_checklist
    if button3:
        specialist = 'Note Writer'
        prompt = "Write a full medical note on this patient"
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button4:
        st.session_state["user_question"] = pt_education + f"\n the patient's instructions needs to be in {st.session_state.patient_language}"
    if button5:
        st.session_state["user_question"] = "What should i do next here in the emergency department?"
    if button6:
        st.session_state["user_question"] = "Ok i did that. Now what?"
    if button7:
        specialist = st.session_state.specialist
        prompt = consult_specialist
        st.session_state["specialist"] = specialist
        button_input(specialist, prompt)
    if button9:
        new_thread()
    if button10:
        specialist = 'Note Writer'
        prompt = "this is just a code test for button 10"
        st.session_state["specialist"] = specialist  # Set the specialist in session state
        button_input(specialist, prompt)
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
        button7 = st.button("Summarize Note")
    with col2:
        button8 = st.button("Optimize Your Note For Legal Protection")

    # Process buttons
    if button7:
        st.session_state["user_question"] = summarize_note + f' here is the note separated by triple backticks```{note_check}```'
    if button8:
        st.session_state["legal_question"] = optimize_legal_note + f' here is the note separated by triple backticks```{note_check}```'

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
    if specialist and specialist != st.session_state.specialist and not st.session_state.button_clicked:
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
        st.session_state.user_question_sidebar = user_question
        print(f'DEBUG user_question: {user_question}')
        #st.session_state.chat_history.append(HumanMessage(user_question, avatar=user_avatar_url))
        st.rerun()
        #st.session_state.assistant_response = get_response(user_question)

        #st.session_state.chat_history.append(AIMessage(st.session_state.assistant_response, avatar=specialist_avatar))
    st.session_state.button_clicked = False

# Updating the patient language
def update_patient_language():
    patient_language = st.text_input("Insert patient language if not English", value=st.session_state.patient_language)
    if patient_language != st.session_state.patient_language:
        st.session_state.patient_language = patient_language

# Processing queries
def process_other_queries():
    if st.session_state.user_question_sidebar is not "" and st.session_state.user_question_sidebar != st.session_state.old_user_question_sidebar:

        # set specialist_avatar for chat history
        specialist_avatar = specialist_id_caption[st.session_state.specialist]["avatar"]
        print(f'DEBUG: PROCESSS OTHER QUERRIES --- ST-SESSION SPECIALIST : {st.session_state.specialist}')
        print(f'DEBUG: SPECIALIST AVATAR: {specialist_avatar}')
        
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
        
        st.session_state.old_user_question_sidebar = user_question


        

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

def parse_json(assistant_response):
    # Call the extract_json function and capture its return values
    differential_diagnosis, critical_actions, modified_text = extract_json(assistant_response)

    # Check if the extracted values indicate no JSON content
    if not differential_diagnosis and not critical_actions:
        print("No JSON content found in assistant response.")
        st.session_state.assistant_response = modified_text
        return
    
    # Add debugging print statements
    print("Debug: assistant response: ", assistant_response)
    print("Debug: differential_diagnosis:", differential_diagnosis)
    print("Debug: critical_actions:", critical_actions)
    print("Debug: modified_text:", modified_text)
    
    # Assign the return values to the session state
    st.session_state.differential_diagnosis = differential_diagnosis
    st.session_state.critical_actions = critical_actions
    st.session_state.assistant_response = modified_text

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
        st.session_state.specialist = specialist
        specialist_avatar = specialist_id_caption[st.session_state.specialist]["avatar"]
        st.session_state.specialist_avatar = specialist_avatar
        
        st.session_state.chat_history.append(HumanMessage(user_question, avatar=user_avatar_url))

        with st.chat_message("user", avatar=user_avatar_url):
            st.markdown(user_question)
        
        with st.chat_message("AI", avatar=specialist_avatar):
            assistant_response = get_response(user_question)
            st.session_state.assistant_response = assistant_response

        # extract json information from AI response   
        parse_json(assistant_response)
        st.session_state.chat_history.append(AIMessage(st.session_state.assistant_response, avatar=specialist_avatar))
        #print(f'DEBUG st.session_state.chat_history: {st.session_state.chat_history}')
   



def main():
    # Create a thread where the conversation will happen and keep Streamlit from initiating a new session state
    if "thread_id" not in st.session_state:
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id

    initialize_session_state()
    display_header()

    tab1, tab2= st.tabs(["History", "Notes"])
    with tab1:
        display_chat_history() 
        handle_user_input_container()   
        process_other_queries() 

    display_sidebar()

  

if __name__ == '__main__':
    main()