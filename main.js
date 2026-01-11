// State Management
const state = {
  files: [],
  prompts: ['', '', '', ''],
  outputDirHandle: null,
  isProcessing: false,
  queue: [],
  activeWorkers: 0,
  processedCount: 0,
  abortController: null,
  maxConcurrency: 4, 
  apiKey: localStorage.getItem('gemini_api_key') || ''
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
  apiKeyInput: document.getElementById('api-key'),
  saveKeyBtn: document.getElementById('save-key-btn'),
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
  if (state.apiKey) els.apiKeyInput.value = state.apiKey;

  els.saveKeyBtn.addEventListener('click', () => {
    state.apiKey = els.apiKeyInput.value.trim();
    localStorage.setItem('gemini_api_key', state.apiKey);
    alert('API Key가 브라우저에 저장되었습니다.');
    updateUI();
  });

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

  els.selectDirBtn.addEventListener('click', selectDirectory);
  els.startBtn.addEventListener('click', startProcessing);
  els.stopBtn.addEventListener('click', stopProcessing);

  els.prompts.forEach((input, idx) => {
    input.addEventListener('input', (e) => {
      state.prompts[idx] = e.target.value;
    });
  });

  updateUI();
}

// --- File Handling ---

function handleDrop(e) {
  e.preventDefault();
  els.dropArea.style.borderColor = 'var(--border-color)';
  const files = [...e.dataTransfer.files].filter(f => f.type.startsWith('image/'));
  addFiles(files);
}

function handleFileSelect(e) {
  const files = [...e.target.files].filter(f => f.type.startsWith('image/'));
  addFiles(files);
  e.target.value = '';
}

function addFiles(newFiles) {
  state.files = [...state.files, ...newFiles];
  updateUI();
}

async function selectDirectory() {
  if (!('showDirectoryPicker' in window)) {
    alert("현재 브라우저는 폴더 자동 저장 기능을 지원하지 않습니다. Chrome/Edge PC 버전을 사용해주세요.");
    return;
  }
  try {
    state.outputDirHandle = await window.showDirectoryPicker();
    els.dirStatus.textContent = state.outputDirHandle.name;
    els.dirStatus.style.color = 'var(--success-color)';
    updateUI();
  } catch (err) {
    console.error(err);
  }
}

function updateUI() {
  els.fileCount.textContent = state.files.length;
  const hasFiles = state.files.length > 0;
  const hasDir = !!state.outputDirHandle;
  const hasKey = !!state.apiKey;
  const processing = state.isProcessing;

  els.startBtn.disabled = !hasFiles || !hasDir || !hasKey || processing;
  els.stopBtn.disabled = !processing;
  
  if (!hasKey) els.statusMsg.textContent = "API Key를 입력하고 저장해주세요.";
  else if (!hasDir) els.statusMsg.textContent = "저장 폴더를 선택해주세요.";
  else if (!hasFiles) els.statusMsg.textContent = "원본 이미지를 추가해주세요.";
  else if (!processing) els.statusMsg.textContent = "준비됨";
}

// --- AI Processing Logic (Gemini + Imagen 3) ---

async function startProcessing() {
  if (state.isProcessing) return;
  state.isProcessing = true;
  state.processedCount = 0;
  state.queue = [...state.files];
  state.abortController = new AbortController();
  
  els.gallery.innerHTML = '';
  updateUI();
  
  processQueue();
}

function stopProcessing() {
  state.isProcessing = false;
  if (state.abortController) state.abortController.abort();
  state.queue = [];
  updateUI();
}

async function processQueue() {
  if (!state.isProcessing) return;

  if (state.queue.length === 0 && state.activeWorkers === 0) {
    finishProcessing();
    return;
  }

  while (state.activeWorkers < state.maxConcurrency && state.queue.length > 0) {
    const file = state.queue.shift();
    state.activeWorkers++;
    
    // Cycle through provided prompts
    const activePrompts = state.prompts.filter(p => p.trim());
    const prompt = activePrompts[state.processedCount % activePrompts.length] || "high quality aesthetic image";

    processImageAI(file, prompt).then(() => {
      state.activeWorkers--;
      state.processedCount++;
      updateProgress();
      processQueue();
    }).catch(err => {
      console.error(err);
      state.activeWorkers--;
      processQueue();
    });
  }
}

function updateProgress() {
  const percent = (state.processedCount / state.files.length) * 100;
  els.progressBar.style.width = `${percent}%`;
  els.statusMsg.textContent = `처리 중: ${state.processedCount} / ${state.files.length}`;
}

function finishProcessing() {
  state.isProcessing = false;
  els.statusMsg.textContent = "모든 작업 완료!";
  updateUI();
  alert("모든 이미지가 생성 및 저장되었습니다.");
}

// --- API Calls ---

async function processImageAI(file, userPrompt) {
  if (state.abortController.signal.aborted) return;

  try {
    // 1. Describe image using Gemini 1.5 Flash (for context)
    const description = await describeImage(file);
    
    // 2. Generate new image using Imagen 3 based on description + user prompt
    const finalPrompt = `${userPrompt}. Reference context: ${description}`;
    const imageBlob = await generateImagen3(finalPrompt);
    
    // 3. Resize to 1600x1600 & Save
    const upscaledBlob = await upscaleTo1600(imageBlob);
    const fileName = `NB_PRO_${Date.now()}_${Math.floor(Math.random()*1000)}.png`;
    
    await saveFileToDisk(upscaledBlob, fileName);
    addToGallery(upscaledBlob, fileName);
  } catch (err) {
    console.error("AI Generation failed:", err);
    throw err;
  }
}

async function describeImage(file) {
  const base64 = await fileToBase64(file);
  const resp = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${state.apiKey}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{
        parts: [
          { text: "Describe this image briefly for use as a generative AI reference. Focus on subject, colors, and composition." },
          { inline_data: { mime_type: file.type, data: base64.split(',')[1] } }
        ]
      }]
    })
  });
  const data = await resp.json();
  return data.candidates[0].content.parts[0].text;
}

async function generateImagen3(prompt) {
  // Using the Imagen 3 prediction endpoint
  const resp = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key=${state.apiKey}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      instances: [{ prompt: prompt }],
      parameters: {
        sampleCount: 1,
        aspectRatio: "1:1"
      }
    })
  });
  
  const data = await resp.json();
  if (data.error) throw new Error(data.error.message);
  
  const b64 = data.predictions[0].bytesBase64Encoded;
  const byteCharacters = atob(b64);
  const byteNumbers = new Array(byteCharacters.length);
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  return new Blob([new Uint8Array(byteNumbers)], { type: 'image/png' });
}

// --- Utilities ---

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function upscaleTo1600(blob) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = 1600;
      canvas.height = 1600;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, 1600, 1600);
      canvas.toBlob(resolve, 'image/png');
    };
    img.src = URL.createObjectURL(blob);
  });
}

async function saveFileToDisk(blob, name) {
  if (!state.outputDirHandle) return;
  const fileHandle = await state.outputDirHandle.getFileHandle(name, { create: true });
  const writable = await fileHandle.createWritable();
  await writable.write(blob);
  await writable.close();
}

function addToGallery(blob, name) {
  const url = URL.createObjectURL(blob);
  const div = document.createElement('div');
  div.className = 'gallery-item';
  div.innerHTML = `<img src="${url}"><div class="overlay">${name}</div>`;
  els.gallery.prepend(div);
}

init();
