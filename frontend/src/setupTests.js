// Jest setup for the PAT frontend.
//
// plotly.js reaches for browser APIs that jsdom does not implement. It is
// imported transitively (react-plotly.js -> every panel), so the polyfills
// have to be in place before any test module loads.
import '@testing-library/jest-dom';

if (typeof window !== 'undefined') {
  if (!window.URL.createObjectURL) {
    window.URL.createObjectURL = () => 'blob:mock';
  }
  if (!window.URL.revokeObjectURL) {
    window.URL.revokeObjectURL = () => {};
  }
  // Plotly feature-detects canvas; jsdom returns null without this.
  if (!window.HTMLCanvasElement.prototype.getContext) {
    window.HTMLCanvasElement.prototype.getContext = () => null;
  } else {
    const original = window.HTMLCanvasElement.prototype.getContext;
    window.HTMLCanvasElement.prototype.getContext = function getContext(...args) {
      try {
        const ctx = original.apply(this, args);
        if (ctx) return ctx;
      } catch {
        // jsdom throws "not implemented"; fall through to null.
      }
      return null;
    };
  }
  window.matchMedia =
    window.matchMedia ||
    (() => ({
      matches: false,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
    }));

  // Plotly logs resize/observer noise that is irrelevant here.
  global.ResizeObserver = global.ResizeObserver || class { observe() {} unobserve() {} disconnect() {} };
}
