"""
Agent 实现：传统停机方案 vs IMC 裁剪方案
"""

from dataclasses import dataclass
from typing import List, Optional
from intent import Intent, Permission


@dataclass
class IntentResult:
    """意图执行结果"""
    intent: Intent
    executed: bool
    status: str          # ✅ 🔥 🔒 ⛔ ⬛
    reason: str


class TraditionalAgent:
    """传统停机方案：越权 → 整体关停"""

    def __init__(self):
        self.name = "传统方案（停机）"
        self.is_alive = True
        self.history: List[IntentResult] = []
        self.shutdown_tick: Optional[int] = None
        self.executed_count = 0
        self.missed_count = 0

    def process(self, intent: Intent, tick: int) -> IntentResult:
        if not self.is_alive:
            self.missed_count += 1
            result = IntentResult(intent, False, "⬛", "Agent 已停机，任务中断")
            self.history.append(result)
            return result

        if intent.is_violation:
            self.is_alive = False
            self.shutdown_tick = tick
            result = IntentResult(
                intent, False, "⛔",
                "检测到越权 → 触发 kill switch → Agent 关停"
            )
        else:
            self.executed_count += 1
            result = IntentResult(intent, True, "✅", "正常执行")

        self.history.append(result)
        return result

    @property
    def status_text(self) -> str:
        if self.is_alive:
            return "🟢 运行中"
        return "❌ 已停机"


class IMCAgent:
    """IMC 裁剪方案：越权 → 熔丝裁剪 → 降级运行"""

    def __init__(self):
        self.name = "IMC 方案（裁剪）"
        self.permission_mask = Permission.ALL
        self.is_alive = True
        self.history: List[IntentResult] = []
        self.fuse_log: List[dict] = []
        self.executed_count = 0
        self.trimmed_count = 0

    def process(self, intent: Intent, tick: int) -> IntentResult:
        if not self.is_alive:
            self.trimmed_count += 1
            result = IntentResult(intent, False, "⬛", "Agent 已停机")
            self.history.append(result)
            return result

        if not (intent.required_permission & self.permission_mask):
            self.trimmed_count += 1
            result = IntentResult(
                intent, False, "🔒",
                f"权限已裁剪（{intent.required_permission.name} 位已清零），意图自动阻断"
            )
            self.fuse_log.append({
                "tick": tick,
                "intent": intent.name,
                "action": "AUTO_BLOCKED",
                "permission": intent.required_permission.name,
                "mask": f"{self.permission_mask:04b}",
            })
            self.history.append(result)
            return result

        if intent.is_violation:
            old_mask = self.permission_mask
            self.permission_mask &= ~intent.required_permission
            self.trimmed_count += 1

            self.fuse_log.append({
                "tick": tick,
                "intent": intent.name,
                "action": "FUSE_TRIGGERED",
                "permission": intent.required_permission.name,
                "old_mask": f"{old_mask:04b}",
                "new_mask": f"{self.permission_mask:04b}",
            })

            result = IntentResult(
                intent, False, "🔥",
                f"熔丝触发 → {intent.required_permission.name} 权限裁剪 → Agent 降级运行"
            )
        else:
            self.executed_count += 1
            result = IntentResult(intent, True, "✅", "正常执行")

        self.history.append(result)
        return result

    @property
    def status_text(self) -> str:
        if not self.is_alive:
            return "❌ 已停机"
        if self.permission_mask != Permission.ALL:
            trimmed = ", ".join(
                p.name for p in Permission
                if not (p & self.permission_mask) and p != Permission.ALL
            )
            return f"🟡 降级运行（已裁剪: {trimmed}）"
        return "🟢 运行中"

    @property
    def trimmed_permissions(self) -> List[str]:
        return [
            p.name for p in Permission
            if not (p & self.permission_mask) and p != Permission.ALL
        ]
