# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

电梯行业周报 — 从新电梯网 RSS 采集资讯，通过 DeepSeek 智能筛选生成中日双语周报 + Word 文档 + 口播稿 MP3 + GitHub Pages 静态站点。

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 周报模式（周一自动触发，也可手动 --weekly 强制）
cd scripts && python main.py --weekly

# 日报模式（默认，非周一）
cd scripts && python main.py

# 仅重建静态站点（不调用 AI，不抓数据）
cd scripts && python -c "from generate_site import generate_site; generate_site()"
```

运行前需设置环境变量 `API_KEY`（PowerShell：`$env:API_KEY="xxx"`）。

## 架构与流水线

`main.py` → 7 个步骤：

| 步骤 | 脚本 | 职责 |
|------|------|------|
| 1. 采集 | `sources.py` | 新电梯网 RSS（`xindianti.cn`），自动分类为 accident/regulation/renovation/business/news，过滤"早新闻"汇总条目，按 URL/标题去重 |
| 2. 保存 | `main.py` | 原始数据写入 `data/{date}.raw.json` |
| 3. 总结 | `summarize.py` | DeepSeek 生成中文简报 → 第二次 API 调用翻译为日语。支持 `API_KEY` / `API_BASE_URL` / `API_MODEL` |
| 4. 保存 | `main.py` | 中文 `daily/{label}.md`，日语 `daily/{label}.ja.md` |
| 5. Word | `main.py` | `python-docx` 生成 .docx，微软雅黑全局字体、来源链接可点击，中日各一份 |
| 6. 语音 | `audio.py` | DeepSeek 改写口播稿（失败回退确定性脚本）→ edge-tts 合成 MP3 → 保留最近 15 期 |
| 7. 建站 | `generate_site.py` | 解析所有 Markdown → `docs/`，中日双语切换、深浅主题、全文搜索、热词趋势、播客 RSS |

**关键设计**：
- **日语翻译**：单独一次 API 调用翻译中文结果，不依赖模型在单次响应中输出双语（DeepSeek 对日语单次双语输出不可靠）
- **周报 vs 日报**：周一自动走周报模式（拉 7 天数据），其他天走日报模式（拉 3 天数据）。`--weekly` 强制周报
- **早新闻过滤**：新电梯网 RSS 每天有一条"新电梯网早新闻"汇总条目，与其他单条重复，`sources.py` 按标题过滤
- **自动分类**：`classify_item()` 基于关键词将资讯分为 5 类（安全事故/政策标准/老旧改造/企业动态/行业综合）

## 数据流

```
xindianti.cn RSS → sources.py → {category: [item, ...]}
                                      │
                          summarize.py → zh_text
                                      │
                          summarize.py → ja_text (第二次调用翻译)
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
              daily/*.md        weekly/*.docx      audio.py
              daily/*.ja.md     weekly/*_ja.docx   (edge-tts)
                    │
            generate_site.py ← daily/*.md + daily/*.ja.md → docs/
```

## 输出结构

```
daily/{label}.md           # 中文 Markdown（日报或周报）
daily/{label}.ja.md        # 日语 Markdown
weekly/{label}.docx        # 中文 Word 文档
weekly/{label}_ja.docx     # 日语 Word 文档
data/{date}.raw.json       # 原始采集数据
docs/                      # GitHub Pages 站点
├── index.html             # 首页 + 归档 + 热词
├── daily/{label}.html     # 详情页（中日切换）
├── audio/{label}.mp3      # 语音播报（保留 15 期）
├── audio/{label}.txt      # 口播稿
├── podcast.xml            # 播客 RSS
├── search-index.json      # 全文搜索索引
└── 404.html
```

## 环境变量

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `API_KEY` | 是 | - | DeepSeek API Key |
| `API_BASE_URL` | 否 | `https://api.deepseek.com` | API 地址 |
| `API_MODEL` | 否 | `deepseek-chat` | 模型名称 |
| `AUDIO_VOICE` | 否 | `zh-CN-YunyangNeural` | edge-tts 音色 |

## 分类体系

| 分类键 | 中文标签 | 日语标签 | 关键词特征 |
|--------|----------|----------|-----------|
| `accident` | 安全事故与监管 | 安全事故と規制 | 事故、伤亡、困人、故障、约谈、罚款、消防救援 |
| `regulation` | 政策标准 | 政策と標準 | 标准、法规、TSG、GB、总局、住建部、市场监管局 |
| `renovation` | 老旧改造与加装 | 改修改造と増設 | 加装、更新、改造、老旧、国债、补贴、惠民 |
| `business` | 企业动态 | 企業動向 | 中标、签约、合作、发布、展会、出海 |
| `news` | 行业综合 | 業界総合 | 默认分类 |

## 扩展指南

- **添加数据源**：编辑 `sources.py` 的 `RSS_SOURCES` 列表，格式 `(url, name, max_items, cutoff_days)`
- **修改 AI 筛选**：编辑 `summarize.py` 的 `SYSTEM_PROMPT` / `WEEKLY_SYSTEM_PROMPT`
- **修改日语翻译质量**：编辑 `summarize.py` 的 `TRANSLATE_SYSTEM_PROMPT`
- **调整分类规则**：编辑 `sources.py` 的 `classify_item()` 关键词列表
