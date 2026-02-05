"""Plan Mode 与 TUI 的回调集成"""

import logging
from typing import Optional
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from elephan_code.tui.plan_todo_display import PlanTodoDisplay

logger = logging.getLogger(__name__)


class PlanModeDisplayIntegration:
    """集成执行模式和 TUI 显示"""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.display = PlanTodoDisplay(self.console)
        self.current_plan = None
        self.plan_manager = None
        self._progress: Optional[Progress] = None
        self._current_task_id = None

    def on_plan_created(self, plan, plan_manager) -> None:
        self.current_plan = plan
        self.plan_manager = plan_manager

        self.console.print()
        self.console.print(f"[bold cyan]Plan[/bold cyan] ({len(plan.steps)} steps)")
        for i, step in enumerate(plan.steps, 1):
            self.console.print(f"  {i}. {step.description}", style="dim")
        self.console.print()

    def on_step_start(self, step) -> None:
        total = len(self.current_plan.steps) if self.current_plan else "?"
        self.console.print(
            f"[yellow]→[/yellow] Step {step.step_id}/{total}: {step.description}"
        )

    def on_step_progress(self, step, iteration: int, max_iterations: int) -> None:
        pass

    def on_step_completed(self, step, observation: str) -> None:
        self.console.print(f"  [green]✓[/green] Done")

    def on_step_failed(self, step, error: str) -> None:
        self.console.print(f"  [red]✗[/red] Failed: {error}")

    def on_step_blocked(self, step) -> None:
        self.console.print(f"  [yellow]◆[/yellow] Blocked (dependencies)")

    def on_step_skipped(self, step_id: int, reason: str) -> None:
        self.console.print(f"  [dim]⊘ Step {step_id} skipped: {reason}[/dim]")

    def on_execution_start(self, task: str) -> None:
        self.console.print(f"\n[bold]Task:[/bold] {task}")

    def on_execution_end(self, result) -> None:
        progress = result.get("progress", 0)
        steps = result.get("plan_steps_completed", result.get("steps_taken", 0))
        total = result.get("plan_total_steps", steps)

        self.console.print()
        if result.get("success"):
            self.console.print(
                f"[bold green]✓ Complete[/bold green] ({steps}/{total} steps, {progress:.0f}%)"
            )
        else:
            self.console.print(
                f"[bold yellow]⚠ Partial[/bold yellow] ({steps}/{total} steps)"
            )

    def on_execution_error(self, error: str) -> None:
        self.console.print(f"\n[bold red]Error:[/bold red] {error}")

    def on_status_update(self, status: str) -> None:
        self.console.print(f"[dim]{status}[/dim]")

    def on_subtask_completed(self, tool_name: str, result) -> None:
        pass

    def on_decision_made(self, decision) -> None:
        complexity = decision.complexity.value
        planning = "yes" if decision.needs_planning else "no"
        self.console.print(f"[dim]Complexity: {complexity}, Planning: {planning}[/dim]")

    def setup_callbacks(self, mode) -> None:
        mode.register_callback("on_plan_created", self.on_plan_created)
        mode.register_callback("on_step_start", self.on_step_start)
        mode.register_callback("on_step_progress", self.on_step_progress)
        mode.register_callback("on_step_completed", self.on_step_completed)
        mode.register_callback("on_step_failed", self.on_step_failed)
        mode.register_callback("on_step_blocked", self.on_step_blocked)
        mode.register_callback("on_step_skipped", self.on_step_skipped)
        mode.register_callback("on_execution_start", self.on_execution_start)
        mode.register_callback("on_execution_end", self.on_execution_end)
        mode.register_callback("on_execution_error", self.on_execution_error)
        mode.register_callback("on_status_update", self.on_status_update)
        mode.register_callback("on_subtask_completed", self.on_subtask_completed)
        mode.register_callback("on_decision_made", self.on_decision_made)
