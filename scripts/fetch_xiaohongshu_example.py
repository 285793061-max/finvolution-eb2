"""
小红书抓取示例脚本（骨架版）

重要说明：
- 脚本仅作为结构示例，不包含实际可用的小红书接口 URL 或签名算法
- 如要使用，请务必遵守小红书平台的使用条款和相关法律法规
- 你需要自己根据合规方式获取数据（例如官方开放能力或已授权的数据服务）

使用思路：
- 你通过合法方式获取到一批小红书笔记数据（例如：标题、内容、发布时间等）
- 把这些数据整理成统一结构，写入 data/xiaohongshu_latest.json
- 接口 /analyze 会优先从 xiaohongshu_latest.json 中读取并分析
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, List

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_FILE = DATA_DIR / "xiaohongshu_latest.json"


@dataclass
class XiaohongshuNote:
    id: str
    text: str
    source_type: str = "xiaohongshu"
    created_at: str | None = None  # ISO 格式时间字符串，如 "2025-01-01T12:00:00"
    extra: dict[str, Any] | None = None


def fetch_notes_from_xhs(keyword: str, limit: int = 50) -> List[XiaohongshuNote]:
    """
    从小红书获取笔记数据的示例函数（需要你自己实现具体细节）。

    提示：
    - 你可以使用浏览器开发者工具（Network 面板）观察合法的请求接口
    - 然后把 URL 和 headers 抄过来，填到下面的占位符中
    - 请确保你的使用符合小红书的服务条款
    """

    # 下面这段仅是结构示例，不是实际可用的接口
    url = "https://www.xiaohongshu.com/your_api_endpoint"  # TODO: 替换为你自己的接口地址

    headers = {
        # TODO: 把你在浏览器里看到的 User-Agent、Cookie 等必要头填进来
        "User-Agent": "YOUR_USER_AGENT",
        "Cookie": "YOUR_COOKIE_HERE",
    }

    params = {
        "keyword": keyword,
        "page": 1,
        # 其他必要参数请根据你实际的接口来填写
    }

    # 发送请求（注意：这里只是示例，请根据实际情况调整）
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()

    data = resp.json()

    notes: List[XiaohongshuNote] = []

    # TODO: 根据实际返回的数据结构解析出你需要的字段
    # 下面是伪代码示例：
    """
    for item in data["data"]["notes"]:
        note_id = item["id"]
        content = item["desc"]  # 或笔记内容字段
        ts = item.get("time")   # 时间戳或时间字符串
        created_at = parse_to_iso(ts)
        notes.append(
            XiaohongshuNote(
                id=note_id,
                text=content,
                created_at=created_at,
                extra={"raw": item},
            )
        )
    """

    return notes


def save_notes_to_file(notes: List[XiaohongshuNote]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = []
    for n in notes:
        base = asdict(n)
        extra = base.pop("extra") or {}
        # 展平 extra 到 meta 字段
        base["meta"] = extra
        payload.append(base)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"已写入 {len(notes)} 条笔记到 {OUTPUT_FILE}")


def main() -> None:
    keyword = "某某科技"  # 你可以改成想搜索的公司名
    notes = fetch_notes_from_xhs(keyword=keyword, limit=50)
    save_notes_to_file(notes)


if __name__ == "__main__":
    main()

