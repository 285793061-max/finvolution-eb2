from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import random
import os
import subprocess
import json
import asyncio
import httpx
from datetime import datetime

router = APIRouter(prefix="/api/generate", tags=["content_gen"])

# 即梦 CLI 路径
DREAMINA_BIN = os.path.expanduser("~/.local/bin/dreamina")

# 文字生成 API (Anthropic/OpenAI 兼容接口)
# 本地原型默认使用模板生成；配置密钥后再调用外部模型。
OPENAI_API_KEY = os.getenv("MINIMAX_API_KEY") or os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("MINIMAX_API_BASE", "https://api.minimaxi.com/anthropic/v1")
OPENAI_MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M2.7")

# 内容类型枚举
CONTENT_TYPES = {
    "social": "社交媒体帖子",
    "job_desc": "招聘JD",
    "company_intro": "公司简介",
    "recruit_notice": "招聘公告",
    "employer_brand": "雇主品牌文案"
}

# 风格选项
STYLE_OPTIONS = {
    "professional": "专业严肃",
    "friendly": "亲切友好",
    "trendy": "年轻潮流",
    "warm": "温暖感人",
    "humor": "幽默风趣"
}

# 平台选项
PLATFORM_OPTIONS = {
    "xiaohongshu": "小红书",
    "weibo": "微博",
    "wechat": "微信公众号",
    "linkedin": "领英",
    "douyin": "抖音"
}


class GenerateRequest(BaseModel):
    content_type: str = Field(..., description="内容类型: social, job_desc, company_intro, recruit_notice, employer_brand")
    keyword: str = Field(..., min_length=1, description="关键词/公司名称")
    platform: Optional[str] = Field(None, description="目标平台")
    style: Optional[str] = Field(None, description="风格: professional, friendly, trendy, warm, humor")
    tone: Optional[str] = Field(None, description="语气: formal, casual, persuasive")
    length: Optional[str] = Field("medium", description="长度: short, medium, long")
    extra_requirements: Optional[str] = Field(None, description="额外要求")


class ImageGenerateRequest(BaseModel):
    prompt: str = Field(..., description="图片生成提示词")
    ratio: Optional[str] = Field("1:1", description="图片比例: 21:9, 16:9, 3:2, 4:3, 1:1, 3:4, 2:3, 9:16")
    model_version: Optional[str] = Field("3.0", description="模型版本: 3.0, 3.1, 4.0, 4.1, 4.5, 4.6, 5.0")
    resolution_type: Optional[str] = Field("2k", description="分辨率: 1k, 2k, 4k")
    session: Optional[int] = Field(0, description="会话ID")


class VideoGenerateRequest(BaseModel):
    prompt: str = Field(..., description="视频生成提示词")
    duration: Optional[int] = Field(5, description="视频时长(秒): 4-15")
    ratio: Optional[str] = Field("16:9", description="视频比例: 1:1, 3:4, 16:9, 4:3, 9:16, 21:9")
    model_version: Optional[str] = Field("seedance2.0fast", description="模型: seedance2.0, seedance2.0fast, seedance2.0_vip, seedance2.0fast_vip")
    session: Optional[int] = Field(0, description="会话ID")


class GenerateResponse(BaseModel):
    success: bool
    content: Optional[str] = None
    title: Optional[str] = None
    suggestions: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    error: Optional[str] = None


class ImageGenerateResponse(BaseModel):
    success: bool
    submit_id: Optional[str] = None
    gen_status: Optional[str] = None
    image_url: Optional[str] = None
    images: Optional[List[str]] = None
    error: Optional[str] = None


class VideoGenerateResponse(BaseModel):
    success: bool
    submit_id: Optional[str] = None
    gen_status: Optional[str] = None
    video_url: Optional[str] = None
    error: Optional[str] = None


class CreditResponse(BaseModel):
    success: bool
    logged_in: bool
    credit: Optional[str] = None
    error: Optional[str] = None


# 模板数据
TEMPLATES = {
    "social": {
        "professional": [
            "{keyword}诚邀英才，共创未来。我们提供有竞争力的薪酬福利和广阔的发展空间，期待优秀人才加入！",
            "加入{keyword}，开启职业新篇章。我们重视员工成长，提供专业培训和晋升通道。",
            "{keyword}正在招聘中，众多岗位虚位以待。欢迎投递简历，与我们一同成长。"
        ],
        "friendly": [
            "嗨~ {keyword}招人啦！如果你正在找机会，不妨来看看呀～ 氛围超棒，团队有爱！",
            "{keyword}的小哥哥小姐姐们都在等你哦！扁平管理，弹性工作，来当同事吧～",
            "救命！这个公司也太香了吧！{keyword}招聘进行中，福利待遇没话说！"
        ],
        "trendy": [
            "救命！{keyword}又在搞事情！招聘帖直接爆了，00后团队太会玩了！",
            "{keyword}校招开启！Z世代集合，玩转职场就在此刻！",
            "{keyword} × 潮酷办公 = yyds！加入我们一起卷起来！（不是"
        ],
        "warm": [
            "{keyword}相信，每个人都值得被看见。这里有温度，有归属，有家一般的感觉。",
            "在{keyword}，你不只是员工，更是家人。我们一起创造价值，一起收获成长。",
            "每一次选择，都是为了遇见更好的自己。{keyword}，期待与你同行。"
        ],
        "humor": [
            "{keyword}招聘啦！虽然不能保证让你走上人生巅峰，但至少能让你走上工位巅峰！",
            "招人了招人了！{keyword}HR已上线，快把简历砸过来！（认真脸",
            "{keyword}招聘 | 听说你来就不走了？（其实是高薪+零食管够）"
        ]
    },
    "job_desc": {
        "professional": [
            "【{keyword}招聘】职位名称：{keyword}精英团队\n职位描述：负责公司核心业务发展，协作能力强，有行业经验优先。\n福利待遇：五险一金、年终奖、定期体检、弹性工作制。",
            "【{keyword}社会招聘】\n岗位职责：\n1. 主导项目推进，确保目标达成\n2. 跨部门协作，解决复杂问题\n3. 带团队，培养新人\n任职要求：本科及以上学历，3年以上相关经验",
            "【{keyword}诚聘】\n我们寻找：具有Owner意识、数据驱动、善于复盘反思的你。\n加入我们，你将获得：成长型思维、有竞争力的薪酬、清晰的晋升通道。"
        ],
        "friendly": [
            "招人招人！{keyword}团队等你加入~\n做什么：负责核心产品迭代\n要求：会写代码、会沟通、会上班（bushi\n福利：零食下午茶、节日礼物、打平rank~",
            "{keyword}招聘啦！不需要你特别特别厉害，但希望你爱学习、爱沟通、爱吐槽（划掉）\n扁平管理，氛围轻松，等你来聊！",
            "【急招】{keyword}小分队招募新成员！\n我们想要：会做事的、会思考的、会摸鱼的（不是\n福利：免费三餐、弹性打卡、撸猫自由！"
        ]
    },
    "company_intro": {
        "professional": [
            "{keyword}成立于20XX年，是一家专注于XX领域的创新型科技公司。公司以'XX'为使命，致力于为客户提供优质的产品和服务。\n目前公司规模XX人，已完成X轮融资。",
            "{keyword}是一家注重技术创新和人才培养的高新技术企业。我们相信，优秀的团队是公司最宝贵的财富。\n加入我们，一起创造更大的价值！",
            "关于{keyword}：\n我们是国内领先的XX服务提供商，产品服务覆盖XX万用户。\n公司文化：创新、协作、务实、进取。\n期待志同道合的你加入！"
        ],
        "friendly": [
            "嗨~向你介绍一下{keyword}！\n我们是一家有点不一样的公司，工作氛围轻松，团队氛围超好，老板nice，同事有爱！\n成立以来，已经服务了XX万用户啦～",
            "来认识一下{keyword}吧！\n我们是一支年轻的团队，用心做产品，用爱做服务。\n如果你也想和我们一起搞事情，就快来加入吧！",
            "{keyword}是一个温馨的大家庭~这里有零食、有下午茶、有撸猫自由（真的！\n更重要的是，有一群志同道合的伙伴，一起成长一起浪！"
        ]
    }
}


def run_dreamina(args: List[str], timeout: int = 120) -> dict:
    """运行即梦CLI命令"""
    env = os.environ.copy()
    # 确保 PATH 包含 dreamina 所在目录，但也要保留原有 PATH
    dreamina_dir = os.path.dirname(DREAMINA_BIN)
    env["PATH"] = f"{dreamina_dir}:{env.get('PATH', '')}"

    try:
        result = subprocess.run(
            [DREAMINA_BIN] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env
        )

        output = result.stdout.strip()
        stderr = result.stderr.strip()
        if result.returncode != 0 and not output:
            output = stderr

        # 如果命令返回1但没有任何输出，可能是需要交互式确认
        if result.returncode == 1 and not output:
            # 尝试获取终端输出
            return {"error": "命令执行失败，可能是需要先在网页端授权", "returncode": 1, "raw_output": ""}

        # 尝试解析JSON输出
        if output:
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                # 解析纯文本格式输出（如 login 命令的输出）
                parsed = {}
                for line in output.split('\n'):
                    if ':' in line:
                        key, val = line.split(':', 1)
                        parsed[key.strip()] = val.strip()
                if parsed:
                    return {**parsed, "returncode": result.returncode}
                return {"raw_output": output, "returncode": result.returncode}
        return {"returncode": result.returncode}

    except subprocess.TimeoutExpired:
        return {"error": "命令执行超时", "returncode": -1}
    except FileNotFoundError:
        return {"error": f"未找到 dreamina CLI，请确认已安装: {DREAMINA_BIN}", "returncode": -1}
    except Exception as e:
        return {"error": str(e), "returncode": -1}


def check_login_status() -> bool:
    """检查登录状态"""
    result = run_dreamina(["user_credit"], timeout=10)
    # 如果有 total_credit 或 user_id，说明已登录
    if "total_credit" in result or "user_id" in result:
        return True
    # 或者 returncode 为 0 且有 credit 信息
    if result.get("returncode") == 0 and ("credit" in result or "可用" in result.get("raw_output", "")):
        return True
    return False


def generate_text_content(req: GenerateRequest) -> dict:
    """根据请求参数生成文本内容"""
    content_type = req.content_type
    keyword = req.keyword
    style = req.style or "professional"
    length = req.length or "medium"

    # 获取模板
    templates = TEMPLATES.get(content_type, TEMPLATES["social"])
    style_templates = templates.get(style, templates["professional"])

    # 根据长度选择模板
    if content_type == "job_desc":
        selected = style_templates[1] if len(style_templates) > 1 else style_templates[0]
    elif content_type == "company_intro":
        selected = style_templates[0]
    else:
        selected = random.choice(style_templates)

    # 填充内容
    content = selected.format(keyword=keyword)

    # 生成标题
    titles = {
        "social": f"加入{keyword}，一起搞事情",
        "job_desc": f"{keyword}热招中",
        "company_intro": f"关于{keyword}",
        "recruit_notice": f"{keyword}招聘公告",
        "employer_brand": f"{keyword}雇主品牌"
    }
    title = titles.get(content_type, f"{keyword}内容生成")

    # 生成标签
    all_tags = ["雇主品牌", "招聘", "职场", "成长", "发展", "福利", "团队", "文化"]
    tags = random.sample(all_tags, min(4, len(all_tags)))

    # 生成建议
    suggestions = [
        "建议搭配相关图片发布，效果更好",
        f"发布到{PLATFORM_OPTIONS.get(req.platform, '目标平台')}效果更佳",
        "可以在评论区与用户互动，提高参与度",
        "建议添加公司主页链接，方便求职者了解更多"
    ]

    return {
        "success": True,
        "content": content,
        "title": title,
        "suggestions": suggestions[:3],
        "tags": tags
    }


@router.post("/", response_model=GenerateResponse)
async def generate(req: GenerateRequest) -> GenerateResponse:
    """生成雇主品牌文本内容"""
    if req.content_type not in CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的内容类型。可选: {list(CONTENT_TYPES.keys())}")

    if req.style and req.style not in STYLE_OPTIONS:
        raise HTTPException(status_code=400, detail=f"不支持的风格。可选: {list(STYLE_OPTIONS.keys())}")

    try:
        if not OPENAI_API_KEY:
            result = generate_text_content(req)
            return GenerateResponse(**result)

        # 构建提示词
        content_type_name = CONTENT_TYPES.get(req.content_type, "内容")
        style_name = STYLE_OPTIONS.get(req.style or "professional", "专业")
        platform_name = PLATFORM_OPTIONS.get(req.platform, "") if req.platform else ""

        prompt = f"""你是一个专业的雇主品牌文案专家。请为{req.keyword}生成一条{style_name}风格的{content_type_name}。
关键词: {req.keyword}
风格: {style_name}
长度: {req.length}
{f"目标平台: {platform_name}" if platform_name else ""}
{f"额外要求: {req.extra_requirements}" if req.extra_requirements else ""}

请直接输出文案内容，不要解释。"""

        # 调用 AI API (Anthropic Claude 兼容)
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OPENAI_API_BASE}/messages",
                headers={
                    "x-api-key": OPENAI_API_KEY,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": OPENAI_MODEL,
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )

            if response.status_code == 200:
                data = response.json()
                # 从 content 数组中提取 text 类型的内容
                content = ""
                for item in data.get("content", []):
                    if item.get("type") == "text":
                        content = item.get("text", "")
                        break

                # 生成标题
                titles = {
                    "social": f"加入{req.keyword}，一起搞事情",
                    "job_desc": f"{req.keyword}热招中",
                    "company_intro": f"关于{req.keyword}",
                    "recruit_notice": f"{req.keyword}招聘公告",
                    "employer_brand": f"{req.keyword}雇主品牌"
                }

                # 生成标签
                all_tags = ["雇主品牌", "招聘", "职场", "成长", "发展", "福利", "团队", "文化"]
                tags = random.sample(all_tags, min(4, len(all_tags)))

                # 生成建议
                suggestions = [
                    "建议搭配相关图片发布，效果更好",
                    f"发布到{PLATFORM_OPTIONS.get(req.platform, '目标平台')}效果更佳" if req.platform else "选择合适的平台发布效果更佳",
                    "可以在评论区与用户互动，提高参与度",
                    "建议添加公司主页链接，方便求职者了解更多"
                ]

                return GenerateResponse(
                    success=True,
                    content=content.strip(),
                    title=titles.get(req.content_type, f"{req.keyword}内容生成"),
                    suggestions=suggestions[:3],
                    tags=tags
                )
            else:
                # 如果 API 调用失败，回退到模板
                result = generate_text_content(req)
                return GenerateResponse(**result)

    except Exception as e:
        # 发生错误时回退到模板
        try:
            result = generate_text_content(req)
            return GenerateResponse(**result)
        except:
            return GenerateResponse(success=False, error=str(e))


@router.post("/image", response_model=ImageGenerateResponse)
async def generate_image(req: ImageGenerateRequest) -> ImageGenerateResponse:
    """生成图片（使用即梦AI）"""
    # 检查登录状态
    if not check_login_status():
        return ImageGenerateResponse(
            success=False,
            error="未登录即梦，请先运行 'dreamina login' 命令登录"
        )

    # 构建命令
    args = [
        "text2image",
        "--prompt", req.prompt,
        "--ratio", req.ratio or "1:1",
        "--resolution_type", req.resolution_type or "2k",
        "--model_version", req.model_version or "3.0",
        "--poll", "60"  # 轮询60秒
    ]

    if req.session:
        args.extend(["--session", str(req.session)])

    result = run_dreamina(args, timeout=120)

    # 检查是否提交成功
    if "submit_id" in result and result.get("gen_status") in ["querying", "success"]:
        return ImageGenerateResponse(
            success=True,
            submit_id=result.get("submit_id"),
            gen_status=result.get("gen_status"),
            images=result.get("images", [])
        )

    # 如果是成功状态，提取图片URL
    if result.get("gen_status") == "success" and "image_url" in result:
        return ImageGenerateResponse(
            success=True,
            submit_id=result.get("submit_id"),
            gen_status="success",
            image_url=result.get("image_url")
        )

    return ImageGenerateResponse(
        success=False,
        error=result.get("error") or result.get("fail_reason") or "图片生成失败"
    )


@router.post("/video", response_model=VideoGenerateResponse)
async def generate_video(req: VideoGenerateRequest) -> VideoGenerateResponse:
    """生成视频（使用即梦AI）"""
    # 检查登录状态
    if not check_login_status():
        return VideoGenerateResponse(
            success=False,
            error="未登录即梦，请先运行 'dreamina login' 命令登录"
        )

    # 构建命令
    args = [
        "text2video",
        "--prompt", req.prompt,
        "--duration", str(req.duration or 5),
        "--ratio", req.ratio or "16:9",
        "--model_version", req.model_version or "seedance2.0fast",
        "--poll", "120"  # 视频生成需要更长时间
    ]

    if req.session:
        args.extend(["--session", str(req.session)])

    result = run_dreamina(args, timeout=180)

    # 检查是否提交成功
    if "submit_id" in result and result.get("gen_status") in ["querying", "success"]:
        return VideoGenerateResponse(
            success=True,
            submit_id=result.get("submit_id"),
            gen_status=result.get("gen_status")
        )

    return VideoGenerateResponse(
        success=False,
        error=result.get("error") or result.get("fail_reason") or "视频生成失败"
    )


@router.get("/query/{submit_id}", response_model=ImageGenerateResponse)
async def query_result(submit_id: str) -> ImageGenerateResponse:
    """查询生成结果"""
    result = run_dreamina(["query_result", "--submit_id", submit_id], timeout=30)

    if "gen_status" in result:
        return ImageGenerateResponse(
            success=True,
            submit_id=submit_id,
            gen_status=result.get("gen_status"),
            image_url=result.get("image_url"),
            video_url=result.get("video_url"),
            images=result.get("images")
        )

    return ImageGenerateResponse(
        success=False,
        error=result.get("error") or "查询失败"
    )


@router.get("/credit", response_model=CreditResponse)
async def get_credit() -> CreditResponse:
    """获取即梦账号积分"""
    result = run_dreamina(["user_credit"], timeout=10)

    # 如果返回成功且有 total_credit 或 user_id，说明已登录
    if result.get("returncode") == 0:
        if "total_credit" in result or "user_id" in result:
            credit_str = f"可用积分: {result.get('total_credit', 'N/A')}"
            return CreditResponse(
                success=True,
                logged_in=True,
                credit=credit_str
            )

    # 如果返回未检测到登录态，说明未登录
    raw = result.get("raw_output", "")
    if "未检测到有效登录态" in raw or "请先执行 dreamina login" in raw:
        return CreditResponse(success=True, logged_in=False, credit=None)

    # 其他情况检查是否有登录态
    logged_in = check_login_status()
    return CreditResponse(
        success=True,
        logged_in=logged_in,
        credit=None if not logged_in else str(result)
    )


@router.get("/checklogin/{device_code}")
async def check_dreamina_login(device_code: str) -> dict:
    """检查即梦登录状态（轮询设备码确认）"""
    result = run_dreamina(["login", "checklogin", "--device_code=" + device_code, "--poll=5"], timeout=15)

    # 如果返回成功或有credit信息，说明已登录
    if result.get("returncode") == 0:
        return {"logged_in": True, "success": True}
    if "credit" in result or "可用" in result.get("raw_output", ""):
        return {"logged_in": True, "success": True}

    return {"logged_in": False, "success": False, "raw": result}


@router.get("/login")
async def get_login_info():
    """获取即梦登录信息"""
    result = run_dreamina(["login", "--headless"], timeout=10)
    return result


@router.get("/tasks")
async def list_tasks(limit: int = 20):
    """列出最近的任务"""
    result = run_dreamina(["list_task", f"--limit={limit}"], timeout=30)
    return result


@router.get("/types")
async def get_content_types():
    """获取支持的内容类型"""
    return {"types": CONTENT_TYPES}


@router.get("/styles")
async def get_styles():
    """获取支持的风格"""
    return {"styles": STYLE_OPTIONS}


@router.get("/platforms")
async def get_platforms():
    """获取支持的平台"""
    return {"platforms": PLATFORM_OPTIONS}


@router.get("/image/models")
async def get_image_models():
    """获取支持的图片模型"""
    return {
        "models": ["3.0", "3.1", "4.0", "4.1", "4.5", "4.6", "5.0"],
        "ratios": ["21:9", "16:9", "3:2", "4:3", "1:1", "3:4", "2:3", "9:16"],
        "resolutions": ["1k", "2k", "4k"]
    }


@router.get("/video/models")
async def get_video_models():
    """获取支持的视频模型"""
    return {
        "models": ["seedance2.0", "seedance2.0fast", "seedance2.0_vip", "seedance2.0fast_vip"],
        "ratios": ["1:1", "3:4", "16:9", "4:3", "9:16", "21:9"],
        "durations": [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        "resolutions": ["720p", "1080p"]
    }
