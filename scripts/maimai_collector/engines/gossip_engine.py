from __future__ import annotations

import asyncio
import json
import os
from typing import List
from pathlib import Path

from .base import Engine


class GossipEngine(Engine):
    """脉脉职言采集引擎"""

    def __init__(
        self,
        cookie_path: Path,
        chrome_path: str,
        user_agent: str,
        max_posts: int = 30,
        max_scrolls: int = 5,
        scroll_pause_s: float = 2.0,
        wait_load_timeout: int = 15000,
        login_wait_minutes: int = 3,
    ):
        self.cookie_path = cookie_path
        self.chrome_path = chrome_path
        self.user_agent = user_agent
        self.max_posts = max_posts
        self.max_scrolls = max_scrolls
        self.scroll_pause_s = scroll_pause_s
        self.wait_load_timeout = wait_load_timeout
        self.login_wait_minutes = login_wait_minutes

    @property
    def name(self) -> str:
        return "gossip"

    async def collect(self, keyword: str, **kwargs) -> List[dict]:
        """采集职言帖子"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                executable_path=self.chrome_path,
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    f'--user-agent={self.user_agent}'
                ]
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=self.user_agent
            )

            # 加载 Cookie
            if self.cookie_path.exists():
                with open(self.cookie_path, 'r') as f:
                    cookies = json.load(f)
                await context.add_cookies(cookies)
                print("✅ 已加载 Cookie")

            page = await context.new_page()

            # 1. 检查登录状态
            print("📱 打开脉脉登录页...")
            await page.goto("https://maimai.cn/platform/login", wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(3)

            current_url = page.url
            print(f"   当前URL: {current_url}")

            # 如果需要登录
            if 'login' in current_url.lower():
                print("⚠️ 需要登录，请在浏览器中完成...")
                for i in range(self.login_wait_minutes * 6):
                    await asyncio.sleep(10)
                    try:
                        current_url = page.url
                        if 'login' not in current_url.lower():
                            print("✅ 登录成功！")
                            break
                    except:
                        break
                    print(f"   等待中... ({i+1}/{self.login_wait_minutes * 6})")
                else:
                    print("❌ 登录超时")
                    await browser.close()
                    return []

                # 保存新 Cookie
                cookies = await context.cookies()
                with open(self.cookie_path, 'w') as f:
                    json.dump(cookies, f)
                print("✅ Cookie 已保存")

            # 2. 打开搜索页（职言）
            encoded_keyword = keyword.replace(' ', '%20')
            search_url = f"https://maimai.cn/web/search_center?type=gossip&query={encoded_keyword}"
            print(f"📱 打开: {search_url}")

            try:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=self.wait_load_timeout)
            except Exception as e:
                print(f"⚠️ 页面跳转失败: {e}")
                await browser.close()
                return []

            # 3. 点击"时间排序"
            print("🔄 点击时间排序按钮...")
            await asyncio.sleep(3)
            try:
                time_btn = await page.query_selector('text=时间')
                if time_btn:
                    await time_btn.click()
                    print("   已点击'时间'排序按钮")
                    await asyncio.sleep(2)
            except Exception as e:
                print(f"   点击失败: {e}")

            # 4. 等待页面加载
            print("⏳ 等待页面加载...")
            await asyncio.sleep(5)

            # 5. 等待搜索结果
            print("⏳ 等待搜索结果...")
            result_loaded = False
            for i in range(30):
                await asyncio.sleep(1)
                try:
                    count = await page.evaluate('''() => {
                        let els = document.querySelectorAll(".list-group-item");
                        if (els.length > 0) return els.length;
                        els = document.querySelectorAll("[class*='item']");
                        return els.length;
                    }''')
                    print(f"   检查 {i+1}/30: 找到 {count} 个元素")
                    if count > 5:
                        result_loaded = True
                        break
                except Exception as e:
                    print(f"   检查出错: {e}")
                    break

            if not result_loaded:
                print("⚠️ 搜索结果加载失败...")
                html = await page.content()
                with open('/tmp/maimai_debug.html', 'w') as f:
                    f.write(html)
                print("   HTML已保存到/tmp/maimai_debug.html")

            # 6. 滚动加载更多
            print("📜 滚动加载更多...")
            for i in range(self.max_scrolls):
                try:
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(self.scroll_pause_s)
                    print(f"   滚动 {i+1}/{self.max_scrolls}")
                except:
                    break

            # 7. 提取数据
            print("📝 提取数据...")
            posts = await page.evaluate('''() => {
                const results = [];
                const cards = document.querySelectorAll(".list-group-item");

                cards.forEach((card, idx) => {
                    if (idx >= 30) return;

                    const text = card.textContent || "";
                    if (text.length < 10) return;

                    let link = "";
                    const aTag = card.querySelector("a");
                    if (aTag) link = aTag.href || "";

                    results.push({
                        title: text.slice(0, 200),
                        content: text.slice(0, 500),
                        author: "",
                        publish_time: "",
                        url: link
                    });
                });

                return results;
            }''')

            print(f"📊 共抓取 {len(posts)} 条帖子")
            await browser.close()

            return posts


# 导入需要在类外面
from playwright.async_api import async_playwright