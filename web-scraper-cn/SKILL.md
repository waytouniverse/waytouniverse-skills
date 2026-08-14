---
name: web-scraper-cn
description: |
  抓取国内网站（SPA单页应用）的内容并提取关键信息。
  当用户需要：
  - 访问并提取国内网站页面内容
  - 抓取SPA/动态渲染页面的内容（如Vue/React构建的网站）
  - 提取政策文件、文章、详情页的结构化信息
  - 需要访问非GitHub的国内链接并整理内容
  - 遇到WebFetch工具无法访问的网站

  使用方法：提供URL，技能会自动渲染页面并提取主要内容。
compatibility: |
  - Python 3.x
  - Playwright (Chrome/Chromium)
  - 需要系统已安装 Chrome 浏览器
---

# Web Scraper CN - 国内网站内容抓取技能

## 功能概述

本技能用于抓取国内网站（特别是SPA单页应用）的内容。由于很多国内政府网站、企业平台使用Vue/React等前端框架构建，直接curl或WebFetch只能获取到空的HTML框架，无法获取实际内容。本技能使用Playwright+Chrome浏览器渲染页面，获取完整内容。

## 触发条件

当用户有以下需求时，使用本技能：

1. "帮我抓取这个链接的内容"
2. "访问这个国内网站"
3. "提取这个页面的信息"
4. "这个SPA网站的内容"
5. "帮我查看这个政策/文章/详情页"
6. 提供的URL是政府网站(.gov.cn)、企业官网、或任何使用前端框架构建的网站
7. WebFetch工具返回空内容或提示无法访问

## 工作流程

### 步骤1：分析URL和用户需求

确认：
- URL是否可访问
- 用户需要提取什么类型的内容（政策文件、文章列表、详情页等）
- 是否需要提取特定字段（标题、日期、正文等）

### 步骤2：运行抓取脚本

```bash
python ~/.claude/skills/web-scraper-cn/scripts/scrape.py "<URL>" [--wait <秒数>] [--output <文件路径>]
```

参数说明：
- `URL`: 要抓取的网页地址（必需）
- `--wait`: 等待页面加载的秒数，默认3秒
- `--output`: 输出文件路径，默认输出到控制台

### 步骤3：提取和整理内容

根据用户需求，从抓取到的HTML/文本中提取关键信息：
- 标题、发布时间、发布机构
- 正文内容
- 表格数据
- 附件列表

### 步骤4：格式化输出

根据内容类型，整理成合适的格式：
- 政策文件：Markdown格式，包含关键条款表格
- 文章/新闻：提取核心要点
- 列表页：结构化表格
- 保存为文件或直接在对话中展示

## 脚本使用说明

### 基本用法

```python
# 抓取单个页面
python scripts/scrape.py "https://example.com/page"

# 抓取并保存到文件
python scripts/scrape.py "https://example.com/page" --output content.txt

# 增加等待时间（适用于加载较慢的页面）
python scripts/scrape.py "https://example.com/page" --wait 5
```

### 脚本输出

脚本会输出：
1. 页面标题
2. 页面URL（处理跳转后的实际URL）
3. 页面主要内容（提取的文本）
4. 可选：完整HTML（用于进一步解析）

## 常见问题

### Q: 脚本运行失败，提示Chrome未找到？
A: 确保系统已安装Chrome浏览器。脚本会自动检测以下路径：
- macOS: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
- Linux: `/usr/bin/google-chrome` 或 `/usr/bin/chromium-browser`

### Q: 页面内容为空？
A: 可能是等待时间不够，尝试增加 `--wait` 参数的值

### Q: 某些元素抓取不到？
A: SPA页面可能需要点击或滚动才能加载全部内容，可以修改脚本添加交互逻辑

## 依赖安装

如果系统没有安装依赖，需要先安装：

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装Playwright
pip install playwright
playwright install chromium
```

或使用系统Chrome（推荐）：
```bash
# macOS
pip install playwright
# 不需要单独安装浏览器，脚本会使用已安装的Chrome
```

## 注意事项

1. **遵守robots.txt**: 抓取前检查网站的robots.txt文件
2. **频率控制**: 不要过于频繁地抓取同一网站
3. **超时处理**: 默认超时30秒，如果页面加载慢可以调整
4. **动态内容**: 某些内容可能需要登录或特定操作才能获取，本技能无法处理这类情况
