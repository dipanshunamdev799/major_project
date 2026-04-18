from src.llm import is_finance_related, generate_search_queries, generate_summary_report
from src.search import search_and_extract
from src.market_data import (
    get_monthly_summary,
    get_ticker_data,
    get_ticker_info,
    get_yearly_summary,
    get_daily_summary,
    search_ticker,
)
from src.neo4j_manager import neo4j_manager


def _build_empty_response(error_message: str) -> dict:
    return {
        "error": error_message,
        "report": "",
        "ticker_data": None,
        "sources": [],
        "graph_updated": False,
        "graph_context": "",
        "graph_results": [],
        "kg_extraction_data": [],
    }

def process_query(user_query: str, expand_graph: bool = True) -> dict:
    """Main pipeline for processing user queries."""
    if not is_finance_related(user_query):
        return _build_empty_response(
            "This assistant only handles finance-related questions. Ask about markets, stocks, companies, economic events, or portfolio topics."
        )

    sources = set()
    graph_updated = False
    kg_extraction_data = []
    raw_text_snippets = []
    
    ticker = search_ticker(user_query)
    if ticker:
        daily_history = get_ticker_data(ticker, "60d")
        monthly_history = get_ticker_data(ticker, "1mo")
        yearly_history = get_ticker_data(ticker, "1y")
        ticker_payload = {
            "symbol": ticker,
            "history_60d": daily_history["Close"].to_dict() if not daily_history.empty else {},
            "history_1m": monthly_history["Close"].to_dict() if not monthly_history.empty else {},
            "history_1y": yearly_history["Close"].to_dict() if not yearly_history.empty else {},
            "info": get_ticker_info(ticker),
            "daily_summary": get_daily_summary(ticker),
            "monthly_summary": get_monthly_summary(ticker),
            "yearly_summary": get_yearly_summary(ticker),
        }
        updated = neo4j_manager.add_ticker_data(ticker, ticker_payload)
        graph_updated = graph_updated or updated

    if expand_graph:
        sub_queries = generate_search_queries(user_query)
        if user_query not in sub_queries:
            sub_queries.insert(0, user_query)

        for sq in filter(None, sub_queries[:5]):
            extracted_results = search_and_extract(sq) or []
            for res in extracted_results:
                url = res["url"]
                sources.add(url)
                graph_data = res["graph_data"]
                
                if res.get("content"):
                    raw_text_snippets.append(f"Source: {url}\n{res['content'][:1000]}...")
                
                if graph_data.get("entities") or graph_data.get("relationships"):
                    kg_extraction_data.append({
                        "url": url,
                        "title": res.get("title", ""),
                        "entities": graph_data.get("entities", []),
                        "relationships": graph_data.get("relationships", [])
                    })

                if graph_data.get("entities"):
                    updated = neo4j_manager.add_financial_data(
                        graph_data,
                        source_url=url,
                        source_title=res.get("title", ""),
                        source_content=res.get("content", ""),
                    )
                    graph_updated = graph_updated or updated

    context = neo4j_manager.query_graph(user_query)
    
    combined_context_parts = []
    if raw_text_snippets:
        combined_context_parts.append("--- RAW SEARCH EXTRACTS ---")
        combined_context_parts.extend(raw_text_snippets[:10])
        
    combined_context_parts.append("--- KNOWLEDGE GRAPH CONTEXT ---")
    combined_context_parts.append(context if context else "No extensive graph context found.")
    
    report_context = "\n".join(combined_context_parts)
    report = generate_summary_report(report_context, user_query)

    return {
        "error": None,
        "report": report,
        "ticker_data": None,
        "sources": sorted(sources),
        "graph_updated": graph_updated,
        "graph_context": context,
        "graph_results": neo4j_manager.retrieve_relevant_subgraph(user_query),
        "kg_extraction_data": kg_extraction_data,
    }
