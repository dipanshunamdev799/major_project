# Financial Sentiment Analysis with Knowledge Graphs & LLMs

A comprehensive framework for gathering financial news, constructing a knowledge graph, and performing sentiment analysis using Local LLMs (Ollama) and Neo4j.

## 🚀 Overview

This project provides an end-to-end pipeline for:
1.  **Intelligent Data Collection**: Generates optimized search queries and scrapes relevant financial news articles using Google Custom Search.
2.  **Knowledge Graph Construction**: Builds a structured Knowledge Graph (using Neo4j) from the unstructured text data.
3.  **Semantic Analysis**: Utilizes Retrieval-Augmented Generation (RAG) to query the graph and generate insightful financial sentiment reports.
4.  **Service Integration**: Exposes functionality via a FastAPI backend for easy integration.

## 🛠️ Tech Stack

*   **Language**: Python 3.10+
*   **LLM Orchestration**: [LlamaIndex](https://www.llamaindex.ai/)
*   **Graph Database**: [Neo4j](https://neo4j.com/)
*   **Local LLM**: [Ollama](https://ollama.com/) (Mistral)
*   **Embeddings**: HuggingFace (`Alibaba-NLP/gte-large-en-v1.5`)
*   **API Framework**: FastAPI
*   **Search**: Google Custom Search API

## 📂 Project Structure

```
├── app.py                      # FastAPI server entry point
├── engine.py                   # Core query processing and reporting logic
├── requirements.txt            # Python dependencies
├── src/
│   ├── constants.py            # Configuration (API keys, DB creds)
│   ├── graph_store_creation.py # Script to scrape data and build the graph
│   └── utils.py                # Utilities for scraping, search, and LLM helper functions
└── dataset/                    # Directory where scraped text files are stored
```

## ⚙️ Prerequisites

1.  **Neo4j Instance**: You need a running Neo4j database (AuraDB or Local).
2.  **Ollama**: Install [Ollama](https://ollama.com/) and pull the mistral model:
    ```bash
    ollama pull mistral
    ```
3.  **Google Custom Search**:
    *   Get an API Key from Google Cloud Platform.
    *   Create a Programmable Search Engine to get the Search Engine ID.

## 📥 Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd <repository-folder>
    ```

2.  **Create and activate a virtual environment**:
    ```bash
    python -m venv myenv
    # Windows
    .\myenv\Scripts\activate
    # Linux/Mac
    source myenv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Credentials**:
    Open `src/constants.py` and update the following values:
    ```python
    neo4j_username = 'neo4j'
    neo4j_password = 'your_password'
    neo4j_url = 'neo4j+s://your-instance.databases.neo4j.io'

    google_api = "YOUR_GOOGLE_API_KEY"
    search_engine_id = "YOUR_SEARCH_ENGINE_ID"
    ```

## 🏃 Usage

### 1. Build the Knowledge Graph
This step scrapes the web for data based on your topic and builds the Neo4j graph.
Edit the `user_input` variable in `src/graph_store_creation.py` if needed, then run:

```bash
python src/graph_store_creation.py
```
*   This will fetch articles, save them to `dataset/`, and populate your Neo4j database.

### 2. Run the Analysis (CLI Mode)
To run pre-defined queries directly from the terminal with usage progress bars:

```bash
python engine.py
```
*   Reports will be saved to `financial_sentiment_reports.txt`.

### 3. Run the API (Server Mode)
Start the FastAPI server:

```bash
python app.py
```

The API will be available at `http://localhost:8000`.

#### API Endpoints:

*   **POST /generate_dataset**: Trigger data scraping.
    ```json
    { "user_input": "Future of EV battery technology" }
    ```
*   **POST /analyze**: sending queries to the Knowledge Graph.
    ```json
    { "queries": ["What are the investment risks in EV batteries?"] }
    ```

You can view the interactive API documentation at `http://localhost:8000/docs`.

## 📊 Features in Detail

*   **Smart Query Generation**: Uses LLMs to convert simple topics into complex, keyword-rich search strings for better retrieval.
*   **Progress Tracking**: Integrated `tqdm` progress bars in the CLI to track scraping and query processing.
*   **Detailed Logging**: Step-by-step console output showing graph node retrieval counts and initial answer previews.
