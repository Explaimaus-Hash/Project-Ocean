"use client";
import { useEffect, useRef, useState } from "react";
import type { Viewer } from "cesium";
import { loadCesium } from "@/lib/loadCesium";
import { useGlobe } from "./GlobeContext";
import { GlobeController } from "./GlobeController";
import { imageryConfiguration } from "./globeConfig";
export function useCesiumGlobe() {
  const host = useRef<HTMLDivElement>(null);
  const surface = useRef<HTMLElement>(null);
  const coordinates = useRef<HTMLSpanElement>(null);
  const altitude = useRef<HTMLSpanElement>(null);
  const controller = useRef<GlobeController | null>(null);
  const { status, setStatus, settings, setViewer } = useGlobe();
  const latestSettings = useRef(settings);
  const [attempt, setAttempt] = useState(0);
  const [imageryState, setImageryState] = useState(
    "Natural Earth · geographic basemap",
  );
  useEffect(() => {
    latestSettings.current = settings;
    controller.current?.applySettings(settings);
  }, [settings]);
  useEffect(() => {
    let disposed = false;
    let viewer: Viewer | undefined;
    const cleanups: (() => void)[] = [];
    const fail = () => {
      if (!disposed) setStatus("error");
    };
    async function initialize() {
      try {
        const C = await loadCesium();
        if (
          disposed ||
          !host.current ||
          !surface.current ||
          !coordinates.current ||
          !altitude.current
        )
          return;
        viewer = new C.Viewer(host.current, {
          baseLayer: false,
          baseLayerPicker: false,
          geocoder: false,
          animation: false,
          timeline: false,
          homeButton: false,
          sceneModePicker: false,
          navigationHelpButton: false,
          fullscreenButton: false,
          infoBox: false,
          selectionIndicator: false,
          requestRenderMode: true,
          maximumRenderTimeChange: Infinity,
          terrainProvider: new C.EllipsoidTerrainProvider(),
          contextOptions: { webgl: { antialias: true, alpha: false } },
          msaaSamples: 4,
        });
        const scene = viewer.scene;
        scene.backgroundColor = C.Color.fromCssColorString("#060b12");
        scene.globe.baseColor = C.Color.fromCssColorString("#17384a");
        scene.globe.showGroundAtmosphere = true;
        scene.globe.depthTestAgainstTerrain = true;
        scene.postProcessStages.fxaa.enabled = true;
        scene.postProcessStages.bloom.enabled = false;
        if (scene.skyBox) scene.skyBox.show = false;
        if (scene.sun) scene.sun.show = false;
        if (scene.moon) scene.moon.show = false;
        viewer.camera.setView({
          destination: C.Cartesian3.fromDegrees(75, 8, 35000000),
        });
        controller.current = new GlobeController(
          viewer,
          C,
          surface.current,
          coordinates.current,
          altitude.current,
        );
        controller.current.applySettings(latestSettings.current);
        const lost = (event: Event) => {
          event.preventDefault();
          controller.current?.stop();
          fail();
        };
        viewer.canvas.addEventListener("webglcontextlost", lost);
        cleanups.push(
          () => viewer?.canvas.removeEventListener("webglcontextlost", lost),
          scene.renderError.addEventListener(fail),
        );
        const removeFirstFrame = scene.postRender.addEventListener(() => {
          removeFirstFrame?.();
          if (disposed) return;
          setStatus("ready");
          controller.current?.launch();
        });
        cleanups.push(() => removeFirstFrame?.());
        scene.requestRender();
        try {
          const configured =
            imageryConfiguration.url && imageryConfiguration.attribution;
          const imagery = configured
            ? new C.UrlTemplateImageryProvider({
                url: imageryConfiguration.url!,
                credit: new C.Credit(imageryConfiguration.attribution!, true),
                maximumLevel: 18,
              })
            : await C.TileMapServiceImageryProvider.fromUrl(
                "/cesium/Assets/Textures/NaturalEarthII",
                {
                  credit: new C.Credit(
                    "Natural Earth II · geographic basemap",
                    true,
                  ),
                },
              );
          if (disposed || viewer.isDestroyed()) return;
          controller.current?.setBasemap(
            viewer.imageryLayers.addImageryProvider(imagery, 0),
          );
          setImageryState(
            configured
              ? imageryConfiguration.attribution!
              : "Natural Earth · geographic basemap",
          );
          cleanups.push(
            imagery.errorEvent.addEventListener(() => {
              if (!disposed)
                setImageryState("Imagery unavailable · basic globe");
            }),
          );
        } catch {
          if (!disposed) setImageryState("Imagery unavailable · basic globe");
        }
        if (!disposed) {
          controller.current?.applySettings(latestSettings.current);
          setViewer(viewer);
        }
      } catch {
        fail();
      }
    }
    void initialize();
    return () => {
      disposed = true;
      setViewer(null);
      for (const cleanup of cleanups) cleanup();
      controller.current?.destroy();
      controller.current = null;
      if (viewer && !viewer.isDestroyed()) viewer.destroy();
    };
  }, [attempt, setStatus, setViewer]);
  return {
    host,
    surface,
    coordinates,
    altitude,
    controller,
    status,
    imageryState,
    retry: () => {
      setStatus("loading");
      setAttempt((value) => value + 1);
    },
  };
}
