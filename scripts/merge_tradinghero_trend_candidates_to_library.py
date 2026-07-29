from __future__ import annotations

import argparse
import csv
import hashlib
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "outputs" / "tradinghero_gift_library"

LIBRARY_COLUMNS = [
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
    "benefit_type",
    "discount_amount",
    "affects_payment_price",
    "payment_price_formula",
]


MERGE_LOG_COLUMNS = [
    "merged_at",
    "candidate_id",
    "gift_id",
    "gift_name",
    "manual_status",
    "manual_budget_cost",
    "manual_stock_status",
    "merge_status",
    "is_selectable",
    "notes",
]


CONFIRM_STATUSES = {
    "确认",
    "納入",
    "纳入",
    "纳入正式库",
    "纳入并可自动推荐",
    "进入正式库",
    "进入active",
    "active",
    "yes",
    "y",
    "true",
    "1",
}

REJECT_STATUSES = {
    "拒绝",
    "不要",
    "不纳入",
    "归档",
    "archive",
    "rejected",
    "no",
    "false",
    "0",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge reviewed trend gift candidates into TradingHero gift library.")
    parser.add_argument("--library", default=str(DEFAULT_DIR / "gift_library_latest.csv"))
    parser.add_argument("--active-library", default=str(DEFAULT_DIR / "gift_library_latest_active.csv"))
    parser.add_argument("--trend-candidates", default=str(DEFAULT_DIR / "gift_trend_candidates.csv"))
    parser.add_argument("--trend-review", default=str(DEFAULT_DIR / "gift_trend_candidates_review.csv"))
    parser.add_argument("--output-library", default=str(DEFAULT_DIR / "gift_library_v2_2.csv"))
    parser.add_argument("--output-active", default=str(DEFAULT_DIR / "gift_library_v2_2_active.csv"))
    parser.add_argument("--merge-log", default=str(DEFAULT_DIR / "gift_trend_merge_applied.csv"))
    parser.add_argument("--update-latest", action="store_true", help="Also overwrite gift_library_latest*.csv with v2.2 outputs.")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def stable_id(text: str, prefix: str = "gift") -> str:
    digest = hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
    return f"{prefix}_{digest}"


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", "", str(name or "")).strip().lower()


def normalize_status(status: str) -> str:
    return str(status or "").strip().lower()


def is_confirmed(status: str) -> bool:
    normalized = normalize_status(status)
    return normalized in {s.lower() for s in CONFIRM_STATUSES} or "纳入" in normalized or "确认" in normalized


def is_rejected(status: str) -> bool:
    normalized = normalize_status(status)
    return normalized in {s.lower() for s in REJECT_STATUSES} or "拒绝" in normalized or "归档" in normalized


def is_number(value: str) -> bool:
    return bool(re.fullmatch(r"\d+(\.\d+)?", str(value or "").strip()))


def to_int_string(value: str, fallback: str = "") -> str:
    text = str(value or "").strip()
    if not is_number(text):
        return fallback
    number = float(text)
    return str(int(number)) if number.is_integer() else str(number)


def budget_band(cost: str) -> str:
    value = to_int_string(cost)
    if value == "":
        return "待确认"
    amount = int(float(value))
    if amount == 0:
        return "0"
    if amount <= 50:
        return "1-50"
    if amount <= 100:
        return "51-100"
    if amount <= 150:
        return "101-150"
    if amount <= 200:
        return "151-200"
    return "200+"


def stock_allows_active(stock_status: str) -> bool:
    text = str(stock_status or "").strip()
    if not text:
        return False
    return text not in {"缺货", "待确认", "不可采购", "下架"}


def infer_gift_role(category: str, benefit_type: str) -> str:
    if benefit_type == "price_discount":
        return "价格直降;现金感福利"
    if benefit_type == "voucher":
        return "现金感福利;卡券加赠"
    if category == "学习资料":
        return "学习礼包;产品相关权益"
    return "实物加赠;互动福利"


def trend_to_library_row(candidate: dict[str, str], review: dict[str, str]) -> tuple[dict[str, object], str, str]:
    name = review.get("gift_name") or candidate.get("gift_name", "")
    category = review.get("category") or candidate.get("category", "")
    benefit_type = review.get("benefit_type") or candidate.get("benefit_type", "gift")
    actual_cost = to_int_string(review.get("manual_actual_cost", ""))
    budget_cost = to_int_string(review.get("manual_budget_cost", ""))
    market_price = to_int_string(review.get("manual_market_price", ""), to_int_string(candidate.get("reference_price", "")))
    stock_status = review.get("manual_stock_status") or "待确认"
    can_activate = bool(budget_cost) and stock_allows_active(stock_status)

    discount_amount = ""
    affects_payment_price = "FALSE"
    payment_price_formula = ""
    if benefit_type == "price_discount":
        discount_amount = budget_cost or to_int_string(candidate.get("reference_price", ""))
        affects_payment_price = "TRUE"
        payment_price_formula = f"final_price = base_price - {discount_amount}" if discount_amount else ""

    lifecycle_status = "confirmed" if can_activate else "confirmed_needs_pricing"
    row = {
        "gift_id": stable_id(name),
        "gift_name": name,
        "category": category,
        "actual_cost": actual_cost,
        "budget_cost": budget_cost,
        "market_price": market_price,
        "perceived_value": market_price,
        "is_inventory": "待确认" if stock_status == "待确认" else "FALSE",
        "is_zero_budget": "TRUE" if budget_cost == "0" else "FALSE",
        "is_selectable": "TRUE" if can_activate else "FALSE",
        "lifecycle_status": lifecycle_status,
        "stock_status": stock_status,
        "stock_qty": "",
        "budget_band": budget_band(budget_cost),
        "suitable_months": candidate.get("suitable_months", ""),
        "suitable_seasons": "待确认",
        "suitable_events": candidate.get("suitable_events", ""),
        "suitable_persona": "期货交易用户;TradingHero用户",
        "suitable_play_types": candidate.get("suitable_play_types", ""),
        "gift_role": infer_gift_role(category, benefit_type),
        "source_type": "趋势候选人工审核",
        "source_ref": candidate.get("source_platform", ""),
        "confidence": "高" if can_activate else "中",
        "price_source": "人工确认趋势候选",
        "pdf_price_clues": "",
        "needs_manual_review": "FALSE" if can_activate else "TRUE",
        "review_priority": "trend",
        "review_notes": candidate.get("trend_reason", ""),
        "frontend_tags": "趋势候选;可选" if can_activate else "趋势候选;待补成本;不可自动选择",
        "skill_usage_notes": "可用于趋势礼品推荐。" if can_activate else "已确认但缺少成本或库存，不能自动推荐。",
        "notes": review.get("manual_notes", "") or candidate.get("risk_notes", ""),
        "benefit_type": benefit_type,
        "discount_amount": discount_amount,
        "affects_payment_price": affects_payment_price,
        "payment_price_formula": payment_price_formula,
    }
    status = "active" if can_activate else "merged_needs_pricing_or_stock"
    note = "已进入 active。" if can_activate else "已进总库，但缺少预算成本或库存状态不可用，未进入 active。"
    return row, status, note


def build_candidate_lookup(candidates: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row.get("candidate_id", ""): row for row in candidates if row.get("candidate_id")}


def merge_rows(base_rows: list[dict[str, str]], new_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    merged: dict[str, dict[str, object]] = {}
    for row in base_rows:
        key = normalize_name(row.get("gift_name", ""))
        merged[key] = {col: row.get(col, "") for col in LIBRARY_COLUMNS}
    for row in new_rows:
        key = normalize_name(str(row.get("gift_name", "")))
        merged[key] = {col: row.get(col, "") for col in LIBRARY_COLUMNS}
    return list(merged.values())


def build(args: argparse.Namespace) -> dict[str, object]:
    library_path = Path(args.library)
    active_path = Path(args.active_library)
    candidates_path = Path(args.trend_candidates)
    review_path = Path(args.trend_review)
    output_library = Path(args.output_library)
    output_active = Path(args.output_active)
    merge_log_path = Path(args.merge_log)

    library_rows = read_csv(library_path)
    candidate_lookup = build_candidate_lookup(read_csv(candidates_path))
    review_rows = read_csv(review_path)
    merged_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_library_rows: list[dict[str, object]] = []
    log_rows: list[dict[str, object]] = []

    for review in review_rows:
        candidate_id = review.get("candidate_id", "")
        status = review.get("manual_status", "")
        if not status or status == "待确认":
            continue
        if is_rejected(status):
            log_rows.append(
                {
                    "merged_at": merged_at,
                    "candidate_id": candidate_id,
                    "gift_id": "",
                    "gift_name": review.get("gift_name", ""),
                    "manual_status": status,
                    "manual_budget_cost": review.get("manual_budget_cost", ""),
                    "manual_stock_status": review.get("manual_stock_status", ""),
                    "merge_status": "skipped_rejected",
                    "is_selectable": "FALSE",
                    "notes": "人工拒绝或归档，未合并。",
                }
            )
            continue
        if not is_confirmed(status):
            log_rows.append(
                {
                    "merged_at": merged_at,
                    "candidate_id": candidate_id,
                    "gift_id": "",
                    "gift_name": review.get("gift_name", ""),
                    "manual_status": status,
                    "manual_budget_cost": review.get("manual_budget_cost", ""),
                    "manual_stock_status": review.get("manual_stock_status", ""),
                    "merge_status": "skipped_unknown_status",
                    "is_selectable": "FALSE",
                    "notes": "manual_status 不是可识别的纳入状态。",
                }
            )
            continue
        candidate = candidate_lookup.get(candidate_id)
        if not candidate:
            log_rows.append(
                {
                    "merged_at": merged_at,
                    "candidate_id": candidate_id,
                    "gift_id": "",
                    "gift_name": review.get("gift_name", ""),
                    "manual_status": status,
                    "manual_budget_cost": review.get("manual_budget_cost", ""),
                    "manual_stock_status": review.get("manual_stock_status", ""),
                    "merge_status": "skipped_missing_candidate",
                    "is_selectable": "FALSE",
                    "notes": "找不到对应的趋势候选原始行。",
                }
            )
            continue

        new_row, merge_status, note = trend_to_library_row(candidate, review)
        new_library_rows.append(new_row)
        log_rows.append(
            {
                "merged_at": merged_at,
                "candidate_id": candidate_id,
                "gift_id": new_row["gift_id"],
                "gift_name": new_row["gift_name"],
                "manual_status": status,
                "manual_budget_cost": review.get("manual_budget_cost", ""),
                "manual_stock_status": review.get("manual_stock_status", ""),
                "merge_status": merge_status,
                "is_selectable": new_row["is_selectable"],
                "notes": note,
            }
        )

    merged_library = merge_rows(library_rows, new_library_rows)
    active_rows = [
        row
        for row in merged_library
        if row.get("is_selectable") == "TRUE"
        and row.get("lifecycle_status") == "confirmed"
        and row.get("needs_manual_review") == "FALSE"
    ]

    write_csv(output_library, merged_library, LIBRARY_COLUMNS)
    write_csv(output_active, active_rows, LIBRARY_COLUMNS)
    write_csv(merge_log_path, log_rows, MERGE_LOG_COLUMNS)

    if args.update_latest:
        write_csv(library_path, merged_library, LIBRARY_COLUMNS)
        write_csv(active_path, active_rows, LIBRARY_COLUMNS)

    return {
        "library_rows_before": len(library_rows),
        "review_rows": len(review_rows),
        "new_rows": len(new_library_rows),
        "active_rows": len(active_rows),
        "log_rows": len(log_rows),
        "output_library": output_library,
        "output_active": output_active,
        "merge_log": merge_log_path,
        "updated_latest": args.update_latest,
    }


def validate(result: dict[str, object]) -> list[str]:
    output_library = Path(result["output_library"])
    output_active = Path(result["output_active"])
    merge_log = Path(result["merge_log"])
    library_rows = read_csv(output_library)
    active_rows = read_csv(output_active)
    log_rows = read_csv(merge_log)

    assert output_library.exists()
    assert output_active.exists()
    assert merge_log.exists()
    assert len(library_rows) >= int(result["library_rows_before"])
    assert all(row["is_selectable"] == "TRUE" for row in active_rows)
    assert all(row["lifecycle_status"] == "confirmed" for row in active_rows)
    assert all(row["needs_manual_review"] == "FALSE" for row in active_rows)

    return [
        f"library_rows={len(library_rows)}",
        f"active_rows={len(active_rows)}",
        f"merge_log_rows={len(log_rows)}",
        f"new_rows={result['new_rows']}",
        f"updated_latest={result['updated_latest']}",
    ]


def main() -> None:
    args = parse_args()
    result = build(args)
    checks = validate(result)
    print("Trend candidate merge complete")
    for check in checks:
        print(f"- {check}")
    print(f"- output_library={result['output_library']}")
    print(f"- output_active={result['output_active']}")
    print(f"- merge_log={result['merge_log']}")


if __name__ == "__main__":
    main()
