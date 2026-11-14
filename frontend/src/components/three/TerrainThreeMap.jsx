import React, { useEffect, useRef, useCallback } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { MarsRoverController } from './MarsRoverModel';
import {
  threeToGrid,
  gridToThree,
  getInterpolatedElevation,
  elevationAt,
  isInsideBounds,
  bilinearElevation,
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

  // Persistent Three.js references
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const controlsRef = useRef(null);
  const terrainMeshRef = useRef(null);
  const roverControllerRef = useRef(null);

  // Multi-Hazard 3D Systems & Overlays
  const volcanicLightsRef = useRef([]);
  const volcanicEmberParticlesRef = useRef(null);
  const windDustParticlesRef = useRef(null);
  const dustDevilsGroupRef = useRef(null);
  const dustDevilVorticesRef = useRef([]);
  const landslideBouldersRef = useRef(null);
  const craterBouldersRef = useRef(null);
  const injectedHazardsGroupRef = useRef(null);

  // Route Ribbons & Tactical Beacons
  const redRouteLineRef = useRef(null);
  const greenRouteLineRef = useRef(null);
  const startBeaconRef = useRef(null);
  const destBeaconRef = useRef(null);

  // Spline Traversal & Continuous Kinematics Ref
  const splineRef = useRef(null);
  const uRef = useRef(0.0);
  const lastRoverPosRef = useRef({ r: 15, c: 15, heading: 0 });

  // State mirror refs for continuous 60+ FPS animation loop
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

  // 1. Initialize Three.js Scene, Camera, Renderer, Controls & Lighting
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;

    // Scene with deep Martian space background & calibrated atmospheric fog
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x06080d);
    // Linear fog: zero fog within 180 units of camera, gentle distant horizon fade
    scene.fog = new THREE.Fog(0x06080d, 180, 750);
    sceneRef.current = scene;

    // Camera (expanded view angle and depth for 200x200 sector)
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.5, 2500);
    camera.position.set(0, 185, 195);
    cameraRef.current = camera;

    // WebGL Renderer
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: 'high-performance',
      logarithmicDepthBuffer: true,
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.35;

    container.innerHTML = '';
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // OrbitControls: framed to view entire 200x200 Martian exploration sector
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 - 0.04;
    controls.minDistance = 4;
    controls.maxDistance = 1200;
    controls.target.set(0, 5, 0);
    controlsRef.current = controls;

    // High-visibility Tactical Lighting
    const ambientLight = new THREE.AmbientLight(0xffeedd, 0.75);
    scene.add(ambientLight);

    const hemiLight = new THREE.HemisphereLight(0xffb592, 0x181a20, 0.7);
    scene.add(hemiLight);

    const sunLight = new THREE.DirectionalLight(0xfff5ea, 1.8);
    sunLight.position.set(100, 160, 80);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 10;
    sunLight.shadow.camera.far = 450;
    sunLight.shadow.camera.left = -140;
    sunLight.shadow.camera.right = 140;
    sunLight.shadow.camera.top = 140;
    sunLight.shadow.camera.bottom = -140;
    sunLight.shadow.bias = 0.0008; // Positive bias prevents shadow acne
    scene.add(sunLight);

    // Warm opposite fill light so shadowed slopes are always clear and legible
    const fillLight = new THREE.DirectionalLight(0xd97757, 0.85);
    fillLight.position.set(-100, 45, -90);
    scene.add(fillLight);

    // Rover Controller Instance
    const roverController = new MarsRoverController();
    scene.add(roverController.root);
    roverControllerRef.current = roverController;

    // Groups for dynamic hazard injection & dust devils
    const dustDevilsGroup = new THREE.Group();
    dustDevilsGroup.name = 'DustDevils';
    scene.add(dustDevilsGroup);
    dustDevilsGroupRef.current = dustDevilsGroup;

    const injectedHazardsGroup = new THREE.Group();
    injectedHazardsGroup.name = 'InjectedHazards';
    scene.add(injectedHazardsGroup);
    injectedHazardsGroupRef.current = injectedHazardsGroup;

    // ─────────────────────────────────────────────────────────────
    // Continuous 60+ FPS Animation Loop with Decoupled Telemetry
    // ─────────────────────────────────────────────────────────────
    let lastTime = performance.now();
    let emberPhase = 0;
    let windTime = 0;
    let lastTelemetrySyncTime = 0;
    let lastCameraSyncTime = 0;

    const animate = () => {
      animFrameIdRef.current = requestAnimationFrame(animate);
      const now = performance.now();
      const deltaSec = Math.min((now - lastTime) / 1000, 0.08);
      lastTime = now;
      emberPhase += deltaSec * 3.0;
      windTime += deltaSec;

      const rover = roverControllerRef.current;
      const currentSpline = splineRef.current;

      // 1. Butter-Smooth Spline Kinematics & Velocity Physics
      if (isPlayingRef.current && currentSpline && rover) {
        const { curve, length: splineLength, count: waypointsCount, demElevation, demRows, demCols } = currentSpline;
        let curU = uRef.current;

        if (curU < 1.0) {
          const currentPoint = curve.getPointAt(curU);
          const tangent = curve.getTangentAt(curU).normalize();

          // Slope physics: dy / ds = sin(theta)
          const sinSlope = Math.max(-1.0, Math.min(1.0, tangent.y));
          const slopeRad = Math.asin(sinSlope);
          const slopeDeg = (slopeRad * 180) / Math.PI;

          // Grid coordinates of continuous rover position
          const curGrid = threeToGrid(currentPoint.x, currentPoint.z, demRows, demCols);
          const cellCost = costMapRef.current?.cost?.[curGrid.row]?.[curGrid.col] ?? 1.0;
          const isCaution = typeof cellCost === 'number' && cellCost > 2.0;

          // Dynamic velocity physics:
          // Base speed: 8.5 units/s * simSpeed
          let velocity = 8.5 * (simSpeedRef.current || 1.0);

          // Slope deceleration: up to 45% reduction when climbing steep uphill (>12 deg)
          if (slopeDeg > 0) {
            const uphillFactor = Math.min(1.0, slopeDeg / 28.0);
            velocity *= 1.0 - 0.45 * uphillFactor;
          } else {
            // Downhill gravity assist
            const downhillFactor = Math.min(1.0, Math.abs(slopeDeg) / 25.0);
            velocity *= 1.0 + 0.15 * downhillFactor;
          }

          // Traction slip penalty in sand dune caution zones
          if (isCaution) {
            velocity *= 0.72; // 28% slip reduction
          }

          const deltaDist = velocity * deltaSec;
          const deltaU = deltaDist / Math.max(1.0, splineLength);
          let nextU = Math.min(1.0, curU + deltaU);
          uRef.current = nextU;

          // Heading angle in horizontal XZ plane
          const headingAngle = Math.atan2(tangent.x, tangent.z);

          // Steering bogie angle from curvature derivative
          const lookAheadU = Math.min(1.0, nextU + 0.02);
          const nextTangent = curve.getTangentAt(lookAheadU).normalize();
          const nextHeading = Math.atan2(nextTangent.x, nextTangent.z);
          let dHeading = nextHeading - headingAngle;
          while (dHeading > Math.PI) dHeading -= Math.PI * 2;
          while (dHeading < -Math.PI) dHeading += Math.PI * 2;
          const steeringAngle = Math.max(-0.4, Math.min(0.4, dHeading * 2.8));

          // Smooth kinematic ground alignment with quaternion slerp damping
          const { minElev, elevScale } = elevConfig.current;
          const rFloat = curGrid.row;
          const cFloat = curGrid.col;
          const kin = rover.updateKinematics(
            rFloat,
            cFloat,
            headingAngle,
            demElevation,
            demRows,
            demCols,
            minElev,
            elevScale,
            deltaDist,
            deltaSec,
            true,
            steeringAngle
          );

          lastRoverPosRef.current = { r: rFloat, c: cFloat, heading: headingAngle, kin };

          // Throttled Telemetry Sync to React HUD (~12.5 Hz / 80ms)
          if (now - lastTelemetrySyncTime >= 80) {
            lastTelemetrySyncTime = now;
            const nominalProgress = nextU * (waypointsCount - 1);
            if (onRoverProgressUpdateRef.current) {
              onRoverProgressUpdateRef.current(nominalProgress, nextU >= 1.0);
            }

            if (onEnvironmentalUpdateRef.current) {
              const windSpeed = isCaution ? 38.5 + Math.random() * 4.0 : 22.0 + Math.random() * 2.5;
              const thermalFlux = cellCost >= 9999 ? 42.0 : cellCost > 2.0 ? 16.5 : 4.1;
              const seismicAlert =
                cellCost >= 9999 ? 'VOLCANIC HAZARD' : isCaution ? 'SEISMIC ACTIVE' : 'NOMINAL';

              onEnvironmentalUpdateRef.current({
                windSpeedMs: windSpeed.toFixed(1),
                windHeading: 'WNW (285°)',
                thermalFluxKw: thermalFlux.toFixed(1),
                seismicAlert,
                opticalDepth: (0.78 + Math.random() * 0.08).toFixed(2),
                roverPitch: kin.pitchDeg.toFixed(1),
                roverRoll: kin.rollDeg.toFixed(1),
              });
            }
          }

          if (nextU >= 1.0) {
            isPlayingRef.current = false;
            if (onRoverProgressUpdateRef.current) {
              onRoverProgressUpdateRef.current(waypointsCount - 1, true);
            }
          }
        }
      }

      // 2. Animate Volcanic Eruption Ember Particles
      const embers = volcanicEmberParticlesRef.current;
      if (embers && embers.geometry.attributes.position) {
        const posAttr = embers.geometry.attributes.position;
        const velAttr = embers.geometry.attributes.velocity;
        const arr = posAttr.array;
        const vArr = velAttr.array;
        const count = posAttr.count;

        for (let i = 0; i < count; i++) {
          const idx = i * 3;
          arr[idx + 1] += vArr[idx + 1] * deltaSec;
          arr[idx + 0] += vArr[idx + 0] * deltaSec + Math.sin(emberPhase + i) * 0.02;
          arr[idx + 2] += vArr[idx + 2] * deltaSec;

          if (arr[idx + 1] > vArr[idx + 1] * 3.0 + 8.0) {
            arr[idx + 1] = 0.5 + Math.random() * 1.5;
          }
        }
        posAttr.needsUpdate = true;
      }

      // 3. Animate Strong Martian Wind & Dust Storm Streaks
      const dust = windDustParticlesRef.current;
      if (dust && dust.geometry.attributes.position) {
        const dPos = dust.geometry.attributes.position;
        const dVel = dust.geometry.attributes.velocity;
        const pArr = dPos.array;
        const vArr = dVel.array;
        const dCount = dPos.count;

        for (let j = 0; j < dCount; j++) {
          const pIdx = j * 3;
          pArr[pIdx + 0] += vArr[pIdx + 0] * deltaSec * 1.8;
          pArr[pIdx + 2] += vArr[pIdx + 2] * deltaSec * 1.8;
          pArr[pIdx + 1] += Math.sin(windTime * 4.0 + j) * 0.02;

          // Wrap boundaries for 200x200 scale (-110 to +110)
          if (pArr[pIdx + 0] > 105) pArr[pIdx + 0] = -105;
          if (pArr[pIdx + 2] > 105) pArr[pIdx + 2] = -105;
        }
        dPos.needsUpdate = true;
      }

      // 4. Animate Roaming Dust Devils (Spin & Drift)
      const devils = dustDevilVorticesRef.current;
      if (devils.length > 0) {
        devils.forEach((vortex) => {
          vortex.mesh.rotation.y += vortex.spinSpeed * deltaSec;
          vortex.mesh.position.x += vortex.driftX * deltaSec;
          vortex.mesh.position.z += vortex.driftZ * deltaSec;

          if (vortex.mesh.position.x > 95) vortex.mesh.position.x = -95;
          if (vortex.mesh.position.z > 95) vortex.mesh.position.z = -95;
        });
      }

      // 5. Pulsing Volcanic Point Lights
      volcanicLightsRef.current.forEach((vLight, li) => {
        vLight.intensity = 2.0 + Math.sin(emberPhase * 1.5 + li * 1.2) * 0.9;
      });

      // 6. Camera Control: ORBIT vs ROVER_CHASE vs MASTCAM_POV
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
            roverPos.x + 0.4,
            roverPos.y + 1.85,
            roverPos.z + 0.7
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

      // Camera state sync for 2D Radar Minimap (Throttled to 500ms to eliminate React churn)
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

  // 2. Smoothly Focus Orbit Camera on Target Location (Triggered by Radar Minimap)
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

  // 3. Build Realistic 200x200 Martian Surface & Geomorphic Multi-Hazards
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
    const elevScale = 18.0 / elevRange; // Scaled for 200x200 relief
    elevConfig.current = { minElev: minE, maxElev: maxE, elevScale };

    // Dispose old terrain mesh and lights
    if (terrainMeshRef.current) {
      scene.remove(terrainMeshRef.current);
      terrainMeshRef.current.geometry.dispose();
      terrainMeshRef.current.material.dispose();
      terrainMeshRef.current = null;
    }

    volcanicLightsRef.current.forEach((l) => scene.remove(l));
    volcanicLightsRef.current = [];

    // PlaneGeometry matching 200x200 DEM
    const geom = new THREE.PlaneGeometry(cols - 1, rows - 1, cols - 1, rows - 1);
    geom.rotateX(-Math.PI / 2);

    const posAttr = geom.attributes.position;
    const vertexCount = posAttr.count;
    const colors = new Float32Array(vertexCount * 3);

    // Realistic Martian Mineral Colors (Rich, warm, highly legible palette)
    const colorBasaltRift = new THREE.Color(0x3a2216);   // Deep warm volcanic basalt
    const colorIronOxide = new THREE.Color(0x943d2b);    // Weathered Martian ferric oxide
    const colorDustyOrange = new THREE.Color(0xcb6e49);  // Windblown dust dune
    const colorPaleMineral = new THREE.Color(0xdfab82);  // High-altitude silica ridge
    const colorMagmaVein = new THREE.Color(0xff3700);    // Active volcanic lava fissure
    const colorCautionAmber = new THREE.Color(0xf59e0b); // High-slip caution / sand trap

    const vents = [];
    const scarpCells = [];
    const craterRimCells = [];

    const offsetX = (cols - 1) / 2;
    const offsetZ = (rows - 1) / 2;

    for (let i = 0; i < vertexCount; i++) {
      const c = i % cols;
      const r = Math.floor(i / cols);

      const rawZ = elevationAt(elevation, r, c) ?? minE;
      const normH = Math.max(0, Math.min(1, (rawZ - minE) / elevRange));
      const yVal = (rawZ - minE) * elevScale;

      posAttr.setY(i, yVal);

      // Strata coloring
      const vertColor = new THREE.Color();
      if (normH < 0.28) {
        vertColor.copy(colorBasaltRift).lerp(colorIronOxide, normH / 0.28);
      } else if (normH < 0.65) {
        vertColor.copy(colorIronOxide).lerp(colorDustyOrange, (normH - 0.28) / 0.37);
      } else {
        vertColor.copy(colorDustyOrange).lerp(colorPaleMineral, (normH - 0.65) / 0.35);
      }

      // Identify Hazards from cost map
      const cellCost = costMap?.cost?.[r]?.[c];
      const isImpassable = cellCost === 'Infinity' || cellCost === Infinity || cellCost >= 9999;
      const isCaution = typeof cellCost === 'number' && cellCost > 2.0 && !isImpassable;

      if (isImpassable) {
        vertColor.copy(colorMagmaVein);
        vents.push({ x: c - offsetX, y: yVal, z: r - offsetZ, r, c });
      } else if (isCaution) {
        vertColor.lerp(colorCautionAmber, 0.45);
        if (cellCost > 3.5) {
          scarpCells.push({ x: c - offsetX, y: yVal, z: r - offsetZ });
        }
      }

      // Check for impact crater rim region
      const dCrater = Math.hypot(r - rows * 0.7, c - cols * 0.7);
      if (Math.abs(dCrater - rows * 0.14) < 2.5) {
        craterRimCells.push({ x: c - offsetX, y: yVal, z: r - offsetZ });
      }

      colors[i * 3 + 0] = vertColor.r;
      colors[i * 3 + 1] = vertColor.g;
      colors[i * 3 + 2] = vertColor.b;
    }

    // Critical Three.js buffer updates & bounding sphere computation
    posAttr.needsUpdate = true;
    geom.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geom.computeVertexNormals();
    geom.computeBoundingBox();
    geom.computeBoundingSphere();

    const mat = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.8,
      metalness: 0.05,
      side: THREE.DoubleSide,
      flatShading: false,
    });

    const terrainMesh = new THREE.Mesh(geom, mat);
    terrainMesh.receiveShadow = true;
    terrainMesh.castShadow = false; // Never cast shadows on self to eliminate shadow acne
    terrainMesh.frustumCulled = false;
    terrainMesh.name = 'MarsRealisticTerrain';
    scene.add(terrainMesh);
    terrainMeshRef.current = terrainMesh;

    // ─────────────────────────────────────────────────────────────
    // Hazard System 1: Active Volcanic Magma Vents & Point Lights
    // ─────────────────────────────────────────────────────────────
    const clusterStep = Math.max(1, Math.floor(vents.length / 10));
    for (let vi = 0; vi < vents.length; vi += clusterStep) {
      const vent = vents[vi];
      const thermalLight = new THREE.PointLight(0xff3700, 2.5, 16, 1.8);
      thermalLight.position.set(vent.x, vent.y + 0.9, vent.z);
      scene.add(thermalLight);
      volcanicLightsRef.current.push(thermalLight);
    }

    // Volcanic Ember Particle System
    if (volcanicEmberParticlesRef.current) {
      scene.remove(volcanicEmberParticlesRef.current);
      volcanicEmberParticlesRef.current.geometry.dispose();
      volcanicEmberParticlesRef.current.material.dispose();
      volcanicEmberParticlesRef.current = null;
    }

    if (vents.length > 0) {
      const emberCount = 2000;
      const emberGeom = new THREE.BufferGeometry();
      const emberPositions = new Float32Array(emberCount * 3);
      const emberVelocities = new Float32Array(emberCount * 3);
      const emberColors = new Float32Array(emberCount * 3);

      const emberColorHot = new THREE.Color(0xffaa00);
      const emberColorRed = new THREE.Color(0xff3b00);

      for (let ei = 0; ei < emberCount; ei++) {
        const vent = vents[ei % vents.length];
        const eIdx = ei * 3;
        emberPositions[eIdx + 0] = vent.x + (Math.random() - 0.5) * 2.0;
        emberPositions[eIdx + 1] = vent.y + Math.random() * 5.0;
        emberPositions[eIdx + 2] = vent.z + (Math.random() - 0.5) * 2.0;

        emberVelocities[eIdx + 0] = (Math.random() - 0.3) * 0.9;
        emberVelocities[eIdx + 1] = 2.0 + Math.random() * 3.0;
        emberVelocities[eIdx + 2] = (Math.random() - 0.5) * 0.7;

        const cLerp = Math.random();
        const col = new THREE.Color().copy(emberColorRed).lerp(emberColorHot, cLerp);
        emberColors[eIdx + 0] = col.r;
        emberColors[eIdx + 1] = col.g;
        emberColors[eIdx + 2] = col.b;
      }

      emberGeom.setAttribute('position', new THREE.BufferAttribute(emberPositions, 3));
      emberGeom.setAttribute('velocity', new THREE.BufferAttribute(emberVelocities, 3));
      emberGeom.setAttribute('color', new THREE.BufferAttribute(emberColors, 3));

      const emberMat = new THREE.PointsMaterial({
        size: 0.35,
        vertexColors: true,
        transparent: true,
        opacity: 0.9,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });

      const emberPoints = new THREE.Points(emberGeom, emberMat);
      scene.add(emberPoints);
      volcanicEmberParticlesRef.current = emberPoints;
    }

    // ─────────────────────────────────────────────────────────────
    // Hazard System 2: Landslide Scarp Instanced Boulders
    // ─────────────────────────────────────────────────────────────
    if (landslideBouldersRef.current) {
      scene.remove(landslideBouldersRef.current);
      landslideBouldersRef.current.geometry.dispose();
      landslideBouldersRef.current.material.dispose();
      landslideBouldersRef.current = null;
    }

    if (scarpCells.length > 0) {
      const boulderCount = Math.min(160, scarpCells.length);
      const boulderGeom = new THREE.DodecahedronGeometry(0.55, 0);
      const boulderMat = new THREE.MeshStandardMaterial({
        color: 0x4a2e22,
        roughness: 0.9,
        metalness: 0.1,
        flatShading: true,
      });
      const boulderMesh = new THREE.InstancedMesh(boulderGeom, boulderMat, boulderCount);
      boulderMesh.castShadow = true;
      boulderMesh.receiveShadow = true;

      const dummy = new THREE.Object3D();
      for (let bi = 0; bi < boulderCount; bi++) {
        const cell = scarpCells[bi % scarpCells.length];
        const s = 0.5 + Math.random() * 0.9;
        dummy.position.set(
          cell.x + (Math.random() - 0.5) * 3.5,
          cell.y + s * 0.35,
          cell.z + (Math.random() - 0.5) * 3.5
        );
        dummy.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, Math.random() * Math.PI);
        dummy.scale.set(s, s * (0.8 + Math.random() * 0.4), s);
        dummy.updateMatrix();
        boulderMesh.setMatrixAt(bi, dummy.matrix);
      }
      boulderMesh.instanceMatrix.needsUpdate = true;
      scene.add(boulderMesh);
      landslideBouldersRef.current = boulderMesh;
    }

    // ─────────────────────────────────────────────────────────────
    // Hazard System 3: Crater Rim Boulder Ejecta InstancedMesh
    // ─────────────────────────────────────────────────────────────
    if (craterBouldersRef.current) {
      scene.remove(craterBouldersRef.current);
      craterBouldersRef.current.geometry.dispose();
      craterBouldersRef.current.material.dispose();
      craterBouldersRef.current = null;
    }

    if (craterRimCells.length > 0) {
      const ejectaCount = Math.min(180, craterRimCells.length);
      const ejectaGeom = new THREE.IcosahedronGeometry(0.48, 0);
      const ejectaMat = new THREE.MeshStandardMaterial({
        color: 0x2e1e17,
        roughness: 0.95,
        metalness: 0.05,
        flatShading: true,
      });
      const ejectaMesh = new THREE.InstancedMesh(ejectaGeom, ejectaMat, ejectaCount);
      ejectaMesh.castShadow = true;

      const dummy = new THREE.Object3D();
      for (let ci = 0; ci < ejectaCount; ci++) {
        const cell = craterRimCells[ci % craterRimCells.length];
        const s = 0.4 + Math.random() * 0.8;
        dummy.position.set(
          cell.x + (Math.random() - 0.5) * 2.8,
          cell.y + s * 0.3,
          cell.z + (Math.random() - 0.5) * 2.8
        );
        dummy.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, Math.random() * Math.PI);
        dummy.scale.set(s, s, s);
        dummy.updateMatrix();
        ejectaMesh.setMatrixAt(ci, dummy.matrix);
      }
      ejectaMesh.instanceMatrix.needsUpdate = true;
      scene.add(ejectaMesh);
      craterBouldersRef.current = ejectaMesh;
    }

    // ─────────────────────────────────────────────────────────────
    // Hazard System 4: Roaming Dust Devils (Spinning Helical Vortices)
    // ─────────────────────────────────────────────────────────────
    const devilsGroup = dustDevilsGroupRef.current;
    if (devilsGroup) {
      while (devilsGroup.children.length > 0) {
        const child = devilsGroup.children[0];
        devilsGroup.remove(child);
        if (child.geometry) child.geometry.dispose();
        if (child.material) child.material.dispose();
      }
      dustDevilVorticesRef.current = [];

      const numVortices = 5;
      const vortexSpawnCoords = [
        [-45, -30],
        [20, -55],
        [-60, 40],
        [35, 25],
        [-15, 65],
      ];

      for (let v = 0; v < numVortices; v++) {
        const spawn = vortexSpawnCoords[v];
        const pCount = 260;
        const vGeom = new THREE.BufferGeometry();
        const vPos = new Float32Array(pCount * 3);
        const vHeight = 14.0;

        for (let p = 0; p < pCount; p++) {
          const t = p / pCount;
          const y = t * vHeight;
          const radius = 0.3 + 2.2 * Math.pow(t, 0.8);
          const angle = t * Math.PI * 14.0 + (p % 3) * ((Math.PI * 2) / 3);
          vPos[p * 3 + 0] = Math.cos(angle) * radius + (Math.random() - 0.5) * 0.4;
          vPos[p * 3 + 1] = y;
          vPos[p * 3 + 2] = Math.sin(angle) * radius + (Math.random() - 0.5) * 0.4;
        }

        vGeom.setAttribute('position', new THREE.BufferAttribute(vPos, 3));
        const vMat = new THREE.PointsMaterial({
          color: 0xe09867,
          size: 0.3,
          transparent: true,
          opacity: 0.65,
          blending: THREE.NormalBlending,
          depthWrite: false,
        });

        const vPoints = new THREE.Points(vGeom, vMat);
        const groundY = bilinearElevation(
          spawn[1] + offsetZ,
          spawn[0] + offsetX,
          elevation,
          rows,
          cols
        );
        vPoints.position.set(spawn[0], (groundY - minE) * elevScale, spawn[1]);
        devilsGroup.add(vPoints);

        dustDevilVorticesRef.current.push({
          mesh: vPoints,
          spinSpeed: 10.0 + Math.random() * 4.0,
          driftX: 1.5 + Math.random() * 1.5,
          driftZ: 0.6 + Math.random() * 1.0,
        });
      }
    }

    // ─────────────────────────────────────────────────────────────
    // Ambient Atmospheric Wind & Dust Storm Streaks
    // ─────────────────────────────────────────────────────────────
    if (windDustParticlesRef.current) {
      scene.remove(windDustParticlesRef.current);
      windDustParticlesRef.current.geometry.dispose();
      windDustParticlesRef.current.material.dispose();
      windDustParticlesRef.current = null;
    }

    const dustCount = 3500;
    const dustGeom = new THREE.BufferGeometry();
    const dustPositions = new Float32Array(dustCount * 3);
    const dustVelocities = new Float32Array(dustCount * 3);

    for (let di = 0; di < dustCount; di++) {
      const dIdx = di * 3;
      dustPositions[dIdx + 0] = (Math.random() - 0.5) * 210;
      dustPositions[dIdx + 1] = 1.0 + Math.random() * 28.0;
      dustPositions[dIdx + 2] = (Math.random() - 0.5) * 210;

      dustVelocities[dIdx + 0] = 7.5 + Math.random() * 4.5;
      dustVelocities[dIdx + 1] = (Math.random() - 0.5) * 0.4;
      dustVelocities[dIdx + 2] = 2.8 + Math.random() * 2.2;
    }

    dustGeom.setAttribute('position', new THREE.BufferAttribute(dustPositions, 3));
    dustGeom.setAttribute('velocity', new THREE.BufferAttribute(dustVelocities, 3));

    const dustMat = new THREE.PointsMaterial({
      color: 0xdf8d64,
      size: 0.26,
      transparent: true,
      opacity: 0.45,
      blending: THREE.NormalBlending,
      depthWrite: false,
    });

    const dustPoints = new THREE.Points(dustGeom, dustMat);
    scene.add(dustPoints);
    windDustParticlesRef.current = dustPoints;
  }, [dem, costMap]);

  // 4. Build Tactical 3D Beacons with Vertical Laser Guides
  const createTacticalBeacon = useCallback((hexColor) => {
    const group = new THREE.Group();

    const coneGeom = new THREE.ConeGeometry(0.7, 2.0, 16);
    coneGeom.rotateX(Math.PI);
    coneGeom.translate(0, 1.0, 0);
    const coneMat = new THREE.MeshStandardMaterial({
      color: hexColor,
      emissive: hexColor,
      emissiveIntensity: 0.85,
      metalness: 0.3,
      roughness: 0.2,
    });
    const cone = new THREE.Mesh(coneGeom, coneMat);
    cone.castShadow = true;
    group.add(cone);

    const laserGeom = new THREE.CylinderGeometry(0.12, 0.12, 90, 8);
    laserGeom.translate(0, 45, 0);
    const laserMat = new THREE.MeshBasicMaterial({
      color: hexColor,
      transparent: true,
      opacity: 0.75,
      blending: THREE.AdditiveBlending,
    });
    const laser = new THREE.Mesh(laserGeom, laserMat);
    group.add(laser);

    const ringGeom = new THREE.RingGeometry(0.45, 0.95, 32);
    ringGeom.rotateX(-Math.PI / 2);
    ringGeom.translate(0, 0.08, 0);
    const ringMat = new THREE.MeshBasicMaterial({
      color: hexColor,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.9,
    });
    const ring = new THREE.Mesh(ringGeom, ringMat);
    group.add(ring);

    const beaconLight = new THREE.PointLight(hexColor, 2.8, 12);
    beaconLight.position.set(0, 1.6, 0);
    group.add(beaconLight);

    return group;
  }, []);

  // Update Start & Destination Tactical Beacons
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene || !dem?.elevation) return;

    if (!startPoint) {
      if (startBeaconRef.current) {
        scene.remove(startBeaconRef.current);
        startBeaconRef.current = null;
      }
    } else {
      if (!startBeaconRef.current) {
        startBeaconRef.current = createTacticalBeacon(0x06b6d4);
        scene.add(startBeaconRef.current);
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
      startBeaconRef.current.position.set(x, y, z);
    }

    if (!destinationPoint) {
      if (destBeaconRef.current) {
        scene.remove(destBeaconRef.current);
        destBeaconRef.current = null;
      }
    } else {
      if (!destBeaconRef.current) {
        destBeaconRef.current = createTacticalBeacon(0xf59e0b);
        scene.add(destBeaconRef.current);
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
      destBeaconRef.current.position.set(x, y, z);
    }
  }, [startPoint, destinationPoint, dem, createTacticalBeacon]);

  // 5. Build 3D Route Ribbons & Setup Continuous Spline Traversal
  const buildRouteMesh = useCallback((path, elevation, rows, cols, hexColor, yOffset) => {
    if (!Array.isArray(path) || path.length < 2) return null;
    const { minElev, elevScale } = elevConfig.current;

    const points = [];
    for (let i = 0; i < path.length; i++) {
      const [r, c] = path[i];
      const { x, y, z } = gridToThree(r, c, elevation, rows, cols, minElev, elevScale, yOffset);
      points.push(new THREE.Vector3(x, y, z));
    }

    const curve = new THREE.CatmullRomCurve3(points, false, 'centripetal', 0.25);
    const tubeGeom = new THREE.TubeGeometry(curve, points.length * 4, 0.52, 8, false);
    const tubeMat = new THREE.MeshStandardMaterial({
      color: hexColor,
      emissive: hexColor,
      emissiveIntensity: 0.85,
      roughness: 0.2,
      metalness: 0.8,
    });

    const mesh = new THREE.Mesh(tubeGeom, tubeMat);
    mesh.castShadow = true;
    return { mesh, curve };
  }, []);

  // Update Route Meshes and Build Continuous Spline Traversal Curve
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

    // 1. Shortest Route in RED (#EF4444)
    const shortestData = navigation.shortest?.route;
    if (shortestData?.success && shortestData.path?.length > 1) {
      const red = buildRouteMesh(shortestData.path, dem.elevation, dem.rows, dem.cols, 0xef4444, 0.38);
      if (red) {
        scene.add(red.mesh);
        redRouteLineRef.current = red.mesh;
      }
    }

    // 2. Safest Practical Route in GREEN (#10B981)
    const safestData = navigation.safest?.route;
    if (safestData?.success && safestData.path?.length > 1) {
      const green = buildRouteMesh(safestData.path, dem.elevation, dem.rows, dem.cols, 0x10b981, 0.46);
      if (green) {
        scene.add(green.mesh);
        greenRouteLineRef.current = green.mesh;
      }
    }

    // 3. Construct Active CatmullRomCurve3 for Continuous Traversal
    const activeRouteData = navigation[activeRoute]?.route;
    if (activeRouteData?.success && activeRouteData.path?.length > 1) {
      const path = activeRouteData.path;
      const { minElev, elevScale } = elevConfig.current;
      const points = path.map(([r, c]) => {
        const { x, y, z } = gridToThree(r, c, dem.elevation, dem.rows, dem.cols, minElev, elevScale, 0);
        return new THREE.Vector3(x, y, z);
      });
      const activeCurve = new THREE.CatmullRomCurve3(points, false, 'centripetal', 0.25);
      splineRef.current = {
        curve: activeCurve,
        length: activeCurve.getLength(),
        path,
        count: path.length,
        demElevation: dem.elevation,
        demRows: dem.rows,
        demCols: dem.cols,
      };
    } else {
      splineRef.current = null;
    }
  }, [navigation, activeRoute, dem, buildRouteMesh]);

  // Sync Rover U progress from external state (e.g., reset, timeline seek)
  useEffect(() => {
    const activeSpline = splineRef.current;
    if (!activeSpline) return;
    const maxIdx = Math.max(1, activeSpline.count - 1);
    const targetU = Math.max(0, Math.min(1, roverProgress / maxIdx));

    // When NOT playing, immediately position the rover at the requested index
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

  // Initial Placement of Rover at Start Point if no active route playing
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

  // 6. Raycast Terrain Interaction for Start/Dest Pins and Hazard Injection
  const handleCanvasClick = useCallback(
    (e) => {
      if (cameraModeRef.current !== 'ORBIT') return;

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
          // If in Hazard Injection mode:
          if (toolMode === 'landslide' || toolMode === 'vortex' || toolMode === 'fissure') {
            if (onInjectHazard) {
              onInjectHazard(toolMode, row, col);
            }
            return;
          }

          // Otherwise Nav selection mode:
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
