// ============================================================
// 로젠 x 카페24 송장 매니저 - Core Logic
// ============================================================

// --- State ---
const appState = {
  cafe24: {
    mallId: localStorage.getItem('lc_cafe24_mall_id') || '',
    clientId: localStorage.getItem('lc_cafe24_client_id') || '',
    clientSecret: localStorage.getItem('lc_cafe24_client_secret') || '',
    token: localStorage.getItem('lc_cafe24_token') || '',
    refreshToken: localStorage.getItem('lc_cafe24_refresh_token') || '',
    tokenExpiresAt: localStorage.getItem('lc_cafe24_token_expires_at') || '',
  },
  logen: {
    customerCode: localStorage.getItem('lc_logen_customer_code') || '',
    senderName: localStorage.getItem('lc_logen_sender_name') || '',
    senderTel: localStorage.getItem('lc_logen_sender_tel') || '',
    senderAddr: localStorage.getItem('lc_logen_sender_addr') || '',
    senderZipcode: localStorage.getItem('lc_logen_sender_zipcode') || '',
  },
  orders: [],           // 카페24에서 가져온 미발송 주문
  selectedOrders: [],    // 송장 발급을 위해 선택된 주문
  invoiceItems: [],      // 송장 발급 대상 (주문 + 송장번호)
  uploadItems: [],       // 카페24 업로드 대상
  trackingItems: [],     // 배송 조회 대상
};

// --- DOM References ---
const dom = {};

function initDom() {
  // Settings
  dom.cafe24MallId = document.getElementById('cafe24-mall-id');
  dom.cafe24ClientId = document.getElementById('cafe24-client-id');
  dom.cafe24ClientSecret = document.getElementById('cafe24-client-secret');
  dom.cafe24Token = document.getElementById('cafe24-token');
  dom.cafe24RefreshToken = document.getElementById('cafe24-refresh-token');
  dom.saveCafe24Btn = document.getElementById('save-cafe24-btn');
  dom.cafe24Status = document.getElementById('cafe24-status');

  dom.logenCustomerCode = document.getElementById('logen-customer-code');
  dom.logenSenderName = document.getElementById('logen-sender-name');
  dom.logenSenderTel = document.getElementById('logen-sender-tel');
  dom.logenSenderAddr = document.getElementById('logen-sender-addr');
  dom.logenSenderZipcode = document.getElementById('logen-sender-zipcode');
  dom.saveLogenBtn = document.getElementById('save-logen-btn');
  dom.logenStatus = document.getElementById('logen-status');

  // Orders
  dom.orderDateFrom = document.getElementById('order-date-from');
  dom.orderDateTo = document.getElementById('order-date-to');
  dom.fetchOrdersBtn = document.getElementById('fetch-orders-btn');
  dom.ordersTbody = document.getElementById('orders-tbody');
  dom.selectAllOrders = document.getElementById('select-all-orders');
  dom.orderCountBadge = document.getElementById('order-count-badge');
  dom.selectedCount = document.getElementById('selected-count');
  dom.exportSelectedBtn = document.getElementById('export-selected-btn');

  // Invoice
  dom.invoiceTbody = document.getElementById('invoice-tbody');
  dom.invoiceCountBadge = document.getElementById('invoice-count-badge');
  dom.downloadLogenExcel = document.getElementById('download-logen-excel');
  dom.generateInvoicesBtn = document.getElementById('generate-invoices-btn');

  // Upload
  dom.invoiceFileDrop = document.getElementById('invoice-file-drop');
  dom.invoiceFileInput = document.getElementById('invoice-file-input');
  dom.manualInvoiceInput = document.getElementById('manual-invoice-input');
  dom.parseManualBtn = document.getElementById('parse-manual-btn');
  dom.uploadTbody = document.getElementById('upload-tbody');
  dom.selectAllUpload = document.getElementById('select-all-upload');
  dom.uploadToCafe24Btn = document.getElementById('upload-to-cafe24-btn');
  dom.uploadProgress = document.getElementById('upload-progress');
  dom.uploadProgressBar = document.getElementById('upload-progress-bar');
  dom.uploadProgressText = document.getElementById('upload-progress-text');

  // Tracking
  dom.trackingInput = document.getElementById('tracking-input');
  dom.trackSingleBtn = document.getElementById('track-single-btn');
  dom.trackAllBtn = document.getElementById('track-all-btn');
  dom.trackingTbody = document.getElementById('tracking-tbody');
  dom.trackingModal = document.getElementById('tracking-modal');
  dom.closeModal = document.getElementById('close-modal');
  dom.trackingDetail = document.getElementById('tracking-detail');

  // Global
  dom.loadingOverlay = document.getElementById('loading-overlay');
  dom.loadingText = document.getElementById('loading-text');
  dom.toastContainer = document.getElementById('toast-container');
}

// --- Init ---
function init() {
  initDom();
  initTabs();
  loadSettings();
  initEventListeners();
  setDefaultDates();
  updateStatusIndicators();
}

function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
    });
  });
}

function loadSettings() {
  dom.cafe24MallId.value = appState.cafe24.mallId;
  dom.cafe24ClientId.value = appState.cafe24.clientId;
  dom.cafe24ClientSecret.value = appState.cafe24.clientSecret;
  dom.cafe24Token.value = appState.cafe24.token;
  dom.cafe24RefreshToken.value = appState.cafe24.refreshToken;
  dom.logenCustomerCode.value = appState.logen.customerCode;
  dom.logenSenderName.value = appState.logen.senderName;
  dom.logenSenderTel.value = appState.logen.senderTel;
  dom.logenSenderAddr.value = appState.logen.senderAddr;
  dom.logenSenderZipcode.value = appState.logen.senderZipcode;
}

function setDefaultDates() {
  const today = new Date();
  const weekAgo = new Date(today);
  weekAgo.setDate(weekAgo.getDate() - 7);
  dom.orderDateTo.value = formatDate(today);
  dom.orderDateFrom.value = formatDate(weekAgo);
}

function initEventListeners() {
  // Settings save
  dom.saveCafe24Btn.addEventListener('click', saveCafe24Settings);
  dom.saveLogenBtn.addEventListener('click', saveLogenSettings);

  // Orders
  dom.fetchOrdersBtn.addEventListener('click', fetchOrders);
  dom.selectAllOrders.addEventListener('change', toggleSelectAllOrders);
  dom.exportSelectedBtn.addEventListener('click', exportToInvoiceTab);

  // Invoice
  dom.downloadLogenExcel.addEventListener('click', downloadLogenEDI);
  dom.generateInvoicesBtn.addEventListener('click', generateTestInvoices);

  // Upload
  dom.invoiceFileDrop.addEventListener('click', () => dom.invoiceFileInput.click());
  dom.invoiceFileDrop.addEventListener('dragover', e => { e.preventDefault(); e.currentTarget.style.borderColor = 'var(--primary-color)'; });
  dom.invoiceFileDrop.addEventListener('dragleave', e => { e.currentTarget.style.borderColor = ''; });
  dom.invoiceFileDrop.addEventListener('drop', handleInvoiceFileDrop);
  dom.invoiceFileInput.addEventListener('change', handleInvoiceFileSelect);
  dom.parseManualBtn.addEventListener('click', parseManualInput);
  dom.selectAllUpload.addEventListener('change', toggleSelectAllUpload);
  dom.uploadToCafe24Btn.addEventListener('click', uploadToCafe24);

  // Tracking
  dom.trackSingleBtn.addEventListener('click', trackSingle);
  dom.trackAllBtn.addEventListener('click', trackAll);
  dom.closeModal.addEventListener('click', () => dom.trackingModal.style.display = 'none');
  dom.trackingModal.addEventListener('click', e => { if (e.target === dom.trackingModal) dom.trackingModal.style.display = 'none'; });
}

// ============================================================
// SETTINGS
// ============================================================

function saveCafe24Settings() {
  appState.cafe24.mallId = dom.cafe24MallId.value.trim();
  appState.cafe24.clientId = dom.cafe24ClientId.value.trim();
  appState.cafe24.clientSecret = dom.cafe24ClientSecret.value.trim();
  appState.cafe24.token = dom.cafe24Token.value.trim();
  appState.cafe24.refreshToken = dom.cafe24RefreshToken.value.trim();
  localStorage.setItem('lc_cafe24_mall_id', appState.cafe24.mallId);
  localStorage.setItem('lc_cafe24_client_id', appState.cafe24.clientId);
  localStorage.setItem('lc_cafe24_client_secret', appState.cafe24.clientSecret);
  localStorage.setItem('lc_cafe24_token', appState.cafe24.token);
  localStorage.setItem('lc_cafe24_refresh_token', appState.cafe24.refreshToken);
  updateStatusIndicators();
  showToast('카페24 설정이 저장되었습니다.', 'success');
}

function saveLogenSettings() {
  appState.logen.customerCode = dom.logenCustomerCode.value.trim();
  appState.logen.senderName = dom.logenSenderName.value.trim();
  appState.logen.senderTel = dom.logenSenderTel.value.trim();
  appState.logen.senderAddr = dom.logenSenderAddr.value.trim();
  appState.logen.senderZipcode = dom.logenSenderZipcode.value.trim();
  localStorage.setItem('lc_logen_customer_code', appState.logen.customerCode);
  localStorage.setItem('lc_logen_sender_name', appState.logen.senderName);
  localStorage.setItem('lc_logen_sender_tel', appState.logen.senderTel);
  localStorage.setItem('lc_logen_sender_addr', appState.logen.senderAddr);
  localStorage.setItem('lc_logen_sender_zipcode', appState.logen.senderZipcode);
  updateStatusIndicators();
  showToast('로젠 설정이 저장되었습니다.', 'success');
}

function updateStatusIndicators() {
  const cafe24Ok = appState.cafe24.mallId && appState.cafe24.token;
  const logenOk = appState.logen.customerCode && appState.logen.senderName;

  const cafe24Dot = dom.cafe24Status.querySelector('.dot');
  const cafe24Text = dom.cafe24Status.querySelector('strong');
  cafe24Dot.className = `dot ${cafe24Ok ? 'connected' : ''}`;
  cafe24Text.textContent = cafe24Ok ? '연결됨' : '미연결';

  const logenDot = dom.logenStatus.querySelector('.dot');
  const logenText = dom.logenStatus.querySelector('strong');
  logenDot.className = `dot ${logenOk ? 'connected' : ''}`;
  logenText.textContent = logenOk ? '설정완료' : '미설정';
}

// ============================================================
// CAFE24 토큰 자동 갱신
// ============================================================

// API 프록시 URL (Vercel에서 호스팅)
const API_PROXY = '/api/cafe24';
const LOGEN_PROXY = '/api/logen';

async function ensureValidToken() {
  // 토큰 만료 시간 확인 (만료 5분 전에 미리 갱신)
  const expiresAt = appState.cafe24.tokenExpiresAt;
  if (expiresAt) {
    const expiresTime = new Date(expiresAt).getTime();
    const now = Date.now();
    if (now < expiresTime - 5 * 60 * 1000) {
      return; // 아직 유효함
    }
  }

  // Refresh Token으로 갱신 시도
  if (!appState.cafe24.refreshToken || !appState.cafe24.clientId || !appState.cafe24.clientSecret) {
    return; // 갱신 불가 (정보 부족)
  }

  try {
    const resp = await fetch(API_PROXY, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'refresh_token',
        mallId: appState.cafe24.mallId,
        clientId: appState.cafe24.clientId,
        clientSecret: appState.cafe24.clientSecret,
        refreshToken: appState.cafe24.refreshToken,
      }),
    });

    if (resp.ok) {
      const data = await resp.json();
      if (data.access_token) {
        appState.cafe24.token = data.access_token;
        appState.cafe24.refreshToken = data.refresh_token;
        appState.cafe24.tokenExpiresAt = data.expires_at;
        localStorage.setItem('lc_cafe24_token', data.access_token);
        localStorage.setItem('lc_cafe24_refresh_token', data.refresh_token);
        localStorage.setItem('lc_cafe24_token_expires_at', data.expires_at);
        dom.cafe24Token.value = data.access_token;
        dom.cafe24RefreshToken.value = data.refresh_token;
        console.log('토큰 자동 갱신 완료:', data.expires_at);
      }
    }
  } catch (err) {
    console.warn('토큰 자동 갱신 실패:', err);
  }
}

// ============================================================
// CAFE24 API - 주문 조회
// ============================================================

async function fetchOrders() {
  if (!appState.cafe24.mallId || !appState.cafe24.token) {
    showToast('카페24 설정을 먼저 완료해주세요.', 'error');
    switchTab('settings');
    return;
  }

  const dateFrom = dom.orderDateFrom.value;
  const dateTo = dom.orderDateTo.value;

  showLoading('카페24에서 미발송 주문을 가져오는 중...');

  try {
    await ensureValidToken();
    const orders = await cafe24GetUnshippedOrders(dateFrom, dateTo);
    appState.orders = orders;
    renderOrdersTable(orders);
    dom.orderCountBadge.textContent = `${orders.length}건`;
    showToast(`${orders.length}건의 미발송 주문을 가져왔습니다.`, 'success');
  } catch (err) {
    console.error('주문 조회 실패:', err);
    showToast(`주문 조회 실패: ${err.message}`, 'error');
    // 데모 모드 - API 호출 실패 시 샘플 데이터
    if (confirm('API 연결에 실패했습니다. 데모 데이터로 테스트하시겠습니까?')) {
      const demoOrders = generateDemoOrders();
      appState.orders = demoOrders;
      renderOrdersTable(demoOrders);
      dom.orderCountBadge.textContent = `${demoOrders.length}건`;
      showToast(`데모 모드: ${demoOrders.length}건의 샘플 주문이 로드되었습니다.`, 'info');
    }
  } finally {
    hideLoading();
  }
}

async function cafe24GetUnshippedOrders(dateFrom, dateTo) {
  const resp = await fetch(API_PROXY, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action: 'get_orders',
      mallId: appState.cafe24.mallId,
      token: appState.cafe24.token,
      startDate: dateFrom,
      endDate: dateTo,
    }),
  });

  if (!resp.ok) {
    const errData = await resp.json().catch(() => ({}));
    throw new Error(errData.error?.message || `HTTP ${resp.status}`);
  }

  const data = await resp.json();
  return (data.orders || []).map(normalizeOrder);
}

function normalizeOrder(order) {
  const item = order.items?.[0] || {};
  const receiver = order.receivers?.[0] || {};
  return {
    orderId: order.order_id,
    orderDate: order.order_date,
    orderItemCode: item.order_item_code || '',
    productName: item.product_name || '상품명 없음',
    quantity: item.quantity || 1,
    receiverName: receiver.name || order.buyer_name || '',
    receiverTel: receiver.cellphone || receiver.phone || '',
    receiverAddr: `${receiver.address1 || ''} ${receiver.address2 || ''}`.trim(),
    receiverZipcode: receiver.zipcode || '',
    shippingMessage: receiver.shipping_message || '',
    trackingNo: '',
    status: 'pending',
  };
}

// ============================================================
// 주문 테이블 렌더링
// ============================================================

function renderOrdersTable(orders) {
  if (orders.length === 0) {
    dom.ordersTbody.innerHTML = '<tr class="empty-row"><td colspan="10">미발송 주문이 없습니다</td></tr>';
    return;
  }

  dom.ordersTbody.innerHTML = orders.map((o, i) => `
    <tr data-index="${i}">
      <td><input type="checkbox" class="order-check" data-index="${i}"></td>
      <td title="${esc(o.orderId)}">${esc(o.orderId)}</td>
      <td>${esc(formatDateTime(o.orderDate))}</td>
      <td>${esc(o.receiverName)}</td>
      <td>${esc(o.receiverTel)}</td>
      <td title="${esc(o.receiverAddr)}">${esc(o.receiverAddr)}</td>
      <td>${esc(o.receiverZipcode)}</td>
      <td title="${esc(o.productName)}">${esc(o.productName)}</td>
      <td>${o.quantity}</td>
      <td title="${esc(o.shippingMessage)}">${esc(o.shippingMessage)}</td>
    </tr>
  `).join('');

  // 체크박스 이벤트
  dom.ordersTbody.querySelectorAll('.order-check').forEach(cb => {
    cb.addEventListener('change', updateOrderSelection);
  });

  dom.selectAllOrders.checked = false;
  updateOrderSelection();
}

function toggleSelectAllOrders() {
  const checked = dom.selectAllOrders.checked;
  dom.ordersTbody.querySelectorAll('.order-check').forEach(cb => cb.checked = checked);
  updateOrderSelection();
}

function updateOrderSelection() {
  const checks = [...dom.ordersTbody.querySelectorAll('.order-check')];
  const selectedCount = checks.filter(c => c.checked).length;
  dom.selectedCount.textContent = `${selectedCount}건 선택됨`;
  dom.exportSelectedBtn.disabled = selectedCount === 0;
}

// ============================================================
// 송장 발급 탭
// ============================================================

function exportToInvoiceTab() {
  const checks = [...dom.ordersTbody.querySelectorAll('.order-check')];
  const selectedIndices = checks.filter(c => c.checked).map(c => parseInt(c.dataset.index));
  appState.invoiceItems = selectedIndices.map(i => ({ ...appState.orders[i], trackingNo: '', status: 'pending' }));
  renderInvoiceTable();
  dom.invoiceCountBadge.textContent = `${appState.invoiceItems.length}건`;
  switchTab('invoice');
  showToast(`${appState.invoiceItems.length}건이 송장 발급 탭으로 이동되었습니다.`, 'success');
}

function renderInvoiceTable() {
  const items = appState.invoiceItems;
  if (items.length === 0) {
    dom.invoiceTbody.innerHTML = '<tr class="empty-row"><td colspan="9">\'주문 조회\' 탭에서 주문을 선택해주세요</td></tr>';
    return;
  }

  dom.invoiceTbody.innerHTML = items.map((item, i) => `
    <tr>
      <td>${i + 1}</td>
      <td>${esc(item.orderId)}</td>
      <td>${esc(item.receiverName)}</td>
      <td>${esc(item.receiverTel)}</td>
      <td title="${esc(item.receiverAddr)}">${esc(item.receiverAddr)}</td>
      <td title="${esc(item.productName)}">${esc(item.productName)}</td>
      <td>${item.quantity}</td>
      <td><input type="text" class="invoice-input" data-index="${i}" value="${esc(item.trackingNo)}" placeholder="송장번호"></td>
      <td><span class="status-tag ${item.status}">${statusLabel(item.status)}</span></td>
    </tr>
  `).join('');

  dom.invoiceTbody.querySelectorAll('.invoice-input').forEach(input => {
    input.addEventListener('change', e => {
      const idx = parseInt(e.target.dataset.index);
      appState.invoiceItems[idx].trackingNo = e.target.value.trim();
      if (e.target.value.trim()) {
        appState.invoiceItems[idx].status = 'assigned';
      }
      renderInvoiceTable();
    });
  });
}

// ============================================================
// 로젠 EDI 엑셀 생성
// ============================================================

function downloadLogenEDI() {
  if (appState.invoiceItems.length === 0) {
    showToast('송장 발급 대상이 없습니다.', 'warning');
    return;
  }

  const sender = appState.logen;
  const rows = appState.invoiceItems.map((item, i) => ({
    '순번': i + 1,
    '고객코드': sender.customerCode,
    '보내는분성명': sender.senderName,
    '보내는분전화번호': sender.senderTel,
    '보내는분주소': sender.senderAddr,
    '보내는분우편번호': sender.senderZipcode,
    '받는분성명': item.receiverName,
    '받는분전화번호': item.receiverTel,
    '받는분주소': item.receiverAddr,
    '받는분우편번호': item.receiverZipcode,
    '품목명': item.productName,
    '수량': item.quantity,
    '주문번호': item.orderId,
    '배송메시지': item.shippingMessage || '',
    '운임구분': '선불',
  }));

  const ws = XLSX.utils.json_to_sheet(rows);

  // 컬럼 너비 설정
  ws['!cols'] = [
    { wch: 5 },   // 순번
    { wch: 12 },  // 고객코드
    { wch: 10 },  // 보내는분성명
    { wch: 15 },  // 보내는분전화번호
    { wch: 40 },  // 보내는분주소
    { wch: 8 },   // 보내는분우편번호
    { wch: 10 },  // 받는분성명
    { wch: 15 },  // 받는분전화번호
    { wch: 40 },  // 받는분주소
    { wch: 8 },   // 받는분우편번호
    { wch: 30 },  // 품목명
    { wch: 5 },   // 수량
    { wch: 20 },  // 주문번호
    { wch: 30 },  // 배송메시지
    { wch: 8 },   // 운임구분
  ];

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, '로젠배송데이터');
  const filename = `로젠EDI_${formatDate(new Date())}_${appState.invoiceItems.length}건.xlsx`;
  XLSX.writeFile(wb, filename);
  showToast(`${filename} 다운로드 완료!`, 'success');
}

function generateTestInvoices() {
  if (appState.invoiceItems.length === 0) {
    showToast('송장 발급 대상이 없습니다.', 'warning');
    return;
  }

  appState.invoiceItems.forEach(item => {
    item.trackingNo = generateFakeTrackingNo();
    item.status = 'assigned';
  });

  renderInvoiceTable();

  // 업로드 탭에도 자동 반영
  appState.uploadItems = appState.invoiceItems.map(item => ({ ...item }));
  renderUploadTable();

  showToast(`${appState.invoiceItems.length}건의 테스트 송장번호가 생성되었습니다.`, 'info');
}

function generateFakeTrackingNo() {
  // 로젠 송장번호 형식: 숫자 11~13자리
  const prefix = '9' + Math.floor(Math.random() * 9 + 1);
  let num = prefix;
  for (let i = 0; i < 9; i++) num += Math.floor(Math.random() * 10);
  return num;
}

// ============================================================
// 송장 등록 (Upload) 탭
// ============================================================

function handleInvoiceFileDrop(e) {
  e.preventDefault();
  e.currentTarget.style.borderColor = '';
  const file = e.dataTransfer.files[0];
  if (file) parseInvoiceFile(file);
}

function handleInvoiceFileSelect(e) {
  const file = e.target.files[0];
  if (file) parseInvoiceFile(file);
  e.target.value = '';
}

async function parseInvoiceFile(file) {
  showLoading('파일 분석 중...');
  try {
    const data = await readFileAsArrayBuffer(file);
    const workbook = XLSX.read(data, { type: 'array' });
    const sheet = workbook.Sheets[workbook.SheetNames[0]];

    // 로젠 출력 파일은 상단에 제목 행이 있어 헤더가 3행째에 있음
    // 먼저 전체 데이터를 배열로 읽어서 헤더 행을 자동 감지
    const allRows = XLSX.utils.sheet_to_json(sheet, { header: 1 });

    // 헤더 행 찾기: '운송장번호' 또는 '송장번호' 가 포함된 행
    let headerRowIdx = -1;
    let headers = [];
    for (let i = 0; i < Math.min(allRows.length, 10); i++) {
      const row = allRows[i];
      if (!row) continue;
      const rowStrs = row.map(c => String(c || '').trim());
      if (rowStrs.some(c => c === '운송장번호' || c === '송장번호' || c === 'tracking_no')) {
        headerRowIdx = i;
        headers = rowStrs;
        break;
      }
    }

    // 헤더를 못 찾으면 기본 방식으로 파싱
    if (headerRowIdx === -1) {
      const rows = XLSX.utils.sheet_to_json(sheet);
      if (rows.length === 0) {
        showToast('파일에 데이터가 없습니다.', 'warning');
        return;
      }
      const mapped = rows.map(row => {
        const orderId = row['주문번호'] || row['order_id'] || row['주문 번호'] || '';
        const trackingNo = row['송장번호'] || row['운송장번호'] || row['tracking_no'] || row['운송장 번호'] || '';
        const receiverName = row['받는분성명'] || row['수령인'] || row['receiver_name'] || row['이름'] || '';
        const productName = row['품목명'] || row['상품명'] || row['product_name'] || row['물품명'] || '';
        return { orderId: String(orderId).trim(), trackingNo: String(trackingNo).trim(), receiverName: String(receiverName).trim(), productName: String(productName).trim(), status: trackingNo ? 'assigned' : 'pending' };
      }).filter(r => r.orderId || r.trackingNo);
      appState.uploadItems = mapped;
      renderUploadTable();
      showToast(`${mapped.length}건의 데이터를 읽었습니다.`, 'success');
      return;
    }

    // 헤더 행을 기반으로 데이터 행 파싱
    const dataRows = allRows.slice(headerRowIdx + 1);
    const findCol = (...names) => {
      for (const name of names) {
        const idx = headers.indexOf(name);
        if (idx !== -1) return idx;
      }
      return -1;
    };

    const colTrackingNo = findCol('운송장번호', '송장번호', 'tracking_no');
    const colName = findCol('이름', '받는분성명', '수령인', '수하인');
    const colProduct = findCol('물품명', '품목명', '상품명');
    const colOrderId = findCol('주문번호', 'order_id');
    const colPhone = findCol('휴대폰', '전화', '연락처');
    const colAddr = findCol('주소');

    const mapped = dataRows.map(row => {
      if (!row || row.length === 0) return null;
      const trackingNo = colTrackingNo >= 0 ? String(row[colTrackingNo] || '').trim() : '';
      const receiverName = colName >= 0 ? String(row[colName] || '').trim() : '';
      const productName = colProduct >= 0 ? String(row[colProduct] || '').trim() : '';
      const orderId = colOrderId >= 0 ? String(row[colOrderId] || '').trim() : '';
      const phone = colPhone >= 0 ? String(row[colPhone] || '').trim() : '';
      const addr = colAddr >= 0 ? String(row[colAddr] || '').trim() : '';

      // 숫자가 아닌 운송장번호는 헤더/소계 행이므로 제외
      if (!trackingNo || trackingNo === '합계' || !/^\d+$/.test(trackingNo)) return null;

      return { orderId, trackingNo, receiverName, productName, phone, addr, status: 'assigned' };
    }).filter(Boolean);

    // 주문번호가 없는 경우, 수령인 이름+물품명으로 기존 주문과 매칭
    if (appState.invoiceItems.length > 0) {
      mapped.forEach(m => {
        if (m.orderId) {
          const match = appState.invoiceItems.find(item => item.orderId === m.orderId);
          if (match) {
            m.receiverName = m.receiverName || match.receiverName;
            m.productName = m.productName || match.productName;
            m.orderItemCode = match.orderItemCode;
          }
        } else {
          // 주문번호 없으면 수령인 이름으로 매칭 시도
          const match = appState.invoiceItems.find(item =>
            item.receiverName === m.receiverName ||
            (m.phone && item.receiverTel && item.receiverTel.replace(/-/g, '').includes(m.phone.replace(/-/g, '')))
          );
          if (match) {
            m.orderId = match.orderId;
            m.productName = m.productName || match.productName;
            m.orderItemCode = match.orderItemCode;
          }
        }
      });
    }

    appState.uploadItems = mapped;
    renderUploadTable();
    showToast(`${mapped.length}건의 데이터를 읽었습니다.`, 'success');
  } catch (err) {
    console.error(err);
    showToast(`파일 파싱 오류: ${err.message}`, 'error');
  } finally {
    hideLoading();
  }
}

function parseManualInput() {
  const text = dom.manualInvoiceInput.value.trim();
  if (!text) {
    showToast('데이터를 입력해주세요.', 'warning');
    return;
  }

  const lines = text.split('\n').filter(l => l.trim());
  const parsed = lines.map(line => {
    const parts = line.split(/[,\t]/).map(p => p.trim());
    return {
      orderId: parts[0] || '',
      trackingNo: parts[1] || '',
      receiverName: '',
      productName: '',
      status: parts[1] ? 'assigned' : 'pending',
    };
  }).filter(r => r.orderId);

  // invoiceItems에서 정보 보충
  parsed.forEach(p => {
    const match = appState.invoiceItems.find(item => item.orderId === p.orderId);
    if (match) {
      p.receiverName = match.receiverName;
      p.productName = match.productName;
    }
  });

  appState.uploadItems = parsed;
  renderUploadTable();
  showToast(`${parsed.length}건이 파싱되었습니다.`, 'success');
}

function renderUploadTable() {
  const items = appState.uploadItems;
  if (items.length === 0) {
    dom.uploadTbody.innerHTML = '<tr class="empty-row"><td colspan="6">송장번호 데이터를 입력해주세요</td></tr>';
    dom.uploadToCafe24Btn.disabled = true;
    return;
  }

  dom.uploadTbody.innerHTML = items.map((item, i) => `
    <tr>
      <td><input type="checkbox" class="upload-check" data-index="${i}" ${item.trackingNo ? 'checked' : ''} ${!item.trackingNo ? 'disabled' : ''}></td>
      <td>${esc(item.orderId)}</td>
      <td>${esc(item.receiverName)}</td>
      <td title="${esc(item.productName)}">${esc(item.productName)}</td>
      <td>${esc(item.trackingNo)}</td>
      <td><span class="status-tag ${item.status}">${statusLabel(item.status)}</span></td>
    </tr>
  `).join('');

  dom.uploadTbody.querySelectorAll('.upload-check').forEach(cb => {
    cb.addEventListener('change', () => {
      const hasChecked = [...dom.uploadTbody.querySelectorAll('.upload-check')].some(c => c.checked);
      dom.uploadToCafe24Btn.disabled = !hasChecked;
    });
  });

  const hasData = items.some(i => i.trackingNo);
  dom.uploadToCafe24Btn.disabled = !hasData;
  dom.selectAllUpload.checked = false;
}

function toggleSelectAllUpload() {
  const checked = dom.selectAllUpload.checked;
  dom.uploadTbody.querySelectorAll('.upload-check:not(:disabled)').forEach(cb => cb.checked = checked);
  dom.uploadToCafe24Btn.disabled = !checked;
}

// ============================================================
// 카페24 송장 일괄 등록
// ============================================================

async function uploadToCafe24() {
  if (!appState.cafe24.mallId || !appState.cafe24.token) {
    showToast('카페24 설정을 먼저 완료해주세요.', 'error');
    switchTab('settings');
    return;
  }

  const checks = [...dom.uploadTbody.querySelectorAll('.upload-check')];
  const selectedItems = checks
    .filter(c => c.checked)
    .map(c => appState.uploadItems[parseInt(c.dataset.index)])
    .filter(item => item.trackingNo);

  if (selectedItems.length === 0) {
    showToast('등록할 송장이 없습니다.', 'warning');
    return;
  }

  if (!confirm(`${selectedItems.length}건의 송장을 카페24에 등록하시겠습니까?`)) return;

  await ensureValidToken();
  dom.uploadProgress.style.display = 'flex';
  dom.uploadToCafe24Btn.disabled = true;

  let success = 0;
  let fail = 0;

  for (let i = 0; i < selectedItems.length; i++) {
    const item = selectedItems[i];
    dom.uploadProgressBar.style.width = `${((i + 1) / selectedItems.length) * 100}%`;
    dom.uploadProgressText.textContent = `${i + 1}/${selectedItems.length}`;

    try {
      await cafe24UpdateShipping(item.orderId, item.orderItemCode, item.trackingNo);
      item.status = 'registered';
      success++;
    } catch (err) {
      console.error(`송장 등록 실패 [${item.orderId}]:`, err);
      item.status = 'failed';
      fail++;
    }

    // 배송조회 대상에도 추가
    if (item.status === 'registered') {
      const existing = appState.trackingItems.find(t => t.orderId === item.orderId);
      if (!existing) {
        appState.trackingItems.push({ ...item, trackingStatus: '접수', lastUpdate: new Date().toLocaleString() });
      }
    }

    renderUploadTable();

    // API 레이트 리밋 방지 - 약간의 딜레이
    if (i < selectedItems.length - 1) {
      await delay(300);
    }
  }

  dom.uploadProgress.style.display = 'none';
  dom.uploadToCafe24Btn.disabled = false;

  const msg = `등록 완료! 성공: ${success}건` + (fail > 0 ? `, 실패: ${fail}건` : '');
  showToast(msg, fail > 0 ? 'warning' : 'success');
}

async function cafe24UpdateShipping(orderId, orderItemCode, trackingNo) {
  const resp = await fetch(API_PROXY, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action: 'update_shipping',
      mallId: appState.cafe24.mallId,
      token: appState.cafe24.token,
      orderId,
      orderItemCode,
      trackingNo,
    }),
  });

  const data = await resp.json().catch(() => ({}));

  // API 응답 내 에러 확인 (200이라도 에러가 있을 수 있음)
  if (data.error) {
    const code = data.error.code;
    const msg = data.error.message || '';
    if (msg.includes('insufficient_scope')) {
      throw new Error('권한 부족: 카페24 앱에 "주문 쓰기(mall.write_order)" 권한을 추가하고 다시 인증하세요.');
    }
    if (code === 404) {
      throw new Error(`API를 찾을 수 없습니다 (404). 주문번호를 확인하세요: ${orderId}`);
    }
    throw new Error(msg || `API 에러 (코드: ${code})`);
  }

  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}`);
  }

  return data;
}

// ============================================================
// 배송 조회
// ============================================================

async function trackSingle() {
  const trackingNo = dom.trackingInput.value.trim();
  if (!trackingNo) {
    showToast('송장번호를 입력해주세요.', 'warning');
    return;
  }

  showLoading('배송 정보 조회 중...');
  try {
    const info = await getTrackingInfo(trackingNo);
    appState.trackingItems = [{ orderId: '-', trackingNo, receiverName: '-', trackingStatus: info.status, lastUpdate: info.lastUpdate, location: info.location }];
    renderTrackingTable();
    showToast('배송 정보를 조회했습니다.', 'success');
  } catch (err) {
    showToast(`배송 조회 실패: ${err.message}`, 'error');
  } finally {
    hideLoading();
  }
}

async function trackAll() {
  // invoiceItems + uploadItems에서 송장번호가 있는 항목들 조회
  const allItems = [...appState.invoiceItems, ...appState.uploadItems]
    .filter(item => item.trackingNo)
    .reduce((acc, item) => {
      if (!acc.find(a => a.trackingNo === item.trackingNo)) acc.push(item);
      return acc;
    }, []);

  if (allItems.length === 0) {
    showToast('조회할 송장번호가 없습니다.', 'warning');
    return;
  }

  showLoading(`${allItems.length}건 배송 조회 중...`);

  try {
    const trackingNumbers = allItems.map(item => item.trackingNo);
    const trackingMap = await getTrackingInfoBatch(trackingNumbers);

    const results = allItems.map(item => {
      const info = trackingMap[item.trackingNo] || {};
      return {
        ...item,
        trackingStatus: info.status || '조회중',
        lastUpdate: info.lastUpdate || '-',
        location: info.location || '',
        trackingDetails: info.details || [],
      };
    });

    appState.trackingItems = results;
    renderTrackingTable();
    showToast(`${results.length}건 조회 완료`, 'success');
  } catch (err) {
    showToast(`배송 조회 실패: ${err.message}`, 'error');
  } finally {
    hideLoading();
  }
}

async function getTrackingInfoBatch(trackingNumbers) {
  // 로젠택배 공식 Open API (서버 프록시 경유)
  const resp = await fetch(LOGEN_PROXY, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      trackingNumbers,
      customerId: appState.logen?.customerId || '33253401',
    }),
  });

  const result = await resp.json();
  if (result.error) throw new Error(result.error);

  // API 응답을 송장번호별 맵으로 변환
  const map = {};
  if (result.data && Array.isArray(result.data)) {
    for (const item of result.data) {
      const no = item.slipNo || item.SLIP_NO || '';
      map[no] = {
        status: item.sttsNm || item.STTS_NM || '조회중',
        lastUpdate: item.scanDt || item.SCAN_DT || '-',
        location: item.brnNm || item.BRN_NM || '',
        details: [],
      };
    }
  }
  return map;
}

async function getTrackingInfo(trackingNo) {
  const map = await getTrackingInfoBatch([trackingNo]);
  return map[trackingNo] || { status: '조회중', lastUpdate: '-', details: [] };
}

function generateDemoTracking(trackingNo) {
  const statuses = ['집하', '간선상차', '간선하차', '배달출발', '배달완료'];
  const locations = ['서울 강남 집하장', '서울 허브터미널', '경기 수원 터미널', '수원 영통 배달소', '배달완료'];
  const randomIdx = Math.floor(Math.random() * statuses.length);
  const now = new Date();

  const details = [];
  for (let i = randomIdx; i >= 0; i--) {
    const d = new Date(now);
    d.setHours(d.getHours() - (randomIdx - i) * 4);
    details.push({
      date: d.toLocaleString('ko-KR'),
      location: locations[i],
      status: statuses[i],
      description: `${locations[i]}에서 ${statuses[i]}`,
    });
  }

  return {
    orderId: '-',
    trackingNo,
    receiverName: '데모 수령인',
    trackingStatus: statuses[randomIdx],
    lastUpdate: details[0]?.date || '-',
    trackingDetails: details,
  };
}

function renderTrackingTable() {
  const items = appState.trackingItems;
  if (items.length === 0) {
    dom.trackingTbody.innerHTML = '<tr class="empty-row"><td colspan="6">송장번호를 입력하거나 \'전체 배송현황 조회\' 버튼을 클릭하세요</td></tr>';
    return;
  }

  dom.trackingTbody.innerHTML = items.map((item, i) => {
    const statusClass = getTrackingStatusClass(item.trackingStatus);
    return `
    <tr>
      <td>${esc(item.orderId || '-')}</td>
      <td>${esc(item.trackingNo)}</td>
      <td>${esc(item.receiverName || item.location || '-')}</td>
      <td><span class="status-tag ${statusClass}">${esc(item.trackingStatus || '조회중')}</span></td>
      <td>${esc(item.lastUpdate || '-')}</td>
      <td><button class="secondary-btn" onclick="showTrackingDetail(${i})">상세</button></td>
    </tr>`;
  }).join('');
}

function getTrackingStatusClass(status) {
  if (!status) return 'pending';
  if (status.includes('완료') || status.includes('배달완료')) return 'delivered';
  if (status.includes('배달출발') || status.includes('배송중')) return 'in-transit';
  if (status.includes('간선') || status.includes('집하')) return 'assigned';
  return 'pending';
}

function showTrackingDetail(index) {
  const item = appState.trackingItems[index];
  const details = item.trackingDetails || [];

  let html = `
    <div style="margin-bottom:1rem">
      <strong>송장번호:</strong> ${esc(item.trackingNo)}<br>
      <strong>수령인:</strong> ${esc(item.receiverName || '-')}<br>
      <strong>현재 상태:</strong> ${esc(item.trackingStatus || '-')}
    </div>
  `;

  if (details.length > 0) {
    html += '<div class="tracking-timeline">';
    details.forEach(d => {
      html += `
        <div class="timeline-item">
          <div class="time">${esc(d.date)}</div>
          <div class="location">${esc(d.location)}</div>
          <div class="description">${esc(d.description || d.status)}</div>
        </div>`;
    });
    html += '</div>';
  } else {
    html += '<p style="color:var(--text-secondary)">상세 배송 이력이 없습니다.</p>';
  }

  dom.trackingDetail.innerHTML = html;
  dom.trackingModal.style.display = 'flex';
}

// ============================================================
// 데모 데이터 생성
// ============================================================

function generateDemoOrders() {
  const names = ['김민수', '이영희', '박지성', '최유리', '정대현', '한소희', '강동원', '윤서연', '임재범', '오승환'];
  const products = [
    '프리미엄 스킨케어 세트', '유기농 그래놀라 3종', '블루투스 이어폰', '실크 파자마 세트',
    '텀블러 500ml', '아로마 캔들 (라벤더)', '가죽 지갑', '스마트워치 밴드',
    '요가 매트', '핸드크림 세트'
  ];
  const addrs = [
    '서울특별시 강남구 역삼동 123-45', '경기도 성남시 분당구 판교역로 200',
    '부산광역시 해운대구 해운대로 456', '인천광역시 남동구 인하로 789',
    '대전광역시 유성구 대학로 100', '대구광역시 수성구 수성로 300',
    '광주광역시 서구 상무대로 555', '울산광역시 남구 삼산동 111',
    '경기도 수원시 영통구 영통로 222', '서울특별시 마포구 홍대입구로 333',
  ];
  const zips = ['06236', '13524', '48094', '21556', '34134', '42188', '61945', '44677', '16499', '04032'];

  const orders = [];
  const today = new Date();

  for (let i = 0; i < 10; i++) {
    const orderDate = new Date(today);
    orderDate.setDate(orderDate.getDate() - Math.floor(Math.random() * 5));
    const orderId = `${formatDate(orderDate).replace(/-/g, '')}-${String(i + 1).padStart(4, '0')}`;

    orders.push({
      orderId,
      orderDate: orderDate.toISOString(),
      orderItemCode: `item_${orderId}`,
      productName: products[i],
      quantity: Math.floor(Math.random() * 3) + 1,
      receiverName: names[i],
      receiverTel: `010-${String(Math.floor(Math.random() * 9000) + 1000)}-${String(Math.floor(Math.random() * 9000) + 1000)}`,
      receiverAddr: addrs[i],
      receiverZipcode: zips[i],
      shippingMessage: i % 3 === 0 ? '부재시 문 앞에 놓아주세요' : (i % 3 === 1 ? '경비실에 맡겨주세요' : ''),
      trackingNo: '',
      status: 'pending',
    });
  }

  return orders;
}

// ============================================================
// Utility Functions
// ============================================================

function switchTab(tabName) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  const btn = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
  if (btn) btn.classList.add('active');
  const content = document.getElementById(`tab-${tabName}`);
  if (content) content.classList.add('active');
}

function formatDate(date) {
  const d = new Date(date);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function formatDateTime(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  return `${formatDate(d)} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

function esc(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}

function statusLabel(status) {
  const labels = {
    pending: '대기',
    assigned: '발급완료',
    registered: '등록완료',
    failed: '실패',
  };
  return labels[status] || status;
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function readFileAsArrayBuffer(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsArrayBuffer(file);
  });
}

function showLoading(text) {
  dom.loadingText.textContent = text || '처리 중...';
  dom.loadingOverlay.style.display = 'flex';
}

function hideLoading() {
  dom.loadingOverlay.style.display = 'none';
}

function showToast(message, type = 'info') {
  const icons = { success: '\u2705', error: '\u274C', warning: '\u26A0\uFE0F', info: '\u2139\uFE0F' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || ''}</span><span>${esc(message)}</span>`;
  dom.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'slideOut 0.3s ease forwards';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ============================================================
// Initialize
// ============================================================
document.addEventListener('DOMContentLoaded', init);
