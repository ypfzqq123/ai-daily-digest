# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

电梯行业周报 — 从新电梯网 RSS 采集资讯，通过 DeepSeek 智能筛选生成中日双语周报 + Word 文档 + 口播稿 MP3 + GitHub Pages 静态站点。

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 生成周报（固定拉 7 天数据）
cd scripts && python main.py

# 仅重建静态站点（不调用 AI，不抓数据）
cd scripts && python -c "from generate_site import generate_site; generate_site()"
```

运行前需设置环境变量 `API_KEY`（PowerShell：`$env:API_KEY="xxx"`）。

## 架构与流水线

`main.py` → 7 个步骤，3 次 DeepSeek API 调用：

| 步骤 | 脚本 | 职责 |
|------|------|------|
| 1. 采集 | `sources.py` | 新电梯网 RSS（`xindianti.cn`），自动分类为 accident/regulation/renovation/business/news，过滤"早新闻"汇总条目，按 URL/标题去重 |
| 2. 保存 | `main.py` | 原始数据写入 `data/{date}.raw.json` |
| 3. 总结 | `summarize.py` | ① DeepSeek 生成中文简报 → ② 第二次调用翻译为日语。API 参数：temperature 0.9、max_tokens 16384 |
| 4. 保存 | `main.py` | 中文 `daily/{label}.md`，日语 `daily/{label}.ja.md` |
| 5. Word | `main.py` | `python-docx` 生成 .docx，微软雅黑全局字体。来源格式 `URL（名称）`可点击。支持 `**加粗**` 渲染。输出去除字段标签前缀 |
| 6. 语音 | `audio.py` | ③ DeepSeek 改写口播稿（失败回退确定性脚本）→ edge-tts 合成 MP3 → 保留最近 15 期 |
| 7. 建站 | `generate_site.py` | 解析所有 Markdown → `docs/`，中日双语全文切换、深浅主题、全文搜索、播客 RSS |

**关键设计**：
- **周报模式**：固定拉 7 天数据，输出 8-14 条，每条含日期字段。日报模式已废弃
- **日语翻译**：单独一次 API 调用翻译中文结果，不依赖模型在单次响应中输出双语（DeepSeek 对日语单次双语输出不可靠）
- **安全事故过滤**：`main.py` 在 AI 调用前 `data.pop('accident', None)` 排除安全事故类资讯，最终只有 4 个分类
- **早新闻过滤**：新电梯网 RSS 每天有一条"新电梯网早新闻"汇总条目，与其他单条重复，`sources.py` 按标题过滤
- **自动分类**：`classify_item()` 基于关键词将资讯分为 5 类，accident 分类虽采集但在汇总前被丢弃
- **AI 输出格式**：标题纯加粗无 `[标签]` 前缀无 `：简述`，AI摘要承载全部详情（300+ 字）。所有视觉输出（Word/HTML）去除"AI摘要："字段标签前缀

## 每个条目的 Markdown 格式

```markdown
- **市场监管总局发布《特种设备使用管理规则》实施通知**
  - AI摘要：详细摘要内容，300+字，不看原文就能了解新闻全貌...
  - 来源：[新电梯网](https://www.xindianti.cn/news/show-xxx.html)
  - 日期：07-08
```

## 数据流

```
xindianti.cn RSS → sources.py → {category: [item, ...]}
                                      │
                              main.py → pop('accident')
                                      │
                          summarize.py → zh_text (调用①)
                                      │
                          summarize.py → ja_text (调用②翻译)
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
              daily/*.md        weekly/*.docx      audio.py (调用③)
              daily/*.ja.md     weekly/*_ja.docx   (edge-tts)
                    │
            generate_site.py ← daily/*.md + daily/*.ja.md → docs/
```

## 输出结构

```
daily/{label}.md           # 中文 Markdown（周报，含 AI摘要 结构标记）
daily/{label}.ja.md        # 日语 Markdown
weekly/{label}.docx        # 中文 Word 文档
weekly/{label}_ja.docx     # 日语 Word 文档
data/{date}.raw.json       # 原始采集数据
docs/                      # GitHub Pages 站点
├── index.html             # 首页 + 归档（中日全文切换）
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

## API 调用参数

| 用途 | temperature | max_tokens | 说明 |
|------|-------------|------------|------|
| 中文简报生成 | 0.9 | 16384 | `summarize.py` `_call_api` |
| 日语翻译 | 0.9 | 8192 | `summarize.py` `_translate_to_japanese` |
| 口播稿改写 | 0.6 | 3000 | `audio.py` `_deepseek_script` |

## 分类体系

| 分类键 | 中文标签 | 日语标签 | 是否纳入周报 |
|--------|----------|----------|-------------|
| `accident` | 安全事故与监管 | 安全事故と規制 | ❌ 被 `main.py` 过滤 |
| `regulation` | 政策标准 | 政策と標準 | ✅ |
| `renovation` | 老旧改造与加装 | 改修改造と増設 | ✅ |
| `business` | 企业动态 | 企業動向 | ✅ |
| `news` | 行业综合 | 業界総合 | ✅ |

## 扩展指南

- **添加数据源**：编辑 `sources.py` 的 `RSS_SOURCES` 列表，格式 `(url, name, max_items, cutoff_days)`
- **修改 AI 筛选**：编辑 `summarize.py` 的 `WEEKLY_SYSTEM_PROMPT`
- **修改日语翻译质量**：编辑 `summarize.py` 的 `TRANSLATE_SYSTEM_PROMPT`
- **调整分类规则**：编辑 `sources.py` 的 `classify_item()` 关键词列表
- **恢复安全事故分类**：移除 `main.py` 中 `data.pop('accident', None)` 并在提示词中加回分类标题
