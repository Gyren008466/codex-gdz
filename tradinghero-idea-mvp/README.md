# TradingHero 鬼点子生成器 MVP

本地可用 MVP：前端页面 + Node 原生轻量后端，不依赖 npm 安装。

## 启动

```powershell
& 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' 'D:\Desktop\codex gdz\tradinghero-idea-mvp\server.js'
```

然后打开：

```text
http://localhost:5177
```

## 已实现

- 读取 `outputs/tradinghero_gift_library/gift_library_latest_active.csv` 作为正式礼品库。
- 输入活动日期、售价、福利预算、目标、模式、是否允许立减金、是否允许趋势礼品。
- 生成 3 个方案：稳妥复用型、冲 GMV 型、互动创意型。
- 立减金会改变最终支付价和 GMV 计算口径。
- 展示正式礼品库，可按礼品类型和来源筛选。
- 调用现有趋势候选脚本生成候选礼品。
- 支持保存候选审核字段，并把确认候选合并进正式礼品库。

## 注意

- 第一版是规则型生成器，不接真实平台抓取，也不调用大模型。
- 趋势礼品必须人工审核后才能进入正式礼品库。
- 合并趋势候选会更新 `gift_library_latest.csv` 和 `gift_library_latest_active.csv`。
