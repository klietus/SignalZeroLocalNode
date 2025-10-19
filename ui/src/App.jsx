import { Route, Routes } from 'react-router-dom';
import TopBar from './components/TopBar';
import SymbolBrowser from './pages/SymbolBrowser';
import Inference from './pages/Inference';
import SymbolSync from './pages/SymbolSync';

const App = () => {
  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
      <TopBar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<SymbolBrowser />} />
          <Route path="/inference" element={<Inference />} />
          <Route path="/sync" element={<SymbolSync />} />
        </Routes>
      </main>
    </div>
  );
};

export default App;
