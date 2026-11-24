import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

const BEIJING_OFFSET = 8 * 60 * 60 * 1000;

function weekdayCountdown(now: number) {
  const beijingTime = now + BEIJING_OFFSET;
  const next = new Date(beijingTime);
  next.setUTCHours(10, 0, 0, 0);
  if (next.getTime() <= beijingTime) next.setUTCDate(next.getUTCDate() + 1);
  while (next.getUTCDay() === 0 || next.getUTCDay() === 6) next.setUTCDate(next.getUTCDate() + 1);
  const seconds = Math.ceil((next.getTime() - beijingTime) / 1000);
  const parts = [Math.floor(seconds / 3600), Math.floor(seconds / 60) % 60, seconds % 60];
  return parts.map((part) => String(part).padStart(2, "0")).join(":");
}

export default function DcaRecords() {
  const [now, setNow] = useState(Date.now);
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <main className="wrap">
      <h1>定投记录</h1>
      <p>五类资产各以 ¥500 万为计划本金，按每日估值倍数分十年投入。</p>
      <div className="card">
        <strong>机器人交易开发中</strong>
        <p>参考站尚未开放五资产实盘记录。沪深300 的已公开记录可在 <Link to="/hs300/#robot-trades">沪深300 详情</Link> 查看。</p>
        <div>计划执行时间为北京时间每个工作日 10:00</div>
        <p className="score">距下一个计划时点 {weekdayCountdown(now)}</p>
      </div>
      <section>
        <h2>收益总览</h2>
        <div className="grid dimension-grid">
          {[["持仓市值", "--"], ["累计盈亏", "--"], ["计划本金", "¥2,500 万"],
            ["定投天数", "--"], ["累计投入", "--"], ["总收益率", "--"]].map(([label, value]) => (
            <div className="card" key={label}><h3>{label}</h3><b>{value}</b></div>
          ))}
        </div>
      </section>
      <section>
        <h2>定投明细</h2>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="定投明细表格">
          <table>
            <thead><tr>{["日期", "资产", "评分", "倍数", "价格", "份额", "金额"].map((label) => (
              <th scope="col" key={label}>{label}</th>
            ))}</tr></thead>
            <tbody><tr><td colSpan={7}>记录服务尚未开放</td></tr></tbody>
          </table>
        </div>
        <div className="toolbar">
          <button type="button" className="btn" disabled>刷新数据</button>
          <button type="button" className="btn" disabled>模拟今日定投</button>
        </div>
      </section>
    </main>
  );
}
