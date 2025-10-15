import { Link, useLocation } from 'react-router-dom';
import './TopBar.css';

const TopBar = () => {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <header className="top-bar">
      <div className="top-bar__logo">Signal Zero</div>
      <nav className="top-bar__nav">
        <Link className={isActive('/inference') ? 'active' : ''} to="/inference">
          Inference
        </Link>
        <Link className={isActive('/') ? 'active' : ''} to="/">
          Symbol Browser
        </Link>
      </nav>
    </header>
  );
};

export default TopBar;
