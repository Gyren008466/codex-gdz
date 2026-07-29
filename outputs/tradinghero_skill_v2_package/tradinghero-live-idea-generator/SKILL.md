---
name: tradinghero-live-idea-generator
description: "Generate TradingHero flagship yearly live-marketing plans with historical evidence, gift-library rules, and optional creative expansion."
---

# TradingHero Live Idea Generator

Use this skill when the user asks to generate TradingHero live-marketing ideas, "鬼点子" campaign options, flagship yearly membership plans, GMV/sales forecasts, live-room benefit stacks, or gift recommendations.

## Required Inputs

Ask for missing high-impact inputs only when they are not provided:

- Activity date or timing context.
- Base price for TradingHero flagship yearly membership. Original price is 3690.
- Benefit budget range, preferably in 50 yuan increments.
- Goal: `冲GMV`, `冲销量`, `前置蓄水`, or `互动增强`.
- Historical mode:
  - `参考历史`: prioritize Excel/PDF-derived TradingHero patterns.
  - `不参考历史`: allow broader live-commerce creativity and market-style mechanics.
  - `混合模式`: use TradingHero evidence as the floor, then add fresh mechanics.

Optional inputs:

- Whether low-price flash sale is allowed.
- Whether extra membership months are allowed.
- Whether price-affecting benefits such as 100/200 yuan 立减金 are allowed.
- Available gift pool or inventory constraints.
- Whether course/private-domain/customer-service follow-up is available.

## Workflow

1. Read `references/historical-findings.md`.
2. Read `references/generation-rules.md`.
3. Read `references/prediction-rules.md`.
4. Read `references/gift-library-rules.md`.
5. Read `references/date-season-rules.md` when activity date is provided.
6. Read `references/market-creativity-rules.md` when historical mode is `不参考历史` or `混合模式`.
7. Use Excel-derived actual-play rules as the evidence base when historical mode includes history. Treat PDF-derived ideas as inspiration unless confirmed in Excel.
8. Generate exactly 3 plans by default: stable, sprint, and interactive.
9. For each plan, include price/discount, stacked benefits, final payment price when applicable, live rhythm, historical or creative reference, expected flagship-year sales, expected GMV, logic, risks, and host talking points.
10. End with a clear recommendation priority.

## Gift Library Rules

- Prefer `assets/gift_library_latest_active.csv` as the active selectable gift pool.
- Only use rows with `is_selectable=TRUE`.
- Never auto-recommend rows with `needs_manual_review=TRUE`.
- Use `budget_cost` to consume benefit budget. Do not use `market_price` as cost.
- `benefit_type=gift`: normal physical/product-related gift; does not change payment price.
- `benefit_type=voucher`: card/coupon benefit such as 京东卡; does not change payment price.
- `benefit_type=price_discount`: 立减金; directly changes final payment price.
- For 立减金:
  - `discount_amount=100` means final payment price = base price - 100.
  - `discount_amount=200` means final payment price = base price - 200.
  - GMV forecast must use final payment price, not the pre-discount base price.
  - Benefit budget still consumes the face value, e.g. 200 元立减金 consumes 200 yuan budget.

## Evidence Rules

- Excel `直播活动玩法简介` is the actual execution source of truth.
- PDF plans are background and idea sources; do not use them as proof of effectiveness when they conflict with Excel.
- Predict only TradingHero flagship yearly membership GMV and sales.
- Do not use flagship monthly membership as the target metric.
- 2024 professional-version and monthly-fee examples may inspire education/private-domain flow, but do not directly predict flagship yearly GMV from them.

## Output

Follow `references/output-template.md`.

Always separate:

- Data facts.
- Reasoned assumptions.
- Recommendation.
- Risk warnings.
