import React, { useEffect, useRef, useCallback } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import {
  threeToGrid,
  gridToThree,
  bilinearElevation,
  elevationAt,
  isInsideBounds,
} from '../../utils/coordinateMapping';

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
  roverProgress = 0, // 0 to maxIndex
  onRoverProgressUpdate,
  onHoverCell,
}) {
  const mountRef = useRef(null);

  // References to persistent Three.js objects
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const controlsRef = useRef(null);
  const terrainMeshRef = useRef(null);
  const startMarkerGroupRef = useRef(null);
  const destMarkerGroupRef = useRef(null);
  const redRouteLineRef = useRef(null);
  const greenRouteLineRef = useRef(null);
  const roverGroupRef = useRef(null);
  const roverWheelsRef = useRef([]);

  const animFrameIdRef = useRef(null);
  const isPlayingRef = useRef(isPlaying);
  const activeRouteRef = useRef(activeRoute);
  const roverProgressRef = useRef(roverProgress);
  const navigationRef = useRef(navigation);

  isPlayingRef.current = isPlaying;
  activeRouteRef.current = activeRoute;
  roverProgressRef.current = roverProgress;
  navigationRef.current = navigation;

  // Elevation scale configuration
  const elevConfig = useRef({ minElev: 0, maxElev: 60, elevScale: 0.28 });

  // 1. Initialize Three.js Scene, Camera, Renderer, Lights, and OrbitControls
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 600;

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x070b12);
    scene.fog = new THREE.FogExp2(0x070b12, 0.007);
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.5, 1000);
    camera.position.set(0, 45, 55);
    cameraRef.current = camera;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 - 0.05; // Prevent camera from going under terrain
    controls.minDistance = 8;
    controls.maxDistance = 180;
    controls.target.set(0, 2, 0);
    controlsRef.current = controls;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffeedd, 0.5);
    scene.add(ambientLight);

    const hemiLight = new THREE.HemisphereLight(0xffaa77, 0x111622, 0.4);
    scene.add(hemiLight);

    const sunLight = new THREE.DirectionalLight(0xffeedd, 1.3);
    sunLight.position.set(40, 70, 30);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 10;
    sunLight.shadow.camera.far = 160;
    sunLight.shadow.camera.left = -40;
    sunLight.shadow.camera.right = 40;
    sunLight.shadow.camera.top = 40;
    sunLight.shadow.camera.bottom = -40;
    scene.add(sunLight);

    // Subtle Martian dust horizon light
    const horizonLight = new THREE.DirectionalLight(0xd97757, 0.4);
    horizonLight.position.set(-50, 15, -40);
    scene.add(horizonLight);

    // Animation Loop
    let lastTime = performance.now();
    const animate = () => {
      animFrameIdRef.current = requestAnimationFrame(animate);
      const now = performance.now();
      const deltaSec = Math.min((now - lastTime) / 1000, 0.1);
      lastTime = now;

      controls.update();

      // Animate Rover if playing
      if (isPlayingRef.current && navigationRef.current) {
        const curRouteKey = activeRouteRef.current;
        const routeData = navigationRef.current[curRouteKey]?.route;
        const path = routeData?.path || [];

        if (path.length > 1) {
          const maxIdx = path.length - 1;
          let nextProgress = roverProgressRef.current + deltaSec * 3.5; // Travel speed in waypoints/sec

          if (nextProgress >= maxIdx) {
            nextProgress = maxIdx;
            if (onRoverProgressUpdate) {
              onRoverProgressUpdate(maxIdx, true); // Finished
            }
          } else {
            if (onRoverProgressUpdate) {
              onRoverProgressUpdate(nextProgress, false);
            }
          }
          roverProgressRef.current = nextProgress;
        }
      }

      renderer.render(scene, camera);
    };
    animate();

    // Resize Handler
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
      renderer.dispose();
      controls.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  // 2. Build Procedural 3D Mars Terrain Mesh from DEM & Cost Map
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene || !dem?.elevation || !Array.isArray(dem.elevation)) return;

    const rows = dem.rows;
    const cols = dem.cols;
    const elevation = dem.elevation;

    // Calculate elevation statistics
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
    const elevScale = 14.0 / elevRange; // Target vertical relief ~14 units
    elevConfig.current = { minElev: minE, maxElev: maxE, elevScale };

    // Remove existing terrain mesh if any
    if (terrainMeshRef.current) {
      scene.remove(terrainMeshRef.current);
      terrainMeshRef.current.geometry.dispose();
      if (Array.isArray(terrainMeshRef.current.material)) {
        terrainMeshRef.current.material.forEach((m) => m.dispose());
      } else {
        terrainMeshRef.current.material.dispose();
      }
      terrainMeshRef.current = null;
    }

    // Create PlaneGeometry with resolution matching DEM grid
    const geom = new THREE.PlaneGeometry(cols - 1, rows - 1, cols - 1, rows - 1);
    geom.rotateX(-Math.PI / 2); // Orient horizontal in X-Z plane

    const posAttr = geom.attributes.position;
    const vertexCount = posAttr.count;
    const colors = new Float32Array(vertexCount * 3);

    // Color swatches for Martian strata
    const colorBasalt = new THREE.Color(0x28120c);   // Deep rift basalt
    const colorRust = new THREE.Color(0x8c3b2b);     // Classic Mars iron oxide
    const colorDune = new THREE.Color(0xbd5f3d);     // Dusty orange slope
    const colorMineral = new THREE.Color(0xe2b18a);  // High exposed silica ridge
    const colorCaution = new THREE.Color(0xd97706);  // Caution warning tint
    const colorHazard = new THREE.Color(0xb91c1c);   // Impassable hazard crimson

    for (let i = 0; i < vertexCount; i++) {
      const c = i % cols;
      const r = Math.floor(i / cols);

      const rawZ = elevationAt(elevation, r, c) ?? minE;
      const normH = Math.max(0, Math.min(1, (rawZ - minE) / elevRange));
      const yVal = (rawZ - minE) * elevScale;

      posAttr.setY(i, yVal);

      // Interpolate geological color based on elevation
      const vertColor = new THREE.Color();
      if (normH < 0.3) {
        vertColor.copy(colorBasalt).lerp(colorRust, normH / 0.3);
      } else if (normH < 0.7) {
        vertColor.copy(colorRust).lerp(colorDune, (normH - 0.3) / 0.4);
      } else {
        vertColor.copy(colorDune).lerp(colorMineral, (normH - 0.7) / 0.3);
      }

      // Check cost map for caution or hazard highlight
      const cellCost = costMap?.cost?.[r]?.[c];
      if (cellCost === 'Infinity' || cellCost === Infinity || cellCost >= 9999) {
        vertColor.lerp(colorHazard, 0.45);
      } else if (typeof cellCost === 'number' && cellCost > 2.0) {
        vertColor.lerp(colorCaution, 0.35);
      }

      colors[i * 3 + 0] = vertColor.r;
      colors[i * 3 + 1] = vertColor.g;
      colors[i * 3 + 2] = vertColor.b;
    }

    geom.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geom.computeVertexNormals();

    const mat = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.88,
      metalness: 0.12,
      flatShading: false,
    });

    const terrainMesh = new THREE.Mesh(geom, mat);
    terrainMesh.receiveShadow = true;
    terrainMesh.castShadow = true;
    terrainMesh.name = 'MarsTerrainMesh';
    scene.add(terrainMesh);
    terrainMeshRef.current = terrainMesh;
  }, [dem, costMap]);

  // 3. Build Distinctive 3D Markers: Blue Start & Yellow Destination
  const createMarker = useCallback((type) => {
    const isStart = type === 'start';
    const primaryHex = isStart ? 0x3b82f6 : 0xf59e0b;
    const emissiveHex = isStart ? 0x1d4ed8 : 0xb45309;

    const group = new THREE.Group();

    // 1. Inverted Indicator Cone (tip touches the ground)
    const coneGeom = new THREE.ConeGeometry(0.5, 1.4, 16);
    coneGeom.rotateX(Math.PI); // Tip down
    coneGeom.translate(0, 0.7, 0); // Base sits at y=1.4, tip at y=0
    const coneMat = new THREE.MeshStandardMaterial({
      color: primaryHex,
      emissive: emissiveHex,
      emissiveIntensity: 0.8,
      metalness: 0.3,
      roughness: 0.2,
    });
    const cone = new THREE.Mesh(coneGeom, coneMat);
    cone.castShadow = true;
    group.add(cone);

    // 2. Beacon Gem on Top
    const gemGeom = new THREE.OctahedronGeometry(0.35);
    gemGeom.translate(0, 1.7, 0);
    const gemMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      emissive: primaryHex,
      emissiveIntensity: 1.0,
      roughness: 0.1,
    });
    const gem = new THREE.Mesh(gemGeom, gemMat);
    group.add(gem);

    // 3. Ground Target Ring
    const ringGeom = new THREE.RingGeometry(0.3, 0.65, 32);
    ringGeom.rotateX(-Math.PI / 2);
    ringGeom.translate(0, 0.05, 0); // Slight offset above terrain
    const ringMat = new THREE.MeshBasicMaterial({
      color: primaryHex,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.85,
    });
    const ring = new THREE.Mesh(ringGeom, ringMat);
    group.add(ring);

    // 4. Point Light for ground illumination
    const light = new THREE.PointLight(primaryHex, 1.5, 6);
    light.position.set(0, 1.2, 0);
    group.add(light);

    return group;
  }, []);

  // Update Blue Start Marker Position
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene || !dem?.elevation) return;

    if (!startPoint) {
      if (startMarkerGroupRef.current) {
        scene.remove(startMarkerGroupRef.current);
        startMarkerGroupRef.current = null;
      }
      return;
    }

    if (!startMarkerGroupRef.current) {
      startMarkerGroupRef.current = createMarker('start');
      scene.add(startMarkerGroupRef.current);
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

    startMarkerGroupRef.current.position.set(x, y, z);
  }, [startPoint, dem, createMarker]);

  // Update Yellow Destination Marker Position
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene || !dem?.elevation) return;

    if (!destinationPoint) {
      if (destMarkerGroupRef.current) {
        scene.remove(destMarkerGroupRef.current);
        destMarkerGroupRef.current = null;
      }
      return;
    }

    if (!destMarkerGroupRef.current) {
      destMarkerGroupRef.current = createMarker('destination');
      scene.add(destMarkerGroupRef.current);
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

    destMarkerGroupRef.current.position.set(x, y, z);
  }, [destinationPoint, dem, createMarker]);

  // 4. Build 3D Route Lines on the Terrain (Shortest in RED, Safest in GREEN)
  const createPathMesh = useCallback((path, elevation, rows, cols, hexColor, yOffset) => {
    if (!Array.isArray(path) || path.length < 2) return null;
    const { minElev, elevScale } = elevConfig.current;

    const points = [];
    for (let i = 0; i < path.length; i++) {
      const [r, c] = path[i];
      const { x, y, z } = gridToThree(r, c, elevation, rows, cols, minElev, elevScale, yOffset);
      points.push(new THREE.Vector3(x, y, z));
    }

    // Create smooth CatmullRom curve following waypoints
    const curve = new THREE.CatmullRomCurve3(points);
    const tubeGeom = new THREE.TubeGeometry(curve, points.length * 3, 0.16, 8, false);
    const tubeMat = new THREE.MeshStandardMaterial({
      color: hexColor,
      emissive: hexColor,
      emissiveIntensity: 0.6,
      roughness: 0.3,
      metalness: 0.5,
    });

    const mesh = new THREE.Mesh(tubeGeom, tubeMat);
    mesh.castShadow = true;
    return mesh;
  }, []);

  // Update Route Visualizations
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene || !dem?.elevation) return;

    // Clean up existing routes
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

    if (!navigation) return;

    // 1. Shortest Route in RED (#EF4444)
    const shortestData = navigation.shortest?.route;
    if (shortestData?.success && shortestData.path?.length > 1) {
      const redMesh = createPathMesh(
        shortestData.path,
        dem.elevation,
        dem.rows,
        dem.cols,
        0xef4444, // Red
        0.18 // Hover offset to avoid z-fighting
      );
      if (redMesh) {
        scene.add(redMesh);
        redRouteLineRef.current = redMesh;
      }
    }

    // 2. Safest Practical Route in GREEN (#10B981)
    const safestData = navigation.safest?.route;
    if (safestData?.success && safestData.path?.length > 1) {
      const greenMesh = createPathMesh(
        safestData.path,
        dem.elevation,
        dem.rows,
        dem.cols,
        0x10b981, // Green
        0.24 // Hover offset slightly above shortest for distinction
      );
      if (greenMesh) {
        scene.add(greenMesh);
        greenRouteLineRef.current = greenMesh;
      }
    }
  }, [navigation, dem, createPathMesh]);

  // 5. Build Procedural 3D Mars Rover Model with Rocker-Bogie Wheels
  const buildRoverModel = useCallback(() => {
    const group = new THREE.Group();
    const wheels = [];

    // Wheel dimensions
    const wheelRadius = 0.22;
    const wheelWidth = 0.14;

    // A. Main Avionics Chassis Deck (Gold insulated foil)
    const deckGeom = new THREE.BoxGeometry(0.85, 0.22, 1.15);
    const deckMat = new THREE.MeshStandardMaterial({
      color: 0xd4af37, // Gold foil
      roughness: 0.35,
      metalness: 0.75,
    });
    const deck = new THREE.Mesh(deckGeom, deckMat);
    deck.position.set(0, wheelRadius + 0.22, 0);
    deck.castShadow = true;
    group.add(deck);

    // B. Top Equipment Solar/Instrument Module (Dark navy)
    const topGeom = new THREE.BoxGeometry(0.72, 0.06, 0.95);
    const topMat = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      roughness: 0.2,
      metalness: 0.5,
    });
    const topModule = new THREE.Mesh(topGeom, topMat);
    topModule.position.set(0, wheelRadius + 0.36, -0.05);
    deck.add(topModule);

    // C. Forward Sensor Mast with Stereo Mastcams
    const mastGeom = new THREE.CylinderGeometry(0.025, 0.03, 0.55);
    const mastMat = new THREE.MeshStandardMaterial({ color: 0x64748b, metalness: 0.8 });
    const mast = new THREE.Mesh(mastGeom, mastMat);
    mast.position.set(0.2, 0.35, 0.38);
    mast.castShadow = true;
    deck.add(mast);

    const headGeom = new THREE.BoxGeometry(0.18, 0.08, 0.12);
    const headMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.3 });
    const camHead = new THREE.Mesh(headGeom, headMat);
    camHead.position.set(0, 0.28, 0);
    mast.add(camHead);

    // Dual stereo camera optics
    const lensGeom = new THREE.CylinderGeometry(0.025, 0.025, 0.04);
    lensGeom.rotateX(Math.PI / 2);
    const lensMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8 });
    const lensL = new THREE.Mesh(lensGeom, lensMat);
    lensL.position.set(-0.05, 0, 0.07);
    const lensR = new THREE.Mesh(lensGeom, lensMat);
    lensR.position.set(0.05, 0, 0.07);
    camHead.add(lensL);
    camHead.add(lensR);

    // D. High-Gain Parabolic Antenna
    const dishGeom = new THREE.CylinderGeometry(0.16, 0.04, 0.06, 16);
    dishGeom.rotateX(-Math.PI / 4);
    const dishMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, metalness: 0.6 });
    const dish = new THREE.Mesh(dishGeom, dishMat);
    dish.position.set(-0.24, 0.18, -0.35);
    deck.add(dish);

    // E. 6 Rocker-Bogie Cylindrical Wheels with Cleats
    const wheelGeom = new THREE.CylinderGeometry(wheelRadius, wheelRadius, wheelWidth, 16);
    wheelGeom.rotateZ(Math.PI / 2); // Oriented to roll along Z
    const wheelMat = new THREE.MeshStandardMaterial({
      color: 0x334155,
      roughness: 0.7,
      metalness: 0.3,
    });

    const wheelPositions = [
      [-0.55, wheelRadius, 0.45],  // Front Left
      [0.55, wheelRadius, 0.45],   // Front Right
      [-0.58, wheelRadius, 0.0],   // Middle Left
      [0.58, wheelRadius, 0.0],    // Middle Right
      [-0.55, wheelRadius, -0.45], // Rear Left
      [0.55, wheelRadius, -0.45],  // Rear Right
    ];

    wheelPositions.forEach(([wx, wy, wz]) => {
      const wheel = new THREE.Mesh(wheelGeom, wheelMat);
      wheel.position.set(wx, wy, wz);
      wheel.castShadow = true;
      group.add(wheel);
      wheels.push(wheel);

      // Suspension strut connecting to deck
      const strutGeom = new THREE.CylinderGeometry(0.02, 0.02, 0.35);
      const strutMat = new THREE.MeshStandardMaterial({ color: 0x475569 });
      const strut = new THREE.Mesh(strutGeom, strutMat);
      strut.position.set(wx * 0.75, wy + 0.12, wz);
      strut.rotation.z = wx > 0 ? -0.4 : 0.4;
      group.add(strut);
    });

    // F. Forward Navigation Beam
    const headlight = new THREE.SpotLight(0xffffff, 1.2, 8, Math.PI / 6, 0.4);
    headlight.position.set(0, wheelRadius + 0.3, 0.5);
    headlight.target.position.set(0, 0, 4);
    group.add(headlight);
    group.add(headlight.target);

    roverWheelsRef.current = wheels;
    return group;
  }, []);

  // Initialize or Position Rover
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene || !dem?.elevation) return;

    if (!roverGroupRef.current) {
      roverGroupRef.current = buildRoverModel();
      scene.add(roverGroupRef.current);
    }

    const path = navigation?.[activeRoute]?.route?.path;
    const originPoint = path?.[0] || startPoint || [2, 2];

    const { minElev, elevScale } = elevConfig.current;
    const { x, y, z } = gridToThree(
      originPoint[0],
      originPoint[1],
      dem.elevation,
      dem.rows,
      dem.cols,
      minElev,
      elevScale,
      0
    );

    // Place rover firmly on the terrain surface
    roverGroupRef.current.position.set(x, y, z);
  }, [dem, navigation, activeRoute, startPoint, buildRoverModel]);

  // 6. Kinematic Update: Keep wheels on terrain, rotate orientation & wheels
  useEffect(() => {
    if (!roverGroupRef.current || !dem?.elevation) return;

    const path = navigation?.[activeRoute]?.route?.path;
    if (!path || path.length < 2) return;

    const maxIdx = path.length - 1;
    const curIdx = Math.max(0, Math.min(maxIdx, roverProgress));
    const k = Math.floor(curIdx);
    const t = curIdx - k;

    const p0 = path[k] || path[0];
    const p1 = path[Math.min(k + 1, maxIdx)];

    // Interpolate continuous grid position
    const rFloat = p0[0] + (p1[0] - p0[0]) * t;
    const cFloat = p0[1] + (p1[1] - p0[1]) * t;

    const { minElev, elevScale } = elevConfig.current;
    const offsetX = (dem.cols - 1) / 2;
    const offsetZ = (dem.rows - 1) / 2;

    const worldX = cFloat - offsetX;
    const worldZ = rFloat - offsetZ;

    // Bilinear ground elevation interpolation guarantees zero floating or clipping
    const rawElev = bilinearElevation(rFloat, cFloat, dem.elevation, dem.rows, dem.cols);
    const worldY = (rawElev - minElev) * elevScale;

    roverGroupRef.current.position.set(worldX, worldY, worldZ);

    // Calculate heading direction
    const dCol = p1[1] - p0[1];
    const dRow = p1[0] - p0[0];
    if (Math.abs(dCol) > 0.001 || Math.abs(dRow) > 0.001) {
      const headingAngle = Math.atan2(dCol, dRow);
      roverGroupRef.current.rotation.y = headingAngle;
    }

    // Calculate local slope normal for terrain surface alignment
    const step = 0.5;
    const eRowPlus = bilinearElevation(rFloat + step, cFloat, dem.elevation, dem.rows, dem.cols);
    const eRowMinus = bilinearElevation(rFloat - step, cFloat, dem.elevation, dem.rows, dem.cols);
    const eColPlus = bilinearElevation(rFloat, cFloat + step, dem.elevation, dem.rows, dem.cols);
    const eColMinus = bilinearElevation(rFloat, cFloat - step, dem.elevation, dem.rows, dem.cols);

    const dz_dr = (eRowPlus - eRowMinus) * elevScale;
    const dz_dc = (eColPlus - eColMinus) * elevScale;

    // Tilt rover with local terrain slope
    roverGroupRef.current.rotation.x = dz_dr * 0.4;
    roverGroupRef.current.rotation.z = -dz_dc * 0.4;

    // Rotate wheels
    roverWheelsRef.current.forEach((wheel) => {
      wheel.rotation.x += 0.25;
    });
  }, [roverProgress, navigation, activeRoute, dem]);

  // 7. Raycasting: Mouse Click Terrain Selection (Start & Destination Markers)
  const handleCanvasClick = useCallback(
    (e) => {
      const container = mountRef.current;
      const camera = cameraRef.current;
      const terrainMesh = terrainMeshRef.current;
      if (!container || !camera || !terrainMesh || !dem?.rows) return;

      const rect = container.getBoundingClientRect();
      const mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const mouseY = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(new THREE.Vector2(mouseX, mouseY), camera);

      const intersects = raycaster.intersectObject(terrainMesh);
      if (intersects.length > 0) {
        const hit = intersects[0].point;
        const { row, col } = threeToGrid(hit.x, hit.z, dem.rows, dem.cols);

        if (isInsideBounds(row, col, dem.rows, dem.cols)) {
          // If explicit mode selected or auto progression
          if (selectionMode === 'start') {
            onSelectStart(row, col);
          } else if (selectionMode === 'destination') {
            onSelectDestination(row, col);
          } else {
            // Auto progression: first click sets Start, second click sets Destination
            if (!startPoint) {
              onSelectStart(row, col);
            } else if (!destinationPoint) {
              onSelectDestination(row, col);
            } else {
              // Both exist: clicking repositions Destination by default
              onSelectDestination(row, col);
            }
          }
        }
      }
    },
    [dem, selectionMode, startPoint, destinationPoint, onSelectStart, onSelectDestination]
  );

  // Mouse Move Hover Inspection
  const handleCanvasMouseMove = useCallback(
    (e) => {
      if (!onHoverCell || !terrainMeshRef.current || !dem?.rows) return;
      const container = mountRef.current;
      const camera = cameraRef.current;
      if (!container || !camera) return;

      const rect = container.getBoundingClientRect();
      const mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const mouseY = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(new THREE.Vector2(mouseX, mouseY), camera);

      const intersects = raycaster.intersectObject(terrainMeshRef.current);
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
        cursor: !startPoint || !destinationPoint ? 'crosshair' : 'grab',
        touchAction: 'none',
      }}
    />
  );
}
