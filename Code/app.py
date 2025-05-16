import streamlit as st
import os
from yt_transcript import get_clean_transcript, get_video_id
from yt_chat import (
    load_transcript_files,
    create_vector_store,
    setup_chatbot,
    TRANSCRIPT_DIR,
    VECTOR_DB_DIR
)
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables and configure
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "video_id" not in st.session_state:
    st.session_state.video_id = None
if "chatbot" not in st.session_state:
    st.session_state.chatbot = None

# Page config
st.set_page_config(
    page_title="YouTube Video Chat",
    page_icon="🎥",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stTextInput>div>div>input {
        background-color: #f0f2f6;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .chat-message.user {
        background-color: #e3f2fd;
    }
    .chat-message.assistant {
        background-color: #f5f5f5;
    }
    .chat-message .message-content {
        display: flex;
        margin-top: 0.5rem;
    }
    .chat-message .avatar {
        width: 40px;
        height: 40px;
        margin-right: 1rem;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #fff;
        border-radius: 50%;
        font-size: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("🎥 YouTube Video Chat")
    st.write("Enter a YouTube video URL to start chatting about its content!")
    
    video_url = st.text_input("YouTube URL", key="video_url")
    
    if st.button("Process Video"):
        if video_url:
            video_id = get_video_id(video_url)
            if video_id:
                with st.spinner("Processing transcript..."):
                    result = get_clean_transcript(video_url)
                    if result.startswith("Error"):
                        st.error(result)
                    else:
                        st.success("Transcript processed successfully!")
                        # Initialize chatbot with new transcript
                        documents = load_transcript_files()
                        vector_store = create_vector_store(documents)
                        st.session_state.chatbot = setup_chatbot(vector_store)
                        st.session_state.video_id = video_id
                        # Embed video
                        st.video(video_url)
            else:
                st.error("Invalid YouTube URL")
    
    st.divider()
    st.markdown("""
    ### How to use:
    1. Paste a YouTube video URL
    2. Click "Process Video"
    3. Wait for transcript processing
    4. Start chatting about the video!
    """)

# Main chat interface
st.title("💬 Chat with Your Video")

# Display chat messages
for message in st.session_state.chat_history:
    with st.container():
        st.markdown(f"""
        <div class="chat-message {message['role']}">
            <div class="message-content">
                <div class="avatar">{'🧑' if message['role'] == 'user' else '🤖'}</div>
                <div class="message">
                    {message['content']}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# Chat input
if st.session_state.chatbot:
    user_input = st.text_input("Ask about the video:", key="user_input")
    
    if user_input:
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        # Get bot response
        with st.spinner("Thinking..."):
            result = st.session_state.chatbot.invoke(
                {"question": user_input},
                config={"configurable": {"session_id": st.session_state.video_id}}
            )
            answer = result.get("answer", "I couldn't generate an answer. Please try rephrasing your question.")
        
        # Add bot response to chat history
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        
        # Rerun to update chat display
        st.rerun()
else:
    st.info("👈 Please process a YouTube video first to start chatting!") 

