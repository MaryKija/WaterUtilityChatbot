"""backend/tool_executor.py

Tool executor for managing and executing tools.

Handles:
- Tool registration with schemas
- Tool execution with parameter validation
- Result processing
"""

from __future__ import annotations

import inspect
import json
from typing import Any, Dict, Optional

from .logger import logger
from .tools import (
    log_complaint,
    get_complaint_status,
    get_bill,
    escalate_to_human,
    get_payment_methods,
    get_office_info,
    create_connection_request,
)


class ToolExecutor:
    """Executor for registered tools."""

    def __init__(self):
        self.tools = {}
        self._register_tools()

    def _register_tools(self):
        """Register all available tools with their schemas."""
        self.tools = {
            "log_complaint": {
                "function": log_complaint,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "area": {"type": "string"},
                        "issue": {"type": "string"}
                    },
                    "required": ["name", "area", "issue"]
                },
                "output_schema": {"type": "string"}
            },
            "get_complaint_status": {
                "function": get_complaint_status,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ticket_id": {"type": "string"}
                    },
                    "required": ["ticket_id"]
                },
                "output_schema": {"type": "string"}
            },
            "get_bill": {
                "function": get_bill,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "account_number": {"type": "string"}
                    },
                    "required": ["account_number"]
                },
                "output_schema": {"type": "string"}
            },
            "escalate_to_human": {
                "function": escalate_to_human,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "include_account_number": {"type": "boolean"}
                    },
                    "required": []
                },
                "output_schema": {"type": "string"}
            },
            "get_payment_methods": {
                "function": get_payment_methods,
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "output_schema": {"type": "string"}
            },
            "get_office_info": {
                "function": get_office_info,
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "output_schema": {"type": "string"}
            },
            "create_connection_request": {
                "function": create_connection_request,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "address": {"type": "string"},
                        "phone": {"type": "string"},
                        "email": {"type": "string"}
                    },
                    "required": ["name", "address", "phone", "email"]
                },
                "output_schema": {"type": "string"}
            }
        }

    def execute(self, tool_name: str, parameters: dict, context: dict) -> Any:
        """Execute a tool with given parameters."""
        if tool_name not in self.tools:
            logger.error(f"Tool not found: {tool_name}")
            return f"Error: Tool '{tool_name}' not found."

        tool_info = self.tools[tool_name]

        try:
            # Validate parameters
            self._validate_parameters(parameters, tool_info["input_schema"])

            # Execute tool
            function = tool_info["function"]
            result = self._call_tool(function, parameters)

            # Update context if needed
            self._update_context_after_execution(tool_name, parameters, result, context)

            logger.info(f"Tool executed successfully: {tool_name}")
            return result

        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}, error: {e}")
            return f"Error executing {tool_name}: {str(e)}"

    def _call_tool(self, function, parameters: dict) -> Any:
        """Call tools that accept either keyword args or a single payload dict."""
        signature = inspect.signature(function)
        params = list(signature.parameters.values())

        accepts_var_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)
        if accepts_var_kwargs:
            return function(**parameters)

        positional_params = [
            p for p in params
            if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        keyword_only_params = [
            p for p in params
            if p.kind == inspect.Parameter.KEYWORD_ONLY
        ]

        if len(positional_params) == 1 and not keyword_only_params:
            return function(parameters)

        return function(**parameters)

    def _validate_parameters(self, parameters: dict, schema: dict):
        """Validate parameters against schema."""
        required = schema.get("required", [])
        for field in required:
            if field not in parameters:
                raise ValueError(f"Missing required parameter: {field}")

        # Basic type checking
        properties = schema.get("properties", {})
        for param, value in parameters.items():
            if param in properties:
                expected_type = properties[param].get("type")
                if expected_type == "string" and not isinstance(value, str):
                    raise ValueError(f"Parameter {param} must be a string")
                elif expected_type == "boolean" and not isinstance(value, bool):
                    raise ValueError(f"Parameter {param} must be a boolean")

    def _update_context_after_execution(self, tool_name: str, parameters: dict, result: Any, context: dict):
        """Update context after tool execution."""
        from .context_engine import context_manager

        if tool_name == "log_complaint" and isinstance(result, str):
            # Extract ticket ID from result
            import re
            ticket_match = re.search(r"WC-[A-Z0-9]{6}", result)
            if ticket_match:
                entities = context.get("entities", {})
                entities["ticket_id"] = ticket_match.group(0)
                context["entities"] = entities

        elif tool_name == "get_bill":
            # Mark billing inquiry as complete
            pass

        elif tool_name == "create_connection_request":
            # Mark connection request as complete
            pass

    def get_available_tools(self) -> list[str]:
        """Get list of available tool names."""
        return list(self.tools.keys())

    def get_tool_schema(self, tool_name: str) -> Optional[dict]:
        """Get schema for a specific tool."""
        tool_info = self.tools.get(tool_name)
        if tool_info:
            return {
                "input_schema": tool_info["input_schema"],
                "output_schema": tool_info["output_schema"]
            }
        return None


# Global tool executor instance
tool_executor = ToolExecutor()
