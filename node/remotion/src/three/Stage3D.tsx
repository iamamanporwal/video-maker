import { noise2D } from "@remotion/noise";
import { ThreeCanvas } from "@remotion/three";
import { useThree } from "@react-three/fiber";
import React, { useEffect, useLayoutEffect, useMemo, useState } from "react";
import { cancelRender, continueRender, delayRender, useCurrentFrame } from "remotion";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { RGBELoader } from "three/examples/jsm/loaders/RGBELoader.js";
import { C } from "../generated/brand";
import { hash, multiKeys } from "../lib/anim";

// NOTE: no useFrame anywhere - everything is driven by useCurrentFrame().

const glbCache = new Map<string, Promise<THREE.Group>>();

const loadGLB = (url: string) => {
  if (!glbCache.has(url)) {
    glbCache.set(
      url,
      new Promise((res, rej) => new GLTFLoader().load(url, (g) => res(g.scene), undefined, (e) => rej(e))),
    );
  }
  return glbCache.get(url)!;
};

export const useGLB = (url: string) => {
  const [handle] = useState(() => delayRender(`glb ${url}`, { timeoutInMilliseconds: 240000 }));
  const [scene, setScene] = useState<THREE.Group | null>(null);
  useEffect(() => {
    loadGLB(url)
      .then((s) => {
        setScene(s);
        continueRender(handle);
      })
      .catch((e) => cancelRender(e));
  }, [url, handle]);
  return scene;
};

const HDR: React.FC<{ url: string; intensity?: number }> = ({ url, intensity = 1 }) => {
  const { scene, gl } = useThree();
  const [handle] = useState(() => delayRender(`hdr ${url}`, { timeoutInMilliseconds: 120000 }));
  useEffect(() => {
    new RGBELoader().load(
      url,
      (tex) => {
        const pm = new THREE.PMREMGenerator(gl);
        scene.environment = pm.fromEquirectangular(tex).texture;
        (scene as any).environmentIntensity = intensity;
        tex.dispose();
        pm.dispose();
        continueRender(handle);
      },
      undefined,
      (e) => cancelRender(e),
    );
  }, [url, scene, gl, handle, intensity]);
  return null;
};

export type CarProps = {
  url: string;
  /** 0..1 progress of the feature-edge scan (solid revealed behind the scan front). */
  scan?: number;
  baseColorFactor?: number;
  rotateX?: number;
  position?: [number, number, number];
  rotation?: [number, number, number];
  edgeColor?: string;
};

/** The real GLB: node transform baked, centred, uniformly scaled to length 1. Own PBR maps kept. */
export const Car: React.FC<CarProps> = ({ url, scan = 1, baseColorFactor, rotateX = 0, position = [0, 0, 0], rotation = [0, 0, 0], edgeColor = C.accent }) => {
  const src = useGLB(url);
  const planes = useMemo(() => ({ solid: new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0), edge: new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0) }), []);
  const built = useMemo(() => {
    if (!src) return null;
    const root = src.clone(true);
    root.rotation.x = rotateX;
    root.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(root);
    const size = box.getSize(new THREE.Vector3());
    const centre = box.getCenter(new THREE.Vector3());
    const s = 1 / Math.max(size.x, size.y, size.z);
    const wrap = new THREE.Group();
    wrap.add(root);
    root.position.sub(centre);
    wrap.scale.setScalar(s);
    root.traverse((o: any) => {
      if (!o.isMesh) return;
      // Some generators (e.g. trimesh exports) ship no normals; lit materials then render black.
      if (!o.geometry.attributes.normal) o.geometry.computeVertexNormals();
      const old = o.material as THREE.MeshStandardMaterial;
      const mat = new THREE.MeshPhysicalMaterial({
        map: old.map ?? null,
        normalMap: old.normalMap ?? null,
        roughnessMap: old.roughnessMap ?? null,
        metalnessMap: old.metalnessMap ?? null,
        aoMap: old.aoMap ?? null,
        color: old.color ? old.color.clone() : new THREE.Color("#888"),
        roughness: old.roughness ?? 0.5,
        metalness: old.metalness ?? 0.2,
        clearcoat: 1,
        clearcoatRoughness: 0.08,
        clippingPlanes: [planes.solid],
      });
      if (baseColorFactor !== undefined) mat.color.multiplyScalar(baseColorFactor);
      o.material = mat;
      // Feature edges, not a triangle wireframe (which becomes a white blob on dense meshes).
      const edges = new THREE.LineSegments(
        new THREE.EdgesGeometry(o.geometry, 32),
        new THREE.LineBasicMaterial({ color: edgeColor, transparent: true, opacity: 0.9, clippingPlanes: [planes.edge] }),
      );
      o.add(edges);
    });
    return wrap;
  }, [src, planes, baseColorFactor, rotateX, edgeColor]);
  // Scan along x from -0.6 to 0.6 (normalised length 1).
  const front = -0.6 + 1.2 * scan;
  planes.solid.constant = front;
  planes.edge.constant = scan >= 1 ? 10 : front + 0.18;
  if (!built) return null;
  return <primitive object={built} position={position} rotation={rotation} />;
};

const coneVert = `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`;
const coneFrag = `uniform vec3 uCore; uniform vec3 uEdge; uniform float uPower; varying vec2 vUv;
void main(){ float a = pow(1.0 - vUv.y, 1.6) * uPower; vec3 c = mix(uEdge, uCore, 1.0 - vUv.y); gl_FragColor = vec4(c * a, a); }`;

/** Deterministic thrusters: gradient cone shader + point light, flicker from seeded noise. */
export const Thrusters: React.FC<{ anchors: [number, number, number][]; power: number; seed?: string }> = ({ anchors, power, seed = "thr" }) => {
  const frame = useCurrentFrame();
  return (
    <group>
      {anchors.map((a, i) => {
        const fl = 0.85 + 0.15 * noise2D(seed + i, frame * 0.35, i);
        const len = 0.22 * power * fl;
        return (
          <group key={i} position={a}>
            <mesh position={[0, -len / 2, 0]} rotation={[Math.PI, 0, 0]}>
              <coneGeometry args={[0.045 * Math.max(0.2, power), len || 0.001, 24, 1, true]} />
              <shaderMaterial
                transparent
                depthWrite={false}
                blending={THREE.AdditiveBlending}
                side={THREE.DoubleSide}
                vertexShader={coneVert}
                fragmentShader={coneFrag}
                uniforms={{ uCore: { value: new THREE.Color("#ffffff") }, uEdge: { value: new THREE.Color(C.accent) }, uPower: { value: power * fl } }}
              />
            </mesh>
            <pointLight color={C.accent} intensity={2.5 * power * fl} distance={0.8} />
          </group>
        );
      })}
    </group>
  );
};

/** Rings of sketch line the camera flies through. Seeded wobble. */
export const SketchTunnel: React.FC<{ rings?: number; spacing?: number; radius?: number; opacity?: number }> = ({ rings = 18, spacing = 0.6, radius = 1.2, opacity = 1 }) => {
  const geos = useMemo(
    () =>
      Array.from({ length: rings }, (_, r) => {
        const pts: THREE.Vector3[] = [];
        for (let i = 0; i <= 64; i++) {
          const a = (i / 64) * Math.PI * 2;
          const w = 1 + 0.05 * Math.sin(a * 3 + hash(r) * 6) + 0.03 * Math.sin(a * 7 + hash(r + 9) * 6);
          pts.push(new THREE.Vector3(Math.cos(a) * radius * w, Math.sin(a) * radius * w * 0.7, -r * spacing));
        }
        return new THREE.BufferGeometry().setFromPoints(pts);
      }),
    [rings, spacing, radius],
  );
  return (
    <group>
      {geos.map((g, i) => (
        <primitive key={i} object={new THREE.Line(g, new THREE.LineBasicMaterial({ color: C.accent, transparent: true, opacity: opacity * (1 - i / rings) }))} />
      ))}
    </group>
  );
};

/** Camera rig from keys [[f, x, y, z, lx, ly, lz, fov], ...]. */
const CamRig: React.FC<{ keys: number[][]; aspect: number }> = ({ keys, aspect }) => {
  const frame = useCurrentFrame();
  const { camera } = useThree();
  // fov keys are authored for 16:9; widen the vertical fov for taller frames so the subject still fits.
  const widen = Math.pow(Math.max(1, 16 / 9 / aspect), 0.75);
  const fn = useMemo(() => multiKeys(keys), [keys]);
  useLayoutEffect(() => {
    const [x, y, z, lx, ly, lz, fov] = fn(frame);
    camera.position.set(x, y, z);
    camera.lookAt(lx, ly, lz);
    const pc = camera as THREE.PerspectiveCamera;
    const vfov = fov ? (2 * Math.atan(Math.tan((fov * Math.PI) / 360) * widen) * 180) / Math.PI : pc.fov;
    if (pc.fov !== vfov) {
      pc.fov = vfov;
      pc.updateProjectionMatrix();
    }
  }, [frame, fn, camera, widen]);
  return null;
};

const Floor: React.FC = () => (
  <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.32, 0]}>
    <planeGeometry args={[40, 40]} />
    <meshStandardMaterial color="#0e0f0e" roughness={0.6} metalness={0.2} dithering />
  </mesh>
);

export type StageProps = {
  width: number;
  height: number;
  glb: string;
  hdri?: string;
  scan?: number;
  camKeys?: number[][];
  carKeys?: number[][]; // [[f, y, rotY, tilt]]
  thrustKeys?: number[][]; // [[f, power]]
  anchors?: [number, number, number][];
  tunnel?: boolean;
  baseColorFactor?: number;
  rotateX?: number;
  frameOffset?: number;
};

export const Stage3D: React.FC<StageProps> = ({ width, height, glb, hdri, scan = 1, camKeys, carKeys, thrustKeys, anchors, tunnel, baseColorFactor, rotateX }) => {
  const frame = useCurrentFrame();
  const car = useMemo(() => multiKeys(carKeys ?? [[0, 0, 0, 0]]), [carKeys]);
  const thrust = useMemo(() => multiKeys(thrustKeys ?? [[0, 0]]), [thrustKeys]);
  const [y, rotY, tilt] = car(frame);
  const [power] = thrust(frame);
  const cams = camKeys ?? [
    [0, 1.1, 0.35, 1.1, 0, 0, 0, 30],
    [240, 1.3, 0.3, -0.6, 0, 0, 0, 30],
  ];
  return (
    <ThreeCanvas
      width={Math.round(width)}
      height={Math.round(height)}
      gl={{ antialias: true, preserveDrawingBuffer: true }}
      onCreated={({ gl }) => {
        gl.localClippingEnabled = true;
        gl.toneMapping = THREE.ACESFilmicToneMapping;
      }}
      camera={{ fov: 30, near: 0.01, far: 100, position: [1.1, 0.35, 1.1] }}
    >
      <color attach="background" args={[C.ink]} />
      <fog attach="fog" args={[C.ink, 2.5, 9]} />
      <CamRig keys={cams} aspect={width / height} />
      {hdri ? <HDR url={hdri} intensity={0.9} /> : null}
      <hemisphereLight args={["#cfd8dc", "#0b0b0c", hdri ? 0.25 : 0.9]} />
      <directionalLight position={[2, 3, 2]} intensity={hdri ? 0.8 : 2.2} />
      <directionalLight position={[-2, 1.5, -1]} intensity={0.6} color={C.accent} />
      <Floor />
      {tunnel ? <SketchTunnel /> : null}
      <group position={[0, y ?? 0, 0]} rotation={[tilt ?? 0, rotY ?? 0, 0]}>
        <Car url={glb} scan={scan} baseColorFactor={baseColorFactor} rotateX={rotateX} />
        {anchors && power > 0.01 ? <Thrusters anchors={anchors} power={power} /> : null}
      </group>
    </ThreeCanvas>
  );
};
