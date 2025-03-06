import requests


class ApiTool:
    def __init__(self, api_url):
        """
        Initializes the ApiTool object with the API base URL.
        :param api_url: The base URL for the API requests.
        """
        self.api_url = api_url

    def send_request(
        self, endpoint, method="GET", params=None, data=None, headers=None
    ):
        """
        Sends an API request and returns the response.
        :param endpoint: The API endpoint to which the request will be sent.
        :param method: The HTTP method (e.g., "GET", "POST", "PUT", "DELETE").
        :param params: URL parameters for GET requests (optional).
        :param data: Data for POST/PUT requests (optional).
        :param headers: Headers for the request (optional).
        :return: The response from the API.
        """
        url = f"{self.api_url}/{endpoint}"

        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params, headers=headers)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=headers)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, headers=headers)
            elif method.upper() == "DELETE":
                response = requests.delete(url, params=params, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Check if the request was successful (status code 200-299)
            if response.status_code >= 200 and response.status_code < 300:
                return response.json()  # Assuming the API returns JSON data
            else:
                return {
                    "error": f"Request failed with status code {response.status_code}",
                    "response": response.text,
                }

        except Exception as e:
            return {"error": f"An error occurred: {str(e)}"}


if __name__ == "__main__":
    # Example usage:
    api_tool = ApiTool("https://jsonplaceholder.typicode.com/")  # Sample API URL

    # Sending a GET request
    response = api_tool.send_request("posts/1", method="GET")
    print(response)

    # Sending a POST request
    data = {"title": "foo", "body": "bar", "userId": 1}
    response = api_tool.send_request("posts", method="POST", data=data)
    print(response)
