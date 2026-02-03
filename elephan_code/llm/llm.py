import json
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError


class ActionModel(BaseModel):
    """定义 Agent 执行的具体动作结构"""
    name: str = Field(..., description="工具名称")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="工具参数")

class AgentResponse(BaseModel):
    """定义 LLM 返回的标准化结构"""
    thought: str = Field(..., description="思考过程")
    action: ActionModel = Field(..., description="下一步动作")


class ResponseParser:
    @staticmethod
    def clean_and_parse(raw_text: str) -> Dict[str, Any]:
        """从杂乱的文本中提取 JSON"""
        # 移除可能的 Markdown 代码块标记
        clean_text = re.sub(r'```json\s*|\s*```', '', raw_text).strip()
        
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试用正则提取第一个 { 到最后一个 }
            match = re.search(r'(\{.*\})', raw_text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Could not parse LLM output as JSON: {raw_text[:100]}...")


class LLMInterface:
    """LLM 抽象基类"""
    def ask(self, messages: List[Dict[str, str]]) -> AgentResponse:
        raise NotImplementedError

class OpenRouterManager(LLMInterface):
    """通过 OpenRouter 调用各类模型"""
    
    def __init__(
        self, 
        api_key: str, 
        model_id: str = "anthropic/claude-3.5-sonnet",
        base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    ):
        self.api_key = api_key
        self.model_id = model_id
        self.base_url = base_url

    def _get_system_prompt_constraint(self) -> str:
        """生成 Pydantic Schema 的描述，嵌入到 Prompt 中"""
        schema = AgentResponse.model_json_schema()
        return f"\nCRITICAL: Your response MUST be a valid JSON object matching this schema:\n{json.dumps(schema, indent=2)}"

    def ask(self, messages: List[Dict[str, str]]) -> AgentResponse:
        # Use OpenAI python client configured to point at OpenRouter's OpenAI-compatible endpoint.
        try:
            import openai
        except Exception as ie:
            raise ImportError("openai package is required to use OpenRouterManager via OpenAI client. Install with `pip install openai`.") from ie

        # Configure openai client to target OpenRouter base
        api_base = self.base_url
        if api_base.endswith('/chat/completions'):
            api_base = api_base.rsplit('/chat/completions', 1)[0]

        openai.api_key = self.api_key
        openai.base_url = api_base


        try:
            # Use OpenAI client v1 style: from openai import OpenAI; client = OpenAI(...)
            try:
                from openai import OpenAI
            except Exception:
                # Older openai package may expose OpenAI differently; re-raise informative error
                raise ImportError("openai>=1.0.0 is required for OpenRouterManager client integration.\n"
                                  "Install/upgrade with: pip install -U openai")

            client = OpenAI(api_key=self.api_key, 
                            base_url=api_base,
                            )
            resp = client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                extra_headers={
                    "HTTP-Referer": "https://github.com/ElephantGit/Elephan-Code.git", # Required for OpenRouter rankings
                    "X-Title": "Elephatn-Code",                  # Optional but recommended
                }     
            )

            # Extract content from response (support dict or attribute access)
            content = ''
            choices = getattr(resp, 'choices', None) or resp.get('choices', [])
            if choices:
                first = choices[0]
                # support both dict and object forms
                if isinstance(first, dict):
                    msg = first.get('message') or first.get('message', {})
                    if isinstance(msg, dict):
                        content = msg.get('content', '')
                    else:
                        content = ''
                else:
                    msg = getattr(first, 'message', None)
                    content = getattr(msg, 'content', '') if msg is not None else ''

            # --- 解析与校验流程 ---
            data_dict = ResponseParser.clean_and_parse(content)
            return AgentResponse.model_validate(data_dict)

        except ValidationError as ve:
            return AgentResponse(
                thought=f"I failed to follow the format: {str(ve)}",
                action=ActionModel(name="recover_from_error", parameters={"error": ve.errors()})
            )
        except Exception as e:
            return AgentResponse(
                thought="System error occurred.",
                action=ActionModel(name="system_error", parameters={"message": str(e)})
            )


class LLMFactory:
    @staticmethod
    def get_llm(provider: str, **kwargs) -> LLMInterface:
        if provider == "openrouter":
            return OpenRouterManager(
                api_key=kwargs.get("api_key"),
                model_id=kwargs.get("model_id")
            )
        # 后续可以轻松添加 OpenAI, Anthropic, Ollama 等实现
        raise ValueError(f"Provider {provider} not supported.")
