import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { getInterpolatedElevation } from '../../utils/coordinateMapping';

export class MarsRoverController {
  constructor() {
    this.root = new THREE.Group();
    this.root.name = 'MarsRoverRoot';
    this.wheels = [];
    this.wheelRadius = 0.36;
    this.roverLength = 3.2;
    this.roverWidth = 2.2;
    this.headlight = null;
    this.headlightTarget = null;
    this.isCustomModel = false;

    this.buildProceduralModel();
    this.tryLoadGLTFModel('/models/perseverance.glb');
  }

  buildProceduralModel() {
    const group = new THREE.Group();
    group.name = 'ProceduralRover';

    const goldFoilMat = new THREE.MeshStandardMaterial({
      color: 0xd4af37,
      roughness: 0.35,
      metalness: 0.85,
    });

    const darkAvionicsMat = new THREE.MeshStandardMaterial({
      color: 0x111827,
      roughness: 0.4,
      metalness: 0.6,
    });

    const structuralMat = new THREE.MeshStandardMaterial({
      color: 0x475569,
      roughness: 0.5,
      metalness: 0.7,
    });

    const wheelMat = new THREE.MeshStandardMaterial({
      color: 0x1f2937,
      roughness: 0.65,
      metalness: 0.5,
    });

    const wheelHubMat = new THREE.MeshStandardMaterial({
      color: 0x94a3b8,
      roughness: 0.25,
      metalness: 0.9,
    });

    // 1. Avionics Chassis (Warm Electronics Box - WEB)
    const chassisGeom = new THREE.BoxGeometry(1.6, 0.45, 2.2);
    const chassis = new THREE.Mesh(chassisGeom, goldFoilMat);
    chassis.position.set(0, this.wheelRadius + 0.35, 0);
    chassis.castShadow = true;
    chassis.receiveShadow = true;
    group.add(chassis);

    // 2. Upper Equipment Deck & Solar / Battery Panels
    const deckGeom = new THREE.BoxGeometry(1.45, 0.08, 1.9);
    const deck = new THREE.Mesh(deckGeom, darkAvionicsMat);
    deck.position.set(0, 0.26, -0.05);
    chassis.add(deck);

    // Instrument sensor boxes on deck
    const ins1Geom = new THREE.BoxGeometry(0.35, 0.2, 0.4);
    const ins1 = new THREE.Mesh(ins1Geom, structuralMat);
    ins1.position.set(0.4, 0.14, 0.3);
    deck.add(ins1);

    const ins2Geom = new THREE.BoxGeometry(0.3, 0.18, 0.35);
    const ins2 = new THREE.Mesh(ins2Geom, structuralMat);
    ins2.position.set(-0.4, 0.13, 0.2);
    deck.add(ins2);

    // 3. Rear RTG (Multi-Mission Radioisotope Thermoelectric Generator)
    const rtgGeom = new THREE.CylinderGeometry(0.22, 0.24, 0.7, 16);
    rtgGeom.rotateX(Math.PI / 2);
    const rtg = new THREE.Mesh(rtgGeom, structuralMat);
    rtg.position.set(0, 0.15, -1.35);
    rtg.castShadow = true;
    chassis.add(rtg);

    // RTG cooling fins
    for (let f = 0; f < 8; f++) {
      const finGeom = new THREE.BoxGeometry(0.04, 0.35, 0.6);
      const fin = new THREE.Mesh(finGeom, structuralMat);
      fin.rotation.z = (f * Math.PI) / 4;
      rtg.add(fin);
    }

    // 4. Remote Sensing Mast (RSM) with Stereo Mastcam
    const mastColGeom = new THREE.CylinderGeometry(0.045, 0.055, 1.1, 12);
    const mastCol = new THREE.Mesh(mastColGeom, structuralMat);
    mastCol.position.set(0.42, 0.75, 0.75);
    mastCol.castShadow = true;
    chassis.add(mastCol);

    const mastHeadGeom = new THREE.BoxGeometry(0.38, 0.16, 0.24);
    const mastHead = new THREE.Mesh(mastHeadGeom, darkAvionicsMat);
    mastHead.position.set(0, 0.58, 0);
    mastHead.castShadow = true;
    mastCol.add(mastHead);

    // Stereo Mastcam lenses (dual cyan glass optics)
    const lensGeom = new THREE.CylinderGeometry(0.045, 0.045, 0.08, 16);
    lensGeom.rotateX(Math.PI / 2);
    const lensMat = new THREE.MeshStandardMaterial({
      color: 0x0284c7,
      emissive: 0x0284c7,
      emissiveIntensity: 0.5,
      roughness: 0.1,
      metalness: 0.9,
    });
    const lensL = new THREE.Mesh(lensGeom, lensMat);
    lensL.position.set(-0.1, 0, 0.13);
    const lensR = new THREE.Mesh(lensGeom, lensMat);
    lensR.position.set(0.1, 0, 0.13);
    mastHead.add(lensL);
    mastHead.add(lensR);

    // Laser calibration target aperture (SuperCam)
    const laserGeom = new THREE.CylinderGeometry(0.02, 0.02, 0.06, 12);
    laserGeom.rotateX(Math.PI / 2);
    const laserMat = new THREE.MeshBasicMaterial({ color: 0xef4444 });
    const laserAperture = new THREE.Mesh(laserGeom, laserMat);
    laserAperture.position.set(0, 0.05, 0.13);
    mastHead.add(laserAperture);

    // 5. High-Gain Parabolic UHF Dish Antenna
    const dishGeom = new THREE.CylinderGeometry(0.32, 0.08, 0.12, 24);
    dishGeom.rotateX(-Math.PI / 3);
    const dish = new THREE.Mesh(dishGeom, structuralMat);
    dish.position.set(-0.45, 0.35, -0.65);
    dish.castShadow = true;
    chassis.add(dish);

    // 6. Six Rocker-Bogie Aluminum Wheels with Cleats
    const wheelPositions = [
      [-1.05, this.wheelRadius, 0.95],   // Front Left
      [1.05, this.wheelRadius, 0.95],    // Front Right
      [-1.15, this.wheelRadius, 0.0],    // Mid Left
      [1.15, this.wheelRadius, 0.0],     // Mid Right
      [-1.05, this.wheelRadius, -0.95],  // Rear Left
      [1.05, this.wheelRadius, -0.95],   // Rear Right
    ];

    const wheelGeom = new THREE.CylinderGeometry(this.wheelRadius, this.wheelRadius, 0.26, 20);
    wheelGeom.rotateZ(Math.PI / 2);

    this.wheels = [];
    wheelPositions.forEach(([wx, wy, wz]) => {
      const wheelGroup = new THREE.Group();
      wheelGroup.position.set(wx, wy, wz);

      const wheelMesh = new THREE.Mesh(wheelGeom, wheelMat);
      wheelMesh.castShadow = true;
      wheelMesh.receiveShadow = true;
      wheelGroup.add(wheelMesh);

      // Hubcap
      const hubGeom = new THREE.CylinderGeometry(0.12, 0.12, 0.28, 16);
      hubGeom.rotateZ(Math.PI / 2);
      const hub = new THREE.Mesh(hubGeom, wheelHubMat);
      wheelGroup.add(hub);

      // Titanium suspension linkages
      const strutGeom = new THREE.CylinderGeometry(0.04, 0.04, 0.65);
      const strut = new THREE.Mesh(strutGeom, structuralMat);
      strut.position.set(wx > 0 ? -0.22 : 0.22, 0.25, 0);
      strut.rotation.z = wx > 0 ? -0.55 : 0.55;
      group.add(strut);

      group.add(wheelGroup);
      this.wheels.push(wheelMesh);
    });

    // 7. Tactical Headlight & Volumetric Forward SpotLight
    this.headlight = new THREE.SpotLight(0xfff5ea, 2.8, 28, Math.PI / 5, 0.45);
    this.headlight.position.set(0, this.wheelRadius + 0.55, 1.15);
    this.headlight.castShadow = true;
    this.headlight.shadow.mapSize.width = 1024;
    this.headlight.shadow.mapSize.height = 1024;

    this.headlightTarget = new THREE.Object3D();
    this.headlightTarget.position.set(0, 0, 10);
    group.add(this.headlight);
    group.add(this.headlightTarget);
    this.headlight.target = this.headlightTarget;

    this.proceduralGroup = group;
    this.root.add(group);
  }

  tryLoadGLTFModel(url) {
    const loader = new GLTFLoader();
    loader.load(
      url,
      (gltf) => {
        const model = gltf.scene;
        model.scale.set(1.5, 1.5, 1.5);
        model.traverse((child) => {
          if (child.isMesh) {
            child.castShadow = true;
            child.receiveShadow = true;
          }
        });
        if (this.proceduralGroup) {
          this.root.remove(this.proceduralGroup);
        }
        this.root.add(model);
        this.isCustomModel = true;
      },
      undefined,
      () => {
        // Fallback silently remains active
      }
    );
  }

  /**
   * Kinematic ground alignment: sets world position, 4-point footprint pitch/roll, and rotates wheels.
   */
  updateKinematics(rFloat, cFloat, headingAngle, dem, rows, cols, minElev, elevScale, deltaDist = 0) {
    const offsetX = (cols - 1) / 2;
    const offsetZ = (rows - 1) / 2;

    const worldX = cFloat - offsetX;
    const worldZ = rFloat - offsetZ;

    // 4-Point Footprint Sampling along heading vector
    const halfLen = 1.0;
    const halfWidth = 0.7;

    const cosH = Math.cos(headingAngle);
    const sinH = Math.sin(headingAngle);

    // Front / Rear (along heading)
    const rFront = rFloat + cosH * halfLen;
    const cFront = cFloat + sinH * halfLen;
    const rRear = rFloat - cosH * halfLen;
    const cRear = cFloat - sinH * halfLen;

    // Left / Right (perpendicular to heading)
    const rLeft = rFloat - sinH * halfWidth;
    const cLeft = cFloat + cosH * halfWidth;
    const rRight = rFloat + sinH * halfWidth;
    const cRight = cFloat - cosH * halfWidth;

    const eCenter = getInterpolatedElevation(dem, rFloat, cFloat);
    const eFront = getInterpolatedElevation(dem, rFront, cFront);
    const eRear = getInterpolatedElevation(dem, rRear, cRear);
    const eLeft = getInterpolatedElevation(dem, rLeft, cLeft);
    const eRight = getInterpolatedElevation(dem, rRight, cRight);

    // Calculate pitch and roll angles
    const pitch = Math.atan2((eFront - eRear) * elevScale, halfLen * 2.0);
    const roll = Math.atan2((eRight - eLeft) * elevScale, halfWidth * 2.0);

    const worldY = (eCenter - minElev) * elevScale;

    // Set position & rotations
    this.root.position.set(worldX, worldY, worldZ);
    this.root.rotation.set(0, 0, 0); // Reset
    this.root.rotation.y = headingAngle;
    this.root.rotation.x = pitch;
    this.root.rotation.z = -roll;

    // Rotate wheels proportionally to linear motion
    if (deltaDist !== 0 && this.wheels.length > 0) {
      const rotDelta = deltaDist / this.wheelRadius;
      this.wheels.forEach((w) => {
        w.rotation.x += rotDelta;
      });
    }

    return {
      worldX,
      worldY,
      worldZ,
      centerElev: eCenter,
      pitchDeg: THREE.MathUtils.radToDeg(pitch),
      rollDeg: THREE.MathUtils.radToDeg(roll),
    };
  }

  dispose() {
    this.root.traverse((obj) => {
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        if (Array.isArray(obj.material)) obj.material.forEach((m) => m.dispose());
        else obj.material.dispose();
      }
    });
  }
}
