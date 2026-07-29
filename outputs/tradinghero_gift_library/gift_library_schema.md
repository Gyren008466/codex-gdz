# TradingHero 礼品库 v1.1 字段说明

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
