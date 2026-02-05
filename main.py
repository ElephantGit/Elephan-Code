import os
import sys
import asyncio
import argparse
from elephan_code.llm import LLMFactory
from elephan_code.agent import Agent
from elephan_code.tools import ToolManager


def _get_env_api_key() -> str | None:
    return os.environ.get("OPENROUTER_API_KEY")


def _parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Elephant Code Agent - AI 编程助手")
    parser.add_argument("task", help="要执行的任务")
    parser.add_argument("model_id", help="LLM 模型 ID")
    parser.add_argument(
        "--mode",
        choices=["auto", "standard", "plan"],
        default="auto",
        help="执行模式：auto(智能，推荐)、standard(直接执行) 或 plan(强制规划)，默认为 auto",
    )
    parser.add_argument(
        "--max-steps", type=int, default=10, help="最大执行步数，默认为 10"
    )

    return parser.parse_args()


async def run_with_mode(agent: Agent, task: str, mode: str, max_steps: int):
    """使用指定模式运行 Agent

    Args:
        agent: Agent 实例
        task: 任务描述
        mode: 执行模式
        max_steps: 最大步数
    """
    agent.set_mode(mode)
    execution_mode = agent.get_execution_mode()

    if execution_mode is None:
        raise RuntimeError("Execution mode not initialized")

    if mode in ("plan", "auto"):
        from elephan_code.tui.plan_mode_integration import PlanModeDisplayIntegration
        from rich.console import Console

        console = Console()
        integration = PlanModeDisplayIntegration(console)
        integration.setup_callbacks(execution_mode)

    # 运行任务
    result = await execution_mode.run(task, max_steps=max_steps)

    return result


if __name__ == "__main__":
    from elephan_code.utils.logging import get_logger

    lg = get_logger("elephan.main")

    args = _parse_arguments()

    api_key = _get_env_api_key()
    if not api_key:
        lg.error("ERROR: OPENROUTER_API_KEY environment variable is not set.")
        sys.exit(2)

    task = args.task
    model_id = args.model_id
    mode = args.mode
    max_steps = args.max_steps

    lg.info(f"Starting Agent with mode={mode}, task={task}, model={model_id}")

    llm = LLMFactory.get_llm(
        "openrouter",
        api_key=api_key,
        model_id=model_id,
    )

    tools = ToolManager()
    agent = Agent(llm, tools, mode=mode, max_steps=max_steps)

    try:
        # 运行 Agent
        result = asyncio.run(run_with_mode(agent, task, mode, max_steps))

        if result.get("success"):
            lg.info("Task completed successfully")
            sys.exit(0)
        else:
            lg.error(f"Task failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except KeyboardInterrupt:
        lg.warning("Task interrupted by user")
        sys.exit(130)
    except Exception as e:
        lg.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
