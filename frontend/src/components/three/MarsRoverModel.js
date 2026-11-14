import * as THREE from 'three';
import { getInterpolatedElevation } from '../../utils/coordinateMapping';

/**
 * A.R.E.S. Rover Geometric Primitive Controller
 * Strict Brutalist Aerospace: Simple geometric primitive (cube + directional pyramid).
 * MeshBasicMaterial with flat monochrome off-white (#D4D4D4) and hairline wireframe outline.
 * Zero GLTF models, zero glossy reflections, zero shadows.
 */
export class MarsRoverController {
  constructor() {
    this.root = new THREE.Group();
    this.root.name = 'AresRoverPrimitive';
    this.wheelRadius = 0.35;
    this.buildBrutalistPrimitive();
  }

  buildBrutalistPrimitive() {
    // 1. Primary Rover Body: Sharp Rectangular Chassis Cube
    const bodyGeom = new THREE.BoxGeometry(1.5, 0.7, 2.0);
    const bodyMat = new THREE.MeshBasicMaterial({
      color: 0xd4d4d4,
      wireframe: false,
    });
    const bodyMesh = new THREE.Mesh(bodyGeom, bodyMat);
    bodyMesh.position.y = 0.45;
    this.root.add(bodyMesh);

    // Wireframe edge grid outline on body
    const edgeGeom = new THREE.EdgesGeometry(bodyGeom);
    const edgeMat = new THREE.LineBasicMaterial({ color: 0x121212, linewidth: 2 });
    const edgeLines = new THREE.LineSegments(edgeGeom, edgeMat);
    bodyMesh.add(edgeLines);

    // 2. Forward Heading Indicator: Sharp Geometric Pyramid
    // ConeGeometry with 4 sides is a four-sided pyramid pointing in the +Z direction
    const pyramidGeom = new THREE.ConeGeometry(0.5, 0.9, 4);
    pyramidGeom.rotateX(Math.PI / 2); // Orient apex forward along +Z heading
    const pyramidMat = new THREE.MeshBasicMaterial({
      color: 0x0284c7, // Nominal Sky Blue heading indicator
      wireframe: false,
    });
    const pyramidMesh = new THREE.Mesh(pyramidGeom, pyramidMat);
    pyramidMesh.position.set(0, 0.9, 0.7);
    this.root.add(pyramidMesh);

    // Outline on pyramid
    const pyrEdgeGeom = new THREE.EdgesGeometry(pyramidGeom);
    const pyrEdgeMat = new THREE.LineBasicMaterial({ color: 0x121212, linewidth: 1.5 });
    const pyrEdges = new THREE.LineSegments(pyrEdgeGeom, pyrEdgeMat);
    pyramidMesh.add(pyrEdges);

    // 3. Central Antenna Mast Primitive: Thin Vertical Cube
    const mastGeom = new THREE.BoxGeometry(0.12, 1.2, 0.12);
    const mastMat = new THREE.MeshBasicMaterial({ color: 0x333333 });
    const mastMesh = new THREE.Mesh(mastGeom, mastMat);
    mastMesh.position.set(0.45, 1.3, -0.4);
    this.root.add(mastMesh);
  }

  /**
   * Kinematic ground alignment: sets world position, 4-point footprint pitch/roll,
   * and smooth rotation updates.
   */
  updateKinematics(
    rFloat,
    cFloat,
    headingAngle,
    dem,
    rows,
    cols,
    minElev,
    elevScale,
    deltaDist = 0,
    dt = 0.016,
    smooth = false,
    steeringAngle = 0
  ) {
    const offsetX = (cols - 1) / 2;
    const offsetZ = (rows - 1) / 2;

    const worldX = cFloat - offsetX;
    const worldZ = rFloat - offsetZ;

    // 4-Point Footprint Sampling along heading vector
    const halfLen = 0.9;
    const halfWidth = 0.6;

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

    const targetY = (eCenter - minElev) * elevScale;

    if (smooth && dt > 0) {
      this.root.position.x = worldX;
      this.root.position.z = worldZ;
      this.root.position.y = THREE.MathUtils.damp(this.root.position.y, targetY, 14.0, dt);

      const targetEuler = new THREE.Euler(pitch, headingAngle, -roll, 'YXZ');
      const targetQuat = new THREE.Quaternion().setFromEuler(targetEuler);
      const dampingFactor = 1.0 - Math.exp(-12.0 * dt);
      this.root.quaternion.slerp(targetQuat, dampingFactor);
    } else {
      this.root.position.set(worldX, targetY, worldZ);
      this.root.rotation.set(0, 0, 0);
      this.root.rotation.y = headingAngle;
      this.root.rotation.x = pitch;
      this.root.rotation.z = -roll;
    }

    return {
      worldX,
      worldY: this.root.position.y,
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
