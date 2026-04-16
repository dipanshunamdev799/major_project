import json
from groq import Groq
from src.config import GROQ_API_KEY, GROQ_MODEL

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def _strip_code_fences(payload: str) -> str:
    cleaned = (payload or "").strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.replace("```json", "", 1)
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```", "", 1)
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()

def call_groq(system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 1000) -> str:
    """Wrapper to make calls to Groq API."""
    if not client:
        return ""
    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Groq API Error: {e}")
        return ""

def is_finance_related(query: str) -> bool:
    """Checks if a user query is related to finance/economics."""
    system_prompt = "You are a classifier. Determine if the user's query is about finance, investing, economy, markets, companies, or money. Reply with strictly 'YES' or 'NO'."
    response = call_groq(system_prompt, query, temperature=0.0, max_tokens=10)
    if not response:
        keywords = {
            "stock", "market", "finance", "financial", "invest", "economy", "share",
            "company", "revenue", "profit", "inflation", "gdp", "nifty", "sensex",
            "bse", "nse", "bond", "equity", "mutual fund", "ticker", "valuation",
        }
        lowered = query.lower()
        return any(keyword in lowered for keyword in keywords)
    return "YES" in response.upper()

def extract_entities(text: str) -> list:
    """Extracts financial entities and relationships from text."""
    system_prompt = """
    Extract financial entities and relationships from the text.
    Return JSON format:
    {
      "entities": [{"name": "string", "type": "Company|Sector|Indicator|Event", "description": "string"}],
      "relationships": [{"source": "Entity1", "target": "Entity2", "type": "OPERATES_IN|REPORTED|AFFECTS|CORRELATED_WITH", "period": "string", "description": "string"}]
    }
    For 'period', extract the timeframe if mentioned (e.g. '2024', 'Q1 2023', 'Oct 2022'). If none, use 'Current'.
    Only return valid JSON, no markdown formatting blocks.
    """
    response = call_groq(system_prompt, text, temperature=0.0, max_tokens=2000)
    
    try:
        data = json.loads(_strip_code_fences(response))
        return data
    except Exception as e:
        print(f"Error parsing JSON from Groq: {e}\nResponse: {response}")
        return {"entities": [], "relationships": []}

def generate_search_queries(user_input: str) -> list:
    """Generates keyword-optimized search queries."""
    system_prompt = """
    You are a financial data engineer. Convert the user input into 3-5 HIGH-DENSITY search queries optimized for search engines.
    Focus on Indian Financial Market (NSE/BSE).
    Output format: STRICTLY a JSON array of strings e.g. ["query 1", "query 2"].
    No markdown formatting blocks.
    """
    response = call_groq(system_prompt, user_input, temperature=0.2, max_tokens=200)
    
    try:
        queries = json.loads(_strip_code_fences(response))
        valid_queries = [query.strip() for query in queries if isinstance(query, str) and query.strip()]
        return valid_queries[:5] if isinstance(queries, list) else []
    except Exception as e:
        print(f"Error parsing search queries JSON: {e}")
        return [
            user_input,
            f"{user_input} latest financial results",
            f"{user_input} market impact india",
        ]

def generate_summary_report(context: str, query: str) -> str:
    """Generates a detailed financial report based on context."""
    system_prompt = (
        "You are a financial research assistant. Answer only using finance context. "
        "Provide: Executive Summary, Key Drivers, Risks, and Actionable Takeaways. "
        "If context is weak, say so explicitly instead of inventing facts."
    )
    
    user_prompt = f"Context:\n{context}\n\nQuery:\n{query}"
    response = call_groq(system_prompt, user_prompt, temperature=0.2, max_tokens=2048)
    if response:
        return response
    return (
        "Executive Summary\n"
        "The assistant could not reach the language model, so this answer is based on available structured context only.\n\n"
        f"Query\n{query}\n\n"
        f"Context Used\n{context[:1200]}"
    )
