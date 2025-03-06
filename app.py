"""
Streamlit UI for the Plans Agent - Clean UI with Reordered Technical Details
"""

import streamlit as st
import json
import time
import re
from agent import process_user_query

# Set page config
st.set_page_config(page_title="Plans Assistant", page_icon="📱", layout="wide")

# Custom CSS
st.markdown(
    """
<style>
    .stTextInput > div > div > input {
        padding: 12px;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: row;
        align-items: flex-start;
    }
    .chat-message.user {
        background-color: #f0f2f6;
    }
    .chat-message.assistant {
        background-color: #e6f7ff;
    }
    .chat-message .avatar {
        width: 40px;
        margin-right: 1rem;
    }
    .chat-message .content {
        width: 80%;
        word-break: break-word;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 8px 16px;  /* Reduced padding for lower height */
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 14px;    /* Slightly smaller font */
        margin: 0;          /* Remove margin */
        cursor: pointer;
        border-radius: 4px;
        height: 36px;       /* Fixed height to match input field */
        line-height: 20px;  /* Adjust line height for centering text */
    }
    .assistant-thinking {
        color: #666;
        font-style: italic;
    }
    
    /* Hide sidebar completely */
    [data-testid="stSidebar"] {
        display: none;
    }
    
    /* Container for input box and clear button */
    .input-container {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    /* Align clear button with chat input */
    [data-testid="column"] [data-testid="stVerticalBlock"] {
        display: flex;
        align-items: center;
    }
</style>
""",
    unsafe_allow_html=True,
)

# App title
st.title("📱 Plan Finder Assistant")
st.subheader("Ask about available plans and offerings")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "technical_details" not in st.session_state:
    st.session_state.technical_details = []


# Function to clean and parse JSON (handles common issues)
def safe_json_loads(json_str):
    """Safely parse JSON with error handling."""
    try:
        # Remove any ANSI color codes or other special characters
        cleaned_str = re.sub(r"\x1b\[[0-9;]*m", "", json_str)

        # Try to parse as is
        return json.loads(cleaned_str)
    except json.JSONDecodeError as e:
        try:
            # Sometimes there are issues with trailing commas
            # This is a hack but works for many cases
            # Replace trailing commas before closing brackets
            fixed_str = re.sub(r",\s*([\}\]])", r"\1", cleaned_str)
            return json.loads(fixed_str)
        except json.JSONDecodeError:
            # If that fails, try to extract just the valid JSON part
            # by finding matching braces
            stack = []
            start_idx = cleaned_str.find("{")
            if start_idx == -1:
                start_idx = cleaned_str.find("[")

            if start_idx != -1:
                for i in range(start_idx, len(cleaned_str)):
                    if cleaned_str[i] in "{[":
                        stack.append(cleaned_str[i])
                    elif cleaned_str[i] == "}" and stack and stack[-1] == "{":
                        stack.pop()
                        if not stack:  # Found matching outer braces
                            try:
                                return json.loads(cleaned_str[start_idx : i + 1])
                            except:
                                pass
                    elif cleaned_str[i] == "]" and stack and stack[-1] == "[":
                        stack.pop()
                        if not stack:  # Found matching outer brackets
                            try:
                                return json.loads(cleaned_str[start_idx : i + 1])
                            except:
                                pass

            # If all else fails, return as a string with an error note
            return {"error": f"JSON parsing failed: {str(e)}", "raw_data": cleaned_str}
    except Exception as e:
        return {"error": f"Unknown error parsing JSON: {str(e)}", "raw_data": json_str}


# Function to process query and capture technical details
def process_query_with_details(query, chat_history=None):
    """Process query and extract technical details."""
    # Initialize empty details
    technical_details = {
        "sql_query": None,
        "db_result": None,
        "api_requests": [],
        "api_result": None,
    }

    # Create a function to capture print output
    import io
    import sys
    from contextlib import redirect_stdout

    # Capture stdout to parse technical details
    f = io.StringIO()
    with redirect_stdout(f):
        try:
            # Execute agent processing
            response = process_user_query(query, chat_history)

        except Exception as e:
            response = f"Error processing query: {str(e)}"

    # Get the captured output
    output = f.getvalue()

    # Extract SQL query
    sql_match = re.search(r"Generated SQL query: (.*?)$", output, re.MULTILINE)
    if sql_match:
        technical_details["sql_query"] = sql_match.group(1).strip()

    # Extract Database Response - find JSON content after "Database response:" marker
    db_section = re.search(
        r"Database response: ([\s\S]*?)(?=\n=+|\n-+|Starting API calls|\Z)", output
    )
    if db_section:
        db_json_str = db_section.group(1).strip()
        technical_details["db_result"] = safe_json_loads(db_json_str)

    # Extract API Endpoints and Requests
    api_requests = []
    api_endpoints = re.findall(
        r"Endpoint: (.*?)$.*?Method: (.*?)$", output, re.MULTILINE | re.DOTALL
    )

    for endpoint, method in api_endpoints:
        api_requests.append({"endpoint": endpoint.strip(), "method": method.strip()})

    if api_requests:
        technical_details["api_requests"] = api_requests

    # Extract API Response - this is more complex as there might be multiple API calls
    api_responses = {}
    api_section = re.search(
        r"Starting API calls\.\.\.([\s\S]*?)(?=Generating natural language response|\Z)",
        output,
    )

    if api_section:
        api_text = api_section.group(1)
        # Find all category/plan names
        categories = re.findall(
            r"Calling API for (?:category|plan): ['\"](.*?)['\"]", api_text
        )

        # Extract JSON responses for each category
        for category in categories:
            # Look for the response section for this category
            response_pattern = rf"Calling API for (?:category|plan): ['\"]({re.escape(category)})['\"][\s\S]*?Response: ([\s\S]*?)(?=\nCalling API|\n=+|\n-+|\Z)"
            response_match = re.search(response_pattern, api_text)

            if response_match:
                api_responses[category] = safe_json_loads(
                    response_match.group(2).strip()
                )

    if api_responses:
        technical_details["api_result"] = api_responses

    return response, technical_details


# Display chat messages
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Show technical details button for assistant messages
        if message["role"] == "assistant" and i // 2 < len(
            st.session_state.technical_details
        ):
            details = st.session_state.technical_details[
                i // 2
            ]  # Every other message is from assistant
            with st.expander("Show processing details"):
                # Display technical details in the requested order

                # 1. SQL Query
                if details.get("sql_query"):
                    st.subheader("SQL Query")
                    st.code(details["sql_query"], language="sql")

                # 2. Database Response
                if details.get("db_result"):
                    st.subheader("Database Response")
                    st.json(details["db_result"])

                # 3. API Requests
                if details.get("api_requests"):
                    st.subheader("API Requests")
                    for idx, req in enumerate(details["api_requests"]):
                        st.markdown(f"**Request {idx+1}:**")
                        st.code(
                            f"Endpoint: {req['endpoint']}\nMethod: {req['method']}",
                            language="bash",
                        )

                # 4. API Response
                if details.get("api_result"):
                    st.subheader("API Response")
                    st.json(details["api_result"])


# Function to convert chat history to format expected by agent
def format_chat_history_for_agent():
    return [
        {"role": msg["role"], "content": msg["content"]}
        for msg in st.session_state.messages
    ]


# Create columns for the input field and clear button
input_col, button_col = st.columns([5, 1])

# Chat input in the first column
with input_col:
    prompt = st.chat_input("Ask me about our plans...")

# Clear button in the second column - with vertical alignment CSS
with button_col:
    # Create a container to help with vertical alignment
    clear_container = st.container()
    with clear_container:
        clear_button = st.button("Clear Chat")
        if clear_button:
            st.session_state.messages = []
            st.session_state.technical_details = []
            st.rerun()

# Process user input
if prompt:
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant thinking indication
    with st.chat_message("assistant"):
        thinking_placeholder = st.empty()
        thinking_placeholder.markdown("*Thinking...*", unsafe_allow_html=True)

        # Get response from agent
        chat_history = format_chat_history_for_agent()

        try:
            # Process the query and get response + technical details
            response, tech_details = process_query_with_details(prompt, chat_history)

            # Store the technical details
            st.session_state.technical_details.append(tech_details)

            # Replace thinking with actual response
            thinking_placeholder.empty()
            st.markdown(response)

        except Exception as e:
            # Handle errors gracefully
            error_message = f"Sorry, I encountered an error: {str(e)}"
            thinking_placeholder.empty()
            st.markdown(error_message)
            response = error_message
            st.session_state.technical_details.append({"error": str(e)})

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

    # Force a rerun to update the chat
    st.rerun()

# Footer
st.markdown("---")
st.markdown("Powered by LangGraph and Claude")
