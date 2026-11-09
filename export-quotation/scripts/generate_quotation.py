# -*- coding: utf-8 -*-
"""中英双语外贸出口报价单生成器（USD）。

从一份 JSON 数据文件生成完整报价单工作簿，明细行数、跟进清单行数全部由数据推导，
所有后续区块与公式引用按锚点动态计算，绝不原地插行。

用法:
    python3 generate_quotation.py --input data.json [--output out.xlsx]

JSON 字段规范见 ../references/quotation_spec.md 与 ../assets/example_input.json。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

try:
    import openpyxl
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "openpyxl>=3.1.0"])
    import openpyxl

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.properties import PageSetupProperties
from openpyxl.worksheet.page import PageMargins
from openpyxl.formatting.rule import CellIsRule
from openpyxl.comments import Comment
from openpyxl.utils import get_column_letter

# ---------------------------------------------------------------- 样式常量
def xl_color(css_hex: str) -> str:
    value = css_hex.removeprefix("#").upper()
    if len(value) != 6:
        raise ValueError(f"Expected #RRGGBB, got: {css_hex}")
    return "FF" + value

XL_WHITE      = xl_color("#FFFFFF")
XL_PRIMARY    = xl_color("#4472C4")
XL_DARK       = xl_color("#2F5597")
XL_SECTION    = xl_color("#D9E2F3")
XL_LABEL      = xl_color("#F2F5FA")
XL_INPUT      = xl_color("#FFF7E0")
XL_CALC       = xl_color("#EDF2F9")
XL_BORDER     = xl_color("#BFBFBF")
XL_TEXT       = xl_color("#1A1A1A")
XL_LABEL_TEXT = xl_color("#404040")
XL_MUTED      = xl_color("#6B7280")
XL_WARN_BG    = xl_color("#FFC7CE")
XL_WARN_FG    = xl_color("#9C0006")
XL_NOTE_BG    = xl_color("#FFF2CC")

FONT_NAME = "Microsoft YaHei"
THIN = Side(style="thin", color=XL_BORDER)
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

def F(size=9.5, bold=False, color=XL_TEXT, italic=False):
    return Font(name=FONT_NAME, size=size, bold=bold, color=color, italic=italic)

def fill(color):
    return PatternFill("solid", fgColor=color)

AL_LEFT   = Alignment(horizontal="left",   vertical="center", wrap_text=True,  indent=1)
AL_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
AL_RIGHT  = Alignment(horizontal="right",  vertical="center", wrap_text=False, indent=1)

FMT_USD, FMT_UPR = '$#,##0.00', '$#,##0.0000'
FMT_QTY, FMT_WT = '#,##0.00', '#,##0.00'
FMT_PCT, FMT_RATE, FMT_DATE, FMT_CNY = '0.00%', '0.0000', 'yyyy-mm-dd', '¥#,##0.00'

FILL_TITLE   = fill(XL_DARK)
FILL_HEADER  = fill(XL_PRIMARY)
FILL_SECTION = fill(XL_SECTION)
FILL_LBL     = fill(XL_LABEL)
FILL_IN      = fill(XL_INPUT)
FILL_CALC    = fill(XL_CALC)
FILL_TOTAL   = fill(XL_DARK)

def style_cell(c, *, font=None, fill_=None, align=None, border=None, numfmt=None):
    if font is not None:   c.font = font
    if fill_ is not None:  c.fill = fill_
    if align is not None:  c.alignment = align
    if border is not None: c.border = border
    if numfmt is not None: c.number_format = numfmt

def put(ws, coord, value=None, **kw):
    c = ws[coord]
    style_cell(c, **kw)
    if value is not None:
        c.value = value
    return c

def block(ws, rng, value=None, **kw):
    """合并区域并统一样式；rng 必须是多单元格范围，单格请用 put()。"""
    ws.merge_cells(rng)
    for row in ws[rng]:
        for c in row:
            style_cell(c, **kw)
    tl = ws[rng.split(":")[0]]
    if value is not None:
        tl.value = value
    return tl

def rh(ws, r, h):
    ws.row_dimensions[r].height = h

# ---------------------------------------------------------------- 数据整理
def pick(d: dict, *keys, default=None):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default

def to_num(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("$", "").replace("¥", "")
    for token in ("USD", "usd", "CNY", "元", "美元"):
        s = s.replace(token, "")
    s = s.strip()
    try:
        return float(s)
    except ValueError:
        return None

DEFAULT_TERMS = [
    "1. 价格与有效期：本报价以美元 (USD) 计价，自报价日起按上列有效天数生效。 / Prices are quoted in USD and valid for the period stated above.",
    "2. 贸易术语：按 Incoterms® 2020 解释；运费、保险费及目的港费用以实际发生为准。 / Trade terms are governed by Incoterms® 2020; freight, insurance and destination charges are subject to actual costs.",
    "3. 付款：请按约定付款方式将货款汇至上列美元账户，银行手续费由付款方承担。 / Payment shall be remitted to the designated USD account; all bank charges are for the payer's account.",
    "4. 交货与包装：收到定金或信用证后按约定交期发货，采用标准出口包装；彩盒等定制包装另行报价。 / Delivery as per the agreed lead time; standard neutral export packing, customized color-box packing quoted separately.",
    "5. 质量与争议：质量以双方确认的样品／规格为准；争议友好协商，协商不成提交 CIETAC 仲裁。本报价不构成合同，以双方签署的销售合同为准。 / Quality as per approved sample/specification; disputes settled amicably or by CIETAC arbitration. This quotation does not constitute a contract; the signed Sales Contract shall prevail.",
]

CHARGE_KEYS = [
    ("packing",         "包装费 / Packing Charges"),
    ("inland_freight",  "内陆运费 / Inland Freight"),
    ("freight",         "国际运费 / Ocean / Air Freight"),
    ("insurance",       "保险费 / Insurance"),
    ("customs",         "报关及杂费 / Customs & Misc."),
    ("other",           "其他费用 / Other Charges"),
]

def normalize(raw: dict) -> tuple[dict, list]:
    d = dict(raw)
    warnings = []
    qd = pick(d, "quote_date", "date", default=date.today().isoformat())
    try:
        date.fromisoformat(str(qd)[:10])
    except ValueError:
        warnings.append(f"quote_date '{qd}' 不是 YYYY-MM-DD，已改用今天")
        qd = date.today().isoformat()
    d["quote_date"] = str(qd)[:10]

    if not pick(d, "quotation_no"):
        d["quotation_no"] = "QT-" + d["quote_date"].replace("-", "") + "-001"
        warnings.append("报价单号未提供，已自动编号，请按贵司规则调整")

    d["validity_days"] = int(to_num(pick(d, "validity_days", "validity", default=30)) or 30)
    d["incoterm"] = pick(d, "incoterm", "incoterms", default="FOB")
    d["currency"] = pick(d, "currency", default="USD / 美元")
    rate = to_num(pick(d, "rate", "exchange_rate"))
    d["rate"] = rate
    if rate is None:
        warnings.append("汇率未提供：主表 I10 留空，请在生成前联网查询当日官方中间价并回填")
    d["rate_source"] = pick(d, "rate_source", "rate_note", default="")
    d["rate_date"] = pick(d, "rate_date", default=d["quote_date"])

    d["seller"] = pick(d, "seller", default={}) or {}
    d["buyer"] = pick(d, "buyer", default={}) or {}
    d["bank"] = pick(d, "bank", default={}) or {}

    items = []
    for i, it in enumerate(d.get("items") or [], start=1):
        qty = to_num(pick(it, "qty", "quantity", "数量"))
        price = to_num(pick(it, "price", "unit_price", "单价"))
        unit = pick(it, "unit", "单位", default=None)
        if unit is None:
            unit = "pcs"
            warnings.append(f"第 {i} 项单位未提供，已默认 pcs，请核对")
        en = pick(it, "en", "name_en", "英文品名", "description", default=None)
        if not en:
            warnings.append(f"第 {i} 项英文品名缺失，双语要求需补齐后重跑")
        if qty is None or price is None:
            warnings.append(f"第 {i} 项数量或单价缺失，金额留空（不编造数据）")
        items.append({
            "cn":      pick(it, "cn", "name_cn", "中文品名", "name", default="") or "",
            "en":      en or "",
            "spec":    pick(it, "spec", "model", "型号规格", "model_spec", default="") or "",
            "hs":      pick(it, "hs", "hs_code", "HS编码", default="") or "",
            "qty":     qty,
            "unit":    unit,
            "price":   price,
            "gw":      to_num(pick(it, "gw", "gross_weight", "毛重")),
            "cbm":     to_num(pick(it, "cbm", "volume", "体积")),
            "remark":  pick(it, "remark", "remarks", "备注", default="") or "",
            "comment": pick(it, "comment", "note", "批注", default="") or "",
        })
    if not items:
        raise ValueError("items 为空：本技能用于「按客户资料出报价单」，至少需要 1 行明细。若只需空白模板请直接复制 assets/ 中的版式基准文件。")
    if len(items) > 200:
        raise ValueError("items 超过 200 行，建议拆分为多份报价单")
    d["items"] = items

    d["discount_rate"] = to_num(pick(d, "discount_rate", "discount", default=0)) or 0
    d["tax_rate"] = to_num(pick(d, "tax_rate", "tax", default=0)) or 0
    charges = pick(d, "additional_charges", "charges", default={}) or {}
    d["additional_charges"] = {k: to_num(charges.get(k)) for k, _ in CHARGE_KEYS}
    terms = pick(d, "terms", default=None) or DEFAULT_TERMS
    d["terms"] = list(terms) if isinstance(terms, (list, tuple)) else [str(terms)]
    d["amount_in_words"] = pick(d, "amount_in_words", "words", default=None)
    d["followups"] = pick(d, "followups", "buyer_notes", default=[]) or []
    d["transcription_notes"] = pick(d, "transcription_notes", "ocr_notes", default="") or ""
    usage = pick(d, "usage_notes", default=None) or []
    d["usage_notes"] = (list(usage) if isinstance(usage, (list, tuple)) else [str(usage)])[:6]
    d["source_note"] = pick(d, "source_note", "source", default="") or ""
    return d, warnings

# ---------------------------------------------------------------- 主生成逻辑
def build(d: dict, out_path: str) -> dict:
    items = d["items"]
    N = len(items)
    D0 = 20
    D1 = D0 + N - 1
    TOTAL  = D1 + 1
    SP1    = TOTAL + 1
    CH_SEC = TOTAL + 2
    GV     = CH_SEC + 1
    DR     = GV + 1
    DA     = DR + 1
    F0     = DA + 1
    F1     = F0 + len(CHARGE_KEYS) - 1
    ADD    = F1 + 1
    TAXR   = ADD + 1
    TAXA   = TAXR + 1
    GRAND  = TAXA + 1
    CNY_R  = GRAND + 1
    WORDS  = CNY_R + 1
    SP2    = WORDS + 1
    BK_SEC = SP2 + 1
    BK1, BK2, BK3 = SP2 + 2, SP2 + 3, SP2 + 4
    SP3    = BK3 + 1
    TM_SEC = SP3 + 1
    TM0    = TM_SEC + 1
    SP4    = TM0 + len(d["terms"]) - 1 + 1
    SG_SEC = SP4 + 1
    SG0    = SG_SEC + 1
    FOOT   = SG0 + 3

    incomplete = sum(1 for it in items if it["qty"] is None or it["price"] is None)
    src = d["source_note"] or ("明细依据客户提供资料整理 / Items transcribed from buyer's supplied list.")
    if incomplete:
        src += f"　｜　注意：{incomplete} 项单价／数量待填 / NOTE: unit price or qty pending for {incomplete} item(s)."

    wb = Workbook()
    ws = wb.active
    ws.title = "报价单 Quotation"
    guide = wb.create_sheet("填写指引 Guide")

    # ==================== Sheet 1 ====================
    for col, w in {"A": 6.5, "B": 22, "C": 30, "D": 24, "E": 12, "F": 10,
                   "G": 9, "H": 14, "I": 15, "J": 12, "K": 12, "L": 28}.items():
        ws.column_dimensions[col].width = w
    ws.sheet_view.showGridLines = False
    ws.sheet_view.zoomScale = 85
    ws.sheet_properties.tabColor = XL_PRIMARY
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = "9"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_options.horizontalCentered = True
    ws.page_margins = PageMargins(left=0.3, right=0.3, top=0.45, bottom=0.45, header=0.15, footer=0.2)
    ws.print_area = f"A1:L{FOOT}"
    ws.print_title_rows = "1:3"
    ws.oddFooter.center.text = "EXPORT QUOTATION  |  Page &P of &N"
    ws.oddFooter.center.size = 8

    banner = pick(d["seller"], "banner", "company", "name",
                  default="[贵公司中文名称]  /  [YOUR COMPANY NAME IN ENGLISH]")
    head_line = pick(d["seller"], "header_line", "address_line", default=None)
    if not head_line:
        head_line = (f"地址 Address: {pick(d['seller'], 'address', default='[Company Address]')}    "
                     f"电话 Tel: {pick(d['seller'], 'tel', default='[+86-...]')}    "
                     f"邮箱 Email: {pick(d['seller'], 'email', default='[sales@...]')}    "
                     f"网址 Web: {pick(d['seller'], 'web', default='[www...]')}")
    block(ws, "A1:L1", "出口报价单  /  EXPORT QUOTATION",
          font=F(18, True, XL_WHITE), fill_=FILL_TITLE, align=AL_CENTER)
    block(ws, "A2:L2", banner, font=F(11, True, XL_DARK), fill_=FILL_SECTION, align=AL_CENTER)
    block(ws, "A3:L3", head_line, font=F(8.5, False, XL_LABEL_TEXT), fill_=FILL_LBL, align=AL_CENTER)
    for r, h in [(1, 36), (2, 22), (3, 19), (4, 6)]:
        rh(ws, r, h)

    meta = [
        (5,  "报价单号 / Quotation No.",      d["quotation_no"],   "报价日期 / Date",                  None),
        (6,  "有效期 / Validity (Days)",      d["validity_days"],  "有效期至 / Valid Until",          None),
        (7,  "贸易术语 / Incoterms® 2020",   d["incoterm"],       "目的港 / Port of Destination",   pick(d, "port_of_destination")),
        (8,  "装运港 / Port of Loading",     pick(d, "port_of_loading"), "交货期 / Lead Time",       pick(d, "lead_time")),
        (9,  "付款方式 / Payment Terms",     pick(d, "payment_terms"), "运输方式 / Shipment Mode",   pick(d, "shipment_mode")),
        (10, "报价币种 / Currency",          d["currency"],       "汇率 / Rate (USD → CNY)",        d["rate"]),
    ]
    for r, l1, v1, l2, v2 in meta:
        block(ws, f"A{r}:B{r}", l1, font=F(9, True, XL_LABEL_TEXT), fill_=FILL_LBL, align=AL_LEFT, border=BORDER)
        block(ws, f"C{r}:F{r}", None, font=F(9.5), fill_=FILL_IN, align=AL_LEFT, border=BORDER)
        block(ws, f"G{r}:H{r}", l2, font=F(9, True, XL_LABEL_TEXT), fill_=FILL_LBL, align=AL_LEFT, border=BORDER)
        block(ws, f"I{r}:L{r}", None, font=F(9.5), fill_=FILL_IN, align=AL_LEFT, border=BORDER)
        if v1 is not None: put(ws, f"C{r}", v1)
        if v2 is not None: put(ws, f"I{r}", v2, align=AL_RIGHT)
        rh(ws, r, 22)
    put(ws, "I5", date.fromisoformat(d["quote_date"]), numfmt=FMT_DATE, align=AL_RIGHT)
    block(ws, "I6:L6", '=IF(OR($I$5="",$C$6=""),"",$I$5+$C$6)',
          font=F(9.5, True, XL_DARK), fill_=FILL_CALC, align=AL_RIGHT, border=BORDER, numfmt=FMT_DATE)
    block(ws, "C10:F10", d["currency"], font=F(9.5, True, XL_DARK), fill_=FILL_CALC, align=AL_LEFT, border=BORDER)
    if d["rate"] is not None:
        put(ws, "I10", d["rate"], numfmt=FMT_RATE, align=AL_RIGHT)
    rh(ws, 11, 6)

    # 买卖双方
    block(ws, "A12:F12", "卖方 / SELLER (EXPORTER)", font=F(10, True, XL_WHITE), fill_=FILL_HEADER, align=AL_CENTER, border=BORDER)
    block(ws, "G12:L12", "买方 / BUYER (IMPORTER)",  font=F(10, True, XL_WHITE), fill_=FILL_HEADER, align=AL_CENTER, border=BORDER)
    rh(ws, 12, 21)
    party = [
        (13, "公司 / Company",   "公司 / Company"),
        (14, "联系人 / Contact", "联系人 / Attn."),
        (15, "电话 / Tel",       "电话 / Tel"),
        (16, "邮箱 / Email",     "邮箱 / Email"),
        (17, "地址 / Address",   "地址 / Address"),
    ]
    buyer_keys = {13: "company", 14: "contact", 15: "tel", 16: "email", 17: "address"}
    for r, l1, l2 in party:
        block(ws, f"A{r}:B{r}", l1, font=F(9, True, XL_LABEL_TEXT), fill_=FILL_LBL, align=AL_LEFT, border=BORDER)
        block(ws, f"C{r}:F{r}", None, font=F(9.5), fill_=FILL_IN, align=AL_LEFT, border=BORDER)
        block(ws, f"G{r}:H{r}", l2, font=F(9, True, XL_LABEL_TEXT), fill_=FILL_LBL, align=AL_LEFT, border=BORDER)
        block(ws, f"I{r}:L{r}", None, font=F(9.5), fill_=FILL_IN, align=AL_LEFT, border=BORDER)
        bv = pick(d["buyer"], buyer_keys[r])
        if bv: put(ws, f"I{r}", bv)
        sv = pick(d["seller"], buyer_keys[r])
        if sv and r != 13: put(ws, f"C{r}", sv)
        rh(ws, r, 22)
    block(ws, "C13:F13", '=$A$2', font=F(9.5, True, XL_DARK), fill_=FILL_CALC, align=AL_LEFT, border=BORDER)

    block(ws, "A18:L18", src,
          font=F(8.5, False, XL_MUTED, italic=True), fill_=FILL_LBL, align=AL_CENTER, border=BORDER)
    rh(ws, 18, 20)

    # 明细表
    headers = [
        "序号\nNo.", "品名（中文）\nItem (CN)", "英文品名\nDescription (EN)",
        "型号 / 规格 / 颜色\nModel / Specs / Color", "HS 编码\nHS Code", "数量\nQty", "单位\nUnit",
        "单价 (USD)\nUnit Price", "金额 (USD)\nAmount", "毛重 (kg)\nG.W.",
        "体积 (CBM)\nVolume", "备注\nRemarks",
    ]
    for i, h in enumerate(headers, start=1):
        put(ws, f"{get_column_letter(i)}19", h,
            font=F(9, True, XL_WHITE), fill_=FILL_HEADER, align=AL_CENTER, border=BORDER)
    rh(ws, 19, 40)

    for idx, it in enumerate(items):
        r = D0 + idx
        for col in range(1, 13):
            put(ws, f"{get_column_letter(col)}{r}", None,
                font=F(9.5), fill_=FILL_IN, align=AL_LEFT, border=BORDER)
        put(ws, f"B{r}", it["cn"])
        put(ws, f"C{r}", it["en"])
        put(ws, f"D{r}", it["spec"])
        put(ws, f"E{r}", it["hs"] or None, align=AL_CENTER)
        put(ws, f"F{r}", it["qty"], align=AL_RIGHT, numfmt=FMT_QTY)
        put(ws, f"G{r}", it["unit"], align=AL_CENTER)
        put(ws, f"H{r}", it["price"], align=AL_RIGHT, numfmt=FMT_UPR)
        put(ws, f"J{r}", it["gw"], align=AL_RIGHT, numfmt=FMT_WT)
        put(ws, f"K{r}", it["cbm"], align=AL_RIGHT, numfmt=FMT_WT)
        put(ws, f"L{r}", it["remark"])
        put(ws, f"A{r}", f'=IF(COUNTA(B{r}:C{r})=0,"",ROW()-{D0 - 1})',
            font=F(9.5, True, XL_DARK), fill_=FILL_CALC, align=AL_CENTER, border=BORDER)
        put(ws, f"I{r}", f'=IF(OR(F{r}="",H{r}=""),"",F{r}*H{r})',
            font=F(9.5, True, XL_DARK), fill_=FILL_CALC, align=AL_RIGHT,
            border=BORDER, numfmt=FMT_USD)
        # 长文本不设固定行高，由 wrapText 自动撑高
        if it["comment"]:
            cm = Comment(it["comment"], "WorkBuddy")
            cm.width, cm.height = 340, 95
            ws[f"D{r}"].comment = cm

    block(ws, f"A{TOTAL}:E{TOTAL}", "合计  /  TOTAL", font=F(10, True, XL_WHITE),
          fill_=FILL_TOTAL, align=AL_LEFT, border=BORDER)
    for col in "FGHIJKL":
        put(ws, f"{col}{TOTAL}", None, font=F(9.5, True, XL_WHITE),
            fill_=FILL_TOTAL, align=AL_RIGHT, border=BORDER)
    put(ws, f"F{TOTAL}", f"=SUM(F{D0}:F{D1})", numfmt=FMT_QTY)
    put(ws, f"I{TOTAL}", f"=SUM(I{D0}:I{D1})", numfmt=FMT_USD)
    put(ws, f"J{TOTAL}", f"=SUM(J{D0}:J{D1})", numfmt=FMT_WT)
    put(ws, f"K{TOTAL}", f"=SUM(K{D0}:K{D1})", numfmt=FMT_WT)
    rh(ws, TOTAL, 22)
    rh(ws, SP1, 6)

    # 费用与总计
    block(ws, f"A{CH_SEC}:L{CH_SEC}", "费用与总计  /  CHARGES & GRAND TOTAL (USD)",
          font=F(10, True, XL_DARK), fill_=FILL_SECTION, align=AL_LEFT, border=BORDER)
    rh(ws, CH_SEC, 22)
    charges = [
        (GV,  "货值合计 / Goods Value",                  f"=I{TOTAL}", True, FMT_USD),
        (DR,  "折扣率 / Discount Rate",                  d["discount_rate"], False, FMT_PCT),
        (DA,  "折扣金额 / Discount Amount",              f'=IF(OR($I${GV}="",$I${DR}=""),0,$I${GV}*$I${DR})', True, FMT_USD),
    ]
    for i, (key, label) in enumerate(CHARGE_KEYS):
        charges.append((F0 + i, label, d["additional_charges"][key], False, FMT_USD))
    charges += [
        (ADD,  "附加费小计 / Total Additional Charges",  f"=SUM(I{F0}:I{F1})", True, FMT_USD),
        (TAXR, "税率 / VAT / Tax Rate",                   d["tax_rate"], False, FMT_PCT),
        (TAXA, "税额 / Tax Amount",                      f'=IF(OR($I${GV}="",$I${TAXR}=""),0,($I${GV}-$I${DA}+$I${ADD})*$I${TAXR})', True, FMT_USD),
    ]
    for r, label, val, is_calc, fmt in charges:
        block(ws, f"A{r}:H{r}", label,
              font=F(9, bool(is_calc), XL_DARK if is_calc else XL_LABEL_TEXT),
              fill_=FILL_LBL, align=AL_LEFT, border=BORDER)
        block(ws, f"I{r}:L{r}", None,
              font=F(9.5, bool(is_calc), XL_DARK if is_calc else XL_TEXT),
              fill_=FILL_CALC if is_calc else FILL_IN,
              align=AL_RIGHT, border=BORDER, numfmt=fmt)
        if val is not None: put(ws, f"I{r}", val, align=AL_RIGHT, numfmt=fmt)
        rh(ws, r, 19)

    block(ws, f"A{GRAND}:H{GRAND}", "总计  /  GRAND TOTAL (USD)",
          font=F(12, True, XL_WHITE), fill_=FILL_TOTAL, align=AL_LEFT, border=BORDER)
    block(ws, f"I{GRAND}:L{GRAND}", f"=SUM(I{GV},I{ADD},I{TAXA})-SUM(I{DA})",
          font=F(12, True, XL_WHITE), fill_=FILL_TOTAL, align=AL_RIGHT, border=BORDER, numfmt=FMT_USD)
    rh(ws, GRAND, 27)
    block(ws, f"A{CNY_R}:H{CNY_R}", "人民币参考金额 / CNY Equivalent (For Reference Only)",
          font=F(9, False, XL_LABEL_TEXT), fill_=FILL_LBL, align=AL_LEFT, border=BORDER)
    block(ws, f"I{CNY_R}:L{CNY_R}", f'=IF(OR($I${GRAND}="",$I$10=""),"",$I${GRAND}*$I$10)',
          font=F(9.5, True, XL_DARK), fill_=FILL_CALC, align=AL_RIGHT, border=BORDER, numfmt=FMT_CNY)
    rh(ws, CNY_R, 19)
    block(ws, f"A{WORDS}:H{WORDS}", "金额大写 / Total Amount in Words (USD)",
          font=F(9, False, XL_LABEL_TEXT), fill_=FILL_LBL, align=AL_LEFT, border=BORDER)
    block(ws, f"I{WORDS}:L{WORDS}", d["amount_in_words"],
          font=F(9.5), fill_=FILL_IN, align=AL_LEFT, border=BORDER)
    rh(ws, WORDS, 19)
    rh(ws, SP2, 6)

    # 银行信息
    block(ws, f"A{BK_SEC}:L{BK_SEC}", "收款银行信息  /  BANK DETAILS (USD)",
          font=F(10, True, XL_DARK), fill_=FILL_SECTION, align=AL_LEFT, border=BORDER)
    rh(ws, BK_SEC, 22)
    for r, l1, l2, k1, k2 in [
        (BK1, "受益人 / Beneficiary",   "开户行 / Beneficiary Bank", "beneficiary", "bank"),
        (BK2, "美元账号 / USD A/C No.", "SWIFT / BIC",               "usd_account", "swift"),
    ]:
        block(ws, f"A{r}:B{r}", l1, font=F(9, True, XL_LABEL_TEXT), fill_=FILL_LBL, align=AL_LEFT, border=BORDER)
        block(ws, f"C{r}:F{r}", None, font=F(9.5), fill_=FILL_IN, align=AL_LEFT, border=BORDER)
        block(ws, f"G{r}:H{r}", l2, font=F(9, True, XL_LABEL_TEXT), fill_=FILL_LBL, align=AL_LEFT, border=BORDER)
        block(ws, f"I{r}:L{r}", None, font=F(9.5), fill_=FILL_IN, align=AL_LEFT, border=BORDER)
        if pick(d["bank"], k1): put(ws, f"C{r}", d["bank"][k1])
        if pick(d["bank"], k2): put(ws, f"I{r}", d["bank"][k2])
        rh(ws, r, 21)
    block(ws, f"A{BK3}:B{BK3}", "银行地址 / Bank Address", font=F(9, True, XL_LABEL_TEXT), fill_=FILL_LBL, align=AL_LEFT, border=BORDER)
    block(ws, f"C{BK3}:L{BK3}", pick(d["bank"], "bank_address"), font=F(9.5), fill_=FILL_IN, align=AL_LEFT, border=BORDER)
    rh(ws, BK3, 21)
    rh(ws, SP3, 6)

    # 条款
    block(ws, f"A{TM_SEC}:L{TM_SEC}", "备注与条款  /  REMARKS & TERMS",
          font=F(10, True, XL_DARK), fill_=FILL_SECTION, align=AL_LEFT, border=BORDER)
    rh(ws, TM_SEC, 22)
    for i, t in enumerate(d["terms"]):
        block(ws, f"A{TM0+i}:L{TM0+i}", t, font=F(8.5), fill_=fill(XL_WHITE), align=AL_LEFT, border=BORDER)
    rh(ws, SP4, 6)

    # 签字
    block(ws, f"A{SG_SEC}:F{SG_SEC}", "卖方确认 / CONFIRMED BY SELLER", font=F(10, True, XL_WHITE), fill_=FILL_HEADER, align=AL_CENTER, border=BORDER)
    block(ws, f"G{SG_SEC}:L{SG_SEC}", "买方确认 / ACCEPTED BY BUYER",  font=F(10, True, XL_WHITE), fill_=FILL_HEADER, align=AL_CENTER, border=BORDER)
    rh(ws, SG_SEC, 21)
    sig = [
        "授权签字 / Authorized Signature:  ____________________",
        "职务 / Title:  ______________    日期 / Date:  ______________",
        "公司盖章 / Company Stamp:  ____________________",
    ]
    for i, t in enumerate(sig):
        r = SG0 + i
        block(ws, f"A{r}:F{r}", t, font=F(9), fill_=FILL_LBL, align=AL_LEFT, border=BORDER)
        block(ws, f"G{r}:L{r}", t, font=F(9), fill_=FILL_LBL, align=AL_LEFT, border=BORDER)
        rh(ws, r, 24)
    block(ws, f"A{FOOT}:L{FOOT}",
          "感谢您的询盘，期待与贵司合作！  /  Thank you for your inquiry. We look forward to a long-term cooperation.",
          font=F(9, True, XL_DARK, italic=True), fill_=FILL_SECTION, align=AL_CENTER, border=BORDER)
    rh(ws, FOOT, 22)

    # 批注
    def note(coord, text, w=340, h=95):
        cm = Comment(text, "WorkBuddy")
        cm.width, cm.height = w, h
        ws[coord].comment = cm

    note("C5", "自动编号，请按贵司编号规则调整。 / Auto-numbered; adjust to your own numbering rule.")
    note("I5", "请按实际报价日期更新；有效期至由本日期 + 有效天数自动计算。 / Update to the actual quotation date.")
    rate_txt = (d["rate_source"] or "请填入当日官方中间价（如中国外汇交易中心人民币汇率中间价）")
    note("I10", f"USD → CNY 参考汇率，来源：{rate_txt}（{d['rate_date']}）。请按报价日更新；结算以 USD 金额为准。 / Reference rate; settlement is in USD.")
    note("C7", "贸易术语默认 FOB，请与客户确认后修改。 / Default FOB; confirm with the buyer.")
    note(f"I{DR}", "请输入 0~1 之间的比例（如 5%）；如需让利请在此填折扣率，总计自动重算。 / Enter a percentage 0~1 to apply a discount.")
    note(f"I{TAXR}", "出口零税率业务填 0%；税额自动计算。 / Use 0% for zero-rated export sales.")
    note(f"I{WORDS}", "英文大写金额需手工填写并核对，例：SAY US DOLLARS THREE THOUSAND FIVE HUNDRED FORTY TWO ONLY.")
    if incomplete:
        note(f"H{D0}", "部分单价／数量待填，填写后金额、合计与总计会自动重算。 / Fill in pending prices or quantities; all totals recalculate automatically.")

    # 数据验证
    def list_dv(cells, opts, prompt):
        dv = DataValidation(type="list", formula1='"' + ",".join(opts) + '"',
                            allow_blank=True, showDropDown=False)
        dv.showErrorMessage = True
        dv.errorTitle = "输入无效 / Invalid entry"
        dv.error = "请从下拉列表中选择。 / Please select from the drop-down list."
        dv.showInputMessage = True
        dv.promptTitle = "填写提示 / Hint"
        dv.prompt = prompt
        ws.add_data_validation(dv)
        for c in cells: dv.add(c)

    def num_dv(cells, operator, f1, f2=None):
        dv = DataValidation(type="decimal", operator=operator, formula1=f1,
                            formula2=f2, allow_blank=True)
        dv.showErrorMessage = True
        dv.errorTitle = "输入无效 / Invalid entry"
        dv.error = "请输入有效的非负数或比例。 / Please enter a valid number."
        ws.add_data_validation(dv)
        for c in cells: dv.add(c)

    list_dv(["C7"], ["EXW", "FCA", "FAS", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP"], "贸易术语 / Incoterms® 2020")
    list_dv(["C9"], ["T/T 100% in advance", "30% T/T deposit + 70% before shipment",
                     "30% T/T deposit + 70% against B/L copy", "L/C at sight",
                     "L/C 30 days", "D/P at sight", "OA 30 days"], "付款方式 / Payment Terms")
    list_dv(["I9"], ["By Sea", "By Air", "By Express", "By Rail", "By Truck", "Multimodal"], "运输方式 / Shipment Mode")
    list_dv([f"G{r}" for r in range(D0, D1 + 1)],
            ["PCS", "SET", "CTN", "BOX", "KG", "TON", "M", "M2", "M3", "L",
             "ROLL", "PALLET", "PAIR", "DOZEN", "UNIT"], "计量单位 / Unit")
    num_dv([f"{c}{r}" for r in range(D0, D1 + 1) for c in "FHJK"] +
           [f"I{r}" for r in range(F0, F1 + 1)], "greaterThanOrEqual", "0")
    num_dv([f"I{DR}", f"I{TAXR}"], "between", "0", "1")
    num_dv(["C6"], "greaterThanOrEqual", "1")
    num_dv(["I10"], "greaterThan", "0")

    warn_fill, warn_font = fill(XL_WARN_BG), F(9.5, True, XL_WARN_FG)
    ws.conditional_formatting.add(f"I{D0}:I{D1}",
        CellIsRule(operator="lessThan", formula=["0"], fill=warn_fill, font=warn_font))
    for rng in [f"I{DR}", f"I{TAXR}"]:
        ws.conditional_formatting.add(rng,
            CellIsRule(operator="greaterThan", formula=["1"], fill=warn_fill, font=warn_font))
    ws.conditional_formatting.add(f"I{GRAND}",
        CellIsRule(operator="lessThan", formula=["0"], fill=warn_fill, font=warn_font))

    # ==================== Sheet 2：填写指引 ====================
    for col, w in {"A": 8, "B": 30, "C": 46, "D": 24, "E": 18, "F": 34}.items():
        guide.column_dimensions[col].width = w
    guide.sheet_view.showGridLines = False
    guide.sheet_view.zoomScale = 95
    guide.sheet_properties.tabColor = XL_DARK
    guide.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    guide.page_setup.orientation = "landscape"
    guide.page_setup.paperSize = "9"
    guide.page_setup.fitToWidth = 1
    guide.page_setup.fitToHeight = 0

    has_follow = bool(d["followups"])
    has_notes = bool(d["transcription_notes"])
    block(guide, "A1:F1", "使用说明、参数与客户要求跟进  /  NOTES, PARAMETERS & BUYER FOLLOW-UP",
          font=F(16, True, XL_WHITE), fill_=FILL_TITLE, align=AL_CENTER)
    rh(guide, 1, 34)
    lead = ("本页含内部填写指引与客户诉求转写（第 40 行起），发送客户前建议删除本工作表。 / Internal guide and buyer notes (from row 40) — recommend removing this sheet before sending."
            if has_follow or has_notes else
            "本页为内部填写指引，发送客户前建议删除本工作表。 / Internal guide — recommend removing this sheet before sending.")
    block(guide, "A2:F2", lead, font=F(9, False, XL_DARK), fill_=fill(XL_NOTE_BG), align=AL_CENTER)
    rh(guide, 2, 30)
    rh(guide, 3, 7)

    def g_section(r, text):
        block(guide, f"A{r}:F{r}", text, font=F(10.5, True, XL_DARK),
              fill_=FILL_SECTION, align=AL_LEFT, border=BORDER)
        rh(guide, r, 23)

    def g_row(r, left, right, *, h=None):
        block(guide, f"A{r}:B{r}", left, font=F(9, True, XL_LABEL_TEXT),
              fill_=FILL_LBL, align=AL_LEFT, border=BORDER)
        block(guide, f"C{r}:F{r}", right, font=F(9), fill_=fill(XL_WHITE),
              align=AL_LEFT, border=BORDER)
        if h: rh(guide, r, h)

    g_section(4, "一、自动计算公式  /  AUTOMATIC FORMULAS（浅蓝灰单元格，请勿覆盖）")
    block(guide, "A5:B5", "单元格 / Cells", font=F(9, True, XL_WHITE), fill_=FILL_HEADER, align=AL_CENTER, border=BORDER)
    block(guide, "C5:F5", "计算逻辑 / Formula logic", font=F(9, True, XL_WHITE), fill_=FILL_HEADER, align=AL_CENTER, border=BORDER)
    rh(guide, 5, 21)
    formulas = [
        (f"A{D0}:A{D1}", "序号：填写品名后自动生成 / Item No. appears once a product name is entered"),
        (f"I{D0}:I{D1}", "行金额 = 数量 × 单价 / Amount = Qty × Unit Price"),
        (f"F{TOTAL} / I{TOTAL} / J{TOTAL} / K{TOTAL}", "数量、金额、毛重、体积合计 / Totals of Qty, Amount, G.W. and Volume"),
        ("I6", "有效期至 = 报价日期 + 有效天数 / Valid Until = Date + Validity Days"),
        (f"I{GV}", "货值合计，引用明细合计 / Goods Value, linked to the item total"),
        (f"I{DA}", "折扣金额 = 货值 × 折扣率 / Discount = Goods Value × Discount Rate"),
        (f"I{ADD}", f"附加费小计 = SUM(I{F0}:I{F1}) / Sum of additional charges"),
        (f"I{TAXA}", "税额 = (货值 − 折扣 + 附加费) × 税率 / Tax Amount"),
        (f"I{GRAND}", "总计 = 货值 − 折扣 + 附加费 + 税额 / GRAND TOTAL (USD)"),
        (f"I{CNY_R}", "人民币参考 = 总计 × 汇率 / CNY reference = Total × Rate (reference only)"),
    ]
    for i, (cell, desc) in enumerate(formulas):
        g_row(6 + i, cell, desc)

    g_section(17, "二、汇率与内部核算  /  EXCHANGE RATE & REFERENCE CONVERSION")
    for rng, val in [("A18:B18", "项目 / Item"), ("C18:D18", "数值 / Value"), ("E18:F18", "说明 / Note")]:
        block(guide, rng, val, font=F(9, True, XL_WHITE), fill_=FILL_HEADER, align=AL_CENTER, border=BORDER)
    rh(guide, 18, 21)

    def g_calc(r, label, formula, explanation, numfmt):
        block(guide, f"A{r}:B{r}", label, font=F(9, True, XL_LABEL_TEXT), fill_=FILL_LBL, align=AL_LEFT, border=BORDER)
        block(guide, f"C{r}:D{r}", formula, font=F(9.5, True, XL_DARK), fill_=FILL_CALC,
              align=AL_RIGHT, border=BORDER, numfmt=numfmt)
        block(guide, f"E{r}:F{r}", explanation, font=F(8.5), fill_=fill(XL_WHITE), align=AL_LEFT, border=BORDER)
        rh(guide, r, 25)

    g_calc(19, "USD → CNY 参考汇率 / Reference Rate", "='报价单 Quotation'!I10",
           "请按报价日更新为当日官方中间价 / Update to the official central parity on the quotation date", FMT_RATE)
    g_calc(20, "报价总额 / Quotation Total (USD)", f"='报价单 Quotation'!I{GRAND}",
           "引用主表总计 / Linked to GRAND TOTAL", FMT_USD)
    g_calc(21, "人民币参考金额 / CNY Equivalent", '=IF(OR($C$19="",$C$20=""),"",$C$20*$C$19)',
           "仅供参考，结算一律以 USD 为准 / For reference only; settlement is in USD", FMT_CNY)
    rh(guide, 22, 7)

    g_section(23, "三、常用选项  /  COMMON OPTIONS")
    block(guide, "A24:B24", "类别 / Category", font=F(9, True, XL_WHITE), fill_=FILL_HEADER, align=AL_CENTER, border=BORDER)
    block(guide, "C24:F24", "可选项 / Options", font=F(9, True, XL_WHITE), fill_=FILL_HEADER, align=AL_CENTER, border=BORDER)
    rh(guide, 24, 21)
    for i, (k, v) in enumerate([
        ("贸易术语 / Incoterms® 2020", "EXW · FCA · FAS · FOB · CFR · CIF · CPT · CIP · DAP · DPU · DDP"),
        ("付款方式 / Payment Terms", "T/T 100% in advance · 30% deposit + 70% before shipment · L/C at sight · D/P · OA"),
        ("运输方式 / Shipment Mode", "By Sea · By Air · By Express · By Rail · By Truck · Multimodal"),
        ("计量单位 / Units", "PCS · SET · CTN · BOX · KG · TON · M · M2 · M3 · L · ROLL · PALLET · PAIR · DOZEN"),
    ]):
        g_row(25 + i, k, v)
    rh(guide, 29, 7)

    g_section(30, "四、填写与使用说明  /  HOW TO USE")
    default_usage = [
        "1. 浅黄色单元格为填写区；浅蓝灰单元格为公式自动计算，请勿手动覆盖。 / Yellow cells are input fields; light blue cells are formula-driven.",
        f"2. 明细区共 {N} 行（第 {D0}~{D1} 行）。如需增减，请修改输入 JSON 的 items 后重新生成，切勿手工插行（公式引用会错位）。 / {N} item rows; regenerate from JSON instead of inserting rows manually.",
        "3. 发送客户前，请把 [ ] 占位内容替换为贵司真实信息，核对银行账号、SWIFT、贸易术语与付款方式。 / Replace all [ ] placeholders and verify bank details, Incoterms and payment terms.",
        "4. 单价按客户资料原样录入；如需让利请在折扣率栏填 0~1 的比例，总计与人民币参考会自动重算。 / Unit prices are transcribed as-is; enter a discount rate if you concede price.",
        "5. HS 编码、毛重、体积等资料未提供的一律留空，报价前请补齐以便核算运费与报关。 / Fill in HS codes, G.W. and CBM before quoting freight and customs.",
    ]
    usage = d["usage_notes"] or default_usage
    for i, t in enumerate(usage):
        block(guide, f"A{31+i}:F{31+i}", t, font=F(9), fill_=fill(XL_WHITE), align=AL_LEFT, border=BORDER)
    rate_line = (f"汇率来源 / Source: {d['rate_source']}（{d['rate_date']}），1 USD = {d['rate']} CNY。"
                 if d["rate_source"] and d["rate"] is not None else
                 "汇率来源 / Source: 请在主表 I10 填入报价当日官方中间价并在此注明来源与日期；结算以 USD 为准。 / Fill in the official central parity on the quotation date and note its source.")
    block(guide, "A37:F37", rate_line, font=F(8.5, False, XL_MUTED), fill_=FILL_LBL, align=AL_LEFT, border=BORDER)
    rh(guide, 37, 20)
    block(guide, "A38:F38",
          "浅黄色 = 填写  |  浅蓝灰 = 自动计算  |  深蓝 = 表头与总计     Yellow = Input  |  Light blue = Formula  |  Dark blue = Header & Total",
          font=F(9, True, XL_DARK), fill_=FILL_SECTION, align=AL_CENTER, border=BORDER)
    rh(guide, 38, 22)
    rh(guide, 39, 7)

    guide_last = 38
    if has_follow or has_notes:
        g_section(40, "五、客户诉求与录入说明  /  BUYER NOTES & TRANSCRIPTION（内部 / INTERNAL）")
        r = 41
        if has_follow:
            for rng, val in [("A41:B41", "原文 / Original note"), ("C41:D41", "中文整理 / Interpretation")]:
                block(guide, rng, val, font=F(9, True, XL_WHITE), fill_=FILL_HEADER, align=AL_CENTER, border=BORDER)
            for coord, val in [("E41", "状态 / Status"), ("F41", "跟进动作 / Action")]:
                put(guide, coord, val, font=F(9, True, XL_WHITE), fill_=FILL_HEADER, align=AL_CENTER, border=BORDER)
            rh(guide, 41, 21)
            dv_status = DataValidation(type="list", formula1='"Pending,Replied,In progress,Noted"', allow_blank=True)
            dv_status.showErrorMessage = True
            guide.add_data_validation(dv_status)
            for i, f in enumerate(d["followups"]):
                rr = 42 + i
                block(guide, f"A{rr}:B{rr}", pick(f, "original", "原文", default=""),
                      font=F(9, False, XL_TEXT), fill_=FILL_LBL, align=AL_LEFT, border=BORDER)
                block(guide, f"C{rr}:D{rr}", pick(f, "interpretation", "中文", default=""),
                      font=F(9), fill_=fill(XL_WHITE), align=AL_LEFT, border=BORDER)
                put(guide, f"E{rr}", pick(f, "status", default="Pending"),
                    font=F(9, True, XL_DARK), fill_=FILL_IN, align=AL_CENTER, border=BORDER)
                put(guide, f"F{rr}", pick(f, "action", "跟进", default=""),
                    font=F(9), fill_=fill(XL_WHITE), align=AL_LEFT, border=BORDER)
                dv_status.add(f"E{rr}")
            r = 42 + len(d["followups"])
        if has_notes:
            block(guide, f"A{r}:F{r}", d["transcription_notes"],
                  font=F(8.5, False, XL_LABEL_TEXT), fill_=fill(XL_NOTE_BG), align=AL_LEFT, border=BORDER)
            rh(guide, r, 42)
            r += 1
        block(guide, f"A{r}:F{r}",
              "本区内容为客户内部跟进事项，请勿随报价单一并发送给客户  /  Internal follow-up list — do not send to the buyer.",
              font=F(9, True, XL_WARN_FG), fill_=fill(XL_WARN_BG), align=AL_CENTER, border=BORDER)
        rh(guide, r, 22)
        guide_last = r
    guide.print_area = f"A1:F{guide_last}"

    # 工作簿属性
    wb.properties.title = pick(d, "title", default=f"出口报价单 {d['quotation_no']}")
    wb.properties.subject = f"Bilingual export quotation (USD), {N} items"
    wb.properties.creator = "WorkBuddy"
    wb.properties.description = f"中英双语 USD 出口报价单，{N} 项明细，含自动计算公式与汇率参考。生成于 {datetime.now():%Y-%m-%d %H:%M}。"

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)

    goods_value = sum((it["qty"] or 0) * (it["price"] or 0) for it in items)
    discount = goods_value * d["discount_rate"]
    add = sum(v or 0 for v in d["additional_charges"].values())
    tax = (goods_value - discount + add) * d["tax_rate"]
    grand = goods_value - discount + add + tax
    return {
        "output": out_path,
        "item_count": N,
        "incomplete_rows": incomplete,
        "anchors": {"D0": D0, "D1": D1, "TOTAL": TOTAL, "GV": GV, "DA": DA,
                    "ADD": ADD, "TAXA": TAXA, "GRAND": GRAND, "CNY_R": CNY_R,
                    "FOOT": FOOT, "guide_last": guide_last},
        "expected": {
            "goods_value": round(goods_value, 6),
            "discount": round(discount, 6),
            "additional": round(add, 6),
            "tax": round(tax, 6),
            "grand_total": round(grand, 6),
            "cny_equivalent": round(grand * d["rate"], 6) if d["rate"] else None,
        },
    }

def main():
    ap = argparse.ArgumentParser(description="中英双语外贸出口报价单生成器")
    ap.add_argument("--input", "-i", required=True, help="输入 JSON 数据文件")
    ap.add_argument("--output", "-o", default=None, help="输出 xlsx 路径（覆盖 JSON 中的 output）")
    args = ap.parse_args()

    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    d, warnings = normalize(raw)
    out = args.output or pick(raw, "output", default=None)
    if not out:
        stamp = d["quote_date"].replace("-", "")
        out = str(Path.cwd() / f"出口报价单_{stamp}.xlsx")
    report = build(d, out)
    report["warnings"] = warnings
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
