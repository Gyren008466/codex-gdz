# TradingHero 礼品库 v1.2 字段说明

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
