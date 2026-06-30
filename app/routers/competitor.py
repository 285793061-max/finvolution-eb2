from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import sqlite3
import os
from datetime import datetime

router = APIRouter(prefix="/api/competitor", tags=["competitor_research"])

# 获取项目根目录 (routers -> app -> project -> data)
# competitor.py 在 app/routers/competitor.py
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "competitor_recruit.db")


def init_db():
    """初始化竞品招聘数据库"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 竞品公司表
    cur.execute("""CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        industry TEXT,
        description TEXT,
        created_time TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # 职位表
    cur.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        title TEXT NOT NULL,
        salary TEXT,
        location TEXT,
        experience TEXT,
        education TEXT,
        job_type TEXT,
        tags TEXT,
        source TEXT,
        url TEXT,
        publish_time TEXT,
        crawl_time TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )""")

    # 薪资统计表
    cur.execute("""CREATE TABLE IF NOT EXISTS salary_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        title TEXT,
        salary_avg TEXT,
        salary_range TEXT,
        updated_time TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES companies(id)
    )""")

    conn.commit()
    conn.close()


init_db()


class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=1, description="公司名称")
    industry: Optional[str] = Field(None, description="行业")
    description: Optional[str] = Field(None, description="描述")


class JobCreate(BaseModel):
    company_id: int
    title: str = Field(..., min_length=1, description="职位名称")
    salary: Optional[str] = Field(None, description="薪资")
    location: Optional[str] = Field(None, description="工作地点")
    experience: Optional[str] = Field(None, description="经验要求")
    education: Optional[str] = Field(None, description="学历要求")
    job_type: Optional[str] = Field(None, description="工作类型")
    tags: Optional[str] = Field(None, description="标签，逗号分隔")
    source: Optional[str] = Field("manual", description="来源")
    url: Optional[str] = Field(None, description="职位链接")
    publish_time: Optional[str] = Field(None, description="发布时间")


class CompanyResponse(BaseModel):
    id: int
    name: str
    industry: Optional[str]
    description: Optional[str]
    created_time: Optional[str]
    job_count: Optional[int] = 0


class JobResponse(BaseModel):
    id: int
    company_id: int
    company_name: Optional[str] = None
    title: str
    salary: Optional[str]
    location: Optional[str]
    experience: Optional[str]
    education: Optional[str]
    job_type: Optional[str]
    tags: Optional[str]
    source: Optional[str]
    url: Optional[str]
    publish_time: Optional[str]
    crawl_time: Optional[str]


class SalaryStatsResponse(BaseModel):
    company_id: int
    company_name: str
    title: str
    salary_avg: Optional[str]
    salary_range: Optional[str]
    count: int


@router.get("/companies")
async def list_companies():
    """获取所有竞品公司列表"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT c.*, COUNT(j.id) as job_count
        FROM companies c
        LEFT JOIN jobs j ON c.id = j.company_id
        GROUP BY c.id
        ORDER BY c.created_time DESC
    """)
    rows = cur.fetchall()
    conn.close()

    return [dict(r) for r in rows]


@router.post("/companies")
async def create_company(req: CompanyCreate):
    """添加竞品公司"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO companies (name, industry, description) VALUES (?, ?, ?)",
            (req.name, req.industry, req.description)
        )
        conn.commit()
        company_id = cur.lastrowid
        conn.close()
        return {"success": True, "id": company_id, "message": f"公司 {req.name} 添加成功"}
    except sqlite3.IntegrityError:
        conn.close()
        return {"success": False, "error": f"公司 {req.name} 已存在"}


@router.delete("/companies/{company_id}")
async def delete_company(company_id: int):
    """删除竞品公司"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DELETE FROM jobs WHERE company_id = ?", (company_id,))
    cur.execute("DELETE FROM companies WHERE id = ?", (company_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "删除成功"}


@router.get("/jobs")
async def list_jobs(company_id: int = None, keyword: str = None, limit: int = 100):
    """获取职位列表"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = """
        SELECT j.*, c.name as company_name
        FROM jobs j
        LEFT JOIN companies c ON j.company_id = c.id
        WHERE 1=1
    """
    params = []

    if company_id:
        query += " AND j.company_id = ?"
        params.append(company_id)

    if keyword:
        query += " AND (j.title LIKE ? OR c.name LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    query += " ORDER BY j.crawl_time DESC LIMIT ?"
    params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    return [dict(r) for r in rows]


@router.post("/jobs")
async def create_job(req: JobCreate):
    """添加职位"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO jobs (company_id, title, salary, location, experience, education, job_type, tags, source, url, publish_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            req.company_id, req.title, req.salary, req.location,
            req.experience, req.education, req.job_type, req.tags,
            req.source, req.url, req.publish_time
        ))
        conn.commit()
        job_id = cur.lastrowid
        conn.close()
        return {"success": True, "id": job_id}
    except Exception as e:
        conn.close()
        return {"success": False, "error": str(e)}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: int):
    """删除职位"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
    return {"success": True}


@router.get("/salary-stats")
async def salary_stats():
    """按公司和职位统计薪资"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT
            j.company_id,
            c.name as company_name,
            j.title,
            COUNT(*) as count,
            AVG(
                CASE
                    WHEN salary LIKE '%-%' THEN
                        (CAST(replace(replace(substr(salary, instr(salary, '-')+1, 4), 'k', ''), 'K', '') as INTEGER) +
                         CAST(substr(salary, 2, instr(salary, '-')-2) as INTEGER)) / 2 * 1000
                    WHEN salary LIKE '%K' OR salary LIKE '%k' THEN
                        CAST(replace(replace(salary, 'K', ''), 'k', '') as INTEGER) * 1000
                    ELSE NULL
                END
            ) as salary_avg_num,
            MIN(salary) as salary_min,
            MAX(salary) as salary_max
        FROM jobs j
        LEFT JOIN companies c ON j.company_id = c.id
        WHERE j.salary IS NOT NULL AND j.salary != ''
        GROUP BY j.company_id, j.title
        ORDER BY count DESC, salary_avg_num DESC
    """)

    rows = cur.fetchall()
    conn.close()

    result = []
    for r in rows:
        row = dict(r)
        if row.get('salary_avg_num'):
            row['salary_avg'] = f"{int(row['salary_avg_num']/1000)}K"
        else:
            row['salary_avg'] = None
        row['salary_range'] = f"{row.get('salary_min', 'N/A')} - {row.get('salary_max', 'N/A')}"
        result.append(row)

    return result


@router.get("/comparison")
async def comparison():
    """竞品对比分析"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT
            c.id,
            c.name,
            c.industry,
            COUNT(j.id) as job_count,
            COUNT(DISTINCT j.title) as position_types,
            SUM(CASE WHEN j.salary IS NOT NULL AND j.salary != '' THEN 1 ELSE 0 END) as job_with_salary,
            MAX(j.crawl_time) as last_update
        FROM companies c
        LEFT JOIN jobs j ON c.id = j.company_id
        GROUP BY c.id
        ORDER BY job_count DESC
    """)

    rows = cur.fetchall()
    conn.close()

    return [dict(r) for r in rows]


@router.get("/export")
async def export_data():
    """导出数据用于分析"""
    companies = await list_companies()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT j.*, c.name as company_name
        FROM jobs j
        LEFT JOIN companies c ON j.company_id = c.id
        ORDER BY c.name, j.title
    """)
    jobs = [dict(r) for r in cur.fetchall()]
    conn.close()

    salary = await salary_stats()

    return {
        "companies": companies,
        "jobs": jobs,
        "salary_stats": salary,
        "export_time": datetime.now().isoformat()
    }