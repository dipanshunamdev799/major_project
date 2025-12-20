from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import uvicorn
from engine import query_and_generate_reports
from src.utils import generate_search_queries, create_dataset_from_queries

app = FastAPI(
    title="Financial Sentiment Analysis API",
    description="API for querying the knowledge graph and generating financial sentiment reports.",
    version="1.0.0"
)

class QueryRequest(BaseModel):
    queries: List[str]

class ReportResponse(BaseModel):
    query: str
    context: str
    report: str

class DatasetRequest(BaseModel):
    user_input: str

@app.get("/")
def read_root():
    return {"message": "Welcome to the Financial Sentiment Analysis API"}

@app.post("/analyze", response_model=List[ReportResponse])
def analyze_sentiment(request: QueryRequest):
    """
    Accepts a list of queries and returns generated reports and context from the knowledge graph.
    """
    if not request.queries:
        raise HTTPException(status_code=400, detail="Query list cannot be empty")
    
    try:
        results = query_and_generate_reports(request.queries)
        # Convert results to the response format if necessary (engine returns Dict[str, str])
        # The engine returns {"query": ..., "context": ..., "report": ...} which matches ReportResponse
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing queries: {str(e)}")

@app.post("/generate_dataset")
def generate_dataset_endpoint(request: DatasetRequest):
    """
    Trigger the dataset generation process based on user input.
    """
    if not request.user_input:
        raise HTTPException(status_code=400, detail="User input cannot be empty")

    try:
        queries = generate_search_queries(request.user_input)
        if not queries:
             raise HTTPException(status_code=500, detail="Failed to generate queries from LLM")
        
        # create_dataset_from_queries prints to stdout/tqdm, it doesn't return the files path
        # It saves to 'dataset' directory by default.
        create_dataset_from_queries(queries)
        
        return {"message": f"Dataset generation initiated/completed for input: {request.user_input}", "generated_queries": queries}
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Error generating dataset: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
