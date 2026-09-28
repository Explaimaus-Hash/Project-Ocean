import type { Viewer, Cartesian2, ImageryLayer } from "cesium";
import { PROJECT_REGION, QUALITY } from "./globeConfig";
import type { GlobeSettings } from "./GlobeContext";
type Cesium = typeof import("cesium");
export type CameraAction =
  | "zoom-in"
  | "zoom-out"
  | "rotate-left"
  | "rotate-right"
  | "pan-left"
  | "pan-right"
  | "pan-up"
  | "pan-down"
  | "tilt-up"
  | "tilt-down"
  | "north"
  | "project"
  | "home"
  | "stop";

/** Owns all camera commands and subscriptions. No React updates on camera frames. */
export class GlobeController {
  private cleanups: (() => void)[] = [];
  private settings?: GlobeSettings;
  private rotationPaused = false;
  private basemap: ImageryLayer | null = null;
  setBasemap(layer: ImageryLayer) {
    this.basemap = layer;
  }
  constructor(
    private viewer: Viewer,
    private C: Cesium,
    private surface: HTMLElement,
    coordinates: HTMLElement,
    altitude: HTMLElement,
  ) {
    const { camera, scene, canvas } = viewer;
    const point = new C.Cartesian3();
    const position = new C.Cartographic();
    const handler = new C.ScreenSpaceEventHandler(canvas);
    let lastPick = 0;
    handler.setInputAction(({ endPosition }: { endPosition: Cartesian2 }) => {
      const now = performance.now();
      if (now - lastPick < 40) return;
      lastPick = now;
      const hit = camera.pickEllipsoid(
        endPosition,
        scene.globe.ellipsoid,
        point,
      );
      if (!hit) {
        coordinates.textContent = "Cursor over space";
        return;
      }
      scene.globe.ellipsoid.cartesianToCartographic(hit, position);
      const longitude = C.Math.toDegrees(position.longitude);
      const latitude = C.Math.toDegrees(position.latitude);
      coordinates.textContent = `${Math.abs(latitude).toFixed(3)}°${latitude < 0 ? "S" : "N"}  ${Math.abs(longitude).toFixed(3)}°${longitude < 0 ? "W" : "E"}`;
    }, C.ScreenSpaceEventType.MOUSE_MOVE);
    const updateAltitude = () => {
      altitude.textContent = `${Math.round(camera.positionCartographic.height / 1000).toLocaleString("en-US")} km altitude`;
    };
    camera.percentageChanged = 0.015;
    this.cleanups.push(
      camera.changed.addEventListener(updateAltitude),
      camera.moveEnd.addEventListener(updateAltitude),
      () => handler.destroy(),
    );
    updateAltitude();
    let lastRotation = performance.now();
    const rotation = window.setInterval(() => {
      const now = performance.now(),
        elapsed = Math.min(0.1, (now - lastRotation) / 1000);
      lastRotation = now;
      const s = this.settings;
      if (
        !s?.earthRotation ||
        s.keepCentered ||
        s.reducedAnimation ||
        this.rotationPaused ||
        document.hidden ||
        !this.surface.checkVisibility() ||
        window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
        this.surface.dataset.cameraMotion === "flying"
      )
        return;
      camera.rotateRight(C.Math.toRadians(elapsed * 0.6 * s.animationSpeed));
      scene.requestRender();
    }, 33);
    this.cleanups.push(() => clearInterval(rotation));
    const interrupt = () => this.stop();
    const leave = () => {
      coordinates.textContent = "Move over Earth for coordinates";
    };
    const key = (event: KeyboardEvent) => {
      const keys: Record<string, CameraAction> = {
        ArrowLeft: "rotate-left",
        ArrowRight: "rotate-right",
        ArrowUp: "tilt-up",
        ArrowDown: "tilt-down",
        "+": "zoom-in",
        "=": "zoom-in",
        "-": "zoom-out",
        Escape: "stop",
        Home: "project",
      };
      const action =
        event.shiftKey && event.key.startsWith("Arrow")
          ? (
              {
                ArrowLeft: "pan-left",
                ArrowRight: "pan-right",
                ArrowUp: "pan-up",
                ArrowDown: "pan-down",
              } as const
            )[event.key as "ArrowLeft"]
          : keys[event.key];
      if (action) {
        event.preventDefault();
        this.command(action);
      }
    };
    canvas.tabIndex = 0;
    canvas.setAttribute(
      "aria-label",
      "Interactive Earth. Arrow keys rotate and tilt, Shift plus arrows pan, plus and minus zoom, Home resets the project region, Escape stops flight.",
    );
    canvas.addEventListener("pointerdown", interrupt);
    canvas.addEventListener("wheel", interrupt, { passive: true });
    canvas.addEventListener("mouseleave", leave);
    canvas.addEventListener("keydown", key);
    this.cleanups.push(() => {
      canvas.removeEventListener("pointerdown", interrupt);
      canvas.removeEventListener("wheel", interrupt);
      canvas.removeEventListener("mouseleave", leave);
      canvas.removeEventListener("keydown", key);
    });
    scene.screenSpaceCameraController.minimumZoomDistance = 1000;
    scene.screenSpaceCameraController.maximumZoomDistance = 60000000;
    scene.screenSpaceCameraController.enableCollisionDetection = true;
  }
  stop() {
    this.rotationPaused = true;
    this.viewer.camera.cancelFlight();
    this.surface.dataset.cameraMotion = "idle";
  }
  private fly(project: boolean, duration: number) {
    this.stop();
    const C = this.C;
    const r = PROJECT_REGION;
    let destination = project
      ? this.viewer.camera.getRectangleCameraCoordinates(
          C.Rectangle.fromDegrees(r.west, r.south, r.east, r.north),
        )
      : C.Cartesian3.fromDegrees(75, 8, 30000000);
    if (project && destination) {
      const fitted = C.Cartographic.fromCartesian(destination);
      // Keep the full Earth clear of the surrounding controls, while including the project extent.
      const minimumHeight =
        this.viewer.canvas.clientWidth < 500 ? 22000000 : 12000000;
      destination = C.Cartesian3.fromRadians(
        fitted.longitude,
        fitted.latitude,
        Math.max(fitted.height, minimumHeight),
      );
    }
    const reduced =
      this.settings?.reducedAnimation ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    this.surface.dataset.cameraMotion = reduced ? "idle" : "flying";
    this.viewer.camera.flyTo({
      destination,
      orientation: { heading: 0, pitch: -C.Math.PI_OVER_TWO, roll: 0 },
      duration: reduced ? 0 : duration / (this.settings?.animationSpeed ?? 1),
      complete: () => {
        this.rotationPaused = false;
        this.surface.dataset.cameraMotion = "idle";
      },
      cancel: () => {
        this.surface.dataset.cameraMotion = "idle";
      },
    });
  }
  launch() {
    this.fly(true, 2.8);
  }
  applySettings(settings: GlobeSettings) {
    const old = this.settings;
    this.settings = settings;
    if (old?.earthRotation !== settings.earthRotation)
      this.rotationPaused = false;
    if (settings.keepCentered && !old?.keepCentered) this.fly(true, 1.2);
    if (settings.reducedAnimation) this.stop();
    this.viewer.scene.screenSpaceCameraController.enableTranslate =
      !settings.keepCentered;
    this.viewer.scene.screenSpaceCameraController.enableRotate =
      !settings.keepCentered;
    this.viewer.scene.globe.showGroundAtmosphere = settings.atmosphere;
    if (this.viewer.scene.skyAtmosphere)
      this.viewer.scene.skyAtmosphere.show = settings.atmosphere;
    const quality = QUALITY[settings.quality];
    this.viewer.resolutionScale = quality.resolutionScale;
    this.viewer.scene.globe.maximumScreenSpaceError =
      quality.maximumScreenSpaceError;
    this.viewer.scene.globe.enableLighting = settings.lighting;
    if (this.basemap && !this.basemap.isDestroyed()) {
      const layer = this.basemap;
      layer.show = settings.basemapVisible;
      layer.alpha = settings.basemapOpacity;
    }
    this.viewer.scene.requestRender();
  }
  command(action: CameraAction) {
    if (this.settings?.keepCentered && /^(pan-|rotate-|tilt-)/.test(action))
      return;
    const camera = this.viewer.camera;
    const C = this.C;
    this.stop();
    const distance = camera.positionCartographic.height * 0.16;
    switch (action) {
      case "zoom-in":
        camera.zoomIn(distance);
        break;
      case "zoom-out":
        camera.zoomOut(distance);
        break;
      case "rotate-left":
        camera.rotateLeft(C.Math.toRadians(8));
        break;
      case "rotate-right":
        camera.rotateRight(C.Math.toRadians(8));
        break;
      case "pan-left":
        camera.moveLeft(distance);
        break;
      case "pan-right":
        camera.moveRight(distance);
        break;
      case "pan-up":
        camera.moveUp(distance);
        break;
      case "pan-down":
        camera.moveDown(distance);
        break;
      case "tilt-up":
      case "tilt-down": {
        const pitch = C.Math.clamp(
          camera.pitch + C.Math.toRadians(action === "tilt-up" ? 8 : -8),
          -C.Math.PI_OVER_TWO,
          -C.Math.toRadians(10),
        );
        camera.setView({
          orientation: { heading: camera.heading, pitch, roll: 0 },
        });
        break;
      }
      case "north":
        camera.setView({
          orientation: { heading: 0, pitch: camera.pitch, roll: 0 },
        });
        break;
      case "project":
        this.fly(true, 1.2);
        break;
      case "home":
        this.fly(false, 1.2);
        break;
    }
    this.viewer.scene.requestRender();
  }
  destroy() {
    this.stop();
    for (const cleanup of this.cleanups) cleanup();
    this.cleanups = [];
  }
}
