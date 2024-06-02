import streamlit as st
from streamlit_option_menu import option_menu
import streamlit as st

# Using HTML to reduce space above the header
st.markdown("<h1 style='margin-top: -50px;'>My Header</h1>", unsafe_allow_html=True)
st.write("Some content below the header.")


option = st.selectbox('Select an option', ['Full Note', 'HPI', 'HPI + ROS'])

selected = st.multiselect('Select options', ['Full Note', 'HPI', 'HPI + ROS', 'HPI + ROS + PE', 'PE', 'DDX', 'A&P + DDX', 'A&P no DDX'])

options = {
    'List 1': [1,2,3], 
    'List 2': ['a','b','c']
}
selected = st.selectbox('Choose a list', list(options.keys()))
choice = options[selected]

option = st.radio("Pick your Group of Specialists", [
"Acute Care",
"Neurological",
"Sensory Systems (Eyes, Ears, Nose, Throat)",
"Cardiovascular and Respiratory",
"Gastrointestinal Systems",
"Renal and GU Systems",
"Dermatology and Plastic Surgery",
"Musculoskeletal Systems",
"General",
"Pediatrics",
],captions = ["EM, Toxicology, Wildnerness", 
              "Neurology, Neurosurgery, Psychiatry", 
              "Ophthalmology, ENT",
              "Cardiology, Cardiovascular Surgery, Vascular Surgery, Pulmonology, Thoracic Surgery",
              "Gastroenterology, Hepatology, Colorectal Surgery, Gen Surg",
              "Nephrology, Gynecology, Urology, Obstetrics",
              "",
              "Sports Med, Orthopedics, PM&R, Rheumatology, Physical Therapy",
              "ICU, Internal Medicine, Infectious Disease, HemOnc, Endo",
              "Pediatrics, Neonatology, Pediatric Surgery",
              "",
              ""     
              ])

st.header(f'Your specialty is :red[{option}]')

import streamlit as st
from streamlit_option_menu import option_menu

selected = option_menu(
    menu_title="Specialty Group",
    options=["Acute Care - EM, Tox",
"Neurological System - Neurology, Neurosurgery, Psychiatry",
"Sensory System (Eyes, Ears, Nose, Throat) - Ophthalmology, Otolaryngology (ENT)",
"Cardiovascular System and Respiratory - Cardiology, Cardiovascular Surgery, Vascular Surgery,Pulmonology, Thoracic Surgery",
"Gastrointestinal System - Gastroenterology, Hepatology, Colorectal Surgery, Gen Surg",
"Renal System and GU - Nephrology, Gynecology, Urology, Obstetrics, Reproductive Endocrinology/Infertility, Andrology",
"Dermatology and Plastic Surgery",
"Musculoskeletal System - Orthopedic Surgery, Physical Medicine and Rehabilitation, Rheumatology",
"General Systems - ICU, Internal Medicine, Infectious Disease, Hematology and Oncology, Endo, Hematology/Oncology, Radiation Oncology",
"Pediatrics - Pediatrics, Neonatology, Pediatric Surgery",
"Diagnostic and Laboratory Services - Pathology, Radiology, Nuclear Medicine, Anesthesiology"
],
    icons=['house', 'gear'],
    default_index=0
)

html = """
<select>
  <option value="option1">Option 1</option>
  <option value="option2">Option 2</option>
  <option value="option3">Option 3</option>
</select>
"""
st.markdown(html, unsafe_allow_html=True)