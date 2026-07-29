# Output Template

Use Chinese for user-facing plans unless the user asks otherwise.

Start with one compact setup summary:

- 活动日期/时间背景。
- 是否参考历史：参考历史 / 不参考历史 / 混合模式。
- 基础售价与折扣：基础售价 / 3690。
- 福利预算区间。
- 目标：冲GMV、冲销量、前置蓄水、互动增强。
- 主要假设：只写缺失输入导致的假设。

Then output exactly 3 plans unless the user asks for a different count.

```markdown
## 方案 A：{稳健方案名}

- 定位：稳健
- 适用场景：
- 基础售价：{base_price} 元，约 {discount_rate} 折
- 立减金：无 / 100 元 / 200 元
- 最终支付价：{base_price} - {discount_amount} = {final_price} 元
- 叠加福利：
- 福利预算消耗：
- 直播节奏：
- 历史参考 / 创意参考：
- 预期旗舰年销量：
  - 保守：
  - 目标：
  - 激进：
- 预期 GMV：
  - 保守：
  - 目标：
  - 激进：
- GMV 计算口径：如果使用立减金，按最终支付价计算；否则按基础售价计算。
- 预测置信度：
- 成交逻辑：
- 风险提示：
- 主播口播要点：

## 方案 B：{冲刺方案名}

- 定位：冲刺
- 适用场景：
- 基础售价：{base_price} 元，约 {discount_rate} 折
- 立减金：无 / 100 元 / 200 元
- 最终支付价：{base_price} - {discount_amount} = {final_price} 元
- 叠加福利：
- 福利预算消耗：
- 直播节奏：
- 历史参考 / 创意参考：
- 预期旗舰年销量：
  - 保守：
  - 目标：
  - 激进：
- 预期 GMV：
  - 保守：
  - 目标：
  - 激进：
- GMV 计算口径：如果使用立减金，按最终支付价计算；否则按基础售价计算。
- 预测置信度：
- 成交逻辑：
- 风险提示：
- 主播口播要点：

## 方案 C：{互动方案名}

- 定位：互动
- 适用场景：
- 基础售价：{base_price} 元，约 {discount_rate} 折
- 立减金：无 / 100 元 / 200 元
- 最终支付价：{base_price} - {discount_amount} = {final_price} 元
- 叠加福利：
- 福利预算消耗：
- 直播节奏：
- 历史参考 / 创意参考：
- 预期旗舰年销量：
  - 保守：
  - 目标：
  - 激进：
- 预期 GMV：
  - 保守：
  - 目标：
  - 激进：
- GMV 计算口径：如果使用立减金，按最终支付价计算；否则按基础售价计算。
- 预测置信度：
- 成交逻辑：
- 风险提示：
- 主播口播要点：

## 推荐优先级

- 首推：
- 备选：
- 不建议：
```

## Style Rules

- Be concrete, not slogan-like.
- Use exact prices, discount rates, benefit quantities, and final payment prices.
- Do not confuse 京东卡 with 立减金:
  - 京东卡 does not change payment price.
  - 立减金 changes payment price and GMV calculation basis.
- Keep host talking points short enough to use directly.
- Separate data fact from assumption.
- Do not overpromise forecast accuracy.
