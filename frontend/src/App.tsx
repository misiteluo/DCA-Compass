import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import Nav from "./components/Nav";
import AssetPage from "./pages/AssetPage";
import Funds from "./pages/Funds";
import Home from "./pages/Home";
import { LazyList, PortfolioDetail } from "./pages/Lazy";
import Manual from "./pages/Manual";

export default function App() {
  return (
    <BrowserRouter>
      <Nav />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/asset/:id" element={<AssetPage />} />
        {["btc", "gold", "nasdaq", "sp500", "hs300"].map((id) => <Route key={id} path={`/${id}`} element={<AssetPage assetId={id} />} />)}
        <Route path="/funds" element={<Funds />} />
        <Route path="/us-fund-holdings" element={<Funds />} />
        <Route path="/lazy" element={<LazyList />} />
        <Route path="/lazy/:id" element={<PortfolioDetail />} />
        <Route path="/manual" element={<Manual />} />
        <Route path="/touzi" element={<Manual />} />
        <Route path="/admin" element={<div className="wrap"><h1>后台管理</h1><p>参考站该入口在采集时返回 HTTP 502，尚未获得可验证的后台功能。</p><p><Link to="/">返回首页</Link></p></div>} />
        <Route path="*" element={<div className="wrap"><h1>页面不存在</h1><Link to="/">返回首页</Link></div>} />
      </Routes>
      <footer>
        定投罗盘 DCA Compass · 公开数据与历史报告来源：btcdca.me（各页标注采集时间及状态） ·
        本系统基于历史数据回测，不构成投资建议。
      </footer>
    </BrowserRouter>
  );
}
