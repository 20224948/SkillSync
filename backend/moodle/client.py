import requests


class MoodleClient:
    """
    Basic Moodle REST API client.

    Moodle uses one REST endpoint for all web service functions.
    The specific function is selected using the wsfunction parameter.
    """

    def __init__(self, base_url: str, token: str, rest_format: str = "json"):
        if not base_url:
            raise ValueError("MOODLE_BASE_URL is missing from the .env file.")

        if not token:
            raise ValueError("MOODLE_TOKEN is missing from the .env file.")

        # Remove trailing slash so the endpoint is built consistently.
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.rest_format = rest_format

        # Moodle's standard REST web service endpoint.
        self.endpoint = f"{self.base_url}/webservice/rest/server.php"

    def call(self, function_name: str, params: dict | None = None) -> dict | list:
        """
        Calls a Moodle web service function and returns the JSON response.
        """

        # These parameters are required for every Moodle web service request.
        payload = {
            "wstoken": self.token,
            "wsfunction": function_name,
            "moodlewsrestformat": self.rest_format,
        }

        # Add function-specific parameters if provided.
        if params:
            payload.update(params)

        response = requests.post(
            self.endpoint,
            data=payload,
            timeout=60,
        )

        # Raises an error if the HTTP request itself failed.
        response.raise_for_status()

        data = response.json()

        # Moodle often returns API errors as JSON instead of HTTP errors.
        if isinstance(data, dict) and "exception" in data:
            raise RuntimeError(
                f"Moodle API error while calling {function_name}: "
                f"{data.get('message', data)}"
            )

        return data