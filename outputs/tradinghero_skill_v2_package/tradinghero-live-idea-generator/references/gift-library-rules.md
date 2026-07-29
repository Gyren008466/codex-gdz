# Gift Library Rules

Use these rules whenever a plan includes gifts, coupons, 立减金, or benefit-budget matching.

## Assets

- Active selectable pool: `assets/gift_library_latest_active.csv`.
- Full pool with pending rows: `assets/gift_library_latest.csv`.
- Review application log: `assets/gift_library_v1_2_review_applied.csv`.

Prefer the active file for generation. The full file is for explanation or manual review only.

## Selection Rules

- Only recommend rows where `is_selectable=TRUE`.
- Do not recommend rows where `needs_manual_review=TRUE`.
- Do not use PDF price clues as actual cost.
- Use `budget_cost` to consume the user's benefit budget.
- Use `market_price` only as perceived value, not as cost.
- When budget is tight, stack zero-budget inventory gifts first.

## Benefit Types

`benefit_type=gift`:

- Normal gift, study material, physical item, or inventory item.
- Does not change software payment price.
- Good for perceived value, interactivity, and product education.

`benefit_type=voucher`:

- Card/coupon style benefit, such as 京东卡.
- Actual value and budget cost usually equal the face value.
- Does not change TradingHero payment price.
- GMV forecast still uses the base software payment price.

`benefit_type=price_discount`:

- Price-affecting benefit, currently 100 元立减金 and 200 元立减金.
- Directly reduces the customer payment price.
- Must be shown separately from ordinary gifts.
- GMV forecast must use the final payment price after discount.

## 立减金 Rules

- 100 元立减金:
  - `budget_cost=100`.
  - `discount_amount=100`.
  - `final_price = base_price - 100`.
- 200 元立减金:
  - `budget_cost=200`.
  - `discount_amount=200`.
  - `final_price = base_price - 200`.

Example:

- Base price: 3250.
- 200 元立减金: final payment price is 3050.
- Forecast GMV should use 3050 times expected flagship-year sales.

## Output Requirements

When a plan uses 立减金, output all of these:

- Base price.
- 立减金额.
- Final payment price.
- Benefit budget consumed.
- GMV calculation basis.

Do not merge 立减金 and 京东卡 in the wording:

- 京东卡 is an extra benefit and does not lower payment price.
- 立减金 lowers payment price and affects GMV.

## Current Active Gift Pool

Known active rows include:

- 好用的指标手册: 0 yuan budget, study material.
- 黄金手机贴: 0 yuan budget, physical gift.
- 马年钥匙扣: 0 yuan budget, physical gift.
- 订单流桌垫: 0 yuan budget, study material.
- 黄金知识桌垫: 0 yuan budget, study material.
- 100元京东E卡: 100 yuan budget, voucher.
- 200元京东卡: 200 yuan budget, voucher.
- 100元立减金: 100 yuan budget, price discount.
- 200元立减金: 200 yuan budget, price discount.
