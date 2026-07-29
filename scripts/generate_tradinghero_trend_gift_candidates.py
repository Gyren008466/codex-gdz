from __future__ import annotations

import argparse
import csv
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs" / "tradinghero_gift_library"

RUNS_PATH = OUTPUT_DIR / "gift_trend_update_runs.csv"
CANDIDATES_PATH = OUTPUT_DIR / "gift_trend_candidates.csv"
REVIEW_PATH = OUTPUT_DIR / "gift_trend_candidates_review.csv"


RUN_COLUMNS = [
    "run_id",
    "created_at",
    "activity_date",
    "source_platforms",
    "keywords",
    "budget_range",
    "goal",
    "max_candidates",
    "status",
    "raw_count",
    "candidate_count",
    "error_notes",
]


CANDIDATE_COLUMNS = [
    "candidate_id",
    "run_id",
    "gift_name",
    "normalized_name",
    "source_platform",
    "source_url",
    "source_title",
    "source_rank",
    "reference_price",
    "price_confidence",
    "budget_band",
    "category",
    "benefit_type",
    "suitable_months",
    "suitable_events",
    "suitable_play_types",
    "persona_fit_notes",
    "trend_reason",
    "risk_notes",
    "hot_score",
    "persona_fit_score",
    "cost_control_score",
    "live_show_score",
    "conversion_score",
    "gift_score",
    "manual_status",
    "manual_actual_cost",
    "manual_budget_cost",
    "manual_market_price",
    "manual_stock_status",
    "manual_notes",
    "updated_at",
]


REVIEW_COLUMNS = [
    "candidate_id",
    "gift_name",
    "source_platform",
    "reference_price",
    "budget_band",
    "category",
    "benefit_type",
    "gift_score",
    "trend_reason",
    "persona_fit_notes",
    "risk_notes",
    "manual_status",
    "manual_actual_cost",
    "manual_budget_cost",
    "manual_market_price",
    "manual_stock_status",
    "manual_notes",
]


@dataclass(frozen=True)
class SeedGift:
    name: str
    category: str
    benefit_type: str
    reference_price: int
    keywords: tuple[str, ...]
    months: tuple[int, ...]
    events: tuple[str, ...]
    play_types: tuple[str, ...]
    persona_notes: str
    risk_notes: str
    base_hot: int
    persona_fit: int
    live_show: int
    conversion: int


SEED_GIFTS = [
    SeedGift(
        "桌面静音小风扇",
        "实物",
        "gift",
        79,
        ("夏季", "办公室", "桌面", "实用", "小电器"),
        (5, 6, 7, 8),
        ("夏季直播", "普通周转化", "互动福利"),
        ("二选一", "前N名", "限时福利"),
        "适合长时间看盘用户，实用性强，直播间容易展示。",
        "需要确认噪音、品牌和售后；不要采购过低价劣质款。",
        4,
        4,
        4,
        3,
    ),
    SeedGift(
        "手机平板折叠支架",
        "实物",
        "gift",
        39,
        ("桌面", "办公室", "看盘", "交易员", "支架"),
        tuple(range(1, 13)),
        ("普通直播", "互动福利", "低成本加赠"),
        ("前N名", "保底赠送", "二选一"),
        "适合多屏看盘、手机盯盘用户，和 TradingHero 使用场景贴合。",
        "单价低，感知价值一般，适合做叠加小礼。",
        3,
        5,
        3,
        3,
    ),
    SeedGift(
        "交易复盘笔记本",
        "学习资料",
        "gift",
        49,
        ("交易", "复盘", "学习", "笔记", "计划"),
        tuple(range(1, 13)),
        ("学习种草", "课程承接", "成交后加赠"),
        ("学习礼包", "保底赠送", "前N名"),
        "能把购买理由从礼品拉回交易学习和复盘习惯。",
        "需要定制内容才有差异化，否则像普通笔记本。",
        3,
        5,
        3,
        4,
    ),
    SeedGift(
        "K线形态速查卡",
        "学习资料",
        "gift",
        29,
        ("交易", "学习", "K线", "指标", "速查"),
        tuple(range(1, 13)),
        ("学习种草", "新手转化", "成交后加赠"),
        ("学习礼包", "主播特权", "保底赠送"),
        "和交易学习强相关，适合作为低成本产品相关权益。",
        "内容质量要可靠，避免过度承诺交易效果。",
        3,
        5,
        2,
        4,
    ),
    SeedGift(
        "桌面计时器",
        "实物",
        "gift",
        59,
        ("交易员", "桌面", "办公", "复盘", "时间管理"),
        tuple(range(1, 13)),
        ("交易纪律", "学习种草", "互动福利"),
        ("二选一", "前N名", "学习礼包"),
        "可包装成交易纪律、复盘番茄钟，适合 TradingHero 人群。",
        "需要主播讲清楚使用场景，否则只是普通小物。",
        3,
        4,
        4,
        3,
    ),
    SeedGift(
        "无线鼠标",
        "实物",
        "gift",
        89,
        ("办公室", "桌面", "电脑", "交易员", "实用"),
        tuple(range(1, 13)),
        ("普通直播", "互动福利", "二选一"),
        ("二选一", "抽奖", "前N名"),
        "办公和看盘场景都能理解，实用性强。",
        "品牌、手感和售后差异大，需要人工确认采购款。",
        3,
        4,
        4,
        3,
    ),
    SeedGift(
        "键盘手托",
        "实物",
        "gift",
        49,
        ("办公室", "桌面", "键盘", "交易员", "久坐"),
        tuple(range(1, 13)),
        ("普通直播", "低成本加赠", "互动福利"),
        ("前N名", "二选一", "保底赠送"),
        "适合长时间盯盘和办公，能和桌面套装组合。",
        "展示感一般，适合做组合里的补充礼。",
        2,
        4,
        3,
        2,
    ),
    SeedGift(
        "护眼台灯",
        "实物",
        "gift",
        169,
        ("办公室", "护眼", "桌面", "学习", "看盘"),
        tuple(range(1, 13)),
        ("大促", "主福利位", "抽奖"),
        ("抽奖", "二选一", "前N名"),
        "适合看盘和学习场景，感知价值比小礼品更强。",
        "成本接近预算上限，需确认品牌和采购价。",
        3,
        4,
        4,
        4,
    ),
    SeedGift(
        "迷你筋膜按摩器",
        "实物",
        "gift",
        129,
        ("久坐", "办公室", "健康", "交易员", "实用"),
        tuple(range(1, 13)),
        ("互动福利", "二选一", "大促"),
        ("二选一", "抽奖", "前N名"),
        "适合久坐看盘人群，直播间展示感较好。",
        "品控和售后风险较高，不宜低价盲采。",
        3,
        3,
        4,
        3,
    ),
    SeedGift(
        "保温杯",
        "实物",
        "gift",
        69,
        ("办公室", "实用", "冬季", "桌面", "礼品"),
        (1, 2, 10, 11, 12),
        ("秋冬直播", "普通直播", "低成本加赠"),
        ("前N名", "保底赠送", "二选一"),
        "通用实用礼品，适合秋冬和办公场景。",
        "和 TradingHero 产品关联较弱，需搭配学习资料。",
        3,
        3,
        3,
        2,
    ),
    SeedGift(
        "100元京东E卡",
        "优惠券",
        "voucher",
        100,
        ("京东", "E卡", "卡券", "现金感", "100元"),
        tuple(range(1, 13)),
        ("冲GMV", "大促", "互动二选一"),
        ("二选一", "前N名", "主播特权"),
        "现金感强，用户容易理解；不改变软件支付价。",
        "不能说成降价，只能说加赠卡券。",
        4,
        4,
        5,
        5,
    ),
    SeedGift(
        "200元京东卡",
        "优惠券",
        "voucher",
        200,
        ("京东", "卡券", "现金感", "200元", "大促"),
        tuple(range(1, 13)),
        ("冲GMV", "大促", "互动二选一"),
        ("二选一", "抽奖", "前N名"),
        "现金感强，适合做主福利位；不改变软件支付价。",
        "预算消耗高，需要控制名额或用于大促。",
        4,
        4,
        5,
        5,
    ),
    SeedGift(
        "100元立减金",
        "立减金",
        "price_discount",
        100,
        ("立减", "现金感", "100元", "冲GMV", "限时"),
        tuple(range(1, 13)),
        ("冲GMV", "限时秒杀", "主播特权"),
        ("限时立减", "前N名", "二选一"),
        "直接降低支付价，适合推动临门一脚转化。",
        "会改变最终支付价和 GMV 计算口径。",
        4,
        5,
        4,
        5,
    ),
    SeedGift(
        "200元立减金",
        "立减金",
        "price_discount",
        200,
        ("立减", "现金感", "200元", "冲GMV", "限时"),
        tuple(range(1, 13)),
        ("冲GMV", "限时秒杀", "大促"),
        ("限时立减", "前N名", "二选一"),
        "直接降低支付价，表达最简单，适合冲 GMV 主福利位。",
        "预算消耗到上限，必须明确最终支付价。",
        4,
        5,
        4,
        5,
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate TradingHero trend gift candidate CSV files.")
    parser.add_argument("--activity-date", required=True, help="Activity date, e.g. 2026-07-15")
    parser.add_argument("--budget-range", required=True, help="Budget range, e.g. 150-200")
    parser.add_argument("--goal", required=True, help="Goal, e.g. 冲GMV")
    parser.add_argument("--keywords", required=True, help="Comma/semicolon separated keywords")
    parser.add_argument("--source-platforms", default="manual_keyword_seed", help="Source platform labels")
    parser.add_argument("--max-candidates", type=int, default=30)
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--append", action="store_true", help="Append to existing trend CSVs instead of replacing current generated candidates")
    return parser.parse_args()


def read_existing(path: Path) -> list[dict[str, str]]:
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


def stable_id(text: str, prefix: str) -> str:
    digest = hashlib.md5(text.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


def split_keywords(text: str) -> list[str]:
    parts = re.split(r"[,，;；、\n]+", text)
    return [part.strip() for part in parts if part.strip()]


def parse_month(activity_date: str) -> int:
    return datetime.strptime(activity_date, "%Y-%m-%d").month


def parse_budget_range(text: str) -> tuple[int, int]:
    numbers = [int(x) for x in re.findall(r"\d+", text)]
    if not numbers:
        return 0, 10_000
    if len(numbers) == 1:
        return 0, numbers[0]
    return min(numbers[0], numbers[1]), max(numbers[0], numbers[1])


def budget_band(price: int) -> str:
    if price <= 0:
        return "0"
    if price <= 50:
        return "1-50"
    if price <= 100:
        return "51-100"
    if price <= 150:
        return "101-150"
    if price <= 200:
        return "151-200"
    return "200+"


def month_reason(month: int) -> str:
    if month in (5, 6, 7, 8):
        return "当前处于夏季/618后延续期，实用桌面、清凉小电器、现金感福利更容易被理解。"
    if month in (11, 12):
        return "年终和双11/双12节点，现金感、复盘学习、新年准备类礼品更合适。"
    if month in (1, 2):
        return "新年和春节前后，财运寓意、开工学习、现金感福利更合适。"
    if month == 3:
        return "适合周年庆、开春学习、工具升级类表达。"
    if month in (9, 10):
        return "适合金九银十、学习重启、办公桌面升级类表达。"
    return "普通月份，优先选择交易学习、桌面办公和现金感福利。"


def score_seed(seed: SeedGift, keywords: list[str], month: int, budget_low: int, budget_high: int, goal: str) -> tuple[int, int, int, int, int, int, str]:
    keyword_blob = " ".join(keywords).lower()
    matched_keywords = [kw for kw in seed.keywords if kw.lower() in keyword_blob or any(kw in user_kw for user_kw in keywords)]
    keyword_bonus = min(2, len(matched_keywords))

    hot = min(5, seed.base_hot + (1 if month in seed.months else 0) + (1 if matched_keywords else 0))
    persona = seed.persona_fit
    live_show = seed.live_show
    conversion = seed.conversion

    if "GMV" in goal.upper() or "冲" in goal:
        if seed.benefit_type in {"price_discount", "voucher"}:
            conversion = min(5, conversion + 1)
        if seed.reference_price > budget_high:
            conversion = max(1, conversion - 1)

    if budget_low <= seed.reference_price <= budget_high:
        cost_control = 5
    elif seed.reference_price <= budget_high:
        cost_control = 4
    elif seed.reference_price <= budget_high + 50:
        cost_control = 2
    else:
        cost_control = 1

    if matched_keywords:
        persona = min(5, persona + 1)

    gift_score = hot * 15 + persona * 25 + cost_control * 20 + live_show * 15 + conversion * 25
    # Normalize from 0-500 to 0-100.
    gift_score = round(gift_score / 5)
    if seed.benefit_type in {"voucher", "price_discount"}:
        # Existing internal rules are useful benchmarks, but trend discovery should not be
        # dominated by benefits already present in the active library.
        gift_score = max(0, gift_score - 8)
    match_text = "、".join(matched_keywords) if matched_keywords else "通用候选"
    return hot, persona, cost_control, live_show, conversion, gift_score, match_text


def source_platform_for(seed: SeedGift, source_platforms: str) -> str:
    if seed.benefit_type in {"voucher", "price_discount"}:
        return "internal_rule"
    return source_platforms or "manual_keyword_seed"


def build_candidates(args: argparse.Namespace) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]]]:
    output_dir = Path(args.output_dir)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    month = parse_month(args.activity_date)
    keywords = split_keywords(args.keywords)
    budget_low, budget_high = parse_budget_range(args.budget_range)
    run_id = stable_id(f"{now}|{args.activity_date}|{args.budget_range}|{args.goal}|{args.keywords}", "trend_run")

    rows: list[dict[str, object]] = []
    raw_ranked: list[tuple[int, SeedGift, tuple[int, int, int, int, int, int, str]]] = []
    for seed in SEED_GIFTS:
        scores = score_seed(seed, keywords, month, budget_low, budget_high, args.goal)
        hot, persona, cost, show, conversion, total, match_text = scores
        # Keep loose candidates, but drop very off-budget low-fit items.
        if total < 55 and seed.reference_price > budget_high:
            continue
        raw_ranked.append((total, seed, scores))

    raw_ranked.sort(key=lambda item: (-item[0], item[1].reference_price, item[1].name))
    selected = raw_ranked[: args.max_candidates]

    for rank, (total, seed, scores) in enumerate(selected, start=1):
        hot, persona, cost, show, conversion, gift_score, match_text = scores
        trend_reason = f"{month_reason(month)}关键词匹配：{match_text}。"
        if seed.benefit_type == "price_discount":
            trend_reason += " 这是价格影响型福利，会直接降低最终支付价。"
        elif seed.benefit_type == "voucher":
            trend_reason += " 这是现金感卡券，不改变 TradingHero 支付价。"

        row = {
            "candidate_id": stable_id(f"{run_id}|{seed.name}", "trend_candidate"),
            "run_id": run_id,
            "gift_name": seed.name,
            "normalized_name": re.sub(r"\s+", "", seed.name),
            "source_platform": source_platform_for(seed, args.source_platforms),
            "source_url": "",
            "source_title": f"CSV最小实现候选：{seed.name}",
            "source_rank": rank,
            "reference_price": seed.reference_price,
            "price_confidence": "中" if seed.benefit_type in {"voucher", "price_discount"} else "低",
            "budget_band": budget_band(seed.reference_price),
            "category": seed.category,
            "benefit_type": seed.benefit_type,
            "suitable_months": ";".join(str(m) for m in seed.months),
            "suitable_events": ";".join(seed.events),
            "suitable_play_types": ";".join(seed.play_types),
            "persona_fit_notes": seed.persona_notes,
            "trend_reason": trend_reason,
            "risk_notes": seed.risk_notes,
            "hot_score": hot,
            "persona_fit_score": persona,
            "cost_control_score": cost,
            "live_show_score": show,
            "conversion_score": conversion,
            "gift_score": gift_score,
            "manual_status": "待确认",
            "manual_actual_cost": "",
            "manual_budget_cost": "",
            "manual_market_price": "",
            "manual_stock_status": "待确认",
            "manual_notes": "",
            "updated_at": now,
        }
        rows.append(row)

    review_rows = [{col: row.get(col, "") for col in REVIEW_COLUMNS} for row in rows]
    run_row = {
        "run_id": run_id,
        "created_at": now,
        "activity_date": args.activity_date,
        "source_platforms": args.source_platforms,
        "keywords": ";".join(keywords),
        "budget_range": args.budget_range,
        "goal": args.goal,
        "max_candidates": args.max_candidates,
        "status": "success",
        "raw_count": len(raw_ranked),
        "candidate_count": len(rows),
        "error_notes": "",
    }
    return run_row, rows, review_rows


def merge_by_id(existing: list[dict[str, str]], new_rows: list[dict[str, object]], id_col: str) -> list[dict[str, object]]:
    merged: dict[str, dict[str, object]] = {str(row.get(id_col, "")): dict(row) for row in existing if row.get(id_col)}
    for row in new_rows:
        merged[str(row[id_col])] = row
    return list(merged.values())


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    global RUNS_PATH, CANDIDATES_PATH, REVIEW_PATH
    RUNS_PATH = output_dir / "gift_trend_update_runs.csv"
    CANDIDATES_PATH = output_dir / "gift_trend_candidates.csv"
    REVIEW_PATH = output_dir / "gift_trend_candidates_review.csv"

    run_row, candidate_rows, review_rows = build_candidates(args)

    runs = read_existing(RUNS_PATH)
    runs.append(run_row)
    if args.append:
        candidates = merge_by_id(read_existing(CANDIDATES_PATH), candidate_rows, "candidate_id")
        reviews = merge_by_id(read_existing(REVIEW_PATH), review_rows, "candidate_id")
    else:
        candidates = candidate_rows
        reviews = review_rows

    write_csv(RUNS_PATH, runs, RUN_COLUMNS)
    write_csv(CANDIDATES_PATH, candidates, CANDIDATE_COLUMNS)
    write_csv(REVIEW_PATH, reviews, REVIEW_COLUMNS)

    print("Generated TradingHero trend gift candidates")
    print(f"- run_id={run_row['run_id']}")
    print(f"- candidates={len(candidate_rows)}")
    print(f"- runs_path={RUNS_PATH}")
    print(f"- candidates_path={CANDIDATES_PATH}")
    print(f"- review_path={REVIEW_PATH}")


if __name__ == "__main__":
    main()
