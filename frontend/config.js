// Where the Couture API lives.
//   ""   -> same origin (the backend serves this folder in development)
//   null -> no backend: demo mode (gallery samples, local fingerprinting only)
//   "https://api.example.com" -> a deployed backend (add this page's origin to COUTURE_CORS_ORIGINS)
window.COUTURE_CONFIG = {
  apiBase: location.hostname.endsWith('github.io') ? null : '',
};
