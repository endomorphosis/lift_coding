"""MCP-IDL Profile A validator used by repository integration tests."""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any, Dict

from .base_mcp import ValidationResult


class MCPIDLValidator:
    """Validate MCP++ Profile A interface descriptor payloads."""

    REQUIRED_DESCRIPTOR_FIELDS = (
        "name",
        "namespace",
        "version",
        "methods",
        "errors",
        "requires",
        "compatibility",
    )
    RECOMMENDED_DESCRIPTOR_FIELDS = (
        "semantic_tags",
        "observability",
        "interaction_patterns",
        "resource_cost_hints",
    )

    def validate_descriptor(self, descriptor: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult(is_valid=True, message_type="interface_descriptor")
        if not isinstance(descriptor, dict):
            result.add_error("Descriptor must be an object")
            return result

        for field in self.REQUIRED_DESCRIPTOR_FIELDS:
            if field not in descriptor:
                result.add_error(f"Missing required field: {field}")

        for field in self.RECOMMENDED_DESCRIPTOR_FIELDS:
            if field not in descriptor:
                result.add_warning(f"Missing recommended field: {field}")

        if "name" in descriptor and (
            not isinstance(descriptor["name"], str) or not descriptor["name"]
        ):
            result.add_error("'name' must be a non-empty string")

        if "namespace" in descriptor and not isinstance(descriptor["namespace"], str):
            result.add_error("'namespace' must be a string")

        if "version" in descriptor:
            version = descriptor["version"]
            if not isinstance(version, str):
                result.add_error("'version' must be a string")
            elif not self._is_valid_semver(version):
                result.add_warning(f"Version should follow semantic versioning: {version}")

        if "methods" in descriptor:
            if not isinstance(descriptor["methods"], list):
                result.add_error("'methods' must be an array")
            else:
                for index, method in enumerate(descriptor["methods"]):
                    self._validate_method(method, index, result)

        if "errors" in descriptor and not isinstance(descriptor["errors"], list):
            result.add_error("'errors' must be an array")

        if "requires" in descriptor and not isinstance(descriptor["requires"], list):
            result.add_error("'requires' must be an array")

        if "compatibility" in descriptor:
            if not isinstance(descriptor["compatibility"], dict):
                result.add_error("'compatibility' must be an object")
            else:
                self._validate_compatibility(descriptor["compatibility"], result)

        if result.is_valid:
            result.metadata["interface_cid"] = self.compute_interface_cid(descriptor)

        return result

    def validate_interface_list_request(self, params: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult(is_valid=True, message_type="interfaces/list")
        if params is not None and not isinstance(params, dict):
            result.add_error("interfaces/list params must be an object when present")
        return result

    def validate_interface_get_request(self, params: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult(is_valid=True, message_type="interfaces/get")
        if not isinstance(params, dict) or "interface_cid" not in params:
            result.add_error("interfaces/get requires 'interface_cid' parameter")
        return result

    def validate_interface_compat_request(self, params: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult(is_valid=True, message_type="interfaces/compat")
        if not isinstance(params, dict):
            result.add_error("interfaces/compat params must be an object")
            return result
        for field in ("source_interface_cid", "target_interface_cid"):
            if field not in params:
                result.add_error(f"interfaces/compat requires '{field}' parameter")
        return result

    def _validate_method(
        self, method: Dict[str, Any], index: int, result: ValidationResult
    ) -> None:
        if not isinstance(method, dict):
            result.add_error(f"Method at index {index} must be an object")
            return
        if "name" not in method:
            result.add_error(f"Method at index {index} missing 'name' field")
        elif not isinstance(method["name"], str) or not method["name"]:
            result.add_error(f"Method at index {index} has invalid 'name'")
        if "input_schema_cid" not in method and "input_schema" not in method:
            result.add_warning(f"Method '{method.get('name', index)}' missing input schema")
        if "output_schema_cid" not in method and "output_schema" not in method:
            result.add_warning(f"Method '{method.get('name', index)}' missing output schema")

    @staticmethod
    def _validate_compatibility(
        compatibility: Dict[str, Any], result: ValidationResult
    ) -> None:
        for field in ("compatible_with", "supersedes"):
            if field in compatibility and not isinstance(compatibility[field], list):
                result.add_error(f"'{field}' must be an array")

    @staticmethod
    def _is_valid_semver(version: str) -> bool:
        parts = version.split(".")
        return len(parts) == 3 and all(part.isdigit() for part in parts)

    @staticmethod
    def compute_interface_cid(descriptor: Dict[str, Any]) -> str:
        canonical = json.dumps(descriptor, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).digest()
        encoded = base64.b32encode(digest).decode("ascii").lower().rstrip("=")
        return f"bafy{encoded}"
