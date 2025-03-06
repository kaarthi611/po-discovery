"""
Simple CLI runner for the Agent
"""

import sys
from agent import process_user_query


def main():
    """Run the agent in interactive mode."""
    print("🤖 PO Agent - Type 'exit' to quit")
    print("-----------------------------------")

    chat_history = []

    while True:
        user_input = input("\nYou: ")

        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Goodbye!")
            break

        response = process_user_query(user_input, chat_history)
        print(f"\nAgent: {response}")

        # Update chat history
        chat_history.append({"role": "user", "content": user_input})
        chat_history.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
