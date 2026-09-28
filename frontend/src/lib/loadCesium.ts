type CesiumModule = typeof import("cesium");
let pending: Promise<CesiumModule> | null = null;

/** Load the pinned, prebuilt browser distribution without re-minifying its WASM. */
export function loadCesium(): Promise<CesiumModule> {
  if (window.Cesium) return Promise.resolve(window.Cesium);
  if (pending) return pending;
  window.CESIUM_BASE_URL = "/cesium/";
  pending = new Promise<CesiumModule>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "/cesium/Cesium.js";
    script.async = true;
    script.onload = () => {
      if (window.Cesium) resolve(window.Cesium);
      else {
        script.remove();
        pending = null;
        reject(new Error("Cesium library unavailable"));
      }
    };
    script.onerror = () => {
      script.remove();
      pending = null;
      reject(new Error("Cesium library could not load"));
    };
    document.head.appendChild(script);
  });
  return pending;
}
