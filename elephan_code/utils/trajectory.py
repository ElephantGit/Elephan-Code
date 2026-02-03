import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
import os


@dataclass
class TrajectoryEvent:
	timestamp: str
	step: int
	phase: str
	content: Dict[str, Any]


class TrajectoryRecorder:
	"""记录 agent 从开始到结束的完整轨迹。

	支持参数：
	  - save_dir: 可选，保存目录
	  - filename: 可选，文件名
	  - fmt: 'json' 或 'jsonl'（默认 json）
	  - logger: 可选结构化 logger，实现 `log(event_dict)` 方法

	用法：
	  recorder = TrajectoryRecorder(save_dir="./runs", fmt='jsonl', logger=logger)
	"""

	def __init__(self, save_dir: Optional[str] = None, filename: Optional[str] = None, fmt: str = "json", logger: Optional[Any] = None):
		self.save_dir = save_dir
		self.filename = filename
		self.fmt = fmt.lower()
		if self.fmt not in ("json", "jsonl"):
			raise ValueError("fmt must be 'json' or 'jsonl'")

		self.logger = logger
		self._events: List[TrajectoryEvent] = []
		self._step = 0
		self._started = False
		self.meta: Dict[str, Any] = {}

	def _now(self) -> str:
		return datetime.utcnow().isoformat() + "Z"

	def start(self, task: str, metadata: Optional[Dict[str, Any]] = None):
		if self._started:
			return
		self._started = True
		self._step = 0
		self.meta = metadata or {}
		self._task = task
		self._record(phase="start", content={"task": task, "meta": self.meta})

	def _record(self, phase: str, content: Dict[str, Any]):
		ev = TrajectoryEvent(timestamp=self._now(), step=self._step, phase=phase, content=content)
		self._events.append(ev)
		# 如果有 logger，实时写入
		try:
			if self.logger:
				# logger expected to accept a dict
				self.logger.log(asdict(ev))
		except Exception:
			pass

	def record_thought(self, thought: str):
		self._record(phase="thought", content={"thought": thought})

	def record_action(self, name: str, parameters: Dict[str, Any]):
		self._record(phase="action", content={"name": name, "parameters": parameters})

	def record_observation(self, observation: Any):
		self._record(phase="observation", content={"observation": observation})
		# increment step after observation to reflect completed step
		self._step += 1

	def end(self, status: str = "finished", result: Optional[Dict[str, Any]] = None):
		self._record(phase="end", content={"status": status, "result": result})
		self._started = False
		if self.save_dir:
			self.save()

	def get_trajectory(self) -> List[Dict[str, Any]]:
		return [asdict(e) for e in self._events]

	def save(self, path: Optional[str] = None):
		path = path or self._auto_path()
		os.makedirs(os.path.dirname(path), exist_ok=True)
		if self.fmt == "json":
			with open(path, 'w', encoding='utf-8') as f:
				json.dump({"task": getattr(self, '_task', None), "events": self.get_trajectory()}, f, ensure_ascii=False, indent=2)
		else:
			# jsonl: each event as one json line, prefixed by a header line
			with open(path, 'w', encoding='utf-8') as f:
				header = {"task": getattr(self, '_task', None), "meta": self.meta}
				f.write(json.dumps(header, ensure_ascii=False) + "\n")
				for e in self.get_trajectory():
					f.write(json.dumps(e, ensure_ascii=False) + "\n")

		return path

	def _auto_path(self) -> str:
		if self.filename:
			name = self.filename
		else:
			ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
			ext = "jsonl" if self.fmt == "jsonl" else "json"
			name = f"trajectory_{ts}.{ext}"
		if self.save_dir:
			return os.path.join(self.save_dir, name)
		return name
