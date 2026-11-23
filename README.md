# 定投罗盘 · DCA Compass

五资产定投信号、历史评分、基金筛选与持仓、十大懒人组合。
参考站：[btcdca.me](https://btcdca.me/)。前端保留本项目的 React / ECharts 布局。

## 当前实现与边界

这次将页面实际使用的数据链路改为参考站公开接口兼容模式，修正原先“用通用百分位算法
替代原站评分”的差异。五资产评分、定投倍数、风控状态与历史记录保留公开接口结果；
基金、组合及固定回测报告保留参考站公布的字段与口径。

**这不是原站私有服务端的独立源码复刻。** 原站未公开服务端评分、数据清洗、平滑、风控
实现。其在线评分仍依赖 `btcdca.me` 的公开只读接口；网络失败时使用上次成功缓存或随库
快照，页面明确标注采集时间及状态。不能把断网后的历史快照当作当天信号。

已移植到本地的可观察规则：沪深300 月度 PE/PB/PEG/ROE 估值评分、分段倍数与最低倍数
限制、策略/普通定投/买入持有现金流；十个组合的年度加权收益和复利增长。固定回测报告
与当前评分分开显示，保留原站存在的不同版本口径。

`/admin/` 在 2026-11-23 采集时返回 502，项目仅展示该不可验证状态，没有虚构后台管理
功能。完整功能对照与残余差异见 [docs/FEATURE_PARITY.md](docs/FEATURE_PARITY.md)。

## 本地运行（Windows PowerShell）

在项目根目录准备依赖：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
npm.cmd --prefix frontend ci
```

两个终端分别启动：

```powershell
# 终端一，项目根目录
.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# 终端二，项目根目录
npm.cmd --prefix frontend run dev
```

打开 http://localhost:5173 。Vite 将同源 `/api` 请求转发至 `127.0.0.1:8000`。
也可 `docker compose up --build`，访问 http://localhost:8080 。后端镜像包含离线快照。

Linux/macOS 使用 `.venv/bin/python` 替换 `.venv/Scripts/python.exe`。

## 数据与刷新

- 评分：每个接口缓存 60 秒；前端首页和资产页每 60 秒更新。
- 基金市场评分、机器人记录：缓存 5 分钟；基金完整目录与历史评分：缓存 1 小时。
- 十大组合与固定报告：版本化快照，见 `backend/reference/site.json`。
- 运行时缓存：`backend/data/cache/reference_*.json`，不覆盖原有独立引擎的缓存。
- 状态：`live` 为最近成功读取；`cached` 为网络失败后沿用本地缓存；`snapshot` 为随库
  离线快照；`report` 为固定历史报告。所有状态都附来源，时间显示为北京时间。

仅使用快照运行：在启动后端的终端设置 `$env:REFERENCE_OFFLINE='1'`。

重新采集公开报告、基金和接口数据：

```powershell
.venv/Scripts/python.exe scripts/sync_reference.py
```

采集器将网页中静态对象解析为数据，不执行下载的 JavaScript，不复制原站统计脚本。
采集后重启后端以加载新版固定报告。更新快照后应复核测试中的已知数值：这些测试是
版本化金样，不是会随行情自动变化的断言。

## 主要 API

| 路径 | 内容 |
|---|---|
| `/api/v1/health` | 服务健康状态 |
| `/api/v1/assets` | 五资产行情、评分、倍数与来源 |
| `/api/v1/assets/{id}` | 维度、历史、固定报告、纳指十二维、沪深300机器人记录 |
| `/api/v1/signals/weekly` | 当前信号摘要 |
| `/api/v1/fund-market-score` | 基金独立四维市场评分，不以纳指评分代替 |
| `/api/v1/funds?kind=active\|passive` | 主动23只 / 被动16只，含同期基准、超额收益和限额 |
| `/api/v1/funds/{code}` | 持仓、风险、资产配置、经理与费率 |
| `/api/v1/portfolios`、`/api/v1/portfolios/{id}` | 十大组合配置、年度回报、风险、压力测试与增长 |

保留 `/asset/:id`、`/funds`、`/manual`；兼容原站 `/btc/`、`/gold/`、`/nasdaq/`、
`/sp500/`、`/hs300/`、`/us-fund-holdings/`、`/lazy/`、`/touzi/`。

旧 `scoring.py`、`backtest.py`、`funds.py`、`portfolios.py` 和 `cache.py` 中的独立数据引擎
仍保留，但当前页面 API 已不调用这些旧计算入口，不能用其测试证明原站私有算法等价。

## 验证

```powershell
.venv/Scripts/python.exe -m pytest backend/tests -q
npm.cmd --prefix frontend run build
New-Item -ItemType Directory -Force output/playwright
npx.cmd --yes --package @playwright/cli playwright-cli -s=dca-parity open http://127.0.0.1:5173 --browser chrome
npx.cmd --yes --package @playwright/cli playwright-cli -s=dca-parity run-code --filename scripts/verify_ui.js
```

浏览器脚本覆盖五资产分页、纳指双评分与风控、23/16基金切换、排序、持仓/费率、
原生弹窗关闭/焦点恢复、组合图表、390px移动端宽度。浏览器验证需要先启动前后端。

本项目用于展示历史数据和策略规则，不执行交易。
