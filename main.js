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
  apiKey: localStorage.getItem('gemini_api_key') || '',
  errors: []
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
    alert('API Key가 저장되었습니다. (이미지 분석에 사용됨)');
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
  const processing = state.isProcessing;

  els.startBtn.disabled = !hasFiles || !hasDir || processing;
  els.stopBtn.disabled = !processing;
  
  if (!hasDir) els.statusMsg.textContent = "저장 폴더를 선택해주세요.";
  else if (!hasFiles) els.statusMsg.textContent = "원본 이미지를 추가해주세요.";
  else if (!processing) els.statusMsg.textContent = "준비됨";
}

// --- AI Processing Logic (Hybrid) ---

async function startProcessing() {
  if (state.isProcessing) return;
  state.isProcessing = true;
  state.processedCount = 0;
  state.errors = [];
  state.queue = [...state.files];
  state.abortController = new AbortController();
  
  els.gallery.innerHTML = '';
  updateUI();
  els.statusMsg.textContent = "AI 엔진 연결 중...";
  
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
    
    // Cycle prompts
    const activePrompts = state.prompts.filter(p => p.trim());
    const prompt = activePrompts.length > 0 
      ? activePrompts[state.processedCount % activePrompts.length] 
      : "high quality artistic illustration, detailed";

    processImageAI(file, prompt).then(() => {
      state.activeWorkers--;
      state.processedCount++;
      updateProgress();
      processQueue();
    }).catch(err => {
      console.error("Task failed:", err);
      state.errors.push(err.message);
      state.activeWorkers--;
      state.processedCount++; // Still count as processed (failed)
      updateProgress();
      processQueue();
    });
  }
}

function updateProgress() {
  const percent = (state.processedCount / state.files.length) * 100;
  els.progressBar.style.width = `${percent}%`;
  els.statusMsg.textContent = `처리 중: ${state.processedCount} / ${state.files.length} (성공: ${state.processedCount - state.errors.length})`;
}

function finishProcessing() {
  state.isProcessing = false;
  
  let msg = "모든 작업이 완료되었습니다.";
  if (state.errors.length > 0) {
    msg += `\n⚠️ ${state.errors.length}개의 오류가 발생했습니다.\n(첫번째 오류: ${state.errors[0]})`;
  }
  
  els.statusMsg.textContent = state.errors.length > 0 ? "완료 (일부 오류)" : "완료!";
  updateUI();
  alert(msg);
}

// --- API Calls ---

async function processImageAI(file, userPrompt) {
  if (state.abortController.signal.aborted) return;

  try {
    // 1. Describe image using Gemini 1.5 Flash (If Key exists)
    let description = "";
    if (state.apiKey) {
      try {
        description = await describeImage(file);
      } catch (geminiErr) {
        console.warn("Gemini description failed, falling back to raw prompt:", geminiErr);
        // Don't stop, just proceed with raw prompt
      }
    }

    // 2. Construct Prompt
    // Combining user prompt with image description for better img2img-like results
    const fullPrompt = description 
      ? `${userPrompt}. The image features: ${description}. High quality, 8k.` 
      : `${userPrompt}. High quality, 8k resolution.`;

    // 3. Generate with Pollinations (Robust, Free, Fast)
    const imageBlob = await generatePollinations(fullPrompt);
    
    // 4. Resize & Save
    const upscaledBlob = await upscaleTo1600(imageBlob);
    const fileName = `NB_PRO_${Date.now()}_${Math.floor(Math.random()*1000)}.png`;
    
    await saveFileToDisk(upscaledBlob, fileName);
    addToGallery(upscaledBlob, fileName);
  } catch (err) {
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
          { text: "Describe the main subject, composition, and colors of this image in one sentence for AI image generation reference." },
          { inline_data: { mime_type: file.type, data: base64.split(',')[1] } }
        ]
      }]
    })
  });
  if (!resp.ok) throw new Error(`Gemini API Error: ${resp.status}`);
  const data = await resp.json();
  if (data.error) throw new Error(data.error.message);
  return data.candidates?.[0]?.content?.parts?.[0]?.text || "";
}

async function generatePollinations(prompt) {
  // Pollinations.ai generates images from text
  const encoded = encodeURIComponent(prompt);
  const seed = Math.floor(Math.random() * 100000);
  // Requesting slightly larger to ensure quality, then scaling
  const url = `https://image.pollinations.ai/prompt/${encoded}?width=1280&height=1280&nologo=true&seed=${seed}&model=flux`;
  
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Image Generation failed: ${resp.status}`);
  return await resp.blob();
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
      // High quality scaling
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(img, 0, 0, 1600, 1600);
      canvas.toBlob(resolve, 'image/png');
    };
    img.src = URL.createObjectURL(blob);
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
    throw new Error("File save failed: " + err.message);
  }
}

function addToGallery(blob, name) {
  const url = URL.createObjectURL(blob);
  const div = document.createElement('div');
  div.className = 'gallery-item';
  div.innerHTML = `<img src="${url}"><div class="overlay">${name}</div>`;
  els.gallery.prepend(div);
}

init();