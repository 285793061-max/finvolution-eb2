#!/usr/bin/env python3
"""
脉脉爬虫 - API版本
按顺序爬取：1.职言交流(gossip) 2.实名动态(feed)
包含完整URL和正确的字段分离
"""
import asyncio
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
COOKIE_PATH = os.getenv("MAIMAI_COOKIE_PATH", str(BASE_DIR / "data" / "maimai_cookies.json"))
DB_PATH = os.getenv("SENTIMENT_DB_PATH", str(BASE_DIR / "data" / "sentiment.db"))
CHROME_PATH = os.getenv("CHROME_PATH", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def get_proxy_config():
    proxy_server = os.getenv("MAIMAI_PROXY_SERVER")
    if not proxy_server:
        return None

    proxy = {"server": proxy_server}
    proxy_username = os.getenv("MAIMAI_PROXY_USERNAME")
    proxy_password = os.getenv("MAIMAI_PROXY_PASSWORD")
    if proxy_username:
        proxy["username"] = proxy_username
    if proxy_password:
        proxy["password"] = proxy_password
    return proxy


async def main():
    keyword = sys.argv[1] if len(sys.argv) > 1 else '信也科技'
    max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    print(f"🔍 开始爬取脉脉: {keyword} (最多 {max_results} 条)")

    async with async_playwright() as p:
        launch_options = {
            "executable_path": CHROME_PATH,
            "headless": False,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ],
        }
        proxy = get_proxy_config()
        if proxy:
            launch_options["proxy"] = proxy

        browser = await p.chromium.launch(**launch_options)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # 加载Cookie
        if os.path.exists(COOKIE_PATH):
            with open(COOKIE_PATH, 'r') as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            print("✅ 已加载Cookie")

        page = await context.new_page()

        # 1. 检查登录状态
        print("📱 打开脉脉登录页...")
        await page.goto("https://maimai.cn/platform/login", timeout=15000)
        await asyncio.sleep(3)

        if 'login' not in page.url.lower():
            print("✅ 已登录")
        else:
            print("⚠️ 需要登录，请在浏览器中完成登录...")
            print("   (等待10分钟，请慢慢登录)")
            for i in range(60):
                await asyncio.sleep(10)
                if 'login' not in page.url.lower():
                    print("✅ 登录成功!")
                    cookies = await context.cookies()
                    os.makedirs(os.path.dirname(COOKIE_PATH), exist_ok=True)
                    with open(COOKIE_PATH, 'w') as f:
                        json.dump(cookies, f)
                    print("✅ Cookie已保存")
                    break
                print(f"   等待中... ({i+1}/60)")
            else:
                print("❌ 登录超时")
                await browser.close()
                return

        # 2. 访问搜索页面以建立有效的会话
        print("📱 访问搜索页面建立有效会话...")
        search_url = f"https://maimai.cn/web/search_center?highlight=true&query={quote(keyword)}&type=gossip"
        await page.goto(search_url, timeout=15000)
        await asyncio.sleep(5)

        print("✅ 已登录，获取API会话...")

        # 3. 通过DOM解析获取数据
        print("\n📡 通过页面DOM获取数据...")
        all_posts = []

        # 3.1 职言 (gossip)
        print("\n📡 爬取职言交流 (匿名讨论区)...")
        gossip_url = f"https://maimai.cn/web/search_center?highlight=true&query={quote(keyword)}&type=gossip"
        await page.goto(gossip_url, timeout=30000)
        await asyncio.sleep(5)

        # 滚动加载更多数据
        for scroll_i in range(10):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            print(f"   滚动 {scroll_i+1}/10 加载更多...")

        # 先检查页面结构和元素
        page_info = await page.evaluate("""
        () => {
            return {
                url: window.location.href,
                title: document.title,
                bodyText: document.body.innerText.substring(0, 500),
                allLinks: Array.from(document.querySelectorAll('a')).slice(0, 10).map(a => a.href),
                cardCount: document.querySelectorAll('[class*="card"], [class*="item"], [class*="list"]').length,
                html: document.body.innerHTML.substring(0, 2000)
            };
        }
        """)
        print(f"   页面URL: {page_info['url']}")
        print(f"   页面标题: {page_info['title']}")
        print(f"   卡片数量: {page_info['cardCount']}")
        print(f"   内容片段: {page_info['bodyText'][:200]}")

        # 从页面提取数据
        gossip_js = """
        () => {
            const items = [];
            const cards = document.querySelectorAll('[class*="card"], [class*="item"], [class*="list"]');
            cards.forEach(card => {
                const titleEl = card.querySelector('[class*="title"], [class*="content"], [class*="text"]');
                const authorEl = card.querySelector('[class*="author"], [class*="name"], [class*="user"]');
                const timeEl = card.querySelector('[class*="time"], [class*="date"]');
                // 查找卡片内所有链接，找包含maimai.cn的详情链接
                const allLinks = card.querySelectorAll('a');
                let linkEl = null;
                for (const a of allLinks) {
                    if (a.href && (a.href.includes('gossip') || a.href.includes('community') || a.href.includes('detail'))) {
                        linkEl = a;
                        break;
                    }
                }
                const likesEl = card.querySelector('[class*="like"]');
                const commentEl = card.querySelector('[class*="comment"], [class*="cmt"]');

                if (titleEl && titleEl.innerText.length > 5) {
                    items.push({
                        title: titleEl.innerText.substring(0, 100),
                        content: titleEl.innerText,
                        author: authorEl ? authorEl.innerText : '',
                        time: timeEl ? timeEl.innerText : '',
                        url: linkEl ? linkEl.href : '',
                        likes: likesEl ? likesEl.innerText : '0',
                        comments: commentEl ? commentEl.innerText : '0'
                    });
                }
            });
            return items;
        }
        """
        gossip_items = await page.evaluate(gossip_js)

        print(f"   职言DOM获取 {len(gossip_items)} 条")

        for item in gossip_items:
            if len(all_posts) >= max_results:
                break
            all_posts.append({
                "title": item['title'],
                "content": item['content'],
                "author": item['author'],
                "username": item['author'],
                "url": item['url'],
                "publish_time": item['time'],
                "likes": int(item['likes']) if item['likes'].isdigit() else 0,
                "comments": int(item['comments']) if item['comments'].isdigit() else 0,
                "post_type": "gossip"
            })

        print(f"📊 职言共获取 {len(all_posts)} 条")

        # 3.2 实名动态 (feed)
        print("\n📡 爬取实名动态 (真实员工发布)...")
        feed_url = f"https://maimai.cn/web/search_center?highlight=true&query={quote(keyword)}&type=feed"

        # 在新页面打开实名动态
        page2 = await context.new_page()
        await page2.goto(feed_url, timeout=30000)
        await asyncio.sleep(5)

        for scroll_i in range(10):
            await page2.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            print(f"   滚动 {scroll_i+1}/10 加载更多...")

        # 检查实名页面结构
        feed_page_info = await page2.evaluate("""
        () => {
            return {
                url: window.location.href,
                title: document.title,
                bodyText: document.body.innerText.substring(0, 500),
                cardCount: document.querySelectorAll('[class*="card"], [class*="item"], [class*="list"]').length,
            };
        }
        """)
        print(f"   页面URL: {feed_page_info['url']}")
        print(f"   页面标题: {feed_page_info['title']}")
        print(f"   卡片数量: {feed_page_info['cardCount']}")
        print(f"   内容片段: {feed_page_info['bodyText'][:200]}")

        feed_js = """
        () => {
            const items = [];
            const cards = document.querySelectorAll('[class*="card"], [class*="item"], [class*="list"]');
            cards.forEach(card => {
                const titleEl = card.querySelector('[class*="title"], [class*="content"], [class*="text"]');
                const authorEl = card.querySelector('[class*="author"], [class*="name"], [class*="user"]');
                const timeEl = card.querySelector('[class*="time"], [class*="date"]');
                // 查找卡片内所有链接，找包含maimai.cn的详情链接
                const allLinks = card.querySelectorAll('a');
                let linkEl = null;
                for (const a of allLinks) {
                    if (a.href && a.href.startsWith('http') && !a.href.includes('mailto') && (a.href.includes('maimai') || a.href.includes('feed') || a.href.includes('detail'))) {
                        linkEl = a;
                        break;
                    }
                }
                const likesEl = card.querySelector('[class*="like"]');
                const commentEl = card.querySelector('[class*="comment"], [class*="cmt"]');

                if (titleEl && titleEl.innerText.length > 5) {
                    items.push({
                        title: titleEl.innerText.substring(0, 100),
                        content: titleEl.innerText,
                        author: authorEl ? authorEl.innerText : '',
                        time: timeEl ? timeEl.innerText : '',
                        url: linkEl ? linkEl.href : '',
                        likes: likesEl ? likesEl.innerText : '0',
                        comments: commentEl ? commentEl.innerText : '0'
                    });
                }
            });
            return items;
        }
        """
        feed_items = await page2.evaluate(feed_js)

        await page2.close()

        print(f"   实名DOM获取 {len(feed_items)} 条")

        for item in feed_items:
            if len(all_posts) >= max_results * 2:
                break
            all_posts.append({
                "title": item['title'],
                "content": item['content'],
                "author": item['author'],
                "username": item['author'],
                "url": item['url'],
                "publish_time": item['time'],
                "likes": int(item['likes']) if item['likes'].isdigit() else 0,
                "comments": int(item['comments']) if item['comments'].isdigit() else 0,
                "post_type": "feed"
            })

        print(f"📊 共获取 {len(all_posts)} 条帖子 (职言+实名)")

        # 4. 保存到数据库
        if all_posts:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            saved = 0
            for post in all_posts:
                try:
                    title = post['title']
                    post_type = post.get('post_type', 'gossip')
                    type_label = "职言" if post_type == "gossip" else "实名"

                    author_info = post['author'] if post['author'] else post['username']
                    content = f"[{type_label}] {author_info}\n{post['publish_time']}\n{post['content']}"

                    cur.execute("""INSERT INTO sentiment_data
                        (platform, title, content, url, publish_time, crawl_time, sentiment_label, likes, comments)
                        VALUES ('maimai', ?, ?, ?, ?, ?, 'neutral', ?, ?)""",
                        (title, content, post['url'],
                         post['publish_time'], datetime.now().isoformat(),
                         post['likes'], post['comments']))
                    saved += 1
                except Exception as e:
                    print(f"   保存错误: {e}")
            conn.commit()
            conn.close()
            print(f"💾 已保存 {saved} 条")

        await browser.close()
        print("🎉 完成!")


if __name__ == "__main__":
    asyncio.run(main())
