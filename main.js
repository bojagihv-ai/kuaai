// State
const state = {
  files: [],
  prompts: ['', '', '', ''],
  outputDirHandle: null,
  isProcessing: false,
  queue: [],
  activeWorkers: 0,
  processedCount: 0,
  abortController: null,
  maxConcurrency: 4, // Nano Banana Pro limit
  results: [] // To store blobs for gallery if needed, though we save directly
};

// DOM Elements
const els = {
  dropArea: document.getElementById('drop-area'),
  fileInput: document.getElementById('file-input'),
  fileCount: document.getElementById('file-count'),
  prompts: [
    document.getElementById('prompt1'),
    document.getElementById('prompt2'),
    document.getElementById('prompt3'),
    document.getElementById('prompt4')
  ],
  selectDirBtn: document.getElementById('select-dir-btn'),
  dirStatus: document.getElementById('dir-status'),
  startBtn: document.getElementById('start-btn'),
  stopBtn: document.getElementById('stop-btn'),
  progressBar: document.getElementById('progress-bar'),
  statusMsg: document.getElementById('status-message'),
  gallery: document.getElementById('gallery')
};

// --- Initialization ---

function init() {
  // File Handling
  els.dropArea.addEventListener('click', () => els.fileInput.click());
  els.dropArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    els.dropArea.style.borderColor = 'var(--primary-color)';
  });
  els.dropArea.addEventListener('dragleave', () => {
    els.dropArea.style.borderColor = 'var(--border-color)';
  });
  els.dropArea.addEventListener('drop', handleDrop);
  els.fileInput.addEventListener('change', handleFileSelect);

  // Directory Selection
  els.selectDirBtn.addEventListener('click', selectDirectory);

  // Controls
  els.startBtn.addEventListener('click', startProcessing);
  els.stopBtn.addEventListener('click', stopProcessing);

  // Prompts
  els.prompts.forEach((input, idx) => {
    input.addEventListener('input', (e) => {
      state.prompts[idx] = e.target.value;
    });
  });
}

// --- File Management ---

function handleDrop(e) {
  e.preventDefault();
  els.dropArea.style.borderColor = 'var(--border-color)';
  const dt = e.dataTransfer;
  const files = [...dt.files].filter(f => f.type.startsWith('image/'));
  addFiles(files);
}

function handleFileSelect(e) {
  const files = [...e.target.files].filter(f => f.type.startsWith('image/'));
  addFiles(files);
  e.target.value = ''; // Reset to allow re-selection of same file
}

function addFiles(newFiles) {
  state.files = [...state.files, ...newFiles];
  updateUI();
}

function updateUI() {
  els.fileCount.textContent = state.files.length;
  
  const hasFiles = state.files.length > 0;
  const hasDir = !!state.outputDirHandle;
  const processing = state.isProcessing;

  els.startBtn.disabled = !hasFiles || !hasDir || processing;
  els.stopBtn.disabled = !processing;
  els.selectDirBtn.disabled = processing;
  
  if (!hasDir) {
    els.statusMsg.textContent = "저장 폴더를 선택해주세요.";
  } else if (!hasFiles) {
    els.statusMsg.textContent = "이미지를 추가해주세요.";
  } else if (!processing) {
    els.statusMsg.textContent = "준비됨";
  }
}

// --- Directory Handle ---

async function selectDirectory() {
  // Feature Check
  if (!('showDirectoryPicker' in window)) {
    alert("❌ 현재 브라우저는 '폴더 직접 저장' 기능을 지원하지 않습니다.\n\nPC 버전의 Chrome 또는 Edge 브라우저를 사용해주세요.\n(Firefox, Safari 및 모바일 브라우저는 보안 제한으로 인해 지원되지 않습니다.)");
    return;
  }

  try {
    state.outputDirHandle = await window.showDirectoryPicker();
    els.dirStatus.textContent = state.outputDirHandle.name;
    els.dirStatus.style.color = 'var(--success-color)';
    updateUI();
  } catch (err) {
    console.error('Directory selection cancelled or failed', err);
    if (err.name !== 'AbortError') {
      alert("폴더 선택 중 오류가 발생했습니다: " + err.message);
    }
  }
}

// --- Processing Logic ---

async function startProcessing() {
  if (state.isProcessing) return;
  state.isProcessing = true;
  state.processedCount = 0;
  state.queue = [...state.files]; // Clone array
  state.abortController = new AbortController();
  
  els.gallery.innerHTML = ''; // Clear gallery
  updateUI();
  els.statusMsg.textContent = "처리 중...";
  
  processQueue();
}

function stopProcessing() {
  if (!state.isProcessing) return;
  if (state.abortController) state.abortController.abort();
  state.isProcessing = false;
  state.queue = [];
  els.statusMsg.textContent = "중지됨";
  updateUI();
}

function processQueue() {
  if (!state.isProcessing) return;

  // Check if finished
  if (state.queue.length === 0 && state.activeWorkers === 0) {
    finishProcessing();
    return;
  }

  // Spawn workers up to limit
  while (state.activeWorkers < state.maxConcurrency && state.queue.length > 0) {
    const file = state.queue.shift();
    state.activeWorkers++;
    processImage(file).then(() => {
      state.activeWorkers--;
      // Update Progress
      state.processedCount++;
      const percent = (state.processedCount / state.files.length) * 100;
      els.progressBar.style.width = `${percent}%`;
      els.statusMsg.textContent = `처리 중: ${state.processedCount} / ${state.files.length}`;
      
      // Trigger next
      processQueue();
    }).catch(err => {
        console.error("Worker error:", err);
        state.activeWorkers--;
        processQueue();
    });
  }
}

function finishProcessing() {
  state.isProcessing = false;
  els.statusMsg.textContent = "완료!";
  els.progressBar.style.width = '100%';
  updateUI();
  alert("모든 작업이 완료되었습니다.");
}

// --- Mock Generation & Saving ---

async function processImage(file) {
  if (state.abortController.signal.aborted) return;

  // Simulate API latency (2-5s)
  const delay = Math.random() * 3000 + 2000;
  await new Promise(r => setTimeout(r, delay));

  if (state.abortController.signal.aborted) return;

  // Generate Image (Canvas)
  const blob = await generateMockImage(file);
  
  // Save to Disk
  const fileName = `NB_PRO_${Date.now()}_${Math.floor(Math.random()*1000)}.png`;
  await saveFileToDisk(blob, fileName);

  // Add to Gallery
  addToGallery(blob, fileName);
}

async function generateMockImage(file) {
  return new Promise((resolve) => {
    const canvas = document.createElement('canvas');
    canvas.width = 1600;
    canvas.height = 1600;
    const ctx = canvas.getContext('2d');

    // Load original image to draw it (simulating img2img)
    const img = new Image();
    img.onload = () => {
      // Background
      ctx.fillStyle = '#1e1e1e';
      ctx.fillRect(0, 0, 1600, 1600);

      // Draw Scaled Image in center
      const scale = Math.min(1400 / img.width, 1400 / img.height);
      const w = img.width * scale;
      const h = img.height * scale;
      ctx.drawImage(img, (1600 - w)/2, (1600 - h)/2, w, h);

      // Overlay "Processing" Effects
      ctx.fillStyle = 'rgba(251, 209, 75, 0.1)'; // Yellow tint
      ctx.fillRect(0, 0, 1600, 1600);
      
      // Text Details
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 60px Inter';
      ctx.textAlign = 'center';
      ctx.fillText('NANO BANANA PRO GENERATION', 800, 1500);
      
      ctx.font = '40px Inter';
      ctx.fillStyle = '#fbd14b';
      const promptText = state.prompts.filter(p => p).join(', ').substring(0, 50) + '...';
      ctx.fillText(promptText || 'No Prompts', 800, 1560);

      canvas.toBlob(resolve, 'image/png');
    };
    img.src = URL.createObjectURL(file);
  });
}

async function saveFileToDisk(blob, name) {
  if (!state.outputDirHandle) return;
  try {
    const fileHandle = await state.outputDirHandle.getFileHandle(name, { create: true });
    const writable = await fileHandle.createWritable();
    await writable.write(blob);
    await writable.close();
  } catch (err) {
    console.error("Save failed:", err);
  }
}

function addToGallery(blob, name) {
  const url = URL.createObjectURL(blob);
  const div = document.createElement('div');
  div.className = 'gallery-item';
  div.innerHTML = `
    <img src="${url}" alt="${name}">
    <div class="overlay">${name}</div>
  `;
  els.gallery.prepend(div);
}

// Start
init();