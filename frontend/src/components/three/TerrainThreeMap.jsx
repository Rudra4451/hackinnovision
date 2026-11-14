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
}) {
  const mountRef = useRef(null);

  // Persistent Three.js references
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const controlsRef = useRef(null);
  const terrainMeshRef = useRef(null);
  const roverControllerRef = useRef(null);

  // Overlays & Particle Systems
  const volcanicLightsRef = useRef([]);
  const volcanicEmberParticlesRef = useRef(null);
  const windDustParticlesRef = useRef(null);
  const redRouteLineRef = useRef(null);
  const greenRouteLineRef = useRef(null);
  const startBeaconRef = useRef(null);
  const destBeaconRef = useRef(null);

  // Volcanic vent coordinates cache
  const volcanicVentsRef = useRef([]);

  // Animation and state refs
  const animFrameIdRef = useRef(null);
  const isPlayingRef = useRef(isPlaying);
  const activeRouteRef = useRef(activeRoute);
  const roverProgressRef = useRef(roverProgress);
  const navigationRef = useRef(navigation);
  const cameraModeRef = useRef(cameraMode);
  const lastRoverPosRef = useRef({ r: 5, c: 5, heading: 0 });

  isPlayingRef.current = isPlaying;
  activeRouteRef.current = activeRoute;
  roverProgressRef.current = roverProgress;
  navigationRef.current = navigation;
  cameraModeRef.current = cameraMode;

  const elevConfig = useRef({ minElev: 0, maxElev: 60, elevScale: 0.32 });

  // 1. Initialize Three.js Scene, Camera, Renderer, Controls & Lighting
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x06080d);
    scene.fog = new THREE.FogExp2(0x06080d, 0.0055);
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.2, 1200);
    camera.position.set(0, 52, 65);
    cameraRef.current = camera;

    // Renderer
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
    renderer.toneMappingExposure = 1.25;

    container.innerHTML = '';
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 - 0.04;
    controls.minDistance = 4;
    controls.maxDistance = 220;
    controls.target.set(0, 2, 0);
    controlsRef.current = controls;

    // Tactical Lighting: Distant Martian Sun + Atmospheric Scatter
    const ambientLight = new THREE.AmbientLight(0xffecd9, 0.45);
    scene.add(ambientLight);

    const hemiLight = new THREE.HemisphereLight(0xffa07a, 0x090b10, 0.5);
    scene.add(hemiLight);

    const sunLight = new THREE.DirectionalLight(0xfff3e6, 1.4);
    sunLight.position.set(60, 95, 45);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 10;
    sunLight.shadow.camera.far = 240;
    sunLight.shadow.camera.left = -55;
    sunLight.shadow.camera.right = 55;
    sunLight.shadow.camera.top = 55;
    sunLight.shadow.camera.bottom = -55;
    sunLight.shadow.bias = -0.0005;
    scene.add(sunLight);

    // Distant Martian Horizon Glow Light
    const horizonLight = new THREE.DirectionalLight(0xd97757, 0.55);
    horizonLight.position.set(-70, 18, -60);
    scene.add(horizonLight);

    // Initialize Mars Rover Controller
    const roverController = new MarsRoverController();
    scene.add(roverController.root);
    roverControllerRef.current = roverController;

    // Animation & Physics Loop
    let lastTime = performance.now();
    let emberPhase = 0;
    let windTime = 0;

    const animate = () => {
      animFrameIdRef.current = requestAnimationFrame(animate);
      const now = performance.now();
      const deltaSec = Math.min((now - lastTime) / 1000, 0.08);
      lastTime = now;
      emberPhase += deltaSec * 3.0;
      windTime += deltaSec;

      // 1. Advance Rover Simulation if playing
      if (isPlayingRef.current && navigationRef.current) {
        const curRouteKey = activeRouteRef.current;
        const routeData = navigationRef.current[curRouteKey]?.route;
        const path = routeData?.path || [];

        if (path.length > 1) {
          const maxIdx = path.length - 1;
          let nextProgress = roverProgressRef.current + deltaSec * 3.8;

          if (nextProgress >= maxIdx) {
            nextProgress = maxIdx;
            if (onRoverProgressUpdate) {
              onRoverProgressUpdate(maxIdx, true);
            }
          } else {
            if (onRoverProgressUpdate) {
              onRoverProgressUpdate(nextProgress, false);
            }
          }
          roverProgressRef.current = nextProgress;
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
          arr[idx + 1] += vArr[idx + 1] * deltaSec; // Vertical rise
          arr[idx + 0] += vArr[idx + 0] * deltaSec + Math.sin(emberPhase + i) * 0.02; // Turbulent drift
          arr[idx + 2] += vArr[idx + 2] * deltaSec;

          // Reset if exceeded apex
          if (arr[idx + 1] > vArr[idx + 1] * 2.8 + 6.0) {
            const vents = volcanicVentsRef.current;
            if (vents.length > 0) {
              const vent = vents[i % vents.length];
              arr[idx + 0] = vent.x + (Math.random() - 0.5) * 1.2;
              arr[idx + 1] = vent.y + 0.2;
              arr[idx + 2] = vent.z + (Math.random() - 0.5) * 1.2;
            }
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
          pArr[pIdx + 1] += Math.sin(windTime * 4.0 + j) * 0.015;

          // Wrap boundaries
          if (pArr[pIdx + 0] > 40) pArr[pIdx + 0] = -40;
          if (pArr[pIdx + 2] > 40) pArr[pIdx + 2] = -40;
        }
        dPos.needsUpdate = true;
      }

      // 4. Animate Volcanic Point Lights (Thermal Fissure Pulsing)
      volcanicLightsRef.current.forEach((vLight, li) => {
        vLight.intensity = 1.8 + Math.sin(emberPhase * 1.5 + li * 1.2) * 0.8;
      });

      // 5. Camera Control Logic: ORBIT vs ROVER_CHASE vs MASTCAM_POV
      const rover = roverControllerRef.current;
      const camMode = cameraModeRef.current;

      if (rover && rover.root) {
        const roverPos = rover.root.position;
        const heading = lastRoverPosRef.current.heading;
        const cosH = Math.cos(heading);
        const sinH = Math.sin(heading);

        if (camMode === 'ROVER_CHASE') {
          controls.enabled = false;
          // Position camera behind and above rover along heading
          const chaseCamTarget = new THREE.Vector3(
            roverPos.x - sinH * 11.0,
            roverPos.y + 5.5,
            roverPos.z - cosH * 11.0
          );
          camera.position.lerp(chaseCamTarget, 0.08);
          const lookAheadTarget = new THREE.Vector3(
            roverPos.x + sinH * 6.0,
            roverPos.y + 1.2,
            roverPos.z + cosH * 6.0
          );
          camera.lookAt(lookAheadTarget);
        } else if (camMode === 'MASTCAM_POV') {
          controls.enabled = false;
          // Position camera at Mastcam optic head
          const mastCamPos = new THREE.Vector3(
            roverPos.x + 0.4,
            roverPos.y + 1.85,
            roverPos.z + 0.7
          );
          camera.position.copy(mastCamPos);
          const forwardTarget = new THREE.Vector3(
            roverPos.x + sinH * 22.0,
            roverPos.y + 0.8,
            roverPos.z + cosH * 22.0
          );
          camera.lookAt(forwardTarget);
        } else {
          // Standard ORBIT mode
          controls.enabled = true;
          controls.update();
        }
      } else {
        controls.update();
      }

      renderer.render(scene, camera);
    };
    animate();

    // Window Resize Handler
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

  // 2. Build High-Realism Martian Surface Mesh with Volcanic Magma Fissures
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
    const elevScale = 16.0 / elevRange;
    elevConfig.current = { minElev: minE, maxElev: maxE, elevScale };

    // Dispose old terrain mesh and lights
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

    volcanicLightsRef.current.forEach((l) => scene.remove(l));
    volcanicLightsRef.current = [];
    volcanicVentsRef.current = [];

    // PlaneGeometry matching DEM shape
    const geom = new THREE.PlaneGeometry(cols - 1, rows - 1, cols - 1, rows - 1);
    geom.rotateX(-Math.PI / 2);

    const posAttr = geom.attributes.position;
    const vertexCount = posAttr.count;
    const colors = new Float32Array(vertexCount * 3);

    // Realistic Martian Mineral Colors
    const colorBasaltRift = new THREE.Color(0x190f0c);    // Dark volcanic basalt
    const colorIronOxide = new THREE.Color(0x823423);     // Weathered ferric oxide
    const colorDustyOrange = new THREE.Color(0xb85938);   // Windblown dust dune
    const colorPaleMineral = new THREE.Color(0xdfab82);   // High-altitude silica ridge
    const colorMagmaVein = new THREE.Color(0xff4500);     // Active volcanic lava fissure
    const colorCautionAmber = new THREE.Color(0xd97706);  // High-slip caution zone

    const vents = [];

    for (let i = 0; i < vertexCount; i++) {
      const c = i % cols;
      const r = Math.floor(i / cols);

      const rawZ = elevationAt(elevation, r, c) ?? minE;
      const normH = Math.max(0, Math.min(1, (rawZ - minE) / elevRange));
      const yVal = (rawZ - minE) * elevScale;

      posAttr.setY(i, yVal);

      // Geological strata coloring
      const vertColor = new THREE.Color();
      if (normH < 0.28) {
        vertColor.copy(colorBasaltRift).lerp(colorIronOxide, normH / 0.28);
      } else if (normH < 0.65) {
        vertColor.copy(colorIronOxide).lerp(colorDustyOrange, (normH - 0.28) / 0.37);
      } else {
        vertColor.copy(colorDustyOrange).lerp(colorPaleMineral, (normH - 0.65) / 0.35);
      }

      // Volcanic Magma Fissure & Hazard Shading
      const cellCost = costMap?.cost?.[r]?.[c];
      const isImpassable = cellCost === 'Infinity' || cellCost === Infinity || cellCost >= 9999;
      const isCaution = typeof cellCost === 'number' && cellCost > 2.0 && !isImpassable;

      if (isImpassable) {
        // Glowing magma fissure
        vertColor.copy(colorMagmaVein);
        const offsetX = (cols - 1) / 2;
        const offsetZ = (rows - 1) / 2;
        vents.push({ x: c - offsetX, y: yVal, z: r - offsetZ, r, c });
      } else if (isCaution) {
        vertColor.lerp(colorCautionAmber, 0.42);
      }

      colors[i * 3 + 0] = vertColor.r;
      colors[i * 3 + 1] = vertColor.g;
      colors[i * 3 + 2] = vertColor.b;
    }

    geom.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geom.computeVertexNormals();

    const mat = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.85,
      metalness: 0.15,
      flatShading: false,
    });

    const terrainMesh = new THREE.Mesh(geom, mat);
    terrainMesh.receiveShadow = true;
    terrainMesh.castShadow = true;
    terrainMesh.name = 'MarsRealisticTerrain';
    scene.add(terrainMesh);
    terrainMeshRef.current = terrainMesh;
    volcanicVentsRef.current = vents;

    // Spawn thermal point lights at primary volcanic fissure clusters
    const clusterStep = Math.max(1, Math.floor(vents.length / 8));
    for (let vi = 0; vi < vents.length; vi += clusterStep) {
      const vent = vents[vi];
      const thermalLight = new THREE.PointLight(0xff3700, 2.2, 10, 1.8);
      thermalLight.position.set(vent.x, vent.y + 0.8, vent.z);
      scene.add(thermalLight);
      volcanicLightsRef.current.push(thermalLight);
    }

    // 3. Build Volcanic Ash & Ember Particle System (GPU Points)
    if (volcanicEmberParticlesRef.current) {
      scene.remove(volcanicEmberParticlesRef.current);
      volcanicEmberParticlesRef.current.geometry.dispose();
      volcanicEmberParticlesRef.current.material.dispose();
      volcanicEmberParticlesRef.current = null;
    }

    if (vents.length > 0) {
      const emberCount = 1800;
      const emberGeom = new THREE.BufferGeometry();
      const emberPositions = new Float32Array(emberCount * 3);
      const emberVelocities = new Float32Array(emberCount * 3);
      const emberColors = new Float32Array(emberCount * 3);

      const emberColorHot = new THREE.Color(0xffaa00);
      const emberColorRed = new THREE.Color(0xff3b00);

      for (let ei = 0; ei < emberCount; ei++) {
        const vent = vents[ei % vents.length];
        const eIdx = ei * 3;

        emberPositions[eIdx + 0] = vent.x + (Math.random() - 0.5) * 1.5;
        emberPositions[eIdx + 1] = vent.y + Math.random() * 4.0;
        emberPositions[eIdx + 2] = vent.z + (Math.random() - 0.5) * 1.5;

        emberVelocities[eIdx + 0] = (Math.random() - 0.3) * 0.8;
        emberVelocities[eIdx + 1] = 1.8 + Math.random() * 2.5; // Upward thermal buoyancy
        emberVelocities[eIdx + 2] = (Math.random() - 0.5) * 0.6;

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
        size: 0.32,
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

    // 4. Build Strong Martian Wind & Dust Storm Streaks
    if (windDustParticlesRef.current) {
      scene.remove(windDustParticlesRef.current);
      windDustParticlesRef.current.geometry.dispose();
      windDustParticlesRef.current.material.dispose();
      windDustParticlesRef.current = null;
    }

    const dustCount = 2800;
    const dustGeom = new THREE.BufferGeometry();
    const dustPositions = new Float32Array(dustCount * 3);
    const dustVelocities = new Float32Array(dustCount * 3);

    for (let di = 0; di < dustCount; di++) {
      const dIdx = di * 3;
      dustPositions[dIdx + 0] = (Math.random() - 0.5) * 75;
      dustPositions[dIdx + 1] = 1.0 + Math.random() * 18.0;
      dustPositions[dIdx + 2] = (Math.random() - 0.5) * 75;

      // Directional wind vector: WNW heading
      dustVelocities[dIdx + 0] = 7.5 + Math.random() * 4.5;
      dustVelocities[dIdx + 1] = (Math.random() - 0.5) * 0.4;
      dustVelocities[dIdx + 2] = 2.8 + Math.random() * 2.2;
    }

    dustGeom.setAttribute('position', new THREE.BufferAttribute(dustPositions, 3));
    dustGeom.setAttribute('velocity', new THREE.BufferAttribute(dustVelocities, 3));

    const dustMat = new THREE.PointsMaterial({
      color: 0xdf8d64,
      size: 0.22,
      transparent: true,
      opacity: 0.45,
      blending: THREE.NormalBlending,
      depthWrite: false,
    });

    const dustPoints = new THREE.Points(dustGeom, dustMat);
    scene.add(dustPoints);
    windDustParticlesRef.current = dustPoints;
  }, [dem, costMap]);

  // 3. Build Tactical 3D Beacons with Vertical Laser Guides (Cyan Start & Amber Destination)
  const createTacticalBeacon = useCallback((hexColor) => {
    const group = new THREE.Group();

    // Inverted Beacon Pointer Cone
    const coneGeom = new THREE.ConeGeometry(0.55, 1.6, 16);
    coneGeom.rotateX(Math.PI);
    coneGeom.translate(0, 0.8, 0);
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

    // Vertical Sky Laser Guide (Cylinder pointing 40 units into the sky)
    const laserGeom = new THREE.CylinderGeometry(0.04, 0.04, 40, 8);
    laserGeom.translate(0, 20, 0);
    const laserMat = new THREE.MeshBasicMaterial({
      color: hexColor,
      transparent: true,
      opacity: 0.55,
      blending: THREE.AdditiveBlending,
    });
    const laser = new THREE.Mesh(laserGeom, laserMat);
    group.add(laser);

    // Ground Target Reticle Rings
    const ringGeom = new THREE.RingGeometry(0.35, 0.75, 32);
    ringGeom.rotateX(-Math.PI / 2);
    ringGeom.translate(0, 0.06, 0);
    const ringMat = new THREE.MeshBasicMaterial({
      color: hexColor,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.9,
    });
    const ring = new THREE.Mesh(ringGeom, ringMat);
    group.add(ring);

    // Illuminating Point Light
    const beaconLight = new THREE.PointLight(hexColor, 2.2, 8);
    beaconLight.position.set(0, 1.4, 0);
    group.add(beaconLight);

    return group;
  }, []);

  // Update Start & Destination Tactical Beacons
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene || !dem?.elevation) return;

    // Start Beacon (Cyan #06B6D4)
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

    // Destination Beacon (Amber #F59E0B)
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

  // 4. Build 3D Route Ribbons (Elevated above terrain, zero clipping)
  const buildRouteMesh = useCallback((path, elevation, rows, cols, hexColor, yOffset) => {
    if (!Array.isArray(path) || path.length < 2) return null;
    const { minElev, elevScale } = elevConfig.current;

    const points = [];
    for (let i = 0; i < path.length; i++) {
      const [r, c] = path[i];
      const { x, y, z } = gridToThree(r, c, elevation, rows, cols, minElev, elevScale, yOffset);
      points.push(new THREE.Vector3(x, y, z));
    }

    const curve = new THREE.CatmullRomCurve3(points);
    const tubeGeom = new THREE.TubeGeometry(curve, points.length * 4, 0.22, 8, false);
    const tubeMat = new THREE.MeshStandardMaterial({
      color: hexColor,
      emissive: hexColor,
      emissiveIntensity: 0.75,
      roughness: 0.2,
      metalness: 0.8,
    });

    const mesh = new THREE.Mesh(tubeGeom, tubeMat);
    mesh.castShadow = true;
    return mesh;
  }, []);

  // Update Safest (Green) and Shortest (Red) Route Ribbons
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

    if (!navigation) return;

    // 1. Shortest Route in RED (#EF4444)
    const shortestData = navigation.shortest?.route;
    if (shortestData?.success && shortestData.path?.length > 1) {
      const redMesh = buildRouteMesh(
        shortestData.path,
        dem.elevation,
        dem.rows,
        dem.cols,
        0xef4444,
        0.26
      );
      if (redMesh) {
        scene.add(redMesh);
        redRouteLineRef.current = redMesh;
      }
    }

    // 2. Safest Practical Route in GREEN (#10B981)
    const safestData = navigation.safest?.route;
    if (safestData?.success && safestData.path?.length > 1) {
      const greenMesh = buildRouteMesh(
        safestData.path,
        dem.elevation,
        dem.rows,
        dem.cols,
        0x10b981,
        0.34 // Slightly higher elevation to clearly differentiate overlays
      );
      if (greenMesh) {
        scene.add(greenMesh);
        greenRouteLineRef.current = greenMesh;
      }
    }
  }, [navigation, dem, buildRouteMesh]);

  // 5. Kinematic Rover Position & Suspension Update (ALWAYS Visible at Start)
  useEffect(() => {
    const rover = roverControllerRef.current;
    if (!rover || !dem?.elevation) return;

    const path = navigation?.[activeRoute]?.route?.path;
    const hasPath = Array.isArray(path) && path.length > 1;

    let rFloat = 5;
    let cFloat = 5;
    let headingAngle = 0;
    let deltaDist = 0.05;

    if (hasPath) {
      const maxIdx = path.length - 1;
      const curIdx = Math.max(0, Math.min(maxIdx, roverProgress));
      const k = Math.floor(curIdx);
      const t = curIdx - k;

      const p0 = path[k] || path[0];
      const p1 = path[Math.min(k + 1, maxIdx)];

      rFloat = p0[0] + (p1[0] - p0[0]) * t;
      cFloat = p0[1] + (p1[1] - p0[1]) * t;

      const dCol = p1[1] - p0[1];
      const dRow = p1[0] - p0[0];
      if (Math.abs(dCol) > 0.001 || Math.abs(dRow) > 0.001) {
        headingAngle = Math.atan2(dCol, dRow);
      }
    } else if (startPoint) {
      rFloat = startPoint[0];
      cFloat = startPoint[1];
    }

    const { minElev, elevScale } = elevConfig.current;
    const kin = rover.updateKinematics(
      rFloat,
      cFloat,
      headingAngle,
      dem.elevation,
      dem.rows,
      dem.cols,
      minElev,
      elevScale,
      isPlaying ? deltaDist : 0
    );

    lastRoverPosRef.current = { r: rFloat, c: cFloat, heading: headingAngle, kin };

    // Environmental Danger Telemetry Calculation
    if (onEnvironmentalUpdate) {
      let closestVentDist = Infinity;
      const vents = volcanicVentsRef.current;
      for (let vi = 0; vi < vents.length; vi++) {
        const dR = vents[vi].r - rFloat;
        const dC = vents[vi].c - cFloat;
        const dist = Math.sqrt(dR * dR + dC * dC);
        if (dist < closestVentDist) closestVentDist = dist;
      }

      const cellCost = costMap?.cost?.[Math.round(rFloat)]?.[Math.round(cFloat)] ?? 1.0;
      const isCaution = typeof cellCost === 'number' && cellCost > 2.0;
      const isHazard = cellCost === 'Infinity' || cellCost === Infinity || cellCost >= 9999;

      const windSpeed = isCaution ? 38.5 + Math.random() * 4.0 : 22.0 + Math.random() * 2.5;
      const thermalFlux = closestVentDist < 4.0 ? 38.4 : closestVentDist < 8.0 ? 18.2 : 4.1;
      const seismicAlert = isHazard ? 'VOLCANIC HAZARD' : closestVentDist < 6.0 ? 'SEISMIC ACTIVE' : 'NOMINAL';

      onEnvironmentalUpdate({
        windSpeedMs: windSpeed.toFixed(1),
        windHeading: 'WNW (285°)',
        thermalFluxKw: thermalFlux.toFixed(1),
        seismicAlert,
        opticalDepth: (0.75 + Math.random() * 0.1).toFixed(2),
        roverPitch: kin.pitchDeg.toFixed(1),
        roverRoll: kin.rollDeg.toFixed(1),
      });
    }
  }, [
    roverProgress,
    navigation,
    activeRoute,
    startPoint,
    dem,
    costMap,
    isPlaying,
    onEnvironmentalUpdate,
  ]);

  // 6. Raycast Terrain Interaction for Start & Destination Pins
  const handleCanvasClick = useCallback(
    (e) => {
      // In CHASE or MASTCAM mode, user can view but clicks shouldn't move pins accidentally
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
    [dem, selectionMode, startPoint, destinationPoint, onSelectStart, onSelectDestination]
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
        cursor: cameraMode === 'ORBIT' ? (!startPoint || !destinationPoint ? 'crosshair' : 'grab') : 'default',
        touchAction: 'none',
      }}
    />
  );
}
