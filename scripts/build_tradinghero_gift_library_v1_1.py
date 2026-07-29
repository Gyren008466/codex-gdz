from __future__ import annotations

import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "outputs" / "tradinghero_gift_library"

CONFIRMED_LIBRARY = INPUT_DIR / "gift_library.csv"
REVIEW_QUEUE = INPUT_DIR / "gift_candidates_review_top.csv"

V11_LIBRARY = INPUT_DIR / "gift_library_v1_1.csv"
V11_ACTIVE = INPUT_DIR / "gift_library_v1_1_active.csv"
V11_REVIEW_TEMPLATE = INPUT_DIR / "gift_library_v1_1_review_template.csv"
SCHEMA_DOC = INPUT_DIR / "gift_library_schema.md"
SELECTION_RULES_DOC = INPUT_DIR / "gift_selection_rules.md"


V11_COLUMNS = [
    "gift_id",
    "gift_name",
    "category",
    "actual_cost",
    "budget_cost",
    "market_price",
    "perceived_value",
    "is_inventory",
    "is_zero_budget",
    "is_selectable",
    "lifecycle_status",
    "stock_status",
    "stock_qty",
    "budget_band",
    "suitable_months",
    "suitable_seasons",
    "suitable_events",
    "suitable_persona",
    "suitable_play_types",
    "gift_role",
    "source_type",
    "source_ref",
    "confidence",
    "price_source",
    "pdf_price_clues",
    "needs_manual_review",
    "review_priority",
    "review_notes",
    "frontend_tags",
    "skill_usage_notes",
    "notes",
]


REVIEW_TEMPLATE_COLUMNS = [
    "review_id",
    "gift_name",
    "category",
    "review_decision",
    "actual_cost",
    "budget_cost",
    "market_price",
    "perceived_value",
    "is_inventory",
    "stock_status",
    "stock_qty",
    "suitable_months",
    "suitable_play_types",
    "gift_role",
    "budget_band",
    "source_pdf_price_clues",
    "source_months",
    "review_priority",
    "review_reason",
    "manual_notes",
]


def stable_id(name: str, prefix: str = "gift") -> str:
    digest = hashlib.md5(name.encode("utf-8")).hexdigest()[:8]
    return f"{prefix}_{digest}"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def parse_price_options(text: str) -> list[int]:
    values: list[int] = []
    for part in str(text or "").replace("；", "/").replace(";", "/").split("/"):
        part = part.strip()
        if part.isdigit():
            values.append(int(part))
    return sorted(set(values))


def budget_band_for(cost: object) -> str:
    try:
        value = int(float(str(cost)))
    except ValueError:
        return "待确认"
    if value == 0:
        return "0"
    lower = ((value - 1) // 50) * 50 + 1
    upper = ((value - 1) // 50 + 1) * 50
    return f"{lower}-{upper}"


def infer_candidate_budget_band(price_clues: str) -> str:
    prices = [price for price in parse_price_options(price_clues) if 1 <= price <= 500]
    if not prices:
        return "待确认"
    return budget_band_for(min(prices))


def infer_gift_role(category: str, name: str) -> str:
    if category == "优惠券" or "京东" in name or "E卡" in name:
        return "现金感福利;价格补强"
    if category == "学习资料":
        return "学习礼包;产品相关权益"
    if category == "虚拟权益":
        return "权益加赠;留存补强"
    if category == "大奖池":
        return "大奖池;直播噱头"
    return "实物加赠;互动福利"


def confirmed_to_v11(row: dict[str, str]) -> dict[str, object]:
    budget_cost = row.get("budget_cost", "0") or "0"
    category = row.get("category", "")
    name = row.get("gift_name", "")
    return {
        "gift_id": row.get("gift_id") or stable_id(name),
        "gift_name": name,
        "category": category,
        "actual_cost": row.get("actual_cost", "0") or "0",
        "budget_cost": budget_cost,
        "market_price": row.get("market_price", ""),
        "perceived_value": row.get("perceived_value", ""),
        "is_inventory": row.get("is_inventory", "TRUE") or "TRUE",
        "is_zero_budget": row.get("is_zero_budget", "TRUE") or "TRUE",
        "is_selectable": "TRUE",
        "lifecycle_status": "confirmed",
        "stock_status": row.get("stock_status", "充足") or "充足",
        "stock_qty": "",
        "budget_band": budget_band_for(budget_cost),
        "suitable_months": row.get("suitable_months", "全年") or "全年",
        "suitable_seasons": row.get("suitable_seasons", "全年") or "全年",
        "suitable_events": row.get("suitable_events", ""),
        "suitable_persona": row.get("suitable_persona", ""),
        "suitable_play_types": row.get("suitable_play_types", ""),
        "gift_role": infer_gift_role(category, name),
        "source_type": row.get("source_type", "内部库存") or "内部库存",
        "source_ref": row.get("source_ref", "用户指定0元库存礼品") or "用户指定0元库存礼品",
        "confidence": row.get("confidence", "高") or "高",
        "price_source": "用户确认0元库存",
        "pdf_price_clues": "",
        "needs_manual_review": "FALSE",
        "review_priority": "P0",
        "review_notes": "已确认可被 skill/front-end 直接选择",
        "frontend_tags": "0元库存;可选;不占预算",
        "skill_usage_notes": "生成方案时可作为保底福利、主播特权、学习礼包叠加，不占用礼品预算。",
        "notes": row.get("notes", ""),
    }


def candidate_to_v11(row: dict[str, str]) -> dict[str, object]:
    name = row.get("gift_name", "")
    category = row.get("suggested_category", "")
    price_clues = row.get("clean_price_options", "")
    role = infer_gift_role(category, name)
    return {
        "gift_id": stable_id(f"pending:{name}", "pending_gift"),
        "gift_name": name,
        "category": category,
        "actual_cost": "",
        "budget_cost": "",
        "market_price": row.get("suggested_market_price", ""),
        "perceived_value": "",
        "is_inventory": "待确认",
        "is_zero_budget": "FALSE",
        "is_selectable": "FALSE",
        "lifecycle_status": "needs_review",
        "stock_status": "待确认",
        "stock_qty": "",
        "budget_band": "待确认",
        "suitable_months": row.get("source_months", "") or "待确认",
        "suitable_seasons": "待确认",
        "suitable_events": "大促;互动直播;待确认",
        "suitable_persona": "期货交易用户;TradingHero用户;待确认",
        "suitable_play_types": "二选一;抽奖/盲盒;前N名;福利叠加;待确认",
        "gift_role": role,
        "source_type": "PDF候选",
        "source_ref": row.get("source_pdfs", ""),
        "confidence": "中",
        "price_source": row.get("price_confidence", "PDF邻近文本线索，需人工确认"),
        "pdf_price_clues": price_clues,
        "needs_manual_review": "TRUE",
        "review_priority": row.get("manual_priority", "P1"),
        "review_notes": row.get("review_reason", ""),
        "frontend_tags": "待确认;候选礼品;不可自动选择",
        "skill_usage_notes": "未人工确认前只能作为灵感，不得计入预算或自动推荐。",
        "notes": "来自PDF候选审核表，需确认成本、库存、市场价后才能设为is_selectable=TRUE。",
    }


def candidate_to_review_template(row: dict[str, str]) -> dict[str, object]:
    category = row.get("suggested_category", "")
    name = row.get("gift_name", "")
    price_clues = row.get("clean_price_options", "")
    return {
        "review_id": row.get("review_id") or stable_id(f"review:{name}", "review"),
        "gift_name": name,
        "category": category,
        "review_decision": "待确认",
        "actual_cost": "",
        "budget_cost": "",
        "market_price": row.get("suggested_market_price", ""),
        "perceived_value": "",
        "is_inventory": "待确认",
        "stock_status": "待确认",
        "stock_qty": "",
        "suitable_months": row.get("source_months", ""),
        "suitable_play_types": "二选一;抽奖/盲盒;前N名;福利叠加;待确认",
        "gift_role": infer_gift_role(category, name),
        "budget_band": "待确认",
        "source_pdf_price_clues": price_clues,
        "source_months": row.get("source_months", ""),
        "review_priority": row.get("manual_priority", ""),
        "review_reason": row.get("review_reason", ""),
        "manual_notes": "",
    }


def build_schema_doc() -> str:
    return """# TradingHero 礼品库 v1.1 字段说明

## 文件定位

- `gift_library_v1_1.csv`：稳定调用层，包含已确认礼品和待确认候选。
- `gift_library_v1_1_active.csv`：当前可被 skill/front-end 自动选择的礼品子集。
- `gift_library_v1_1_review_template.csv`：P1 候选人工审核模板，补齐成本、市场价、库存后再进入正式可选。

## 前端/skill 必须遵守的字段

| 字段 | 含义 | 调用规则 |
| --- | --- | --- |
| `gift_id` | 稳定礼品 ID | 前端保存选择结果时使用，不用礼品名做主键 |
| `gift_name` | 礼品名称 | 展示用 |
| `category` | 礼品分类 | 常见值：实物、学习资料、优惠券、虚拟权益、大奖池 |
| `actual_cost` | 实际成本 | 内部复盘用，可为空 |
| `budget_cost` | 占用活动预算的成本 | 生成方案时只用这个字段扣预算 |
| `market_price` | 对外市场价/标价 | 用于提升感知价值，不等于成本 |
| `perceived_value` | 主观感知价值 | 可用于排序，v1.1 可为空 |
| `is_inventory` | 是否库存 | TRUE/FALSE/待确认 |
| `is_zero_budget` | 是否 0 元预算礼品 | TRUE 时 `budget_cost` 必须为 0 |
| `is_selectable` | 是否允许自动推荐 | skill/front-end 自动生成方案时只能选 TRUE |
| `lifecycle_status` | 生命周期状态 | `confirmed` 可选；`needs_review` 只能当灵感 |
| `stock_status` | 库存状态 | 充足/少量/缺货/待确认 |
| `budget_band` | 预算带 | 按 50 元区间归类，例如 1-50、51-100、101-150 |
| `suitable_months` | 适合月份 | 可用于活动日期联想 |
| `suitable_play_types` | 适合玩法 | 二选一、抽奖/盲盒、前N名、福利叠加等 |
| `gift_role` | 礼品角色 | 学习礼包、现金感福利、实物加赠、大奖池等 |
| `needs_manual_review` | 是否需要人工确认 | TRUE 不可自动推荐 |
| `review_priority` | 审核优先级 | P0 已确认；P1 优先确认；P2 灵感候选；P3 噪声/弱候选 |

## 稳定调用原则

1. 自动生成直播方案时，只能读取 `is_selectable=TRUE` 且 `lifecycle_status=confirmed` 的礼品。
2. 礼品预算扣减只看 `budget_cost`，不看 `market_price`。
3. `is_zero_budget=TRUE` 的礼品不占用活动礼品预算，但仍可用于提升感知福利。
4. `needs_manual_review=TRUE` 的礼品只能展示在后台候选库，不能自动进入用户方案。
5. PDF 抽取价格只保存在 `pdf_price_clues`，不能直接当作实际成本。
6. `needs_manual_review=TRUE` 的礼品即使有 `market_price` 或 `pdf_price_clues`，也必须人工填写 `budget_cost` 后才能参与预算筛选。
"""


def build_selection_rules_doc() -> str:
    return """# TradingHero 礼品选择规则 v1.1

## 生成器读取顺序

1. 读取 `gift_library_v1_1_active.csv`，只使用已确认可选礼品。
2. 根据用户输入的福利预算，筛选 `budget_cost <= 剩余预算` 的礼品。
3. 优先叠加 0 元库存礼品，再选择占预算礼品。
4. 如果预算不足，输出“建议仅用 0 元库存礼品 + 价格折扣/限时机制”，不要硬塞未确认候选礼品。

## 预算匹配

- 0 元：可使用 `is_zero_budget=TRUE` 的库存礼品，不扣预算。
- 1-50 元：适合低成本实物、学习资料、钥匙扣/贴纸类礼品。
- 51-100 元：适合小家电、桌面用品、低面额京东 E 卡。
- 101-150 元：适合更强现金感礼品或组合福利。
- 151-200 元：适合冲 GMV 的主福利位，可搭配 0 元库存礼品做“多重礼”。
- 200 元以上：优先用于大促、抽奖、盲盒、二选一或大奖池，不建议常规场次消耗。

## 玩法匹配

- 冲 GMV：优先选择现金感强、容易理解、可限时表达的礼品，例如京东 E 卡、立减金、实物二选一。
- 提升互动：优先选择可展示、可投票、可抽取的礼品，例如盲盒墙、刮刮乐、飞行棋礼品池。
- 提升转化质量：优先选择产品相关学习资料，例如订单流桌垫、黄金知识桌垫、指标手册。
- 控制成本：先叠加 0 元库存礼品，再用小额预算补一个有感知的实物或卡券。

## 日期联想规则

- 1-2 月：春节、新年、开工、财运寓意类礼品更合适。
- 3 月：周年庆、开春学习、工具升级类礼品更合适。
- 5-6 月：618、大促、夏季实用礼品、京东 E 卡更合适。
- 9-10 月：开学/金九银十，可偏学习资料、交易工具、办公桌面用品。
- 11-12 月：双十一、双十二、年终复盘、新年台历、年货礼盒更合适。

## 禁用规则

1. 不得自动推荐 `is_selectable=FALSE` 的礼品。
2. 不得把 `pdf_price_clues` 当成成本。
3. 不得把 `market_price` 当成预算扣减值。
4. 不得在库存状态为缺货/待确认时自动推荐。
5. 不得把月会员权益混入旗舰年会员销量预测。
6. 不得根据待确认候选的 PDF 价格线索自动归入预算档位。
"""


def build() -> dict[str, Path]:
    confirmed_rows = read_csv(CONFIRMED_LIBRARY)
    review_rows = read_csv(REVIEW_QUEUE)
    p1_rows = [row for row in review_rows if row.get("manual_priority") == "P1"]

    v11_rows: list[dict[str, object]] = [confirmed_to_v11(row) for row in confirmed_rows]
    v11_rows.extend(candidate_to_v11(row) for row in p1_rows)
    active_rows = [row for row in v11_rows if row.get("is_selectable") == "TRUE"]
    review_template_rows = [candidate_to_review_template(row) for row in p1_rows]

    write_csv(V11_LIBRARY, v11_rows, V11_COLUMNS)
    write_csv(V11_ACTIVE, active_rows, V11_COLUMNS)
    write_csv(V11_REVIEW_TEMPLATE, review_template_rows, REVIEW_TEMPLATE_COLUMNS)
    SCHEMA_DOC.write_text(build_schema_doc(), encoding="utf-8")
    SELECTION_RULES_DOC.write_text(build_selection_rules_doc(), encoding="utf-8")

    return {
        "gift_library_v1_1": V11_LIBRARY,
        "gift_library_v1_1_active": V11_ACTIVE,
        "gift_library_v1_1_review_template": V11_REVIEW_TEMPLATE,
        "gift_library_schema": SCHEMA_DOC,
        "gift_selection_rules": SELECTION_RULES_DOC,
    }


def validate(paths: dict[str, Path]) -> list[str]:
    rows = read_csv(paths["gift_library_v1_1"])
    active = read_csv(paths["gift_library_v1_1_active"])
    review = read_csv(paths["gift_library_v1_1_review_template"])

    selectable = [row for row in rows if row["is_selectable"] == "TRUE"]
    needs_review = [row for row in rows if row["needs_manual_review"] == "TRUE"]

    assert len(active) == len(selectable), "Active file must match selectable rows"
    assert all(row["lifecycle_status"] == "confirmed" for row in active)
    assert all(row["budget_cost"] != "" for row in active)
    assert all(row["is_selectable"] == "FALSE" for row in needs_review)
    assert len(review) == len(needs_review), "Review template should match P1 pending rows"

    return [
        f"gift_library_v1_1_rows={len(rows)}",
        f"active_selectable_rows={len(active)}",
        f"pending_review_rows={len(needs_review)}",
        f"review_template_rows={len(review)}",
    ]


def main() -> None:
    paths = build()
    checks = validate(paths)
    print("Validation:")
    for check in checks:
        print(f"- {check}")
    print("Outputs:")
    for name, path in paths.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
