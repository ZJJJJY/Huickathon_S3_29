"""Claude agent loop。

负责把 user prompt 喂给 Claude，循环处理 tool_use → 执行 → tool_result，
直到 stop_reason == 'end_turn'。

设计目标:
- 简单透明，没有花哨抽象
- 把每次 tool 调用的输入输出打印出来，方便 hackathon 现场调试
- 支持 async tool（playwright 是 async 的）
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Awaitable, Callable

from anthropic import Anthropic
from anthropic.types import Message, MessageParam

ToolFn = Callable[..., Awaitable[Any]]

DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
MAX_ITERATIONS = 20  # 防止 agent 卡死


class AgentLoop:
    def __init__(
        self,
        tools_schema: list[dict],
        tool_dispatch: dict[str, ToolFn],
        model: str = DEFAULT_MODEL,
        system: str | None = None,
        max_tokens: int = 4096,
        verbose: bool = True,
    ):
        self.client = Anthropic()
        self.tools_schema = tools_schema
        self.tool_dispatch = tool_dispatch
        self.model = model
        self.system = system
        self.max_tokens = max_tokens
        self.verbose = verbose

    async def run(self, user_prompt: str) -> tuple[str, list[MessageParam]]:
        """跑一次 agent loop。

        返回 (最终文本回复, 完整 messages 历史)。
        历史里包含所有 tool_use / tool_result，外面可以从中提取爬到的 Post。
        """
        messages: list[MessageParam] = [{"role": "user", "content": user_prompt}]

        for iteration in range(MAX_ITERATIONS):
            kwargs: dict[str, Any] = dict(
                model=self.model,
                max_tokens=self.max_tokens,
                tools=self.tools_schema,
                messages=messages,
            )
            if self.system:
                kwargs["system"] = self.system

            resp: Message = self.client.messages.create(**kwargs)

            if self.verbose:
                self._log_assistant(resp)

            # 把 assistant 这一回合塞回 messages
            messages.append({"role": "assistant", "content": resp.content})

            if resp.stop_reason == "end_turn":
                final_text = _extract_text(resp)
                return final_text, messages

            if resp.stop_reason == "tool_use":
                tool_results = await self._execute_tools(resp)
                messages.append({"role": "user", "content": tool_results})
                continue

            # 其他 stop_reason（max_tokens / refusal 等）直接结束
            if self.verbose:
                print(f"[agent] stop_reason={resp.stop_reason}, 结束")
            return _extract_text(resp), messages

        raise RuntimeError(f"agent loop 超过 {MAX_ITERATIONS} 轮还没结束")

    async def _execute_tools(self, resp: Message) -> list[dict]:
        results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            fn = self.tool_dispatch.get(block.name)
            if fn is None:
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"未知 tool: {block.name}",
                        "is_error": True,
                    }
                )
                continue

            try:
                if self.verbose:
                    print(f"[tool] {block.name}({_short(block.input)})")
                out = await fn(**block.input)
                payload = json.dumps(out, ensure_ascii=False, default=str)
                if self.verbose:
                    print(f"[tool] {block.name} -> {len(payload)} chars")
                results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": payload}
                )
            except Exception as e:
                if self.verbose:
                    print(f"[tool] {block.name} ERROR: {e}")
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"工具执行失败: {e}",
                        "is_error": True,
                    }
                )
        return results

    def _log_assistant(self, resp: Message):
        for block in resp.content:
            if block.type == "text" and block.text.strip():
                print(f"[claude] {block.text.strip()[:300]}")


def _extract_text(resp: Message) -> str:
    parts = [b.text for b in resp.content if b.type == "text"]
    return "\n".join(parts).strip()


def _short(d: dict, n: int = 80) -> str:
    s = json.dumps(d, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + "..."


# 单次同步调用（用于第二阶段「基于素材生成结构化 JSON」），不需要 tool。
def call_json(
    prompt: str,
    system: str | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 16384,
) -> dict:
    client = Anthropic()
    kwargs: dict[str, Any] = dict(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    if system:
        kwargs["system"] = system
    resp = client.messages.create(**kwargs)
    if resp.stop_reason == "max_tokens":
        # 输出被截断,JSON 必然不完整,提前抛错好过乱 parse
        raise RuntimeError(
            f"LLM 输出被 max_tokens={max_tokens} 截断,需要更大的 token 上限"
        )
    text = _extract_text(resp)
    # 模型可能用 ```json ... ``` 包裹
    text = _strip_code_fence(text)
    return json.loads(text)


def _strip_code_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        # 去掉首行 ```json 和末尾 ```
        lines = s.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


# 测试用入口
if __name__ == "__main__":

    async def echo(text: str) -> str:
        return f"echoed: {text}"

    schema = [
        {
            "name": "echo",
            "description": "回显文本",
            "input_schema": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        }
    ]
    loop = AgentLoop(schema, {"echo": echo})
    result, _ = asyncio.run(loop.run("调用 echo 工具，传入 'hello'"))
    print("FINAL:", result)
