import { Api as PyWebViewApi } from "./hooks/pythonBridge";

declare global {
  interface Window {
    pywebview: {
      api: PyWebViewApi;
      state: {
        [key: string]: any;
        addEventListener: (event: string, callback: (event: any) => void) => void;
        removeEventListener: (event: string, callback: (event: any) => void) => void;
      };
    };
  }
}

export {};
