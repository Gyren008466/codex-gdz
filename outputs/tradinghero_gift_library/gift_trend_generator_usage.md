# TradingHero 趋势候选礼品生成器使用说明

## 作用

这是礼品库 v2 的最小实现。它不接真实平台，不联网抓取，而是根据：

- 活动日期
- 福利预算
- 活动目标
- 关键词

从内置的 TradingHero 适配礼品种子库中生成一批趋势候选礼品，并输出评分表，供人工审核流程验证。

## 运行命令示例

```powershell
& 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  'D:\Desktop\codex gdz\scripts\generate_tradinghero_trend_gift_candidates.py' `
  --activity-date '2026-07-15' `
  --budget-range '150-200' `
  --goal '冲GMV' `
  --keywords '夏季办公室礼品,交易员桌面用品,100元礼品,京东E卡,立减金' `
  --source-platforms 'manual_keyword_seed' `
  --max-candidates 20
```

## 输出文件

- `gift_trend_update_runs.csv`：每次更新记录。
- `gift_trend_candidates.csv`：完整趋势候选表。
- `gift_trend_candidates_review.csv`：人工审核视图表。

## 审核方式

优先打开：

`gift_trend_candidates_review.csv`

按 `gift_score` 从高到低看，重点填写：

- `manual_status`
- `manual_actual_cost`
- `manual_budget_cost`
- `manual_market_price`
- `manual_stock_status`
- `manual_notes`

只有人工补齐 `manual_budget_cost` 并确认纳入后，候选礼品才应该进入正式礼品库。

## 注意

- 当前版本是 CSV 最小实现，不代表真实平台热销。
- `reference_price` 是脚本种子参考价，不能直接当采购成本。
- 京东卡不改变支付价。
- 立减金会改变支付价和 GMV 计算口径。
- 趋势候选默认 `manual_status=待确认`，不能自动推荐。

