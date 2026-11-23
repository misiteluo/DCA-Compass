import { Link, NavLink } from "react-router-dom";

const LINKS = [
  ["/", "首页"],
  ["/asset/btc", "BTC"],
  ["/asset/gold", "黄金"],
  ["/asset/nasdaq", "纳指"],
  ["/asset/sp500", "标普500"],
  ["/asset/hs300", "沪深300"],
  ["/funds", "美股基金"],
  ["/lazy", "懒人组合"],
] as const;

export default function Nav() {
  return (
    <nav className="main">
      <Link to="/" className="logo">🧭 定投罗盘</Link>
      {LINKS.map(([to, label]) => (
        <NavLink key={to} to={to} className={({ isActive }) => `link${isActive ? " active" : ""}`}>
          {label}
        </NavLink>
      ))}
      <NavLink to="/manual" className="link">三资产手册</NavLink>
      <NavLink to="/admin" className="link">后台管理</NavLink>
    </nav>
  );
}
