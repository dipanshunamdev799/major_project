from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.core import PropertyGraphIndex, Settings
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from typing import List, Dict
from src.constants import *
from src.utils import *
import nest_asyncio

nest_asyncio.apply()

# Initialize Hugging Face Embedding
Settings.embed_model = HuggingFaceEmbedding(model_name=hf_embedding_model, trust_remote_code=True)

from tqdm import tqdm

def query_and_generate_reports(queries: List[str]) -> List[Dict[str, str]]:
    """
    Query the knowledge graph for each query, aggregate context, and generate summary reports.
    Returns a list of dictionaries containing the query, aggregated context, and generated report.
    """
    results = []

    for query in tqdm(queries, desc="Processing Queries", unit="query"):
        tqdm.write("\n" + "="*80)
        tqdm.write(f"PROCESSING QUERY: {query}")
        tqdm.write("="*80)
        
        tqdm.write("\n[Step 1] Querying Knowledge Graph for context...")
        context = query_engine.query(query)
        
        if hasattr(context, 'source_nodes'):
            num_nodes = len(context.source_nodes)
            tqdm.write(f"  > Retrieved {num_nodes} relevant nodes/fragments from the graph.")
        
        response_text = str(context)
        preview = response_text[:150].replace("\n", " ") + "..." if len(response_text) > 150 else response_text
        tqdm.write(f"  > Initial Graph Answer: {preview}")

        # Generate a summary report using the aggregated context
        tqdm.write("\n[Step 2] Generating Executive Summary Report...")
        report = generate_summary_report(context, query)
        tqdm.write("  > Report generated successfully.")

        results.append({
            "query": query,
            "context": context,
            "report": report
        })
        tqdm.write("-" * 80 + "\n")

    return results

def save_reports_to_file(results: List[Dict[str, str]], filename: str):
    """
    Save query results and their generated reports to a file.
    """
    with open(filename, "w", encoding="utf-8") as file:
        for result in results:
            file.write(f"Query:\n{result['query']}\n\n")
            file.write(f"Context:\n{result['context']}\n\n")
            file.write(f"Generated Report:\n{result['report']}\n\n")
            file.write("-" * 80 + "\n\n")



import certifi
from neo4j import TrustCustomCAs

# Define connection to the Neo4j graph store
graph_store = Neo4jPropertyGraphStore(
    username=neo4j_username,
    password=neo4j_password,
    url=neo4j_url,
    encrypted=True,
    trusted_certificates=TrustCustomCAs(certifi.where())
)

# Initialize Ollama LLM for query engine (LlamaIndex integration - uses local Ollama service)
llm = Ollama(
    model=ollama_model,
    temperature=0.0,
    request_timeout=120.0
)
Settings.llm = llm

# Load the index from the existing graph store
index = PropertyGraphIndex.from_existing(
    property_graph_store=graph_store
)

# Create the query engine with Ollama LLM
query_engine = index.as_query_engine(
    include_text=True,
    llm=llm
)

# Define a list of queries, Different kinds of queries to see the effectiveness of in EV sector
# Define a list of queries, Different kinds of queries to see the effectiveness of in EV sector
if __name__ == "__main__":
    queries = [
        "How to invest in the EV sector? Summarize the most important financial trends in the EV Sector.",
        # "What are the recent financial sentiments about renewable energy investments?",
        # "Summarize the financial outlook for the technology sector in 2024.",
        # "What are the key financial risks in the automotive industry this year?",
        # "Provide insights on the financial performance of AI startups in the US."
    ]

    # Execute the queries and generate reports
    results = query_and_generate_reports(queries)

    # Save the reports to a file
    output_file = "financial_sentiment_reports.txt"
    save_reports_to_file(results, output_file)

    # Print a summary of the generated reports
    for result in results:
        print(f"Query: {result['query']}")
        print(f"Generated Report:\n{result['report']}")
        print("-" * 80)

