import json
import re
from typing import List, Dict, Any, Optional, Iterator, Callable
from pydantic import BaseModel, Field, ValidationError
from abc import ABC, abstractmethod


class ActionModel(BaseModel):
    name: str = Field(..., description="Tool name")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Tool parameters"
    )


class AgentResponse(BaseModel):
    thought: str = Field(..., description="Reasoning process")
    action: Optional[ActionModel] = Field(
        default=None, description="Single action (legacy)"
    )
    actions: Optional[List[ActionModel]] = Field(
        default=None, description="Multiple parallel actions"
    )

    def get_actions(self) -> List[ActionModel]:
        if self.actions:
            return self.actions
        if self.action:
            return [self.action]
        return []

    @property
    def is_parallel(self) -> bool:
        return self.actions is not None and len(self.actions) > 1


class ResponseParser:
    @staticmethod
    def clean_and_parse(raw_text: str) -> Dict[str, Any]:
        clean_text = re.sub(r"```json\s*|\s*```", "", raw_text).strip()

        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Could not parse LLM output as JSON: {raw_text[:100]}...")


class LLMInterface(ABC):
    @abstractmethod
    def ask(self, messages: List[Dict[str, str]]) -> AgentResponse:
        raise NotImplementedError

    def ask_stream(
        self,
        messages: List[Dict[str, str]],
        on_token: Optional[Callable[[str], None]] = None,
    ) -> AgentResponse:
        return self.ask(messages)

    def _get_system_prompt_constraint(self) -> str:
        schema = AgentResponse.model_json_schema()
        return f"\nCRITICAL: Your response MUST be a valid JSON object matching this schema:\n{json.dumps(schema, indent=2)}"


class OpenRouterManager(LLMInterface):
    def __init__(
        self,
        api_key: str,
        model_id: str = "anthropic/claude-3.5-sonnet",
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        self.api_key = api_key
        self.model_id = model_id
        self.base_url = base_url
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "openai>=1.0.0 is required. Install with: pip install -U openai"
                )

            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def plan_ask(self, messages: List[Dict[str, str]]) -> str:
        client = self._get_client()

        try:
            resp = client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                extra_headers={
                    "HTTP-Referer": "https://github.com/ElephantGit/Elephan-Code.git",
                    "X-Title": "Elephan-Code",
                },
            )
            content = ""
            if resp.choices:
                msg = resp.choices[0].message
                content = msg.content or ""
            return content
        except Exception as e:
            logger.error(f"Error in OpenRouterManager.ask: {e}")
            return f"Error: {e}"

    def ask(self, messages: List[Dict[str, str]]) -> AgentResponse:
        client = self._get_client()

        try:
            resp = client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                extra_headers={
                    "HTTP-Referer": "https://github.com/ElephantGit/Elephan-Code.git",
                    "X-Title": "Elephan-Code",
                },
            )

            content = ""
            if resp.choices:
                msg = resp.choices[0].message
                content = msg.content or ""

            data_dict = ResponseParser.clean_and_parse(content)
            return AgentResponse.model_validate(data_dict)

        except ValidationError as ve:
            return AgentResponse(
                thought=f"Format error: {str(ve)}",
                action=ActionModel(
                    name="recover_from_error", parameters={"error": ve.errors()}
                ),
            )
        except Exception as e:
            return AgentResponse(
                thought="System error occurred.",
                action=ActionModel(name="system_error", parameters={"message": str(e)}),
            )

    def ask_stream(
        self,
        messages: List[Dict[str, str]],
        on_token: Optional[Callable[[str], None]] = None,
    ) -> AgentResponse:
        client = self._get_client()

        try:
            stream = client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                stream=True,
                extra_headers={
                    "HTTP-Referer": "https://github.com/ElephantGit/Elephan-Code.git",
                    "X-Title": "Elephan-Code",
                },
            )

            content = ""
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    content += token
                    if on_token:
                        on_token(token)

            data_dict = ResponseParser.clean_and_parse(content)
            return AgentResponse.model_validate(data_dict)

        except ValidationError as ve:
            return AgentResponse(
                thought=f"Format error: {str(ve)}",
                action=ActionModel(
                    name="recover_from_error", parameters={"error": ve.errors()}
                ),
            )
        except Exception as e:
            return AgentResponse(
                thought="System error occurred.",
                action=ActionModel(name="system_error", parameters={"message": str(e)}),
            )


class OpenAIManager(LLMInterface):
    def __init__(
        self, api_key: str, model_id: str = "gpt-4o", base_url: Optional[str] = None
    ):
        self.api_key = api_key
        self.model_id = model_id
        self.base_url = base_url
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "openai>=1.0.0 is required. Install with: pip install -U openai"
                )

            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def ask(self, messages: List[Dict[str, str]]) -> AgentResponse:
        client = self._get_client()

        try:
            resp = client.chat.completions.create(
                model=self.model_id, messages=messages
            )

            content = ""
            if resp.choices:
                content = resp.choices[0].message.content or ""

            data_dict = ResponseParser.clean_and_parse(content)
            return AgentResponse.model_validate(data_dict)

        except ValidationError as ve:
            return AgentResponse(
                thought=f"Format error: {str(ve)}",
                action=ActionModel(
                    name="recover_from_error", parameters={"error": ve.errors()}
                ),
            )
        except Exception as e:
            return AgentResponse(
                thought="System error occurred.",
                action=ActionModel(name="system_error", parameters={"message": str(e)}),
            )

    def ask_stream(
        self,
        messages: List[Dict[str, str]],
        on_token: Optional[Callable[[str], None]] = None,
    ) -> AgentResponse:
        client = self._get_client()

        try:
            stream = client.chat.completions.create(
                model=self.model_id, messages=messages, stream=True
            )

            content = ""
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    content += token
                    if on_token:
                        on_token(token)

            data_dict = ResponseParser.clean_and_parse(content)
            return AgentResponse.model_validate(data_dict)

        except ValidationError as ve:
            return AgentResponse(
                thought=f"Format error: {str(ve)}",
                action=ActionModel(
                    name="recover_from_error", parameters={"error": ve.errors()}
                ),
            )
        except Exception as e:
            return AgentResponse(
                thought="System error occurred.",
                action=ActionModel(name="system_error", parameters={"message": str(e)}),
            )


class AnthropicManager(LLMInterface):
    def __init__(
        self,
        api_key: str,
        model_id: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 4096,
    ):
        self.api_key = api_key
        self.model_id = model_id
        self.max_tokens = max_tokens
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from anthropic import Anthropic
            except ImportError:
                raise ImportError(
                    "anthropic is required. Install with: pip install anthropic"
                )

            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def _convert_messages(self, messages: List[Dict[str, str]]) -> tuple:
        system_prompt = ""
        converted = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_prompt = content
            else:
                anthropic_role = "assistant" if role == "assistant" else "user"
                converted.append({"role": anthropic_role, "content": content})

        return system_prompt, converted

    def ask(self, messages: List[Dict[str, str]]) -> AgentResponse:
        client = self._get_client()
        system_prompt, converted_messages = self._convert_messages(messages)

        try:
            resp = client.messages.create(
                model=self.model_id,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=converted_messages,
            )

            content = ""
            if resp.content:
                content = resp.content[0].text

            data_dict = ResponseParser.clean_and_parse(content)
            return AgentResponse.model_validate(data_dict)

        except ValidationError as ve:
            return AgentResponse(
                thought=f"Format error: {str(ve)}",
                action=ActionModel(
                    name="recover_from_error", parameters={"error": ve.errors()}
                ),
            )
        except Exception as e:
            return AgentResponse(
                thought="System error occurred.",
                action=ActionModel(name="system_error", parameters={"message": str(e)}),
            )

    def ask_stream(
        self,
        messages: List[Dict[str, str]],
        on_token: Optional[Callable[[str], None]] = None,
    ) -> AgentResponse:
        client = self._get_client()
        system_prompt, converted_messages = self._convert_messages(messages)

        try:
            content = ""
            with client.messages.stream(
                model=self.model_id,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=converted_messages,
            ) as stream:
                for text in stream.text_stream:
                    content += text
                    if on_token:
                        on_token(text)

            data_dict = ResponseParser.clean_and_parse(content)
            return AgentResponse.model_validate(data_dict)

        except ValidationError as ve:
            return AgentResponse(
                thought=f"Format error: {str(ve)}",
                action=ActionModel(
                    name="recover_from_error", parameters={"error": ve.errors()}
                ),
            )
        except Exception as e:
            return AgentResponse(
                thought="System error occurred.",
                action=ActionModel(name="system_error", parameters={"message": str(e)}),
            )


class OllamaManager(LLMInterface):
    def __init__(
        self, model_id: str = "llama3.1", base_url: str = "http://localhost:11434"
    ):
        self.model_id = model_id
        self.base_url = base_url
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from ollama import Client
            except ImportError:
                raise ImportError(
                    "ollama is required. Install with: pip install ollama"
                )

            self._client = Client(host=self.base_url)
        return self._client

    def ask(self, messages: List[Dict[str, str]]) -> AgentResponse:
        client = self._get_client()

        try:
            resp = client.chat(model=self.model_id, messages=messages)

            content = resp.get("message", {}).get("content", "")

            data_dict = ResponseParser.clean_and_parse(content)
            return AgentResponse.model_validate(data_dict)

        except ValidationError as ve:
            return AgentResponse(
                thought=f"Format error: {str(ve)}",
                action=ActionModel(
                    name="recover_from_error", parameters={"error": ve.errors()}
                ),
            )
        except Exception as e:
            return AgentResponse(
                thought="System error occurred.",
                action=ActionModel(name="system_error", parameters={"message": str(e)}),
            )

    def ask_stream(
        self,
        messages: List[Dict[str, str]],
        on_token: Optional[Callable[[str], None]] = None,
    ) -> AgentResponse:
        client = self._get_client()

        try:
            content = ""
            for chunk in client.chat(
                model=self.model_id, messages=messages, stream=True
            ):
                token = chunk.get("message", {}).get("content", "")
                if token:
                    content += token
                    if on_token:
                        on_token(token)

            data_dict = ResponseParser.clean_and_parse(content)
            return AgentResponse.model_validate(data_dict)

        except ValidationError as ve:
            return AgentResponse(
                thought=f"Format error: {str(ve)}",
                action=ActionModel(
                    name="recover_from_error", parameters={"error": ve.errors()}
                ),
            )
        except Exception as e:
            return AgentResponse(
                thought="System error occurred.",
                action=ActionModel(name="system_error", parameters={"message": str(e)}),
            )


class LLMFactory:
    PROVIDERS = {
        "openrouter": OpenRouterManager,
        "openai": OpenAIManager,
        "anthropic": AnthropicManager,
        "ollama": OllamaManager,
    }

    @staticmethod
    def get_llm(provider: str, **kwargs) -> LLMInterface:
        provider = provider.lower()

        if provider not in LLMFactory.PROVIDERS:
            available = ", ".join(LLMFactory.PROVIDERS.keys())
            raise ValueError(
                f"Provider '{provider}' not supported. Available: {available}"
            )

        manager_class = LLMFactory.PROVIDERS[provider]

        if provider == "ollama":
            return manager_class(
                model_id=kwargs.get("model_id", "llama3.1"),
                base_url=kwargs.get("base_url", "http://localhost:11434"),
            )

        api_key = kwargs.get("api_key")
        if not api_key:
            raise ValueError(f"api_key is required for provider '{provider}'")

        return manager_class(
            api_key=api_key, **{k: v for k, v in kwargs.items() if k != "api_key"}
        )

    @staticmethod
    def list_providers() -> List[str]:
        return list(LLMFactory.PROVIDERS.keys())
