#!/usr/bin/env python3
"""脉脉评论爬虫 - 简化版"""
import asyncio
import json
import os
import sqlite3
from pathlib import Path
from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
COOKIE_PATH = os.getenv("MAIMAI_COOKIE_PATH", str(BASE_DIR / "data" / "maimai_cookies.json"))
DB_PATH = os.getenv("SENTIMENT_DB_PATH", str(BASE_DIR / "data" / "sentiment.db"))

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # 加载cookie
        if os.path.exists(COOKIE_PATH):
            with open(COOKIE_PATH, 'r') as f:
                cookies = json.load(f)
                await context.add_cookies(cookies)
            print("已加载Cookie")
        else:
            print("没有Cookie文件")

        # 打开第一个需要评论的URL
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT id, url FROM sentiment_data
            WHERE url LIKE '%maimai.cn%'
            AND (comments_text IS NULL OR comments_text = '')
            AND platform = 'maimai'
            LIMIT 1
        """)
        row = cur.fetchone()
        conn.close()

        if not row:
            print("没有需要抓评论的数据")
            return

        url = row['url']
        print(f"打开: {url}")

        await page.goto(url)
        await page.wait_for_load_state()

        print("请登录脉脉后，按回车继续爬取评论...")
        input()

        # 尝试找评论
        comments = []
        try:
            # 尝试多种选择器
            selectors = [
                '.comment-item',
                '.reply-item',
                '[class*="comment"]',
                '.feed-comment-item'
            ]

            for sel in selectors:
                els = await page.query_selector_all(sel)
                if els:
                    for el in els[:10]:
                        text = await el.text_content()
                        if text and len(text.strip()) > 3:
                            comments.append(text.strip())
                    if comments:
                        break
        except Exception as e:
            print(f"抓取失败: {e}")

        print(f"找到 {len(comments)} 条评论")

        if comments:
            # 保存到数据库
            comments_json = json.dumps(comments[:20], ensure_ascii=False)
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("UPDATE sentiment_data SET comments_text = ? WHERE id = ?",
                       (comments_json, row['id']))
            conn.commit()
            conn.close()
            print("已保存到数据库")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
