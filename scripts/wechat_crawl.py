#!/usr/bin/env python3
"""
微信公众号文章爬虫
使用方法：
1. 先安装依赖: .venv/bin/pip install playwright requests beautifulsoup4
2. 安装浏览器: .venv/bin/playwright install chromium
3. 运行脚本: .venv/bin/python scripts/wechat_crawl.py
"""
import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

async def crawl_wechat_articles():
    """使用Playwright爬取公众号文章"""
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print("请扫码登录微信公众号后台...")
        print("登录成功后会自动爬取")

        # 跳转登录
        await page.goto("https://mp.weixin.qq.com/", timeout=60000)

        # 等待登录成功（看到页面有"新的图文消息"按钮说明已登录）
        await page.wait_for_selector('text=新的图文消息', timeout=120000)
        print("登录成功！")

        # 进入草稿箱或已发送文章页面
        # 这里以已发送为例，你可以根据需要修改URL
        await page.goto("https://mp.weixin.qq.com/cgi-bin/appmsgpublish?sub=list&begin=0&count=20&token=&lang=zh_CN")
        await page.wait_for_timeout(3000)

        # 爬取文章列表
        articles = []

        # 获取页面内容
        content = await page.content()
        print("页面内容长度:", len(content))

        # 尝试解析文章
        # 公众号页面结构可能随时变化，这里需要根据实际调整
        try:
            # 尝试找文章链接
            links = await page.query_selector_all('a[href*="/appmsg"]')
            for link in links[:10]:
                title = await link.text_content()
                href = await link.get_attribute('href')
                if title and href:
                    print(f"找到: {title.strip()}")
                    articles.append({
                        "platform": "公众号",
                        "title": title.strip(),
                        "url": "https://mp.weixin.qq.com" + href,
                        "publish_time": datetime.now().strftime("%Y-%m-%d"),
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "metrics": {"views": 0, "likes": 0, "comments": 0, "shares": 0}
                    })
        except Exception as e:
            print(f"解析出错: {e}")

        if not articles:
            print("未找到文章，请手动复制文章信息")
            print("请在浏览器中打开文章列表页面，然后按回车继续...")
            input()

        await browser.close()

        # 保存结果
        if articles:
            with open('wechat_articles.json', 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            print(f"已保存 {len(articles)} 篇文章到 wechat_articles.json")

            # 询问是否导入到系统
            print("\n是否导入到内容分析系统？(y/n)")
            if input().strip().lower() == 'y':
                import requests
                resp = requests.post('http://localhost:8000/api/content/import',
                             json={"items": articles})
                result = resp.json()
                if result.get('success'):
                    print(f"导入成功！共 {result.get('imported')} 篇")
                else:
                    print(f"导入失败: {result}")
        else:
            print("没有找到文章")

if __name__ == "__main__":
    asyncio.run(crawl_wechat_articles())