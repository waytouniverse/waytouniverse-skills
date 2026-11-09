# export-quotation · 中英双语外贸出口报价单生成器

> 把产品参数、规格表或客户采购清单交给 AI，直接得到一份**可以发给客户**的 USD 报价单 Excel。
> English documentation: [jump to English](#english).

一个标准 Agent Skill（`SKILL.md` + `scripts/` + `references/`），最初为 WorkBuddy 编写，也可被任何支持 SKILL.md 的 Agent 读取。生成器本身是纯 Python，不依赖任何 AI 平台。

## 能做什么

- **输入**：产品参数文字、Excel/CSV 表格、PDF 产品目录、手写采购清单照片，或客户聊天里的一段描述。
- **输出**：2 个工作表的 `.xlsx`：
  - `报价单 Quotation` —— 客户版，中英双语抬头、买卖双方、报价信息（单号／日期／有效期／Incoterms 2020／港口／付款／交期／币种／汇率）、12 列商品明细、附加费与税费、GRAND TOTAL、银行信息、5 条中英对照条款、双方签字盖章栏；A4 横向打印。
  - `填写指引 Guide` —— 内部页：公式清单、汇率与内部核算、常用下拉选项、客户诉求跟进清单（**发送客户前建议删除**）。
- **自带公式**：序号（填品名自动生成）、行金额＝数量×单价、数量／金额／毛重／体积合计、有效期至、折扣额、附加费小计、税额、GRAND TOTAL、人民币参考金额、跨表核算。所有公式带空值保护。
- **不编造**：公司名、银行账号、SWIFT、HS 编码、毛重、体积、单价——资料里没有的一律留空或 `[ ]` 占位并明确提示。
- **无单价模式**：客户只给参数没给价格时，单价留空、总计暂为 0，填好单价后自动重算，不替你编价格。

## 快速开始（WorkBuddy 完整流程）

```bash
SKILL=/path/to/export-quotation

# 1) 把客户资料整理成输入 JSON（字段见 references/quotation_spec.md）
#    汇率请查报价当日官方中间价，不要用样例里的历史值
# 2) 生成
python3 $SKILL/scripts/generate_quotation.py --input data.json --output 客户名报价单_20261109.xlsx
# 3) 交付前一键重算 + AIGC 标识 + 逐项核对计算链
python3 $SKILL/scripts/finalize.py --file 客户名报价单_20261109.xlsx
```

第 3 步返回 `"status": "passed"` 才能交付；失败会明确指出是哪一项。

## 独立使用（任何 Agent / 纯 Python）

`generate_quotation.py` 只依赖 Python 3.9+ 与 `openpyxl`，可以直接用：

```bash
pip install -r requirements.txt
python3 scripts/generate_quotation.py --input assets/example_input.json --output quotation.xlsx
```

生成的公式在 Excel / WPS / LibreOffice 中打开即自动计算；若预览器需要缓存值，用 LibreOffice 打开后另存一次即可刷新。`finalize.py` 是可选的**交付前校验**封装。

## 平台依赖说明（重要）

| 文件 | 依赖 | 非 WorkBuddy 环境 |
|---|---|---|
| `scripts/generate_quotation.py` | Python 3.9+、`openpyxl` | ✅ 完全可用 |
| `scripts/finalize.py` | 重算与标识脚本来自 WorkBuddy 内置 `workbuddy-sheet-generation` 插件，且需要 LibreOffice | ⚠️ 可跳过；改用 Excel/WPS/LibreOffice 打开并保存刷新公式缓存，AIGC 标识可忽略 |
| `SKILL.md` | 标准 Agent Skill 格式 | ✅ 可被 Claude Code / Codex / 其他 Agent 读取 |
| `assets/版式基准…xlsx` | 无 | ✅ 空白模板，需要空白单时直接复制 |

`SKILL.md` 中提到的「规矩文档」「踩坑日志」是作者工作区的可选协作约定，普通用户可忽略；通用防错清单已整理在 `references/pitfalls.md`。

## 最小输入示例

```json
{
  "quotation_no": "QT-20261109-001",
  "quote_date": "2026-11-09",
  "rate": 6.7188,
  "rate_source": "报价当日官方中间价及来源",
  "items": [
    {"cn": "门锁", "en": "Door Lock", "spec": "DL-801 / SS 304",
     "qty": 100, "unit": "pcs", "price": 7.85, "remark": "带钥匙 / w/ keys"}
  ]
}
```

完整字段表、别名、行锚点与公式清单见 [`references/quotation_spec.md`](./references/quotation_spec.md)；14 项真实回归样例见 [`assets/example_input.json`](./assets/example_input.json)。

## 回归基准

| 场景 | 明细行 | 公式数 | 校验项 | GRAND TOTAL |
|---|---|---|---|---|
| 14 项手写清单 | 14 | 43 | 49 | **3542.00 USD** / CNY 23797.9896 |
| 只给参数、无单价无汇率 | 3 | 21 | 27 | 0.00（待填） |
| 折扣 5% + 运费 800 + 税 13% | 1 | 17 | 23 | 2245.875 USD / CNY 15089.58495 |

## 使用前必读

1. 汇率每次查**报价当日**官方中间价并注明来源；人民币金额仅供参考，结算以 USD 为准。
2. 明细行数变化请修改 `items` 后重新生成整份工作簿，**不要手工插行**（公式引用会错位）。
3. 发送客户前替换所有 `[ ]` 占位符，核对银行账号与 SWIFT，删除「填写指引 Guide」内部页。
4. 本仓库样例中的品名、单价、单号均为演示数据，不代表任何真实报价。

## 目录结构

```
export-quotation/
├── SKILL.md                       # 技能入口：触发词、工作流、硬性规矩
├── README.md                      # 本文件
├── requirements.txt               # openpyxl
├── scripts/
│   ├── generate_quotation.py      # JSON → xlsx（参数化生成）
│   └── finalize.py                # 重算 + AIGC 标识 + 计算链校验
├── references/
│   ├── quotation_spec.md          # 字段 / 锚点 / 公式 / 双语术语
│   └── pitfalls.md                # 踩坑与防错清单
└── assets/
    ├── example_input.json         # 14 项回归样例
    └── 版式基准_中英双语出口报价单模板.xlsx   # 空白版式基准
```

## 许可证

MIT，见仓库根目录 [`LICENSE`](../LICENSE)。

---

<a id="english"></a>

# English

**Bilingual (CN/EN) export quotation generator.** Give an AI agent your product parameters, spec sheet, or a buyer's purchase list (including a photo of a handwritten list); it produces a ready-to-send, printable USD quotation workbook with live formulas.

**Highlights**

- Two sheets: `报价单 Quotation` (customer-facing) and `填写指引 Guide` (internal notes, remove before sending).
- Full bilingual structure: seller/buyer, quotation metadata (Incoterms 2020, ports, payment, lead time, currency, FX rate), 12-column item table, charges & tax, GRAND TOTAL, bank details, terms, signatures.
- Built-in formulas with blank-value guards: item No., line amount, column totals, valid-until date, discount, additional charges, tax, grand total, CNY equivalent, cross-sheet checks.
- **Never fabricates** company / bank / HS code / weight / price data. Missing fields stay blank or use `[ ]` placeholders.
- **No-price mode**: when only parameters are given, unit prices stay blank and totals recalculate once filled.

**Standalone use** (no AI platform required):

```bash
pip install -r requirements.txt
python3 scripts/generate_quotation.py --input assets/example_input.json --output quotation.xlsx
```

`finalize.py` additionally requires the WorkBuddy `workbuddy-sheet-generation` plugin scripts plus LibreOffice; on other platforms simply open and re-save the workbook in Excel / WPS / LibreOffice to refresh formula caches.

**Rules of thumb**: look up the official central parity rate on the quotation date (CNY figures are reference only, settlement is in USD); never insert rows manually — change `items` and regenerate; replace all `[ ]` placeholders and delete the internal Guide sheet before sending to the buyer.

See [`references/quotation_spec.md`](./references/quotation_spec.md) for the complete input schema, row anchors and formula list. Licensed under MIT.
