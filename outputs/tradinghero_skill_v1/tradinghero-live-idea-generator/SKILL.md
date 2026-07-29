---
name: tradinghero-live-idea-generator
description: "Generate TradingHero flagship yearly live-marketing plans from historical campaign data."
---

# TradingHero Live Idea Generator

Use this skill when the user asks to plan TradingHero live-marketing activities, generate "鬼点子" campaign options, estimate GMV/sales for flagship yearly membership, or reuse historical TradingHero campaign patterns.

## Required Input

Ask for missing high-impact inputs only when they are not provided:

- Activity date or timing context.
- Base price for TradingHero flagship yearly membership. Original price is 3690.
- Benefit budget range, preferably in 50 yuan increments.
- Goal: `冲GMV`, `冲销量`, `前置蓄水`, or `互动增强`.

Optional inputs:

- Whether low-price flash sale is allowed.
- Whether extra membership months are allowed.
- Available gift pool.
- Whether course/private-domain/customer-service follow-up is available.

## Workflow

1. Read `references/historical-findings.md`.
2. Read `references/generation-rules.md`.
3. Read `references/prediction-rules.md`.
4. Use Excel-derived actual-play rules as the evidence base. Treat PDF-derived ideas only as inspiration.
5. Generate exactly 3 plans: stable, sprint, and interactive.
6. For each plan, include price/discount, stacked benefits, live rhythm, historical cases, expected flagship-year sales, expected GMV, logic, risks, and host talking points.
7. End with a clear recommendation priority.

## Evidence Rules

- Excel `直播活动玩法简介` is the actual execution source of truth.
- PDF plans are background and idea sources; do not use them as proof of effectiveness when they conflict with Excel.
- Predict only flagship yearly membership GMV and sales.
- Do not use flagship monthly membership as the target metric.
- 2024 professional-version and monthly-fee examples may inspire education/private-domain flow, but do not directly predict flagship yearly GMV from them.

## Output

Follow `references/output-template.md`.

Always separate:

- Data facts.
- Reasoned assumptions.
- Recommendation.
- Risk warnings.

