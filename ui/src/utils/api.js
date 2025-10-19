const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

export const buildApiUrl = (path, params) => {
  const normalisedPath = path.startsWith('/') ? path : `/${path}`;
  const query = params && typeof params.toString === 'function' ? params.toString() : '';
  return `${API_BASE_URL}${normalisedPath}${query ? `?${query}` : ''}`;
};

export { API_BASE_URL };
