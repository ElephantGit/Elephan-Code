import json
from typing import Optional, Callable, Any, List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

from elephan_code.llm.llm import LLMInterface, ActionModel
from elephan_code.llm.prompt_manager import PromptManager
from elephan_code.tools import ToolManager
from elephan_code.utils.trajectory import TrajectoryRecorder
from elephan_code.utils.logging import get_logger

logger = get_logger("elephan.agent")


DEFAULT_MAX_STEPS = 10
DEFAULT_MAX_MEMORY_MESSAGES = 50
DEFAULT_CONTEXT_WINDOW_TOKENS = 8000
DEFAULT_MAX_PARALLEL_TOOLS = 5


class Agent:
    def __init__(
        self,
        llm: LLMInterface,
        tools: ToolManager,
        max_steps: int = DEFAULT_MAX_STEPS,
        max_memory_messages: int = DEFAULT_MAX_MEMORY_MESSAGES,
        context_window_tokens: int = DEFAULT_CONTEXT_WINDOW_TOKENS,
        max_parallel_tools: int = DEFAULT_MAX_PARALLEL_TOOLS,
        enable_parallel: bool = True,
    ):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.max_memory_messages = max_memory_messages
        self.context_window_tokens = context_window_tokens
        self.max_parallel_tools = max_parallel_tools
        self.enable_parallel = enable_parallel

        tools_prompt = self.tools.get_tools_prompt()
        self.prompt_manager = PromptManager(tools_prompt=tools_prompt)

        schema_constraint = self._get_schema_constraint()

        self.memory: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": self.prompt_manager.compose(
                    schema_constraint=schema_constraint
                ),
            }
        ]
        self.trajectory: Optional[TrajectoryRecorder] = None
        self.on_thought: Optional[Callable[[str], None]] = None
        self.on_action: Optional[Callable[[str, dict], None]] = None
        self.on_observation: Optional[Callable[[str], None]] = None

    def _get_schema_constraint(self) -> Optional[str]:
        try:
            if hasattr(self.llm, "_get_system_prompt_constraint"):
                return self.llm._get_system_prompt_constraint()
        except Exception:
            pass
        return None

    def _generate_system_prompt(self) -> str:
        schema_constraint = self._get_schema_constraint()
        return self.prompt_manager.compose(schema_constraint=schema_constraint)

    def _estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def _truncate_memory(self) -> None:
        if len(self.memory) <= 2:
            return

        total_tokens = sum(
            self._estimate_tokens(m.get("content", "")) for m in self.memory
        )

        while len(self.memory) > 2 and (
            len(self.memory) > self.max_memory_messages
            or total_tokens > self.context_window_tokens
        ):
            removed = self.memory.pop(1)
            total_tokens -= self._estimate_tokens(removed.get("content", ""))

    def step(self) -> bool:
        self._truncate_memory()

        response_data = self.llm.ask(self.memory)
        self.memory.append(
            {
                "role": "assistant",
                "content": json.dumps(response_data.model_dump_json()),
            }
        )

        logger.info("[Thought]: %s", response_data.thought)

        if self.on_thought:
            self.on_thought(str(response_data.thought))

        try:
            if self.trajectory:
                self.trajectory.record_thought(str(response_data.thought))
        except Exception:
            pass

        actions = response_data.get_actions()

        if not actions:
            return False

        if any(a.name == "finish" for a in actions):
            return False

        if self.enable_parallel and len(actions) > 1:
            observations = self._execute_parallel(actions)
        else:
            observations = self._execute_sequential(actions)

        combined_obs = "\n---\n".join(observations)

        logger.info("[Observation]: %s", combined_obs)

        if self.on_observation:
            self.on_observation(combined_obs)

        try:
            if self.trajectory:
                self.trajectory.record_observation(combined_obs)
        except Exception:
            pass

        self.memory.append({"role": "user", "content": f"Observation: {combined_obs}"})

        return True

    def _execute_sequential(self, actions: List[ActionModel]) -> List[str]:
        observations = []
        for action in actions:
            try:
                params = self._extract_params(action.parameters)
            except Exception:
                params = {}

            logger.info("[Action]: %s(%s)", action.name, params)

            if self.on_action:
                self.on_action(action.name, params)

            try:
                if self.trajectory:
                    self.trajectory.record_action(action.name, params)
            except Exception:
                pass

            observation = self.tools.call(action.name, params)
            obs_str = self._format_observation(observation)
            observations.append(f"[{action.name}]: {obs_str}")

        return observations

    def _execute_parallel(self, actions: List[ActionModel]) -> List[str]:
        actions_to_run = actions[: self.max_parallel_tools]
        results: Dict[int, str] = {}

        def run_action(idx: int, action: ActionModel) -> tuple:
            try:
                params = self._extract_params(action.parameters)
            except Exception:
                params = {}

            logger.info("[Action %d]: %s(%s)", idx, action.name, params)

            if self.on_action:
                self.on_action(action.name, params)

            try:
                if self.trajectory:
                    self.trajectory.record_action(action.name, params)
            except Exception:
                pass

            observation = self.tools.call(action.name, params)
            obs_str = self._format_observation(observation)
            return idx, f"[{action.name}]: {obs_str}"

        with ThreadPoolExecutor(max_workers=self.max_parallel_tools) as executor:
            futures = {
                executor.submit(run_action, i, action): i
                for i, action in enumerate(actions_to_run)
            }
            for future in as_completed(futures):
                try:
                    idx, result = future.result()
                    results[idx] = result
                except Exception as e:
                    idx = futures[future]
                    results[idx] = f"[Error]: {str(e)}"

        return [results[i] for i in sorted(results.keys())]

    def _extract_params(self, parameters: Any) -> dict:
        if isinstance(parameters, dict):
            return parameters
        if hasattr(parameters, "model_dump"):
            return parameters.model_dump()
        if hasattr(parameters, "dict"):
            return parameters.dict()
        return {}

    def _format_observation(self, observation: Any) -> str:
        try:
            from elephan_code.tools.base_tool import ToolResult as _ToolResult

            if isinstance(observation, _ToolResult):
                if observation.success:
                    if isinstance(observation.data, str):
                        return observation.data
                    return json.dumps(observation.data, ensure_ascii=False)
                return f"Error: {observation.error}"
            return str(observation)
        except Exception:
            return str(observation)

    def run(self, task: str) -> None:
        self.memory.append({"role": "user", "content": task})
        if self.trajectory:
            self.trajectory.start(task)

        for _ in range(self.max_steps):
            if not self.step():
                break

        if self.trajectory:
            self.trajectory.end(status="completed")

    def reset(self) -> None:
        schema_constraint = self._get_schema_constraint()
        self.memory = [
            {
                "role": "system",
                "content": self.prompt_manager.compose(
                    schema_constraint=schema_constraint
                ),
            }
        ]
