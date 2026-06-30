# Employer Sentiment MVP

基于 Python + FastAPI 的雇主品牌舆情检测 MVP，使用本地示例数据 + 规则/词典实现中文情感分析与维度标签。

## 安装依赖

推荐使用项目内虚拟环境（避免写入系统目录权限问题）。

在项目根目录（`employer_sentiment_mvp/`）执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

## 启动服务

```bash
.venv/bin/uvicorn app.main:app --reload
```

默认监听 `http://127.0.0.1:8000`。

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

## 调用分析接口

`POST /analyze`

示例：

```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{"keyword": "某某科技", "limit": 10}'
```

返回内容包含：

- items：每条文本的情感标签、得分和维度标签
- summary.overall：整体情感分布及占比
- summary.by_dimension：按维度（如薪资、加班、管理等）的情感分布
- summary.reputation_score：简单“雇主品牌口碑指数”（0–100）

## 小红书“准实时”数据接入（阶段 C 思路）

当前项目对小红书的支持方式：

- `app/services/xiaohongshu_adapter.py`：从本地 `data/xiaohongshu_latest.json` 读取最新小红书数据
- `app/services/collector.py`：优先使用 `xiaohongshu_latest.json`，没有时再退回示例数据
- `scripts/xhs_human_collect.py`：**真人模拟采集脚本**（你先登录网页端），自动搜索/滚动并通过 OCR/DOM 抽取文本，写入 `data/xiaohongshu_latest.json`
- `scripts/fetch_xiaohongshu_example.py`：旧的 HTTP 请求骨架示例（当前不作为推荐方案）

典型使用流程：

1. 通过“真人模拟采集脚本”生成 `data/xiaohongshu_latest.json`
2. 启动本服务：`.venv/bin/uvicorn app.main:app --reload`
3. 调用 `POST /analyze`，系统会优先使用 `xiaohongshu_latest.json` 中的数据进行分析

## 小红书真人模拟采集（推荐）

### macOS 权限（必看）

`pyautogui` 需要系统权限才能控制鼠标键盘和截图：

- 系统设置 → 隐私与安全性 → **辅助功能**：给你的终端（Terminal/iTerm）或运行 Python 的 App 授权
- 系统设置 → 隐私与安全性 → **屏幕录制**：同样授予

如果不授权，脚本可能无法截图/无法控制键盘鼠标。

### OCR 模式（默认）

你手动打开浏览器并登录小红书网页端，然后运行：

```bash
.venv/bin/python scripts/xhs_human_collect.py --keyword "某某科技" --extractor ocr --calibrate
```

说明：

- `--calibrate` 会让你用鼠标指定一次“搜索结果列表区域”的截图范围，并保存到 `data/xhs_screen_region.json`（后续可不带该参数）。
- 脚本会自动打开搜索 URL、滚动若干屏、OCR 抽取文本并写入 `data/xiaohongshu_latest.json`。

常用参数：

```bash
.venv/bin/python scripts/xhs_human_collect.py --keyword "某某科技" --limit 50 --pages 10 --scroll-pause 2.5
```

### DOM 模式（可选，实验性）

DOM 模式会启动一个 Playwright 的可见浏览器窗口，并复用登录态。首次使用前需要安装浏览器运行时：

```bash
.venv/bin/playwright install chromium
```

运行：

```bash
.venv/bin/python scripts/xhs_human_collect.py --keyword "某某科技" --extractor dom
```

说明：

- 弹出浏览器后你在该窗口里手动登录一次，脚本会继续打开搜索页并从页面 DOM 中抽取文本。
- `--dom-selector` 可调整抽取范围（默认 `a`，可能会比较噪音，按实际页面情况再调）。

## 本地快速自测（不打开浏览器）

写入一份 demo 小红书数据，便于验证 `/analyze` 链路：

```bash
.venv/bin/python scripts/xhs_human_collect.py --demo --keyword "某某科技"
```


