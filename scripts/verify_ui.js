// Run through playwright-cli run-code --filename scripts/verify_ui.js.
async (page) => {
  const assert = (condition, message) => { if (!condition) throw new Error(message); };
  const base = "http://127.0.0.1:5173";
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (msg) => {
    const expectedFailure = msg.location().url.endsWith("/api/v1/markets") && msg.text().includes("503");
    if (!expectedFailure && (msg.type() === "error" || msg.text().includes("Can't get DOM width"))) errors.push(msg.text());
  });
  const checked = [];
  await page.setViewportSize({ width: 1440, height: 1000 });
  const home = await (await page.request.get(`${base}/api/v1/markets`)).json();
  await page.clock.install();
  await page.goto(base);
  const homeCards = page.locator(".cards5 a");
  await homeCards.first().waitFor();
  assert(await homeCards.count() === 5, "home: five market cards missing");
  const nasdaq = home.assets.find((row) => row.id === "nasdaq");
  assert(await homeCards.filter({ hasText: "纳斯达克100" }).locator(".score").innerText() === String(nasdaq.score ?? "--"),
    "home: NASDAQ score differs from aggregate feed");
  let homeRequests = 0;
  await page.route("**/api/v1/markets", async (route) => {
    homeRequests++;
    if (homeRequests === 1) {
      await route.fulfill({ status: 503, json: {} });
      return;
    }
    await route.fulfill({ json: home });
  });
  await page.clock.fastForward(30_000);
  await page.getByRole("status").filter({ hasText: "刷新失败" }).waitFor();
  assert(await homeCards.count() === 5, "home: refresh failure discarded prior data");
  await page.clock.fastForward(30_000);
  await page.getByRole("status").filter({ hasText: "刷新失败" }).waitFor({ state: "hidden" });
  assert(homeRequests === 2, "home: refresh did not recover");
  await page.unroute("**/api/v1/markets");
  checked.push("home: aggregate feed, periodic refresh, retain last data and recover after failure");
  await page.clock.setFixedTime(new Date("2026-11-27T02:00:00Z"));
  await page.goto(`${base}/dca/`);
  await page.getByText("距下一个计划时点 72:00:00").waitFor();
  assert(await page.getByRole("button", { name: "模拟今日定投" }).isDisabled(), "dca: development mode action enabled");
  await page.getByRole("link", { name: "沪深300 详情" }).click();
  await page.waitForFunction(() => {
    const section = document.getElementById("robot-trades");
    if (!section || location.hash !== "#robot-trades") return false;
    const { top } = section.getBoundingClientRect();
    return top >= 0 && top < innerHeight;
  });
  await page.clock.setFixedTime(new Date());
  checked.push("dca: Beijing weekend countdown, development state and public records link");
  for (const id of ["btc", "gold", "nasdaq", "sp500", "hs300"]) {
    await page.goto(`${base}/${id}/`);
    await page.getByRole("heading", { level: 1 }).waitFor({ timeout: 40000 });
    await page.getByRole("heading", { name: "历史价格、评分与定投倍数", exact: true }).waitFor();
    assert(await page.locator("canvas").count() >= 2, `${id}: charts missing`);
    const table = page.locator(".table-scroll table").first();
    assert(await table.locator("tbody tr").count() === 10, `${id}: pagination size`);
    const first = await table.locator("tbody tr").first().innerText();
    await page.getByRole("button", { name: "下一页", exact: true }).click();
    assert((await table.locator("tbody tr").first().innerText()) !== first, `${id}: pagination did not change rows`);
    await page.getByRole("group", { name: "评分历史分页" }).getByRole("button", { name: "第 1 页", exact: true }).click();
    assert((await table.locator("tbody tr").first().innerText()) === first, `${id}: direct first page did not restore rows`);
    if (id === "gold" || id === "sp500") {
      const heatmap = page.getByRole("region", { name: "月度收益热力图" });
      await heatmap.waitFor();
      if (id === "gold") await heatmap.getByRole("rowheader", { name: "月均" }).waitFor();
      else assert((await heatmap.getByRole("row").filter({ hasText: "2015" }).innerText()).includes("-1.2%"), "sp500: report heatmap values differ");
    }
    if (id === "nasdaq") {
      assert(await page.getByRole("heading", { name: "12 维度量化系统", exact: true }).count() === 1, "12D missing");
      const response = await page.request.get(`${base}/api/v1/assets/nasdaq`);
      const data = await response.json();
      assert(await page.getByText("风控已触发", { exact: false }).count() === (data.risk_control?.active ? 1 : 0), "risk control differs from API");
    }
    if (id === "hs300") {
      assert(await page.getByRole("heading", { name: "机器人定投记录", exact: true }).count() === 1, "robot trades missing");
    }
    checked.push(`${id}: route, source, charts, records, pagination`);
  }
  await page.goto(`${base}/us-fund-holdings/`);
  const fundTable = page.locator(".table-scroll table").first();
  await page.waitForFunction(() => document.querySelectorAll(".table-scroll table tbody tr").length === 23, null, { timeout: 40000 });
  const scale = page.getByRole("button", { name: "规模(亿)", exact: true });
  assert(await scale.locator("..").getAttribute("aria-sort") === "descending", "fund scale default sort");
  await scale.click();
  const scales = await fundTable.locator("tbody tr").evaluateAll((rows) => rows.map((r) => Number(r.children[1].textContent)));
  assert(scales.every((v, i) => !i || v >= scales[i - 1]), "fund scale sorting failed");
  assert(await scale.locator("..").getAttribute("aria-sort") === "ascending", "fund scale sort announcement");
  const fundList = await (await page.request.get(`${base}/api/v1/funds?kind=active`)).json();
  await page.getByRole("button", { name: "基金名称（恢复默认顺序）", exact: true }).click();
  const names = await fundTable.locator("tbody button").allTextContents();
  assert(names.join("\n") === fundList.map((fund) => fund.name).join("\n"), "fund sort did not restore dataset order");
  assert(await fundTable.getByText(/跑赢|跑输/).count() === 23, "fund benchmark labels missing");
  const invoker = fundTable.locator("tbody button").first();
  await invoker.click();
  const dialog = page.locator("dialog:modal");
  await dialog.waitFor();
  await dialog.locator("canvas").first().waitFor();
  assert(await dialog.getByRole("heading", { name: /最新季报前十大持仓/ }).count() === 1, "quarterly holdings missing");
  assert(await dialog.getByText(fundList[0].holdings_top10.reportDate, { exact: false }).count() === 1, "quarterly report date missing");
  assert(await dialog.getByText("成立以来", { exact: true }).count() === 1, "since-inception performance missing");
  const limit = await fundTable.locator("tbody tr").first().locator("td").last().textContent();
  assert((await dialog.getByText("支付宝日买入限额", { exact: true }).locator("..").textContent()).includes(limit), "fund detail limit differs from list");
  assert((await dialog.innerText()).includes("综合运作费率"), "fees missing");
  await page.keyboard.press("Escape");
  await dialog.waitFor({ state: "hidden" });
  assert(await invoker.evaluate((el) => el === document.activeElement), "focus did not return to fund button");
  await invoker.click();
  await dialog.waitFor();
  await dialog.getByRole("button", { name: "关闭", exact: true }).click();
  await dialog.waitFor({ state: "hidden" });
  await page.getByRole("button", { name: "被动型（纳指100指数）", exact: true }).click();
  await page.waitForFunction(() => document.querySelectorAll(".table-scroll table tbody tr").length === 16);
  await fundTable.locator("tbody button").first().click();
  await dialog.waitFor();
  assert(await dialog.getByRole("heading", { name: /最新季报前十大持仓|完整持仓明细/ }).count() === 0, "passive fund shows unreported holdings");
  checked.push("funds: 23/16 switch, sort and reset, benchmark, holdings, details, fees, modal close, Escape, focus return");
  await page.goto(`${base}/lazy`);
  await page.locator('a[href="/lazy/all-weather"]').waitFor();
  assert(await page.locator('a.card[href^="/lazy/"]').count() === 10, "portfolio count mismatch");
  await page.locator('a[href="/lazy/all-weather"]').click();
  await page.getByRole("heading", { name: "组合增长（初始 $10,000）", exact: true }).waitFor();
  assert(await page.locator("canvas").count() === 3, "portfolio charts missing");
  assert(await page.getByRole("heading", { name: "历史压力测试", exact: true }).count() === 1, "portfolio stress missing");
  checked.push("portfolios: ten cards, allocation, growth, annual returns, stress tests");
  await page.setViewportSize({ width: 390, height: 844 });
  for (const route of ["/", "/asset/btc", "/funds", "/lazy/all-weather", "/manual", "/dca/"]) {
    await page.goto(base + route);
    await page.locator(".wrap").first().waitFor();
    await page.waitForLoadState("networkidle", { timeout: 40000 });
    const dimensions = await page.evaluate(() => ({ content: document.documentElement.scrollWidth, viewport: innerWidth }));
    assert(dimensions.content <= dimensions.viewport + 1, `${route}: mobile horizontal overflow ${JSON.stringify(dimensions)}`);
  }
  checked.push("mobile: 390px, home, asset, funds, portfolio, manual and dca");
  assert(!errors.length, `Browser errors: ${errors.join("; ")}`);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`${base}/`);
  await page.locator(".cards5 a").first().waitFor({ timeout: 40000 });
  await page.screenshot({ path: "output/playwright/home-desktop.png", fullPage: true });
  return { checked, pageErrors: errors };
}
