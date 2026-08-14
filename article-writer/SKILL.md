---
name: article-writer
description: |
  基于素材的深度评论文章写作+配图+微信公众号排版发布。当用户提供多篇素材（URL、文件路径或文本），要求围绕某个主题写文章时使用此技能。

  触发条件：
  - "帮我写一篇关于XX的文章" + 提供了素材链接/文件
  - "根据这些素材写篇文章"
  - "基于这些内容，写一篇XX主题的文章"
  - 用户提供了多篇文章/链接，要求提炼后写作

  核心流程：三稿法——先写3篇不同角度的初稿，再合并为1篇最终稿，然后配图、排版、发布。

  风格：有温度的犀利科技评论体——像有见识的普通人在认真跟你聊一件打动他的事。短句断行、节奏波动、口语化、数据当锤子、文化升维。详见风格指南。
---

# Article Writer：基于素材的深度评论文章写作

## 功能概述

本技能用于根据用户提供的素材（文章链接、文件、文本等），围绕一个主题撰写深度评论文章，并完成配图、微信公众号排版和发布。

核心方法论是**三稿法**：
1. 消化素材，提炼主题
2. 写3篇不同角度/风格的初稿（各生成md文档）
3. 从3篇中提取精华，合并为1篇最终稿（生成md文档）
4. 为文章配图（封面图+正文插图）
5. 微信公众号排版并发布

## 步骤0：判断文章类型（必须先执行）

动笔之前，根据素材内容和用户意图，判断文章类型。不同类型对应不同的写作目标和风格。

### 类型对照表

| 特征 | 深度评论 | 项目推荐 | 技术教程 |
|------|---------|---------|---------|
| **典型素材** | 多篇新闻/报道/分析 | GitHub 仓库、产品链接 | 技术文档、代码片段 |
| **用户意图** | "分析一下XX"、"怎么看XX" | "介绍这个项目"、"推荐XX工具" | "XX怎么用"、"写个教程" |
| **写作目标** | 输出观点，让读者对事件有更深理解 | 让读者觉得好用，想去试试 | 让读者学会，能照着做 |
| **核心内容** | 因果分析、数据对比、判断 | 使用场景、功能亮点、上手体验 | 步骤拆解、代码示例、注意事项 |
| **技术细节** | 翻译成人话，术语带解释 | 降到最低，只讲和"用"相关的 | 充分展开，关键步骤配代码 |
| **三稿法** | 叙事体+分析体+评论体 | 场景体+功能体+体验体 | 概述体+步骤体+避坑体 |

### 判断规则

1. 用户给了 GitHub 链接/仓库地址，说"介绍"、"推荐"、"写文章" → **项目推荐**
2. 用户给了多篇新闻/报道，说"分析"、"评论"、"怎么看" → **深度评论**
3. 用户给了技术文档/代码，说"教程"、"怎么用"、"怎么实现" → **技术教程**
4. 混合场景（如既有仓库链接又有技术分析需求），以用户主要意图为准

### 项目推荐类的写作要求

项目推荐的核心是**让读者觉得这个项目有用、好用、想用**：

- **先说能干什么**：用一句话说清项目解决什么问题，然后描述 2-3 个真实使用场景（年会、团建、发布会…），让读者产生"我也用得上"的感觉
- **再说好在哪**：和常见替代方案对比（不是和竞品撕，是和"自己写一个"比），突出省时省力
- **截图优先于文字**：界面是用户的第一印象，关键页面（首页、核心功能、后台）必须有截图
- **技术细节大幅度压缩**：只提技术栈名字，不拆架构、不列依赖、不写配置。读者不需要知道用了几个 useState
- **上手成本一定要讲**：clone → 改配置 → 跑起来，给一个清晰的时间预期（"三十分钟上线"比"支持 Nginx 反向代理配置"更有效）
- **风格**：轻松、直接、像朋友推荐一个好工具。可以用"你"称呼读者。可以有感叹号。句子不需要像深度评论那么锋利。

### ⚠️ 判断错误示例

- ❌ 用户给了 GitHub 仓库让介绍 → 写成了技术架构分析文 → 读者看完不知道这项目能干嘛
- ❌ 用户给了多篇报道让分析趋势 → 写成了产品功能介绍 → 没有观点

## 作者身份与写作视角

写作前必须读取 `{{SKILL_PATH}}/author-profile.md`，所有文章以该文件中定义的作者身份和视角撰写。该文件包含：

- 默认作者身份（产品经理、框架设计师、重度 vibe Coding 用户）
- 写作姿态与第一人称视角规范
- 身份切换规则

以后新增个人背景、经历、偏好等信息，直接追加到 `author-profile.md` 中即可，无需修改 SKILL.md。

## 工作流程

### 步骤1：收集素材

用户会提供素材来源，可能是：
- 微信公众号链接
- 网页URL
- 本地文件路径
- 直接粘贴的文本

对URL素材，优先使用 `web-scraper-cn` 技能抓取内容（微信公众号等国内网站 WebFetch 无法访问）。对本地文件直接读取。

确保所有素材内容完整提取后再进入下一步。

### 步骤2：消化素材，确定主题

阅读所有素材后：
- 如果用户指定了主题，使用用户主题
- 如果用户未指定主题，自行提炼一个主题
  - 主题要尖锐、有判断，不要中性描述
  - 好的主题："DeepSeek V4：算力困局逼出的中国答案"
  - 坏的主题："DeepSeek V4 的一些分析"

### 2.1 高级感选题与标题要求

当用户明确要求文章要有"高级感"，或素材本身是行业评论、产品趋势、商业判断类文章时，必须先把选题从"工具体验/功能介绍"抬到"关系变化/结构变化/行业判断"：

- **借产品写行业判断**：不要只写"用了几天XX"、"XX真正打动我的是什么"、"XX为什么好用"，而要写这个产品背后改变了什么关系，例如人和软件的关系、入口和后台的关系、工具和任务的关系、采购和结果的关系
- **标题要有判断和概念张力**：标题应像一个可争论的判断，不像普通体验感受；优先使用"XX 抢的不是A，是B"、"XX 之后，A 开始 B"、"真正危险的不是A，是B"这类结构
- **避免AI味标题**：少用"我发现"、"真正打动我"、"为什么越来越累"、"不是X而是Y"的模板化痛点标题；如果使用第一人称，必须有真实、具体、不可替代的经历支撑，不能硬编场景
- **不要照搬参考文靶子**：参考文章可以借论证路径和结构力度，但不能复用同一个核心问题；要换一个新靶子，例如参考文讲"SaaS会不会被杀死"，新文可以讲"办公入口从软件迁移到任务"
- **高级感来自关系重定义**：每个核心段落都要回答"这件事重新定义了谁和谁的关系"，而不是罗列产品功能

### 步骤3：创建文章文件夹

在用户当前工作目录下创建专属文件夹，本次写作的所有文件都放在这个文件夹里：

- 文件夹命名格式：`文章主题名/`（去掉标题中的冒号等不适合文件名的字符）
- 例如：`DeepSeek-V4算力困局逼出的中国答案/`
- 文件夹内包含：3篇初稿 + 1篇最终稿 + 图片子目录

### 步骤4：写3篇初稿

**根据步骤0判断的文章类型，选择对应的三稿方案：**

#### 深度评论类：叙事体 + 分析体 + 评论体

1. **叙事体**：故事线驱动，用人物、事件、时间串联，节奏感强
2. **分析体**：结构化拆解，用数据、对比、因果论证，逻辑清晰
3. **评论体**：观点先行，先立靶子再反驳，判断鲜明

#### 项目推荐类：场景体 + 功能体 + 体验体

1. **场景体**：从使用场景切入，"你下周年会要抽奖→你搜了一圈GitHub→你发现了这个"。让读者代入自己的需求，产生"我也用得上"的感觉
2. **功能体**：展示项目能做什么，图文配合（标注"此处放截图"），每个功能配一个场景说明——不是罗列，是"这个功能能帮你省什么事"
3. **体验体**：第一人称上手体验，"我花 30 分钟从 clone 到上线"，突出低门槛。写真实的感受，包括小坑（如果有的话），增加可信度

#### 技术教程类：概述体 + 步骤体 + 避坑体

1. **概述体**：一句话说清要做什么，前置效果展示
2. **步骤体**：按操作顺序，每一步配代码/截图
3. **避坑体**：常见报错、配置陷阱、环境问题

每篇初稿：
- 独立成文，有自己的完整性
- 侧重点不同，但核心论点一致
- 生成独立的md文档，文件名格式：`初稿-叙事体.md`、`初稿-分析体.md`、`初稿-评论体.md`
- 保存到步骤3创建的文章文件夹内

### 步骤5：合并最终稿

从3篇初稿中提取精华，合并为1篇最终稿：

**合并原则**（根据文章类型选择）：

**深度评论类**：
- 偏重评论体和分析体的风格，叙事体只取故事性片段
- 每篇中最有力的段落、最精准的数据、最击中人心的判断，优先保留
- 确保逻辑链条完整：开篇立靶→困局铺陈→核心论证→代价不回避→升华收尾

**项目推荐类**：
- 偏重场景体和体验体的风格，功能体作为骨架穿插
- 核心逻辑：你有什么需求 → 这个项目怎么满足 → 上手多简单 → 截图证明
- 技术细节严格压缩，每个技术点必须问自己"读者需要知道这个才用得上吗"
- 必须有一个明确的上手成本陈述（"从零到上线 X 分钟"）

**技术教程类**：
- 偏重步骤体，概述体做引子，避坑体穿插在对应步骤后
- 步骤必须可复现，每步给预期结果
- 报错信息原文保留（方便读者搜索）

**⚠️ 大标题不要进正文**：终稿.md 的第一行写 `# 大标题` 仅供文件识别用。但在生成**排版终稿.md**时，**必须去掉 `# 大标题` 这一行**。公众号的标题是在发布时单独填写的，正文里再出现大标题就是重复显示。排版终稿.md 应该直接从正文第一段开始。

**风格要求**：严格遵循 `{{SKILL_PATH}}/references/style-guide.md` 中的风格指南。核心特征：
- 短句为主，单句成段，节奏波动推进
- "不是X。是Y。"的否定+重判句式
- 反问句当武器，用后必答
- 比喻从日常生活取材，一句话搞定
- 数据当锤子：先冲击性数字→对比→判断
- 技术内容翻译成人话，术语用括号补充
- 知识"聊着聊着顺手掏出来"，不是教科书式科普
- 私人视角切入，敢下判断，也敢承认不确定
- 必须有不回避短板的段落
- 收尾用判断或回环呼应，不用总结
- 开篇从具体事件切入，绝不宏大叙事
- 写完后跑四层自检体系

最终稿生成md文档，文件名格式：`终稿.md`，保存到文章文件夹内。

### 步骤6：配图

**⚠️ 无论文章类型、无论用户是否提供截图，封面图（cover-wide.png + cover-square.png）和文章开篇插图（illustration-01.png）必须用 `gpt-image` 技能生成。** 这是公众号排版的基本要求。用户提供的真实截图作为正文插图穿插使用，不能替代封面图和开篇图。

为文章生成图片，使用 `gpt-image` 技能。所有图片保存到文章文件夹内的 `images/` 子目录。

**固定风格提示词**（每张图的提示词末尾必须追加）：
```
retro pixel art, CRT monitor effect, DOS terminal UI, cyberpunk hacker aesthetic, 8-bit pixel illustration, scanline texture, VHS noise, glitch art, green phosphor screen, old computer interface, low resolution graphics, retro tech poster, dark cyber aesthetic, pixel UI dashboard, arcade game style, vintage operating system interface ,Chinese
```

#### 6.1 封面图（2张，不进正文）

封面图仅用于公众号封面缩略图，**不进正文**：

| 图片 | 比例 | 用途 | 文件名 |
|------|------|------|--------|
| 封面横图 | 2.35:1（用 `21:9`） | 公众号封面 | `cover-wide.png` |
| 封面方图 | 1:1 | 公众号次条封面/分享图 | `cover-square.png` |

提示词构成：根据文章主题提炼核心视觉元素 + 固定风格提示词。

示例：
```bash
python3 ~/.claude/skills/gpt-image/scripts/generate.py "A pixel art illustration of a giant whale breaking through digital chains, circuit board patterns, Chinese AI chips emerging from matrix code, retro computer terminal display, retro pixel art, CRT monitor effect, DOS terminal UI, cyberpunk hacker aesthetic, 8-bit pixel illustration, scanline texture, VHS noise, glitch art, green phosphor screen, old computer interface, low resolution graphics, retro tech poster, dark cyber aesthetic, pixel UI dashboard, arcade game style, vintage operating system interface" 21:9 2k ./文章文件夹/images
```

#### 6.2 正文插图（0-6张）

根据文章内容判断是否需要插图：
- 总图片数量（含封面）控制在 **3-6张**
- 插图放在能增强阅读体验的位置，不要强行插入
- 适合插图的位置：关键数据段之后、核心比喻处、转折点
- 提示词 = 根据该段落内容提炼的视觉描述 + 固定风格提示词
- 正文插图比例默认 `16:9`，分辨率 `2k`
- 文件名格式：`illustration-01.png`、`illustration-02.png`

#### 6.3 在终稿中标记图片位置

在 `终稿.md` 中用 Markdown 图片语法标记所有图片位置：
- **文章开头必须是一张正文插图**（封面图不进正文）
- 正文插图放在对应段落的上方或下方
- 插图数量 2-4 张，总数（含封面）4-6 张

```markdown
![](images/illustration-01.png)

文章开头内容...

更多正文内容...

![](images/illustration-02.png)

继续正文...
```

**重要**：生成图片后，**不要使用 Read 工具查看图片文件**，只报告文件路径即可。

### 步骤7：选择排版引擎 → 排版

#### 7.0 排版引擎选择

使用 AskUserQuestion 让用户选择排版引擎：

| 引擎 | 风格 | 主题数 | 适用场景 |
|------|------|--------|---------|
| **gzh-design（推荐）** | 丰富组件·6套主题·自动章节编号·关键词下划线 | 6 + 可自定义 | 深度长文、教程、测评 |
| **format.py** | 简洁科技风 | 3 | 快速排版、简短内容 |

- 用户选 gzh-design → 进入 7.1
- 用户选 format.py → 进入 7.5
- 用户未明确选择 → 默认使用 gzh-design（推荐）

---

#### 7.1 [gzh-design] 选定主题

读取 `{{SKILL_PATH}}/references/gzh-themes/theme-index.md`（主题信息的单一来源）。根据文章题材主动推荐最契合的主题：

| 文章题材 | 推荐主题 |
|---------|---------|
| 教程/测评/清单/工具盘点（信息密度高） | **摸鱼绿**（默认） |
| 深度分析/观点/力量感话题 | **红白色系** |
| 设计/科技评论/专业观点/高端品牌 | **石墨极简风** |
| 禅意/极简生活/深度随笔 | **留白禅意风** |
| 工具对比/创意评测 | **摸鱼票据风** |
| 内刊手记/深度评测/案例复盘 | **橄榄手记** |

用 AskUserQuestion 一步确认推荐主题（给出推荐项 + 1~2 个备选 + "看全部6套"），用户指定了主题则直接用。

#### 7.2 [gzh-design] 读取组件库

同时读取两份文件：
1. 选定主题的专属组件库：`{{SKILL_PATH}}/references/gzh-themes/theme-{标识}.md`
2. 通用增量库：`{{SKILL_PATH}}/references/gzh-themes/common-components.md`（代码块/图片/GIF/小标签，所有主题共用）

后续 HTML 生成完全依据这两份组件库，不凭记忆手写。

#### 7.3 [gzh-design] 装配 HTML

读取 `排版终稿.md`，按以下规则装配：

1. **判定文章类型**（教程/盘点/观点/访谈/数据/随笔/案例），查主题库的「文章类型→组件组合配方表」，确定核心组件组合
2. **按主题库的「完整文章模板骨架」顺序装配**，每个 Markdown 元素替换为对应组件
3. **智能处理**（必须执行）：
   - 章节自动编号（`##` 按顺序 01/02/03…，末章若为结语用 `∞`）
   - 正文关键词下划线：每个段落主动找 1-3 个核心短语用主题下划线 CSS 标记
   - 引言关键词高亮、目录提取（取前 3 个 `##` 为导读要点）
   - 开头引言卡署名：有作者就写，没有就用占位符
   - 尾部签名区：默认保留 `{{作者名}}` / `{{简介}}` 占位，提示用户替换
4. **行内标记映射**：`**加粗**`→主色加粗；`==高亮==`→渐变背景高亮；`<u>文字</u>`→下划线
5. **代码块**：用通用库的深色/浅色代码块组件，每行一个 `<p style="margin:0">`，绝不用 `white-space:pre`
6. **平台红线**：禁 `<style>`/`<script>`/`<div>`/`class`/`id`/`position:fixed`/`float`/`@media`/`display:grid`/CSS 变量/外部字体；样式全部内联；所有文字用 `<span leaf="">` 包裹
7. **中文全角标点**：正文标点一律全角（，。！？：；""''），代码块内保持原样
8. **输出格式**：纯 `<section>…</section>` 正文片段，不包 `<!DOCTYPE>`/`<html>`/`<head>`/`<body>`

将 HTML 写入 `文章文件夹/排版终稿_gzh.html`。

#### 7.4 [gzh-design] 校验 + 生成预览

```bash
# 第一步：合规校验（ERROR 必须清零，半角标点 WARNING 也要清零）
python3 ~/.claude/skills/article-writer/scripts/gzh_validate.py "文章文件夹/排版终稿_gzh.html"

# 第二步：生成带「复制」按钮的预览页
python3 ~/.claude/skills/article-writer/scripts/gzh_wrap_preview.py "文章文件夹/排版终稿_gzh.html"
```

如果校验报 ERROR，回到 7.3 修复后重新校验，直到 0 ERROR + 0 WARNING。

然后将干净 HTML 写入 `/tmp/article_final.html`，供步骤 8 推送使用：

```bash
cp "文章文件夹/排版终稿_gzh.html" /tmp/article_final.html
```

同时保存一份排版预览到文章文件夹：

```bash
cp "文章文件夹/排版终稿_gzh_预览.html" "文章文件夹/排版预览.html"
```

---

#### 7.5 [format.py] 简洁排版（原流程）

使用本技能自带的 `scripts/format.py` 将终稿排版为微信公众号格式。

**排版要求**：
- **标题（## 二级标题）**：绿色字体（`#07a35a`），18px，加粗，无背景/边框/阴影
- **正文**：15px，行间距 1.8
- **背景色**：`#f5f5f5` 浅灰
- **加粗关键词**：保持加粗，颜色跟随正文
- **整体风格**：科技深度长文风格，使用主题 `green-phosphor`

```bash
python3 ~/.claude/skills/article-writer/scripts/format.py \
  --input "文章文件夹/排版终稿.md" \
  --theme green-phosphor
```

脚本输出到 `/tmp/wechat-format/排版终稿/preview.html`。

**后处理（仅去 h1 + 保存）**：

```python
import re

with open('/tmp/wechat-format/排版终稿/preview.html', 'r') as f:
    html = f.read()

# 去掉 h1 大标题
html = re.sub(r'<h1[^>]*>.*?</h1>', '', html, flags=re.DOTALL)

# 保存本地排版预览
local_path = '文章文件夹/排版预览.html'
with open(local_path, 'w') as f:
    f.write(html)

# 同步回 /tmp
with open('/tmp/wechat-format/排版终稿/preview.html', 'w') as f:
    f.write(html)

# 提取 wechatHtml 用于服务器推送
match = re.search(r'<div id="wechatHtml">(.*?)</div>', html, re.DOTALL)
wechat_content = match.group(1)
with open('/tmp/article_final.html', 'w') as f:
    f.write(wechat_content)
```

### 步骤8：同步到服务器 → 推送到公众号（必须执行）

**⚠️ 严格按顺序：先保存本地排版预览 → 再上传服务器 → 再推公众号。绝对不能跳过本地。**

**⚠️ 每次必须完整执行 8.0→8.1→8.2→8.3，一步都不能少。不要问用户"要不要推送"，写完了就直接推。**

**⚠️ 推送结果必须向用户报告：文章标题、草稿创建成功/失败状态。**

SSH 密钥统一使用 `~/.claude/skills/aliyun-deploy/wudiyuzhou.pem`。

#### 8.0 先创建服务器目录

**SCP 不会自动创建目标目录，必须先 SSH 手动创建，否则 SCP 静默失败！**

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -i ~/.claude/skills/aliyun-deploy/wudiyuzhou.pem \
  root@8.134.156.178 "mkdir -p /var/www/wechat-publisher/articles/{文章目录}/images"
```

#### 8.1 生成 params.json 并同步到服务器

**⚠️ publish.py 从 `params.json` 读取文章标题，没有这个文件标题就是"未命名文章"。必须在推送前生成。**

params.json 是推送流程的临时文件，生成到 `/tmp` 即可，不要放到文章文件夹里。

```bash
# 生成 params.json 到 /tmp
python3 -c "
import json
params = {
    'title': '文章大标题（从终稿.md的第一行 # 提取）',
    'digest': '一句话摘要'
}
with open('/tmp/article_params.json', 'w') as f:
    json.dump(params, f, ensure_ascii=False, indent=2)
print('params.json 已生成')
"

# 同步 params.json 到服务器
scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -i ~/.claude/skills/aliyun-deploy/wudiyuzhou.pem \
  /tmp/article_params.json \
  root@8.134.156.178:/var/www/wechat-publisher/articles/{文章目录}/params.json

# 同步 HTML 到服务器
scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -i ~/.claude/skills/aliyun-deploy/wudiyuzhou.pem \
  /tmp/article_final.html \
  root@8.134.156.178:/var/www/wechat-publisher/articles/{文章目录}/article.html
```

#### 8.2 同步图片到服务器

封面图（公众号缩略图）和正文插图都要同步。**必须逐张上传，不能用 glob 通配符（可能静默失败）。每张上传后验证文件大小 > 0。**

```bash
# 封面图（重命名为 cover.png，publish.py 固定读这个名字）
scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -i ~/.claude/skills/aliyun-deploy/wudiyuzhou.pem \
  "文章文件夹/images/cover-wide.png" \
  root@8.134.156.178:/var/www/wechat-publisher/articles/{文章目录}/cover.png

# 正文插图 — 逐张上传，不能用 *.png 通配符
scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -i ~/.claude/skills/aliyun-deploy/wudiyuzhou.pem \
  "文章文件夹/images/illustration-01.png" \
  root@8.134.156.178:/var/www/wechat-publisher/articles/{文章目录}/images/

scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -i ~/.claude/skills/aliyun-deploy/wudiyuzhou.pem \
  "文章文件夹/images/illustration-02.png" \
  root@8.134.156.178:/var/www/wechat-publisher/articles/{文章目录}/images/
```

**上传后必须验证**：SSH 到服务器 `ls -la` 确认图片文件大小 > 0，目录非空。

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -i ~/.claude/skills/aliyun-deploy/wudiyuzhou.pem \
  root@8.134.156.178 "ls -la /var/www/wechat-publisher/articles/{文章目录}/images/"
```

如果 `images/` 是空的或者缺少图片，**立刻重新上传缺失的图片，不要跳过直接推送**。

#### 8.3 推送到公众号草稿箱

确认所有文件就位后推送：

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -i ~/.claude/skills/aliyun-deploy/wudiyuzhou.pem \
  root@8.134.156.178 "cd /var/www/wechat-publisher && python3 publish.py articles/{文章目录}"
```

服务器上的 `publish.py` 会自动：
1. 读取 `config.json` 获取公众号 AppID/AppSecret
2. 获取 access_token
3. 上传封面图为 thumb 素材
4. 上传正文中所有 `<img>` 引用的图片到微信 CDN，替换为 CDN 链接
5. 创建草稿
6. 调用 `notify.py` 发送企业微信机器人通知

推送成功后，到公众号后台「内容管理 → 草稿箱」查看，企业微信群也会收到通知。

#### 服务器自动化

阿里云服务器上已配置以下自动化：

| 功能 | 脚本 | 说明 |
|------|------|------|
| 推送通知 | `notify.py` | publish.py 推送成功后自动调用，发送文章标题、草稿 ID、时间到企业微信群和飞书群 |
| 定期清理 | `cleanup.py` | 每天凌晨 2:07 执行，清理 `articles/` 下 mtime 超过 30 天的目录，清理后发通知到企业微信 |

### 步骤9：告知用户

完成后告知用户：
- 文章文件夹路径
- 最终稿的文件路径
- 3篇初稿的文件路径（如需参考）
- 所有生成的图片路径
- 排版结果和发布状态
- **必须报告推送结果**：文章标题、草稿 media_id、是否成功推送到公众号草稿箱
- 简要说明最终稿的核心论点和结构

## 风格指南

完整的风格规范见 `{{SKILL_PATH}}/references/style-guide.md`，以下为核心要点的速查：

| 维度 | 要求 |
|------|------|
| 定位 | 有温度的犀利科技评论体，像有见识的普通人在认真跟你聊一件打动他的事 |
| 节奏 | 波动推进，扣主线句高频出现，偏出去再拉回来 |
| 句式 | 短句为主，单句成段，动词前置，句式断裂制造停顿 |
| 反问 | 当武器用，用后必答，也当节奏刹车和转向 |
| 比喻 | 接地气，一句话，不展开 |
| 数据 | 先冲击数字→对比→判断，不用表格 |
| 知识输出 | 聊着聊着顺手掏出来，不教科书式科普 |
| 私人视角 | 以产品经理+框架设计师+vibe Coding实践者的身份切入，"我自己用 AI 做过这件事"，敢下判断也敢承认不确定，不装全知 |
| 对立面 | 先理解对方处境再给出自己视角 |
| 开篇 | 从具体事件/场景切入，绝不宏大叙事 |
| 标题 | 像判断，不像学术章节 |
| 让步段 | 必须有，"我不打算洗地" |
| 收尾 | 用判断或回环呼应结束，不总结 |
| 升维 | 从具体事件自然连接到更大的文化/哲学/历史参照物 |
| 长度 | 见风格指南 |
| 禁忌 | 无学术腔、无套话、无堆术语、无空洞升华、无两面讨好、无连续长段、无emoji、无冒号/破折号/双引号 |
| 自检 | 写完跑四层质检体系（L1硬性规则→L2风格一致性→L3内容质量→L4活人感） |

## 配图风格规范

所有图片统一使用固定风格提示词，确保视觉一致性：

```
retro pixel art, CRT monitor effect, DOS terminal UI, cyberpunk hacker aesthetic,
8-bit pixel illustration, scanline texture, VHS noise, glitch art,
green phosphor screen, old computer interface, low resolution graphics,
retro tech poster, dark cyber aesthetic, pixel UI dashboard,
arcade game style, vintage operating system interface, Chinese,
```

这是像素复古+赛博朋克+老式终端的美学风格，绿色磷光屏幕、CRT 扫描线、VHS 噪点、8-bit 像素插画。所有图片必须追加此风格词，保证同一篇文章的配图风格统一。有文字，必须是中文。

## 微信公众号排版规范

- 标题：绿色字体（#07a35a），18px，加粗
- 正文：15-16px，行间距 1.75-2.0
- 默认主题：green-phosphor（绿色科技风格，开箱即用无需清理）
- 备选主题：newspaper、ink

## 文件夹结构示例

每次写作完成后，文件夹结构如下：

```
DeepSeek-V4算力困局逼出的中国答案/
  初稿-叙事体.md
  初稿-分析体.md
  初稿-评论体.md
  终稿.md
  排版终稿.md          （带绿色标题标记的md，供排版脚本使用）
  排版预览.html         （清理后的排版预览，本地查看用）
  images/
    cover-wide.png     （封面横图，仅用于公众号缩略图，不进正文）
    cover-square.png   （封面方图，仅用于分享图）
    illustration-01.png （正文插图）
    illustration-02.png （正文插图）
    illustration-03.png （正文插图，文章开头）
```

所有文件集中在同一个文件夹内，不散落在工作目录中。

## 注意事项

1. 素材是背景资料，不是抄写对象。要消化后用自己的话重新组织，不是改写原文
2. 三稿法的意义是探索不同角度，最终稿的合并不是简单拼接，而是有机重组
3. 如果用户对某篇初稿特别满意，可以在合并时加大那篇的权重
4. 所有文件保存到文章专属文件夹内，不要保存到临时目录，不要散落在工作目录根目录
5. 生成图片后不要用 Read 工具查看图片，只报告路径
6. 配图数量控制在3-6张，不要过度配图
7. 封面图必须生成，正文插图视内容需要而定
