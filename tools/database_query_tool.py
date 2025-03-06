import mysql.connector
import json
import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv


class DatabaseQueryTool:
    """
    Agent tool to connect to a MySQL database (including AWS RDS) and execute SQL queries.
    Returns results in JSON format.
    """

    def __init__(self):
        # Load environment variables from .env file automatically
        load_dotenv()

        # Get connection params from environment variables
        self.connection_params = {
            "database": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT", "3306"),
        }

        # Validate required parameters
        required_params = ["database", "user", "password", "host"]
        missing_params = [
            param for param in required_params if not self.connection_params.get(param)
        ]

        if missing_params:
            raise ValueError(
                f"Missing required environment variables: {', '.join(['DB_' + p.upper() for p in missing_params])}"
            )

        self.conn = None

    def connect(self) -> None:
        """Establish connection to the MySQL database."""
        try:
            self.conn = mysql.connector.connect(**self.connection_params)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to MySQL database: {str(e)}")

    def execute_query(self, query: str) -> Dict[str, Any]:
        """
        Execute SQL query and return results as JSON.

        Args:
            query: SQL query to execute

        Returns:
            Dictionary with query results and metadata
        """
        if not self.conn or not self.conn.is_connected():
            self.connect()

        try:
            # Create cursor
            cursor = self.conn.cursor(dictionary=True)

            # Execute query
            cursor.execute(query)

            # Fetch results if it's a SELECT query
            if query.strip().lower().startswith("select"):
                results_list = cursor.fetchall()
            else:
                results_list = []

            # Get row count for operations
            row_count = cursor.rowcount

            # Get last inserted id if applicable
            last_id = cursor.lastrowid if hasattr(cursor, "lastrowid") else None

            # Commit if this was a write operation
            if not query.strip().lower().startswith("select"):
                self.conn.commit()

            cursor.close()

            # Create a result that's fully JSON serializable
            serializable_results = []
            for row in results_list:
                serializable_row = {}
                for key, value in row.items():
                    # Convert non-serializable types to strings
                    if isinstance(value, (bytes, bytearray)):
                        serializable_row[key] = value.decode("utf-8", errors="replace")
                    else:
                        serializable_row[key] = value
                serializable_results.append(serializable_row)

            # Return JSON-serializable result
            result = {
                "success": True,
                "results": serializable_results,
                "row_count": row_count,
                "message": f"Query executed successfully. Returned {len(serializable_results)} rows.",
            }

            if last_id:
                result["last_insert_id"] = last_id

            return result

        except Exception as e:
            # Rollback on error
            if self.conn and self.conn.is_connected():
                self.conn.rollback()

            # Return error information
            return {
                "success": False,
                "results": [],
                "row_count": 0,
                "error": str(e),
                "message": f"Query execution failed: {str(e)}",
            }

    def close(self) -> None:
        """Close the database connection."""
        if self.conn and self.conn.is_connected():
            self.conn.close()
            self.conn = None

    def __call__(self, query: str) -> str:
        """
        Call the tool directly with just the SQL query and return JSON string.

        Args:
            query: SQL query to execute

        Returns:
            JSON string with query results
        """
        result = self.execute_query(query)
        return json.dumps(result, default=str, indent=2)

    def __del__(self):
        """Ensure connection is closed when object is destroyed."""
        self.close()


# Example usage as an agent tool
if __name__ == "__main__":
    # Create the tool - it will automatically load from .env file
    db_tool = DatabaseQueryTool()

    # Example query - just pass the query
    query = "select * from podiscovery.plans"

    # Execute and get JSON result
    result_json = db_tool(query)
    print(result_json)

    # Close connection
    db_tool.close()
