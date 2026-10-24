import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js';
import { OrbitControls } from 'https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/loaders/GLTFLoader.js';

const canvas = document.querySelector('#scene');
const robotSelect = document.querySelector('#robot-select');
const playButton = document.querySelector('#play-button');
const timeSlider = document.querySelector('#time-slider');
const speedSelect = document.querySelector('#speed-select');
const currentTimeLabel = document.querySelector('#current-time');
const durationLabel = document.querySelector('#duration');
const statusText = document.querySelector('#status-text');
const statusDot = document.querySelector('#status-dot');
const sceneRobot = document.querySelector('#scene-robot');
const loading = document.querySelector('#loading');
const overlayDrawer = document.querySelector('#overlay-drawer');
const drawerToggle = document.querySelector('#drawer-toggle');
const overlayContent = document.querySelector('#overlay-content');
const axisToggle = document.querySelector('#axis-toggle');
const headingToggle = document.querySelector('#heading-toggle');
const depthValue = document.querySelector('#depth-value');
const depthGauge = document.querySelector('#depth-gauge');
const depthMaxLabel = document.querySelector('#depth-max-label');
const depthMinLabel = document.querySelector('#depth-min-label');
const depthZeroLine = document.querySelector('#depth-zero-line');
const depthFill = document.querySelector('#depth-fill');
const depthMarker = document.querySelector('#depth-marker');
const nearbyCount = document.querySelector('#nearby-count');
const nearbyNearest = document.querySelector('#nearby-nearest');
const nearbyAverage = document.querySelector('#nearby-average');
const nearbyList = document.querySelector('#nearby-list');

const scene = new THREE.Scene();
scene.fog = new THREE.Fog(0x151e1e, 500, 2500);

const camera = new THREE.PerspectiveCamera(43, 1, 0.1, 3000);
camera.position.set(0, 3.5, 8);

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.07;
controls.minDistance = 2.5;
controls.maxDistance = 1500;
controls.maxPolarAngle = Math.PI * 0.48;

scene.add(new THREE.HemisphereLight(0xdcebdc, 0x26322c, 2.1));
const keyLight = new THREE.DirectionalLight(0xffefcf, 3.0);
keyLight.position.set(-8, 14, 9);
scene.add(keyLight);
const fillLight = new THREE.DirectionalLight(0x7eb8a7, 1.2);
fillLight.position.set(9, 6, -10);
scene.add(fillLight);

const grid = new THREE.GridHelper(2000, 96, 0x9bd8f5, 0x6fa9c8);
grid.material.transparent = true;
grid.material.opacity = 0.55;
grid.material.color = new THREE.Color(0x9bd8f5);
scene.add(grid);

const robotRoot = new THREE.Group();
scene.add(robotRoot);
const modelRoot = new THREE.Group();
robotRoot.add(modelRoot);
const robotMarker = new THREE.Mesh(
  new THREE.SphereGeometry(0.12, 16, 12),
  new THREE.MeshBasicMaterial({ color: 0xa7e56f }),
);
robotMarker.visible = false;
robotRoot.add(robotMarker);
const robotAxes = new THREE.AxesHelper(1.25);
robotRoot.add(robotAxes);
robotAxes.visible = axisToggle.checked;
const headingArrow = new THREE.ArrowHelper(
  new THREE.Vector3(0, 0, -1),
  new THREE.Vector3(),
  2.1,
  0xff7a30,
  0.48,
  0.28,
);
robotRoot.add(headingArrow);
headingArrow.visible = headingToggle.checked;

const robotColors = [0xa7e56f, 0xe9b35f, 0x69c6c3];
const trajectories = new Map();
const nearbyRobots = new Map();
let replayData;
let activeSamples = [];
let duration = 0;
let currentTime = 0;
let playing = false;
let playbackTimer = null;
let lastPlaybackTimestamp = 0;
let cameraHasStarted = false;
let previousRobotPosition = new THREE.Vector3();
let orientationBasis;
let depthRange = { min: -0.5, max: 0.5 };

const basisMatrix = new THREE.Matrix4().set(
  0, 1, 0, 0,
  0, 0, -1, 0,
  -1, 0, 0, 0,
  0, 0, 0, 1,
);
orientationBasis = new THREE.Quaternion().setFromRotationMatrix(basisMatrix);
const inverseBasis = orientationBasis.clone().invert();

function setStatus(message, state = 'ready') {
  statusText.textContent = message;
  statusDot.className = `status-dot ${state}`;
}

function setPlaying(nextPlaying) {
  playing = nextPlaying;
  playButton.classList.toggle('playing', playing);
  playButton.setAttribute('aria-label', playing ? 'Pause' : 'Play');
  if (playing) {
    lastPlaybackTimestamp = performance.now();
    playbackTimer = window.setInterval(advancePlayback, 50);
  } else if (playbackTimer !== null) {
    window.clearInterval(playbackTimer);
    playbackTimer = null;
  }
}

function formatTime(seconds) {
  return `${seconds.toFixed(1)} s`;
}

function configureDepthRange() {
  const initialUp = activeSamples[0][2];
  let rawMin = 0;
  let rawMax = 0;
  activeSamples.forEach((sample) => {
    const depth = initialUp - sample[2];
    rawMin = Math.min(rawMin, depth);
    rawMax = Math.max(rawMax, depth);
  });
  const padding = Math.max(0.5, (rawMax - rawMin) * 0.05);
  depthRange = {
    min: Math.floor((rawMin - padding) * 10) / 10,
    max: Math.ceil((rawMax + padding) * 10) / 10,
  };
  depthMaxLabel.textContent = depthRange.max.toFixed(1);
  depthMinLabel.textContent = depthRange.min.toFixed(1);
  depthGauge.setAttribute('aria-valuemin', depthRange.min.toFixed(1));
  depthGauge.setAttribute('aria-valuemax', depthRange.max.toFixed(1));
}

function updateDepthMeter(up) {
  const depth = activeSamples[0][2] - up;
  const roundedDepth = Math.abs(depth) < 0.05 ? 0 : depth;
  const range = depthRange.max - depthRange.min;
  const position = THREE.MathUtils.clamp((depth - depthRange.min) / range, 0, 1) * 100;
  const zeroPosition = THREE.MathUtils.clamp((0 - depthRange.min) / range, 0, 1) * 100;
  const fillLeft = Math.min(position, zeroPosition);
  const fillWidth = Math.abs(position - zeroPosition);

  depthValue.textContent = `${roundedDepth.toFixed(1)} m`;
  depthGauge.setAttribute('aria-valuenow', roundedDepth.toFixed(1));
  depthGauge.setAttribute('aria-valuetext', `${roundedDepth.toFixed(1)} meters`);
  depthZeroLine.style.left = `${zeroPosition}%`;
  depthFill.style.left = `${fillLeft}%`;
  depthFill.style.width = `${fillWidth}%`;
  depthMarker.style.left = `${position}%`;
}

function createTintedModel(model, color) {
  const tintedModel = model.clone(true);
  const tint = new THREE.Color(color);
  tintedModel.traverse((object) => {
    if (!object.isMesh) return;
    const tintMaterial = (material) => {
      const clone = material.clone();
      if (clone.color) clone.color.lerp(tint, 0.35);
      return clone;
    };
    object.material = Array.isArray(object.material)
      ? object.material.map(tintMaterial)
      : tintMaterial(object.material);
  });
  return tintedModel;
}

function setModel(gltf) {
  modelRoot.clear();
  const model = gltf.scene;
  const bounds = new THREE.Box3().setFromObject(model);
  const dimensions = bounds.getSize(new THREE.Vector3());
  const largestDimension = Math.max(dimensions.x, dimensions.y, dimensions.z);
  if (largestDimension > 0) model.scale.setScalar(2.8 / largestDimension);
  bounds.setFromObject(model);
  model.position.copy(bounds.getCenter(new THREE.Vector3()).multiplyScalar(-1));
  modelRoot.add(model);
  nearbyRobots.forEach(({ group, color }) => {
    group.add(createTintedModel(model, color));
  });
  robotMarker.visible = false;
  loading.classList.add('hidden');
}

function drawTrajectories() {
  for (const { line } of trajectories.values()) {
    scene.remove(line);
    line.geometry.dispose();
    line.material.dispose();
  }
  trajectories.clear();
  nearbyRobots.forEach(({ group }) => {
    scene.remove(group);
  });
  nearbyRobots.clear();

  Object.entries(replayData.robots).forEach(([name, samples], index) => {
    const vertices = new Float32Array(samples.length * 3);
    samples.forEach((sample, sampleIndex) => {
      const offset = sampleIndex * 3;
      vertices[offset] = sample[1];
      vertices[offset + 1] = sample[2];
      vertices[offset + 2] = -sample[3];
    });
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
    const color = robotColors[index % robotColors.length];
    const line = new THREE.Line(
      geometry,
      new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.72 }),
    );
    scene.add(line);
    trajectories.set(name, { line, color });
    if (name !== robotSelect.value) {
      const group = new THREE.Group();
      const marker = new THREE.Mesh(
        new THREE.SphereGeometry(0.2, 16, 12),
        new THREE.MeshBasicMaterial({ color }),
      );
      group.add(marker);
      group.visible = false;
      scene.add(group);
      nearbyRobots.set(name, { group, color });
    }
  });
}

function findSamplePair(samples, time) {
  let low = 0;
  let high = samples.length - 1;
  while (low + 1 < high) {
    const middle = (low + high) >> 1;
    if (samples[middle][0] <= time) low = middle;
    else high = middle;
  }
  return [samples[low], samples[high]];
}

const sourceQuaternion = new THREE.Quaternion();
const mappedQuaternion = new THREE.Quaternion();
const otherSourceQuaternion = new THREE.Quaternion();
const otherMappedQuaternion = new THREE.Quaternion();
const previousPosition = new THREE.Vector3();
const otherRobotPosition = new THREE.Vector3();
const followOffset = new THREE.Vector3();

function renderNearbyRobots() {
  const visibleRovers = [];
  nearbyRobots.forEach(({ group }, name) => {
    if (name === robotSelect.value) {
      group.visible = false;
      return;
    }
    const samples = replayData.robots[name];
    const first = samples[0];
    const last = samples[samples.length - 1];
    if (currentTime < first[0] || currentTime > last[0]) {
      group.visible = false;
      return;
    }

    const [before, after] = findSamplePair(samples, currentTime);
    const span = after[0] - before[0];
    const blend = span > 0 ? THREE.MathUtils.clamp((currentTime - before[0]) / span, 0, 1) : 0;
    otherRobotPosition.set(
      THREE.MathUtils.lerp(before[1], after[1], blend),
      THREE.MathUtils.lerp(before[2], after[2], blend),
      -THREE.MathUtils.lerp(before[3], after[3], blend),
    );
    const distance = otherRobotPosition.distanceTo(robotRoot.position);
    if (distance > 1000) {
      group.visible = false;
      return;
    }

    const beforeQuaternion = new THREE.Quaternion(before[4], before[5], before[6], before[7]);
    const afterQuaternion = new THREE.Quaternion(after[4], after[5], after[6], after[7]);
    otherSourceQuaternion.slerpQuaternions(beforeQuaternion, afterQuaternion, blend).normalize();
    otherMappedQuaternion.copy(orientationBasis).multiply(otherSourceQuaternion).multiply(inverseBasis);
    group.position.copy(otherRobotPosition);
    group.quaternion.copy(otherMappedQuaternion);
    group.visible = true;
    visibleRovers.push({ name, distance, color: nearbyRobots.get(name).color });
  });

  visibleRovers.sort((left, right) => left.distance - right.distance);
  nearbyCount.textContent = String(visibleRovers.length);
  nearbyNearest.textContent = visibleRovers.length ? `${visibleRovers[0].distance.toFixed(1)} m` : '—';
  const averageDistance = visibleRovers.reduce((sum, rover) => sum + rover.distance, 0)
    / (visibleRovers.length || 1);
  nearbyAverage.textContent = visibleRovers.length ? `${averageDistance.toFixed(1)} m` : '—';
  nearbyList.replaceChildren();
  visibleRovers.forEach(({ name, distance, color }) => {
    const row = document.createElement('li');
    row.className = 'nearby-row';
    const label = document.createElement('span');
    label.className = 'nearby-name';
    const swatch = document.createElement('i');
    swatch.className = 'nearby-swatch';
    swatch.style.backgroundColor = `#${color.toString(16).padStart(6, '0')}`;
    const nameLabel = document.createElement('span');
    nameLabel.textContent = name;
    const distanceLabel = document.createElement('span');
    distanceLabel.textContent = `${distance.toFixed(1)} m`;
    label.append(swatch, nameLabel);
    row.append(label, distanceLabel);
    nearbyList.append(row);
  });
}

function updatePose(time, translateCamera = false) {
  if (activeSamples.length === 0) return;
  const [before, after] = findSamplePair(activeSamples, time);
  const span = after[0] - before[0];
  const blend = span > 0 ? THREE.MathUtils.clamp((time - before[0]) / span, 0, 1) : 0;
  previousPosition.copy(robotRoot.position);
  robotRoot.position.set(
    THREE.MathUtils.lerp(before[1], after[1], blend),
    THREE.MathUtils.lerp(before[2], after[2], blend),
    -THREE.MathUtils.lerp(before[3], after[3], blend),
  );

  const beforeQuaternion = new THREE.Quaternion(before[4], before[5], before[6], before[7]);
  const afterQuaternion = new THREE.Quaternion(after[4], after[5], after[6], after[7]);
  sourceQuaternion.slerpQuaternions(beforeQuaternion, afterQuaternion, blend).normalize();
  mappedQuaternion.copy(orientationBasis).multiply(sourceQuaternion).multiply(inverseBasis);
  robotRoot.quaternion.copy(mappedQuaternion);
  updateDepthMeter(robotRoot.position.y);
  renderNearbyRobots();

  const movement = robotRoot.position.clone().sub(previousPosition);
  if (cameraHasStarted && translateCamera) {
    camera.position.add(movement);
    controls.target.add(movement);
  } else if (!cameraHasStarted) {
    controls.target.copy(robotRoot.position);
    followOffset.set(0, 3.2, 7.5).applyQuaternion(robotRoot.quaternion);
    camera.position.copy(robotRoot.position).add(followOffset);
    controls.update();
    cameraHasStarted = true;
  }
  previousRobotPosition.copy(robotRoot.position);
}

function selectRobot(name) {
  const requestedTime = currentTime;
  activeSamples = replayData.robots[name];
  const { color } = trajectories.get(name);
  configureDepthRange();
  const earliestTime = activeSamples[0][0];
  duration = activeSamples[activeSamples.length - 1][0];
  currentTime = THREE.MathUtils.clamp(requestedTime, earliestTime, duration);
  timeSlider.min = String(earliestTime);
  timeSlider.max = String(duration);
  timeSlider.value = String(currentTime);
  currentTimeLabel.textContent = formatTime(currentTime);
  durationLabel.textContent = formatTime(duration);
  sceneRobot.textContent = name;
  durationLabel.style.color = `#${color.toString(16).padStart(6, '0')}`;
  setPlaying(false);
  cameraHasStarted = false;
  updatePose(currentTime);
  setStatus(`${name} loaded`);
}

function resizeRenderer() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  if (!width || !height) return;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

function advancePlayback() {
  const now = performance.now();
  const delta = Math.max(0, (now - lastPlaybackTimestamp) / 1000);
  lastPlaybackTimestamp = now;
  currentTime += delta * Number(speedSelect.value);
  if (currentTime >= duration) {
    currentTime = duration;
    setPlaying(false);
  }
  timeSlider.value = String(currentTime);
  currentTimeLabel.textContent = formatTime(currentTime);
  updatePose(currentTime, true);
}

function animate(now) {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}

async function initialize() {
  try {
    const response = await fetch('/api/robot-trajectories');
    if (!response.ok) throw new Error(`Trajectory request failed (${response.status})`);
    replayData = await response.json();
    drawTrajectories();

    Object.keys(replayData.robots).forEach((name) => {
      const option = document.createElement('option');
      option.value = name;
      option.textContent = name;
      robotSelect.append(option);
    });
    robotSelect.disabled = false;

    const loader = new GLTFLoader();
    loader.load(
      '/robot-model/scene.gltf',
      (gltf) => {
        setModel(gltf);
        playButton.disabled = false;
        timeSlider.disabled = false;
        selectRobot(robotSelect.value || Object.keys(replayData.robots)[0]);
      },
      undefined,
      (error) => {
        console.error(error);
        loading.textContent = 'Could not load the AUV model';
        robotMarker.visible = true;
        playButton.disabled = false;
        timeSlider.disabled = false;
        selectRobot(robotSelect.value || Object.keys(replayData.robots)[0]);
        setStatus('Model unavailable; showing position marker', 'error');
      },
    );
  } catch (error) {
    console.error(error);
    loading.textContent = 'Could not load trajectory data';
    setStatus('Trajectory unavailable', 'error');
  }
}

robotSelect.addEventListener('change', () => {
  selectRobot(robotSelect.value);
});
drawerToggle.addEventListener('click', () => {
  const isOpen = overlayDrawer.classList.toggle('open');
  drawerToggle.setAttribute('aria-expanded', String(isOpen));
  drawerToggle.setAttribute('aria-label', isOpen ? 'Close overlay panel' : 'Open overlay panel');
  overlayContent.inert = !isOpen;
});
window.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && overlayDrawer.classList.contains('open')) {
    overlayDrawer.classList.remove('open');
    drawerToggle.setAttribute('aria-expanded', 'false');
    drawerToggle.setAttribute('aria-label', 'Open overlay panel');
    overlayContent.inert = true;
    drawerToggle.focus();
  }
});
axisToggle.addEventListener('change', () => {
  robotAxes.visible = axisToggle.checked;
});
headingToggle.addEventListener('change', () => {
  headingArrow.visible = headingToggle.checked;
});
playButton.addEventListener('click', () => {
  if (currentTime >= duration) {
    currentTime = activeSamples[0][0];
    updatePose(currentTime, true);
  }
  setPlaying(!playing);
});
timeSlider.addEventListener('input', () => {
  currentTime = Number(timeSlider.value);
  currentTimeLabel.textContent = formatTime(currentTime);
  updatePose(currentTime, true);
});
window.addEventListener('keydown', (event) => {
  if (event.code === 'Space' && !['INPUT', 'SELECT', 'BUTTON'].includes(document.activeElement?.tagName)) {
    event.preventDefault();
    if (!playButton.disabled) playButton.click();
  }
});
window.addEventListener('resize', resizeRenderer);
new ResizeObserver(resizeRenderer).observe(canvas.parentElement);

resizeRenderer();
initialize();
requestAnimationFrame(animate);