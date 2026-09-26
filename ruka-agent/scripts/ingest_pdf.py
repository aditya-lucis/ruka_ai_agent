import sys
import os
from pathlib import Path
import pypdf
from google import genai

# Setup path so we can import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.retrieval.chunker import chunk_markdown
from src.retrieval.embedder import GeminiEmbedder
from src.retrieval.store import VectorStore
from src.config import load_settings

def ingest_pdf(pdf_path: str):
    print(f"Loading {pdf_path}...")
    text = ""
    with open(pdf_path, 'rb') as f:
        reader = pypdf.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() + "\n\n"
    
    print(f"Extracted {len(text)} characters.")
    
    chunks = chunk_markdown(text, source=Path(pdf_path).name)
    print(f"Created {len(chunks)} chunks.")
    
    settings = load_settings(dotenv_path=Path(os.path.join(os.path.dirname(__file__), '..', '.env')))
    api_key = settings.api_key
    if not api_key:
        print("GEMINI_API_KEY not found in .env")
        return
        
    client = genai.Client(api_key=api_key)
    embedder = GeminiEmbedder(client)
    
    # store in vector store
    store = VectorStore(path=os.path.join(os.path.dirname(__file__), '..', 'ruka.db'))
    
    import time
    batch_size = 20
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i+batch_size]
        texts = [c.text for c in batch_chunks]
        print(f"Embedding batch {i//batch_size + 1}/{ (len(chunks) + batch_size - 1)//batch_size }...")
        try:
            vectors = embedder.embed_documents(texts)
            store.add(batch_chunks, vectors)
            time.sleep(10) # Avoid rate limit
        except Exception as e:
            print(f"Error embedding batch: {e}")
            time.sleep(15)
            
    print("Ingestion complete.")

if __name__ == "__main__":
    pdf = r"c:\Traine\ruka\book\RUKA-IV-The-Awakening-of-the-Senses.pdf"
    ingest_pdf(pdf)
