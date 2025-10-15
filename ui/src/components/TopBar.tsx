import { Link, useLocation } from 'react-router-dom';

const TopBar = () => {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  const linkClass = (path: string) => {
    const base =
      'rounded-lg px-4 py-2 text-sm font-medium transition-colors duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400';
    const active = 'bg-sky-400 text-slate-900 shadow';
    const idle = 'text-slate-200 hover:bg-slate-800/80 hover:text-white';
    return `${base} ${isActive(path) ? active : idle}`;
  };

  return (
    <header className="sticky top-0 z-10 border-b border-slate-800 bg-slate-950/70 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-4">
        <div className="text-sm font-semibold uppercase tracking-[0.28em] text-slate-200">
          Signal Zero
        </div>
        <nav className="flex items-center gap-3">
          <Link className={linkClass('/inference')} to="/inference">
            Inference
          </Link>
          <Link className={linkClass('/')} to="/">
            Symbol Browser
          </Link>
        </nav>
      </div>
    </header>
  );
};

export default TopBar;
