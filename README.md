# waytouniverse-skills

开源 AI 技能合集，支持 **Claude Code** / **OpenClaw (QClaw)** / **OpenAI Codex** 三种 AI 编码工具。

共 **18 个技能**，按用途分三组。带源码目录的可直接复制安装；其余提供 zip 包下载（也可在网页端「技能库」点「复制给 AI」一键安装）。

## 技能列表

### 内容创作

| 技能 | 说明 | 获取 |
|------|------|------|
| PPT 生成器 | 根据 PPT 大纲，用 AI 逐页生成视觉风格统一的 PPT 图片。 | [ppt-generator/](./ppt-generator) |
| 深度评论文章写作 | 基于素材的深度评论文章写作＋配图＋公众号排版发布，三稿法成文。 | [article-writer.zip](https://github.com/waytouniverse/waytouniverse-skills/releases/latest/download/article-writer.zip) |
| AI 生图 | 通过 APIMart 调用 GPT-Image-2 生成图片，文生图/图生图，13 种比例 + 3 档分辨率。 | [gpt-image.zip](https://github.com/waytouniverse/waytouniverse-skills/releases/latest/download/gpt-image.zip) |
| PPT 演示生成 | 预置视觉主题组合页面，生成可离线打开、浏览器可编辑的 HTML 演示，支持导出 PPTX / PDF。 | [dashi-ppt.zip](https://github.com/waytouniverse/waytouniverse-skills/releases/latest/download/dashi-ppt.zip) |
| 公文格式 Word | 生成符合中国政府公文标准的正式 Word 文档，严格字体、行距与版式。 | [official-docx.zip](https://github.com/waytouniverse/waytouniverse-skills/releases/latest/download/official-docx.zip) |
| 公文格式转换 | 按照 GB/T 9704 标准生成中国党政机关公文格式 Word 文档。 | [chinese-gov-docx/](./chinese-gov-docx) |
| Word 文档处理 | 创建、编辑、分析 .docx，支持修订、批注、格式保留与文本提取。 | [docx.zip](https://github.com/waytouniverse/waytouniverse-skills/releases/latest/download/docx.zip) |
| PDF 全能处理 | 合并、拆分、旋转、水印、加解密、表单填写与 OCR 识别。 | [pdf.zip](https://github.com/waytouniverse/waytouniverse-skills/releases/latest/download/pdf.zip) |
| 电子表格处理 | 创建、编辑、分析 .xlsx / .csv，支持公式、格式化与数据可视化。 | [xlsx.zip](https://github.com/waytouniverse/waytouniverse-skills/releases/latest/download/xlsx.zip) |

### 飞书生态

| 技能 | 说明 | 获取 |
|------|------|------|
| 飞书云文档 | 读取和编辑飞书 Docx / Wiki 文档，支持插入与下载图片附件。 | [lark-doc.zip](https://github.com/waytouniverse/waytouniverse-skills/releases/latest/download/lark-doc.zip) |
| 飞书多维表格 | 建表、字段、记录、视图、公式、表单、仪表盘与 workflow 全覆盖。 | [lark-base.zip](https://github.com/waytouniverse/waytouniverse-skills/releases/latest/download/lark-base.zip) |
| 飞书电子表格 | 管理行列结构、批量读写、公式图表、透视表与财务建模。 | [lark-sheets.zip](https://github.com/waytouniverse/waytouniverse-skills/releases/latest/download/lark-sheets.zip) |
| 飞书即时通讯 | 收发消息、管理群聊、文件收发、交互卡片与回调处理。 | [lark-im.zip](https://github.com/waytouniverse/waytouniverse-skills/releases/latest/download/lark-im.zip) |
| 飞书日历 | 管理日程与会议室，查询忙闲、推荐时段、预定会议。 | [lark-calendar.zip](https://github.com/waytouniverse/waytouniverse-skills/releases/latest/download/lark-calendar.zip) |
| 飞书幻灯片 | 创建、编辑幻灯片，管理页面与内容替换。 | [lark-slides.zip](https://github.com/waytouniverse/waytouniverse-skills/releases/latest/download/lark-slides.zip) |

### 搜索与工具

| 技能 | 说明 | 获取 |
|------|------|------|
| 联网搜索 | 豆包 AI Search 实时搜索互联网，最新新闻、热点与数据一搜即得。 | [web-search.zip](https://github.com/waytouniverse/waytouniverse-skills/releases/latest/download/web-search.zip) |
| 发现与安装技能 | 从开放技能生态发现并安装更多 Agent Skill，npx skills 一键搞定。 | [find-skills.zip](https://github.com/waytouniverse/waytouniverse-skills/releases/latest/download/find-skills.zip) |
| 国内网页抓取 | 抓取国内 SPA 动态渲染页面内容，提取政策、文章等结构化信息。 | [web-scraper-cn.zip](https://github.com/waytouniverse/waytouniverse-skills/releases/latest/download/web-scraper-cn.zip) |

## 安装方法

根据你使用的 AI 工具，将技能文件夹复制到对应目录：

```bash
# Claude Code
cp -r <技能目录> ~/.claude/skills/

# OpenClaw (QClaw)
cp -r <技能目录> ~/.agents/skills/

# OpenAI Codex
cp -r <技能目录> ~/.codex/skills/
```

下载 zip 的技能，解压后再复制，例如：

```bash
unzip gpt-image.zip -d ~/.claude/skills/
```

例如安装 PPT 生成器：

```bash
# Claude Code
cp -r ppt-generator ~/.claude/skills/
```

也支持符号链接：

```bash
ln -s /你的路径/waytouniverse-skills/ppt-generator ~/.claude/skills/ppt-generator
```

## 安装路径速查

| 工具 | 技能目录 |
|------|----------|
| Claude Code | `~/.claude/skills/` |
| OpenClaw (QClaw) | `~/.agents/skills/` |
| OpenAI Codex | `~/.codex/skills/` |

## 许可证

MIT
