import '@testing-library/jest-dom';

// Provide a minimal ResizeObserver implementation for components relying on it.
class StubResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (typeof window !== 'undefined' && !('ResizeObserver' in window)) {
  // @ts-expect-error override for test environment
  window.ResizeObserver = StubResizeObserver;
}
