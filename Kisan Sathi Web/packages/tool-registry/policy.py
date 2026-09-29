"""Fail-closed workflow allowlists and effect policy."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    import yaml
except ImportError as exc:  # pragma: no cover - dependency is locked in pyproject.toml
    raise RuntimeError("PyYAML is required to load the workflow policy") from exc

try:
    from .errors import PolicyError
    from .registry import FORBIDDEN_ARGUMENT_NAMES, TOOL_REGISTRY, ToolDefinition, get_tool, model_visible_tools
except ImportError:  # pragma: no cover - direct package-path imports
    from errors import PolicyError
    from registry import FORBIDDEN_ARGUMENT_NAMES, TOOL_REGISTRY, ToolDefinition, get_tool, model_visible_tools


DEFAULT_POLICY_PATH = Path(__file__).resolve().parent / "workflows" / "kisansathi.yaml"


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    workflow: str
    tool_name: str
    allowed: bool
    effect_class: str
    confirmation_required: bool
    risk_level: str
    reason: str = "allowed"


@dataclass(frozen=True, slots=True)
class WorkflowRule:
    name: str
    allowlist: tuple[str, ...]


def _contains_forbidden_key(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key).casefold()
            if key_text in FORBIDDEN_ARGUMENT_NAMES:
                return str(key)
            found = _contains_forbidden_key(item)
            if found:
                return found
    elif isinstance(value, (list, tuple)):
        for item in value:
            found = _contains_forbidden_key(item)
            if found:
                return found
    return None


class WorkflowPolicy:
    """Policy is selected by the trusted server workflow, never by tool data."""

    def __init__(
        self,
        workflows: Mapping[str, Iterable[str]],
        *,
        prohibited_categories: Iterable[str] = (),
        prohibited_tools: Iterable[str] = (),
        deny_unknown_tool: bool = True,
        deny_unknown_workflow: bool = True,
    ) -> None:
        self.workflows = {
            str(name): WorkflowRule(str(name), tuple(str(tool) for tool in tools))
            for name, tools in workflows.items()
        }
        self.prohibited_categories = frozenset(str(item) for item in prohibited_categories)
        self.prohibited_tools = frozenset(str(item) for item in prohibited_tools)
        self.deny_unknown_tool = deny_unknown_tool
        self.deny_unknown_workflow = deny_unknown_workflow
        self._validate_configuration()

    @classmethod
    def from_yaml(cls, path: str | Path = DEFAULT_POLICY_PATH) -> "WorkflowPolicy":
        policy_path = Path(path)
        try:
            document = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise PolicyError("The workflow policy is unavailable.", code="policy_unavailable") from exc
        if not isinstance(document, dict) or document.get("version") != "1.0":
            raise PolicyError("The workflow policy version is unsupported.", code="policy_version_invalid")
        defaults = document.get("default") or {}
        workflows = document.get("workflows") or {}
        if not isinstance(workflows, dict):
            raise PolicyError("The workflow allowlists are invalid.", code="policy_invalid")
        allowlists: dict[str, Iterable[str]] = {}
        for name, rule in workflows.items():
            if not isinstance(rule, dict) or not isinstance(rule.get("allowlist"), list):
                raise PolicyError("A workflow allowlist is invalid.", code="policy_invalid")
            allowlists[str(name)] = rule["allowlist"]
        return cls(
            allowlists,
            prohibited_categories=defaults.get("prohibited_categories", ()),
            prohibited_tools=defaults.get("prohibited_tools", ()),
            deny_unknown_tool=bool(defaults.get("deny_unknown_tool", True)),
            deny_unknown_workflow=bool(defaults.get("deny_unknown_workflow", True)),
        )

    def _validate_configuration(self) -> None:
        for workflow, rule in self.workflows.items():
            if len(set(rule.allowlist)) != len(rule.allowlist):
                raise PolicyError("A workflow contains duplicate tool names.", code="policy_duplicate_tool")
            for name in rule.allowlist:
                if name not in {tool.name for tool in TOOL_REGISTRY}:
                    raise PolicyError("A workflow references an unknown tool.", code="policy_unknown_tool")
                if name in self.prohibited_tools:
                    raise PolicyError("A prohibited tool was added to a workflow.", code="policy_prohibited_tool")

    def _rule(self, workflow: str) -> WorkflowRule:
        rule = self.workflows.get(workflow)
        if rule is None:
            raise PolicyError("The requested workflow is not available.", code="unknown_workflow")
        return rule

    def is_prohibited(self, tool: ToolDefinition | str) -> bool:
        definition = get_tool(tool) if isinstance(tool, str) else tool
        return definition.name in self.prohibited_tools or definition.effect_class == "prohibited"

    def select_tools(
        self,
        workflow: str,
        *,
        provider_capabilities: Iterable[str] | None = None,
    ) -> list[ToolDefinition]:
        """Return the smallest allowlist for one trusted workflow turn."""

        rule = self._rule(workflow)
        capabilities = frozenset(provider_capabilities) if provider_capabilities is not None else None
        selected: list[ToolDefinition] = []
        for name in rule.allowlist:
            definition = get_tool(name)
            if self.is_prohibited(definition):
                continue
            if capabilities is not None and not definition.required_provider_capabilities <= capabilities:
                continue
            selected.append(definition)
        return selected

    def model_tools(
        self,
        workflow: str,
        *,
        provider_capabilities: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        return model_visible_tools(tool.name for tool in self.select_tools(workflow, provider_capabilities=provider_capabilities))

    def authorize(self, workflow: str, tool_name: str, arguments: Mapping[str, Any] | None = None) -> PolicyDecision:
        rule = self._rule(workflow)
        if tool_name not in {tool.name for tool in TOOL_REGISTRY}:
            if self.deny_unknown_tool:
                raise PolicyError("The requested tool is not registered.", code="unknown_tool")
            raise PolicyError("The requested tool is unavailable.", code="tool_unavailable")
        if tool_name in self.prohibited_tools:
            raise PolicyError("This action is prohibited by the farm safety policy.", code="prohibited_action")
        if tool_name not in rule.allowlist:
            raise PolicyError("The tool is outside the selected workflow allowlist.", code="tool_not_allowed")
        if arguments is not None:
            forbidden = _contains_forbidden_key(arguments)
            if forbidden:
                raise PolicyError("Identity, secret, authorization, and filesystem arguments are not accepted.", code="forbidden_tool_argument")
        definition = get_tool(tool_name)
        if self.is_prohibited(definition):
            raise PolicyError("This action is prohibited by the farm safety policy.", code="prohibited_action")
        return PolicyDecision(
            workflow=workflow,
            tool_name=tool_name,
            allowed=True,
            effect_class=definition.effect_class,
            confirmation_required=definition.confirmation_required,
            risk_level=definition.risk_level,
        )

    def requires_confirmation(self, workflow: str, tool_name: str) -> bool:
        return self.authorize(workflow, tool_name).confirmation_required

    def classify(self, tool_name: str) -> str:
        return get_tool(tool_name).effect_class

    def assert_no_prohibited_actions(self) -> None:
        for tool in TOOL_REGISTRY:
            if tool.name in self.prohibited_tools or tool.effect_class == "prohibited":
                raise PolicyError("A prohibited action is present in the canonical registry.", code="prohibited_registry_action")


DEFAULT_POLICY = WorkflowPolicy.from_yaml()
DEFAULT_POLICY.assert_no_prohibited_actions()
