from retrieval.ingestion import load_directory
from retrieval.vector_store import CulturalVectorStore
from config.settings import RAW_DATA_DIR

if __name__ == "__main__":
    records = load_directory(RAW_DATA_DIR)
    store = CulturalVectorStore()
    store.replace(records)
    print(f"Indexed {len(records)} records in ChromaDB.")