import os
from typing import List, Optional, Any, Dict
import warnings

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*The function.*was deprecated.*")
warnings.filterwarnings("ignore", category=UserWarning)

from langchain_google_genai import GoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
import google.generativeai as genai

# -------------------------------
# Configuration
# -------------------------------

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
VECTOR_DB_DIR = "vectorstore"
TRANSCRIPT_DIR = "transcripts"

# In-memory store for session histories
store = {}

# -------------------------------
# Helper Functions
# -------------------------------

def get_session_history(session_id: str) -> ChatMessageHistory:
    """Retrieve or create message history for a session"""
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


def load_transcript_files(directory: str = TRANSCRIPT_DIR) -> List[Document]:
    """Load all transcript text files into LangChain Documents with metadata"""
    documents = []
    if not os.path.exists(directory):
        raise FileNotFoundError(f"Transcript directory '{directory}' does not exist.")

    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            file_path = os.path.join(directory, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                documents.append(
                    Document(page_content=content, metadata={"source": filename})
                )
                print(f"Loaded: {filename}")
            except Exception as e:
                print(f"Error loading {filename}: {str(e)}")
    return documents


def create_vector_store(documents: List[Document], api_key: str, persist_dir: str = VECTOR_DB_DIR):
    """Create or load vector store with Gemini embeddings"""
    if not documents:
        raise ValueError("No documents provided to create vector store")

    # If the vector store already exists, load it
    if os.path.exists(persist_dir):
        print("Loading existing vector store...")
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
        # It's important to be cautious with allow_dangerous_deserialization=True
        # Ensure you trust the source of your persisted vector store.
        vector_store = FAISS.load_local(persist_dir, embeddings, allow_dangerous_deserialization=True)
        print("Done")
        return vector_store

    print("Creating new vector store...")
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ". ", "? ", "! "],
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len
    )
    
    try:
        # Split documents into chunks
        chunks = text_splitter.split_documents(documents)
        if not chunks:
            raise ValueError("No text chunks created from documents")
            
        print(f"Created {len(chunks)} text chunks")
        
        # Create embeddings
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
        
        # Create vector store
        vector_store = FAISS.from_documents(chunks, embeddings)
        
        # Save the vector store
        os.makedirs(persist_dir, exist_ok=True)
        vector_store.save_local(persist_dir)
        print(f"Vector store saved to {persist_dir}")
        
        return vector_store
        
    except Exception as e:
        print(f"Error creating vector store: {str(e)}")
        raise


def setup_chatbot(vector_store, api_key: str, verbose: bool = False):
    """Set up conversational chain with custom prompt and message history"""
 
    llm = GoogleGenerativeAI(model="gemini-2.0-flash-lite", temperature=0.6, google_api_key=api_key)

    # Custom Prompt Template with Markdown Formatting Instructions
    prompt_template = """
    You are an expert AI assistant specialized in analyzing and discussing YouTube video content.

        Role and Behavior:
        - Provide direct, accurate answers based solely on the video transcript
        - Be concise yet informative in your responses
        - Always respond in English
        - Maintain a conversational and engaging tone
        - Focus on the main points and key details from the video
        - If asked about something not in the transcript, politely indicate that information isn't covered in the video

        Guidelines:
        - Never mention that you're using a transcript
        - Don't reference timestamps or transcript sections
        - Don't make assumptions beyond the provided content
        - If multiple interpretations are possible, present the most relevant one
        - Keep responses focused and to the point

        Formatting Guidelines (Use Markdown):
        - Use **bold text** for important concepts or key points
        - Use *italics* for emphasis or to highlight terms
        - Use `code formatting` for technical terms, product names, or specific terminology
        - Use appropriate heading levels (## for main sections, ### for subsections) to structure longer responses
        - Create bullet points or numbered lists when presenting multiple items or steps
        - Use > blockquotes when referencing direct quotes from the video
        - Format any code examples with ```language syntax highlighting

        Context from Video:
        {context}

        User Question:
        {question}

        Response (following all guidelines above with Markdown formatting):
    """

    PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])

    # Conversational Chain without deprecated args
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vector_store.as_retriever(search_kwargs={"k": 6}),
        combine_docs_chain_kwargs={"prompt": PROMPT},
        verbose=verbose
    )

    # Wrap with message history
    chain_with_history = RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="question",
        history_messages_key="chat_history"
    )

    return chain_with_history


def display_sources(response):
    """Display retrieved source chunks"""
    if "source_documents" in response:
        print("\nSources:")
        for i, doc in enumerate(response["source_documents"], 1):
            source = doc.metadata.get("source", "Unknown")
            content = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
            print(f"\n{i}. From: {source}")
            print(f"{content}")


# -------------------------------
# Main Application Loop
# -------------------------------

def main():
    api_key = input("Enter your Gemini API key: ").strip()
    if not api_key:
        print("Error: GOOGLE_API_KEY not provided!")
        return

    # Configure the Google Generative AI library with the provided API key
    genai.configure(api_key=api_key)

    print("Loading transcripts...")
    documents = load_transcript_files()
    if not documents:
        print(f"No transcript files found in '{TRANSCRIPT_DIR}'")
        return

    print("Building vector database...")
    vector_store = create_vector_store(documents, api_key)

    print("Setting up chatbot...")
    chatbot = setup_chatbot(vector_store, api_key)

    print("\n🤖 Chatbot ready! Type 'quit' to exit.\n")

    session_id = "abc123"  # You can make this dynamic per user in web apps

    while True:
        query = input("You: ").strip()
        if query.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        if not query:
            continue

        try:
            result = chatbot.invoke(
                {"question": query},
                config={"configurable": {"session_id": session_id}}
            )
            answer = result.get("answer", "No answer generated.")
            print(f"\nBot: {answer}")

            # Uncomment to show sources if needed for debugging/inspection
            # display_sources(result)

        except Exception as e:
            print(f"\n⚠️ Error processing request: {str(e)}")


if __name__ == "__main__":
    main()
