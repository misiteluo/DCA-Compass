import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";

const LINKS = [
  ["/", "首页"],
  ["/btc", "比特币", "/asset/btc"],
  ["/gold", "黄金", "/asset/gold"],
  ["/nasdaq", "纳指", "/asset/nasdaq"],
  ["/sp500", "标普500", "/asset/sp500"],
  ["/hs300", "沪深300", "/asset/hs300"],
  ["/us-fund-holdings", "美股基金", "/funds"],
  ["/lazy", "懒人组合"],
  ["/touzi", "策略手册", "/manual"],
  ["/dca", "定投记录"],
] as const;

const MOBILE_NAV = "(width < 64rem)";

export default function Nav() {
  const { pathname, hash } = useLocation();
  const path = pathname.replace(/\/$/, "") || "/";
  const [collapsed, setCollapsed] = useState(() => matchMedia(MOBILE_NAV).matches);
  const menu = useRef<HTMLUListElement>(null);
  const isPopover = collapsed && "showPopover" in HTMLElement.prototype;

  useEffect(() => {
    const query = matchMedia(MOBILE_NAV);
    const update = () => setCollapsed(query.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    if (menu.current?.hasAttribute("popover")) menu.current.hidePopover();
    if (!hash) window.scrollTo(0, 0);
  }, [pathname, hash]);

  return (
    <header className="site-header">
      <nav className="main" aria-label="主导航">
        <Link to="/" className="logo"><img src="/compass.svg" width="32" height="32" alt="" />定投罗盘</Link>
        {isPopover && (
          <button type="button" className="btn menu-button" aria-controls="site-menu" {...{ popovertarget: "site-menu" }}>
            菜单
          </button>
        )}
        <ul ref={menu} id="site-menu" className="site-menu" {...(isPopover ? { popover: "auto" } : {})}>
          {LINKS.map(([to, label, alias]) => (
            <li key={to}>
              <NavLink to={alias === path ? alias : to} end={to === "/"} className="link"
                onClick={() => { if (isPopover) menu.current?.hidePopover(); }}>
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  );
}
