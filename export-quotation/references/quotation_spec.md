# 输入数据规范与报价单结构

## 一、输入 JSON 字段表

`generate_quotation.py --input data.json` 读取。除 `items` 外全部可选；脚本会打印 `warnings` 列出所有自动兜底与待补项。

### 顶层

| 字段 | 类型 | 默认 / 说明 |
|---|---|---|
| `output` | string | 输出路径；命令行 `--output` 优先。缺省为当前目录 `出口报价单_YYYYMMDD.xlsx` |
| `title` | string | 工作簿属性标题 |
| `quotation_no` | string | 缺省自动 `QT-YYYYMMDD-001`，并提示按贵司编号规则调整 |
| `quote_date` | `YYYY-MM-DD` | 缺省今天（建议显式传，别让脚本猜） |
| `validity_days` | number | 默认 30；有效期至 = 报价日 + 天数 |
| `incoterm` | string | 默认 `FOB`；下拉含 Incoterms® 2020 十一项 |
| `port_of_loading` / `port_of_destination` | string | 装运港 / 目的港，缺省留空 |
| `payment_terms` / `shipment_mode` / `lead_time` | string | 付款方式 / 运输方式 / 交货期，缺省留空 |
| `currency` | string | 默认 `USD / 美元` |
| `rate` | number \| null | **USD→CNY 汇率，必须由调用方联网查当日官方中间价后传入**。缺省 `null` → I10 留空并告警，不得沿用历史值 |
| `rate_date` / `rate_source` | string | 汇率日期与来源，写进 Guide 第 37 行与 I10 批注 |
| `source_note` | string | 明细来源说明（中英双语），写在主表第 18 行；有缺项时脚本自动追加「N 项待填」提示 |
| `seller` / `buyer` / `bank` | object | 见下；缺省全部 `[ ]` 占位或留空，**不编造** |
| `discount_rate` / `tax_rate` | number | 0~1 比例，默认 0；填了会自动重算总计 |
| `additional_charges` | object | 六项费用，缺省全空：`packing` / `inland_freight` / `freight` / `insurance` / `customs` / `other` |
| `amount_in_words` | string | 英文大写金额，需人工核对，缺省留空 |
| `terms` | string[] | 覆盖默认 5 条中英对照条款 |
| `followups` | object[] | 客户诉求跟进：`original` / `interpretation` / `status` / `action`；Guide 页第 40 行起动态排布，带状态下拉 |
| `transcription_notes` | string | 手写歧义、涂改、同上引号展开等录入说明，写在跟进区下方 |
| `usage_notes` | string[] | 覆盖 Guide 页第 31 行起的填写说明，最多 6 条 |
| `items` | object[] | **必填，1~200 行**，见下 |

### `seller` 可选键

`banner`（A2 抬头，默认 `[贵公司中文名称]  /  [YOUR COMPANY NAME IN ENGLISH]`）、`header_line`（A3 整行）、`company` / `address` / `tel` / `email` / `web` / `contact`。
注意 C13 卖方公司名恒为公式 `=$A$2`，自动引用抬头，不要手填。

### `buyer` / `bank` 可选键

- buyer：`company` / `contact` / `tel` / `email` / `address`，写入 I13:I17。
- bank：`beneficiary` / `bank` / `usd_account` / `swift` / `bank_address`。

### `items` 每项（含别名兼容）

| 字段 | 别名 | 类型 | 说明 |
|---|---|---|---|
| `cn` | `name_cn` / `中文品名` / `name` | string | 中文品名 |
| `en` | `name_en` / `英文品名` / `description` | string | 英文品名；缺失会告警，双语要求必须补 |
| `spec` | `model` / `型号规格` / `model_spec` | string | 型号 / 规格 / 颜色，照录 |
| `hs` | `hs_code` / `HS编码` | string | HS 编码，资料没给就留空 |
| `qty` | `quantity` / `数量` | number \| null | 数量；允许 `"1,000"`、`"$7.85"` 这类字符串，脚本清洗 |
| `unit` | `单位` | string | 单位；缺失默认 `pcs` 并告警 |
| `price` | `unit_price` / `单价` | number \| null | USD 单价；`null` = 无单价模式 |
| `gw` | `gross_weight` / `毛重` | number \| null | 毛重 kg |
| `cbm` | `volume` / `体积` | number \| null | 体积 CBM |
| `remark` | `remarks` / `备注` | string | 原始备注，照录 |
| `comment` | `note` / `批注` | string | 写进该行 D 列单元格批注（歧义、待核对） |

## 二、12 列明细表（固定）

| 列 | 字段 | 列 | 字段 |
|---|---|---|---|
| A | 序号 No.（公式） | G | 单位 Unit（下拉） |
| B | 品名（中文） | H | 单价 USD（输入） |
| C | 英文品名 | I | 金额 USD（公式） |
| D | 型号 / 规格 / 颜色 | J | 毛重 kg（输入） |
| E | HS 编码（输入） | K | 体积 CBM（输入） |
| F | 数量 Qty（输入） | L | 备注 Remarks |

## 三、行锚点（全部由 `N = len(items)` 推导）

```
D0 = 20,  D1 = 20+N-1
TOTAL = D1+1,  CH_SEC = TOTAL+2,  GV = CH_SEC+1,  DR = GV+1,  DA = DR+1
F0 = DA+1,  F1 = F0+5,  ADD = F1+1,  TAXR = ADD+1,  TAXA = TAXR+1
GRAND = TAXA+1,  CNY_R = GRAND+1,  WORDS = CNY_R+1
BK_SEC → 银行 3 行 → TM_SEC → 条款 M 行 → SG_SEC → 签字 3 行 → FOOT
```

Guide 页 1~39 行固定（公式清单、汇率核算、常用选项、填写说明、色例），第 40 行起按 `followups` 数量动态排布。

## 四、公式清单（25~43 个，随行数变化）

| 位置 | 公式 | 作用 |
|---|---|---|
| `I6` | `=IF(OR($I$5="",$C$6=""),"",$I$5+$C$6)` | 有效期至 |
| `C13` | `=$A$2` | 卖方公司引用抬头 |
| `A{D0}:A{D1}` | `=IF(COUNTA(B{r}:C{r})=0,"",ROW()-19)` | 序号（填品名才显示） |
| `I{D0}:I{D1}` | `=IF(OR(F{r}="",H{r}=""),"",F{r}*H{r})` | 行金额 |
| `F/I/J/K{TOTAL}` | `=SUM(...)` | 数量、金额、毛重、体积合计 |
| `I{GV}` | `=I{TOTAL}` | 货值合计 |
| `I{DA}` | `=IF(OR($I${GV}="",$I${DR}=""),0,$I${GV}*$I${DR})` | 折扣金额 |
| `I{ADD}` | `=SUM(I{F0}:I{F1})` | 附加费小计 |
| `I{TAXA}` | `=IF(OR($I${GV}="",$I${TAXR}=""),0,($I${GV}-$I${DA}+$I${ADD})*$I${TAXR})` | 税额 |
| `I{GRAND}` | `=SUM(I{GV},I{ADD},I{TAXA})-SUM(I{DA})` | **GRAND TOTAL** |
| `I{CNY_R}` | `=IF(OR($I${GRAND}="",$I$10=""),"",$I${GRAND}*$I$10)` | CNY 参考 |
| Guide C19/C20/C21 | 引用主表 I10 / I{GRAND}、相乘 | 内部核算 |

所有公式都带空值保护；`SUM()` 会忽略返回 `""` 的单元格，不会出现 `#VALUE!`。

## 五、样式与数字格式

| 用途 | 色值 | 用途 | 格式 |
|---|---|---|---|
| 深蓝标题/总计 | `#2F5597` | 金额 USD | `$#,##0.00` |
| 蓝表头 | `#4472C4` | 单价 USD | `$#,##0.0000` |
| 浅蓝分区 | `#D9E2F3` | 数量/重量 | `#,##0.00` |
| 浅灰标签 | `#F2F5FA` | 折扣率/税率 | `0.00%` |
| **浅黄填写区** | `#FFF7E0` | 汇率 | `0.0000` |
| **浅蓝灰计算区** | `#EDF2F9` | 日期 | `yyyy-mm-dd` |
| 警示 | `#FFC7CE` / `#9C0006` | CNY 参考 | `¥#,##0.00` |

字体 Microsoft YaHei；A4 横向、fitToWidth=1 / fitToHeight=0、重复标题行 1:3、页脚 `EXPORT QUOTATION | Page &P of &N`。

## 六、下拉选项

- 贸易术语：EXW · FCA · FAS · FOB · CFR · CIF · CPT · CIP · DAP · DPU · DDP
- 付款方式：T/T 100% in advance · 30% deposit + 70% before shipment · 30% deposit + 70% against B/L copy · L/C at sight · L/C 30 days · D/P at sight · OA 30 days
- 运输方式：By Sea · By Air · By Express · By Rail · By Truck · Multimodal
- 单位：PCS · SET · CTN · BOX · KG · TON · M · M2 · M3 · L · ROLL · PALLET · PAIR · DOZEN · UNIT
- 跟进状态：Pending · Replied · In progress · Noted

## 七、双语术语速查（录入时常用）

| 中文 | English | 中文 | English |
|---|---|---|---|
| 品名 | Description / Item | 型号 | Model / Spec. |
| 数量 | Qty | 单价 | Unit Price |
| 金额 | Amount | 毛重 / 净重 | G.W. / N.W. |
| 体积 | Volume / CBM | 备注 | Remarks |
| 同上 | ditto / same as above | 最小起订量 | MOQ |
| 缓冲阻尼 | soft close | 锌合金 | zinc alloy |
| 不锈钢 304 | SS 304 | 彩盒 | color box |
| 中性出口包装 | neutral export packing | 交期 | Lead Time |
| 装运港 / 目的港 | Port of Loading / Destination | 付款方式 | Payment Terms |
| 报价单号 | Quotation No. | 有效期 | Validity |
| 授权签字 | Authorized Signature | 公司盖章 | Company Stamp |

## 八、无单价模式

客户只给产品参数、没给价格时：`price` 填 `null`，H 列留空，I 列公式返回空白，货值与总计暂为 0。脚本会在 `warnings` 和主表第 18 行提示「N 项单价／数量待填」。交付时必须明确告知用户：**填好单价后所有金额自动重算**，不要手工改公式，也不要替客户编造价格。
