from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
import os
import re

from .routers import analysis

# 获取静态文件目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
# 舆情数据库 - 使用环境变量或当前项目的数据目录
DB_PATH = os.getenv("SENTIMENT_DB_PATH") or os.path.join(BASE_DIR, "data", "sentiment.db")
# 内容分析数据库
CONTENT_DB_PATH = os.path.join(BASE_DIR, "data", "content.db")


def init_content_db():
    """初始化内容分析数据库"""
    import sqlite3
    conn = sqlite3.connect(CONTENT_DB_PATH)
    cur = conn.cursor()

    # 内容表 - 存储发布的内容信息
    cur.execute("""CREATE TABLE IF NOT EXISTS contents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT,
        url TEXT,
        publish_time TEXT,
        created_time TEXT DEFAULT CURRENT_TIMESTAMP,
        deleted_time TEXT
    )""")

    # 每日指标表 - 存储每天的数据变化
    cur.execute("""CREATE TABLE IF NOT EXISTS daily_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content_id INTEGER,
        date TEXT NOT NULL,
        views INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        comments INTEGER DEFAULT 0,
        shares INTEGER DEFAULT 0,
        favorites INTEGER DEFAULT 0,
        coins INTEGER DEFAULT 0,
        followers INTEGER DEFAULT 0,
        created_time TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (content_id) REFERENCES contents(id)
    )""")

    # 账号整体数据表 - 存储账号每日粉丝数
    cur.execute("""CREATE TABLE IF NOT EXISTS account_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,
        date TEXT NOT NULL,
        followers INTEGER DEFAULT 0,
        created_time TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(platform, date)
    )""")

    conn.commit()
    conn.close()


def init_qa_db():
    """初始化招聘问答数据库"""
    import sqlite3

    qa_db = os.path.join(BASE_DIR, "data", "qa.db")
    conn = sqlite3.connect(qa_db)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS qa_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        answer TEXT,
        contact TEXT,
        status TEXT DEFAULT 'pending',
        created_time TEXT DEFAULT CURRENT_TIMESTAMP,
        answered_time TEXT
    )""")
    conn.commit()
    conn.close()


def init_articles_db():
    """初始化资料/文章数据库"""
    import sqlite3

    articles_db = os.path.join(BASE_DIR, "data", "articles.db")
    conn = sqlite3.connect(articles_db)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        type TEXT NOT NULL,
        content TEXT NOT NULL,
        created_time TEXT DEFAULT CURRENT_TIMESTAMP,
        deleted_time TEXT
    )""")
    conn.commit()
    conn.close()


def init_projects_db():
    """初始化项目管理数据库"""
    import sqlite3

    projects_db = os.path.join(BASE_DIR, "data", "projects.db")
    conn = sqlite3.connect(projects_db)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'planning',
        created_time TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS project_timelines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        task TEXT,
        start_date TEXT,
        end_date TEXT,
        status TEXT DEFAULT 'pending'
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS project_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        name TEXT,
        role TEXT
    )""")
    conn.commit()
    conn.close()


def _read_frontend_wechat_app_id():
    config_path = os.path.join(BASE_DIR, "static", "config.js")
    if not os.path.exists(config_path):
        return None

    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()
    appid_match = re.search(r'appId\s*:\s*[\'"]([^\'"]+)[\'"]', content, re.IGNORECASE)
    if appid_match:
        return appid_match.group(1) or None
    return None


def get_wechat_credentials(appid=None, appsecret=None):
    """获取微信配置。AppSecret 只从后端参数或环境变量读取。"""
    resolved_appid = appid or os.getenv("WECHAT_APP_ID") or _read_frontend_wechat_app_id()
    resolved_secret = appsecret or os.getenv("WECHAT_APP_SECRET")
    return resolved_appid, resolved_secret


# 平台关键指标配置
PLATFORM_METRICS = {
    "公众号": {"views": "阅读量", "likes": "点赞", "comments": "在看", "shares": "转发"},
    "视频号": {"views": "播放量", "likes": "点赞", "comments": "评论", "shares": "转发", "favorites": "收藏"},
    "领英": {"views": "阅读量", "likes": "点赞", "comments": "评论", "shares": "分享"},
    "小红书": {"likes": "点赞", "favorites": "收藏", "comments": "评论", "shares": "分享"},
    "B站": {"views": "播放量", "likes": "点赞", "coins": "投币", "favorites": "收藏", "comments": "评论"}
}

PLATFORM_LIST = ["公众号", "视频号", "领英", "小红书", "B站"]


def init_sentiment_db_from_json():
    """从JSON文件初始化情感数据库"""
    import sqlite3
    import json

    # 使用环境变量指定的路径，或者默认路径
    db_path = os.getenv("SENTIMENT_DB_PATH", DB_PATH)
    json_path = os.path.join(BASE_DIR, "data", "sentiment_data.json")
    if not os.path.exists(json_path):
        print(f"JSON文件不存在: {json_path}")
        return

    # 如果数据库已存在且有数据，跳过
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM sentiment_data")
            count = cur.fetchone()[0]
            if count > 0:
                conn.close()
                return
        except:
            pass
        conn.close()

    # 从JSON加载数据
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 创建数据库和表
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sentiment_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            author TEXT,
            publish_time TEXT,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0,
            url TEXT,
            sentiment_score REAL,
            sentiment_label TEXT,
            sentiment_confidence REAL,
            keywords TEXT,
            crawl_time TEXT NOT NULL,
            metadata TEXT,
            category TEXT,
            source_type TEXT DEFAULT 'external',
            is_ad INTEGER DEFAULT 0,
            is_reviewed INTEGER DEFAULT 0,
            image TEXT,
            comments_text TEXT
        )
    """)

    for item in data:
        cur.execute("""
            INSERT INTO sentiment_data (
                platform, title, content, author, publish_time,
                likes, comments, shares, views, url,
                sentiment_score, sentiment_label, sentiment_confidence,
                keywords, crawl_time, metadata, category,
                source_type, is_ad, is_reviewed, image, comments_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.get('platform'), item.get('title'), item.get('content'),
            item.get('author'), item.get('publish_time'),
            item.get('likes', 0), item.get('comments', 0), item.get('shares', 0),
            item.get('views', 0), item.get('url'),
            item.get('sentiment_score'), item.get('sentiment_label'),
            item.get('sentiment_confidence'), item.get('keywords'),
            item.get('crawl_time'), item.get('metadata'), item.get('category'),
            item.get('source_type', 'external'), item.get('is_ad', 0),
            item.get('is_reviewed', 0), item.get('image'), item.get('comments_text')
        ))

    conn.commit()
    conn.close()
    print(f"从JSON加载了 {len(data)} 条数据到数据库")


def get_stats():
    """统计数据"""
    if not os.path.exists(DB_PATH):
        return {"total": 0, "maimai": 0, "xiaohongshu": 0}

    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM sentiment_data")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM sentiment_data WHERE platform='maimai'")
    maimai = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM sentiment_data WHERE platform='xiaohongshu'")
    xhs = cur.fetchone()[0]

    conn.close()
    return {"total": total, "maimai": maimai, "xiaohongshu": xhs}


def get_data(limit=100, sentiment=None):
    """获取数据列表"""
    if not os.path.exists(DB_PATH):
        return []

    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    query = "SELECT id, platform, title, content, url, likes, comments, publish_time, crawl_time, sentiment_label, source_type, image FROM sentiment_data"
    params = []

    if sentiment:
        query += " WHERE sentiment_label = ?"
        params.append(sentiment)

    # 按笔记发布时间排序（最新的在前）
    # SQLite没有COALESCE，用CASE处理空值
    query += " ORDER BY CASE WHEN publish_time IS NULL OR publish_time = '' THEN 0 ELSE 1 END DESC, publish_time DESC, crawl_time DESC LIMIT ?"
    params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "platform": row[1],
            "title": row[2],
            "content": row[3],
            "url": row[4],
            "likes": row[5],
            "comments": row[6],
            "publish_time": row[7],
            "crawl_time": row[8],
            "sentiment_label": row[9],
            "source_type": row[10],
            "image": row[11] if len(row) > 11 else None
        }
        for row in rows
    ]


def create_app() -> FastAPI:
    app = FastAPI(
        title="雇主品牌管理后台",
        description="雇主品牌管理系统",
        version="1.0.0",
    )

    init_content_db()
    init_qa_db()
    init_articles_db()
    init_projects_db()
    init_sentiment_db_from_json()

    app.include_router(analysis.router)
    from .routers import content_gen
    from .routers import competitor
    app.include_router(content_gen.router)
    app.include_router(competitor.router)

    # 静态文件
    if os.path.exists(STATIC_DIR):
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def home():
        """主页面 - 显示管理后台"""
        index_path = os.path.join(STATIC_DIR, "main.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "欢迎使用雇主品牌管理系统"}

    @app.get("/sentiment")
    async def sentiment():
        """舆情监控页面"""
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_path):
            return RedirectResponse("/static/index.html")
        return {"message": "舆情监控系统"}

    @app.get("/health")
    async def health():
        stats = get_stats()
        return {"status": "ok", "service": "雇主品牌管理", "stats": stats}

    @app.get("/api/data")
    async def api_data(limit: int = 100, sentiment: str = None):
        """API: 获取数据列表"""
        data = get_data(limit=limit, sentiment=sentiment)
        return data

    @app.post("/api/sentiment/update")
    async def update_sentiment(request: dict):
        """更新情绪标签"""
        import sqlite3

        id = request.get('id')
        sentiment_label = request.get('sentiment_label')

        if not id or not sentiment_label:
            return {"success": False, "error": "缺少参数"}

        if not os.path.exists(DB_PATH):
            return {"success": False, "error": "数据库不存在"}

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE sentiment_data SET sentiment_label = ? WHERE id = ?",
                    (sentiment_label, id))
        conn.commit()
        conn.close()

        return {"success": True}

    @app.post("/api/delete")
    async def delete_item(request: dict):
        """删除数据"""
        import sqlite3

        id = request.get('id')

        if not id:
            return {"success": False, "error": "缺少参数"}

        if not os.path.exists(DB_PATH):
            return {"success": False, "error": "数据库不存在"}

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM sentiment_data WHERE id = ?", (id,))
        conn.commit()
        conn.close()

        return {"success": True}

    @app.get("/api/stats")
    async def api_stats():
        """API: 获取统计数据"""
        return get_stats()

    @app.post("/api/crawl")
    async def run_crawl():
        """触发爬虫更新数据"""
        import subprocess
        import threading
        import shlex
        import sys

        crawl_command = os.getenv("EMPLOYER_CRAWL_COMMAND")
        if crawl_command:
            command_args = shlex.split(crawl_command)
        else:
            script_path = os.path.join(BASE_DIR, "scripts", "maimai_crawl.py")
            if not os.path.exists(script_path):
                return {"success": False, "error": "未配置爬虫命令，且未找到本地 scripts/maimai_crawl.py"}
            command_args = [sys.executable, script_path]

        def run_script():
            try:
                env = os.environ.copy()
                env["PYTHONPATH"] = BASE_DIR + os.pathsep + env.get("PYTHONPATH", "")
                result = subprocess.run(
                    command_args,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=BASE_DIR,
                    env=env
                )
                print("爬虫输出:", result.stdout)
                if result.stderr:
                    print("爬虫错误:", result.stderr)
            except Exception as e:
                print(f"爬虫运行失败: {e}")

        thread = threading.Thread(target=run_script)
        thread.start()

        return {"success": True, "message": "采集任务已启动。如需要登录，请在弹出的浏览器中完成操作。"}

    # QA 问答系统 API
    @app.post("/api/qa/submit")
    async def qa_submit(request: dict):
        """提交问题"""
        import sqlite3
        from datetime import datetime

        init_qa_db()
        qa_db = os.path.join(BASE_DIR, "data", "qa.db")
        conn = sqlite3.connect(qa_db)
        cur = conn.cursor()

        now = datetime.now().isoformat()
        question = request.get('question', '')
        contact = request.get('contact', '')
        status = request.get('status', 'pending')  # 支持自定义状态

        cur.execute("INSERT INTO qa_questions (question, contact, status, created_time) VALUES (?, ?, ?, ?)",
                  (question, contact, status, now))
        conn.commit()
        conn.close()
        return {"success": True}

    @app.get("/api/qa/list")
    async def qa_list():
        """获取问题列表"""
        import sqlite3

        init_qa_db()
        qa_db = os.path.join(BASE_DIR, "data", "qa.db")
        if not os.path.exists(qa_db):
            return []

        conn = sqlite3.connect(qa_db)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM qa_questions ORDER BY created_time DESC")
        rows = cur.fetchall()
        conn.close()

        return [
            {
                "id": row['id'],
                "question": row['question'],
                "answer": row['answer'],
                "contact": row['contact'],
                "status": row['status'],
                "created_time": row['created_time'],
                "answered_time": row['answered_time']
            }
            for row in rows
        ]

    @app.post("/api/qa/answer")
    async def qa_answer(request: dict):
        """回复问题"""
        import sqlite3
        from datetime import datetime

        init_qa_db()
        qa_db = os.path.join(BASE_DIR, "data", "qa.db")
        conn = sqlite3.connect(qa_db)
        cur = conn.cursor()

        now = datetime.now().isoformat()
        cur.execute("UPDATE qa_questions SET answer = ?, status = 'answered', answered_time = ? WHERE id = ?",
                  (request.get('answer', ''), now, request.get('id', 0)))
        conn.commit()
        conn.close()
        return {"success": True}

    # 内容发布 API
    @app.get("/api/articles")
    async def articles_list(type: str = None):
        """获取文章列表（不包含已删除）"""
        import sqlite3
        init_articles_db()
        articles_db = os.path.join(BASE_DIR, "data", "articles.db")
        if not os.path.exists(articles_db):
            return []

        conn = sqlite3.connect(articles_db)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if type:
            cur.execute("SELECT * FROM articles WHERE type = ? AND deleted_time IS NULL ORDER BY created_time DESC", (type,))
        else:
            cur.execute("SELECT * FROM articles WHERE deleted_time IS NULL ORDER BY created_time DESC")
        rows = cur.fetchall()
        conn.close()

        type_map = {"news": "公司动态", "recruit": "招聘公告", "event": "活动通知", "link": "链接", "project": "项目"}
        return [
            {
                "id": row['id'],
                "title": row['title'],
                "type": row['type'],
                "type_name": type_map.get(row['type'], row['type']),
                "content": row['content'],
                "created_time": row['created_time']
            }
            for row in rows
        ]

    @app.get("/api/articles/recycle")
    async def articles_recycle():
        """获取回收站文章"""
        import sqlite3
        init_articles_db()
        articles_db = os.path.join(BASE_DIR, "data", "articles.db")
        if not os.path.exists(articles_db):
            return []

        conn = sqlite3.connect(articles_db)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM articles WHERE deleted_time IS NOT NULL ORDER BY deleted_time DESC")
        rows = cur.fetchall()
        conn.close()

        type_map = {"news": "公司动态", "recruit": "招聘公告", "event": "活动通知", "link": "链接", "project": "项目"}
        return [
            {
                "id": row['id'],
                "title": row['title'],
                "type": row['type'],
                "type_name": type_map.get(row['type'], row['type']),
                "content": row['content'],
                "created_time": row['created_time'],
                "deleted_time": row['deleted_time']
            }
            for row in rows
        ]

    @app.post("/api/articles")
    async def articles_create(request: dict):
        """创建文章"""
        import sqlite3
        from datetime import datetime

        init_articles_db()
        articles_db = os.path.join(BASE_DIR, "data", "articles.db")
        conn = sqlite3.connect(articles_db)
        cur = conn.cursor()

        # 创建表（如果不存在）
        cur.execute("""CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            created_time TEXT DEFAULT CURRENT_TIMESTAMP,
            deleted_time TEXT
        )""")

        now = datetime.now().isoformat()
        cur.execute("INSERT INTO articles (title, type, content, created_time) VALUES (?, ?, ?, ?)",
                  (request.get('title', ''), request.get('type', 'news'), request.get('content', ''), now))
        conn.commit()
        conn.close()
        return {"success": True}

    @app.delete("/api/articles")
    async def articles_delete(id: int):
        """删除文章（放入回收站）"""
        import sqlite3
        from datetime import datetime

        init_articles_db()
        articles_db = os.path.join(BASE_DIR, "data", "articles.db")
        conn = sqlite3.connect(articles_db)
        cur = conn.cursor()

        now = datetime.now().isoformat()
        cur.execute("UPDATE articles SET deleted_time = ? WHERE id = ?", (now, id))
        conn.commit()
        conn.close()
        return {"success": True}

    @app.post("/api/articles/restore")
    async def articles_restore(request: dict):
        """恢复文章"""
        import sqlite3

        init_articles_db()
        articles_db = os.path.join(BASE_DIR, "data", "articles.db")
        conn = sqlite3.connect(articles_db)
        cur = conn.cursor()
        cur.execute("UPDATE articles SET deleted_time = NULL WHERE id = ?", (request.get('id'),))
        conn.commit()
        conn.close()
        return {"success": True}

    @app.delete("/api/articles/permanent")
    async def articles_permanent_delete(request: dict):
        """永久删除文章"""
        import sqlite3

        init_articles_db()
        articles_db = os.path.join(BASE_DIR, "data", "articles.db")
        conn = sqlite3.connect(articles_db)
        cur = conn.cursor()
        cur.execute("DELETE FROM articles WHERE id = ?", (request.get('id'),))
        conn.commit()
        conn.close()
        return {"success": True}

    # 项目管理 API - 独立数据库
    @app.get("/api/projects")
    async def projects_list():
        """获取项目列表"""
        import sqlite3
        init_projects_db()
        projects_db = os.path.join(BASE_DIR, "data", "projects.db")
        if not os.path.exists(projects_db):
            return []

        conn = sqlite3.connect(projects_db)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM projects ORDER BY created_time DESC")
        rows = cur.fetchall()
        conn.close()

        return [
            {
                "id": row['id'],
                "title": row['title'],
                "description": row['description'],
                "status": row['status'],
                "created_time": row['created_time']
            }
            for row in rows
        ]

    @app.post("/api/projects")
    async def projects_create(request: dict):
        """创建项目"""
        import sqlite3
        from datetime import datetime

        init_projects_db()
        projects_db = os.path.join(BASE_DIR, "data", "projects.db")
        conn = sqlite3.connect(projects_db)
        cur = conn.cursor()

        # 创建表（如果不存在）
        cur.execute("""CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'planning',
            created_time TEXT
        )""")

        now = datetime.now().isoformat()
        cur.execute("INSERT INTO projects (title, description, status, created_time) VALUES (?, ?, ?, ?)",
                  (request.get('title', ''), request.get('description', ''), request.get('status', 'planning'), now))
        conn.commit()
        conn.close()
        return {"success": True}

    @app.delete("/api/projects")
    async def projects_delete(id: int):
        """删除项目"""
        import sqlite3

        init_projects_db()
        projects_db = os.path.join(BASE_DIR, "data", "projects.db")
        conn = sqlite3.connect(projects_db)
        cur = conn.cursor()
        cur.execute("DELETE FROM projects WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return {"success": True}

    # 项目详情 API
    @app.get("/api/projects/{project_id}")
    async def project_detail(project_id: int):
        """获取项目详情（包括时间规划和人员）"""
        import sqlite3

        init_projects_db()
        projects_db = os.path.join(BASE_DIR, "data", "projects.db")
        conn = sqlite3.connect(projects_db)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 获取项目基本信息
        cur.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        project = cur.fetchone()

        if not project:
            conn.close()
            return {"error": "项目不存在"}

        # 获取时间规划
        cur.execute("SELECT * FROM project_timelines WHERE project_id = ? ORDER BY start_date", (project_id,))
        timelines = cur.fetchall()

        # 获取项目成员
        cur.execute("SELECT * FROM project_members WHERE project_id = ?", (project_id,))
        members = cur.fetchall()

        conn.close()

        return {
            "id": project['id'],
            "title": project['title'],
            "description": project['description'],
            "status": project['status'],
            "created_time": project['created_time'],
            "timelines": [
                {
                    "id": row['id'],
                    "task": row['task'],
                    "start_date": row['start_date'],
                    "end_date": row['end_date'],
                    "status": row['status']
                }
                for row in timelines
            ],
            "members": [
                {
                    "id": row['id'],
                    "name": row['name'],
                    "role": row['role']
                }
                for row in members
            ]
        }

    @app.post("/api/projects/{project_id}/timelines")
    async def add_timeline(project_id: int, request: dict):
        """添加时间规划"""
        import sqlite3
        from datetime import datetime

        init_projects_db()
        projects_db = os.path.join(BASE_DIR, "data", "projects.db")
        conn = sqlite3.connect(projects_db)
        cur = conn.cursor()

        # 创建时间规划表
        cur.execute("""CREATE TABLE IF NOT EXISTS project_timelines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            task TEXT,
            start_date TEXT,
            end_date TEXT,
            status TEXT DEFAULT 'pending'
        )""")

        now = datetime.now().isoformat()
        cur.execute("INSERT INTO project_timelines (project_id, task, start_date, end_date, status) VALUES (?, ?, ?, ?, ?)",
                  (project_id, request.get('task', ''), request.get('start_date', ''), request.get('end_date', ''), 'pending'))
        conn.commit()
        conn.close()
        return {"success": True}

    @app.post("/api/projects/{project_id}/members")
    async def add_member(project_id: int, request: dict):
        """添加项目成员"""
        import sqlite3
        from datetime import datetime

        init_projects_db()
        projects_db = os.path.join(BASE_DIR, "data", "projects.db")
        conn = sqlite3.connect(projects_db)
        cur = conn.cursor()

        # 创建成员表
        cur.execute("""CREATE TABLE IF NOT EXISTS project_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            name TEXT,
            role TEXT
        )""")

        now = datetime.now().isoformat()
        cur.execute("INSERT INTO project_members (project_id, name, role) VALUES (?, ?, ?)",
                  (project_id, request.get('name', ''), request.get('role', '')))
        conn.commit()
        conn.close()
        return {"success": True}

    @app.delete("/api/projects/timelines/{timeline_id}")
    async def delete_timeline(timeline_id: int):
        """删除时间规划"""
        import sqlite3

        init_projects_db()
        projects_db = os.path.join(BASE_DIR, "data", "projects.db")
        conn = sqlite3.connect(projects_db)
        cur = conn.cursor()
        cur.execute("DELETE FROM project_timelines WHERE id = ?", (timeline_id,))
        conn.commit()
        conn.close()
        return {"success": True}

    @app.delete("/api/projects/members/{member_id}")
    async def delete_member(member_id: int):
        """删除项目成员"""
        import sqlite3

        init_projects_db()
        projects_db = os.path.join(BASE_DIR, "data", "projects.db")
        conn = sqlite3.connect(projects_db)
        cur = conn.cursor()
        cur.execute("DELETE FROM project_members WHERE id = ?", (member_id,))
        conn.commit()
        conn.close()
        return {"success": True}

    # 微信公众号OAuth代理 API
    @app.get("/api/wechat/auth")
    async def wechat_auth(code: str, appid: str = None, appsecret: str = None):
        """微信OAuth - 通过code换取access_token和openid"""
        import requests

        appid, appsecret = get_wechat_credentials(appid, appsecret)

        if not appid or not appsecret:
            return {"error": "缺少微信公众号 AppID 或 AppSecret，请配置 WECHAT_APP_ID / WECHAT_APP_SECRET"}

        # 调用微信API
        url = f"https://api.weixin.qq.com/sns/oauth2/access_token?appid={appid}&secret={appsecret}&code={code}&grant_type=authorization_code"
        try:
            resp = requests.get(url, timeout=5)
            data = resp.json()
            if data.get("openid"):
                return {
                    "openid": data.get("openid"),
                    "access_token": data.get("access_token"),
                    "scope": data.get("scope")
                }
            else:
                return {"error": data.get("errcode", "未知错误")}
        except Exception as e:
            return {"error": str(e)}

    # ========== 热门话题 API ==========
    @app.get("/api/hot-topics")
    async def hot_topics(platform: str = None):
        """获取各平台热门话题，platform为空返回所有平台"""
        from app.services.hot_topics import get_all_hot_topics, fetch_weibo_hot, fetch_douyin_hot, fetch_zhihu_hot
        if platform:
            if platform == 'weibo':
                return {"platform": "微博", "data": fetch_weibo_hot()}
            elif platform == 'douyin':
                return {"platform": "抖音", "data": fetch_douyin_hot()}
            elif platform == 'zhihu':
                return {"platform": "知乎", "data": fetch_zhihu_hot()}
            else:
                return {"error": f"不支持的平台: {platform}"}
        return get_all_hot_topics()

    @app.get("/api/hot-topics/weibo")
    async def hot_weibo():
        from app.services.hot_topics import fetch_weibo_hot
        return {"platform": "微博", "data": fetch_weibo_hot()}

    @app.get("/api/hot-topics/douyin")
    async def hot_douyin():
        from app.services.hot_topics import fetch_douyin_hot
        return {"platform": "抖音", "data": fetch_douyin_hot()}

    @app.get("/api/hot-topics/zhihu")
    async def hot_zhihu():
        from app.services.hot_topics import fetch_zhihu_hot
        return {"platform": "知乎", "data": fetch_zhihu_hot()}

    # ========== 内容分析 API ==========
    @app.get("/api/content/platforms")
    async def content_platforms():
        """获取支持的平台列表"""
        return {"platforms": PLATFORM_LIST, "metrics": PLATFORM_METRICS}

    @app.get("/api/content/list")
    async def content_list(platform: str = None):
        """获取内容列表"""
        import sqlite3
        init_content_db()
        conn = sqlite3.connect(CONTENT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        if platform:
            cur.execute("SELECT * FROM contents WHERE platform = ? AND deleted_time IS NULL ORDER BY publish_time DESC", (platform,))
        else:
            cur.execute("SELECT * FROM contents WHERE deleted_time IS NULL ORDER BY publish_time DESC")

        rows = cur.fetchall()
        conn.close()

        result = []
        for row in rows:
            # 获取最新的一条指标数据
            conn = sqlite3.connect(CONTENT_DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM daily_metrics WHERE content_id = ? ORDER BY date DESC LIMIT 1", (row['id'],))
            latest = c.fetchone()
            conn.close()

            result.append({
                "id": row['id'],
                "platform": row['platform'],
                "title": row['title'],
                "url": row['url'],
                "publish_time": row['publish_time'],
                "metrics": dict(latest) if latest else {}
            })

        return result

    @app.post("/api/content")
    async def content_create(request: dict):
        """创建内容"""
        import sqlite3
        from datetime import datetime
        init_content_db()

        conn = sqlite3.connect(CONTENT_DB_PATH)
        cur = conn.cursor()

        now = datetime.now().isoformat()
        cur.execute("""INSERT INTO contents (platform, title, content, url, publish_time, created_time)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                    (request.get('platform'), request.get('title'), request.get('content', ''),
                     request.get('url', ''), request.get('publish_time', ''), now))
        conn.commit()
        content_id = cur.lastrowid
        conn.close()

        # 如果传入了初始指标数据，同时创建
        if request.get('metrics'):
            conn = sqlite3.connect(CONTENT_DB_PATH)
            cur = conn.cursor()
            date = request.get('date', now[:10])
            m = request.get('metrics', {})
            cur.execute("""INSERT INTO daily_metrics (content_id, date, views, likes, comments, shares, favorites, coins)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (content_id, date, m.get('views', 0), m.get('likes', 0), m.get('comments', 0),
                         m.get('shares', 0), m.get('favorites', 0), m.get('coins', 0)))
            conn.commit()
            conn.close()

        return {"success": True, "id": content_id}

    @app.post("/api/content/import")
    async def content_import(request: dict):
        """批量导入内容数据"""
        import sqlite3
        from datetime import datetime
        init_content_db()

        items = request.get('items', [])
        imported = 0

        conn = sqlite3.connect(CONTENT_DB_PATH)
        cur = conn.cursor()
        now = datetime.now().isoformat()

        for item in items:
            # 检查内容是否已存在
            cur.execute("SELECT id FROM contents WHERE platform = ? AND title = ? AND deleted_time IS NULL",
                        (item.get('platform'), item.get('title')))
            existing = cur.fetchone()

            if existing:
                content_id = existing[0]
            else:
                cur.execute("""INSERT INTO contents (platform, title, content, url, publish_time, created_time)
                            VALUES (?, ?, ?, ?, ?, ?)""",
                            (item.get('platform'), item.get('title'), item.get('content', ''),
                             item.get('url', ''), item.get('publish_time', ''), now))
                content_id = cur.lastrowid

            # 更新或添加指标
            date = item.get('date', now[:10])
            m = item.get('metrics', {})
            cur.execute("""INSERT OR REPLACE INTO daily_metrics
                        (content_id, date, views, likes, comments, shares, favorites, coins)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (content_id, date, m.get('views', 0), m.get('likes', 0), m.get('comments', 0),
                         m.get('shares', 0), m.get('favorites', 0), m.get('coins', 0)))
            imported += 1

        conn.commit()
        conn.close()

        return {"success": True, "imported": imported}

    @app.put("/api/content/{content_id}/metrics")
    async def content_update_metrics(content_id: int, request: dict):
        """更新内容的指标数据"""
        import sqlite3
        from datetime import datetime
        init_content_db()

        now = datetime.now().isoformat()
        date = request.get('date', now[:10])
        m = request.get('metrics', {})

        conn = sqlite3.connect(CONTENT_DB_PATH)
        cur = conn.cursor()

        # 检查当天是否已有数据
        cur.execute("SELECT id FROM daily_metrics WHERE content_id = ? AND date = ?", (content_id, date))
        existing = cur.fetchone()

        if existing:
            cur.execute("""UPDATE daily_metrics SET views = ?, likes = ?, comments = ?, shares = ?, favorites = ?, coins = ?
                        WHERE content_id = ? AND date = ?""",
                        (m.get('views', 0), m.get('likes', 0), m.get('comments', 0),
                         m.get('shares', 0), m.get('favorites', 0), m.get('coins', 0), content_id, date))
        else:
            cur.execute("""INSERT INTO daily_metrics (content_id, date, views, likes, comments, shares, favorites, coins)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (content_id, date, m.get('views', 0), m.get('likes', 0), m.get('comments', 0),
                         m.get('shares', 0), m.get('favorites', 0), m.get('coins', 0)))

        conn.commit()
        conn.close()

        return {"success": True}

    @app.get("/api/content/{content_id}/metrics")
    async def content_get_metrics(content_id: int):
        """获取内容的指标历史"""
        import sqlite3
        init_content_db()

        conn = sqlite3.connect(CONTENT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM daily_metrics WHERE content_id = ? ORDER BY date DESC", (content_id,))
        rows = cur.fetchall()
        conn.close()

        return [
            {
                "id": row['id'],
                "date": row['date'],
                "views": row['views'],
                "likes": row['likes'],
                "comments": row['comments'],
                "shares": row['shares'],
                "favorites": row['favorites'],
                "coins": row['coins']
            }
            for row in rows
        ]

    @app.delete("/api/content/{content_id}")
    async def content_delete(content_id: int):
        """删除内容"""
        import sqlite3
        from datetime import datetime

        init_content_db()
        now = datetime.now().isoformat()

        conn = sqlite3.connect(CONTENT_DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE contents SET deleted_time = ? WHERE id = ?", (now, content_id))
        conn.commit()
        conn.close()

        return {"success": True}

    @app.get("/api/content/trend")
    async def content_trend(platform: str = None, metric: str = "views", days: int = 30):
        """获取趋势数据（用于折线图）"""
        import sqlite3
        from datetime import datetime, timedelta
        init_content_db()

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        conn = sqlite3.connect(CONTENT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        if platform:
            # 获取该平台下所有内容的每日指标汇总
            cur.execute("""
                SELECT dm.date,
                       SUM(dm.views) as views,
                       SUM(dm.likes) as likes,
                       SUM(dm.comments) as comments,
                       SUM(dm.shares) as shares,
                       SUM(dm.favorites) as favorites,
                       SUM(dm.coins) as coins
                FROM daily_metrics dm
                JOIN contents c ON dm.content_id = c.id
                WHERE c.platform = ? AND dm.date >= ? AND dm.date <= ?
                GROUP BY dm.date
                ORDER BY dm.date
            """, (platform, start_date, end_date))
        else:
            # 获取所有平台的汇总
            cur.execute("""
                SELECT c.platform, dm.date,
                       SUM(dm.views) as views,
                       SUM(dm.likes) as likes,
                       SUM(dm.comments) as comments,
                       SUM(dm.shares) as shares,
                       SUM(dm.favorites) as favorites,
                       SUM(dm.coins) as coins
                FROM daily_metrics dm
                JOIN contents c ON dm.content_id = c.id
                WHERE dm.date >= ? AND dm.date <= ?
                GROUP BY c.platform, dm.date
                ORDER BY dm.date
            """, (start_date, end_date))

        rows = cur.fetchall()
        conn.close()

        if platform:
            # 返回单个平台的趋势
            return {
                "platform": platform,
                "metric": metric,
                "data": [{"date": row['date'], "value": row[metric] or 0} for row in rows]
            }
        else:
            # 返回所有平台按日期分组的趋势
            trend = {}
            for row in rows:
                p = row['platform']
                if p not in trend:
                    trend[p] = []
                trend[p].append({
                    "date": row['date'],
                    "views": row['views'] or 0,
                    "likes": row['likes'] or 0,
                    "comments": row['comments'] or 0,
                    "shares": row['shares'] or 0,
                    "favorites": row['favorites'] or 0,
                    "coins": row['coins'] or 0
                })
            return trend

    @app.get("/api/content/account")
    async def content_account(platform: str = None):
        """获取账号整体数据"""
        import sqlite3
        from datetime import datetime, timedelta
        init_content_db()

        # 默认查最近30天
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        conn = sqlite3.connect(CONTENT_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        if platform:
            cur.execute("""SELECT * FROM account_metrics
                          WHERE platform = ? AND date >= ? AND date <= ?
                          ORDER BY date DESC""", (platform, start_date, end_date))
        else:
            cur.execute("""SELECT * FROM account_metrics
                          WHERE date >= ? AND date <= ?
                          ORDER BY date DESC""", (start_date, end_date))

        rows = cur.fetchall()
        conn.close()

        return [
            {
                "id": row['id'],
                "platform": row['platform'],
                "date": row['date'],
                "followers": row['followers']
            }
            for row in rows
        ]

    @app.post("/api/content/account")
    async def content_account_update(request: dict):
        """更新账号整体粉丝数据"""
        import sqlite3
        from datetime import datetime
        init_content_db()

        now = datetime.now().isoformat()
        date = request.get('date', now[:10])

        conn = sqlite3.connect(CONTENT_DB_PATH)
        cur = conn.cursor()

        cur.execute("""INSERT OR REPLACE INTO account_metrics (platform, date, followers, created_time)
                        VALUES (?, ?, ?, ?)""",
                    (request.get('platform'), date, request.get('followers', 0), now))
        conn.commit()
        conn.close()

        return {"success": True}

    # ========== 微信公众号 API ==========
    @app.get("/api/wechat/articles")
    async def wechat_articles(offset: int = 0, count: int = 20):
        """获取公众号文章列表"""
        import requests
        import json

        app_id, app_secret = get_wechat_credentials()

        if not app_id or not app_secret:
            return {"error": "未配置微信公众号 AppID 或 AppSecret，请配置 WECHAT_APP_ID / WECHAT_APP_SECRET"}

        # 获取access_token
        token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}"
        try:
            resp = requests.get(token_url, timeout=5)
            resp.encoding = 'utf-8'
            token_data = resp.json()
            access_token = token_data.get('access_token')

            if not access_token:
                return {"error": token_data.get('errcode'), "message": token_data.get('errmsg', '获取token失败')}

            # 获取素材列表（图文素材）
            list_url = f"https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token={access_token}"
            payload = {
                "type": "news",
                "offset": offset,
                "count": count
            }
            resp2 = requests.post(list_url, json=payload, timeout=5)
            resp2.encoding = 'utf-8'
            data = resp2.json()

            if data.get('item'):
                articles = []
                for item in data['item']:
                    for article in item.get('content', {}).get('news_item', []):
                        articles.append({
                            "title": article.get('title'),
                            "author": article.get('author'),
                            "digest": article.get('digest'),
                            "content": article.get('content'),
                            "url": article.get('url'),
                            "thumb_url": article.get('thumb_url'),
                            "update_time": article.get('update_time')
                        })
                return {"articles": articles, "total_count": data.get('total_count', 0)}
            else:
                return {"articles": [], "total_count": 0}

        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/wechat/stats")
    async def wechat_stats():
        """获取公众号图文数据"""
        import requests
        import json
        from datetime import datetime, timedelta

        app_id, app_secret = get_wechat_credentials()

        if not app_id or not app_secret:
            return {"error": "未配置微信公众号 AppID 或 AppSecret，请配置 WECHAT_APP_ID / WECHAT_APP_SECRET"}

        # 获取access_token
        token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}"
        try:
            resp = requests.get(token_url, timeout=5)
            resp.encoding = 'utf-8'
            token_data = resp.json()
            access_token = token_data.get('access_token')

            if not access_token:
                return {"error": token_data.get('errcode'), "message": token_data.get('errmsg', '获取token失败')}

            # 获取用户群发数据（最近7天）
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

            stats_url = f"https://api.weixin.qq.com/datacube/getarticlesummary?access_token={access_token}"
            payload = {
                "start_date": start_date,
                "end_date": end_date
            }
            resp2 = requests.post(stats_url, json=payload, timeout=5)
            resp2.encoding = 'utf-8'
            data = resp2.json()

            return {"data": data.get('list', []), "start_date": start_date, "end_date": end_date}

        except Exception as e:
            return {"error": str(e)}

    # 微信公众号文章Webhook接收接口
    @app.post("/api/wechat/webhook")
    async def wechat_webhook(request: dict):
        """
        接收三方服务推送的微信公众号文章数据
        数据格式:
        {
          "version": "1",
          "event": "NEW_ARTICLE",
          "deliveryId": "uuid",
          "sentAt": "2026-03-26T10:00:00.000Z",
          "userId": "user_xxx",
          "accountName": "公众号名称",
          "articles": [
            {
              "id": "article_xxx",
              "title": "文章标题",
              "url": "https://mp.weixin.qq.com/...",
              "summary": "文章摘要",
              "publishDate": "2026-03-26T09:58:00.000Z",
              "coverImage": "https://..."
            }
          ]
        }
        """
        import sqlite3
        from datetime import datetime

        wechat_db = os.path.join(BASE_DIR, "data", "wechat_articles.db")
        conn = sqlite3.connect(wechat_db)
        cur = conn.cursor()

        # 创建表
        cur.execute("""CREATE TABLE IF NOT EXISTS wechat_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL,
            article_id TEXT,
            title TEXT NOT NULL,
            url TEXT,
            summary TEXT,
            publish_date TEXT,
            cover_image TEXT,
            crawl_time TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(article_id)
        )""")

        articles = request.get('articles', [])
        account_name = request.get('accountName', '')
        saved_count = 0

        for article in articles:
            article_id = article.get('id', '')
            title = article.get('title', '')
            url = article.get('url', '')
            summary = article.get('summary', '')
            publish_date = article.get('publishDate', '')
            cover_image = article.get('coverImage', '')

            # 格式化发布时间
            if publish_date:
                try:
                    dt = datetime.fromisoformat(publish_date.replace('Z', '+00:00'))
                    publish_date = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass

            # 插入或更新
            try:
                cur.execute("""INSERT OR REPLACE INTO wechat_articles
                    (account_name, article_id, title, url, summary, publish_date, cover_image)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (account_name, article_id, title, url, summary, publish_date, cover_image))
                saved_count += 1
            except Exception as e:
                print(f"保存文章失败: {e}")

        conn.commit()
        conn.close()

        return {"success": True, "saved": saved_count, "account": account_name}

    # 获取微信公众号文章列表
    @app.get("/api/wechat/articles")
    async def wechat_articles(account: str = None, limit: int = 50):
        """获取微信公众号文章列表"""
        import sqlite3

        wechat_db = os.path.join(BASE_DIR, "data", "wechat_articles.db")

        if not os.path.exists(wechat_db):
            return []

        conn = sqlite3.connect(wechat_db)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        if account:
            cur.execute("""SELECT * FROM wechat_articles WHERE account_name = ?
                ORDER BY publish_date DESC LIMIT ?""", (account, limit))
        else:
            cur.execute("""SELECT * FROM wechat_articles
                ORDER BY publish_date DESC LIMIT ?""", (limit,))

        rows = cur.fetchall()
        conn.close()

        return [
            {
                "id": row['id'],
                "account_name": row['account_name'],
                "title": row['title'],
                "url": row['url'],
                "summary": row['summary'],
                "publish_date": row['publish_date'],
                "cover_image": row['cover_image']
            }
            for row in rows
        ]

    # 从数据库读取微信文章列表的简单API
    @app.get("/api/wechat/list")
    async def wechat_list():
        import sqlite3

        wechat_db = os.path.join(BASE_DIR, "data", "wechat_articles.db")
        if not os.path.exists(wechat_db):
            return []

        conn = sqlite3.connect(wechat_db)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""SELECT * FROM wechat_articles ORDER BY publish_date DESC LIMIT 20""")
        rows = cur.fetchall()
        conn.close()

        return [
            {
                "id": row['id'],
                "account_name": row['account_name'],
                "title": row['title'],
                "url": row['url'],
                "summary": row['summary'],
                "publish_date": row['publish_date'],
                "cover_image": row['cover_image']
            }
            for row in rows
        ]

    return app

app = create_app()
