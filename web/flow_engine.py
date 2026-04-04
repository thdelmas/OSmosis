"""Universal flow engine for multi-step device operations.

Evaluates declarative flow definitions (YAML) against device state
to produce a resolved step tree with statuses, blocking reasons,
and template-expanded action payloads.

The engine does NOT execute steps — it only evaluates which steps
are visible, blocked, or available. Execution goes through existing
route endpoints and the Task system.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResolvedStep:
    """A flow step with its status computed against current context."""

    id: str
    name: str
    description: str = ""
    type: str = "task"  # task, choice, rom_picker, user_input, info, api_call
    action: dict = field(default_factory=dict)
    status: str = "available"  # available, blocked, done, hidden, active
    reason: str = ""
    input_fields: list[dict] = field(default_factory=list)
    physical_steps: list[str] = field(default_factory=list)
    options: list[dict] = field(default_factory=list)
    children: list[ResolvedStep] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "action": self.action,
            "status": self.status,
            "reason": self.reason,
            "input_fields": self.input_fields,
            "physical_steps": self.physical_steps,
            "options": [_resolve_option(o) for o in self.options],
            "children": [c.to_dict() for c in self.children],
            "metadata": self.metadata,
        }


def _resolve_option(opt: dict) -> dict:
    """Ensure option is JSON-serializable."""
    return {
        "id": opt.get("id", ""),
        "label": opt.get("label", ""),
        "description": opt.get("description", ""),
        "status": opt.get("status", "available"),
        "reason": opt.get("reason", ""),
    }


class FlowEngine:
    """Evaluates flow definitions against a context dict."""

    def evaluate(self, flow_def: dict, context: dict) -> dict:
        """Evaluate a flow definition against the given context.

        Args:
            flow_def: Parsed YAML flow definition.
            context: Dict of device state, user choices, etc.

        Returns:
            Dict with resolved steps, diagnosis, warnings, and recommendations.
        """
        steps_def = flow_def.get("steps", [])
        resolved = []
        completed_ids = set(context.get("_completed_steps", []))

        for step_def in steps_def:
            step = self._resolve_step(step_def, context, completed_ids)
            if step:
                resolved.append(step)

        # Build diagnosis
        diagnosis = self._diagnose(context, flow_def)
        warnings = self._warnings(context, flow_def)
        recommended = self._recommend(resolved, context)

        return {
            "flow_id": flow_def.get("id", ""),
            "flow_name": flow_def.get("name", ""),
            "description": flow_def.get("description", ""),
            "steps": [s.to_dict() for s in resolved],
            "diagnosis": diagnosis,
            "warnings": warnings,
            "recommended_step": recommended,
            "context_summary": {
                k: v
                for k, v in context.items()
                if not k.startswith("_")
                and not isinstance(v, (bytes, memoryview))
            },
        }

    def _resolve_step(
        self, step_def: dict, context: dict, completed: set
    ) -> ResolvedStep | None:
        """Resolve a single step definition against context."""
        step_id = step_def.get("id", "")

        # Check 'when' conditions — if not met, step is hidden
        when = step_def.get("when", {})
        if when and not self._check_conditions(when, context):
            return None

        # Determine status
        status = "available"
        reason = ""

        if step_id in completed:
            status = "done"

        # Check blocked_when
        for block in step_def.get("blocked_when", []):
            cond = block.get("condition", "")
            if self._eval_condition_expr(cond, context):
                status = "blocked"
                reason = self._expand_template(block.get("reason", ""), context)
                break

        # Check depends_on
        for dep in step_def.get("depends_on", []):
            if dep not in completed:
                if status != "done":
                    status = "blocked"
                    reason = reason or f"Complete '{dep}' first"
                break

        # Resolve action templates
        action = step_def.get("action", {})
        if isinstance(action, dict):
            action = {
                k: self._expand_template(v, context)
                if isinstance(v, str)
                else v
                for k, v in action.items()
            }
            # Expand body templates
            if "body" in action and isinstance(action["body"], dict):
                action["body"] = {
                    k: self._expand_template(v, context)
                    if isinstance(v, str)
                    else v
                    for k, v in action["body"].items()
                }

        # Resolve options for choice steps
        options = []
        for opt_def in step_def.get("options", []):
            opt = dict(opt_def)
            opt_when = opt.pop("when", {})
            opt_always = opt.pop("always", False)
            if (
                opt_always
                or not opt_when
                or self._check_conditions(opt_when, context)
            ):
                opt["status"] = "available"
            else:
                opt["status"] = "blocked"
                opt["reason"] = "Not available for this device state"
            options.append(opt)

        # Resolve children recursively
        children = []
        for child_def in step_def.get("children", []):
            child = self._resolve_step(child_def, context, completed)
            if child:
                children.append(child)

        return ResolvedStep(
            id=step_id,
            name=step_def.get("name", step_id),
            description=self._expand_template(
                step_def.get("description", ""), context
            ),
            type=step_def.get("type", "task"),
            action=action,
            status=status,
            reason=reason,
            input_fields=step_def.get("input_fields", []),
            physical_steps=step_def.get("physical_steps", []),
            options=options,
            children=children,
            metadata=step_def.get("metadata", {}),
        )

    def _check_conditions(self, conditions: dict, context: dict) -> bool:
        """Check if all conditions match the context.

        Conditions are simple key-value checks:
            mode: sideload          → context['mode'] == 'sideload'
            mode: [sideload, fastboot] → context['mode'] in [...]
            bl_locked: true         → context['bl_locked'] == True
            is_cross_flashed: false → context['is_cross_flashed'] == False
            path_chosen: fastboot   → context['path_chosen'] == 'fastboot'
        """
        for key, expected in conditions.items():
            actual = self._get_nested(context, key)

            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif isinstance(expected, bool):
                if bool(actual) != expected:
                    return False
            else:
                if str(actual) != str(expected):
                    return False
        return True

    def _eval_condition_expr(self, expr: str, context: dict) -> bool:
        """Evaluate a simple condition expression.

        Supports: 'key == value', 'key != value', 'key == null',
                  'key == true', 'key == false'
        """
        if not expr:
            return False

        for op in ("!=", "=="):
            if op in expr:
                left, right = [s.strip() for s in expr.split(op, 1)]
                actual = self._get_nested(context, left)

                if right == "null":
                    result = actual is None
                elif right == "true":
                    result = bool(actual)
                elif right == "false":
                    result = not bool(actual)
                else:
                    result = str(actual) == right

                return result if op == "==" else not result

        # Simple truthy check
        return bool(self._get_nested(context, expr))

    def _get_nested(self, context: dict, key: str) -> Any:
        """Get a value from context, supporting dotted paths."""
        parts = key.split(".")
        val = context
        for part in parts:
            if isinstance(val, dict):
                val = val.get(part)
            else:
                return None
        return val

    def _expand_template(self, template: str, context: dict) -> str:
        """Expand {{key}} templates in a string."""
        if not isinstance(template, str) or "{{" not in template:
            return template

        def replace(match):
            key = match.group(1).strip()
            val = self._get_nested(context, key)
            return str(val) if val is not None else ""

        return re.sub(r"\{\{(.+?)\}\}", replace, template)

    def _diagnose(self, context: dict, flow_def: dict) -> dict:
        """Generate a diagnosis from flow-level diagnosis rules."""
        rules = flow_def.get("diagnosis", [])
        issues = []

        for rule in rules:
            when = rule.get("when", {})
            if self._check_conditions(when, context):
                issues.append(
                    {
                        "id": rule.get("id", ""),
                        "severity": rule.get("severity", "info"),
                        "title": self._expand_template(
                            rule.get("title", ""), context
                        ),
                        "detail": self._expand_template(
                            rule.get("detail", ""), context
                        ),
                    }
                )

        if not issues:
            issues.append(
                {
                    "id": "ok",
                    "severity": "info",
                    "title": "Device is ready",
                    "detail": "",
                }
            )

        severity = "info"
        for issue in issues:
            if issue["severity"] == "critical":
                severity = "critical"
            elif issue["severity"] == "warning" and severity != "critical":
                severity = "warning"

        return {"issues": issues, "severity": severity}

    def _warnings(self, context: dict, flow_def: dict) -> list[dict]:
        """Generate warnings from flow-level warning rules."""
        rules = flow_def.get("warnings", [])
        result = []
        for rule in rules:
            when = rule.get("when", {})
            if self._check_conditions(when, context):
                result.append(
                    {
                        "type": rule.get("type", "info"),
                        "message": self._expand_template(
                            rule.get("message", ""), context
                        ),
                    }
                )
        return result

    def _recommend(
        self, steps: list[ResolvedStep], context: dict
    ) -> str | None:
        """Return the ID of the first available step."""
        for step in steps:
            if step.status == "available":
                return step.id
        return None
