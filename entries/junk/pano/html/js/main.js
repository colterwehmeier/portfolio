import * as THREE from './three.module.js';

const panoramaContainer = document.getElementById('panorama');

const width = panoramaContainer.clientWidth;
const height = panoramaContainer.clientHeight;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
function loadPanorama(pano) {
  const renderer = new THREE.WebGLRenderer();
  renderer.setSize(width, height);
  panoramaContainer.appendChild(renderer.domElement);

  const geometry = new THREE.SphereGeometry(100, 100, 100);
  const loader = new THREE.TextureLoader();
  const texture = loader.load(pano, animate);
  const material = new THREE.MeshBasicMaterial({ map: texture, side: THREE.BackSide });
  const sphere = new THREE.Mesh(geometry, material);
  scene.add(sphere);

  function animate() {
    requestAnimationFrame(animate);
    renderer.render(scene, camera);
  }

  function onWindowResize() {
    const newWidth = panoramaContainer.clientWidth;
    const newHeight = panoramaContainer.clientHeight;

    camera.aspect = newWidth / newHeight;
    camera.updateProjectionMatrix();

    renderer.setSize(newWidth, newHeight);
  }

  window.addEventListener('resize', onWindowResize);
}

let isMouseDown = false;
let prevMouseX, prevMouseY;
let pitch = 0, yaw = 0;

function updateCameraRotation() {
  const quaternionPitch = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), pitch);
  const quaternionYaw = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), yaw);
  camera.quaternion.copy(quaternionYaw).multiply(quaternionPitch);
}

function handleMouseDown(event) {
  isMouseDown = true;
  prevMouseX = event.clientX;
  prevMouseY = event.clientY;
}

function handleMouseMove(event) {
  if (isMouseDown) {
    const deltaX = event.clientX - prevMouseX;
    const deltaY = event.clientY - prevMouseY;
    yaw += deltaX * 0.005;
    pitch = Math.min(Math.max(pitch + deltaY * 0.005, -Math.PI / 2), Math.PI / 2);
    updateCameraRotation();

    // Check if the mouse cursor is close to the edge of the screen.
    const edgeThreshold = 10;
    const isCloseToEdge =
      event.clientX <= edgeThreshold ||
      event.clientY <= edgeThreshold ||
      event.clientX >= window.innerWidth - edgeThreshold ||
      event.clientY >= window.innerHeight - edgeThreshold;

    if (isCloseToEdge) {
      // Reset the previous mouse coordinates.
      prevMouseX = event.clientX;
      prevMouseY = event.clientY;
    } else {
      prevMouseX = event.clientX;
      prevMouseY = event.clientY;
    }
  }
}

function handleMouseUp(event) {
  isMouseDown = false;
}

function handleTouchStart(event) {
  if (event.touches.length === 1) {
    prevMouseX = event.touches[0].clientX;
    prevMouseY = event.touches[0].clientY;
  }
}

function handleTouchMove(event) {
  if (event.touches.length === 1) {
    const deltaX = event.touches[0].clientX - prevMouseX;
    const deltaY = event.touches[0].clientY - prevMouseY;
    yaw += deltaX * 0.005;
    pitch = Math.min(Math.max(pitch + deltaY * 0.005, -Math.PI / 2), Math.PI / 2);
    updateCameraRotation();
    prevMouseX = event.touches[0].clientX;
    prevMouseY = event.touches[0].clientY;
  }
}

function handleTouchEnd(event) {}

function getCamera() {
  return camera;
}
function getScene() {
  return scene;
}

function init() {
  return {
    panoramaContainer,
    getCamera,
    getScene,
    loadPanorama,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handleTouchStart,
    handleTouchMove,
    handleTouchEnd,
  };
}

export { init };