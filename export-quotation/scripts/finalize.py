# -*- coding: utf-8 -*-
"""报价单交付前一键校验：重算公式 → 写入 AIGC 隐式标识 → 核对整条计算链。

顺序不可颠倒：recalc.py 会重写整个 xlsx 包，若先写标识会被冲掉。

用法:
    python3 finalize.py --file 出口报价单_20261109.xlsx [--input data.json]

输出 JSON 报告；任何一项失败返回非零退出码，禁止交付。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path

try:
    import openpyxl
except ImportError:
    import subprocess as _sp
    _sp.check_call([sys.executable, "-m", "pip", "install", "--quiet", "openpyxl>=3.1.0"])
    import openpyxl

BASE = Path.home() / ".workbuddy/plugins/cache/workbuddy-builtin/workbuddy-sheetagent"


def version_key(p: Path):
    m = re.search(r"workbuddy-sheetagent/([0-9.]+)-", str(p))
    if not m:
        return (0,)
    return tuple(int(x) for x in m.group(1).split("."))


def find_script(name: str) -> Path:
    hits = list(BASE.glob(f"*/skills/workbuddy-sheet-generation/scripts/{name}"))
    if not hits:
        raise FileNotFoundError(
            f"找不到 {name}。请先加载 workbuddy-sheet-generation 技能，或检查插件缓存目录：{BASE}")
    return max(hits, key=version_key)


def run(cmd, timeout=300):
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    out = (proc.stdout or "").strip()
    try:
        payload = json.loads(out[out.find("{"):])
    except (ValueError, TypeError):
        payload = {"raw_stdout": out, "raw_stderr": (proc.stderr or "").strip()}
    return proc.returncode, payload


def locate(ws) -> dict:
    """从工作簿内容反查行锚点，顺带确认公式未被覆盖。"""
    a = {}
    d0 = None
    for r in range(1, ws.max_row + 1):
        v = ws.cell(r, 1).value
        if not isinstance(v, str):
            continue
        if v.startswith("=IF(COUNTA(") and d0 is None:
            d0 = r
        for key, token in {
            "total": "合计  /  TOTAL",
            "goods": "货值合计 / Goods Value",
            "discount_rate": "折扣率 / Discount Rate",
            "discount_amount": "折扣金额 / Discount Amount",
            "additional": "附加费小计 / Total Additional",
            "tax_rate": "税率 / VAT / Tax Rate",
            "tax_amount": "税额 / Tax Amount",
            "grand": "总计  /  GRAND TOTAL (USD)",
            "cny": "人民币参考金额 / CNY Equivalent",
        }.items():
            if token in v and key not in a:
                a[key] = r
    if d0 is None or not all(k in a for k in ("total", "goods", "discount_rate", "additional", "tax_rate", "grand", "cny")):
        raise ValueError("无法定位行锚点：文件可能不是本技能生成的报价单，或公式/标签被改动")
    a["d0"] = d0
    a["d1"] = a["total"] - 1
    m = re.search(r"=SUM\(I(\d+):I(\d+)\)", str(ws.cell(a["additional"], 9).value))
    if not m:
        raise ValueError("附加费小计公式异常，无法核对费用区间")
    a["f0"], a["f1"] = int(m.group(1)), int(m.group(2))
    return a


def num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def verify(path: str) -> dict:
    wf = openpyxl.load_workbook(path)                 # 公式
    wv = openpyxl.load_workbook(path, data_only=True)  # 缓存值
    if "报价单 Quotation" not in wf.sheetnames or "填写指引 Guide" not in wf.sheetnames:
        raise ValueError("缺少「报价单 Quotation」或「填写指引 Guide」工作表")
    ws, wsv = wf["报价单 Quotation"], wv["报价单 Quotation"]
    gd, gdv = wf["填写指引 Guide"], wv["填写指引 Guide"]
    A = locate(ws)
    checks, failures = [], []

    def check(name, got, expected, tol=1e-6):
        if expected is None:
            ok = got in (None, "")
        elif isinstance(expected, (int, float)) and isinstance(got, (int, float)):
            ok = abs(float(got) - float(expected)) <= tol
        else:
            ok = got == expected
        checks.append({"name": name, "got": got, "expected": expected, "ok": ok})
        if not ok:
            failures.append(name)

    # 公式仍在（防止被重算引擎或手工覆盖成静态值）
    for key in ("goods", "discount_amount", "additional", "tax_amount", "grand", "cny"):
        v = ws.cell(A[key], 9).value
        check(f"公式保留 I{A[key]} ({key})", isinstance(v, str) and v.startswith("="), True)
    check("明细金额公式保留 I%d" % A["d0"],
          isinstance(ws.cell(A["d0"], 9).value, str) and ws.cell(A["d0"], 9).value.startswith("="), True)

    # 逐行金额与序号
    goods = 0.0
    for r in range(A["d0"], A["d1"] + 1):
        qty, price = num(ws.cell(r, 6).value), num(ws.cell(r, 8).value)
        expected = round(qty * price, 6) if qty is not None and price is not None else None
        got = num(wsv.cell(r, 9).value)
        check(f"行金额 I{r}", got, expected)
        if expected is not None:
            goods += expected
        named = bool(ws.cell(r, 2).value or ws.cell(r, 3).value)
        check(f"序号 A{r}", num(wsv.cell(r, 1).value), r - A["d0"] + 1 if named else None)
    goods = round(goods, 6)

    d_rate = num(ws.cell(A["discount_rate"], 9).value) or 0.0
    t_rate = num(ws.cell(A["tax_rate"], 9).value) or 0.0
    add = round(sum(num(ws.cell(r, 9).value) or 0 for r in range(A["f0"], A["f1"] + 1)), 6)
    discount = round(goods * d_rate, 6)
    tax = round((goods - discount + add) * t_rate, 6)
    grand = round(goods - discount + add + tax, 6)
    rate = num(ws["I10"].value)
    cny = round(grand * rate, 6) if rate else None

    check(f"数量合计 F{A['total']}", num(wsv.cell(A["total"], 6).value),
          round(sum(num(ws.cell(r, 6).value) or 0 for r in range(A["d0"], A["d1"] + 1)), 6))
    check(f"货值合计 I{A['total']}", num(wsv.cell(A["total"], 9).value), goods)
    check(f"货值引用 I{A['goods']}", num(wsv.cell(A["goods"], 9).value), goods)
    check(f"折扣金额 I{A['discount_amount']}", num(wsv.cell(A["discount_amount"], 9).value), discount)
    check(f"附加费小计 I{A['additional']}", num(wsv.cell(A["additional"], 9).value), add)
    check(f"税额 I{A['tax_amount']}", num(wsv.cell(A["tax_amount"], 9).value), tax)
    check(f"GRAND TOTAL I{A['grand']}", num(wsv.cell(A["grand"], 9).value), grand)
    check(f"CNY 参考 I{A['cny']}", num(wsv.cell(A["cny"], 9).value), cny)

    # 有效期 = 报价日 + 有效天数
    qd, vd = wsv["I5"].value, num(ws["C6"].value)
    if hasattr(qd, "date"):
        qd = qd.date()
    if isinstance(qd, date) and vd:
        check("有效期至 I6", wsv["I6"].value.strftime("%Y-%m-%d") if hasattr(wsv["I6"].value, "strftime")
              else str(wsv["I6"].value), (qd + timedelta(days=int(vd))).isoformat())

    # 卖方公司自动引用抬头
    check("卖方公司 C13 = A2", wsv["C13"].value, wsv["A2"].value)
    # Guide 页三处引用
    # 汇率留空时，跨表引用空单元格在 Excel/LibreOffice 中返回 0，属正常行为
    if rate is None:
        check("Guide C19 汇率(未填)", num(gdv["C19"].value) in (None, 0.0), True)
        check("Guide C21 人民币(未填)", num(gdv["C21"].value) in (None, 0.0), True)
    else:
        check("Guide C19 汇率", num(gdv["C19"].value), rate)
        check("Guide C21 人民币", num(gdv["C21"].value), cny)
    check("Guide C20 总额", num(gdv["C20"].value), grand)
    check("Guide 公式保留 C20", isinstance(gd["C20"].value, str) and gd["C20"].value.startswith("="), True)

    with zipfile.ZipFile(path) as z:
        aigc = "docProps/custom.xml" in z.namelist()

    return {
        "anchors": A,
        "computed": {"goods_value": goods, "discount": discount, "additional": add,
                     "tax": tax, "grand_total": grand, "cny_equivalent": cny, "rate": rate},
        "checks": checks,
        "failures": failures,
        "check_count": len(checks),
        "aigc_custom_xml": aigc,
        "print_area": str(ws.print_area),
    }


def main():
    ap = argparse.ArgumentParser(description="报价单交付前校验")
    ap.add_argument("--file", "-f", required=True, help="待校验的 xlsx")
    ap.add_argument("--input", "-i", default=None, help="生成时用的 JSON（可选，仅记录用）")
    args = ap.parse_args()

    path = str(Path(args.file).resolve())
    if not Path(path).exists():
        print(json.dumps({"status": "failed", "error": "文件不存在", "file": path}, ensure_ascii=False, indent=2))
        sys.exit(1)

    report = {"file": path, "steps": []}
    try:
        recalc = find_script("recalc.py")
        aigc_script = find_script("aigc_label.py")
    except FileNotFoundError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2))
        sys.exit(1)

    # 1) 重算
    rc, res = run([sys.executable, str(recalc), path, "120"], timeout=300)
    report["steps"].append({"step": "recalc", "returncode": rc, "result": res})
    if rc != 0 or res.get("status") != "success" or res.get("total_errors", 1) != 0:
        report["status"] = "failed"
        report["error"] = "公式重算未通过（status 非 success 或存在公式错误）"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(1)

    # 2) AIGC 隐式标识（必须在 recalc 之后）
    rc2, res2 = run([sys.executable, str(aigc_script), path, "--platform", "WORKBUDDY"], timeout=120)
    report["steps"].append({"step": "aigc_label", "returncode": rc2, "result": res2})
    if rc2 != 0 or res2.get("status") != "labeled":
        report["status"] = "failed"
        report["error"] = "AIGC 隐式标识写入失败"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(1)

    # 3) 计算链与版式校验
    try:
        report["verification"] = verify(path)
    except Exception as exc:  # noqa: BLE001
        report["status"] = "failed"
        report["error"] = f"校验异常: {exc}"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(1)

    v = report["verification"]
    if v["failures"] or not v["aigc_custom_xml"]:
        report["status"] = "failed"
        report["error"] = "计算链或版式校验未通过：" + ", ".join(v["failures"] or ["AIGC 标识缺失"])
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(1)

    report["status"] = "passed"
    report["summary"] = {
        "items": v["anchors"]["d1"] - v["anchors"]["d0"] + 1,
        "formulas": res.get("total_formulas"),
        "engine": res.get("engine"),
        "checks_passed": v["check_count"],
        "grand_total_usd": v["computed"]["grand_total"],
        "cny_equivalent": v["computed"]["cny_equivalent"],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
