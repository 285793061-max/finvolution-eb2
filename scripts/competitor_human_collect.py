from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pyautogui

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REGION_FILE = DATA_DIR / "competitor_screen_region.json"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.services.xhs_extractors import ocr_extract_lines


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
    print("将浏览器置于前台，并把招聘职位列表区域完整显示出来。")
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


def screenshot_region(region: Optional[tuple[int, int, int, int]]) -> Any:
    if region is None:
        return pyautogui.screenshot()
    return pyautogui.screenshot(region=region)


def parse_job_lines(lines: list[str]) -> list[dict[str, str]]:
    """
    从 OCR 识别的文本行中解析职位信息。
    尝试匹配职位名、薪资、地点等常见格式。
    """
    jobs = []
    current_job = {}

    salary_pattern = re.compile(r"[\d,\,]+[kK]?\s*[-~]\s*[\d,\,]+[kK]?|[上下高低]下.*[kK]|[①②③④⑤⑥⑦⑧⑨⑩]")
    location_pattern = re.compile(r"[北京上海广州深圳杭州南京成都武汉西安天津重庆香港澳门]+|[省份]+[省市]|[东南西北]+部")
    experience_pattern = re.compile(r"\d+[\-到年]\d+年|经验|应届|社招|校招")
    education_pattern = re.compile(r"本科|硕士|博士|大专|学历")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 跳过导航链接和表头
        if any(kw in line for kw in ["首页", "关于", "联系我们", "登录", "注册", "职位详情", "展开", "收起"]):
            continue

        # 检测薪资行
        if salary_pattern.search(line) and "职位" not in line:
            if current_job and "title" in current_job:
                if current_job.get("salary"):
                    current_job["salary"] += " " + line
                else:
                    current_job["salary"] = line
            continue

        # 检测城市/地点
        loc_match = location_pattern.search(line)
        if loc_match and "职位" not in line:
            if current_job and "title" in current_job:
                current_job["location"] = loc_match.group()
            continue

        # 检测经验要求
        if experience_pattern.search(line):
            if current_job and "title" in current_job:
                current_job["experience"] = line[:50]
            continue

        # 检测学历要求
        if education_pattern.search(line):
            if current_job and "title" in current_job:
                current_job["education"] = line[:50]
            continue

        # 职位名检测（包含职位、工程师、经理、专员、总监等关键词）
        job_keywords = ["工程师", "经理", "专员", "总监", "主管", "助理", "专家", "负责人", "设计师", "运营", "产品", "开发", "测试", "运维", "安全", "数据", "算法", "分析", "策划", "顾问"]
        if any(kw in line for kw in job_keywords) and len(line) < 50:
            if current_job and "title" in current_job:
                jobs.append(current_job)
            current_job = {"title": line, "salary": "", "location": "", "experience": "", "education": ""}

    if current_job and "title" in current_job:
        jobs.append(current_job)

    return jobs


def collect_jobs(
    *,
    pages: int,
    scroll_amount: int,
    scroll_pause_s: float,
    region: Optional[tuple[int, int, int, int]],
) -> list[dict[str, Any]]:
    collected_lines: list[str] = []

    for page_idx in range(pages):
        img = screenshot_region(region)
        lines = ocr_extract_lines(img)
        collected_lines.extend(lines)

        pyautogui.scroll(-abs(scroll_amount))
        time.sleep(max(0.0, scroll_pause_s))

    # 去重
    seen = set()
    deduped = []
    for line in collected_lines:
        norm = line.strip()
        if norm and norm not in seen:
            seen.add(norm)
            deduped.append(norm)

    jobs = parse_job_lines(deduped)
    return jobs


def save_jobs(jobs: list[dict], out_path: Path, company_name: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 读取现有数据
    existing = []
    if out_path.exists():
        with out_path.open("r", encoding="utf-8") as f:
            existing = json.load(f)

    # 添加新数据
    timestamp = datetime.now(timezone.utc).isoformat()
    for job in jobs:
        existing.append({
            "company": company_name,
            "title": job.get("title", ""),
            "salary": job.get("salary", ""),
            "location": job.get("location", ""),
            "experience": job.get("experience", ""),
            "education": job.get("education", ""),
            "collected_at": timestamp,
            "raw_text": json.dumps(job, ensure_ascii=False)
        })

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="竞品招聘截图采集")
    p.add_argument("--company", required=True, help="公司名称")
    p.add_argument("--pages", type=int, default=5, help="滚动/采集的屏幕次数")
    p.add_argument("--scroll-amount", type=int, default=800, help="每次滚动像素")
    p.add_argument("--scroll-pause", type=float, default=2.0, help="滚动后等待加载秒数")
    p.add_argument("--calibrate", action="store_true", help="校准截图区域")
    p.add_argument("--region-file", type=Path, default=REGION_FILE, help="截图区域配置文件")
    p.add_argument("--out", type=Path, default=DATA_DIR / "competitor_jobs_raw.json", help="输出 JSON 文件路径")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    region = load_region(args.region_file)
    if args.calibrate or region is None:
        region = calibrate_region(args.region_file)

    print(f"请确保：浏览器已打开竞品招聘页面，且窗口在最前。")
    input("准备好后按 Enter 开始采集 ...")

    jobs = collect_jobs(
        pages=int(args.pages),
        scroll_amount=int(args.scroll_amount),
        scroll_pause_s=float(args.scroll_pause),
        region=region,
    )

    save_jobs(jobs, args.out, args.company)
    print(f"[{_now_iso()}] 已采集 {len(jobs)} 个职位，保存到：{args.out}")


if __name__ == "__main__":
    main()