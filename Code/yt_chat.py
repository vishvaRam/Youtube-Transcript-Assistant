import os
from typing import List
import warnings
# Suppress deprecation warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', message='.*The function.*was deprecated.*')

from langchain_google_genai import GoogleGenerativeAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
import google.generativeai as genai
from dotenv import load_dotenv
from langchain_core._api.deprecation import LangChainDeprecationWarning

warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)

# Load environment variables
load_dotenv()

def load_transcript_files(directory: str = "transcripts") -> List[str]:
    """Load all transcript files from the specified directory"""
    documents = []
    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            with open(os.path.join(directory, filename), 'r', encoding='utf-8') as f:
                documents.append(f.read())
    return documents

def create_vector_store(documents: List[str]):
    """Create a FAISS vector store from the documents"""
    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.create_documents(documents)
    
    # Create vector store using Vertex AI embeddings
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_documents(chunks, embeddings)
    return vector_store

def setup_chatbot(vector_store):
    """Set up the conversational chain"""
    # Initialize Gemini model
    llm = GoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7)
    
    # Set up memory
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        output_key="answer"
    )
    
    # Create chain
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vector_store.as_retriever(search_kwargs={"k": 3}),
        memory=memory,
        return_source_documents=True,
        combine_docs_chain_kwargs={"prompt": None},
        verbose=True
    )
    
    return chain

def main():
    # Get API key from environment variable
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in .env file!")
        return
    
    # Configure Gemini
    os.environ["GOOGLE_API_KEY"] = api_key
    genai.configure(api_key=api_key)
    
    # Load documents
    print("Loading transcript files...")
    documents = load_transcript_files()
    if not documents:
        print("No transcript files found in the 'transcripts' directory!")
        return
    
    # Create vector store
    print("Creating vector store...")
    vector_store = create_vector_store(documents)
    
    # Set up chatbot
    print("Setting up chatbot...")
    chat_chain = setup_chatbot(vector_store)
    
    # Simple command-line interface
    print("\nChatbot ready! Type 'quit' to exit.")
    while True:
        question = input("\nYou: ")
        if question.lower() == 'quit':
            break
            
        try:
            response = chat_chain({"question": question})
            print("\nBot:", response["answer"])
            
            # Uncomment to see sources
            # if "source_documents" in response:
            #     print("\nSources:")
            #     for idx, doc in enumerate(response["source_documents"], 1):
            #         print(f"\nSource {idx}:")
            #         print(doc.page_content[:200] + "...")
            
        except Exception as e:
            print(f"\nError: An error occurred while processing your question.")
            print(f"Error details: {str(e)}")
            print("Please try asking your question in a different way or try another question.")

if __name__ == "__main__":
    main() 