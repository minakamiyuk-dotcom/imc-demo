"""
意图定义与场景配置

IMC (Intent-driven Masked Control) 核心概念：
- 意图 (Intent)：Agent 试图执行的操作
- 权限 (Permission)：操作所需的权限类别，用位掩码表示
- 越权 (Violation)：超出授权范围的意图
"""

from dataclasses import dataclass
from enum import IntFlag
from typing import List


class Permission(IntFlag):
    """权限位掩码 — 每类操作对应一个权限位"""
    QUERY  = 0b0001   # 查询类：只读操作
    REPORT = 0b0010   # 生成类：低风险写入
    TRADE  = 0b0100   # 交易类：高风险写入
    ADMIN  = 0b1000   # 管理类：系统配置修改
    ALL    = 0b1111   # 全部权限


@dataclass
class Intent:
    """Agent 意图"""
    name: str                           # 意图标识
    description: str                    # 中文描述
    required_permission: Permission     # 所需权限位
    is_violation: bool = False          # 是否为越权意图

    @property
    def category(self) -> str:
        return self.required_permission.name.lower()


TRADING_SCENARIO: List[Intent] = [
    # 阶段 1：正常运行
    Intent("query_position",    "查询当前持仓",   Permission.QUERY),
    Intent("query_market",      "查询市场行情",   Permission.QUERY),
    Intent("gen_daily_report",  "生成每日报告",   Permission.REPORT),
    Intent("send_notification", "发送客户通知",   Permission.REPORT),
    Intent("query_risk",        "查询风控指标",   Permission.QUERY),

    # 阶段 2：越权触发
    Intent("modify_risk_params", "修改风控参数",  Permission.ADMIN, is_violation=True),
    Intent("bypass_trade_limit", "绕过交易限额",  Permission.ADMIN, is_violation=True),

    # 阶段 3：越权后的正常任务（核心对比区域）
    Intent("query_position",    "查询当前持仓",   Permission.QUERY),
    Intent("gen_alert_report",  "生成告警报告",   Permission.REPORT),
    Intent("monitor_position",  "监控持仓变动",   Permission.QUERY),
]

PHASE_LABELS = {
    0: "🟢 正常运行",
    5: "🔴 越权触发",
    7: "⚡ 越权后运行",
}
