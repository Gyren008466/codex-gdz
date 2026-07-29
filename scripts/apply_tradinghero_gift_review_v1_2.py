from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs" / "tradinghero_gift_library"

BASE_LIBRARY = OUTPUT_DIR / "gift_library_v1_1.csv"
FILLED_REVIEW_TEMPLATE = OUTPUT_DIR / "gift_library_v1_1_review_template.csv"
CANDIDATE_REVIEW = OUTPUT_DIR / "gift_candidates_review_top.csv"

V12_LIBRARY = OUTPUT_DIR / "gift_library_v1_2.csv"
V12_ACTIVE = OUTPUT_DIR / "gift_library_v1_2_active.csv"
V12_REVIEW_APPLIED = OUTPUT_DIR / "gift_library_v1_2_review_applied.csv"
V12_SCHEMA = OUTPUT_DIR / "gift_library_schema_v1_2.md"
V12_SELECTION_RULES = OUTPUT_DIR / "gift_selection_rules_v1_2.md"
LATEST_LIBRARY = OUTPUT_DIR / "gift_library_latest.csv"
LATEST_ACTIVE = OUTPUT_DIR / "gift_library_latest_active.csv"


V12_EXTRA_COLUMNS = [
    "benefit_type",
    "discount_amount",
    "affects_payment_price",
    "payment_price_formula",
]


REVIEW_APPLIED_COLUMNS = [
    "review_id",
    "gift_name",
    "category",
    "review_decision",
    "actual_cost",
    "budget_cost",
    "market_price",
    "is_selectable",
    "lifecycle_status",
    "needs_manual_review",
    "apply_status",
    "apply_notes",
]


def stable_id(name: str, prefix: str = "gift") -> str:
    digest = hashlib.md5(name.encode("utf-8")).hexdigest()[:8]
    return f"{prefix}_{digest}"


def read_text_with_fallback(path: Path) -> str:
    for encoding in ("utf-8-sig", "gbk", "cp936", "utf-16"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def read_csv(path: Path) -> list[dict[str, str]]:
    text = read_text_with_fallback(path)
    return list(csv.DictReader(text.splitlines()))


def write_csv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def parse_amount(*values: object) -> int | None:
    for value in values:
        text = str(value or "")
        numbers = [int(x) for x in re.findall(r"\d+", text)]
        if numbers:
            return numbers[0]
    return None


def is_confirmed(value: str) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return False
    if text in {"确认", "是", "纳入", "yes", "y", "true", "1", "confirmed"}:
        return True
    # Excel may have saved a mojibake version of "确认"; keep this tolerant.
    if "ȷ" in text or "confirm" in text:
        return True
    return False


def budget_band(cost: object) -> str:
    try:
        value = int(float(str(cost)))
    except ValueError:
        return "待确认"
    if value == 0:
        return "0"
    lower = ((value - 1) // 50) * 50 + 1
    upper = ((value - 1) // 50 + 1) * 50
    return f"{lower}-{upper}"


def normalize_base_row(row: dict[str, str], columns: list[str]) -> dict[str, object]:
    normalized: dict[str, object] = {col: row.get(col, "") for col in columns}
    category = str(normalized.get("category", ""))
    if category == "立减金":
        normalized["benefit_type"] = "price_discount"
    elif category in {"优惠券", "卡券"}:
        normalized["benefit_type"] = "voucher"
    else:
        normalized["benefit_type"] = "gift"
    normalized.setdefault("discount_amount", "")
    normalized.setdefault("affects_payment_price", "FALSE")
    normalized.setdefault("payment_price_formula", "")
    return normalized


def candidate_name_from_review(original: dict[str, str], filled: dict[str, str]) -> str:
    original_name = original.get("gift_name", "")
    category = original.get("suggested_category", "")
    amount = parse_amount(filled.get("market_price"), filled.get("gift_name"), original_name)
    if category == "优惠券" and amount:
        if "E卡" in original_name or "京东" in original_name:
            return f"{amount}元京东E卡" if "E" in original_name else f"{amount}元京东卡"
    return original_name


def reviewed_candidate_to_library(original: dict[str, str], filled: dict[str, str], columns: list[str]) -> tuple[dict[str, object], dict[str, object]]:
    category = original.get("suggested_category", "")
    name = candidate_name_from_review(original, filled)
    amount = parse_amount(filled.get("budget_cost"), filled.get("actual_cost"), filled.get("market_price"), name)
    is_coupon = category == "优惠券" or "京东" in name or "E卡" in name

    actual_cost = filled.get("actual_cost", "")
    budget_cost = filled.get("budget_cost", "")
    market_price = filled.get("market_price", "")
    apply_notes = ""

    if is_coupon and amount:
        actual_cost = str(amount)
        budget_cost = str(amount)
        market_price = market_price or str(amount)
        lifecycle_status = "confirmed"
        is_selectable = "TRUE"
        needs_review = "FALSE"
        apply_status = "active"
        apply_notes = "卡券金额明确，按面额计入预算成本。"
    elif budget_cost.strip().isdigit():
        lifecycle_status = "confirmed"
        is_selectable = "TRUE"
        needs_review = "FALSE"
        apply_status = "active"
        apply_notes = "已填写预算成本，允许进入自动推荐。"
    else:
        lifecycle_status = "confirmed_needs_pricing"
        is_selectable = "FALSE"
        needs_review = "TRUE"
        apply_status = "confirmed_needs_pricing"
        apply_notes = "已确认纳入候选，但缺少预算成本，暂不进入自动推荐。"

    row: dict[str, object] = {col: "" for col in columns}
    row.update(
        {
            "gift_id": stable_id(name),
            "gift_name": name,
            "category": "优惠券" if is_coupon else category,
            "actual_cost": actual_cost,
            "budget_cost": budget_cost,
            "market_price": market_price,
            "perceived_value": filled.get("perceived_value", ""),
            "is_inventory": filled.get("is_inventory", "待确认") or "待确认",
            "is_zero_budget": "FALSE",
            "is_selectable": is_selectable,
            "lifecycle_status": lifecycle_status,
            "stock_status": filled.get("stock_status", "待确认") or "待确认",
            "stock_qty": filled.get("stock_qty", ""),
            "budget_band": budget_band(budget_cost),
            "suitable_months": filled.get("suitable_months", original.get("source_months", "")),
            "suitable_seasons": "待确认",
            "suitable_events": "大促;互动直播;福利叠加",
            "suitable_persona": "期货交易用户;TradingHero用户",
            "suitable_play_types": filled.get("suitable_play_types", "二选一;抽奖/盲盒;前N名;福利叠加"),
            "gift_role": "现金感福利;卡券加赠" if is_coupon else filled.get("gift_role", ""),
            "source_type": "人工审核PDF候选",
            "source_ref": original.get("source_pdfs", ""),
            "confidence": "高" if is_selectable == "TRUE" else "中",
            "price_source": "人工确认" if is_selectable == "TRUE" else "待补预算成本",
            "pdf_price_clues": original.get("clean_price_options", ""),
            "needs_manual_review": needs_review,
            "review_priority": original.get("manual_priority", "P1"),
            "review_notes": original.get("review_reason", ""),
            "frontend_tags": "可选;卡券;占预算" if is_selectable == "TRUE" and is_coupon else "已确认;待补成本;不可自动选择",
            "skill_usage_notes": "可作为现金感福利计入礼品预算。" if is_selectable == "TRUE" else "缺少预算成本前，只能作为候选灵感。",
            "notes": filled.get("manual_notes", ""),
            "benefit_type": "voucher" if is_coupon else "gift",
            "discount_amount": "",
            "affects_payment_price": "FALSE",
            "payment_price_formula": "",
        }
    )
    applied = {
        "review_id": filled.get("review_id", ""),
        "gift_name": name,
        "category": row["category"],
        "review_decision": "确认",
        "actual_cost": actual_cost,
        "budget_cost": budget_cost,
        "market_price": market_price,
        "is_selectable": is_selectable,
        "lifecycle_status": lifecycle_status,
        "needs_manual_review": needs_review,
        "apply_status": apply_status,
        "apply_notes": apply_notes,
    }
    return row, applied


def discount_row(amount: int) -> dict[str, object]:
    name = f"{amount}元立减金"
    return {
        "gift_id": stable_id(name),
        "gift_name": name,
        "category": "立减金",
        "actual_cost": amount,
        "budget_cost": amount,
        "market_price": amount,
        "perceived_value": amount,
        "is_inventory": "FALSE",
        "is_zero_budget": "FALSE",
        "is_selectable": "TRUE",
        "lifecycle_status": "confirmed",
        "stock_status": "按活动预算",
        "stock_qty": "",
        "budget_band": budget_band(amount),
        "suitable_months": "全年",
        "suitable_seasons": "全年",
        "suitable_events": "大促;冲GMV;限时秒杀;价格锚点",
        "suitable_persona": "价格敏感用户;临门一脚用户;TradingHero意向用户",
        "suitable_play_types": "限时立减;主播特权;前N名;二选一;福利叠加",
        "gift_role": "价格直降;现金感福利",
        "source_type": "用户新增规则",
        "source_ref": "立减金按面额直接降低支付价",
        "confidence": "高",
        "price_source": "用户确认",
        "pdf_price_clues": "",
        "needs_manual_review": "FALSE",
        "review_priority": "P0",
        "review_notes": "用户确认立减金面额为100元/200元，实际价值按面额计算。",
        "frontend_tags": "可选;立减金;影响支付价;占预算",
        "skill_usage_notes": f"若基础售价为 base_price，使用后支付价 = base_price - {amount}。例如 base_price=3250 时，{amount}元立减金后为 {3250 - amount}。",
        "notes": "立减金不是实物礼品，会直接降低用户支付价，也会影响GMV测算的单客支付价。",
        "benefit_type": "price_discount",
        "discount_amount": amount,
        "affects_payment_price": "TRUE",
        "payment_price_formula": f"final_price = base_price - {amount}",
    }


def build_schema_doc() -> str:
    return """# TradingHero 礼品库 v1.2 字段说明

## v1.2 新增能力

v1.2 在 v1.1 的基础上加入“价格影响型福利”，目前支持 `立减金`。立减金不是实物礼品，也不是京东卡券，而是直接降低用户支付价。

例子：基础售价 3250 元，使用 200 元立减金后，用户实际支付价为 3050 元。

## 关键调用字段

| 字段 | 含义 | 调用规则 |
| --- | --- | --- |
| `is_selectable` | 是否可自动推荐 | 只有 TRUE 才能进入生成方案 |
| `budget_cost` | 占用福利预算 | 实物、卡券、立减金都按此字段扣预算 |
| `market_price` | 对外感知价值 | 不参与预算扣减 |
| `benefit_type` | 福利类型 | `gift` 实物/资料；`voucher` 卡券；`price_discount` 立减金 |
| `discount_amount` | 立减金额 | 仅 `benefit_type=price_discount` 时使用 |
| `affects_payment_price` | 是否影响支付价 | TRUE 时必须重算最终支付价 |
| `payment_price_formula` | 支付价公式 | 供前端/skill 展示和计算 |

## 计算规则

1. 普通礼品和京东卡不改变软件售价，只增加福利预算。
2. 立减金会改变用户实际支付价：`final_price = base_price - discount_amount`。
3. 预测 GMV 时，如果方案包含立减金，应使用 `final_price` 乘以预计旗舰年会员销量。
4. 礼品预算消耗仍按 `budget_cost` 计算。100 元立减金占用 100 元福利预算，200 元立减金占用 200 元福利预算。
5. `is_selectable=FALSE` 的礼品即使已人工确认，也不能自动推荐，通常是因为缺少 `budget_cost`。
"""


def build_selection_rules_doc() -> str:
    return """# TradingHero 礼品选择规则 v1.2

## 读取顺序

1. 优先读取 `gift_library_v1_2_active.csv` 或 `gift_library_latest_active.csv`。
2. 只允许选择 `is_selectable=TRUE` 的礼品。
3. 若选择普通礼品或京东卡，软件支付价不变。
4. 若选择立减金，必须重算最终支付价和 GMV。

## 立减金规则

- 当前支持：100 元立减金、200 元立减金。
- 实际价值：按面额计算，即 100 元/200 元。
- 福利预算：按面额扣减，即 100 元立减金占用 100 元预算，200 元立减金占用 200 元预算。
- 支付价：`最终支付价 = 基础售价 - 立减金额`。
- 示例：基础售价 3250 元，使用 200 元立减金后，支付价为 3050 元。

## 方案生成建议

- 冲 GMV：优先用“限时立减 + 0 元库存礼品”组合，表达简单，转化阻力低。
- 控成本：若福利预算只有 100 元，可选 100 元立减金或 0 元库存礼品组合，不要再叠加未确认礼品。
- 高感知：200 元立减金适合大促主福利位，可搭配订单流桌垫/黄金知识桌垫/指标手册做多重礼。
- 不建议把立减金和同等面额京东卡混为一类：京东卡不改变支付价，立减金会改变成交价和 GMV。

## 禁用规则

1. 不得把 `market_price` 当成预算扣减。
2. 不得把 PDF 价格线索当成真实成本。
3. 不得自动推荐 `is_selectable=FALSE` 的候选。
4. 方案中若出现立减金，必须在输出里同时展示基础售价、立减金额、最终支付价。
"""


def build() -> dict[str, Path]:
    base_rows = read_csv(BASE_LIBRARY)
    candidates = {row["review_id"]: row for row in read_csv(CANDIDATE_REVIEW)}
    filled_rows = read_csv(FILLED_REVIEW_TEMPLATE)

    base_columns = list(base_rows[0].keys()) if base_rows else []
    columns = base_columns + [col for col in V12_EXTRA_COLUMNS if col not in base_columns]

    rows: list[dict[str, object]] = []
    rows.extend(normalize_base_row(row, columns) for row in base_rows if row.get("lifecycle_status") == "confirmed")

    applied_rows: list[dict[str, object]] = []
    for filled in filled_rows:
        review_id = filled.get("review_id", "")
        if not is_confirmed(filled.get("review_decision", "")):
            continue
        original = candidates.get(review_id)
        if not original:
            continue
        row, applied = reviewed_candidate_to_library(original, filled, columns)
        rows.append(row)
        applied_rows.append(applied)

    rows.append(discount_row(100))
    rows.append(discount_row(200))

    # De-duplicate by gift_id while preserving the latest reviewed/explicit rows.
    deduped: dict[str, dict[str, object]] = {}
    for row in rows:
        deduped[str(row["gift_id"])] = row
    rows = list(deduped.values())
    active_rows = [row for row in rows if row.get("is_selectable") == "TRUE" and row.get("lifecycle_status") == "confirmed"]

    write_csv(V12_LIBRARY, rows, columns)
    write_csv(V12_ACTIVE, active_rows, columns)
    write_csv(LATEST_LIBRARY, rows, columns)
    write_csv(LATEST_ACTIVE, active_rows, columns)
    write_csv(V12_REVIEW_APPLIED, applied_rows, REVIEW_APPLIED_COLUMNS)
    V12_SCHEMA.write_text(build_schema_doc(), encoding="utf-8")
    V12_SELECTION_RULES.write_text(build_selection_rules_doc(), encoding="utf-8")

    return {
        "gift_library_v1_2": V12_LIBRARY,
        "gift_library_v1_2_active": V12_ACTIVE,
        "gift_library_latest": LATEST_LIBRARY,
        "gift_library_latest_active": LATEST_ACTIVE,
        "gift_library_v1_2_review_applied": V12_REVIEW_APPLIED,
        "gift_library_schema_v1_2": V12_SCHEMA,
        "gift_selection_rules_v1_2": V12_SELECTION_RULES,
    }


def validate(paths: dict[str, Path]) -> list[str]:
    rows = read_csv(paths["gift_library_v1_2"])
    active = read_csv(paths["gift_library_v1_2_active"])
    applied = read_csv(paths["gift_library_v1_2_review_applied"])

    discount_rows = [row for row in active if row.get("benefit_type") == "price_discount"]
    discount_amounts = sorted(int(row["discount_amount"]) for row in discount_rows)
    assert discount_amounts == [100, 200], "Expected 100 and 200 yuan discount rows"
    assert all(row["affects_payment_price"] == "TRUE" for row in discount_rows)
    assert all(row["is_selectable"] == "TRUE" for row in active)
    assert all(row["lifecycle_status"] == "confirmed" for row in active)
    assert any(row["gift_name"] == "200元立减金" and row["payment_price_formula"] == "final_price = base_price - 200" for row in rows)

    return [
        f"gift_library_v1_2_rows={len(rows)}",
        f"active_selectable_rows={len(active)}",
        f"review_applied_rows={len(applied)}",
        f"price_discount_rows={len(discount_rows)}",
        f"active_discount_amounts={','.join(str(x) for x in discount_amounts)}",
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
