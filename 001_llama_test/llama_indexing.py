# llama_indexing.py
import os
import time
import gc
import psutil
from typing import List
from llama_index.core import (
    VectorStoreIndex, 
    SimpleDirectoryReader,
    Settings,
    StorageContext,
    load_index_from_storage
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.node_parser import SemanticSplitterNodeParser
from deepseek_llm import DeepSeekLLM  # Your fixed custom LLM class

# ======================
# Configuration
# ======================
class Config:
    PROJECT_PATH = "/home/opc/news_dagster-etl/news_aggregator"
    PERSIST_DIR = os.path.expanduser("~/news_aggregator_index")
    SAFE_MEMORY_THRESHOLD = 4 * 1024**3  # 4GB (more conservative)
    MAX_BATCH_SIZE = 1     # Maintain single-file processing
    MAX_RETRIES = 5        # Same retry count
    RETRY_DELAY = 90       # Longer GC time (from 60s)
    CHUNK_SIZE = 64        # Smaller chunks (from 128)
    CHUNK_OVERLAP = 5      # Minimal overlap (from 10)

# ======================
# Core Functions
# ======================
def process_batch(batch: List, splitter: SemanticSplitterNodeParser) -> List:
    try:
        nodes = splitter.get_nodes_from_documents(batch)
        del batch  # Explicit cleanup
        return nodes
    except Exception as e:
        print(f"Batch error: {str(e)}")
        return []

def initialize_components():
    os.environ["FAISS_USE_GPU"] = "0"
    os.environ["FAISS_OPT_LEVEL"] = "2"
    
    Settings.embed_model = HuggingFaceEmbedding(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        device="cpu"
    )
    
    llm = DeepSeekLLM(
        api_key="sk-7cb9d35fa9e34ce18d1c4aff62c3f628",
        model="deepseek-reasoner"
    )
    Settings.llm = llm
    
    Settings.num_workers = 1  # Reduced from 2
    Settings.chunk_size = Config.CHUNK_SIZE
    Settings.chunk_overlap = Config.CHUNK_OVERLAP
    
    return llm

# ======================
# Index Management
# ======================
def memory_safe(func):
    def wrapper(*args, **kwargs):
        process = psutil.Process(os.getpid())
        for attempt in range(Config.MAX_RETRIES):
            mem = psutil.virtual_memory()
            if mem.available < Config.SAFE_MEMORY_THRESHOLD:
                print(f"Memory low ({mem.available/1024**3:.1f}GB). Waiting {Config.RETRY_DELAY}s...")
                time.sleep(Config.RETRY_DELAY)
                continue
                
            try:
                return func(*args, **kwargs)
            except MemoryError:
                print(f"Memory error (attempt {attempt+1}). Retrying...")
                time.sleep(Config.RETRY_DELAY)
                gc.collect()
                
        raise MemoryError("Memory exhausted. Try smaller batches.")
    return wrapper

@memory_safe
def get_or_create_index():
    if os.path.exists(Config.PERSIST_DIR):
        return load_index_from_storage(
            StorageContext.from_defaults(persist_dir=Config.PERSIST_DIR),
            llm=Settings.llm
        )
    
    loader = SimpleDirectoryReader(
        input_dir=Config.PROJECT_PATH,
        recursive=True,
        exclude_hidden=True,
        required_exts=[".py"],
        exclude=["__pycache__", "venv", "tests"]
    )
    
    splitter = SemanticSplitterNodeParser(
        buffer_size=32,  # Reduced buffer (from 64)
        breakpoint_percentile_threshold=90,  # Lower threshold (from 95)
        embed_model=Settings.embed_model
    )
    
    all_nodes = []
    current_batch = []
    
    for docs in loader.iter_data():
        current_batch.extend(docs)
        
        if len(current_batch) >= Config.MAX_BATCH_SIZE:
            print(f"Processing {len(current_batch)} files...")
            nodes = process_batch(current_batch, splitter)
            all_nodes.extend(nodes)
            
            del current_batch[:]
            gc.collect()
    
    if current_batch:
        print(f"Final batch: {len(current_batch)} files")
        nodes = process_batch(current_batch, splitter)
        all_nodes.extend(nodes)
    
    index = VectorStoreIndex(all_nodes)
    index.storage_context.persist(persist_dir=Config.PERSIST_DIR)
    return index

# ======================
# Main Execution
# ======================
class ProjectAssistant:
    def __init__(self):
        self.llm = initialize_components()
        self.index = get_or_create_index()
        self.query_engine = self.index.as_query_engine(
            similarity_top_k=1,  # Reduced from 2
            streaming=False
        )
    
    def ask(self, question: str) -> str:
        try:
            return str(self.query_engine.query(question))
        except Exception as e:
            return f"Error: {str(e)}"

if __name__ == "__main__":
    assistant = ProjectAssistant()
    print("Assistant ready. Ask questions about your project!")
    
    try:
        while True:
            question = input("\nQuestion (q to quit): ").strip()
            if question.lower() in ("q", "quit"):
                break
                
            start = time.time()
            response = assistant.ask(question)
            print(f"\n[Response in {time.time()-start:.1f}s]\n{response}")
            
    except KeyboardInterrupt:
        print("\nExiting...")
