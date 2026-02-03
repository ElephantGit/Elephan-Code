from typing import List, Optional


class PromptManager:
    """管理和渲染 agent 的 system prompt。

    功能：
    - 根据可用工具与示例生成标准化 system prompt
    - 支持在运行时附加外部 schema 约束字符串
    - 可由外部注入模板或使用默认模板
    """

    DEFAULT_TEMPLATE = (
        "You are an expert, modular AI Coding Agent whose job is to accomplish developer tasks by thinking and taking tool actions.\n\n"
        "Rules (必须严格遵守):\n"
        "1) ALWAYS respond with a single VALID JSON object (no surrounding text, no Markdown) that matches the schema: {\"thought\": str, \"action\": {\"name\": str, \"parameters\": dict}}.\n"
        "2) `thought` should be a short, clear reasoning string describing intent and plan.\n"
        "3) `action.name` must be one of the available tools listed below. `action.parameters` must be a JSON object containing only the parameters required by that tool.\n"
        "4) If the task is finished, return `\"action\": {\"name\": \"finish\", \"parameters\": {}}`.\n"
        "5) On any interpretation/formatting error or inability to proceed, return `\"action\": {\"name\": \"recover_from_error\", \"parameters\": {\"error\": \"<short message>\"}}`.\n"
        "6) Do not call tools directly inside the JSON — the runtime will execute the returned `action`.\n\n"
        "Available tools and signatures (use exactly these names):\n"
    )

    def __init__(self, tools: Optional[List[str]] = None, examples: Optional[List[str]] = None, template: Optional[str] = None):
        self.tools = tools or []
        self.examples = examples or []
        self.template = template or self.DEFAULT_TEMPLATE

    def _render_tools(self) -> str:
        if not self.tools:
            return "- (no tools registered)"
        lines = []
        for t in sorted(self.tools):
            # 默认不提供复杂签名，Agent 层可以在需要时提供更精确的签名注入
            lines.append(f"- {t}")
        return "\n".join(lines)

    def _render_examples(self) -> str:
        if not self.examples:
            return ""
        return "\nExamples:\n" + "\n---\n".join(self.examples)

    def compose(self, task: Optional[str] = None, schema_constraint: Optional[str] = None, additional_tools: Optional[List[str]] = None) -> str:
        """返回最终的 system prompt 字符串。

        参数:
        - task: 可选的当前任务描述，会被追加到提示中以便 LLM 知道上下文
        - schema_constraint: 可选的额外约束（例如 pydantic schema JSON），会被追加到末尾
        - additional_tools: 运行时附加的工具名称列表
        """
        tools = list(self.tools) + (additional_tools or [])
        tools_section = "Available tools and signatures (use exactly these names):\n" + ("\n".join([f"- {t}" for t in sorted(tools)]) if tools else "- (no tools registered)")

        prompt = self.template + "\n" + tools_section + "\n\n"
        if task:
            prompt += f"Current task: {task}\n\n"
        prompt += self._render_examples()
        if schema_constraint:
            prompt += "\n" + schema_constraint
        return prompt
