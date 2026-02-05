"""Plan Mode 的 Todo List TUI 显示组件"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree
from rich.table import Table

from elephan_code.agent.plan.plan_structures import PlanProgress, StepStatus
from elephan_code.agent.plan.plan_todo import PlanTodoManager
from elephan_code.utils.logging import get_logger

logger = get_logger("elephan.plan_display")


class PlanTodoDisplay:
    """Plan Mode 的 todo list TUI 显示"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
    
    def display_plan_overview(self, progress: PlanProgress):
        """显示计划整体概览"""
        overall_pct = progress.get_overall_progress()
        
        panel_content = Text()
        panel_content.append(f"总进度: ", style="bold")
        panel_content.append(f"{overall_pct:.1f}%\n", style="cyan bold")
        
        # 绘制进度条
        bar_length = 40
        filled = int(bar_length * overall_pct / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        panel_content.append(f"[{bar}]", style="yellow")
        
        # 添加统计信息
        completed = sum(
            1 for sp in progress.steps_progress.values()
            if sp.status == StepStatus.COMPLETED
        )
        panel_content.append(
            f"\n\n完成: {completed}/{progress.total_steps} 步骤",
            style="green"
        )
        
        failed = len(progress.get_failed_steps())
        if failed > 0:
            panel_content.append(f" | 失败: {failed}", style="red")
        
        self.console.print(
            Panel(
                panel_content,
                title="[Plan Progress]",
                border_style="cyan",
                padding=(0, 1)
            )
        )
    
    def display_todo_list(self, progress: PlanProgress, plan=None):
        """显示详细 todo 列表（树形）"""
        tree = Tree("📋 Plan Todo List")
        
        for step_id in sorted(progress.steps_progress.keys()):
            sp = progress.steps_progress[step_id]
            
            # 构建步骤文本
            icon = PlanTodoManager._get_status_icon(sp.status)
            status_style = self._get_status_style(sp.status)
            
            step_text = Text(f"{icon} ", style=status_style)
            step_text.append(f"Step {step_id}: ", style="bold")
            step_text.append(sp.description, style="dim")
            
            # 添加时间信息
            if sp.duration_seconds:
                step_text.append(f" [{sp.duration_seconds:.1f}s]", style="dim cyan")
            
            step_node = tree.add(step_text)
            
            # 添加子任务（如有）
            if sp.subtask_count > 0:
                for subtask_name, completed in sp.subtasks.items():
                    subtask_icon = "✓" if completed else "☐"
                    subtask_text = f"{subtask_icon} {subtask_name}"
                    step_node.add(Text(subtask_text, style="dim"))
            
            # 显示错误信息
            if sp.error_message:
                step_node.add(
                    Text(f"⚠️  Error: {sp.error_message}", style="red")
                )
            
            # 显示依赖信息
            if plan:
                step_obj = next(
                    (s for s in plan.steps if s.step_id == step_id), None
                )
                if step_obj and step_obj.dependencies:
                    dep_text = f"Depends on: {step_obj.dependencies}"
                    step_node.add(Text(dep_text, style="dim blue"))
        
        self.console.print(tree)
    
    def display_step_status(self, step_id: int, progress: PlanProgress):
        """显示单个步骤的详细状态"""
        sp = progress.steps_progress.get(step_id)
        if not sp:
            self.console.print(f"[red]Step {step_id} not found[/red]")
            return
        
        status_icon = PlanTodoManager._get_status_icon(sp.status)
        status_text = sp.status.value.upper()
        
        panel_content = Text()
        panel_content.append(f"{status_icon} ", style=self._get_status_style(sp.status))
        panel_content.append(f"{status_text}\n", style="bold")
        
        if sp.subtask_count > 0:
            pct = sp.progress_percentage()
            panel_content.append(
                f"进度: {sp.subtask_completed}/{sp.subtask_count} ({pct:.0f}%)\n",
                style="cyan"
            )
        
        if sp.duration_seconds:
            panel_content.append(
                f"耗时: {sp.duration_seconds:.2f}s\n",
                style="dim cyan"
            )
        
        if sp.observation:
            truncated = sp.observation[:300] + "..." if len(sp.observation) > 300 else sp.observation
            panel_content.append(f"输出: {truncated}", style="dim")
        
        if sp.error_message:
            panel_content.append(f"错误: {sp.error_message}", style="red")
        
        self.console.print(
            Panel(
                panel_content,
                title=f"[Step {step_id} Status]",
                border_style="cyan",
                padding=(0, 1)
            )
        )
    
    def display_failed_steps(self, progress: PlanProgress):
        """显示失败和阻塞的步骤"""
        failed = progress.get_failed_steps()
        blocked = progress.get_blocked_steps()
        
        if not failed and not blocked:
            return
        
        table = Table(title="Issues", border_style="red")
        table.add_column("Step", style="bold", width=8)
        table.add_column("Status", style="red", width=10)
        table.add_column("Info", style="dim red")
        
        for step_id in failed:
            sp = progress.steps_progress[step_id]
            table.add_row(
                str(step_id),
                "FAILED",
                sp.error_message or "Unknown error"
            )
        
        for step_id in blocked:
            sp = progress.steps_progress[step_id]
            table.add_row(
                str(step_id),
                "BLOCKED",
                sp.observation or "Dependencies not met"
            )
        
        self.console.print(table)
    
    def display_execution_summary(self, progress: PlanProgress):
        """显示执行总结"""
        completed = sum(
            1 for sp in progress.steps_progress.values()
            if sp.status == StepStatus.COMPLETED
        )
        failed = len(progress.get_failed_steps())
        skipped = sum(
            1 for sp in progress.steps_progress.values()
            if sp.status == StepStatus.SKIPPED
        )
        
        total_duration = sum(
            sp.duration_seconds for sp in progress.steps_progress.values()
            if sp.duration_seconds
        )
        
        panel_content = Text()
        panel_content.append("执行完成\n\n", style="bold green")
        
        panel_content.append(f"✓ 完成: {completed}/{progress.total_steps}\n", style="green")
        if failed > 0:
            panel_content.append(f"✗ 失败: {failed}\n", style="red")
        if skipped > 0:
            panel_content.append(f"⊘ 跳过: {skipped}\n", style="dim")
        
        panel_content.append(f"\n总耗时: {total_duration:.1f}s", style="cyan")
        
        self.console.print(
            Panel(
                panel_content,
                title="[Summary]",
                border_style="green",
                padding=(0, 1)
            )
        )
    
    @staticmethod
    def _get_status_style(status: StepStatus) -> str:
        """获取状态的样式"""
        styles = {
            StepStatus.NOT_STARTED: "dim",
            StepStatus.IN_PROGRESS: "yellow bold",
            StepStatus.COMPLETED: "green bold",
            StepStatus.FAILED: "red bold",
            StepStatus.SKIPPED: "dim",
            StepStatus.BLOCKED: "red",
        }
        return styles.get(status, "white")
