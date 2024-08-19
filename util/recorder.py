# recorder.py

import streamlit as st
from streamlit_mic_recorder import mic_recorder, speech_to_text
from deepgram import DeepgramClient, PrerecordedOptions
import io
import os
from dotenv import load_dotenv
from prompts import transcript_prompt

import logging

logging.basicConfig(level=logging.INFO)


load_dotenv()

DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')

def on_mic_ready():
    st.session_state.mic_ready = True


def record_audio():
    
    print("Recording audio...")
    audio_data = mic_recorder(
        start_prompt="🎙️Record",
        stop_prompt="🔴Stop",
        just_once=True,
        callback=None,
        key="main_recorder"
    )
    if audio_data:
        print("Audio recorded successfully.")
        audio_bytes = io.BytesIO(audio_data['bytes'])
        audio_bytes.seek(0)
        with st.spinner("transcribing audio...."):
            raw_transcript = transcribe_audio(audio_bytes)
        if raw_transcript:
            transcript = raw_transcript['results']['channels'][0]['alternatives'][0]['paragraphs']['transcript']
            specialist = 'Emergency Medicine'
            st.session_state.specialist = specialist

            if "Speaker 1" in transcript:
                prompt = f"{transcript_prompt} '''{transcript}'''"
                return prompt
            else:
                prompt = transcript.replace("Speaker 0:", "").strip()
                return prompt
    return None

def transcribe_audio(audio_file):
    try:
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        options = PrerecordedOptions(
            model="nova-2-medical",
            language="en",
            intents=False, 
            smart_format=True, 
            punctuate=True, 
            paragraphs=True, 
            diarize=True, 
            filler_words=True, 
            sentiment=False, 
        )
        source = {'buffer': audio_file, 'mimetype': 'audio/wav'}
        response = deepgram.listen.rest.v("1").transcribe_file(source, options)
        return response
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None



# free google speech to text
def record_audio_and_transcribe():
    print("Recording audio from record_uadio_and_transcribe...")
    audio_data = speech_to_text(
        start_prompt="🎙️",
        stop_prompt="🔴Stop",
        just_once=True,
        callback=None
    )
    print(f'audio_data: {audio_data}')

def safe_mic_recorder():
    if 'mic_initialized' not in st.session_state:
        st.session_state.mic_initialized = False
    
    if not st.session_state.mic_initialized:
        st.session_state.mic_initialized = True
        return None
    
    return mic_recorder(
        start_prompt="🎙️Record",
        stop_prompt="🔴Stop",
        just_once=True,
        key=f"mic_recorder_{st.session_state.get('rerun_count', 0)}"
    )
