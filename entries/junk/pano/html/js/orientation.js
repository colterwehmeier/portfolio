var degreeToRadiansFactor = Math.PI / 180;
function degToRad(degrees) {
  return degrees * degreeToRadiansFactor;
}

function orientationControl(THREE,object) {

  object.rotation.reorder("YXZ");

  var enabled = false;
  var deviceOrientation = {};
  var screenOrientation = 0;

  var originalRotation;
  var setObjectQuaternion = createObjectQuaterionSetter(THREE);

  connect();

  return {
    update: update,
    connect: connect,
    disconnect: disconnect,
  };

  function connect() {
    deviceOrientation = {};
    originalRotation = object.quaternion.clone();

    onScreenOrientationChangeEvent(); // run once on load
    window.addEventListener('orientationchange', onScreenOrientationChangeEvent, false);
    window.addEventListener('deviceorientation', onDeviceOrientationChangeEvent, false);

    enabled = true;
  }

  function disconnect() {
    enabled = false;
    window.removeEventListener('orientationchange', onScreenOrientationChangeEvent, false);
    window.removeEventListener('deviceorientation', onDeviceOrientationChangeEvent, false);
  }

  function update() {
    if (!enabled) return;

    var alpha = deviceOrientation.alpha ? degToRad(deviceOrientation.alpha) : 0; // Z
    var beta = deviceOrientation.beta ? degToRad(deviceOrientation.beta) : 0; // X'
    var gamma = deviceOrientation.gamma ? degToRad(deviceOrientation.gamma) : 0; // Y''
    var orient = screenOrientation ? degToRad(screenOrientation) : 0; // O

    setObjectQuaternion(object.quaternion, alpha, beta, gamma, orient);
  }

  function onDeviceOrientationChangeEvent(event) {
    deviceOrientation = event;
  }

  function onScreenOrientationChangeEvent() {
    screenOrientation = window.orientation || 0;
  }

  function createObjectQuaterionSetter(THREE) {
    var deviceEuler = new THREE.Euler();
    var deviceQuaternion = new THREE.Quaternion();
    var screenTransform = new THREE.Quaternion();
    var worldTransform = new THREE.Quaternion(-Math.sqrt(0.5), 0, 0, Math.sqrt(0.5)); // - PI/2 around the x-axis
    var minusHalfAngle = 0;

    return function(quaternion, alpha, beta, gamma, orient) {
      quaternion.copy(originalRotation);
      deviceEuler.set(beta, alpha, -gamma, 'YXZ'); // 'ZXY' for the device, but 'YXZ' for us
      quaternion.multiply(deviceQuaternion.setFromEuler(deviceEuler)); // orient the device

      minusHalfAngle = -orient / 2;
      screenTransform.set( 0, Math.sin( minusHalfAngle ), 0, Math.cos( minusHalfAngle ) );

      quaternion.multiply(screenTransform); // adjust for screen orientation
      quaternion.multiply(worldTransform);  // camera looks out the back of the device, not the top
    };
  }
}

export {
  orientationControl
};
