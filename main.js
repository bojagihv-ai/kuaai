// State Management
const state = {
  files: [],
  prompts: JSON.parse(localStorage.getItem('nb_saved_prompts')) || ['', '', '', ''], // Load saved prompts
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
  // Restore API Key
  if (state.apiKey) els.apiKeyInput.value = state.apiKey;

  // Restore Prompts
  els.prompts.forEach((input, idx) => {
    input.value = state.prompts[idx] || '';
    input.addEventListener('input', (e) => {
      state.prompts[idx] = e.target.value;
      // Auto-save prompts
      localStorage.setItem('nb_saved_prompts', JSON.stringify(state.prompts));
    });
  });

  // API Key Saving Logic
  els.saveKeyBtn.addEventListener('click', () => {
    const inputVal = els.apiKeyInput.value.trim();
    
    // Validation check
    if (inputVal.startsWith('http')) {
      alert("⚠️ 주의: API Key란에는 '주소(URL)'가 아닌 '키(AIza...)'를 입력해야 합니다.\n구글 AI Studio에서 발급받은 키를 확인해주세요.");
      return;
    }

    state.apiKey = inputVal;
    localStorage.setItem('gemini_api_key', state.apiKey);
    alert('API Key가 저장되었습니다! (이제 이미지 분석 기능이 활성화됩니다)');
    updateUI();
  });

  // File & Directory Handlers
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
    alert("❌ 현재 브라우저는 폴더 자동 저장을 지원하지 않습니다.\n(Chrome 또는 Edge PC 버전을 사용해주세요)");
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

// --- AI Processing Logic (Refined) ---

async function startProcessing() {
  if (state.isProcessing) return;
  
  // Validation check before start
  if (!state.apiKey) {
    if (!confirm("⚠️ API Key가 입력되지 않았습니다.\n키가 없으면 원본 사진을 분석하지 못하고 '프롬프트'로만 이미지를 생성합니다.\n(원본과 전혀 다른 그림이 나올 수 있습니다.)\n\n그대로 진행하시겠습니까?")) {
      return;
    }
  }

  state.isProcessing = true;
  state.processedCount = 0;
  state.errors = [];
  state.queue = [...state.files];
  state.abortController = new AbortController();
  
  els.gallery.innerHTML = '';
  updateUI();
  els.statusMsg.textContent = "작업 시작...";
  
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
      : "high quality, detailed, masterpiece";

    processImageAI(file, prompt).then(() => {
      state.activeWorkers--;
      state.processedCount++;
      updateProgress();
      processQueue();
    }).catch(err => {
      console.error("Task failed:", err);
      state.errors.push(err.message);
      state.activeWorkers--;
      state.processedCount++;
      updateProgress();
      processQueue();
    });
  }
}

function updateProgress() {
  const percent = (state.processedCount / state.files.length) * 100;
  els.progressBar.style.width = `${percent}%`;
  els.statusMsg.textContent = `처리 중: ${state.processedCount} / ${state.files.length} (실패: ${state.errors.length})`;
}

function finishProcessing() {
  state.isProcessing = false;
  
  let msg = "작업이 완료되었습니다!";
  if (state.errors.length > 0) {
    msg += `\n⚠️ ${state.errors.length}장의 이미지가 생성에 실패했습니다.\n(API 키 오류 또는 인터넷 연결을 확인하세요)`;
  }
  
  els.statusMsg.textContent = state.errors.length > 0 ? "완료 (일부 오류)" : "완료!";
  updateUI();
  
  // Delay alert slightly to let UI update
  setTimeout(() => alert(msg), 100);
}

// --- API Calls ---

async function processImageAI(file, userPrompt) {
  if (state.abortController.signal.aborted) return;

  let description = "";
  
  // 1. Describe Image (Gemini) - Only if Key exists
  if (state.apiKey) {
    try {
      description = await describeImage(file);
    } catch (err) {
      console.warn("Gemini Analysis Failed:", err);
      // Don't throw, just continue. But prompt might be weak.
      if (!userPrompt) throw new Error("이미지 분석 실패 & 프롬프트 없음");
    }
  }

  // 2. Build Strong Prompt
  // Combining User Prompt + Image Description
  let finalPrompt = "";
  if (description) {
    finalPrompt = `(Subject: ${description}). ${userPrompt}. high quality, 8k resolution, detailed texture.`;
  } else {
    finalPrompt = `${userPrompt}. high quality, 8k resolution.`;
  }

  // 3. Generate Image (Pollinations - Flux Model)
  // Flux model follows prompts very well
  const imageBlob = await generatePollinations(finalPrompt);
  
  // 4. Resize to 1600x1600 (Upscale)
  const upscaledBlob = await upscaleTo1600(imageBlob);
  const fileName = `NB_PRO_${Date.now()}_${Math.floor(Math.random()*1000)}.png`;
  
  // 5. Save & Display
  await saveFileToDisk(upscaledBlob, fileName);
  addToGallery(upscaledBlob, fileName);
}

async function describeImage(file) {
  const base64 = await fileToBase64(file);
  // Using Gemini 1.5 Flash for speed/cost
  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${state.apiKey}`;
  
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{
        parts: [
          // More specific system instruction for Gemini
          { text: "Describe the visual content of this image in detail. Focus on the main subject, pose, action, background, colors, and lighting. Do not evaluate quality. Output only the description." },
          { inline_data: { mime_type: file.type, data: base64.split(',')[1] } }
        ]
      }]
    })
  });

  if (!resp.ok) {
    const errData = await resp.json().catch(()=>({}));
    throw new Error(`Gemini API Error ${resp.status}: ${errData.error?.message || 'Unknown'}`);
  }
  
  const data = await resp.json();
  const text = data.candidates?.[0]?.content?.parts?.[0]?.text;
  if (!text) throw new Error("Gemini returned empty description");
  
  return text;
}

async function generatePollinations(prompt) {
  const encoded = encodeURIComponent(prompt);
  const seed = Math.floor(Math.random() * 1000000);
  // Using 'flux' model for better prompt adherence
  const url = `https://image.pollinations.ai/prompt/${encoded}?width=1280&height=1280&nologo=true&seed=${seed}&model=flux`;
  
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Pollinations Generation failed: ${resp.status}`);
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
    throw new Error("File save failed (Permission?)");
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
