import sys
import os
import time
from pathlib import Path
import pypdf
from google import genai
from google.genai.errors import APIError

# Setup path so we can import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.retrieval.chunker import chunk_markdown
from src.retrieval.embedder import GeminiEmbedder
from src.retrieval.store import VectorStore
from src.config import load_settings

def ingest_pdf_robust(pdf_path: str):
    print(f"Loading {pdf_path}...")
    text = ""
    with open(pdf_path, 'rb') as f:
        reader = pypdf.PdfReader(f)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n\n"
    
    chunks = chunk_markdown(text, source=Path(pdf_path).name)
    print(f"Total characters: {len(text)}. Total chunks: {len(chunks)}.")
    
    settings = load_settings(dotenv_path=Path(os.path.join(os.path.dirname(__file__), '..', '.env')))
    api_key = settings.api_key
    if not api_key:
        print("API Key not found.")
        return
        
    client = genai.Client(api_key=api_key)
    embedder = GeminiEmbedder(client)
    store = VectorStore(path=os.path.join(os.path.dirname(__file__), '..', 'ruka.db'))
    
    batch_size = 10
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i+batch_size]
        texts = [c.text for c in batch_chunks]
        batch_idx = i // batch_size + 1
        total_batches = (len(chunks) + batch_size - 1) // batch_size
        
        success = False
        retries = 0
        while not success and retries < 5:
            print(f"Embedding batch {batch_idx}/{total_batches} (Attempt {retries+1})...")
            try:
                vectors = embedder.embed_documents(texts)
                store.add(batch_chunks, vectors)
                success = True
                print(f"Batch {batch_idx} success.")
                time.sleep(5)  # small delay on success
            except APIError as e:
                if e.code == 429:
                    wait_time = 15 * (2 ** retries)
                    print(f"Rate limited (429). Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    print(f"API Error: {e}")
                    break
            except Exception as e:
                if '429' in str(e):
                    wait_time = 15 * (2 ** retries)
                    print(f"Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    print(f"Error: {e}")
                    break
        if not success:
            print(f"Failed to embed batch {batch_idx} after {retries} retries.")
            
    print("Ingestion complete.")

if __name__ == "__main__":
    pdf = r"c:\Traine\ruka\book\RUKA-IV-The-Awakening-of-the-Senses.pdf"
    ingest_pdf_robust(pdf)
