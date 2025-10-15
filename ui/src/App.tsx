import { Route, Routes } from 'react-router-dom';
import TopBar from './components/TopBar';
import SymbolBrowser from './pages/SymbolBrowser';
import InferenceStub from './pages/InferenceStub';

const App = () => {
  return (
    <div className="app-shell">
      <TopBar />
      <Routes>
        <Route path="/" element={<SymbolBrowser />} />
        <Route path="/inference" element={<InferenceStub />} />
      </Routes>
    </div>
  );
};

export default App;
