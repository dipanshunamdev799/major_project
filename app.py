import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
warnings.filterwarnings("ignore", message=".*Accessing `__path__`.*")

import streamlit as st
import pandas as pd
from streamlit_agraph import agraph, Node, Edge, Config

from core import process_query
from src.auth import sign_in_with_email_password, sign_in_with_google_id_token, sign_up_with_email_password, send_password_reset_email
from src.neo4j_manager import neo4j_manager

# --- Page Config ---
st.set_page_config(
    page_title="Financial Intelligence Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
/* Import sleek Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Outfit:wght@500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

h1, h2, h3 {
    font-family: 'Outfit', sans-serif;
}

/* Custom Title Styling with Gradient */
.title-gradient {
    background: linear-gradient(90deg, #00FF88 0%, #00B8D9 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
    margin-bottom: 0px;
    padding-bottom: 0px;
}

/* Hide default hamburger menu and footer for professionalism */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {background: transparent !important;}

/* Sleek Chat Boundaries */
.stChatMessage {
    background: rgba(20, 24, 36, 0.4) !important;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 1.5rem;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.1);
    transition: transform 0.2s ease-in-out;
}
.stChatMessage:hover {
    transform: translateY(-2px);
}

/* Metric styling overhauls */
[data-testid="stMetricValue"] {
    font-size: 2rem !important;
    font-weight: 700;
    color: #00FF88 !important;
    text-shadow: 0px 0px 10px rgba(0, 255, 136, 0.3);
}

[data-testid="stMetricLabel"] {
    font-weight: 600;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Glassmorphic buttons */
.stButton>button {
    background: linear-gradient(135deg, rgba(0, 255, 136, 0.1) 0%, rgba(0, 184, 217, 0.1) 100%);
    border: 1px solid rgba(0, 255, 136, 0.4);
    color: #00FF88;
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.3s ease;
}

.stButton>button:hover {
    background: linear-gradient(135deg, rgba(0, 255, 136, 0.2) 0%, rgba(0, 184, 217, 0.2) 100%);
    box-shadow: 0 0 15px rgba(0, 255, 136, 0.4);
    transform: translateY(-2px);
    border-color: #00FF88;
    color: #FFF;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background-color: transparent;
}
.stTabs [data-baseweb="tab"] {
    font-weight: 600;
    color: #94A3B8;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    color: #00FF88;
}

/* Sticky Container for Graph */
.sticky-graph {
    position: sticky;
    top: 3rem;
    z-index: 10;
}

</style>
""", unsafe_allow_html=True)



# --- Session State ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []
if 'auth_mode' not in st.session_state:
    st.session_state['auth_mode'] = "email"

with st.sidebar:
    st.title("Control Panel")
    if not st.session_state['authenticated']:
        st.subheader("Authentication")
        auth_mode = st.radio("Mode", ["Email/Password", "Google Token"], horizontal=True)
        if auth_mode == "Email/Password":
            auth_action = st.radio("Action", ["Sign In", "Sign Up", "Reset Password"], horizontal=True)
            email = st.text_input("Email")
            
            if auth_action != "Reset Password":
                password = st.text_input("Password", type="password")
            
            if auth_action == "Sign Up":
                button_label = "Create Account"
            elif auth_action == "Reset Password":
                button_label = "Send Reset Link"
            else:
                button_label = "Sign In"
                
            if st.button(button_label):
                if auth_action == "Reset Password":
                    if email:
                        with st.spinner("Sending reset email..."):
                            res = send_password_reset_email(email)
                            if "error" in res:
                                st.error(f"Error: {res['error']}")
                            else:
                                st.success("Password reset email sent! Check your inbox.")
                    else:
                        st.warning("Please enter your email address.")
                else:
                    if email and password:
                        with st.spinner("Working with Firebase..."):
                            if auth_action == "Sign Up":
                                res = sign_up_with_email_password(email, password)
                            else:
                                res = sign_in_with_email_password(email, password)
                            if "error" in res:
                                st.error(f"Error: {res['error']}")
                            else:
                                st.session_state['authenticated'] = True
                                st.session_state['user'] = res.get('email') or email
                                st.rerun()
                    else:
                        st.warning("Provide both email and password")
        else:
            st.caption("Use the Firebase JS frontend to sign in with Google, then paste the returned Firebase ID token here.")
            google_token = st.text_area("Firebase ID token", height=140)
            if st.button("Validate Google Sign-In"):
                res = sign_in_with_google_id_token(google_token.strip())
                if "error" in res:
                    st.error(res["error"])
                else:
                    st.session_state['authenticated'] = True
                    st.session_state['user'] = res.get("email") or "Google user"
                    st.rerun()
    else:
        st.success(f"Logged in as: {st.session_state['user']}")
        if st.button("Log Out"):
            st.session_state['authenticated'] = False
            st.session_state['user'] = None
            st.rerun()
    st.markdown("---")
    st.caption("powered by Groq (llama-3.3-70b-versatile) & Neo4j")

st.title("Financial Intelligence Platform")
st.caption("Finance-only research assistant with a growing Neo4j knowledge graph.")

if not st.session_state['authenticated']:
    st.info("Please sign in from the sidebar to use the platform.")
else:
    expand_graph = st.toggle("Expand Knowledge Graph", value=True, help="If enabled, it will search the web and add new entities to the knowledge graph. If disabled, answers will be based only on existing knowledge.")
    query_input = st.chat_input("Ask a financial question... (e.g. 'What is the EV sector outlook?')")

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("Analysis Flow")
        for msg in st.session_state['chat_history']:
            if msg["role"] == "user":
                st.markdown(f'<div class="user-msg"><b>User:</b><br>{msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="bot-msg"><b>Agent:</b><br>{msg["content"]}</div>', unsafe_allow_html=True)
                if msg.get("sources"):
                    with st.expander("Sources"):
                        for s in msg["sources"]:
                            st.write(s)
                if msg.get("graph_results"):
                    with st.expander("Graph Matches"):
                        for row in msg["graph_results"]:
                            st.write(f"{row.get('source_name')} -> {row.get('target_name') or 'context'} (score {row.get('score', 0):.2f})")
                if msg.get("ticker_data"):
                    ticker_data = msg["ticker_data"]
                    st.markdown(f"**Ticker:** `{ticker_data['symbol']}`")
                    hist_60d = ticker_data.get("history_60d") or {}
                    hist_1m = ticker_data.get("history_1m") or {}
                    hist_1y = ticker_data.get("history_1y") or {}
                    if hist_60d or hist_1m or hist_1y:
                        tab1, tab2, tab3 = st.tabs(["60-Day", "1-Month", "1-Year"])
                        with tab1:
                            if hist_60d: st.line_chart(pd.Series(hist_60d))
                            else: st.info("No 60-day historical data available.")
                        with tab2:
                            if hist_1m: st.line_chart(pd.Series(hist_1m))
                            else: st.info("No 1-month historical data available.")
                        with tab3:
                            if hist_1y: st.line_chart(pd.Series(hist_1y))
                            else: st.info("No 1-year historical data available.")
                            
                    daily_summary = ticker_data.get("daily_summary") or {}
                    monthly_summary = ticker_data.get("monthly_summary") or {}
                    yearly_summary = ticker_data.get("yearly_summary") or {}
                    metrics = st.columns(4)
                    metrics[0].metric("Latest Close", f"{daily_summary.get('latest_close', 'N/A'):.2f}" if 'latest_close' in daily_summary else "N/A")
                    metrics[1].metric("60D Return", f"{daily_summary.get('60d_return', 0):.2f}%")
                    metrics[2].metric("1M Return", f"{monthly_summary.get('1m_return', 0):.2f}%")
                    metrics[3].metric("1Y Return", f"{yearly_summary.get('1y_return', 0):.2f}%")

        if query_input:
            st.session_state['chat_history'].append({"role": "user", "content": query_input})
            st.rerun()  # forces chat update instantly 

    if st.session_state['chat_history'] and st.session_state['chat_history'][-1]['role'] == 'user':
        with col1:
            with st.spinner(f"Analyzing markets{' & growing knowledge graph' if expand_graph else ''}..."):
                recent_query = st.session_state['chat_history'][-1]['content']
                result = process_query(recent_query, expand_graph)
                
                if result.get("error"):
                    response_text = result["error"]
                else:
                    response_text = result["report"]

                response_obj = {
                    "role": "agent",
                    "content": response_text,
                    "sources": result.get("sources", []),
                    "ticker_data": result.get("ticker_data"),
                    "graph_results": result.get("graph_results", []),
                }

                st.session_state['chat_history'].append(response_obj)
                st.rerun()

    with col2:
        st.markdown('<div class="sticky-graph">', unsafe_allow_html=True)
        st.subheader("Live Knowledge Graph")
        st.caption("The graph expands with each finance query and shows the strongest discovered market relationships.")

        nodes_data, edges_data = neo4j_manager.get_graph_data()

        with st.container():
            st.markdown('<div class="panel">', unsafe_allow_html=True)
            st.metric("Tracked Entities", len(nodes_data))
            st.metric("Tracked Relationships", len(edges_data))
            st.markdown('</div>', unsafe_allow_html=True)

        if nodes_data:
            import networkx as nx
            from networkx.algorithms.community import louvain_communities
            
            # Map into networkx for Louvain
            G = nx.Graph()
            for n in nodes_data:
                G.add_node(n["id"])
            for e in edges_data:
                G.add_edge(e["source"], e["target"])
                
            try:
                communities = louvain_communities(G)
                cluster_map = {}
                for i, cluster in enumerate(communities):
                    for node in cluster:
                        cluster_map[node] = str(i)
                        
                for n in nodes_data:
                    # Update group to the community ID to color-code it
                    # Overriding the default 'type' group
                    n["group"] = cluster_map.get(n["id"], "0")
            except Exception as e:
                print(f"Louvain clustering error: {e}")

            nodes = [Node(id=n["id"], label=n["label"], group=n.get("group", "0"), size=22, shape="dot") for n in nodes_data]
            edges = [Edge(source=e["source"], target=e["target"], label=e["label"]) for e in edges_data]

            config = Config(
                width="100%",
                height=620,
                directed=True,
                physics=True,
                hierarchical=False,
                nodeHighlightBehavior=True,
                highlightColor="#d6d6d6",
                collapsible=False,
                node={'labelProperty':'label'},
                link={'labelProperty': 'label', 'renderLabel': True}
            )

            agraph(nodes=nodes, edges=edges, config=config)
        else:
            st.info("The knowledge graph is currently empty. Ask a finance question to start growing it.")
            
        st.markdown('</div>', unsafe_allow_html=True)
