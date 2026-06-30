from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pyautogui

# Ensure parent directory is in path for imports
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.services.xhs_extractors import (
    ExtractedItem,
    dedupe_texts,
    keyword_filter,
    ocr_extract_lines,
    texts_to_items,
)

from .config import CollectorConfig
from .engines import OCREngine, DOMEngine
from .output import OutputWriter, write_latest
from .challenges import ChallengeOrchestrator, CloudflareChallengeHandler
from .proxy import ProxyManager
from .session import SessionPool
from .progress import ProgressTracker, CrawlLimits
from .cache import CacheManager
from .hooks import HookManager, HookContext


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_region(path: Path) -> Optional[tuple[int, int, int, int]]:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    x = int(obj["x"])
    y = int(obj["y"])
    w = int(obj["w"])
    h = int(obj["h"])
    return (x, y, w, h)


def save_region(path: Path, region: tuple[int, int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    x, y, w, h = region
    with path.open("w", encoding="utf-8") as f:
        json.dump({"x": x, "y": y, "w": w, "h": h}, f, ensure_ascii=False, indent=2)


def calibrate_region(path: Path) -> tuple[int, int, int, int]:
    print("将浏览器置于前台，并把搜索结果列表区域完整显示出来。")
    input("把鼠标移动到【结果区域左上角】后按 Enter ...")
    p1 = pyautogui.position()
    input("把鼠标移动到【结果区域右下角】后按 Enter ...")
    p2 = pyautogui.position()

    x1, y1 = int(min(p1.x, p2.x)), int(min(p1.y, p2.y))
    x2, y2 = int(max(p1.x, p2.x)), int(max(p1.y, p2.y))
    region = (x1, y1, max(1, x2 - x1), max(1, y2 - y1))
    save_region(path, region)
    print(f"已保存截图区域到 {path}：{region}")
    return region


def focus_and_open_search(keyword: str, wait_after_open_s: float) -> None:
    q = urllib.parse.quote(keyword)
    url = f"https://www.xiaohongshu.com/search_result?keyword={q}"

    pyautogui.hotkey("command", "l")
    time.sleep(0.2)
    pyautogui.typewrite(url, interval=0.02)
    pyautogui.press("enter")
    time.sleep(max(0.0, wait_after_open_s))


def write_demo(keyword: str, out_path: Path) -> None:
    demo_texts = [
        f"{keyword} 氛围好，团队很友善，福利也不错。",
        f"{keyword} 996 加班严重，管理混乱，离职率高。",
        f"听说 {keyword} 薪资高但强度大，成长快机会多。",
        f"{keyword} 面试体验差评：流程拖沓，不合理。",
    ]
    items = texts_to_items(
        demo_texts,
        keyword=keyword,
        captured_at=datetime.now(timezone.utc),
        meta={"extractor": "demo"},
    )
    write_latest(items, out_path)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="小红书真人模拟采集（你先登录网页端）")
    p.add_argument("--keyword", required=True, help="搜索关键词（公司名）")
    p.add_argument("--limit", type=int, default=50, help="最多采集条数（去重后）")
    p.add_argument("--out", type=Path, default=BASE_DIR / "data" / "xiaohongshu_latest.json", help="输出 JSON 文件路径")
    p.add_argument("--extractor", choices=["ocr", "dom"], default="ocr", help="抽取方式：ocr 或 dom")
    p.add_argument("--calibrate", action="store_true", help="校准截图区域并保存到 data/xhs_screen_region.json")
    p.add_argument("--region-file", type=Path, default=BASE_DIR / "data" / "xhs_screen_region.json", help="截图区域配置文件")
    p.add_argument("--pages", type=int, default=8, help="滚动/采集的屏幕次数（每次截图一次）")
    p.add_argument("--scroll-amount", type=int, default=900, help="每次滚动像素（Mac 触控板环境可适当调大/调小）")
    p.add_argument("--scroll-pause", type=float, default=2.0, help="滚动后等待加载秒数")
    p.add_argument("--open-wait", type=float, default=4.0, help="打开搜索 URL 后等待加载秒数")
    p.add_argument("--dom-selector", type=str, default="a", help="DOM 抽取时用于收集文本的选择器（实验性）")
    p.add_argument(
        "--dom-profile-dir",
        type=Path,
        default=BASE_DIR / "data" / ".xhs_playwright_profile",
        help="DOM 抽取时的 Playwright 持久化 profile 目录",
    )
    p.add_argument("--demo", action="store_true", help="不打开浏览器，直接写一份 demo xiaohongshu_latest.json 便于测试")
    return p.parse_args()


class XHSCollector:
    """Main collector class that orchestrates all components."""

    def __init__(self, config: CollectorConfig):
        self.config = config
        self.progress_tracker = ProgressTracker()
        self.cache_manager = CacheManager()
        self.session_pool = SessionPool()
        self.proxy_manager = ProxyManager()
        self.challenge_orchestrator = ChallengeOrchestrator([
            CloudflareChallengeHandler(),
        ])
        self.hook_manager = HookManager()

    def collect(self) -> list[ExtractedItem]:
        """Run the collection process."""
        self.progress_tracker.start()

        if self.config.extractor == "ocr":
            return self._collect_ocr()
        else:
            return self._collect_dom()

    def _collect_ocr(self) -> list[ExtractedItem]:
        """Collect using OCR engine."""
        region = load_region(self.config.region_file)
        if region is None:
            region = calibrate_region(self.config.region_file)

        print("请确保：浏览器已打开并登录小红书网页端，且窗口在最前。")
        input("准备好后按 Enter 开始自动搜索与采集 ...")

        focus_and_open_search(self.config.keyword, wait_after_open_s=float(self.config.open_wait_s))

        engine = OCREngine(
            region=region,
            scroll_amount=self.config.scroll_amount,
            scroll_pause_s=self.config.scroll_pause_s,
        )

        items = engine.collect(
            keyword=self.config.keyword,
            limit=self.config.limit,
            pages=self.config.pages,
        )

        return items

    def _collect_dom(self) -> list[ExtractedItem]:
        """Collect using DOM engine."""
        engine = DOMEngine(
            selector=self.config.dom_selector,
            user_data_dir=self.config.dom_profile_dir,
            scroll_pause_s=self.config.scroll_pause_s,
        )

        items = engine.collect(
            keyword=self.config.keyword,
            limit=self.config.limit,
            pages=self.config.pages,
        )

        return items


def main() -> None:
    args = parse_args()

    if args.demo:
        write_demo(args.keyword, args.out)
        print(f"[{_now_iso()}] demo 已写入：{args.out}")
        return

    # Build config from args
    config = CollectorConfig.from_args(args)

    if args.calibrate:
        calibrate_region(args.region_file)
        return

    collector = XHSCollector(config)
    items = collector.collect()

    write_latest(items, args.out)
    print(f"[{_now_iso()}] 已写入 {len(items)} 条到：{args.out}")