from pymongo import MongoClient
import json
from dotenv import load_dotenv
from bson import ObjectId
import os
load_dotenv()


DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
MONGODB_URI = os.getenv('MONGODB_ATLAS_URI')
CLIENT_SECRET_JSON = json.loads(os.getenv('CLIENT_SECRET_JSON'))
ENVIRONMENT = os.getenv('ENVIRONMENT')

DB_NAME = 'emma-dev'


# Connect to your MongoDB database
# MongoDB setup
client = MongoClient(MONGODB_URI, maxPoolSize=1, connect=False)
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
print("Successfully connected to MongoDB")
    
collection_name = db['user_110882409052588346228_session_66a8f8dbdad394922f3495fc']

# Query for the document with type "chat_history"
# result = collection.find_one({"type": "chat_history"})

# if result:
#     session_state_chat_history = result.get('session_state_chat_history')
    
#     # Remove the triple backticks
#     cleaned_history = session_state_chat_history.strip('`')

    
#     # Pretty print the result   
#     print(cleaned_history)
# else:
#     print("Document not found")



def load_chat_history(collection_name):
    chat_history = []
    differential_diagnosis = []

    result = list(db[collection_name].find_one({"type": "chat_history"}))
    session_state_chat_history = result.get('session_state_chat_history')
    cleaned_history = session_state_chat_history.strip('`')
    st.session_state.session_state.chat_history = cleaned_history
    return cleaned_history


load_chat_history(collection_name)


normal_chat_history= [HumanMessage(content='10:43:22\n            \n13 yo male with penis pain\n            \n\n            ', avatar='https://lh3.googleusercontent.com/a/ACg8ocIRCJCVRmzRoeyJJWfxDywU-tEbxmtl9FlhwNYGGGpao69d1hiJwg=s96-





























                                                                                                                                                                                                                                                                               -c'), AIMessage(content='As an emergency medicine specialist, I\'ll need more information to provide a comprehensive assessment and plan for this 13-year-old male presenting with penis pain. However, I can offer some general insights and steps to follow:\n\n## 1. Brief Assessment\n13-year-old male presenting with penis pain; no other details provided about medical history, onset, duration, or associated symptoms.\n\n## 2. Differential Diagnosis\n\n1. Balanitis (70%)\n   - Common in uncircumcised males\n   - Often associated with poor hygiene\n   - Can cause pain, redness, and swelling\n   - Weak evidence: Lack of specific symptoms described\n\n2. Phimosis (60%)\n   - Inability to retract foreskin\n   - Can cause pain, especially during urination or erection\n   - Common in adolescents\n   - Weak evidence: Lack of specific symptoms described\n\n3. Paraphimosis (40%)\n   - Medical emergency where foreskin is stuck behind the glans\n   - Causes severe pain and swelling\n   - Weak evidence: Lack of urgency in presentation description\n\n4. Urinary Tract Infection (30%)\n   - Can cause pain in the penis, especially during urination\n   - Often accompanied by frequency and urgency\n   - Weak evidence: Lack of urinary symptoms described\n\n5. Sexually Transmitted Infection (20%)\n   - Such as chlamydia or gonorrhea\n   - Can cause pain, discharge, or burning sensation\n   - Weak evidence: Patient\'s young age, lack of sexual history provided\n\n6. Trauma (15%)\n   - Accidental injury or "zipper injury"\n   - Would typically have a clear history of injury\n   - Weak evidence: No mention of recent injury\n\n7. Testicular Torsion (10%)\n   - While primarily affecting the testicle, can cause referred pain to the penis\n   - Medical emergency\n   - Weak evidence: No mention of sudden onset or severe pain\n\n## 3. High-Risk Diagnoses\n- Paraphimosis: Requires immediate attention to prevent tissue damage\n- Testicular Torsion: Time-sensitive condition that can lead to loss of testicle if not treated promptly\n\n## 4. Suggested Follow-Up Steps\n\n**Additional Questions:**\n- When did the pain start?\n- Is the pain constant or intermittent?\n- Any associated symptoms (fever, discharge, urinary symptoms)?\n- Any history of sexual activity?\n- Any recent trauma or injury?\n- Is the patient circumcised?\n\n**Physical Examinations:**\n- Complete genital examination\n- Assess for signs of inflammation, swelling, or discharge\n- Check for ability to retract foreskin (if uncircumcised)\n- Examine testicles for signs of torsion\n\n**Lab Tests:**\n- Urinalysis and urine culture\n- STI screening if sexually active\n\n**Imaging Studies:**\n- Ultrasound if testicular torsion is suspected\n\n## 5. Interventions\nWill depend on the specific diagnosis but may include:\n- Topical antifungal or antibiotic creams for balanitis\n- Antibiotics for UTI or certain STIs\n- Manual reduction for paraphimosis\n\n## 6. Critical Actions\n- Immediate urology consultation if paraphimosis or testicular torsion is suspected\n- Ensure proper hygiene practices are being followed\n\n## 7. Academic Insights\nThe differential diagnosis of penile pain in adolescents highlights the importance of considering both common and emergent conditions. While infections like balanitis are frequent, it\'s crucial not to overlook time-sensitive diagnoses such as testicular torsion, which can present with referred pain to the penis. The presentation also underscores the need for sensitive and age-appropriate communication when discussing genital issues with adolescent patients.', avatar='https://i.ibb.co/LnrQp8p/Designer-17.jpg')]