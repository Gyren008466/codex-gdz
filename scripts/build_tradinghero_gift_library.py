from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs" / "tradinghero_gift_library"
PDFS = [
    Path(r"D:\Desktop\TradingHero2024年11-2025年12月活动方案.pdf"),
    Path(r"D:\Desktop\TradingHero2026年1-6月直播活动.pdf"),
]


GIFT_COLUMNS = [
    "gift_id",
    "gift_name",
    "category",
    "actual_cost",
    "budget_cost",
    "market_price",
    "perceived_value",
    "is_inventory",
    "is_zero_budget",
    "stock_status",
    "suitable_months",
    "suitable_seasons",
    "suitable_events",
    "suitable_persona",
    "suitable_play_types",
    "source_type",
    "source_ref",
    "confidence",
    "notes",
]


CANDIDATE_COLUMNS = [
    "candidate_id",
    "gift_name",
    "normalized_name",
    "source_pdf",
    "source_month",
    "context_excerpt",
    "price_text",
    "suggested_market_price",
    "suggested_category",
    "is_zero_budget_candidate",
    "confidence",
    "manual_status",
    "notes",
]


REVIEW_COLUMNS = [
    "review_id",
    "gift_name",
    "normalized_name",
    "suggested_category",
    "appearances",
    "source_pdfs",
    "source_months",
    "clean_price_options",
    "suggested_market_price",
    "price_confidence",
    "is_zero_budget_candidate",
    "manual_priority",
    "manual_status",
    "review_reason",
    "best_context_excerpt",
    "notes",
]


ZERO_BUDGET_GIFTS = [
    ("好用的指标手册", "学习资料", "指标学习、功能教育、成交后加赠"),
    ("黄金手机贴", "实物", "低成本实物感知、主播特权加赠"),
    ("马年钥匙扣", "实物", "低成本实物感知、主播特权加赠"),
    ("订单流桌垫", "学习资料", "订单流学习、产品相关权益"),
    ("黄金知识桌垫", "学习资料", "黄金知识学习、产品相关权益"),
]


STOP_WORDS = {
    "活动",
    "福利",
    "直播",
    "直播间",
    "购买",
    "用户",
    "主播",
    "旗舰",
    "会员",
    "旗舰会员",
    "旗舰年会员",
    "专业版",
    "基础",
    "折扣",
    "第一轮",
    "第二轮",
    "第三轮",
    "第四轮",
    "第五轮",
    "第六轮",
    "时间",
    "主题",
    "玩法",
    "加赠",
    "限时",
    "秒杀",
    "大促",
    "大营销",
    "返场",
    "元",
    "折",
    "名额",
    "概率",
    "链接",
    "点击",
    "淘宝",
    "京东",
}


GENERIC_CANDIDATE_NAMES = {
    "成本",
    "价值",
    "礼盒",
    "桌垫",
    "台历",
    "显示屏",
    "投影仪",
    "电视",
    "风扇",
    "优惠券",
    "立减金",
    "红包",
    "会员",
}


KNOWN_MEMBERSHIP_OR_CAMPAIGN_PRICES = {
    999,
    2590,
    2690,
    2691,
    2702,
    2802,
    2890,
    2950,
    2990,
    3250,
    3690,
}


NOISY_NAME_PATTERNS = [
    r"价值",
    r"号签",
    r"^\d+红包",
    r"^\d+元",
    r"补贴",
    r"1元抵",
    r"立减",
    r"第[一二三四五六七八九十\d]+轮",
]


GIFT_KEYWORDS = [
    "京东E卡",
    "京东 e 卡",
    "京东卡",
    "E卡",
    "立减金",
    "优惠券",
    "便携屏",
    "便携显示屏",
    "显示屏",
    "带鱼屏",
    "小米电视",
    "电视",
    "投影仪",
    "极米投影仪",
    "行李箱",
    "小米行李箱",
    "充电宝",
    "3C充电宝",
    "键盘鼠标",
    "办公套装",
    "鼠标",
    "支架",
    "手机平板支架",
    "蓝牙耳机",
    "无线蓝牙耳机",
    "挂脖风扇",
    "风扇",
    "养生壶",
    "九阳养生壶",
    "保温杯",
    "手冲壶",
    "电火锅",
    "电动牙刷",
    "扫地机",
    "洗碗机",
    "智能手环",
    "吹风机",
    "水暖毯",
    "暖手宝",
    "加热按摩腰靠",
    "加热坐垫",
    "泡脚桶",
    "电动泡脚桶",
    "除螨仪",
    "挂烫机",
    "小熊便携烘衣机",
    "空气炸锅",
    "煮壶",
    "电炖杯",
    "露营拉杆车",
    "登山背包",
    "亚朵星球枕",
    "枕头",
    "四件套",
    "蚕丝被",
    "抱枕毯子",
    "米面油",
    "苹果",
    "期货交割苹果",
    "礼盒",
    "年货礼盒",
    "故宫福筒",
    "春联",
    "红包袋",
    "窗花",
    "黄金摆件",
    "马上发财摆件",
    "马上暴富黄金摆件",
    "黄金钥匙扣",
    "马年黄金钥匙扣",
    "马年钥匙扣",
    "黄金手机贴",
    "五路财神黄金贴",
    "财源滚滚黄金贴",
    "顺风顺水顺财神黄金贴",
    "黄金大饼",
    "日进斗金黄金大饼",
    "牛气冲天",
    "金钞红包",
    "马年金钞红包",
    "银钞",
    "摇钱树",
    "故宫摇钱树",
    "黄金摇钱树",
    "五福聚财挂件",
    "五福聚财礼盒",
    "台历",
    "2025年台历",
    "2026年期货人台历",
    "期货台历",
    "桌垫",
    "订单流桌垫",
    "黄金知识桌垫",
    "知识桌垫",
    "原油知识地图桌垫",
    "指标手册",
    "好用指标手册",
    "TH好用指标手册",
    "好用的指标手册",
    "技术指标卡片",
    "指标三折页",
    "技术指标三折页",
    "期货锦囊交易卡片",
    "盘外价教程",
    "学习视频",
    "内部教学直播",
    "快闪群",
    "加赠1个月",
    "加赠2个月",
    "15天旗舰版会员",
    "1个月旗舰会员",
]


def read_pdf_text(path: Path) -> str:
    reader = PdfReader(path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    text = text.replace("\u200b", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text


def normalize_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"\s+", "", name)
    name = name.replace("ｅ", "e").replace("Ｅ", "E")
    replacements = {
        "京东e卡": "京东E卡",
        "京东E卡": "京东E卡",
        "京东卡": "京东E卡",
        "便携显示屏幕": "便携显示屏",
        "11.6寸便携显示屏": "便携显示屏",
        "无线蓝牙耳机": "蓝牙耳机",
        "TradingHero好用的指标介绍A5小册/折页": "好用的指标手册",
        "TH好用指标手册": "好用的指标手册",
        "好用指标手册": "好用的指标手册",
        "黄金知识桌垫": "黄金知识桌垫",
        "订单流知识桌垫": "订单流桌垫",
        "五路财神黄金手机贴": "黄金手机贴",
        "马年黄金钥匙扣": "马年钥匙扣",
    }
    return replacements.get(name, name)


def gift_id(name: str, prefix: str = "gift") -> str:
    digest = hashlib.md5(name.encode("utf-8")).hexdigest()[:8]
    return f"{prefix}_{digest}"


def infer_month(context: str) -> str:
    matches = re.findall(r"(\d{1,2})\s*月", context)
    valid = [m for m in matches if 1 <= int(m) <= 12]
    return valid[0] if valid else ""


def infer_price(context: str, name: str) -> tuple[str, str]:
    idx = context.find(name)
    window = context[max(0, idx - 80) : idx + len(name) + 100] if idx >= 0 else context[:180]
    prices = re.findall(r"([1-9]\d{1,4})\s*元", window)
    prices = [p for p in prices if 10 <= int(p) <= 10000]
    if not prices:
        return "", ""
    return "/".join(dict.fromkeys(prices)), prices[0]


def infer_category(name: str) -> str:
    if any(k in name for k in ["会员", "加赠", "课程", "直播", "快闪群"]):
        return "虚拟权益"
    if any(k in name for k in ["手册", "桌垫", "卡片", "三折页", "教程", "学习", "指标", "订单流", "台历"]):
        return "学习资料"
    if any(k in name for k in ["券", "立减金", "E卡"]):
        return "优惠券"
    if any(k in name for k in ["电视", "投影仪", "显示屏", "大奖"]):
        return "大奖池"
    return "实物"


def is_zero_budget_candidate(name: str) -> bool:
    normalized = normalize_name(name)
    return normalized in {
        "好用的指标手册",
        "黄金手机贴",
        "马年钥匙扣",
        "订单流桌垫",
        "黄金知识桌垫",
    }


def confidence_for(name: str, context: str) -> str:
    score = 0
    if name in GIFT_KEYWORDS:
        score += 2
    if re.search(r"礼品|加赠|抽奖|二选一|三选一|赠送|送|福利", context):
        score += 2
    if infer_price(context, name)[0]:
        score += 1
    if len(name) <= 1 or name in STOP_WORDS:
        score -= 4
    if score >= 4:
        return "高"
    if score >= 2:
        return "中"
    return "低"


def clean_candidate_name(raw: str) -> str:
    raw = raw.strip(" ：:，,。、；;（）()[]【】\"'“” ")
    raw = re.sub(r"https?://\S+", "", raw)
    raw = re.sub(r"\d{1,2}[:：]\d{2}.*", "", raw)
    raw = re.sub(r"^[第一二三四五六七八九十]+轮", "", raw)
    raw = re.sub(r"^(A|B|组合\d+|福利[一二三四五六])", "", raw)
    raw = raw.strip(" ：:，,。、；;（）()[]【】\"'“” ")
    return raw


def extract_candidates_from_text(text: str, source_pdf: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    # Keyword-based exact extraction.
    for keyword in sorted(GIFT_KEYWORDS, key=len, reverse=True):
        for match in re.finditer(re.escape(keyword), text, flags=re.I):
            context = text[max(0, match.start() - 140) : min(len(text), match.end() + 180)]
            name = normalize_name(clean_candidate_name(match.group(0)))
            if not name or name in STOP_WORDS:
                continue
            price_text, market_price = infer_price(context, match.group(0))
            key = (name, source_pdf)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "candidate_id": gift_id(f"{source_pdf}:{name}", "candidate"),
                    "gift_name": name,
                    "normalized_name": name,
                    "source_pdf": source_pdf,
                    "source_month": infer_month(context),
                    "context_excerpt": re.sub(r"\s+", " ", context).strip()[:240],
                    "price_text": price_text,
                    "suggested_market_price": market_price,
                    "suggested_category": infer_category(name),
                    "is_zero_budget_candidate": "TRUE" if is_zero_budget_candidate(name) else "FALSE",
                    "confidence": confidence_for(keyword, context),
                    "manual_status": "待确认",
                    "notes": "关键词抽取",
                }
            )

    # Pattern-based extraction for priced snippets near gift words.
    pattern = re.compile(r"([\u4e00-\u9fa5A-Za-z0-9\.·]{2,18})[（(]?\s*([1-9]\d{1,4})\s*元")
    for match in pattern.finditer(text):
        raw_name = clean_candidate_name(match.group(1))
        name = normalize_name(raw_name)
        if not name or name in STOP_WORDS or re.search(r"^\d+$", name):
            continue
        if any(w in name for w in ["目标", "折扣", "旗舰版", "专业版", "会员", "单场", "成交", "预算", "价格", "GMV"]):
            continue
        context = text[max(0, match.start() - 120) : min(len(text), match.end() + 160)]
        if not re.search(r"礼品|加赠|赠送|抽奖|二选一|三选一|送|福利|奖品", context):
            continue
        key = (name, source_pdf)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "candidate_id": gift_id(f"{source_pdf}:{name}", "candidate"),
                "gift_name": name,
                "normalized_name": name,
                "source_pdf": source_pdf,
                "source_month": infer_month(context),
                "context_excerpt": re.sub(r"\s+", " ", context).strip()[:240],
                "price_text": match.group(2),
                "suggested_market_price": match.group(2),
                "suggested_category": infer_category(name),
                "is_zero_budget_candidate": "TRUE" if is_zero_budget_candidate(name) else "FALSE",
                "confidence": confidence_for(name, context),
                "manual_status": "待确认",
                "notes": "价格上下文抽取",
            }
        )

    return rows


def zero_budget_gift_rows() -> list[dict[str, object]]:
    rows = []
    for name, category, notes in ZERO_BUDGET_GIFTS:
        rows.append(
            {
                "gift_id": gift_id(name),
                "gift_name": name,
                "category": category,
                "actual_cost": 0,
                "budget_cost": 0,
                "market_price": "",
                "perceived_value": "",
                "is_inventory": True,
                "is_zero_budget": True,
                "stock_status": "充足",
                "suitable_months": "全年",
                "suitable_seasons": "全年",
                "suitable_events": "普通直播;大促;课程种草;成交后加赠",
                "suitable_persona": "期货交易用户;TradingHero用户;指标学习用户",
                "suitable_play_types": "主播特权;前N名;保底赠送;学习礼包;福利叠加",
                "source_type": "内部库存",
                "source_ref": "用户指定0元库存礼品",
                "confidence": "高",
                "notes": notes,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def parse_clean_price_options(price_text: str) -> list[int]:
    prices: list[int] = []
    for raw in re.findall(r"\d+", str(price_text or "")):
        value = int(raw)
        if value <= 0:
            continue
        if value in KNOWN_MEMBERSHIP_OR_CAMPAIGN_PRICES:
            continue
        if value > 3000:
            continue
        prices.append(value)
    return sorted(set(prices))


def pick_suggested_price(name: str, category: str, prices: list[int], zero_budget: bool) -> tuple[str, str]:
    if zero_budget:
        return "0", "已确认0元库存"
    if not prices:
        return "", "待人工补价"
    if "京东" in name or "E卡" in name or "优惠券" in name or "立减金" in name:
        return str(max(prices)), "面额来自PDF"
    if category == "大奖池":
        return "", "大奖池需按采购/电商实时价补价"
    if len(prices) == 1 and prices[0] <= 1000:
        return str(prices[0]), "单一PDF价格线索，需复核"
    return "", "多价格线索，需人工定价"


def manual_priority_for(row: dict[str, object]) -> tuple[str, str]:
    name = str(row["normalized_name"])
    category = str(row["suggested_category"])
    appearances = int(row["appearances"])
    zero_budget = row["is_zero_budget_candidate"] == "TRUE"
    prices = parse_clean_price_options(str(row.get("clean_price_options", "")))

    if zero_budget:
        return "P0", "用户已确认0元库存，可直接进入正式礼品库"
    if any(re.search(pattern, name) for pattern in NOISY_NAME_PATTERNS) and "京东" not in name:
        return "P3", "疑似活动文案或价格片段，不像独立礼品"
    if name in GENERIC_CANDIDATE_NAMES or len(name) <= 2:
        return "P3", "名称过泛，先不进入正式库"
    if category == "优惠券" and ("京东" in name or "E卡" in name):
        if len(name) > 10:
            return "P3", "疑似多个礼品粘连成一个名称，需回看PDF拆分"
        return "P1", "现金感强、历史高频，可优先确认面额和成本"
    if category == "虚拟权益":
        return "P2", "可进入福利库，但不是实物礼品，需单独核算权益成本"
    if category == "大奖池":
        return "P2", "适合做大奖池或噱头，需补真实采购价"
    if appearances >= 2 and category in {"实物", "学习资料"}:
        return "P1", "历史重复出现，优先确认库存、成本和市场价"
    if category in {"实物", "学习资料", "大奖池"} and (appearances >= 2 or prices):
        return "P2", "有复用潜力，适合人工确认库存和价格"
    return "P3", "证据较弱，仅保留作灵感"


def best_context_for(rows: list[dict[str, str]]) -> str:
    high_rows = [row for row in rows if row.get("confidence") == "高"]
    chosen = high_rows[0] if high_rows else rows[0]
    return chosen.get("context_excerpt", "")


def build_review_rows(candidates: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in candidates:
        grouped.setdefault(row["normalized_name"], []).append(row)

    review_rows: list[dict[str, object]] = []
    for name, rows in grouped.items():
        prices: list[int] = []
        for row in rows:
            prices.extend(parse_clean_price_options(row.get("price_text", "")))
            prices.extend(parse_clean_price_options(row.get("suggested_market_price", "")))
        prices = sorted(set(prices))

        zero_budget = any(row.get("is_zero_budget_candidate") == "TRUE" for row in rows)
        source_pdfs = sorted({row.get("source_pdf", "") for row in rows if row.get("source_pdf")})
        source_months = sorted({row.get("source_month", "") for row in rows if row.get("source_month")}, key=lambda x: int(x) if x.isdigit() else 99)
        category_counts = pd.Series([row.get("suggested_category", "") for row in rows]).value_counts()
        category = str(category_counts.index[0]) if len(category_counts) else ""
        if "京东" in name and ("卡" in name or "E卡" in name):
            category = "优惠券"
        if zero_budget:
            prices = [0]
        suggested_price, price_confidence = pick_suggested_price(name, category, prices, zero_budget)

        review_row: dict[str, object] = {
            "review_id": gift_id(f"review:{name}", "review"),
            "gift_name": name,
            "normalized_name": name,
            "suggested_category": category,
            "appearances": len(rows),
            "source_pdfs": ";".join(source_pdfs),
            "source_months": ";".join(source_months),
            "clean_price_options": "/".join(str(price) for price in prices),
            "suggested_market_price": suggested_price,
            "price_confidence": price_confidence,
            "is_zero_budget_candidate": "TRUE" if zero_budget else "FALSE",
            "manual_status": "待确认" if not zero_budget else "已确认0元库存",
            "best_context_excerpt": best_context_for(rows),
            "notes": "从PDF候选表去重聚合；价格不是实时市场价",
        }
        priority, reason = manual_priority_for(review_row)
        review_row["manual_priority"] = priority
        review_row["review_reason"] = reason
        review_rows.append(review_row)

    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    return sorted(
        review_rows,
        key=lambda row: (
            priority_order.get(str(row["manual_priority"]), 9),
            -int(row["appearances"]),
            str(row["normalized_name"]),
        ),
    )


def markdown_table(rows: list[dict[str, object]], columns: list[tuple[str, str]]) -> str:
    lines = [
        "| " + " | ".join(title for _, title in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        values = []
        for key, _ in columns:
            value = str(row.get(key, "")).replace("\n", " ").replace("|", "/")
            values.append(value)
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def build_review_markdown(zero_rows: list[dict[str, object]], review_rows: list[dict[str, object]]) -> str:
    p1_rows = [row for row in review_rows if row["manual_priority"] == "P1"][:30]
    p2_examples = [row for row in review_rows if row["manual_priority"] == "P2"][:20]
    zero_table = markdown_table(
        zero_rows,
        [
            ("gift_name", "礼品"),
            ("category", "分类"),
            ("budget_cost", "占用预算"),
            ("stock_status", "库存状态"),
            ("suitable_play_types", "适合玩法"),
        ],
    )
    p1_table = markdown_table(
        p1_rows,
        [
            ("gift_name", "候选礼品"),
            ("suggested_category", "分类"),
            ("appearances", "出现次数"),
            ("clean_price_options", "PDF价格线索"),
            ("source_months", "月份线索"),
            ("review_reason", "为什么优先确认"),
        ],
    )
    p2_table = markdown_table(
        p2_examples,
        [
            ("gift_name", "候选礼品"),
            ("suggested_category", "分类"),
            ("clean_price_options", "PDF价格线索"),
            ("price_confidence", "价格状态"),
        ],
    )
    return f"""# TradingHero 礼品库 v1 审核说明

## 已确认 0 元库存礼品

这些礼品已进入 `gift_library.csv`，`actual_cost=0`、`budget_cost=0`，后续生成方案时不占用活动礼品预算。

{zero_table}

## P1 优先人工确认候选

这些礼品来自 PDF 自动抽取，历史重复出现或现金感较强，适合优先确认库存、采购成本、市场标价和是否继续复用。它们尚未进入正式礼品库。

{p1_table}

## P2 候选示例

P2 更适合作为灵感池或大奖池，需要人工筛掉噪声并补真实价格。

{p2_table}

## 使用规则

- `gift_library.csv` 是正式库，前端和 skill v2 可以直接使用。
- `gift_candidates_from_pdf.csv` 是原始抽取候选，适合追溯 PDF 上下文。
- `gift_candidates_review_top.csv` 是人工审核入口，建议先处理 P1，再看 P2。
- PDF 中抽到的价格只是邻近文本线索，不等于实时市场价，也不等于你的实际采购成本。
- PDF 候选礼品不代表当前有库存；只有人工确认后才应进入正式礼品库。
"""


def build_library() -> dict[str, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    zero_rows = zero_budget_gift_rows()
    candidates: list[dict[str, str]] = []
    for pdf in PDFS:
        text = read_pdf_text(pdf)
        candidates.extend(extract_candidates_from_text(text, pdf.name))

    # Merge zero-budget gifts into candidate table if absent.
    existing_names = {row["normalized_name"] for row in candidates}
    for row in zero_rows:
        if row["gift_name"] not in existing_names:
            candidates.append(
                {
                    "candidate_id": gift_id(f"manual:{row['gift_name']}", "candidate"),
                    "gift_name": row["gift_name"],
                    "normalized_name": row["gift_name"],
                    "source_pdf": "manual_zero_budget",
                    "source_month": "",
                    "context_excerpt": row["notes"],
                    "price_text": "0",
                    "suggested_market_price": "",
                    "suggested_category": row["category"],
                    "is_zero_budget_candidate": "TRUE",
                    "confidence": "高",
                    "manual_status": "已确认",
                    "notes": "用户指定0元库存礼品",
                }
            )

    candidates = sorted(candidates, key=lambda r: (r["confidence"] != "高", r["normalized_name"]))
    review_rows = build_review_rows(candidates)

    gift_library_path = OUTPUT_DIR / "gift_library.csv"
    zero_path = OUTPUT_DIR / "zero_budget_gifts.csv"
    candidates_path = OUTPUT_DIR / "gift_candidates_from_pdf.csv"
    review_path = OUTPUT_DIR / "gift_candidates_review_top.csv"
    notes_path = OUTPUT_DIR / "gift_library_notes.md"
    review_md_path = OUTPUT_DIR / "gift_library_v1_review.md"

    write_csv(gift_library_path, zero_rows, GIFT_COLUMNS)
    write_csv(zero_path, zero_rows, GIFT_COLUMNS)
    write_csv(candidates_path, candidates, CANDIDATE_COLUMNS)
    write_csv(review_path, review_rows, REVIEW_COLUMNS)
    review_md_path.write_text(build_review_markdown(zero_rows, review_rows), encoding="utf-8")

    high_count = sum(1 for row in candidates if row["confidence"] == "高")
    zero_candidate_count = sum(1 for row in candidates if row["is_zero_budget_candidate"] == "TRUE")
    p1_count = sum(1 for row in review_rows if row["manual_priority"] == "P1")
    p2_count = sum(1 for row in review_rows if row["manual_priority"] == "P2")
    notes = f"""# TradingHero Gift Library v1 Notes

## Outputs

- `gift_library.csv`: confirmed gift library v1. Currently contains only user-confirmed zero-budget inventory gifts.
- `zero_budget_gifts.csv`: zero-budget inventory gift subset.
- `gift_candidates_from_pdf.csv`: PDF-extracted candidate gifts for manual review.
- `gift_candidates_review_top.csv`: deduplicated review queue with priority, cleaned PDF price clues, and suggested category.
- `gift_library_v1_review.md`: readable review guide for confirmed zero-budget gifts and priority candidates.

## Extraction Scope

- PDFs parsed: {len(PDFS)}
- Candidate gifts extracted: {len(candidates)}
- High-confidence candidates: {high_count}
- Zero-budget candidates: {zero_candidate_count}
- Deduplicated review rows: {len(review_rows)}
- Priority review rows: P1={p1_count}, P2={p2_count}

## Rules

- `gift_library.csv` is conservative and confirmed.
- PDF candidates are not automatically available gifts.
- `manual_status=待确认` rows should be reviewed before entering the official gift library.
- Zero-budget gifts have `actual_cost=0` and `budget_cost=0` because the user said these are inventory items.
- Price fields in candidate/review files are extracted from nearby PDF text, not live market prices.
- P0 means confirmed zero-budget inventory; P1 means review first; P2 means useful candidate; P3 means weak/noisy inspiration only.
"""
    notes_path.write_text(notes, encoding="utf-8")

    return {
        "gift_library": gift_library_path,
        "zero_budget_gifts": zero_path,
        "gift_candidates": candidates_path,
        "gift_candidates_review_top": review_path,
        "gift_library_v1_review": review_md_path,
        "notes": notes_path,
    }


def validate(paths: dict[str, Path]) -> list[str]:
    checks: list[str] = []
    library = pd.read_csv(paths["gift_library"])
    candidates = pd.read_csv(paths["gift_candidates"])
    review_rows = pd.read_csv(paths["gift_candidates_review_top"])
    assert len(library) == len(ZERO_BUDGET_GIFTS), f"Expected {len(ZERO_BUDGET_GIFTS)} zero gifts, got {len(library)}"
    assert set(library["gift_name"]) == {name for name, _, _ in ZERO_BUDGET_GIFTS}
    assert (library["budget_cost"] == 0).all()
    assert len(candidates) >= len(ZERO_BUDGET_GIFTS), "Expected PDF candidates plus zero-budget gifts"
    assert len(review_rows) <= len(candidates), "Review table should be a deduplicated view"
    assert (review_rows["manual_priority"] == "P0").sum() >= len(ZERO_BUDGET_GIFTS), "Expected confirmed zero-budget gifts in review table"
    checks.append(f"gift_library_rows={len(library)}")
    checks.append(f"gift_candidates_rows={len(candidates)}")
    checks.append(f"gift_candidates_review_rows={len(review_rows)}")
    checks.append(f"high_confidence_candidates={(candidates['confidence'] == '高').sum()}")
    checks.append(f"zero_budget_candidates={(candidates['is_zero_budget_candidate'] == True).sum() if candidates['is_zero_budget_candidate'].dtype == bool else (candidates['is_zero_budget_candidate'] == 'TRUE').sum()}")
    checks.append(f"priority_p1_review_rows={(review_rows['manual_priority'] == 'P1').sum()}")
    checks.append(f"priority_p2_review_rows={(review_rows['manual_priority'] == 'P2').sum()}")
    return checks


def main() -> None:
    paths = build_library()
    checks = validate(paths)
    print("Validation:")
    for check in checks:
        print(f"- {check}")
    print("Outputs:")
    for name, path in paths.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
