import React, { useEffect, useRef, useCallback } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { MarsRoverController } from './MarsRoverModel';
import {
  threeToGrid,
  gridToThree,
  elevationAt,
  isInsideBounds,
  bilinearElevation,
} from '../../utils/coordinateMapping';

/**
 * A.R.E.S. 3D Terrain Tactical Map
 * Strict Utilitarian Aerospace / Brutalist Implementation:
 * 1. Lighting & Textures: Zero shadows, zero glossy materials. Matte #121212 background with flat ambient lighting.
 * 2. Mesh: Mars terrain rendered as a flat matte surface with a precision #333333 topological wireframe mesh (with #DC2626 hazard and #D97706 caution highlights).
 * 3. Route Lines: Rover's smoothed_x / smoothed_y trajectories rendered as solid, un-glowing lines (LineBasicMaterial).
 * 4. Markers: Simple geometric primitives (cubes and pyramids) for rover and science/navigation targets.
 */
export default function TerrainThreeMap({
  dem,
  costMap,
  navigation,
  startPoint,
  destinationPoint,
  onSelectStart,
  onSelectDestination,
  selectionMode = 'auto', // 'auto' | 'start' | 'destination'
  activeRoute = 'safest', // 'safest' | 'shortest'
  isPlaying = false,
  roverProgress = 0,
  onRoverProgressUpdate,
  onHoverCell,
  cameraMode = 'ORBIT', // 'ORBIT' | 'ROVER_CHASE' | 'MASTCAM_POV'
  onEnvironmentalUpdate,
  toolMode = 'nav', // 'nav' | 'landslide' | 'vortex' | 'fissure'
  onInjectHazard,
  onCameraUpdate,
  focusTarget,
  simSpeed = 1.0,
}) {
  const mountRef = useRef(null);
  const animFrameIdRef = useRef(null);

  // Persistent Three.js references
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const controlsRef = useRef(null);
  const terrainGroupRef = useRef(null);
  const roverControllerRef = useRef(null);
  const injectedHazardsGroupRef = useRef(null);

  // Route Lines & Geometric Target Markers
  const redRouteLineRef = useRef(null);
  const greenRouteLineRef = useRef(null);
  const startMarkerRef = useRef(null);
  const destMarkerRef = useRef(null);

  // Spline Traversal & Kinematics Ref
  const splineRef = useRef(null);
  const uRef = useRef(0.0);
  const lastRoverPosRef = useRef({ r: 15, c: 15, heading: 0 });

  // State mirror refs for animation loop
  const isPlayingRef = useRef(isPlaying);
  const activeRouteRef = useRef(activeRoute);
  const navigationRef = useRef(navigation);
  const cameraModeRef = useRef(cameraMode);
  const simSpeedRef = useRef(simSpeed);
  const costMapRef = useRef(costMap);
  const onRoverProgressUpdateRef = useRef(onRoverProgressUpdate);
  const onEnvironmentalUpdateRef = useRef(onEnvironmentalUpdate);
  const onCameraUpdateRef = useRef(onCameraUpdate);

  isPlayingRef.current = isPlaying;
  activeRouteRef.current = activeRoute;
  navigationRef.current = navigation;
  cameraModeRef.current = cameraMode;
  simSpeedRef.current = simSpeed;
  costMapRef.current = costMap;
  onRoverProgressUpdateRef.current = onRoverProgressUpdate;
  onEnvironmentalUpdateRef.current = onEnvironmentalUpdate;
  onCameraUpdateRef.current = onCameraUpdate;

  // Elevation scale configuration
  const elevConfig = useRef({ minElev: 0, maxElev: 60, elevScale: 0.28 });

  // 1. Initialize Scene, Camera, Renderer & Brutalist Flat Lighting
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;

    // Solid matte black #121212 background with strict distance cutoff
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x121212);
    scene.fog = new THREE.Fog(0x121212, 220, 850);
    sceneRef.current = scene;

    // Perspective Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.5, 2500);
    camera.position.set(0, 185, 195);
    cameraRef.current = camera;

    // WebGL Renderer: Strict zero-shadow, non-glossy configuration
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: 'high-performance',
      logarithmicDepthBuffer: true,
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = false; // Disable realistic shadows per spec

    container.innerHTML = '';
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // OrbitControls: Full sector inspection
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 - 0.04;
    controls.minDistance = 4;
    controls.maxDistance = 1200;
    controls.target.set(0, 5, 0);
    controlsRef.current = controls;

    // Brutalist Flat Lighting: Simple un-glowing ambient light
    const ambientLight = new THREE.AmbientLight(0xd4d4d4, 1.0);
    scene.add(ambientLight);

    // Rover Controller Instance (Geometric Primitive)
    const roverController = new MarsRoverController();
    scene.add(roverController.root);
    roverControllerRef.current = roverController;

    // Group for dynamic hazard injection markers (Cubes/Pyramids)
    const injectedHazardsGroup = new THREE.Group();
    injectedHazardsGroup.name = 'InjectedHazardsGroup';
    scene.add(injectedHazardsGroup);
    injectedHazardsGroupRef.current = injectedHazardsGroup;

    // ─────────────────────────────────────────────────────────────
    // Continuous 60+ FPS Animation Loop with Decoupled Telemetry
    // ─────────────────────────────────────────────────────────────
    let lastTime = performance.now();
    let lastTelemetrySyncTime = 0;
    let lastCameraSyncTime = 0;

    const animate = () => {
      animFrameIdRef.current = requestAnimationFrame(animate);
      const now = performance.now();
      const deltaSec = Math.min((now - lastTime) / 1000, 0.08);
      lastTime = now;

      const rover = roverControllerRef.current;
      const currentSpline = splineRef.current;

      // 1. Spline Kinematics & Linear Velocity Traversal
      if (isPlayingRef.current && currentSpline && rover) {
        const { curve, length: splineLength, count: waypointsCount, demElevation, demRows, demCols } = currentSpline;
        let curU = uRef.current;

        if (curU < 1.0) {
          const currentPoint = curve.getPointAt(curU);
          const tangent = curve.getTangentAt(curU).normalize();

          // Grid coordinates of continuous rover position
          const curGrid = threeToGrid(currentPoint.x, currentPoint.z, demRows, demCols);
          const cellCost = costMapRef.current?.cost?.[curGrid.row]?.[curGrid.col] ?? 1.0;
          const isCaution = typeof cellCost === 'number' && cellCost > 2.0;

          // Kinematic linear velocity: 9.0 units/s * simSpeed
          let velocity = 9.0 * (simSpeedRef.current || 1.0);
          if (isCaution) velocity *= 0.75;

          const deltaDist = velocity * deltaSec;
          const deltaU = deltaDist / Math.max(1.0, splineLength);
          let nextU = Math.min(1.0, curU + deltaU);
          uRef.current = nextU;

          // Heading angle in horizontal XZ plane
          const headingAngle = Math.atan2(tangent.x, tangent.z);

          // Update rover primitive kinematics
          const { minElev, elevScale } = elevConfig.current;
          const kin = rover.updateKinematics(
            curGrid.row,
            curGrid.col,
            headingAngle,
            demElevation,
            demRows,
            demCols,
            minElev,
            elevScale,
            deltaDist,
            deltaSec,
            true,
            0
          );

          lastRoverPosRef.current = {
            r: curGrid.row,
            c: curGrid.col,
            heading: headingAngle,
          };

          // Continuous Progress Sync to App State
          const currentWaypointFloat = nextU * Math.max(1, waypointsCount - 1);
          if (onRoverProgressUpdateRef.current) {
            onRoverProgressUpdateRef.current(currentWaypointFloat, nextU >= 1.0);
          }

          // Telemetry Inclinometer Sync (Throttled to 60ms)
          if (now - lastTelemetrySyncTime >= 60 && onEnvironmentalUpdateRef.current) {
            lastTelemetrySyncTime = now;
            onEnvironmentalUpdateRef.current((prev) => ({
              ...prev,
              roverPitch: kin.pitchDeg.toFixed(1),
              roverRoll: kin.rollDeg.toFixed(1),
            }));
          }
        }
      }

      // 2. Camera Controller (Orbit vs Chase vs Mastcam POV)
      const camMode = cameraModeRef.current;
      if (rover && rover.root) {
        const roverPos = rover.root.position;
        const heading = lastRoverPosRef.current.heading;
        const cosH = Math.cos(heading);
        const sinH = Math.sin(heading);

        if (camMode === 'ROVER_CHASE') {
          controls.enabled = false;
          const chaseCamTarget = new THREE.Vector3(
            roverPos.x - sinH * 12.0,
            roverPos.y + 6.0,
            roverPos.z - cosH * 12.0
          );
          camera.position.lerp(chaseCamTarget, 0.08);
          const lookAheadTarget = new THREE.Vector3(
            roverPos.x + sinH * 7.0,
            roverPos.y + 1.2,
            roverPos.z + cosH * 7.0
          );
          camera.lookAt(lookAheadTarget);
        } else if (camMode === 'MASTCAM_POV') {
          controls.enabled = false;
          const mastCamPos = new THREE.Vector3(
            roverPos.x + 0.3,
            roverPos.y + 1.5,
            roverPos.z + 0.5
          );
          camera.position.copy(mastCamPos);
          const forwardTarget = new THREE.Vector3(
            roverPos.x + sinH * 25.0,
            roverPos.y + 0.8,
            roverPos.z + cosH * 25.0
          );
          camera.lookAt(forwardTarget);
        } else {
          controls.enabled = true;
          controls.update();
        }
      } else {
        controls.update();
      }

      // Camera State Sync for Radar Minimap (Throttled to 500ms)
      if (now - lastCameraSyncTime >= 500 && onCameraUpdateRef.current) {
        lastCameraSyncTime = now;
        onCameraUpdateRef.current({
          pos: { x: camera.position.x, y: camera.position.y, z: camera.position.z },
          target: { x: controls.target.x, y: controls.target.y, z: controls.target.z },
        });
      }

      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      if (!container || !renderer || !camera) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (animFrameIdRef.current) cancelAnimationFrame(animFrameIdRef.current);
      if (roverControllerRef.current) roverControllerRef.current.dispose();
      renderer.dispose();
      controls.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  // 2. Camera Target Focus
  useEffect(() => {
    if (!focusTarget || !controlsRef.current || !dem?.elevation) return;
    const { row, col } = focusTarget;
    const { minElev, elevScale } = elevConfig.current;
    const { x, y, z } = gridToThree(row, col, dem.elevation, dem.rows, dem.cols, minElev, elevScale, 0);

    const controls = controlsRef.current;
    const camera = cameraRef.current;
    if (controls && camera) {
      controls.target.set(x, y + 2, z);
      camera.position.set(x, y + 55, z + 65);
      controls.update();
    }
  }, [focusTarget, dem]);

  // 3. Build Brutalist 200x200 Mars Terrain: Matte Base + Hairline Wireframe Mesh
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene || !dem?.elevation || !Array.isArray(dem.elevation)) return;

    const rows = dem.rows;
    const cols = dem.cols;
    const elevation = dem.elevation;

    // Elevation range analysis
    let minE = Infinity;
    let maxE = -Infinity;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const val = elevation[r]?.[c];
        if (typeof val === 'number' && Number.isFinite(val)) {
          if (val < minE) minE = val;
          if (val > maxE) maxE = val;
        }
      }
    }
    if (minE === Infinity) minE = 0;
    if (maxE === -Infinity) maxE = 60;
    const elevRange = Math.max(1, maxE - minE);
    const elevScale = 18.0 / elevRange;
    elevConfig.current = { minElev: minE, maxElev: maxE, elevScale };

    // Dispose old terrain group
    if (terrainGroupRef.current) {
      scene.remove(terrainGroupRef.current);
      terrainGroupRef.current.traverse((child) => {
        if (child.geometry) child.geometry.dispose();
        if (child.material) {
          if (Array.isArray(child.material)) child.material.forEach((m) => m.dispose());
          else child.material.dispose();
        }
      });
      terrainGroupRef.current = null;
    }

    const terrainGroup = new THREE.Group();
    terrainGroup.name = 'AresBrutalistTerrain';

    // PlaneGeometry matching 200x200 DEM
    const geom = new THREE.PlaneGeometry(cols - 1, rows - 1, cols - 1, rows - 1);
    geom.rotateX(-Math.PI / 2);

    const posAttr = geom.attributes.position;
    const vertexCount = posAttr.count;
    const wireframeColors = new Float32Array(vertexCount * 3);

    // Strict Utilitarian Palette:
    // Safe wireframe: #333333
    // Caution wireframe: #D97706 (Flat Amber)
    // Impassable hazard: #DC2626 (Flat Crimson)
    const colorNormalWire = new THREE.Color(0x333333);
    const colorCautionWire = new THREE.Color(0xd97706);
    const colorHazardWire = new THREE.Color(0xdc2626);

    for (let i = 0; i < vertexCount; i++) {
      const c = i % cols;
      const r = Math.floor(i / cols);

      const rawZ = elevationAt(elevation, r, c) ?? minE;
      const yVal = (rawZ - minE) * elevScale;
      posAttr.setY(i, yVal);

      // Check cost map for hazard wireframe coloring
      const cellCost = costMap?.cost?.[r]?.[c];
      const isImpassable = cellCost === 'Infinity' || cellCost === Infinity || cellCost >= 9999;
      const isCaution = typeof cellCost === 'number' && cellCost > 2.0 && !isImpassable;

      const vCol = new THREE.Color();
      if (isImpassable) {
        vCol.copy(colorHazardWire);
      } else if (isCaution) {
        vCol.copy(colorCautionWire);
      } else {
        vCol.copy(colorNormalWire);
      }

      wireframeColors[i * 3 + 0] = vCol.r;
      wireframeColors[i * 3 + 1] = vCol.g;
      wireframeColors[i * 3 + 2] = vCol.b;
    }

    posAttr.needsUpdate = true;
    geom.setAttribute('color', new THREE.BufferAttribute(wireframeColors, 3));
    geom.computeVertexNormals();

    // 1. Solid Matte Black Underlay Mesh (Zero gloss, pure #121212)
    const matteMat = new THREE.MeshBasicMaterial({
      color: 0x121212,
      side: THREE.DoubleSide,
      polygonOffset: true,
      polygonOffsetFactor: 1,
      polygonOffsetUnits: 1,
    });
    const matteMesh = new THREE.Mesh(geom, matteMat);
    matteMesh.frustumCulled = false;
    terrainGroup.add(matteMesh);

    // 2. Brutalist Topological Wireframe Overlay (MeshBasicMaterial wireframe: true, colored #333333)
    const wireMat = new THREE.MeshBasicMaterial({
      wireframe: true,
      vertexColors: true,
    });
    const wireMesh = new THREE.Mesh(geom, wireMat);
    wireMesh.frustumCulled = false;
    terrainGroup.add(wireMesh);

    scene.add(terrainGroup);
    terrainGroupRef.current = terrainGroup;
  }, [dem, costMap]);

  // 4. Build Simple Geometric Primitives for Markers (Start: Cube, Goal: Pyramid)
  const createStartPrimitive = useCallback(() => {
    const group = new THREE.Group();
    // Sky Blue (#0284C7) Geometric Cube Marker
    const cubeGeom = new THREE.BoxGeometry(1.6, 1.6, 1.6);
    const cubeMat = new THREE.MeshBasicMaterial({ color: 0x0284c7 });
    const cube = new THREE.Mesh(cubeGeom, cubeMat);
    cube.position.y = 1.8;
    group.add(cube);

    // Wireframe edge on cube
    const edgeGeom = new THREE.EdgesGeometry(cubeGeom);
    const edgeMat = new THREE.LineBasicMaterial({ color: 0xd4d4d4, linewidth: 2 });
    const edge = new THREE.LineSegments(edgeGeom, edgeMat);
    cube.add(edge);

    // Hairline vertical guide
    const lineGeom = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(0, 1.0, 0),
    ]);
    const lineMat = new THREE.LineBasicMaterial({ color: 0x0284c7 });
    const line = new THREE.Line(lineGeom, lineMat);
    group.add(line);

    return group;
  }, []);

  const createGoalPrimitive = useCallback(() => {
    const group = new THREE.Group();
    // Flat Amber (#D97706) Inverted Pyramid Marker (pointing down to waypoint)
    const pyrGeom = new THREE.ConeGeometry(1.2, 2.2, 4);
    pyrGeom.rotateX(Math.PI); // Apex points down
    const pyrMat = new THREE.MeshBasicMaterial({ color: 0xd97706 });
    const pyr = new THREE.Mesh(pyrGeom, pyrMat);
    pyr.position.y = 1.6;
    group.add(pyr);

    // Wireframe outline on pyramid
    const edgeGeom = new THREE.EdgesGeometry(pyrGeom);
    const edgeMat = new THREE.LineBasicMaterial({ color: 0xd4d4d4, linewidth: 2 });
    const edge = new THREE.LineSegments(edgeGeom, edgeMat);
    pyr.add(edge);

    return group;
  }, []);

  // Update Start & Destination Markers
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene || !dem?.elevation) return;

    if (!startPoint) {
      if (startMarkerRef.current) {
        scene.remove(startMarkerRef.current);
        startMarkerRef.current = null;
      }
    } else {
      if (!startMarkerRef.current) {
        startMarkerRef.current = createStartPrimitive();
        scene.add(startMarkerRef.current);
      }
      const { minElev, elevScale } = elevConfig.current;
      const { x, y, z } = gridToThree(
        startPoint[0],
        startPoint[1],
        dem.elevation,
        dem.rows,
        dem.cols,
        minElev,
        elevScale,
        0
      );
      startMarkerRef.current.position.set(x, y, z);
    }

    if (!destinationPoint) {
      if (destMarkerRef.current) {
        scene.remove(destMarkerRef.current);
        destMarkerRef.current = null;
      }
    } else {
      if (!destMarkerRef.current) {
        destMarkerRef.current = createGoalPrimitive();
        scene.add(destMarkerRef.current);
      }
      const { minElev, elevScale } = elevConfig.current;
      const { x, y, z } = gridToThree(
        destinationPoint[0],
        destinationPoint[1],
        dem.elevation,
        dem.rows,
        dem.cols,
        minElev,
        elevScale,
        0
      );
      destMarkerRef.current.position.set(x, y, z);
    }
  }, [startPoint, destinationPoint, dem, createStartPrimitive, createGoalPrimitive]);

  // 5. Build Solid, Un-Glowing Route Lines (LineBasicMaterial) using smoothed_x / smoothed_y
  const buildBrutalistRouteLine = useCallback((routeData, elevation, rows, cols, hexColor, yOffset) => {
    if (!routeData) return null;

    let points = [];

    // Prefer smoothed_x / smoothed_y paths per requirement
    if (
      Array.isArray(routeData.smoothed_x) &&
      Array.isArray(routeData.smoothed_y) &&
      routeData.smoothed_x.length > 1
    ) {
      const { minElev, elevScale } = elevConfig.current;
      for (let i = 0; i < routeData.smoothed_x.length; i++) {
        const r = routeData.smoothed_y[i];
        const c = routeData.smoothed_x[i];
        const { x, y, z } = gridToThree(r, c, elevation, rows, cols, minElev, elevScale, yOffset);
        points.push(new THREE.Vector3(x, y, z));
      }
    } else if (Array.isArray(routeData.path) && routeData.path.length > 1) {
      const { minElev, elevScale } = elevConfig.current;
      for (let i = 0; i < routeData.path.length; i++) {
        const [r, c] = routeData.path[i];
        const { x, y, z } = gridToThree(r, c, elevation, rows, cols, minElev, elevScale, yOffset);
        points.push(new THREE.Vector3(x, y, z));
      }
    }

    if (points.length < 2) return null;

    const lineGeom = new THREE.BufferGeometry().setFromPoints(points);
    // Strict LineBasicMaterial: solid, un-glowing
    const lineMat = new THREE.LineBasicMaterial({
      color: hexColor,
      linewidth: 3,
    });

    const lineMesh = new THREE.Line(lineGeom, lineMat);
    return { lineMesh, points };
  }, []);

  // Update Route Lines and Spline Curve for Traversal
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene || !dem?.elevation) return;

    if (redRouteLineRef.current) {
      scene.remove(redRouteLineRef.current);
      redRouteLineRef.current.geometry.dispose();
      redRouteLineRef.current.material.dispose();
      redRouteLineRef.current = null;
    }
    if (greenRouteLineRef.current) {
      scene.remove(greenRouteLineRef.current);
      greenRouteLineRef.current.geometry.dispose();
      greenRouteLineRef.current.material.dispose();
      greenRouteLineRef.current = null;
    }

    if (!navigation) {
      splineRef.current = null;
      return;
    }

    // 1. Shortest Route in Flat Crimson (#DC2626)
    const shortestData = navigation.shortest?.route;
    if (shortestData?.success) {
      const red = buildBrutalistRouteLine(shortestData, dem.elevation, dem.rows, dem.cols, 0xdc2626, 0.4);
      if (red) {
        scene.add(red.lineMesh);
        redRouteLineRef.current = red.lineMesh;
      }
    }

    // 2. Safest Route in Nominal Sky Blue (#0284C7)
    const safestData = navigation.safest?.route;
    if (safestData?.success) {
      const green = buildBrutalistRouteLine(safestData, dem.elevation, dem.rows, dem.cols, 0x0284c7, 0.5);
      if (green) {
        scene.add(green.lineMesh);
        greenRouteLineRef.current = green.lineMesh;
      }
    }

    // 3. Traversal Spline for Active Route
    const activeRouteData = navigation[activeRoute]?.route;
    if (activeRouteData?.success) {
      let activePoints = [];
      const { minElev, elevScale } = elevConfig.current;

      if (
        Array.isArray(activeRouteData.smoothed_x) &&
        Array.isArray(activeRouteData.smoothed_y) &&
        activeRouteData.smoothed_x.length > 1
      ) {
        for (let i = 0; i < activeRouteData.smoothed_x.length; i++) {
          const r = activeRouteData.smoothed_y[i];
          const c = activeRouteData.smoothed_x[i];
          const { x, y, z } = gridToThree(r, c, dem.elevation, dem.rows, dem.cols, minElev, elevScale, 0);
          activePoints.push(new THREE.Vector3(x, y, z));
        }
      } else if (Array.isArray(activeRouteData.path) && activeRouteData.path.length > 1) {
        activePoints = activeRouteData.path.map(([r, c]) => {
          const { x, y, z } = gridToThree(r, c, dem.elevation, dem.rows, dem.cols, minElev, elevScale, 0);
          return new THREE.Vector3(x, y, z);
        });
      }

      if (activePoints.length > 1) {
        const activeCurve = new THREE.CatmullRomCurve3(activePoints, false, 'centripetal', 0.2);
        splineRef.current = {
          curve: activeCurve,
          length: activeCurve.getLength(),
          path: activeRouteData.path || [],
          count: activePoints.length,
          demElevation: dem.elevation,
          demRows: dem.rows,
          demCols: dem.cols,
        };
      } else {
        splineRef.current = null;
      }
    } else {
      splineRef.current = null;
    }
  }, [navigation, activeRoute, dem, buildBrutalistRouteLine]);

  // Sync Rover U progress from external state (e.g. Reset, timeline scrub)
  useEffect(() => {
    const activeSpline = splineRef.current;
    if (!activeSpline) return;
    const maxIdx = Math.max(1, activeSpline.count - 1);
    const targetU = Math.max(0, Math.min(1, roverProgress / maxIdx));

    if (!isPlaying) {
      uRef.current = targetU;
      const rover = roverControllerRef.current;
      if (rover && dem?.elevation) {
        const point = activeSpline.curve.getPointAt(targetU);
        const tangent = activeSpline.curve.getTangentAt(targetU).normalize();
        const headingAngle = Math.atan2(tangent.x, tangent.z);
        const curGrid = threeToGrid(point.x, point.z, dem.rows, dem.cols);
        const { minElev, elevScale } = elevConfig.current;

        rover.updateKinematics(
          curGrid.row,
          curGrid.col,
          headingAngle,
          dem.elevation,
          dem.rows,
          dem.cols,
          minElev,
          elevScale,
          0,
          0.016,
          false
        );
      }
    }
  }, [roverProgress, isPlaying, dem]);

  // Initial Placement of Rover at Start Point
  useEffect(() => {
    const rover = roverControllerRef.current;
    if (!rover || !dem?.elevation) return;
    if (splineRef.current && isPlaying) return;

    const r = startPoint ? startPoint[0] : 15;
    const c = startPoint ? startPoint[1] : 15;
    const { minElev, elevScale } = elevConfig.current;

    rover.updateKinematics(
      r,
      c,
      0,
      dem.elevation,
      dem.rows,
      dem.cols,
      minElev,
      elevScale,
      0,
      0.016,
      false
    );
  }, [startPoint, dem, isPlaying]);

  // 6. Terrain Interaction (Raycast on Terrain Mesh)
  const handleCanvasClick = useCallback(
    (e) => {
      if (cameraModeRef.current !== 'ORBIT') return;

      const container = mountRef.current;
      const camera = cameraRef.current;
      const terrainGroup = terrainGroupRef.current;
      if (!container || !camera || !terrainGroup || !dem?.rows) return;

      const rect = container.getBoundingClientRect();
      const mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const mouseY = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(new THREE.Vector2(mouseX, mouseY), camera);

      const intersects = raycaster.intersectObjects(terrainGroup.children);
      if (intersects.length > 0) {
        const hit = intersects[0].point;
        const { row, col } = threeToGrid(hit.x, hit.z, dem.rows, dem.cols);

        if (isInsideBounds(row, col, dem.rows, dem.cols)) {
          if (toolMode === 'landslide' || toolMode === 'vortex' || toolMode === 'fissure') {
            if (onInjectHazard) {
              onInjectHazard(toolMode, row, col);
            }
            return;
          }

          if (selectionMode === 'start') {
            onSelectStart(row, col);
          } else if (selectionMode === 'destination') {
            onSelectDestination(row, col);
          } else {
            if (!startPoint) {
              onSelectStart(row, col);
            } else if (!destinationPoint) {
              onSelectDestination(row, col);
            } else {
              onSelectDestination(row, col);
            }
          }
        }
      }
    },
    [
      dem,
      toolMode,
      onInjectHazard,
      selectionMode,
      startPoint,
      destinationPoint,
      onSelectStart,
      onSelectDestination,
    ]
  );

  const handleCanvasMouseMove = useCallback(
    (e) => {
      if (!onHoverCell || !terrainGroupRef.current || !dem?.rows) return;
      const container = mountRef.current;
      const camera = cameraRef.current;
      if (!container || !camera) return;

      const rect = container.getBoundingClientRect();
      const mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const mouseY = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(new THREE.Vector2(mouseX, mouseY), camera);

      const intersects = raycaster.intersectObjects(terrainGroupRef.current.children);
      if (intersects.length > 0) {
        const hit = intersects[0].point;
        const { row, col } = threeToGrid(hit.x, hit.z, dem.rows, dem.cols);
        if (isInsideBounds(row, col, dem.rows, dem.cols)) {
          const rawZ = elevationAt(dem.elevation, row, col);
          const cellCost = costMap?.cost?.[row]?.[col] ?? 1.0;
          onHoverCell({ row, col, elevation: rawZ, cost: cellCost });
        }
      }
    },
    [dem, costMap, onHoverCell]
  );

  return (
    <div
      ref={mountRef}
      onClick={handleCanvasClick}
      onMouseMove={handleCanvasMouseMove}
      style={{
        width: '100%',
        height: '100%',
        position: 'relative',
        cursor:
          cameraMode === 'ORBIT'
            ? toolMode !== 'nav'
              ? 'copy'
              : !startPoint || !destinationPoint
              ? 'crosshair'
              : 'grab'
            : 'default',
        touchAction: 'none',
      }}
    />
  );
}
