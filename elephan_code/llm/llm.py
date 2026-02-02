import json
import re
import requests
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
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/coding-agent", # OpenRouter 必填
        }

        # 构造 Payload
        payload = {
            "model": self.model_id,
            "messages": messages,
            "response_format": {"type": "json_object"} # 强制模型输出 JSON 模式
        }

        try:
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            raw_data = response.json()
            content = raw_data['choices'][0]['message']['content']
            
            # --- 解析与校验流程 ---
            # 1. 提取 JSON 字典
            data_dict = ResponseParser.clean_and_parse(content)
            
            # 2. Pydantic 强校验（解决 KeyError 的核心）
            return AgentResponse.model_validate(data_dict)

        except ValidationError as ve:
            # 如果字段缺失或类型错误，返回一个特殊的失败动作
            return AgentResponse(
                thought=f"I failed to follow the format: {str(ve)}",
                action=ActionModel(name="recover_from_error", parameters={"error": ve.errors()})
            )
        except Exception as e:
            # 网络或其他异常
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
