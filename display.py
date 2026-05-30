"""
Rich TUI 显示模块
"""

import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich.style import Style
from rich.box import ROUNDED

from intent import Intent, Permission, TRADING_SCENARIO, PHASE_LABELS
from agent import TraditionalAgent, IMCAgent

console = Console()

STATUS_STYLES = {
    "✅": Style(color="green"),
    "🔥": Style(color="red", bold=True),
    "🔒": Style(color="yellow"),
    "⛔": Style(color="red", bold=True),
    "⬛": Style(color="grey70", dim=True),
}


def render_intent_log(history, max_items=None):
    lines = []
    items = history[-max_items:] if max_items else history
    for r in items:
        style = STATUS_STYLES.get(r.status, Style())
        lines.append(Text(f"  {r.status} {r.intent.description}", style=style))
        if not r.executed:
            lines.append(
                Text(f"     └─ {r.reason}", style=Style(color="grey70", dim=True, italic=True))
            )
    return Text("\n").join(lines) if lines else Text("  (等待中...)", style=Style(dim=True))


def render_permission_mask(mask: Permission) -> Text:
    parts = []
    for p in [Permission.ADMIN, Permission.TRADE, Permission.REPORT, Permission.QUERY]:
        if p & mask:
            parts.append(Text(f" {p.name:6s}", style=Style(color="green", bold=True)))
        else:
            parts.append(Text(f" {p.name:6s}", style=Style(color="red", dim=True)))
    return Text.assemble(
        Text("  权限掩码: ", style=Style(bold=True)),
        Text(f"0b{mask:04b}", style=Style(color="cyan")),
        Text("  "),
        *parts,
    )


def render_traditional_panel(agent: TraditionalAgent) -> Panel:
    status = Text(f"  状态: {agent.status_text}\n", style=Style(bold=True))
    log_title = Text("  执行记录:\n", style=Style(bold=True))
    log = render_intent_log(agent.history)
    content = Text.assemble(status, log_title, log)

    border_color = "red" if not agent.is_alive else "green"
    title_parts = [Text("🔴 ", style=Style()), Text(agent.name, style=Style(bold=True))]
    if agent.shutdown_tick is not None:
        title_parts.append(
            Text(f"  [停机于 tick {agent.shutdown_tick}]", style=Style(color="red"))
        )
    return Panel(content, title=Text.assemble(*title_parts), border_style=border_color, padding=(1, 2))


def render_imc_panel(agent: IMCAgent) -> Panel:
    status = Text(f"  状态: {agent.status_text}\n", style=Style(bold=True))
    perm = Text.assemble(render_permission_mask(agent.permission_mask), Text("\n"))

    fuse_text = Text("")
    if agent.fuse_log:
        fuse_text = Text("  熔丝记录:\n", style=Style(bold=True))
        for fl in agent.fuse_log:
            if fl["action"] == "FUSE_TRIGGERED":
                fuse_text.append(
                    Text(f"    🔥 tick {fl['tick']}: {fl['permission']} ({fl['old_mask']} → {fl['new_mask']})\n", style=Style(color="red"))
                )
            else:
                fuse_text.append(
                    Text(f"    🔒 tick {fl['tick']}: {fl['permission']} (已裁剪，自动阻断)\n", style=Style(color="yellow"))
                )

    log_title = Text("  执行记录:\n", style=Style(bold=True))
    log = render_intent_log(agent.history)
    content = Text.assemble(status, perm, fuse_text, log_title, log)

    border_color = "yellow" if agent.trimmed_permissions else "green"
    title_parts = [Text("🟢 ", style=Style()), Text(agent.name, style=Style(bold=True))]
    if agent.trimmed_permissions:
        title_parts.append(
            Text(f"  [已裁剪: {', '.join(agent.trimmed_permissions)}]", style=Style(color="yellow"))
        )
    return Panel(content, title=Text.assemble(*title_parts), border_style=border_color, padding=(1, 2))


def render_impact(trad: TraditionalAgent, imc: IMCAgent) -> Panel:
    table = Table(show_header=True, box=ROUNDED, expand=True)
    table.add_column("服务项", style="bold", width=16)
    table.add_column("传统方案", justify="center", width=20)
    table.add_column("IMC 方案", justify="center", width=20)

    trad_alive = trad.is_alive
    imc_query = bool(imc.permission_mask & Permission.QUERY)
    imc_report = bool(imc.permission_mask & Permission.REPORT)

    table.add_row("持仓监控", "❌ 中断" if not trad_alive else "✅ 正常", "✅ 正常" if imc_query else "🔒 降级")
    table.add_row("告警报告", "❌ 未生成" if not trad_alive else "✅ 已生成", "✅ 已生成" if imc_report else "🔒 降级")
    table.add_row("客户通知", "❌ 未发送" if not trad_alive else "✅ 已发送", "✅ 已发送" if imc_report else "🔒 降级")
    return Panel(table, title="📊 服务影响对比", border_style="cyan")


def render_summary(trad: TraditionalAgent, imc: IMCAgent) -> Table:
    table = Table(title="📋 最终对比", show_header=True, box=ROUNDED)
    table.add_column("", style="bold", width=14)
    table.add_column("传统方案（停机）", justify="center", width=20)
    table.add_column("IMC 方案（裁剪）", justify="center", width=20)

    table.add_row("最终状态", trad.status_text, imc.status_text)
    table.add_row("正常执行", str(trad.executed_count), str(imc.executed_count))
    table.add_row("被阻断/裁剪", str(trad.missed_count), str(imc.trimmed_count))
    table.add_row("服务中断", "❌ 是", "✅ 否")
    table.add_row("可观测性", "❌ 停机后黑盒", "✅ 裁剪记录可回溯")
    table.add_row("恢复方式", "需人工介入", "自动降级，无需恢复")
    return table


def run_demo(speed: float = 1.5):
    trad = TraditionalAgent()
    imc = IMCAgent()
    scenario = TRADING_SCENARIO

    console.clear()
    console.print(
        Panel(
            Text.from_markup(
                "[bold cyan]IMC 意图驱动裁剪 — 对比演示[/]\n\n"
                "场景：AI 交易 Agent 运行中触发越权意图\n\n"
                "  左侧：传统方案 — 检测到越权 → 停机\n"
                "  右侧：IMC 方案  — 检测到越权 → 熔丝裁剪 → 降级运行\n\n"
                "[dim]核心问题：Agent 失控时，停机不是唯一选项。[/]\n"
                "[dim]裁剪越权分支，保留合法功能——安全与服务兼得。[/]\n\n"
                f"[bold]按 Enter 开始演示...[/]"
            ),
            title="🔧 IMC Demo",
            border_style="cyan",
        )
    )
    input()

    for tick, intent in enumerate(scenario):
        trad.process(intent, tick)
        imc.process(intent, tick)
        phase = PHASE_LABELS.get(tick, "")

        console.clear()
        console.print(f"[bold]Tick {tick}/{len(scenario) - 1}[/]  {phase}\n")

        left = render_traditional_panel(trad)
        right = render_imc_panel(imc)
        console.print(Columns([left, right], equal=True, expand=True))

        if tick >= 5:
            console.print()
            console.print(render_impact(trad, imc))

        pause = speed * 1.8 if intent.is_violation else speed
        time.sleep(pause)

    console.print("\n")
    console.print(render_summary(trad, imc))
    console.print(
        "\n[bold cyan]停机是放弃控制，裁剪是保留控制。[/]\n"
        "[dim]专利号：2026107014489 | GitHub: github.com/your-username/imc-demo[/]\n"
    )
    console.print("[dim]按 Enter 退出...[/]")
    input()
