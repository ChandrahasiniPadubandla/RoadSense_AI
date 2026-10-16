import { useEffect, useMemo, useRef } from 'react';
import L from 'leaflet';
import { Marker } from 'react-leaflet';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const MODEL_PATHS = {
  car: '/models/car.glb',
  bike: '/models/motorcycle.glb',
  foot: '/models/walking-person.glb',
};

/** Renders a real GLB model inside a Leaflet marker and rotates it with GPS heading. */
export default function ThreeDTravelMarker({ position, mode = 'car', heading = 0 }) {
  const markerRef = useRef(null);
  const headingRef = useRef(heading);
  headingRef.current = heading;

  const icon = useMemo(() => L.divIcon({
    className: 'three-d-travel-marker',
    html: '<div class="three-d-travel-model"></div>',
    iconSize: [72, 72],
    iconAnchor: [36, 36],
  }), []);

  useEffect(() => {
    let disposed = false;
    let animationFrame = 0;
    let attachFrame = 0;
    let model = null;
    let mount = null;
    let renderer = null;

    const attachModel = () => {
      if (disposed) return;
      mount = markerRef.current?.getElement()?.querySelector('.three-d-travel-model');
      if (!mount) {
        attachFrame = window.requestAnimationFrame(attachModel);
        return;
      }

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
      camera.position.set(2.5, 2.7, 3.8);
      camera.lookAt(0, 0.25, 0);

      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.setSize(72, 72);
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.setClearColor(0x000000, 0);
      mount.replaceChildren(renderer.domElement);

      scene.add(new THREE.HemisphereLight(0xffffff, 0x526078, 2.2));
      const keyLight = new THREE.DirectionalLight(0xffffff, 2.4);
      keyLight.position.set(3, 5, 4);
      scene.add(keyLight);

      const modelGroup = new THREE.Group();
      scene.add(modelGroup);

      new GLTFLoader().load(
        MODEL_PATHS[mode] || MODEL_PATHS.car,
        (gltf) => {
          if (disposed) return;
          model = gltf.scene;
          const bounds = new THREE.Box3().setFromObject(model);
          const size = bounds.getSize(new THREE.Vector3());
          const center = bounds.getCenter(new THREE.Vector3());
          const largestDimension = Math.max(size.x, size.y, size.z) || 1;
          model.scale.setScalar(1.55 / largestDimension);
          model.position.set(
            (-center.x * 1.55) / largestDimension,
            (-center.y * 1.55) / largestDimension,
            (-center.z * 1.55) / largestDimension
          );
          modelGroup.add(model);
        },
        undefined,
        (error) => console.error(`Could not load the ${mode} 3D map model:`, error)
      );

      const render = () => {
        if (disposed) return;
        modelGroup.rotation.y = THREE.MathUtils.degToRad(headingRef.current || 0);
        renderer.render(scene, camera);
        animationFrame = window.requestAnimationFrame(render);
      };
      render();
    };
    attachModel();

    return () => {
      disposed = true;
      window.cancelAnimationFrame(attachFrame);
      window.cancelAnimationFrame(animationFrame);
      renderer?.dispose();
      mount?.replaceChildren();
      if (model) {
        model.traverse((object) => {
          object.geometry?.dispose?.();
          const materials = Array.isArray(object.material) ? object.material : [object.material];
          materials.forEach((material) => material?.dispose?.());
        });
      }
    };
  }, [mode]);

  return (
    <Marker
      ref={markerRef}
      position={position}
      icon={icon}
      zIndexOffset={1000}
      interactive={false}
    />
  );
}
