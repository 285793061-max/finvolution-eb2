#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时更新脉脉和小红书的点赞评论数
每两天运行一次
"""
import asyncio
import sqlite3
import os
import sys
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv("SENTIMENT_DB_PATH", str(BASE_DIR / "data" / "sentiment.db"))
COOKIE_PATH = os.getenv("MAIMAI_COOKIE_DIR", str(BASE_DIR / "data"))

sys.path.insert(0, str(BASE_DIR))


async def update_maimai():
    """更新脉脉的点赞评论数"""
    from playwright.async_api import async_playwright

    print('--- 更新脉脉数据 ---')

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(viewport={'width': 1920, 'height': 3000})
        page = await context.new_page()

        cookie_file = os.path.join(COOKIE_PATH, 'maimai.json')
        if os.path.exists(cookie_file):
            import json
            with open(cookie_file) as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, url, title FROM sentiment_data WHERE platform='maimai' AND url LIKE '%maimai.cn%' ORDER BY publish_time DESC LIMIT 30")
        rows = cur.fetchall()
        conn.close()

        print(f'  找到 {len(rows)} 条脉脉数据')

        updated = 0
        for row in rows:
            try:
                url = row['url']
                title = row['title']
                if not url:
                    continue

                await page.goto(url, wait_until='domcontentloaded', timeout=10000)
                await asyncio.sleep(1.5)

                # 滚动加载
                await page.evaluate('window.scrollBy(0, 500)')
                await asyncio.sleep(0.5)

                text = await page.evaluate('document.body.innerText')

                # 更精确的匹配
                like_match = re.search(r'(\d+)\s*赞', text)
                comment_match = re.search(r'(\d+)\s*评论', text)

                likes = int(like_match.group(1)) if like_match else 0
                comments = int(comment_match.group(1)) if comment_match else 0

                # 如果详情页没找到，尝试搜索结果页
                if comments == 0:
                    search_url = f'https://maimai.cn/web/search_center?highlight=true&query={title[:10]}&type=feed'
                    await page.goto(search_url, wait_until='networkidle', timeout=10000)
                    await asyncio.sleep(2)

                    # 在搜索结果中找
                    search_text = await page.evaluate('document.body.innerText')
                    lines = search_text.split('\n')
                    for line in lines:
                        if title[:8] in line:
                            cm = re.search(r'(\d+)\s*评论', line)
                            if cm:
                                comments = int(cm.group(1))
                                lm = re.search(r'(\d+)\s*赞', line)
                                if lm:
                                    likes = int(lm.group(1))
                                break

                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("UPDATE sentiment_data SET likes=?, comments=? WHERE id=?",
                           (likes, comments, row['id']))
                conn.commit()
                conn.close()

                if likes > 0 or comments > 0:
                    print(f'  {row["id"]}: {likes}赞 {comments}评论')
                    updated += 1
                await asyncio.sleep(0.8)

            except Exception as e:
                print(f'  错误: {e}')

        await browser.close()
        print(f'  脉脉更新: {updated} 条')
        return updated


async def update_xiaohongshu():
    """更新小红书的点赞评论数"""
    from playwright.async_api import async_playwright

    print('--- 更新小红书数据 ---')

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(viewport={'width': 1920, 'height': 3000})
        page = await context.new_page()

        cookie_file = os.path.join(COOKIE_PATH, 'xiaohongshu.json')
        if os.path.exists(cookie_file):
            import json
            with open(cookie_file) as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, url FROM sentiment_data WHERE platform='xiaohongshu'")
        rows = cur.fetchall()
        conn.close()

        print(f'  找到 {len(rows)} 条小红书数据')

        updated = 0
        for row in rows[:10]:
            try:
                url = row['url']
                if not url:
                    continue

                await page.goto(url, wait_until='domcontentloaded', timeout=10000)
                await asyncio.sleep(2)

                text = await page.evaluate('document.body.innerText')
                like_match = re.search(r'(\d+)\s*[赞喜欢]', text)
                comment_match = re.search(r'(\d+)\s*评论', text)

                likes = int(like_match.group(1)) if like_match else 0
                comments = int(comment_match.group(1)) if comment_match else 0

                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("UPDATE sentiment_data SET likes=?, comments=? WHERE id=?",
                           (likes, comments, row['id']))
                conn.commit()
                conn.close()

                if likes > 0 or comments > 0:
                    print(f'  {row["id"]}: {likes}赞 {comments}评论')
                    updated += 1
                await asyncio.sleep(1)

            except Exception as e:
                print(f'  错误: {e}')

        await browser.close()
        print(f'  小红书更新: {updated} 条')
        return updated


async def main():
    print(f'=== 更新点赞评论数 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ===')

    await update_maimai()
    await update_xiaohongshu()

    print('=== 完成 ===')


if __name__ == '__main__':
    asyncio.run(main())
