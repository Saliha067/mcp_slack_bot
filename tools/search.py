from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_ollama import OllamaEmbeddings
import pathlib
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from langchain_community.document_loaders.text import TextLoader
from uuid import uuid4
from dotenv import load_dotenv

load_dotenv()


def get_embeddings():
    """Get embeddings based on LLM_MODEL configuration."""
    llm_model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    
    # Use OpenAI embeddings if model starts with 'gpt'
    if llm_model.startswith("gpt"):
        return OpenAIEmbeddings(model="text-embedding-3-large")
    else:
        # Use Ollama embeddings with dedicated embedding model
        ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        # Use nomic-embed-text or mxbai-embed-large for embeddings, not chat models
        embedding_model = os.environ.get("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
        return OllamaEmbeddings(
            model=embedding_model,
            base_url=ollama_base_url
        )


def get_vectorstore() -> Chroma:
    """Check if vector store exists and initialize if needed."""
    embeddings = get_embeddings()
    vectorstore_path = pathlib.Path("./chroma_langchain_db")
    if not vectorstore_path.exists() or not any(vectorstore_path.iterdir()):
        initialize_rag()
    return Chroma(
        embedding_function=embeddings,
        persist_directory="./chroma_langchain_db",
    )


def initialize_rag():
    """Initialize the RAG system by creating and populating the vector store."""
    embeddings = get_embeddings()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    documents = []
    docs_dir = "./docs"
    
    if os.path.exists(docs_dir):
        # Walk through all subdirectories to find .md and .txt files
        for root, dirs, files in os.walk(docs_dir):
            for filename in files:
                if filename.endswith((".txt", ".md")):
                    file_path = os.path.join(root, filename)
                    try:
                        loader = TextLoader(file_path, encoding='utf-8')
                        loaded_docs = loader.load()
                        texts = text_splitter.split_documents(loaded_docs)
                        documents.extend(texts)
                        print(f"  ✓ Loaded: {file_path}")
                    except Exception as e:
                        print(f"  ✗ Failed to load {file_path}: {e}")
    
    if not documents:
        raise ValueError(
            f"No documents found in {docs_dir}. "
            "Vector store requires at least one document to initialize."
        )
    
    print(f"\n  Total documents to index: {len(documents)}")

    uuids = [str(uuid4()) for _ in range(len(documents))]
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory="./chroma_langchain_db",
        ids=uuids,
    )
    return vectorstore
