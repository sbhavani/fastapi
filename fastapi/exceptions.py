from collections.abc import Mapping, Sequence
from difflib import get_close_matches
from typing import Annotated, Any, TypedDict

from annotated_doc import Doc
from pydantic import BaseModel, create_model
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.exceptions import WebSocketException as StarletteWebSocketException


# Field name suggestions cache for performance
_field_suggestion_cache: dict[str, list[str]] = {}


def _get_field_suggestion(
    field_name: str, expected_fields: Sequence[str]
) -> list[str]:
    """Get similar field name suggestions using cached results."""
    cache_key = f"{field_name}:{','.join(sorted(expected_fields))}"
    if cache_key in _field_suggestion_cache:
        return _field_suggestion_cache[cache_key]

    if not expected_fields:
        _field_suggestion_cache[cache_key] = []
        return []

    # Use difflib's get_close_matches for finding similar field names
    suggestions = get_close_matches(field_name, expected_fields, n=3, cutoff=0.6)
    _field_suggestion_cache[cache_key] = suggestions
    return suggestions


def _extract_expected_fields_from_loc(
    loc: tuple[int | str, ...], all_loc_fields: dict[str, list[str]]
) -> list[str]:
    """Extract expected field names based on location prefix."""
    if not loc:
        return []

    # Convert loc to string path
    loc_path = ()
    for item in loc:
        if isinstance(item, str):
            loc_path = loc_path + (item,)
            # Check if we have fields for this path
            if loc_path in all_loc_fields:
                return all_loc_fields[loc_path]

    # Try partial matches
    for i in range(len(loc), 0, -1):
        partial_loc = loc[:i]
        if partial_loc in all_loc_fields:
            return all_loc_fields[partial_loc]

    return []


def _generate_example_for_type(type_hint: Any) -> Any:
    """Generate a simple example value based on type hint."""
    type_str = str(type_hint)

    # Handle common types
    if "int" in type_str.lower():
        return 0
    elif "float" in type_str.lower():
        return 0.0
    elif "str" in type_str.lower():
        return "string"
    elif "bool" in type_str.lower():
        return True
    elif "list" in type_str.lower() or "Sequence" in type_str:
        return []
    elif "dict" in type_str.lower() or "Mapping" in type_str:
        return {}
    elif "None" in type_str or "null" in type_str.lower():
        return None

    return None


def _extract_fields_from_input(input_data: Any, loc: tuple[int | str, ...]) -> list[str]:
    """Extract available field names from the input data based on location."""
    if not input_data:
        return []

    # Special case: if loc starts with 'body', the input_data is the body directly
    # not nested under 'body' key
    if loc and loc[0] == "body" and isinstance(input_data, dict):
        # Check if 'body' is actually in the input (nested case)
        if "body" in input_data and isinstance(input_data["body"], dict):
            input_data = input_data["body"]
        else:
            # The input is the body directly, so return its keys
            return list(input_data.keys())

    if not isinstance(input_data, dict):
        return []

    # Navigate through the location to find the relevant dict
    current = input_data
    for item in loc:
        # Skip 'body' prefix as we handled it above
        if item == "body":
            continue
        if isinstance(item, str) and item in current:
            current = current[item]
            if not isinstance(current, dict):
                return []
        elif isinstance(item, int):
            # For list indices, return empty as we can't suggest field names
            return []
        else:
            # If the key is not found, return the keys from the current level
            # This handles the case where the error is about a missing field
            if isinstance(current, dict):
                return list(current.keys())
            return []

    # Return all keys from the current dict
    if isinstance(current, dict):
        return list(current.keys())
    return []


def enhance_validation_errors(
    errors: Sequence[Any],
    expected_fields: dict[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    """
    Enhance validation errors with:
    - Similar field names suggestions for missing/extra fields
    - Example corrections in the error detail

    Args:
        errors: Sequence of validation error dictionaries
        expected_fields: Optional dict mapping location prefixes to expected field names

    Returns:
        Enhanced list of error dictionaries with suggestions and examples
    """
    if expected_fields is None:
        expected_fields = {}

    enhanced_errors = []

    for error in errors:
        enhanced_error = dict(error)
        error_type = error.get("type", "")
        loc = error.get("loc", ())

        # Get the field name from location (last element)
        field_name = None
        if loc:
            last_loc = loc[-1]
            if isinstance(last_loc, str):
                field_name = last_loc

        # Add suggestions for missing fields
        if error_type == "missing" and field_name:
            # First try explicit expected_fields
            expected = _extract_expected_fields_from_loc(loc, expected_fields)
            # If not found, try to infer from input data
            if not expected:
                input_data = error.get("input")
                expected = _extract_fields_from_input(input_data, loc)
            if expected:
                suggestions = _get_field_suggestion(field_name, expected)
                if suggestions:
                    enhanced_error["suggestions"] = suggestions

        # Add suggestions for extra fields (unknown fields)
        elif error_type == "extra_forbidden" and field_name:
            # First try explicit expected_fields
            expected = _extract_expected_fields_from_loc(loc[:-1], expected_fields)
            # If not found, try to infer from input data
            if not expected:
                input_data = error.get("input")
                expected = _extract_fields_from_input(input_data, loc[:-1])
            if expected:
                suggestions = _get_field_suggestion(field_name, expected)
                if suggestions:
                    enhanced_error["suggestions"] = suggestions

        # Add example correction for type errors
        elif error_type in ("string_type", "int_type", "float_type", "bool_type",
                           "list_type", "dict_type", "json_invalid"):
            # Try to generate an example based on the expected type
            ctx = error.get("ctx", {})
            expected_type = ctx.get("expected_type")
            if expected_type:
                example = _generate_example_for_type(expected_type)
                if example is not None:
                    enhanced_error["example"] = example

        enhanced_errors.append(enhanced_error)

    return enhanced_errors


class EndpointContext(TypedDict, total=False):
    function: str
    path: str
    file: str
    line: int


class HTTPException(StarletteHTTPException):
    """
    An HTTP exception you can raise in your own code to show errors to the client.

    This is for client errors, invalid authentication, invalid data, etc. Not for server
    errors in your code.

    Read more about it in the
    [FastAPI docs for Handling Errors](https://fastapi.tiangolo.com/tutorial/handling-errors/).

    ## Example

    ```python
    from fastapi import FastAPI, HTTPException

    app = FastAPI()

    items = {"foo": "The Foo Wrestlers"}


    @app.get("/items/{item_id}")
    async def read_item(item_id: str):
        if item_id not in items:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"item": items[item_id]}
    ```
    """

    def __init__(
        self,
        status_code: Annotated[
            int,
            Doc(
                """
                HTTP status code to send to the client.

                Read more about it in the
                [FastAPI docs for Handling Errors](https://fastapi.tiangolo.com/tutorial/handling-errors/#use-httpexception)
                """
            ),
        ],
        detail: Annotated[
            Any,
            Doc(
                """
                Any data to be sent to the client in the `detail` key of the JSON
                response.

                Read more about it in the
                [FastAPI docs for Handling Errors](https://fastapi.tiangolo.com/tutorial/handling-errors/#use-httpexception)
                """
            ),
        ] = None,
        headers: Annotated[
            Mapping[str, str] | None,
            Doc(
                """
                Any headers to send to the client in the response.

                Read more about it in the
                [FastAPI docs for Handling Errors](https://fastapi.tiangolo.com/tutorial/handling-errors/#add-custom-headers)

                """
            ),
        ] = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class WebSocketException(StarletteWebSocketException):
    """
    A WebSocket exception you can raise in your own code to show errors to the client.

    This is for client errors, invalid authentication, invalid data, etc. Not for server
    errors in your code.

    Read more about it in the
    [FastAPI docs for WebSockets](https://fastapi.tiangolo.com/advanced/websockets/).

    ## Example

    ```python
    from typing import Annotated

    from fastapi import (
        Cookie,
        FastAPI,
        WebSocket,
        WebSocketException,
        status,
    )

    app = FastAPI()

    @app.websocket("/items/{item_id}/ws")
    async def websocket_endpoint(
        *,
        websocket: WebSocket,
        session: Annotated[str | None, Cookie()] = None,
        item_id: str,
    ):
        if session is None:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
        await websocket.accept()
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Session cookie is: {session}")
            await websocket.send_text(f"Message text was: {data}, for item ID: {item_id}")
    ```
    """

    def __init__(
        self,
        code: Annotated[
            int,
            Doc(
                """
                A closing code from the
                [valid codes defined in the specification](https://datatracker.ietf.org/doc/html/rfc6455#section-7.4.1).
                """
            ),
        ],
        reason: Annotated[
            str | None,
            Doc(
                """
                The reason to close the WebSocket connection.

                It is UTF-8-encoded data. The interpretation of the reason is up to the
                application, it is not specified by the WebSocket specification.

                It could contain text that could be human-readable or interpretable
                by the client code, etc.
                """
            ),
        ] = None,
    ) -> None:
        super().__init__(code=code, reason=reason)


RequestErrorModel: type[BaseModel] = create_model("Request")
WebSocketErrorModel: type[BaseModel] = create_model("WebSocket")


class FastAPIError(RuntimeError):
    """
    A generic, FastAPI-specific error.
    """


class DependencyScopeError(FastAPIError):
    """
    A dependency declared that it depends on another dependency with an invalid
    (narrower) scope.
    """


class ValidationException(Exception):
    def __init__(
        self,
        errors: Sequence[Any],
        *,
        endpoint_ctx: EndpointContext | None = None,
        expected_fields: dict[str, list[str]] | None = None,
    ) -> None:
        self._errors = errors
        self.endpoint_ctx = endpoint_ctx
        self._expected_fields = expected_fields

        ctx = endpoint_ctx or {}
        self.endpoint_function = ctx.get("function")
        self.endpoint_path = ctx.get("path")
        self.endpoint_file = ctx.get("file")
        self.endpoint_line = ctx.get("line")

    def errors(self) -> Sequence[Any]:
        return self._errors

    def errors_with_suggestions(self) -> list[dict[str, Any]]:
        """Return errors with field name suggestions and examples."""
        return enhance_validation_errors(
            self._errors, expected_fields=self._expected_fields
        )

    def _format_endpoint_context(self) -> str:
        if not (self.endpoint_file and self.endpoint_line and self.endpoint_function):
            if self.endpoint_path:
                return f"\n  Endpoint: {self.endpoint_path}"
            return ""

        context = f'\n  File "{self.endpoint_file}", line {self.endpoint_line}, in {self.endpoint_function}'
        if self.endpoint_path:
            context += f"\n    {self.endpoint_path}"
        return context

    def __str__(self) -> str:
        message = f"{len(self._errors)} validation error{'s' if len(self._errors) != 1 else ''}:\n"
        for err in self._errors:
            message += f"  {err}\n"
        message += self._format_endpoint_context()
        return message.rstrip()


class RequestValidationError(ValidationException):
    def __init__(
        self,
        errors: Sequence[Any],
        *,
        body: Any = None,
        endpoint_ctx: EndpointContext | None = None,
        expected_fields: dict[str, list[str]] | None = None,
    ) -> None:
        super().__init__(errors, endpoint_ctx=endpoint_ctx, expected_fields=expected_fields)
        self.body = body


class WebSocketRequestValidationError(ValidationException):
    def __init__(
        self,
        errors: Sequence[Any],
        *,
        endpoint_ctx: EndpointContext | None = None,
        expected_fields: dict[str, list[str]] | None = None,
    ) -> None:
        super().__init__(errors, endpoint_ctx=endpoint_ctx, expected_fields=expected_fields)


class ResponseValidationError(ValidationException):
    def __init__(
        self,
        errors: Sequence[Any],
        *,
        body: Any = None,
        endpoint_ctx: EndpointContext | None = None,
        expected_fields: dict[str, list[str]] | None = None,
    ) -> None:
        super().__init__(errors, endpoint_ctx=endpoint_ctx, expected_fields=expected_fields)
        self.body = body


class PydanticV1NotSupportedError(FastAPIError):
    """
    A pydantic.v1 model is used, which is no longer supported.
    """


class FastAPIDeprecationWarning(UserWarning):
    """
    A custom deprecation warning as DeprecationWarning is ignored
    Ref: https://sethmlarson.dev/deprecations-via-warnings-dont-work-for-python-libraries
    """
