from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
XLS_PATH = Path(r"D:\Desktop\2024年至2026年直播活动数据.xls")
PDF_PATH = Path(r"D:\Desktop\TradingHero2026年1-6月直播活动.pdf")
OUTPUT_DIR = ROOT / "outputs" / "tradinghero_2026h1"
ORIGINAL_PRICE = 3690


NUMERIC_COLUMNS = ["销量（旗舰年会员）", "GMV", "直播扫码人数", "直播UV", "平均观看时时长"]


def normalize_text(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    text = str(value)
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_event_date(name: str) -> tuple[int | None, int | None]:
    name = normalize_text(name)
    m = re.search(r"(\d{1,2})\s*[.月]\s*(\d{1,2})", name)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日", name)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def read_excel_2026() -> pd.DataFrame:
    df = pd.read_excel(XLS_PATH, sheet_name="Sheet1", engine="xlrd")
    df = df[df["年份"].astype(str).str.contains("2026", na=False)].copy()
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    parsed = df["大促直播数据统计"].map(parse_event_date)
    df["月份"] = [m for m, _ in parsed]
    df["日期"] = [d for _, d in parsed]
    df["活动日期"] = df.apply(
        lambda r: f"2026-{int(r['月份']):02d}-{int(r['日期']):02d}" if pd.notna(r["月份"]) and pd.notna(r["日期"]) else "",
        axis=1,
    )
    df["Excel玩法简介"] = df["直播活动玩法简介"].map(normalize_text)
    df["客单价"] = df["GMV"] / df["销量（旗舰年会员）"].replace({0: pd.NA})
    df["GMV/UV"] = df["GMV"] / df["直播UV"].replace({0: pd.NA})
    df["销量/UV"] = df["销量（旗舰年会员）"] / df["直播UV"].replace({0: pd.NA})
    df["扫码/UV"] = df["直播扫码人数"] / df["直播UV"].replace({0: pd.NA})
    return df.sort_values(["月份", "日期"]).reset_index(drop=True)


def read_pdf_text() -> str:
    reader = PdfReader(PDF_PATH)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    text = text.replace("\u200b", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text


def date_patterns(month: int, day: int) -> list[re.Pattern[str]]:
    dates = [(month, day)]
    # The PDF names this event as 5月8日晚, while the Excel log records it as 5.7大促.
    # Keep it explicit so the report can still flag the source mismatch.
    if (month, day) == (5, 7):
        dates.append((5, 8))
    patterns = []
    for m, d in dates:
        patterns.extend(
            [
                re.compile(rf"{m}\s*月\s*{d}\s*日"),
                re.compile(rf"{m}\s*\.\s*{d}(?!\d)"),
                re.compile(rf"{m}\s*月\s*{d}(?!\d)"),
            ]
        )
    return patterns


def score_context(context: str) -> int:
    score = 0
    for kw in ["大促", "大营销", "基础", "福利", "旗舰", "主题", "玩法", "直播间"]:
        if kw in context:
            score += 2
    for kw in ["数据", "统计至", "新增", "GMV"]:
        if kw in context:
            score -= 1
    for kw in ["晚 大营销", "日晚", "大营销时间", "大促主题"]:
        if kw in context[:120]:
            score += 4
    for kw in ["24:00", "官网上线时间", "Step①", "打卡"]:
        if kw in context[:180]:
            score -= 4
    return score


def find_pdf_events(pdf_text: str, excel_df: pd.DataFrame) -> dict[str, dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for _, row in excel_df.iterrows():
        month = int(row["月份"])
        day = int(row["日期"])
        event_key = row["活动日期"]
        for pattern in date_patterns(month, day):
            for match in pattern.finditer(pdf_text):
                context = pdf_text[max(0, match.start() - 80) : min(len(pdf_text), match.start() + 800)]
                candidates.append(
                    {
                        "event_key": event_key,
                        "month": month,
                        "day": day,
                        "start": match.start(),
                        "score": score_context(context),
                        "match": match.group(0),
                    }
                )

    chosen: dict[str, dict[str, object]] = {}
    for event_key, group in pd.DataFrame(candidates).groupby("event_key"):
        rows = group.sort_values(["score", "start"], ascending=[False, True])
        chosen[event_key] = rows.iloc[0].to_dict()

    ordered = sorted(chosen.values(), key=lambda x: int(x["start"]))
    for idx, item in enumerate(ordered):
        start = int(item["start"])
        later_known_date_starts = [
            int(c["start"])
            for c in candidates
            if int(c["start"]) > start and str(c["event_key"]) != str(item["event_key"])
        ]
        later_known_date_starts = sorted(set(later_known_date_starts))
        next_known_date = later_known_date_starts[0] if later_known_date_starts else len(pdf_text)
        next_chosen_date = int(ordered[idx + 1]["start"]) if idx + 1 < len(ordered) else len(pdf_text)
        end = min(next_known_date, next_chosen_date, start + 1800, len(pdf_text))
        segment = pdf_text[start:end].strip()
        segment = re.split(r"活动总结复盘|TH\d+月调优记录|TH\d+月活动|朋友圈", segment, maxsplit=1)[0].strip()
        chosen[str(item["event_key"])]["segment"] = segment
    return chosen


def extract_prices(text: str) -> list[int]:
    prices = []
    price_patterns = [
        r"(?<!\d)([12]\d{3}|3[0-6]\d{2})\s*元",
        r"(?<!\d)([12]\d{3}|3[0-6]\d{2})\s*[+＋]",
        r"(?<!\d)([12]\d{3}|3[0-6]\d{2})\s*得",
    ]
    for pattern in price_patterns:
        for raw in re.findall(pattern, text):
            value = int(raw)
            if 1800 <= value <= ORIGINAL_PRICE:
                prices.append(value)
    # Also catch compact stepped-price patterns such as 2391/2491/2591.
    for m in re.finditer(r"(?<!\d)((?:[12]\d{3}|3[0-6]\d{2})(?:\s*/\s*(?:[12]\d{3}|3[0-6]\d{2})){1,})", text):
        for part in re.findall(r"[12]\d{3}|3[0-6]\d{2}", m.group(1)):
            value = int(part)
            if 1800 <= value <= ORIGINAL_PRICE:
                prices.append(value)
    return sorted(set(prices))


def has_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.I) for pattern in patterns)


def classify_tags(text: str, prices: list[int]) -> list[str]:
    tags: list[str] = []
    min_price = min(prices) if prices else None
    if has_any(text, [r"秒杀"]) or (min_price is not None and min_price <= 2691) or (
        min_price is not None and min_price <= 2890 and has_any(text, [r"限时"])
    ):
        tags.append("强折扣秒杀")
    if len(prices) >= 2 and has_any(text, [r"三轮", r"阶段", r"时段", r"越早", r"恢复", r"第一轮", r"第二轮", r"第三轮"]):
        tags.append("阶梯价")
    if has_any(text, [r"1\s*元\s*抵", r"1元抵", r"预购"]):
        tags.append("1元抵扣")
    if has_any(text, [r"抽", r"盲盒", r"扭蛋", r"刮刮", r"福签", r"红包", r"飞行棋", r"元宵", r"钞票枪", r"洞洞乐"]):
        tags.append("抽奖/盲盒")
    if has_any(text, [r"二选一", r"2\s*选\s*1", r"2选1", r"三选一", r"3\s*抽\s*1", r"三抽一", r"4\s*选\s*2", r"4选2"]):
        tags.append("礼品二选一")
    if has_any(text, [r"加赠.{0,8}月", r"\d+\s*个?月旗舰", r"抽月数", r"月数", r"13\s*个月"]):
        tags.append("加赠月数")
    if has_any(
        text,
        [
            r"京东",
            r"便携",
            r"行李箱",
            r"黄金",
            r"钥匙扣",
            r"桌垫",
            r"手册",
            r"墙报",
            r"风扇",
            r"礼盒",
            r"粽子",
            r"E\s*卡",
            r"充电宝",
            r"摆件",
            r"平板",
            r"耳机",
            r"台历",
            r"养生壶",
            r"鼠标",
            r"支架",
            r"投影",
            r"电视",
        ],
    ):
        tags.append("实物礼品")
    if has_any(text, [r"指标", r"学习", r"课程", r"教学", r"手册", r"墙报", r"订单流"]):
        tags.append("学习礼包")
    if has_any(text, [r"元宵", r"周年", r"CPI", r"端午", r"618", r"新年", r"春节", r"非农", r"开门红", r"520"]):
        tags.append("主题节日")
    if has_any(text, [r"限\s*\d+", r"名额", r"前\s*\d+", r"仅限", r"最后", r"剩"]):
        tags.append("稀缺名额")
    return tags


def merge_structured_data(excel_df: pd.DataFrame, pdf_text: str) -> pd.DataFrame:
    pdf_events = find_pdf_events(pdf_text, excel_df)
    records = []
    for _, row in excel_df.iterrows():
        key = row["活动日期"]
        event = pdf_events.get(key, {})
        segment = normalize_text(event.get("segment", ""))
        combined = "\n".join([segment, row["Excel玩法简介"]]).strip()
        prices = extract_prices(combined)
        min_price = min(prices) if prices else pd.NA
        tags = classify_tags(combined, prices)
        match_status = "已匹配PDF" if segment else "待人工确认"
        records.append(
            {
                "活动日期": key,
                "活动名称": row["大促直播数据统计"],
                "销量_旗舰年": row["销量（旗舰年会员）"],
                "GMV": row["GMV"],
                "扫码人数": row["直播扫码人数"],
                "直播UV": row["直播UV"],
                "平均观看时长": row["平均观看时时长"],
                "客单价": row["客单价"],
                "GMV/UV": row["GMV/UV"],
                "销量/UV": row["销量/UV"],
                "扫码/UV": row["扫码/UV"],
                "Excel玩法简介": row["Excel玩法简介"],
                "PDF方案摘要": re.sub(r"\s+", " ", segment)[:420],
                "PDF匹配状态": match_status,
                "候选价格": "/".join(map(str, prices)),
                "最低有效售价": min_price,
                "最低售价折扣": (float(min_price) / ORIGINAL_PRICE if pd.notna(min_price) else pd.NA),
                "玩法标签": "、".join(tags),
            }
        )
    details = pd.DataFrame(records)
    q75 = details["GMV"].quantile(0.75)
    median = details["GMV"].median()
    details["效果分层"] = details["GMV"].map(lambda x: "零销售" if x == 0 else ("高GMV" if x >= q75 else ("中GMV" if x >= median else "低GMV")))
    details["异常备注"] = ""
    uv_q75 = details["直播UV"].quantile(0.75)
    details.loc[(details["GMV"] == 0) & (details["直播UV"] >= uv_q75), "异常备注"] = "高UV零销售"
    details.loc[details["PDF匹配状态"] != "已匹配PDF", "异常备注"] = details["异常备注"].where(
        details["异常备注"] == "", details["异常备注"] + "；"
    ) + "PDF待人工确认"
    details.loc[details["活动日期"] == "2026-05-07", "异常备注"] = details.loc[
        details["活动日期"] == "2026-05-07", "异常备注"
    ].map(lambda x: "PDF日期疑似为5月8，按玩法内容匹配" if not x else f"{x}；PDF日期疑似为5月8，按玩法内容匹配")
    return details


def tag_summary(details: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in details.iterrows():
        tags = [tag for tag in str(row["玩法标签"]).split("、") if tag]
        for tag in tags:
            rows.append(
                {
                    "标签": tag,
                    "GMV": row["GMV"],
                    "销量_旗舰年": row["销量_旗舰年"],
                    "是否零销售": row["GMV"] == 0,
                    "活动名称": row["活动名称"],
                }
            )
    expanded = pd.DataFrame(rows)
    if expanded.empty:
        return expanded
    summary = (
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
    return summary


def fmt_num(value: object, digits: int = 0) -> str:
    if pd.isna(value):
        return "-"
    if digits == 0:
        return f"{float(value):,.0f}"
    return f"{float(value):,.{digits}f}"


def fmt_pct(value: object, digits: int = 1) -> str:
    if pd.isna(value):
        return "-"
    return f"{float(value) * 100:.{digits}f}%"


def md_table(df: pd.DataFrame, columns: list[str], max_rows: int | None = None) -> str:
    data = df[columns].copy()
    if max_rows:
        data = data.head(max_rows)
    headers = list(data.columns)

    def cell(value: object) -> str:
        if pd.isna(value):
            return ""
        text = str(value).replace("\n", "<br>")
        return text.replace("|", "\\|")

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in data.iterrows():
        lines.append("| " + " | ".join(cell(row[col]) for col in headers) + " |")
    return "\n".join(lines)


def build_report(details: pd.DataFrame, summary: pd.DataFrame) -> str:
    top = details.sort_values("GMV", ascending=False).head(10).copy()
    bottom = details.sort_values(["GMV", "直播UV"], ascending=[True, False]).head(10).copy()
    high_uv_zero = details[(details["GMV"] == 0) & (details["直播UV"] >= details["直播UV"].quantile(0.75))].sort_values("直播UV", ascending=False)
    strong_discount = details[details["玩法标签"].str.contains("强折扣秒杀", na=False)]
    non_zero = details[details["GMV"] > 0]
    median_gmv = details["GMV"].median()
    q75_gmv = details["GMV"].quantile(0.75)
    total_gmv = details["GMV"].sum()
    total_sales = details["销量_旗舰年"].sum()
    zero_count = int((details["GMV"] == 0).sum())
    pdf_unmatched = int((details["PDF匹配状态"] != "已匹配PDF").sum())

    top_display = top.assign(
        **{
            "客单价": top["客单价"].map(lambda x: fmt_num(x)),
            "GMV/UV": top["GMV/UV"].map(lambda x: fmt_num(x, 2)),
            "最低售价折扣": top["最低售价折扣"].map(lambda x: fmt_pct(x)),
        }
    )
    bottom_display = bottom.assign(
        **{
            "GMV/UV": bottom["GMV/UV"].map(lambda x: fmt_num(x, 2)),
            "最低售价折扣": bottom["最低售价折扣"].map(lambda x: fmt_pct(x)),
        }
    )
    summary_display = summary.copy()
    if not summary_display.empty:
        summary_display["平均GMV"] = summary_display["平均GMV"].map(lambda x: fmt_num(x))
        summary_display["中位GMV"] = summary_display["中位GMV"].map(lambda x: fmt_num(x))
        summary_display["平均销量"] = summary_display["平均销量"].map(lambda x: fmt_num(x, 1))
        summary_display["零销售率"] = summary_display["零销售率"].map(lambda x: fmt_pct(x, 0))
        summary_display["总GMV"] = summary_display["总GMV"].map(lambda x: fmt_num(x))

    strong_discount_gmv = strong_discount["GMV"].mean() if len(strong_discount) else pd.NA
    non_strong = details[~details["玩法标签"].str.contains("强折扣秒杀", na=False)]
    non_strong_gmv = non_strong["GMV"].mean() if len(non_strong) else pd.NA

    report = f"""# TradingHero 2026H1 直播活动效果研究报告

## 1. 研究口径

- 数据范围：2026年1-6月直播活动，共 {len(details)} 场。
- 主排序口径：旗舰年会员 GMV；销量作为并列核心指标。
- 辅助解释指标：直播 UV、扫码人数、平均观看时长、GMV/UV、销量/UV、扫码/UV。
- 原价口径：旗舰年会员原价 {ORIGINAL_PRICE} 元；最低有效售价折扣 = 自动抽取的最低售价 / {ORIGINAL_PRICE}。
- 归因边界：标签之间高度重叠，本报告把结果视为“相关性与可复用假设”，不是严格因果实验。

## 2. 总体画像

- 45 场合计 GMV {fmt_num(total_gmv)} 元，合计旗舰年销量 {fmt_num(total_sales)} 个。
- 单场 GMV 中位数 {fmt_num(median_gmv)} 元，75分位数 {fmt_num(q75_gmv)} 元；报告将 GMV 高于或等于75分位的场次标记为“高GMV”。
- 零销售场次 {zero_count} 场，占 {fmt_pct(zero_count / len(details), 0)}。
- PDF 自动匹配待人工确认 {pdf_unmatched} 场；所有待确认场次仍保留 Excel 玩法简介和效果指标。

## 3. 核心结论

### 数据事实

1. 强折扣/秒杀是 2026H1 最稳定的头部信号。带“强折扣秒杀”标签的活动平均 GMV 为 {fmt_num(strong_discount_gmv)} 元；不带该标签的活动平均 GMV 为 {fmt_num(non_strong_gmv)} 元。
2. Top 3 活动均是明确低价或阶梯秒杀：6.18大促 2280元秒杀、3.19大促 2391/2491/2591 三轮秒杀、1.22大促 2490/2690/2890 三轮秒杀。
3. 单纯提高福利复杂度不保证成交。4.21大促有 13,109 UV、玩法为三轮秒杀，但 GMV 为 0；5.22大促 7,074 UV、3140 附近加礼品和加赠月数，也为 0。
4. 2026H1 头部活动的共同点不是“礼品多”，而是价格锚点清晰、购买理由强、直播节奏明确，用户能快速判断“现在买是否划算”。

### 原因假设

1. 2280-2691 元区间更容易触发“必须当场买”的决策；3140-3250 元区间若只靠普通实物礼品，用户感知折扣不足。
2. 阶梯价有效的前提是第一档足够低，且有明确时间压力；如果阶梯价整体偏高，例如 2850/2950/3050，可能仍无法突破用户心理价位。
3. 礼品玩法更适合作为“成交后的兴奋点”，不适合替代价格理由；礼品三抽一、扭蛋、盲盒在高价场次里表现不稳定。
4. 学习礼包/指标手册/订单流桌垫这类产品相关权益，适合与低价或加赠月数绑定，单独拉动能力弱于强折扣。

## 4. Top GMV 案例

{md_table(top_display, ["活动日期", "活动名称", "销量_旗舰年", "GMV", "直播UV", "平均观看时长", "客单价", "GMV/UV", "候选价格", "最低售价折扣", "玩法标签"], 10)}

## 5. Bottom / 异常案例

{md_table(bottom_display, ["活动日期", "活动名称", "销量_旗舰年", "GMV", "直播UV", "平均观看时长", "GMV/UV", "候选价格", "最低售价折扣", "玩法标签", "异常备注"], 10)}

高 UV 零销售尤其需要复盘。它们说明问题不在流量，而可能在价格锚点、购买理由、直播承接或销售跟进：

{md_table(high_uv_zero, ["活动日期", "活动名称", "GMV", "直播UV", "平均观看时长", "Excel玩法简介", "异常备注"], None)}

## 6. 玩法标签表现

{md_table(summary_display, ["标签", "场次", "总GMV", "平均GMV", "中位GMV", "平均销量", "零销售率"], None)}

## 7. 对“鬼点子生成器”的规则建议

### 推荐优先复用

- 主推价格：2280-2691 元，用作大促、节点、月底冲刺、重大行情夜。
- 结构：低价秒杀 + 时间段/轮次 + 小额实物或产品相关礼包。
- 强玩法：三轮阶梯秒杀、越早买越优惠、低价名额、月底抽大奖但不替代基础折扣。
- 福利组合：低价基础上叠加 1个月/2个月、指标学习礼包、少量可感知实物礼品。
- 直播表达：标题直接写价格和稀缺性，例如“2280元秒杀”“2391/2491/2591三轮秒杀”。

### 谨慎使用

- 3140-3250 元价格带 + 普通礼品：需要更强理由，否则易出现高 UV 零成交。
- 复杂抽奖/盲盒/扭蛋：可作为互动氛围，不应成为核心成交理由。
- “礼品三抽一”“礼品二选一”如果没有低价托底，用户可能只看热闹不购买。

### 预期 GMV / 销量估算

- 基线估算：先按相似价格带和玩法标签找历史中位 GMV，再根据 UV 做修正。
- 保守档：取同类玩法中位 GMV 或销量。
- 目标档：取同类玩法75分位 GMV 或销量。
- 激进档：仅在价格低于2691元、具备限时/稀缺/重大节点时，参考 Top 案例。
- 输出时必须同时给出“不确定性说明”：样本量、是否高UV、是否重大节点、是否已有预购/私域承接。

## 8. 后续补数据建议

- 继续补齐 2024/2025 PDF 后，可用同一套标签体系做跨年度验证。
- 每场直播建议新增字段：实际支付链接/公域或私域来源、是否预热、是否有销售跟进、退款数、直播前预约量。
- 生成器上线前，建议先做一个“历史相似活动检索器”，让每个新方案都能反查 3-5 个历史对照案例。
"""
    return report


def build_skill_draft(details: pd.DataFrame, summary: pd.DataFrame) -> str:
    best_tags = summary.sort_values("平均GMV", ascending=False)["标签"].head(5).tolist() if not summary.empty else []
    if "强折扣秒杀" in best_tags:
        best_tags = ["强折扣秒杀"] + [tag for tag in best_tags if tag != "强折扣秒杀"]
    return f"""# TradingHero 直播鬼点子生成器 Skill 雏形

> 这是研究产出的 skill 草案，不是正式安装的 `SKILL.md`。

## 触发场景

当用户需要策划 TradingHero 旗舰年会员直播营销活动，或根据历史活动数据生成多个直播营销方案时使用。

## 输入项

- 活动日期或节点：普通日、大促、月底冲刺、重大行情夜、节日主题。
- 基础售价：默认原价 3690 元，可输入候选售价。
- 福利预算：按 50 元区间选择，可包含实物礼品、加赠月数、学习礼包、优惠券。
- 活动目标：冲 GMV、冲销量、提高扫码、测试新玩法。
- 可用资源：主播、客服、运营、预热渠道、礼品池、是否允许低价秒杀。

## 输出格式

每次至少输出 3 个方案：

1. 稳健方案：参考历史中位 GMV，价格和玩法不过度激进。
2. 冲刺方案：使用强折扣/限时/稀缺机制，参考历史高GMV案例。
3. 互动方案：保留抽奖、盲盒、二选一等直播互动，但必须有清晰价格锚点。

每个方案包含：

- 基础折扣售价和折扣率。
- 叠加福利清单和估算福利成本。
- 直播玩法节奏。
- 对标历史案例。
- 预期旗舰年销量、GMV区间、风险说明。

## 当前推荐规则

- 优先玩法标签：{"、".join(best_tags)}
- 低价秒杀优先级最高，尤其是 2280-2691 元价格带。
- 阶梯价仅在第一档足够低且有明确时间压力时优先使用。
- 礼品玩法必须服务于成交理由，不能替代成交理由。
- 3140-3250 元价格带需要强主题、强稀缺或高价值权益支撑。
- 遇到高 UV 零销售历史相似场景时，优先降低基础售价或强化私域承接，而不是继续堆礼品。

## 分析规则

- 只分析旗舰年会员，默认原价 3690 元。
- 主效果口径为 GMV，销量为并列核心指标。
- UV、扫码人数、观看时长只用于解释转化，不作为唯一成功标准。
- 历史对照必须区分数据事实和原因假设。
"""


def write_outputs(details: pd.DataFrame, summary: pd.DataFrame) -> dict[str, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report(details, summary)
    skill = build_skill_draft(details, summary)
    report_path = OUTPUT_DIR / "TradingHero_2026H1_直播活动效果研究报告.md"
    csv_path = OUTPUT_DIR / "TradingHero_2026H1_直播活动结构化明细.csv"
    md_path = OUTPUT_DIR / "TradingHero_2026H1_直播活动结构化明细.md"
    skill_path = OUTPUT_DIR / "TradingHero_直播鬼点子生成器_skill雏形.md"
    summary_path = OUTPUT_DIR / "TradingHero_2026H1_玩法标签汇总.csv"

    report_path.write_text(report, encoding="utf-8")
    details.to_csv(csv_path, index=False, encoding="utf-8-sig")
    md_path.write_text(md_table(details, list(details.columns)), encoding="utf-8")
    skill_path.write_text(skill, encoding="utf-8")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    return {
        "report": report_path,
        "csv": csv_path,
        "details_md": md_path,
        "skill": skill_path,
        "summary": summary_path,
    }


def validate(details: pd.DataFrame) -> list[str]:
    checks: list[str] = []
    checks.append(f"2026_rows={len(details)}")
    assert len(details) == 45, f"Expected 45 2026 rows, got {len(details)}"
    top_names = set(details.sort_values("GMV", ascending=False).head(5)["活动名称"].astype(str))
    for expected in ["6.18大促", "3.19大促", "1.22大促"]:
        assert expected in top_names, f"Missing expected top GMV case: {expected}"
    checks.append("top_cases_include_6.18_3.19_1.22=true")
    for month in [1, 3, 6]:
        matched = details[(details["活动日期"].str.startswith(f"2026-{month:02d}-")) & (details["PDF匹配状态"] == "已匹配PDF")]
        assert len(matched) >= 2, f"Expected at least 2 matched PDF events for month {month}, got {len(matched)}"
    checks.append("sample_pdf_match_months_1_3_6>=2=true")
    zero_high_uv = details[(details["GMV"] == 0) & (details["直播UV"] >= details["直播UV"].quantile(0.75))]
    assert len(zero_high_uv) >= 1, "Expected high UV zero sales cases to be retained"
    checks.append(f"high_uv_zero_cases={len(zero_high_uv)}")
    return checks


def main() -> None:
    excel_df = read_excel_2026()
    pdf_text = read_pdf_text()
    details = merge_structured_data(excel_df, pdf_text)
    summary = tag_summary(details)
    checks = validate(details)
    paths = write_outputs(details, summary)
    print("Validation:")
    for check in checks:
        print(f"- {check}")
    print("Outputs:")
    for key, path in paths.items():
        print(f"- {key}: {path}")


if __name__ == "__main__":
    main()
