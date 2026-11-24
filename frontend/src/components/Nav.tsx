import { Link, NavLink, useLocation } from "react-router-dom";

const LINKS = [
  ["/", "首页"],
  ["/btc", "BTC", "/asset/btc"],
  ["/gold", "黄金", "/asset/gold"],
  ["/nasdaq", "纳指", "/asset/nasdaq"],
  ["/sp500", "标普500", "/asset/sp500"],
  ["/hs300", "沪深300", "/asset/hs300"],
  ["/us-fund-holdings", "美股基金", "/funds"],
  ["/lazy", "懒人组合"],
  ["/touzi", "三资产手册", "/manual"],
  ["/dca", "定投记录"],
  ["/admin", "后台管理"],
] as const;

export default function Nav() {
  const path = useLocation().pathname.replace(/\/$/, "") || "/";
  return (
    <nav className="main" aria-label="主导航">
      <Link to="/" className="logo">🧭 定投罗盘</Link>
      {LINKS.map(([to, label, alias]) => (
        <NavLink key={to} to={alias === path ? alias : to} className={({ isActive }) => `link${isActive ? " active" : ""}`}>
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
