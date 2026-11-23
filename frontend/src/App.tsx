import { BrowserRouter, Route, Routes } from "react-router-dom";
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
        <Route path="/funds" element={<Funds />} />
        <Route path="/lazy" element={<LazyList />} />
        <Route path="/lazy/:id" element={<PortfolioDetail />} />
        <Route path="/manual" element={<Manual />} />
      </Routes>
      <footer>
        定投罗盘 DCA Compass v2.0 · 数据来源：Yahoo Finance / CoinMetrics / alternative.me / FRED / 东方财富 ·
        本系统基于历史数据回测，不构成投资建议。
      </footer>
    </BrowserRouter>
  );
}
