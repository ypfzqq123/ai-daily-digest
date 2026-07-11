# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AI Daily Digest — 全自动 AI 领域每日简报生成器。从 ~12 个数据源采集资讯，通过 DeepSeek（兼容 OpenAI API）智能筛选并生成中英双语日报 + 口播稿，语音合成 MP3，构建 GitHub Pages 静态站点（含全文搜索、热词趋势、播客 RSS）。

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 本地运行完整流程（需设置环境变量 API_KEY）
cd scripts && python main.py

# 仅重新生成静态站点（不调用 AI，不抓数据）
cd scripts && python -c "from generate_site import generate_site; generate_site()"

# 手动合成当日语音（不重新抓数据/总结）
cd scripts && python -c "
from audio import generate_audio, prune_old_audio
from pathlib import Path
md = Path('../daily/2026-07-11.md').read_text(encoding='utf-8')
generate_audio(md, '2026-07-11', Path('../docs/audio'))
prune_old_audio(Path('../docs/audio'), keep=15)
"
```

## 架构与流水线

5 个脚本按顺序构成一条流水线（`main.py` → Step 1-6）：

| 步骤 | 脚本 | 职责 |
|------|------|------|
| 1. 采集 | `sources.py` | HuggingFace Papers API、arXiv、GitHub Trending 页面+OSSInsight API、Hacker News Algolia API、20+ RSS 源（含 RSSHub 多实例容错）。每条素材自动计算 `importance_hint`，按 URL/标题去重。 |
| 2. 保存 | `main.py` | 原始数据写入 `data/{date}.raw.json` |
| 3. 总结 | `summarize.py` | 单次 API 调用同时产出中英双语简报，通过 `===ENGLISH===` 分隔符切分。支持 `API_KEY` / `API_BASE_URL` / `API_MODEL` 环境变量。 |
| 4. 保存 | `main.py` | 中文写入 `daily/{date}.md`，英文写入 `daily/{date}.en.md` |
| 5. 语音 | `audio.py` | DeepSeek 将日报改写为口播稿（失败时回退到确定性脚本）→ edge-tts 合成 MP3 → 仅保留最近 15 期 |
| 6. 建站 | `generate_site.py` | 解析所有 Markdown 生成 `docs/`：首页、每日页、全文搜索索引、热词趋势、播客 RSS、小宇宙上传助手 |

**关键设计决策**：
- **双语一次生成**：`summarize.py` 的系统提示要求 AI 先输出中文，再输出 `===ENGLISH===`，然后输出英文。不发起两次 API 调用。
- **数据源容错**：RSSHub 使用多实例 fallback 列表，任何单个源失败不影响整体。
- **语音兜底**：AI 口播稿生成失败时，`_fallback_script()` 通过解析 Markdown 结构生成确定性朗读稿，保证总有音频产出。
- **无 API Key 时**：语音模块自动退回确定性脚本，站点生成不受影响。
- **GitHub Actions 触发**：主要依靠 cron-job.org 通过 `workflow_dispatch` 触发（规避 GitHub 定时任务不稳定的问题），GitHub 内置 cron 作为兜底。`keepalive.yml` 每 50 天触发一次空提交防止仓库被标记为不活跃。

## 数据流

```
RSS/REST APIs → sources.py → {category: [item, ...]} → summarize.py → (zh_md, en_md)
                                                                              │
                                                                    audio.py ← zh_md → edge-tts → MP3
                                                                              │
                                                              generate_site.py ← daily/*.md → docs/
```

每个 item 的稳定字段：`category`, `title`, `url`, `normalized_url`, `summary`, `source`, `published`, `importance_hint`, `metadata`。

## 输出结构

```
daily/{date}.md          # 中文 Markdown 日报（AI 生成）
daily/{date}.en.md       # 英文 Markdown 日报（AI 生成，结构对齐中文版）
data/{date}.raw.json     # 原始采集数据（含 counts + items）
docs/                    # GitHub Pages 站点（自动生成，无需手动编辑）
├── index.html           # 首页：最新一期 + 归档网格 + 热词
├── daily/{date}.html    # 每日详情页
├── audio/{date}.mp3     # 语音播报（仅保留最近 15 期）
├── audio/{date}.txt     # 口播稿文本
├── podcast.xml          # 播客 RSS（含 iTunes 标签）
├── podcast.xsl          # 浏览器美化播客页样式表
├── search-index.json    # 客户端全文搜索索引
├── creator.html         # 小宇宙上传助手工具页
└── 404.html
```

## 环境变量

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `API_KEY` | 是 | - | DeepSeek/OpenAI API Key |
| `API_BASE_URL` | 否 | `https://api.deepseek.com` | API 地址 |
| `API_MODEL` | 否 | `deepseek-chat` | 模型名称 |
| `AUDIO_VOICE` | 否 | `zh-CN-YunyangNeural` | edge-tts 音色 |
| `BUTTONDOWN_API_KEY` | 否 | - | Buttondown 邮件推送 |

## 扩展指南

- **添加数据源**：编辑 `sources.py` 中的 `RSS_SOURCES` 列表，格式为 `(url_or_list, name, max_items, cutoff_days)`。URL 可以是字符串或候选 URL 列表（fallback）。
- **修改 AI 筛选逻辑**：编辑 `summarize.py` 中的 `SYSTEM_PROMPT`。
- **调整发布时间**：真正的定时触发在 cron-job.org 上配置，仓库内的 `.github/workflows/daily.yml` cron 仅作为兜底。
- **添加新类别**：修改 `sources.py` 中的 `make_item()` 的 `category` 参数，并在 `summarize.py` 的 `format_raw_content()` 中添加对应的格式化段落，同时在 `generate_site.py` 的 `cat_type()` 中添加分类映射。
