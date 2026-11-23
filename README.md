# 定投罗盘 · DCA Compass

五资产智能定投评分站：每天给 BTC / 黄金 / 纳斯达克100 / 标普500 / 沪深300 算一个
0–100 的估值综合分，并按各资产自己的映射表换算成本周定投倍数，附 2015 年至今的
回测（策略定投 vs 普通定投 vs 买入持有）、QDII 美股基金清单与懒人组合回测。

功能结构对标 btcdca.me（页面、区块顺序、维度与权重、倍数映射），全部代码与文案为
原创实现；视觉主题为本站自有设计。

## 架构

```
            ┌──────────── frontend (React + Vite + TS + ECharts) ───────────┐
  浏览器 ──▶ │  pages: Home / AssetPage / Funds / Lazy / Portfolio / Manual   │
            │  components: Nav / TickerTape / Gauge / Radar / Heatmap / ...  │
            └──────────────────────────┬─────────────────────────────────────┘
                                       │ REST  /api/v1/*
            ┌──────────────────────────▼─────────────────────────────────────┐
            │ backend (FastAPI, 分层)                                     │
            │  api/routes ─▶ cache (每日文件缓存) ─▶ services             │
            │    ├─ providers/  Yahoo · CoinMetrics · alternative.me      │
            │    │              FRED · 东方财富                            │
            │    ├─ indicators  RSI/MACD/布林/波动率/百分位（纯函数）      │
            │    ├─ scoring     维度 → 百分位分 → 加权综合 → 倍数映射      │
            │    ├─ backtest    周频定投回测（扩张窗口，无未来函数）       │
            │    ├─ funds       QDII 基金净值统计（东方财富）              │
            │    └─ portfolios  10 个懒人组合季度再平衡回测                │
            └─────────────────────────────────────────────────────────────────┘
```

## 运行

后端：

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --port 8000     # http://localhost:8000/docs
.venv/bin/python -m pytest                      # 单元测试
```

前端：

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 （默认连 localhost:8000 的 API）
npm run build      # 类型检查 + 生产构建
```

或一键：`docker compose up --build`（前端 http://localhost:8080 ，nginx 反代 /api）。

首次访问数据接口会抓取全部历史行情并计算（约 2–4 分钟），结果缓存到
`backend/data/cache/`，每天自动刷新一次。

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/health` | 健康检查 |
| GET | `/api/v1/assets` | 五资产摘要（价格/评分/倍数/区间） |
| GET | `/api/v1/assets/{id}` | 资产详情：维度、回测全量图表数据、映射表、风控 |
| GET | `/api/v1/signals/weekly` | 本周定投信号表 |
| GET | `/api/v1/funds?kind=active\|passive` | QDII 基金列表（主动 23 / 被动 16） |
| GET | `/api/v1/funds/{code}` | 基金详情（业绩/风险/配置/经理） |
| GET | `/api/v1/portfolios` | 10 个懒人组合回测摘要 |
| GET | `/api/v1/portfolios/{id}` | 组合详情（配置/年度回报） |

## 方法论

- 每个维度取当前原始值在自身历史中的百分位 → 0–100 分（越便宜/机会越大分越高）；
  维度数据源不可达时该维度记为 unavailable，剩余维度权重重新归一化到 100%，不编造数据。
- 倍数映射每资产一张表（BTC 分段线性 0.10–3.00x、黄金阶梯、纳指 0–2.50x、
  标普 0–2.25x、沪深300 公式 M = 0.2 + (Score − 25) × 0.024），展示与回测共用同一函数。
- 回测：每周定投基准 100，历史评分由价格派生维度以扩张窗口百分位合成，无未来函数。
- 数据源（全部免费无 key）：Yahoo Finance、CoinMetrics community、alternative.me、
  FRED fredgraph、东方财富。各维度的具体来源见资产页与 `docs/FEATURE_PARITY.md`。

## 目录

- `backend/` FastAPI 后端（app/api、app/services、app/schemas、app/core、tests）
- `frontend/` React 前端（src/pages、src/components、src/api）
- `docs/FEATURE_PARITY.md` 与原站的功能对标清单（done / partial / unavailable 及原因）
- `V2_BUILD_REPORT.md` 本次构建与验证报告

本项目仅为历史数据回测与定投纪律工具，不构成投资建议。
