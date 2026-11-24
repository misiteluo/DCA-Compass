import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import Nav from "./components/Nav";
import AssetPage from "./pages/AssetPage";
import Funds from "./pages/Funds";
import Home from "./pages/Home";
import { LazyList, PortfolioDetail } from "./pages/Lazy";
import Manual from "./pages/Manual";
import DcaRecords from "./pages/DcaRecords";

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
        <Route path="/dca" element={<DcaRecords />} />
        <Route path="/admin" element={<main className="wrap"><h1>后台管理</h1><p>参考站该入口在采集时返回 HTTP 502，尚未获得可验证的后台功能。</p><p><Link to="/">返回首页</Link></p></main>} />
        <Route path="*" element={<main className="wrap"><h1>页面不存在</h1><Link to="/">返回首页</Link></main>} />
      </Routes>
      <footer>
        <div className="wrap">
          <strong>定投罗盘</strong> · 行情与历史报告来自 btcdca.me。历史回测不构成投资建议。
        </div>
      </footer>
    </BrowserRouter>
  );
}
