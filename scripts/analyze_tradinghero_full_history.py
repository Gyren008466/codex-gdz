from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
XLS_PATH = Path(r"D:\Desktop\2024年至2026年直播活动数据.xls")
PDF_2024_2025_PATH = Path(r"D:\Desktop\TradingHero2024年11-2025年12月活动方案.pdf")
PDF_2026_PATH = Path(r"D:\Desktop\TradingHero2026年1-6月直播活动.pdf")
OUTPUT_DIR = ROOT / "outputs" / "tradinghero_full_history"
ORIGINAL_PRICE = 3690
NUMERIC_COLUMNS = ["销量（旗舰年会员）", "GMV", "直播扫码人数", "直播UV", "平均观看时时长"]


def normalize_text(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    text = str(value).replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_year(value: object) -> int | None:
    m = re.search(r"(20\d{2})", normalize_text(value))
    return int(m.group(1)) if m else None


def parse_event_month_day(name: str) -> tuple[int | None, int | None, str]:
    name = normalize_text(name)
    m = re.search(r"(\d{1,2})\s*[.月]\s*(\d{1,2})", name)
    if not m:
        return None, None, ""
    month, day = int(m.group(1)), int(m.group(2))
    if "下午" in name:
        session = "下午"
    elif "晚上" in name or "晚" in name:
        session = "晚上"
    elif "cpi" in name.lower():
        session = "晚上"
    else:
        session = ""
    return month, day, session


def read_excel_history() -> pd.DataFrame:
    df = pd.read_excel(XLS_PATH, sheet_name="Sheet1", engine="xlrd")
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["年份数值"] = df["年份"].map(parse_year)
    parsed = df["大促直播数据统计"].map(parse_event_month_day)
    df["月份"] = [m for m, _, _ in parsed]
    df["日期"] = [d for _, d, _ in parsed]
    df["场次时段"] = [s for _, _, s in parsed]
    df = df[df["年份数值"].notna() & df["月份"].notna() & df["日期"].notna()].copy()
    df = df[df["年份数值"].between(2024, 2026)].copy()
    df["年份数值"] = df["年份数值"].astype(int)
    df["月份"] = df["月份"].astype(int)
    df["日期"] = df["日期"].astype(int)
    df["活动日期"] = df.apply(lambda r: f"{r['年份数值']}-{r['月份']:02d}-{r['日期']:02d}", axis=1)
    df["Excel玩法简介"] = df["直播活动玩法简介"].map(normalize_text)
    df["客单价"] = df["GMV"] / df["销量（旗舰年会员）"].replace({0: pd.NA})
    df["GMV/UV"] = df["GMV"] / df["直播UV"].replace({0: pd.NA})
    df["销量/UV"] = df["销量（旗舰年会员）"] / df["直播UV"].replace({0: pd.NA})
    df["扫码/UV"] = df["直播扫码人数"] / df["直播UV"].replace({0: pd.NA})
    df["数据阶段"] = df["年份数值"].map(lambda y: "2026H1旗舰年阶段" if y == 2026 else ("2025过渡验证阶段" if y == 2025 else "2024早期专业版阶段"))
    return df.sort_values(["年份数值", "月份", "日期", "序号"]).reset_index(drop=True)


def read_pdf_text(path: Path) -> str:
    reader = PdfReader(path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    text = text.replace("\u200b", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text


def date_patterns(year: int, month: int, day: int) -> list[re.Pattern[str]]:
    candidates = [(month, day)]
    if (year, month, day) == (2026, 5, 7):
        candidates.append((5, 8))
    patterns: list[re.Pattern[str]] = []
    for m, d in candidates:
        patterns.extend(
            [
                re.compile(rf"{m}\s*月\s*{d}\s*日"),
                re.compile(rf"{m}\s*\.\s*{d}(?!\d)"),
                re.compile(rf"{m}\s*月\s*{d}(?!\d)"),
            ]
        )
    return patterns


def score_context(context: str, row: pd.Series) -> int:
    score = 0
    excel_text = str(row.get("Excel玩法简介", ""))
    for kw in ["大促", "大营销", "基础", "福利", "旗舰", "专业版", "主题", "玩法", "直播间", "活动"]:
        if kw in context:
            score += 2
    for kw in ["数据", "统计至", "新增", "GMV", "活动总结复盘"]:
        if kw in context:
            score -= 2
    for kw in ["下午", "晚上", "晚"]:
        if row.get("场次时段") and kw == row.get("场次时段") and kw in context[:80]:
            score += 5
    for token in re.split(r"[+、，,（）()\s]+", excel_text):
        if len(token) >= 2 and token in context:
            score += 1
    return score


def find_pdf_segment(row: pd.Series, pdf_text: str) -> tuple[str, str, int, str]:
    matches: list[dict[str, object]] = []
    for pattern in date_patterns(int(row["年份数值"]), int(row["月份"]), int(row["日期"])):
        for match in pattern.finditer(pdf_text):
            context = pdf_text[max(0, match.start() - 80) : min(len(pdf_text), match.start() + 900)]
            matches.append({"start": match.start(), "score": score_context(context, row), "match": match.group(0)})
    if not matches:
        return "", "未匹配PDF", 0, ""
    best = sorted(matches, key=lambda x: (-int(x["score"]), int(x["start"])))[0]
    start = int(best["start"])
    later_starts = sorted({int(m["start"]) for m in matches if int(m["start"]) > start})
    end = later_starts[0] if later_starts else min(len(pdf_text), start + 1600)
    segment = pdf_text[start:end]
    segment = re.split(r"活动总结复盘|TH20\d{2}年\d+\s*月|TH\d+月活动|朋友圈|宣发节奏|活动广告筹备", segment, maxsplit=1)[0].strip()
    if int(best["score"]) >= 8:
        confidence = "高"
    elif int(best["score"]) >= 3:
        confidence = "中"
    else:
        confidence = "低"
    return segment, f"{confidence}置信度", int(best["score"]), str(best["match"])


def extract_prices(text: str) -> list[int]:
    prices: list[int] = []
    patterns = [
        r"(?<!\d)([3-9]\d{2}|[12]\d{3}|3[0-6]\d{2})\s*元",
        r"(?<!\d)([3-9]\d{2}|[12]\d{3}|3[0-6]\d{2})\s*[+＋]",
        r"(?<!\d)([3-9]\d{2}|[12]\d{3}|3[0-6]\d{2})\s*得",
        r"(?<!\d)((?:[3-9]\d{2}|[12]\d{3}|3[0-6]\d{2})(?:\s*/\s*(?:[3-9]\d{2}|[12]\d{3}|3[0-6]\d{2})){1,})",
    ]
    for pattern in patterns:
        for raw in re.findall(pattern, text):
            for part in re.findall(r"[3-9]\d{2}|[12]\d{3}|3[0-6]\d{2}", raw):
                value = int(part)
                if 300 <= value <= ORIGINAL_PRICE:
                    prices.append(value)
    return sorted(set(prices))


def has_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.I) for pattern in patterns)


def classify_tags(text: str, prices: list[int]) -> tuple[list[str], list[str]]:
    tags: list[str] = []
    product_tags: list[str] = []
    min_price = min(prices) if prices else None
    if has_any(text, [r"旗舰"]):
        product_tags.append("旗舰年会员")
    if has_any(text, [r"专业版"]):
        product_tags.append("专业版年费")
    if has_any(text, [r"月费", r"月会员"]):
        product_tags.append("月费/月会员")
    if has_any(text, [r"私密", r"课程", r"训练营", r"内部教学", r"快闪群", r"打卡", r"作业"]):
        product_tags.append("课程/私域转化")

    if has_any(text, [r"秒杀"]) or (min_price is not None and min_price <= 2691) or (
        min_price is not None and min_price <= 2890 and has_any(text, [r"限时"])
    ):
        tags.append("强折扣秒杀")
    if len(prices) >= 2 and has_any(text, [r"三轮", r"阶段", r"时段", r"越早", r"恢复", r"第一轮", r"第二轮", r"第三轮", r"阶梯"]):
        tags.append("阶梯价")
    if has_any(text, [r"1\s*元", r"预购", r"预约", r"预定"]):
        tags.append("1元预购/预约")
    if has_any(text, [r"抽", r"盲盒", r"扭蛋", r"刮刮", r"福袋", r"福签", r"红包", r"砸金蛋", r"飞行棋", r"元宵", r"钞票枪", r"洞洞乐", r"5\s*抽\s*1"]):
        tags.append("抽奖/盲盒")
    if has_any(text, [r"二选一", r"2\s*选\s*1", r"三选一", r"3\s*抽\s*1", r"三抽一", r"5\s*抽\s*1", r"4\s*选\s*2"]):
        tags.append("礼品选择")
    if has_any(text, [r"加赠.{0,8}月", r"\d+\s*个?月", r"抽月数", r"月数", r"13\s*个月"]):
        tags.append("加赠月数")
    if has_any(text, [r"课程", r"私密", r"教学", r"作业", r"打卡", r"训练营", r"指标", r"订单流", r"盘外价", r"快闪群"]):
        tags.append("课程种草/功能教育")
    if has_any(text, [r"返场", r"预热", r"倒计时", r"最后", r"加播", r"冲业绩"]):
        tags.append("预热/返场/冲刺")
    if has_any(text, [r"京东", r"便携", r"行李箱", r"黄金", r"钥匙扣", r"桌垫", r"手册", r"墙报", r"风扇", r"礼盒", r"粽子", r"E\s*卡", r"充电宝", r"摆件", r"平板", r"耳机", r"台历", r"养生壶", r"米面油", r"苹果", r"保温杯", r"投影", r"电视"]):
        tags.append("实物礼品")
    if has_any(text, [r"双11", r"双十一", r"双12", r"元旦", r"春节", r"感恩节", r"小年", r"周年", r"618", r"端午", r"CPI", r"非农", r"520"]):
        tags.append("节日/节点")
    if has_any(text, [r"限\s*\d+", r"名额", r"前\s*\d+", r"仅限", r"最后", r"剩"]):
        tags.append("稀缺名额")
    return tags, product_tags


def build_details(excel_df: pd.DataFrame, pdf_2024_2025: str, pdf_2026: str) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for _, row in excel_df.iterrows():
        pdf_text = pdf_2026 if int(row["年份数值"]) == 2026 else pdf_2024_2025
        segment, status, score, matched_token = find_pdf_segment(row, pdf_text)
        excel_text = row["Excel玩法简介"]
        actual_text = excel_text if excel_text else segment
        prices = extract_prices(actual_text)
        tags, product_tags = classify_tags(actual_text, prices)
        pdf_prices = extract_prices(segment)
        pdf_tags, _ = classify_tags(segment, pdf_prices)
        min_price = min(prices) if prices else pd.NA
        notes: list[str] = []
        if status in {"未匹配PDF", "低置信度"}:
            notes.append("PDF与Excel可能对不上，以Excel玩法简介为主")
        if row["活动日期"] == "2026-05-07":
            notes.append("PDF日期疑似为5月8，按玩法内容匹配")
        if pd.isna(row["GMV"]) or pd.isna(row["销量（旗舰年会员）"]):
            notes.append("Excel销量或GMV缺失")
        records.append(
            {
                "活动日期": row["活动日期"],
                "年份": row["年份数值"],
                "月份": row["月份"],
                "活动名称": row["大促直播数据统计"],
                "场次时段": row["场次时段"],
                "数据阶段": row["数据阶段"],
                "销量_旗舰年": row["销量（旗舰年会员）"],
                "GMV": row["GMV"],
                "扫码人数": row["直播扫码人数"],
                "直播UV": row["直播UV"],
                "平均观看时长": row["平均观看时时长"],
                "客单价": row["客单价"],
                "GMV/UV": row["GMV/UV"],
                "销量/UV": row["销量/UV"],
                "扫码/UV": row["扫码/UV"],
                "Excel玩法简介": excel_text,
                "PDF方案摘要": re.sub(r"\s+", " ", segment)[:420],
                "PDF匹配状态": status,
                "PDF匹配分": score,
                "PDF命中日期文本": matched_token,
                "候选价格": "/".join(map(str, prices)),
                "PDF候选价格": "/".join(map(str, pdf_prices)),
                "最低有效售价": min_price,
                "最低售价折扣": (float(min_price) / ORIGINAL_PRICE if pd.notna(min_price) else pd.NA),
                "产品/阶段标签": "、".join(product_tags),
                "玩法标签": "、".join(tags),
                "PDF灵感标签": "、".join(pdf_tags),
                "异常备注": "；".join(notes),
            }
        )
    details = pd.DataFrame(records)
    q75 = details["GMV"].quantile(0.75)
    median = details["GMV"].median()
    details["效果分层"] = details["GMV"].map(lambda x: "缺失" if pd.isna(x) else ("零销售" if x == 0 else ("高GMV" if x >= q75 else ("中GMV" if x >= median else "低GMV"))))
    uv_q75 = details["直播UV"].quantile(0.75)
    mask = (details["GMV"] == 0) & (details["直播UV"] >= uv_q75)
    details.loc[mask, "异常备注"] = details.loc[mask, "异常备注"].map(lambda x: "高UV零销售" if not x else f"{x}；高UV零销售")
    return details


def expand_tags(details: pd.DataFrame, col: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, row in details.iterrows():
        for tag in [x for x in str(row[col]).split("、") if x]:
            rows.append({"标签": tag, "GMV": row["GMV"], "销量_旗舰年": row["销量_旗舰年"], "是否零销售": row["GMV"] == 0, "活动名称": row["活动名称"], "年份": row["年份"]})
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def tag_summary(details: pd.DataFrame, col: str) -> pd.DataFrame:
    expanded = expand_tags(details, col)
    if expanded.empty:
        return expanded
    return (
        expanded.groupby("标签")
        .agg(
            场次=("活动名称", "count"),
            总GMV=("GMV", "sum"),
            平均GMV=("GMV", "mean"),
            中位GMV=("GMV", "median"),
            平均销量=("销量_旗舰年", "mean"),
            零销售率=("是否零销售", "mean"),
        )
        .reset_index()
        .sort_values(["平均GMV", "场次"], ascending=[False, False])
    )


def fmt_num(value: object, digits: int = 0) -> str:
    if pd.isna(value):
        return "-"
    return f"{float(value):,.{digits}f}" if digits else f"{float(value):,.0f}"


def fmt_pct(value: object, digits: int = 0) -> str:
    if pd.isna(value):
        return "-"
    return f"{float(value) * 100:.{digits}f}%"


def md_table(df: pd.DataFrame, columns: list[str], max_rows: int | None = None) -> str:
    data = df[columns].copy()
    if max_rows:
        data = data.head(max_rows)

    def cell(value: object) -> str:
        if pd.isna(value):
            return ""
        return str(value).replace("\n", "<br>").replace("|", "\\|")

    lines = ["| " + " | ".join(data.columns) + " |", "| " + " | ".join(["---"] * len(data.columns)) + " |"]
    for _, row in data.iterrows():
        lines.append("| " + " | ".join(cell(row[col]) for col in data.columns) + " |")
    return "\n".join(lines)


def format_summary(summary: pd.DataFrame) -> pd.DataFrame:
    out = summary.copy()
    if out.empty:
        return out
    out["总GMV"] = out["总GMV"].map(lambda x: fmt_num(x))
    out["平均GMV"] = out["平均GMV"].map(lambda x: fmt_num(x))
    out["中位GMV"] = out["中位GMV"].map(lambda x: fmt_num(x))
    out["平均销量"] = out["平均销量"].map(lambda x: fmt_num(x, 1))
    out["零销售率"] = out["零销售率"].map(lambda x: fmt_pct(x))
    return out


def build_report(details: pd.DataFrame, play_summary: pd.DataFrame, product_summary: pd.DataFrame) -> str:
    total_rows = len(details)
    valid_gmv = int(details["GMV"].notna().sum())
    total_gmv = details["GMV"].sum()
    total_sales = details["销量_旗舰年"].sum()
    zero_count = int((details["GMV"] == 0).sum())
    low_conf = int(details["PDF匹配状态"].isin(["未匹配PDF", "低置信度"]).sum())
    top = details.sort_values("GMV", ascending=False).head(15).copy()
    bottom = details.sort_values(["GMV", "直播UV"], ascending=[True, False]).head(15).copy()
    by_year = details.groupby("年份").agg(场次=("活动名称", "count"), 有GMV场次=("GMV", "count"), 总GMV=("GMV", "sum"), 平均GMV=("GMV", "mean"), 零销售率=("GMV", lambda s: (s == 0).mean())).reset_index()
    by_year_fmt = by_year.copy()
    by_year_fmt["总GMV"] = by_year_fmt["总GMV"].map(lambda x: fmt_num(x))
    by_year_fmt["平均GMV"] = by_year_fmt["平均GMV"].map(lambda x: fmt_num(x))
    by_year_fmt["零销售率"] = by_year_fmt["零销售率"].map(lambda x: fmt_pct(x))

    strong = details[details["玩法标签"].str.contains("强折扣秒杀", na=False)]
    non_strong = details[~details["玩法标签"].str.contains("强折扣秒杀", na=False)]
    preorder = details[details["玩法标签"].str.contains("1元预购/预约", na=False)]
    education = details[details["玩法标签"].str.contains("课程种草/功能教育", na=False)]
    high_uv_zero = details[(details["GMV"] == 0) & details["异常备注"].str.contains("高UV零销售", na=False)]

    top_display = top.assign(
        客单价=top["客单价"].map(lambda x: fmt_num(x)),
        **{"GMV/UV": top["GMV/UV"].map(lambda x: fmt_num(x, 2)), "最低售价折扣": top["最低售价折扣"].map(lambda x: fmt_pct(x, 1))},
    )
    bottom_display = bottom.assign(
        **{"GMV/UV": bottom["GMV/UV"].map(lambda x: fmt_num(x, 2)), "最低售价折扣": bottom["最低售价折扣"].map(lambda x: fmt_pct(x, 1))}
    )
    play_display = format_summary(play_summary)
    product_display = format_summary(product_summary)

    return f"""# TradingHero 2024.11-2026.06 直播活动效果扩展研究报告

## 1. 研究口径

- 数据范围：Excel 中 2024年11月-2026年6月可解析日期的直播记录，共 {total_rows} 场；其中 {valid_gmv} 场有 GMV 数值。
- 主证据：Excel 的“直播活动玩法简介”更接近当天真实玩法，作为效果归因主证据。
- 辅助证据：两个 PDF 作为策划背景、玩法库和活动链路解释；2024-2025 PDF 与 Excel 可能错位，因此设置 PDF 匹配状态和异常备注。
- 标签口径：效果归因用的“玩法标签/产品阶段标签”只来自 Excel 真实玩法简介；PDF 标签仅作为灵感背景，不参与效果汇总。
- 主排序口径：GMV；销量作为并列核心指标。UV/扫码/观看时长只用于解释转化，不作为唯一成功标准。
- 重要边界：2024-2025 包含专业版、月费、课程私域等过渡阶段，不可直接等同于 2026 旗舰年会员大促。

## 2. 总体画像

- 合计 GMV {fmt_num(total_gmv)} 元，合计销量字段 {fmt_num(total_sales)} 个。
- 零销售场次 {zero_count} 场，占 {fmt_pct(zero_count / valid_gmv if valid_gmv else 0)}。
- PDF 未匹配或低置信度 {low_conf} 场；这些场次全部以 Excel 玩法简介为主。

{md_table(by_year_fmt, ["年份", "场次", "有GMV场次", "总GMV", "平均GMV", "零销售率"])}

## 3. 对鬼点子生成器的新增价值

### 数据事实

1. 全量样本后，“强折扣秒杀”仍是最强直接成交信号：该标签平均 GMV 为 {fmt_num(strong["GMV"].mean())} 元；非强折扣场次平均 GMV 为 {fmt_num(non_strong["GMV"].mean())} 元。
2. 2024-2025 补充了 2026H1 没有的“预热-课程-预约-返场”链路；这些更多来自 PDF 的策划背景，适合进入创意库和链路设计，不直接当作单场效果标签。
3. 礼品玩法本身不是充分条件。抽奖/盲盒、实物礼品覆盖场次多，但应和价格锚点、课程种草、私域承接组合使用。
4. 2024 早期的专业版活动能提供“低价教育型转化”的证据，但不能直接用于预测 2026 旗舰年会员 GMV，需要单独作为低客单/种草模型。

### 原因假设

1. 生成器应拆成两类思路：一类是“当天直接成交”，核心是低价、限时、稀缺；另一类是“前置蓄水”，核心是课程、打卡、预购、私域承接。
2. 2024-2025 的有效经验不一定是某个单场直播玩法，而是连续活动结构：预热教育 -> 预约/加客服 -> 大促成交 -> 返场收割。
3. 高价位或普通折扣场次若缺少课程种草和销售承接，容易变成高观看低成交。

## 4. Top GMV 案例

{md_table(top_display, ["活动日期", "活动名称", "数据阶段", "销量_旗舰年", "GMV", "直播UV", "客单价", "GMV/UV", "Excel玩法简介", "玩法标签"], 15)}

## 5. Bottom / 异常案例

{md_table(bottom_display, ["活动日期", "活动名称", "数据阶段", "销量_旗舰年", "GMV", "直播UV", "Excel玩法简介", "PDF匹配状态", "异常备注"], 15)}

## 6. 玩法标签表现

{md_table(play_display, ["标签", "场次", "总GMV", "平均GMV", "中位GMV", "平均销量", "零销售率"])}

## 7. 产品/阶段标签表现

{md_table(product_display, ["标签", "场次", "总GMV", "平均GMV", "中位GMV", "平均销量", "零销售率"])}

## 8. 生成器规则升级建议

- 先选择活动目标：直接冲 GMV、前置蓄水、私域转化、返场收割，不同目标不要用同一套预测逻辑。
- 直接冲 GMV：优先 2280-2691 价格带、秒杀、限时、稀缺名额、清晰标题。
- 前置蓄水：使用课程/私密课/打卡/作业挑战/1元预购，目标不是当天 GMV，而是为大促建立可转化名单。
- 礼品互动：适合作为直播氛围和成交后奖励，不应替代价格理由。
- 预测方式：先按产品阶段过滤，再按 Excel 真实玩法标签找相似历史案例，输出保守/目标/激进三档 GMV 与销量。
- PDF 使用方式：作为灵感库和链路说明；当 PDF 与 Excel 不一致时，生成器训练和效果归因以 Excel 为准。

## 9. 后续建议

- 补一个“活动链路字段”：预热天数、是否1元预约、是否课程种草、是否私域承接、是否返场。
- 单独维护“可复用玩法库”：把 PDF 中未执行或临时修改的玩法也保留，但标记为“策划未验证”。
- 下一步做成 skill 时，应把“相似历史案例检索”放在生成方案之前。
"""


def build_skill_draft(play_summary: pd.DataFrame) -> str:
    best_tags = play_summary.sort_values("平均GMV", ascending=False)["标签"].head(6).tolist() if not play_summary.empty else []
    if "强折扣秒杀" in best_tags:
        best_tags = ["强折扣秒杀"] + [tag for tag in best_tags if tag != "强折扣秒杀"]
    return f"""# TradingHero 鬼点子生成器 Skill 雏形 - 全量历史版

## 触发场景

用于策划 TradingHero 直播营销活动，或基于 2024.11-2026.06 历史活动数据生成多个可选方案。

## 核心原则

- Excel 的“直播活动玩法简介”是实际执行主证据。
- PDF 是策划背景和玩法灵感库；若与 Excel 不一致，以 Excel 归因，以 PDF 补充创意。
- 先判断目标：直接成交、前置蓄水、私域转化、返场收割。

## 输入项

- 活动日期/节点、目标 GMV 或销量。
- 基础售价、折扣底线、是否允许秒杀。
- 福利预算，以 50 元为区间。
- 可用承接方式：课程、私密课、打卡、1元预购、客服加微、返场。
- 可用礼品池和产品相关权益。

## 输出格式

每次输出 3 个方案：

1. 直接成交方案：低价/秒杀/限时/稀缺。
2. 蓄水转化方案：课程/打卡/1元预购/私域承接。
3. 互动增强方案：抽奖/盲盒/礼品选择，但必须绑定价格或承接理由。

每个方案必须包含历史对照案例、预期 GMV/销量三档、风险说明。

## 当前规则

- 优先玩法标签：{"、".join(best_tags)}
- 强折扣秒杀是直接成交优先级最高的玩法。
- 课程种草和1元预购更适合做前置链路，不应只按当天 GMV 评价。
- 2024专业版/月费案例只用于低客单或种草模型，不直接套用到旗舰年会员。
- PDF里的未执行玩法可进入创意库，但必须标记“未验证”。
"""


def write_outputs(details: pd.DataFrame, play_summary: pd.DataFrame, product_summary: pd.DataFrame) -> dict[str, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT_DIR / "TradingHero_2024-2026_直播活动效果扩展研究报告.md"
    csv_path = OUTPUT_DIR / "TradingHero_2024-2026_直播活动结构化明细.csv"
    md_path = OUTPUT_DIR / "TradingHero_2024-2026_直播活动结构化明细.md"
    play_path = OUTPUT_DIR / "TradingHero_2024-2026_玩法标签汇总.csv"
    product_path = OUTPUT_DIR / "TradingHero_2024-2026_产品阶段标签汇总.csv"
    skill_path = OUTPUT_DIR / "TradingHero_鬼点子生成器_skill雏形_全量历史版.md"
    report_path.write_text(build_report(details, play_summary, product_summary), encoding="utf-8")
    details.to_csv(csv_path, index=False, encoding="utf-8-sig")
    md_path.write_text(md_table(details, list(details.columns)), encoding="utf-8")
    play_summary.to_csv(play_path, index=False, encoding="utf-8-sig")
    product_summary.to_csv(product_path, index=False, encoding="utf-8-sig")
    skill_path.write_text(build_skill_draft(play_summary), encoding="utf-8")
    return {
        "report": report_path,
        "details_csv": csv_path,
        "details_md": md_path,
        "play_summary": play_path,
        "product_summary": product_path,
        "skill": skill_path,
    }


def validate(details: pd.DataFrame) -> list[str]:
    checks: list[str] = []
    assert len(details) == 360, f"Expected 360 parsed rows, got {len(details)}"
    checks.append("rows=360")
    assert int((details["年份"] == 2026).sum()) == 45, "Expected 45 rows for 2026"
    checks.append("2026_rows=45")
    assert int((details["年份"] == 2025).sum()) == 273, "Expected 273 rows for 2025"
    assert int((details["年份"] == 2024).sum()) == 42, "Expected 42 rows for 2024"
    checks.append("year_counts_2024_42_2025_273_2026_45=true")
    top_names = set(details.sort_values("GMV", ascending=False).head(10)["活动名称"].astype(str))
    for expected in ["6.18大促", "3.19大促", "1.22大促"]:
        assert expected in top_names, f"Missing expected top case: {expected}"
    checks.append("top_cases_include_6.18_3.19_1.22=true")
    assert (details["PDF匹配状态"].isin(["未匹配PDF", "低置信度"]).sum()) > 0, "Expected low confidence PDF matches to be tracked"
    checks.append("pdf_low_confidence_tracked=true")
    return checks


def main() -> None:
    excel_df = read_excel_history()
    pdf_2024_2025 = read_pdf_text(PDF_2024_2025_PATH)
    pdf_2026 = read_pdf_text(PDF_2026_PATH)
    details = build_details(excel_df, pdf_2024_2025, pdf_2026)
    play_summary = tag_summary(details, "玩法标签")
    product_summary = tag_summary(details, "产品/阶段标签")
    checks = validate(details)
    paths = write_outputs(details, play_summary, product_summary)
    print("Validation:")
    for check in checks:
        print(f"- {check}")
    print("Outputs:")
    for name, path in paths.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
