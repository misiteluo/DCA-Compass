// Run through playwright-cli run-code --filename scripts/verify_ui.js.
async (page) => {
  const assert = (condition, message) => { if (!condition) throw new Error(message); };
  const base = "http://127.0.0.1:5173";
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (msg) => { if (msg.type() === "error" || msg.text().includes("Can't get DOM width")) errors.push(msg.text()); });
  const checked = [];
  await page.setViewportSize({ width: 1440, height: 1000 });
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
  const scale = page.getByRole("button", { name: "规模(亿) ↓", exact: true });
  await scale.click();
  const scales = await fundTable.locator("tbody tr").evaluateAll((rows) => rows.map((r) => Number(r.children[1].textContent)));
  assert(scales.every((v, i) => !i || v >= scales[i - 1]), "fund scale sorting failed");
  const invoker = fundTable.locator("tbody button").first();
  await invoker.click();
  const dialog = page.locator("dialog:modal");
  await dialog.waitFor();
  await dialog.locator("canvas").first().waitFor();
  assert(await dialog.getByRole("heading", { name: /最新季报前十大持仓/ }).count() === 1, "quarterly holdings missing");
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
  checked.push("funds: 23/16 switch, sorting, holdings, fees, modal close, Escape, focus return");
  await page.goto(`${base}/lazy`);
  await page.locator('a[href="/lazy/all-weather"]').waitFor();
  assert(await page.locator('a.card[href^="/lazy/"]').count() === 10, "portfolio count mismatch");
  await page.locator('a[href="/lazy/all-weather"]').click();
  await page.getByRole("heading", { name: "组合增长（初始 $10,000）", exact: true }).waitFor();
  assert(await page.locator("canvas").count() === 3, "portfolio charts missing");
  assert(await page.getByRole("heading", { name: "历史压力测试", exact: true }).count() === 1, "portfolio stress missing");
  checked.push("portfolios: ten cards, allocation, growth, annual returns, stress tests");
  await page.setViewportSize({ width: 390, height: 844 });
  for (const route of ["/", "/asset/btc", "/funds", "/lazy/all-weather", "/manual"]) {
    await page.goto(base + route);
    await page.locator(".wrap").first().waitFor();
    await page.waitForLoadState("networkidle", { timeout: 40000 });
    const dimensions = await page.evaluate(() => ({ content: document.documentElement.scrollWidth, viewport: innerWidth }));
    assert(dimensions.content <= dimensions.viewport + 1, `${route}: mobile horizontal overflow ${JSON.stringify(dimensions)}`);
  }
  checked.push("mobile: 390px, home, asset, funds, portfolio, manual");
  assert(!errors.length, `Browser errors: ${errors.join("; ")}`);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`${base}/`);
  await page.locator(".cards5 a").first().waitFor({ timeout: 40000 });
  await page.screenshot({ path: "output/playwright/home-desktop.png", fullPage: true });
  return { checked, pageErrors: errors };
}
