import io
import streamlit as st
from util.recorder import transcribe_audio
from streamlit_mic_recorder import mic_recorder
from prompts import transcript_prompt

def render_mobile():
    # Add custom CSS to center all content
    st.markdown("""
        <style>
        .stApp {
            max-width: 100%;
            padding: 1rem;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .stApp > * {
            max-width: 100%;
            width: 100%;
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)

    # Existing header code
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

    # st.write("Start a new patient session")
    text = record_audio_mobile()
    return text

def record_audio_mobile():
    
    print("Recording audio...")
    
    audio = mic_recorder(
        start_prompt="🎙️ REC",
        stop_prompt="🔴 Stop",
        just_once=False,
        callback=None,
        use_container_width=True, 
    )

    return handle_record_audio_mobile(audio)


def handle_record_audio_mobile(audio):
    processing_message = st.empty()
    if audio is not None:
        # Create a placeholder for the processing message
        processing_message.success("Audio recorded successfully! Transcribing..")
        
        audio_bytes = io.BytesIO(audio['bytes'])
        audio_bytes.seek(0)
        raw_transcript = transcribe_audio(audio_bytes)

        if raw_transcript:
            # Clear the processing message
            processing_message.empty()
            
            transcript = raw_transcript['results']['channels'][0]['alternatives'][0]['paragraphs']['transcript']
            specialist = 'Emergency Medicine'
            st.session_state.specialist = specialist
            st.success("Audio transcribed successfully!")

            if "Speaker 1" in transcript:
                prompt = f"{transcript_prompt} '''{transcript}'''"
                return prompt
            else:
                prompt = transcript.replace("Speaker 0:", "").strip()
                return prompt
    else:
        processing_message.empty()

    return None  # Return None i



if __name__ == '__main__':
    render_mobile()
