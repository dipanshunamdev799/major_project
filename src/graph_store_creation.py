from src.utils import *
from llama_index.core import SimpleDirectoryReader
from llama_index.core import PropertyGraphIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.core.indices.property_graph import SchemaLLMPathExtractor
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
import nest_asyncio
import asyncio
# Constants are imported via src.utils import *

# Apply nest_asyncio
nest_asyncio.apply()



# Change the input as needed
user_input = "Financial sentiment analysis for the electric vehicle sector in the US"
queries = generate_search_queries(user_input)
queries
create_dataset_from_queries(queries)


# Documents Reader
documents = SimpleDirectoryReader("dataset").load_data()


graph_store = Neo4jPropertyGraphStore(
    username=neo4j_username,
    password=neo4j_password,
    url=neo4j_url,
)


# Initialize Hugging Face embedding model
embed_model = HuggingFaceEmbedding(
    model_name=hf_embedding_model
)

# Initialize Ollama LLM (LlamaIndex integration - uses local Ollama service)
llm = Ollama(
    model=ollama_model,
    temperature=0.0,
    request_timeout=120.0  # Increase timeout for larger models
)

# Create the index
index = PropertyGraphIndex.from_documents(
    documents,
    embed_model=embed_model,
    kg_extractors=[
        SchemaLLMPathExtractor(
            llm=llm
        )
    ],
    property_graph_store=graph_store,
    show_progress=True,
    use_async=True
)


# save
index.storage_context.persist(persist_dir="./storage")
print("index saved")