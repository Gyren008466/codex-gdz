# Prediction Rules

Use similar historical cases, not machine learning.

## Prediction Target

Predict only:

- TradingHero flagship yearly membership GMV.
- TradingHero flagship yearly membership sales count.

Do not predict flagship monthly membership.

## Similar Case Selection

Use this order:

1. Product phase: prefer flagship yearly membership cases.
2. Goal: GMV sprint, sales sprint, lead capture, or interaction.
3. Price band.
4. Actual Excel play tags.
5. Event timing: normal week, month-end, major promotion, holiday, market-event night.
6. UV/scanning/watch-time context when available.

If fewer than 3 similar cases exist, say the prediction is low-confidence.

## GMV Bands

Output 3 bands:

- Conservative: median of similar cases or a lower historical reference when confidence is weak.
- Target: around the 75th percentile of similar cases.
- Aggressive: top-case reference only when low price, strong event, urgency, and follow-up are all present.

Never present aggressive GMV as the default expectation.

## Sales Estimate

Base formula:

`expected sales = expected GMV / base price`

Adjustment:

- Lower price can raise sales count, but does not automatically raise total GMV.
- Price above 3090 without course/private-domain follow-up should reduce sales expectation.
- If benefits are complex but price reason is weak, reduce conversion confidence.
- If historical cases include high-UV zero-sales examples, warn that traffic alone may not convert.

## Confidence Labels

Use:

- High confidence: at least 5 similar actual Excel cases and no major conflict.
- Medium confidence: 3-4 similar cases or partly different product phase.
- Low confidence: fewer than 3 cases, mostly PDF inspiration, or cross-phase analogy from 2024 professional/monthly cases.

Always include the confidence label with each plan's forecast.

## Risk Warnings

Warn when:

- Base price is above 3090 and benefits are ordinary gifts.
- User asks for high GMV but disallows discount, flash sale, urgency, and scarcity.
- Gift mechanics are the main hook.
- Budget cannot support promised benefits.
- The best matching historical cases are low-confidence or PDF-only.
- Similar plays have high UV but zero sales.

