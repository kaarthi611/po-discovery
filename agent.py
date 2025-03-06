"""
Agent - Processes user queries to fetch plan information from a database and API.
"""

import os
import sys
from typing import Dict, List, Optional, Any, TypedDict, Annotated, Literal, Tuple
import json
from operator import itemgetter
from dotenv import load_dotenv

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

import langgraph
from langgraph.graph import END, StateGraph

from tools.database_query_tool import DatabaseQueryTool
from tools.api_tool import ApiTool

# Load environment variables
load_dotenv()

# Initialize the tools
db_tool = DatabaseQueryTool()
api_tool = ApiTool(os.getenv("API_BASE_URL", "http://35.182.5.113:5001"))

# Set up the LLM
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
if not anthropic_api_key:
    raise ValueError("ANTHROPIC_API_KEY environment variable is required")

llm = ChatAnthropic(
    api_key=anthropic_api_key,
    model=os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219"),
    temperature=0.1,
)


# Define the state for our agent
class AgentState(TypedDict):
    """State object for the agent."""

    messages: List[Dict]
    user_query: str
    sql_query: Optional[str]
    query_type: Optional[str]  # 'category' or 'plan'
    db_result: Optional[Dict]
    api_result: Optional[Dict]
    response: Optional[str]
    context: Optional[str]  # Added to track conversation context


# Define the nodes
def parse_user_input(state: AgentState) -> AgentState:
    """Parse user input into SQL query for either category or specific plan information."""
    messages = state["messages"]
    user_query = state["user_query"]

    print("\n" + "=" * 80)
    print(f"🔍 Processing user query: '{user_query}'")

    # Build context from previous messages
    context = ""
    if len(messages) > 0:
        context_pairs = []
        for i in range(0, len(messages), 2):
            if i + 1 < len(messages):  # Make sure there's a response for this query
                user_msg = messages[i]["content"]
                assistant_msg = messages[i + 1]["content"]
                context_pairs.append(f"User: {user_msg}\nAssistant: {assistant_msg}")

        if context_pairs:
            context = "Previous conversation:\n" + "\n\n".join(context_pairs)
            print(
                f"📝 Using conversation context from {len(context_pairs)} exchange(s)"
            )

    # Create messages directly instead of using ChatPromptTemplate
    system_message = SystemMessage(
        content="""You are an expert at converting natural language into SQL queries. 
    The database contains a table called 'plans' with the following columns:
    - id
    - Category (e.g., 'Business Internet', 'Business Mobile', 'Business TV')
    - Plans (e.g., 'Business Internet 300 Mbps', '5G Infinite Premium')
    - Price
    - Description
    
    First, analyze the user query to determine if they're asking about:
    1. A CATEGORY of plans (e.g., mobile plans, internet plans, TV plans)
    2. A SPECIFIC PLAN or feature (e.g., 5G plans, Gigabit plans)
    
    If they're asking about a CATEGORY:
    - Generate a SQL query that searches for categories matching their request
    - Example: For "I need mobile plans", return:
      SELECT DISTINCT Category FROM plans WHERE Category LIKE '%Mobile%'
    
    If they're asking about a SPECIFIC PLAN or feature:
    - Generate a SQL query that searches for specific plans matching their request
    - Example: For "I need 5G plans", return:
      SELECT Plans FROM plans WHERE Plans LIKE '%5G%'
    
    Do not use 'SELECT *' in your query. Instead use 'SELECT Category, Plans, Description'
    
    Pay attention to the conversation context when generating the query.
    If the user query is a follow-up question or references something previously mentioned,
    use that context to generate an appropriate SQL query.
    
    DO NOT explain your reasoning. ONLY return the SQL query."""
    )

    # Include context in the human message if available
    if context:
        human_content = f"{context}\n\nCurrent user query: {user_query}"
    else:
        human_content = user_query

    human_message = HumanMessage(content=human_content)

    print("📝 Generating SQL query...")
    # Invoke the LLM with the messages
    query_response = llm.invoke([system_message, human_message])

    # Extract the SQL query from the response
    sql_query = query_response.content.strip()
    print(f"🔧 Generated SQL query: {sql_query}")

    # Determine query type (category or plan)
    query_type = "category"  # Default
    if "SELECT DISTINCT Category" in sql_query or "SELECT Category FROM" in sql_query:
        query_type = "category"
    else:
        query_type = "plan"

    print(f"📋 Query type: {query_type}")

    return {
        **state,
        "sql_query": sql_query,
        "query_type": query_type,
        "context": context,
    }


def call_db(state: AgentState) -> AgentState:
    """Execute the SQL query using the database tool."""
    sql_query = state["sql_query"]

    print("🔄 Executing SQL query...")
    db_response = json.loads(db_tool(sql_query))
    print(f"📊 Database response: {json.dumps(db_response, indent=2)}")

    return {**state, "db_result": db_response}


def call_api(state: AgentState) -> AgentState:
    """Call the API with results from database."""
    db_result = state["db_result"]
    query_type = state["query_type"]

    print("\n" + "-" * 80)
    print("🌐 Starting API calls...")

    # If DB query failed, skip API call
    if not db_result.get("success", False):
        print("❌ Database query failed, skipping API calls")
        return {
            **state,
            "api_result": {
                "error": "Database query failed",
                "details": db_result.get("message", "Unknown error"),
            },
        }

    api_results = {}

    if query_type == "category":
        # Extract categories from the DB result
        categories = [row.get("Category") for row in db_result.get("results", [])]
        print(f"📋 Found categories: {categories}")

        # If no categories found, skip API call
        if not categories:
            print("⚠️ No categories found in database response")
            return {
                **state,
                "api_result": {
                    "error": "No categories found",
                    "details": "The database query did not return any categories",
                },
            }

        # Make API calls for each category
        for category in categories:
            print(f"📲 Calling API for category: '{category}'")

            # Format the endpoint correctly using the category
            endpoint = f"plans/category/{category}"
            method = "GET"

            print(f"   Endpoint: {endpoint}")
            print(f"   Method: {method}")

            # Call API to get plans for this category
            response = api_tool.send_request(endpoint=endpoint, method=method)

            print(f"   Response: {json.dumps(response, indent=2)}")
            api_results[category] = response

    elif query_type == "plan":
        # Extract plan names from the DB result
        plans = [row.get("Plans") for row in db_result.get("results", [])]
        print(f"📋 Found plans: {plans}")

        # If no plans found, skip API call
        if not plans:
            print("⚠️ No plans found in database response")
            return {
                **state,
                "api_result": {
                    "error": "No plans found",
                    "details": "The database query did not return any plans",
                },
            }

        # Make API calls for each plan
        for plan in plans:
            print(f"📲 Calling API for plan: '{plan}'")

            # Format the endpoint correctly using the plan name
            endpoint = f"plans/{plan}"
            method = "GET"

            print(f"   Endpoint: {endpoint}")
            print(f"   Method: {method}")

            # Call API to get details for this plan
            response = api_tool.send_request(endpoint=endpoint, method=method)

            print(f"   Response: {json.dumps(response, indent=2)}")
            api_results[plan] = response

    return {**state, "api_result": api_results}


def generate_response(state: AgentState) -> AgentState:
    """Generate a natural language response based on DB and API results."""
    user_query = state["user_query"]
    db_result = state["db_result"]
    api_result = state["api_result"]
    query_type = state["query_type"]
    context = state.get("context", "")

    print("\n" + "-" * 80)
    print("💬 Generating natural language response...")

    # Create messages directly
    system_message = SystemMessage(
        content="""You are a helpful customer service assistant. 
    Your task is to provide information about plans based on the data provided.
    
    Generate a natural, conversational response to the user's query using the 
    database and API results. Be helpful and informative.
    
    If there were errors in retrieving the data, apologize and explain what went wrong 
    in user-friendly terms without technical details.
    
    Maintain conversation context and refer to previous information when appropriate.
    If the user is asking about something you've already discussed, acknowledge that.
    
    Make your responses concise and focused on answering the user's question."""
    )

    # Include context in the human message if available
    human_content = f"""
    User Query: {user_query}
    
    Query Type: {query_type}
    
    Database Result: {json.dumps(db_result, indent=2)}
    
    API Result: {json.dumps(api_result, indent=2)}
    """

    if context:
        human_content = f"""
        {context}
        
        {human_content}
        """

    human_content += "\nPlease provide a natural language response to the user's query."

    human_message = HumanMessage(content=human_content)

    # Invoke the LLM with the messages
    response = llm.invoke([system_message, human_message])
    print(f"✅ Response generated: {response.content}")
    print("=" * 80 + "\n")

    return {
        **state,
        "response": response.content,
        "messages": state["messages"]
        + [{"role": "assistant", "content": response.content}],
    }


# Build the agent graph
def build_agent_graph() -> StateGraph:
    """Build the LangGraph agent workflow."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("parse_user_input", parse_user_input)
    workflow.add_node("call_db", call_db)
    workflow.add_node("call_api", call_api)
    workflow.add_node("generate_response", generate_response)

    # Connect the nodes
    workflow.add_edge("parse_user_input", "call_db")
    workflow.add_edge("call_db", "call_api")
    workflow.add_edge("call_api", "generate_response")
    workflow.add_edge("generate_response", END)

    # Set the entry point
    workflow.set_entry_point("parse_user_input")

    return workflow


# Create the agent for execution
agent_executor = build_agent_graph().compile()


def process_user_query(query: str, chat_history: List[Dict] = None) -> str:
    """Process a user query and return a response."""
    if chat_history is None:
        chat_history = []

    # Initialize the state
    state = {
        "messages": chat_history,
        "user_query": query,
        "sql_query": None,
        "query_type": None,
        "db_result": None,
        "api_result": None,
        "response": None,
        "context": None,  # Add context field to state
    }

    # Run the agent
    result = agent_executor.invoke(state)

    # Return the response
    return result["response"]


def process_user_query_with_details(
    query: str, chat_history: List[Dict] = None
) -> Tuple[str, Dict]:
    """Process a user query and return both response and technical details."""
    if chat_history is None:
        chat_history = []

    # Initialize the state
    state = {
        "messages": chat_history,
        "user_query": query,
        "sql_query": None,
        "query_type": None,
        "db_result": None,
        "api_result": None,
        "response": None,
        "context": None,  # Add context field to state
    }

    # Run the agent
    result = agent_executor.invoke(state)

    # Extract technical details
    technical_details = {
        "sql_query": result.get("sql_query"),
        "query_type": result.get("query_type"),
        "db_result": result.get("db_result"),
        "api_result": result.get("api_result"),
    }

    # Return both the response and technical details
    return result["response"], technical_details
