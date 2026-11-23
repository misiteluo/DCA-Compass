# 定投罗盘 DCA Compass — v2 构建报告

构建日期：2026-11-23。v1（单脚本 + 静态站）已按用户指示直接丢弃（其代码仍在
GitHub 仓库历史中），仓库已按标准前后端项目重构。未推送 GitHub、未部署，等上级复核。

## 技术栈与结构

- 后端：FastAPI + Pydantic，Python 3.12，分层 `app/api/routes`（assets/signals/
  funds/portfolios/health）、`app/services`（providers/yahoo、providers/external、
  indicators、scoring、backtest、market、funds、portfolios）、`app/schemas`、
  `app/core/config`、`app/cache.py`（每日文件缓存）。抓取全部用标准库 urllib，
  运行时依赖只有 fastapi/uvicorn。
- 前端：React 18 + Vite 5 + TypeScript + ECharts 5，react-router 路由；
  pages（Home/AssetPage/Funds/Lazy/PortfolioDetail/Manual）+ components
  （Nav/TickerTape/ScoreGauge/DimensionCard/Charts/Heatmap/SignalFeed/Drawer）+
  `src/api/client.ts`。前端只渲染 API 数据，无硬编码分数。深色自有主题。
- 部署：`docker-compose.yml`（backend :8000 + frontend nginx :8080，/api 反代）。

## 当日评分（2026-11-23，真实数据）

BTC 86.1 → 2.03x（极度低估）· 黄金 62.0 → 1.50x（合理）· 纳指 82.0 → 1.86x（低估）·
标普 64.2 → 1.43x（合理）· 沪深300 63.2 → 1.12x（合理）。
已逐一核对：倍数 = 各资产映射函数（评分），/assets 与 /assets/{id} 五资产全部一致。

## 维度覆盖（live / 总数，其余如实标 unavailable 并权重归一化）

- BTC 6/7：AHR999、MVRV Z（CoinMetrics）、MA200、FGI（alternative.me）、
  Puell（CoinMetrics IssTotUSD）、算力丝带（CoinMetrics HashRate）live；
  Reserve Risk 需付费链上数据，未接入。
- 黄金 6/7：DXY、MA200、RSI、VIX、MACD、季节性 live；TIPS（FRED DFII10 已接入代码，
  本机网络访问 FRED 多次超时，恢复即自动 live）。
- 纳指 9/12（+AAII 权重 0 待接入）：价格派生 6 维 + VIX + 美债10Y + 美元 + FGI live；
  PE/PB 无免费可靠历史序列。
- 标普 3/10：RSI、FGI（VIX 情绪代理）、宏观利率 live；PE/CAPE/巴菲特/ROE/ETF 流/
  PMI/GPR 无免费结构化来源（巴菲特已写 FRED 对接，同样受 FRED 超时影响）。
- 沪深300 4/10：趋势、波动率、拥挤度（成交量）、牛熊位置 live；估值/股息
  （东方财富指数接口 502）、盈利、资金流、宏观、行业无免费可靠来源。
- 细节与原因逐项见 `docs/FEATURE_PARITY.md`。

## 回测与组合/基金

- 五资产回测（2015→最新，周频，扩张窗口无未来函数）：含三策略对比、年度/月度/
  滚动/分布/增长曲线/压力测试窗口，全部由真实价格计算。注：本口径下 BTC 策略
  DCA（+1,530%）低于普通 DCA（+2,064%），页面如实展示，未做挑选。
- 懒人组合 10/10 全部真实回测（2017+，季度再平衡）：如巴菲特 90/10 年化 10.91% /
  回撤 −25.10%，60/40 年化 6.98%。
- 基金：主动 23 只 + 被动 16 只（纳指100指数 C 类，代码经东方财富目录逐一核对），
  成立至今/年化/回撤/当日涨跌/规模/经理/配置均由真实净值（pingzhongdata）计算，
  如广发全球精选 270023 成立至今 +405.84%、规模 159.07 亿、经理李耀柱。
  日限额与费率表数据源不提供，显示 -- 并注明。

## 验证结果

- 后端测试：`python -m pytest` → 9 passed（倍数映射五资产、百分位方向与边界、
  权重合计 100% 与归一化、回测无未来函数、最大回撤）。
- API：13 个端点全部 HTTP 200（health、assets、assets×5、signals/weekly、
  funds 主动/被动、funds/270023、portfolios、portfolios/all-weather）；
  /assets 与 /assets/{id} 评分/倍数一致性 5/5。
- 前端：`npm install && npm run build` 成功（仅 ECharts 包体积警告）；
  `vite preview` 首页 HTTP 200。
- 首次冷启动构建约 2–4 分钟（FRED 超时重试 + 全量回测），之后走每日缓存，秒级。

## 运行命令

```bash
cd backend && .venv/bin/uvicorn app.main:app --port 8000   # 或 pip install -r requirements.txt 后 uvicorn
cd frontend && npm run dev        # :5173
# 或 docker compose up --build   # 前端 :8080
```

## 已知待办（v2.1 候选）

- FRED 网络恢复后 TIPS 与巴菲特指标自动转 live（代码就绪，只需清缓存重跑）。
- 基金列表补「同期纳指超额」列与贝塔/阿尔法（需基准对齐）。
- 前端按路由 code-split，减小首屏包体积。
