#!/usr/bin/env python3
"""
脉脉评论抓取脚本
获取每条帖子的评论内容
"""
import asyncio
import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
COOKIE_PATH = os.getenv("MAIMAI_COOKIE_PATH", str(BASE_DIR / "data" / "maimai_cookies.json"))
DB_PATH = os.getenv("SENTIMENT_DB_PATH", str(BASE_DIR / "data" / "sentiment.db"))

class CommentCrawler:
    def __init__(self):
        self.browser = None
        self.page = None

    async def init(self):
        print("启动浏览器...")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await self.browser.new_context()
        self.page = await context.new_page()

        # 加载cookie
        if os.path.exists(COOKIE_PATH):
            with open(COOKIE_PATH, 'r') as f:
                cookies = json.load(f)
                await context.add_cookies(cookies)
            print("已加载Cookie")

    async def crawl_comments(self, url, platform="maimai"):
        """抓取评论"""
        await self.page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(2)

        comments = []

        if platform == "maimai":
            # 尝试抓取脉脉评论
            try:
                # 等待评论加载
                await self.page.wait_for_selector('.comment-list, .reply-list, [class*="comment"]', timeout=5)
                comment_elements = await self.page.query_selector_all('[class*="comment"], .reply-item')

                for el in comment_elements[:20]:  # 最多取20条
                    text = await el.text_content()
                    if text and len(text.strip()) > 5:
                        comments.append(text.strip())
            except:
                pass

        return comments[:10]

async def get_urls_without_comments():
    """获取没有评论内容的URL"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 获取没有评论文本的记录
    cur.execute("""
        SELECT id, url, platform
        FROM sentiment_data
        WHERE url IS NOT NULL
        AND url != ''
        AND (comments_text IS NULL OR comments_text = '')
        AND platform IN ('maimai', 'xiaohongshu')
        LIMIT 20
    """)

    rows = cur.fetchall()
    conn.close()
    return rows

async def update_comments(url, comments_text):
    """更新评论到数据库"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        UPDATE sentiment_data
        SET comments_text = ?
        WHERE url = ?
    """, (comments_text, url))

    conn.commit()
    conn.close()

async def main():
    crawler = CommentCrawler()
    await crawler.init()

    print("登录脉脉后按回车继续...")
    input()

    # 获取需要抓评论的URL
    urls = await get_urls_without_comments()
    print(f"找到 {len(urls)} 条需要抓评论的数据")

    for id, url, platform in urls:
        if not url:
            continue
        print(f"抓取 {id}: {url[:50]}...")

        try:
            comments = await crawler.crawl_comments(url, platform)
            if comments:
                text = json.dumps(comments, ensure_ascii=False)
                await update_comments(url, text)
                print(f"  获取到 {len(comments)} 条评论")
            else:
                print("  没有评论")
        except Exception as e:
            print(f"  失败: {e}")

        await asyncio.sleep(1)

    print("完成!")
    await crawler.browser.close()

if __name__ == "__main__":
    asyncio.run(main())
