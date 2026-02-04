from typing import List, Optional, Dict, Any


class PromptManager:
    """管理和渲染 agent 的 system prompt。"""

    DEFAULT_TEMPLATE = (
        "You are an expert AI Coding Agent that accomplishes developer tasks by thinking and taking tool actions.\n\n"
        "Rules:\n"
        "1) ALWAYS respond with a single VALID JSON object (no surrounding text, no Markdown).\n"
        '2) Response format for single action: {"thought": str, "action": {"name": str, "parameters": dict}}\n'
        '3) Response format for parallel actions: {"thought": str, "actions": [{"name": str, "parameters": dict}, ...]}\n'
        "4) `thought` should be clear reasoning describing your intent and plan.\n"
        "5) Tool names must match available tools. Parameters must match tool requirements.\n"
        "6) Use `actions` (plural) when multiple independent operations can run in parallel.\n"
        '7) When task is finished, return `"action": {"name": "finish", "parameters": {}}`.\n'
        '8) On errors, return `"action": {"name": "recover_from_error", "parameters": {"error": "<message>"}}`.\n'
        "9) Do not call tools inside JSON - the runtime executes the returned action(s).\n\n"
    )

    def __init__(
        self,
        tools: Optional[List[str]] = None,
        tools_prompt: Optional[str] = None,
        examples: Optional[List[str]] = None,
        template: Optional[str] = None,
    ):
        self.tools = tools or []
        self.tools_prompt = tools_prompt
        self.examples = examples or []
        self.template = template or self.DEFAULT_TEMPLATE

    def _render_tools(self) -> str:
        if self.tools_prompt:
            return self.tools_prompt
        if not self.tools:
            return "- (no tools registered)"
        lines = []
        for t in sorted(self.tools):
            lines.append(f"- {t}")
        return "\n".join(lines)

    def _render_examples(self) -> str:
        if not self.examples:
            return ""
        return "\nExamples:\n" + "\n---\n".join(self.examples)

    def compose(
        self,
        task: Optional[str] = None,
        schema_constraint: Optional[str] = None,
        additional_tools: Optional[List[str]] = None,
    ) -> str:
        tools_section = "Available tools:\n" + self._render_tools()

        if additional_tools:
            tools_section += "\n" + "\n".join(
                [f"- {t}" for t in sorted(additional_tools)]
            )

        prompt = self.template + tools_section + "\n\n"
        if task:
            prompt += f"Current task: {task}\n\n"
        prompt += self._render_examples()
        if schema_constraint:
            prompt += "\n" + schema_constraint
        return prompt
