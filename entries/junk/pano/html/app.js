import {orientationControl} from './js/orientation.js';
import * as THREE from './js/three.module.js';

//building the rendering canvas
const panoramaContainer = document.getElementById('panorama');

//setting up the 3D scene
const width = panoramaContainer.clientWidth;
const height = panoramaContainer.clientHeight;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
const renderer = new THREE.WebGLRenderer();
const geometry = new THREE.SphereGeometry(100, 100, 100);

//pulling the site ID from the URL
function getURLParameter(name) {
  const regex = new RegExp('[?|&]' + name + '=' + '([^&;]+?)(&|#|;|$)');
  const matches = regex.exec(window.location.search);
  return matches ? decodeURIComponent(matches[1].replace(/\+/g, '%20')) : null;
}
let siteId = getURLParameter('id');

let material;
let sphere;
function loadPanorama(pano) {
  renderer.setSize(width, height);
  panoramaContainer.appendChild(renderer.domElement);

  const loader = new THREE.TextureLoader();
  const texture = loader.load(pano, () => {
    animate();
  });

  material = new THREE.MeshBasicMaterial({
    map: texture,
    opacity: 0, // Start with an opacity of 0 for the fade-in effect
    transparent: true,
    side: THREE.BackSide
  });
  sphere = new THREE.Mesh(geometry, material);

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

let deviceSupported = false;
let permissionsGranted = false;
let needToAskPermission = false;
let hasValidSiteID = false;

async function checkSupportAndPermissionNoRequest(){
  function isMobile() {
    const userAgent = navigator.userAgent || navigator.vendor || window.opera;
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
  }

  async function checkIOSPermissions() {
    console.log("checking for existing permissions setting")
    try {
      const deviceOrientationPermission = await navigator.permissions.query({ name: 'deviceorientation' });
      const deviceMotionPermission = await navigator.permissions.query({ name: 'devicemotion' });

      const deviceOrientationGranted = deviceOrientationPermission.state === 'granted';
      const deviceMotionGranted = deviceMotionPermission.state === 'granted';

      if (deviceOrientationGranted && deviceMotionGranted) {
        console.log('Both permissions are already granted');
        return true;
      } else {
        console.log('One or both permissions are not granted');
        return false;
      }
    } catch (error) {
      console.error('Error while checking permissions:', error);
      return false;
    }
  }

  console.log("checking if we're mobile: "+(isMobile == true));
  deviceSupported = isMobile() && (
    "DeviceOrientationEvent" in window && "DeviceMotionEvent" in window);

  if (deviceSupported) {
    console.log("Device is supported. Checking if we're iOS")
    if (
      typeof DeviceOrientationEvent.requestPermission === "function" &&
      typeof DeviceMotionEvent.requestPermission === "function"
    ) {
      needToAskPermission = true;

    } 
    else {
      permissionsGranted = true;
    }
  } else {
    console.log("device does not support tilt controls");
    permissionsGranted = false;
}}

async function AskPermission() {
  try {
        const deviceOrientationPermission = await DeviceOrientationEvent.requestPermission();
        const deviceMotionPermission = await DeviceMotionEvent.requestPermission();

        permissionsGranted =
          deviceOrientationPermission === "granted" &&
          deviceMotionPermission === "granted";
      } catch (error) {
        console.log("Error requesting permissions:", error);
        permissionsGranted = false;
      }
}

function subscribeToTouchInput() {
    // Set up touch/click-and-drag event listeners for the panorama viewer
    console.log("touch controls enabled")
    panoramaContainer.addEventListener('mousedown', handleMouseDown);
    panoramaContainer.addEventListener('mousemove', handleMouseMove);
    panoramaContainer.addEventListener('mouseup', handleMouseUp);

    panoramaContainer.addEventListener('touchstart', handleTouchStart);
    panoramaContainer.addEventListener('touchmove', handleTouchMove);
    panoramaContainer.addEventListener('touchend', handleTouchEnd);
}

function subscribeToDeviceMotionInput() {
  console.log(getCamera());
    const control = orientationControl(THREE, getCamera());

    function animate() {
      requestAnimationFrame(animate);

      control.update();
      renderer.render(getScene(), getCamera());
    }
    animate();
}

async function clickStartPanoramaCheckPermissions() {
  if ((!permissionsGranted && deviceSupported)) await AskPermission();
  console.log("Asked for Permissions: Result: "+(permissionsGranted == true))

  if (permissionsGranted) subscribeToDeviceMotionInput();
  else subscribeToTouchInput();

  // Remove the event listener once it's no longer needed
  panoramaContainer.removeEventListener('click', clickStartPanoramaCheckPermissions);
}

function createClickToBeginFadeHandler(audioDataList, duration,fadeoutGroup) {
  // Return the actual event handler function with the parameters in its closure
  return function clickHandler() {
    console.log("clicked. starting audio fadein");
    startStreamingFadeIn(audioDataList, duration);
    startTextureFadeIn(duration);
    animateFadeOut(fadeoutGroup, 0)
    
    panoramaContainer.removeEventListener('click', clickHandler);
  
  
  };
}

function LoadPanoramaFromURL(){
  
  function addPath(siteId, fileName) {
    return `./loc/${siteId}/${fileName}`;
  }
  
  console.log("getting ID from URL")
  if (siteId) {
    fetch(`./loc/${siteId}/manifest.json`)
      .then(response => response.json())
      .then(manifest => {
        
        const titleElement = document.getElementById('title');
          titleElement.textContent = manifest.title;

          const descriptionElement = document.getElementById('description');
          descriptionElement.textContent = manifest.desc;
          const footerText = document.getElementById('footer');
          footerText.textContent = "touch to enter";
 
          const fadeOutGroup = [
            {element: titleElement, duration: manifest.fadeIn},
            {element: descriptionElement, duration: manifest.fadeIn},
            {element: footerText, duration: 1}
          ];
          

        console.log("loading panorama")
        loadPanorama(addPath(siteId,manifest.pano));
        const audioFilesWithRootDir = manifest.sound.map(file => addPath(siteId, file));
        console.log("constructing audio Payload: "+audioFilesWithRootDir);
        
        const onClickHandler = createClickToBeginFadeHandler(audioFilesWithRootDir, parseFloat(manifest.fadeIn),fadeOutGroup);
        panoramaContainer.addEventListener('click', onClickHandler);
        // panoramaContainer.addEventListener('click', () => ClickToBeginFade(audioFilesWithRootDir, parseFloat(manifest.fadeIn)));
        hasValidSiteID = true;
      })
      .catch(error => {console.error('Error fetching manifest.json:', error);});
  } else {
    console.error('No site ID provided.');
  }
}
function animateFadeOut(fadeOutGroup, delay) {
  setTimeout(() => {
    fadeOutGroup.forEach(item => {
      const { element, duration } = item;

      // Add a transition to the element
      element.style.transition = `opacity ${duration}s ease-in-out`;

      // Set the opacity to 0 to start the fade-out animation
      element.style.opacity = 0;

      // Disable the element once the animation is complete
      setTimeout(() => {
        element.style.pointerEvents = 'none';
      }, duration * 1000);
    });
  }, delay * 1000);
}




let audioContext = null;

function createStreamingAudioElement(filePath, loop = true) {
  const audioElement = new Audio(filePath);
  audioElement.loop = loop;

  const mediaElementSource = audioContext.createMediaElementSource(audioElement);
  const gainNode = audioContext.createGain();
  mediaElementSource.connect(gainNode);
  gainNode.connect(audioContext.destination);

  return { audioElement, gainNode };
}

function startStreamingFadeIn(audioFiles, duration) {
  console.log("starting fade in of streamed audio");
  if (!audioContext) audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const audioDataList = audioFiles.map(file => createStreamingAudioElement(file));

  // Start playing the audio immediately, but with a volume of 0
  audioDataList.forEach(({ audioElement, gainNode }) => {
    gainNode.gain.value = 0;
    audioElement.play();
  });
  requestAnimationFrame(timestamp => fadeInAudioElements(timestamp, audioDataList, duration * 1000));

}

function fadeInAudioElements(timestamp, audioDataList, duration, startTime = null, lastProgress = 0) {
  if (startTime === null) {
    startTime = timestamp;
  }

  const elapsedTime = timestamp - startTime;
  const progress = Math.min(elapsedTime / duration, 1);

  // Update the volume for the audio
  const audioVolume = progress;
  audioDataList.forEach(({ gainNode }) => {
    gainNode.gain.value = audioVolume;
  });

  if (progress < 1) {
    requestAnimationFrame(newTimestamp => fadeInAudioElements(newTimestamp, audioDataList, duration, startTime, progress));
  }
}


function startTextureFadeIn(duration) {
  console.log("starting texture fade-in");
  requestAnimationFrame(timestamp => fadeInTexture(timestamp, duration * 1000));
}

function fadeInTexture(timestamp, duration, startTime = null, lastProgress = 0) {
  if (startTime === null) {
    startTime = timestamp;
  }

  const elapsedTime = timestamp - startTime;
  const progress = Math.min(elapsedTime / duration, 1);

  // Update the opacity for the texture
  const textureOpacity = progress;
  sphere.material.opacity = textureOpacity;

  if (progress < 1) {
    requestAnimationFrame(newTimestamp => fadeInTexture(newTimestamp, duration, startTime, progress));
  }
}

LoadPanoramaFromURL();

checkSupportAndPermissionNoRequest();

if(permissionsGranted) subscribeToDeviceMotionInput();
else if(needToAskPermission)panoramaContainer.addEventListener('click', clickStartPanoramaCheckPermissions);
else subscribeToTouchInput();