/* ─── 코인 자동매매 봇 - Frontend JS ─────────────────────────────────────── */
const API = '';  // same origin
let ws = null;
let priceChart = null;
let volumeChart = null;
let refreshInterval = null;
let kimchiGaugeCtx = null;

// ─── Init ────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  initWebSocket();
  initCharts();
  initKimchiGauge();
  loadStatus();
  loadTrades();
  loadPnl();

  // Auto-refresh every 30s
  refreshInterval = setInterval(() => {
    refreshTickerData();
    loadKimchi();
    loadFundingRate();
    loadPnl();
  }, 30000);

  // Initial load
  refreshTickerData();
  refreshChart();
  loadKimchi();
  loadFundingRate();
});

// ─── WebSocket ────────────────────────────────────────────────────────────────
function initWebSocket() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws`);

  ws.onopen = () => {
    setEl('ws-status', '● WS 연결됨', 'badge badge-on');
    // keepalive ping every 20s
    setInterval(() => ws.readyState === 1 && ws.send('ping'), 20000);
  };

  ws.onclose = () => setEl('ws-status', 'WS 끊김', 'badge badge-off');
  ws.onerror = () => setEl('ws-status', 'WS 오류', 'badge badge-off');

  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      handleWsMessage(msg);
    } catch(e) {}
  };
}

function handleWsMessage(msg) {
  switch(msg.type) {
    case 'analysis':
      updateIndicators(msg.data);
      break;
    case 'kimchi':
      updateKimchiDisplay(msg.data);
      break;
    case 'trade':
      loadTrades();
      loadPnl();
      toast(`${msg.data.side.toUpperCase()} 체결! ${fmt(msg.data.price)}원`, msg.data.side === 'buy' ? 'green' : 'red');
      break;
    case 'error':
      toast('봇 오류: ' + msg.data.message, 'red');
      break;
  }
}

// ─── Chart ────────────────────────────────────────────────────────────────────
function initCharts() {
  Chart.defaults.color = '#8892a4';
  Chart.defaults.borderColor = '#2a2f45';

  const priceCtx = document.getElementById('price-chart').getContext('2d');
  priceChart = new Chart(priceCtx, {
    type: 'line',
    data: { labels: [], datasets: [
      { label: '종가', data: [], borderColor: '#4e8ef7', borderWidth: 2, pointRadius: 0, tension: 0.1, fill: false },
      { label: 'EMA20', data: [], borderColor: '#f5c842', borderWidth: 1.5, pointRadius: 0, tension: 0, fill: false, borderDash: [] },
      { label: 'BB상단', data: [], borderColor: 'rgba(255,75,110,.5)', borderWidth: 1, pointRadius: 0, fill: false },
      { label: 'BB하단', data: [], borderColor: 'rgba(0,208,132,.5)', borderWidth: 1, pointRadius: 0, fill: false },
    ]},
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      plugins: { legend: { display: true, position: 'top', labels: { boxWidth: 12, font: { size: 11 } } } },
      scales: {
        x: { grid: { color: '#2a2f45' }, ticks: { maxTicksLimit: 8, font: { size: 10 } } },
        y: { position: 'right', grid: { color: '#2a2f45' }, ticks: { callback: v => fmtShort(v) } },
      },
    },
  });

  const volCtx = document.getElementById('volume-chart').getContext('2d');
  volumeChart = new Chart(volCtx, {
    type: 'bar',
    data: { labels: [], datasets: [{ label: '거래량', data: [], backgroundColor: 'rgba(78,142,247,.4)', borderWidth: 0 }] },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { display: false },
        y: { position: 'right', grid: { color: '#2a2f45' }, ticks: { maxTicksLimit: 3, callback: v => fmtShort(v) } },
      },
    },
  });
}

async function refreshChart() {
  const exchange = val('chart-exchange');
  const symbol = val('chart-symbol');
  const interval = val('chart-interval');

  try {
    const [ohlcvRes, analysisRes] = await Promise.all([
      fetch(`${API}/api/ohlcv?symbol=${symbol}&interval=${interval}&limit=100&exchange=${exchange}`).then(r => r.json()),
      fetch(`${API}/api/analysis?symbol=${symbol}&interval=${interval}&exchange=${exchange}`).then(r => r.json()),
    ]);

    const data = ohlcvRes.data || [];
    const labels = data.map(d => tsLabel(d[0]));
    const closes = data.map(d => d[4]);
    const volumes = data.map(d => d[5]);

    // Compute BB and EMA20 for chart
    const ema20 = computeEMA(closes, 20);
    const bb = computeBB(closes, 20);

    priceChart.data.labels = labels;
    priceChart.data.datasets[0].data = closes;
    priceChart.data.datasets[1].data = ema20;
    priceChart.data.datasets[2].data = bb.upper;
    priceChart.data.datasets[3].data = bb.lower;
    priceChart.update('none');

    volumeChart.data.labels = labels;
    volumeChart.data.datasets[0].data = volumes;
    volumeChart.data.datasets[0].backgroundColor = closes.map((c, i) =>
      i === 0 ? 'rgba(78,142,247,.4)' : c >= (closes[i-1]||c) ? 'rgba(0,208,132,.4)' : 'rgba(255,75,110,.4)'
    );
    volumeChart.update('none');

    if (!analysisRes.error) updateIndicators(analysisRes);

  } catch(e) {
    console.error('Chart refresh error:', e);
  }
}

// ─── Ticker ───────────────────────────────────────────────────────────────────
async function refreshTickerData() {
  try {
    const [upbit, bybit] = await Promise.all([
      fetch(`${API}/api/ticker?symbol=KRW-BTC&exchange=upbit`).then(r => r.json()),
      fetch(`${API}/api/ticker?symbol=BTCUSDT&exchange=bybit`).then(r => r.json()),
    ]);

    el('upbit-price').textContent = fmt(upbit.price) + ' KRW';
    const upbitChg = upbit.change_24h || 0;
    el('upbit-change').textContent = (upbitChg >= 0 ? '+' : '') + upbitChg.toFixed(2) + '%';
    el('upbit-change').className = 'ticker-change ' + (upbitChg >= 0 ? 'up' : 'down');

    el('bybit-price').textContent = '$' + fmt(bybit.price);
    const bybitChg = bybit.change_24h || 0;
    el('bybit-change').textContent = (bybitChg >= 0 ? '+' : '') + bybitChg.toFixed(2) + '%';
    el('bybit-change').className = 'ticker-change ' + (bybitChg >= 0 ? 'up' : 'down');

  } catch(e) { console.warn('Ticker error:', e); }
}

// ─── Kimchi premium ────────────────────────────────────────────────────────────
async function loadKimchi() {
  try {
    const d = await fetch(`${API}/api/kimchi`).then(r => r.json());
    updateKimchiDisplay(d);
  } catch(e) { console.warn('Kimchi error:', e); }
}

function updateKimchiDisplay(d) {
  if (!d || d.error) return;

  const pct = d.kimchi_pct ?? d.kimchi_premium_pct ?? 0;
  const net = d.net_profit_pct ?? 0;

  el('kimchi-pct').textContent = (pct >= 0 ? '+' : '') + pct.toFixed(3) + '%';
  el('kimchi-pct').className = 'ticker-price ' + (pct >= 0 ? 'green' : 'red');
  el('kimchi-net').textContent = '수수료 후: ' + (net >= 0 ? '+' : '') + net.toFixed(3) + '%';
  el('kimchi-net').className = 'ticker-change ' + (net >= 0 ? 'up' : 'down');

  el('usd-krw').textContent = fmt(d.usd_krw ?? d.usd_krw_rate) + ' ₩';

  el('kd-upbit').textContent = fmt(d.upbit_price ?? d.upbit_price_krw) + ' ₩';
  el('kd-bybit-krw').textContent = fmt(d.bybit_price_krw) + ' ₩';
  el('kd-kimchi').textContent = (pct >= 0 ? '+' : '') + pct.toFixed(4) + '%';
  el('kd-net').textContent = (net >= 0 ? '+' : '') + net.toFixed(4) + '%';
  el('kd-dir').textContent = d.direction === 'kimchi_buy_bybit' ? '바이비트 매수 / 업비트 매도' : '업비트 매수 / 바이비트 숏';

  drawKimchiGauge(pct);

  const minProfit = parseFloat(val('arb-min-profit') || 0.3);
  const amount = parseFloat(val('arb-amount') || 1000000);
  if (d.is_profitable) {
    const profitInfo = el('arb-profit-info');
    profitInfo.classList.remove('hidden');
    profitInfo.innerHTML = `💰 차익 기회! 예상 순수익: <strong class="green">${(amount * net / 100).toLocaleString()}원</strong> (${net.toFixed(3)}%)`;
  } else {
    el('arb-profit-info').classList.add('hidden');
  }
}

// ─── Kimchi gauge canvas ──────────────────────────────────────────────────────
function initKimchiGauge() {
  kimchiGaugeCtx = document.getElementById('kimchi-gauge').getContext('2d');
  drawKimchiGauge(0);
}

function drawKimchiGauge(pct) {
  if (!kimchiGaugeCtx) return;
  const ctx = kimchiGaugeCtx;
  const w = 200, h = 110, cx = w / 2, cy = h - 10, r = 80;

  ctx.clearRect(0, 0, w, h);

  // Arc background
  const grad = ctx.createLinearGradient(0, 0, w, 0);
  grad.addColorStop(0, '#ff4b6e');
  grad.addColorStop(0.5, '#555');
  grad.addColorStop(1, '#00d084');

  ctx.beginPath();
  ctx.arc(cx, cy, r, Math.PI, 0, false);
  ctx.strokeStyle = grad;
  ctx.lineWidth = 14;
  ctx.lineCap = 'round';
  ctx.stroke();

  // Needle
  const clamp = Math.max(-5, Math.min(5, pct));
  const angle = Math.PI + (clamp / 10) * Math.PI;
  const nx = cx + (r - 7) * Math.cos(angle);
  const ny = cy + (r - 7) * Math.sin(angle);

  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.lineTo(nx, ny);
  ctx.strokeStyle = '#fff';
  ctx.lineWidth = 3;
  ctx.stroke();

  // Center dot
  ctx.beginPath();
  ctx.arc(cx, cy, 5, 0, Math.PI * 2);
  ctx.fillStyle = '#fff';
  ctx.fill();

  // Labels
  ctx.fillStyle = '#ff4b6e';
  ctx.font = '10px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('-5%', cx - r + 5, cy + 18);
  ctx.fillStyle = '#00d084';
  ctx.fillText('+5%', cx + r - 5, cy + 18);

  ctx.fillStyle = pct >= 0 ? '#00d084' : '#ff4b6e';
  ctx.font = 'bold 16px sans-serif';
  ctx.fillText((pct >= 0 ? '+' : '') + pct.toFixed(2) + '%', cx, cy - 20);
}

// ─── Funding rate ─────────────────────────────────────────────────────────────
async function loadFundingRate() {
  try {
    const d = await fetch(`${API}/api/funding-rate`).then(r => r.json());
    if (d.error) return;
    const sign = d.rate >= 0 ? '+' : '';
    el('funding-rate').textContent = sign + (d.rate_pct || 0).toFixed(4) + '%';
    el('funding-rate').className = 'ticker-price ' + (d.rate >= 0 ? 'green' : 'red');
    const nextDate = d.next_funding ? new Date(d.next_funding * 1000) : null;
    el('funding-next').textContent = nextDate ? '다음: ' + nextDate.toLocaleTimeString('ko-KR', {hour:'2-digit', minute:'2-digit'}) : '';
  } catch(e) {}
}

// ─── Analysis indicators ──────────────────────────────────────────────────────
async function runAnalysis() {
  const symbol = val('chart-symbol');
  const interval = val('chart-interval');
  const exchange = val('chart-exchange');
  try {
    const d = await fetch(`${API}/api/analysis?symbol=${symbol}&interval=${interval}&exchange=${exchange}`).then(r => r.json());
    updateIndicators(d);
    toast('분석 완료!', 'green');
  } catch(e) { toast('분석 실패: ' + e.message, 'red'); }
}

function updateIndicators(d) {
  if (!d || d.error) return;
  const ind = d.indicators || {};

  setText('ind-rsi', fmtN(ind.rsi), rsiColor(ind.rsi));
  setText('ind-macd', fmtN(ind.macd, 2));
  setText('ind-macd-hist', fmtN(ind.macd_hist, 2), ind.macd_hist > 0 ? 'ind-val green' : 'ind-val red');
  setText('ind-bb-upper', fmt(ind.bb_upper));
  setText('ind-bb-mid', fmt(ind.bb_mid));
  setText('ind-bb-lower', fmt(ind.bb_lower));
  setText('ind-ema5', fmt(ind.ema5));
  setText('ind-ema20', fmt(ind.ema20));
  setText('ind-ema60', fmt(ind.ema60));
  setText('ind-stoch-k', fmtN(ind.stoch_k), stochColor(ind.stoch_k));
  setText('ind-stoch-d', fmtN(ind.stoch_d));
  setText('ind-vol-ratio', fmtN(ind.volume_ratio, 1) + 'x', ind.volume_ratio > 2 ? 'ind-val yellow' : 'ind-val');
  setText('ind-atr', fmt(ind.atr));
  setText('ind-trend', trendText(d.trend));

  // Score bar
  const score = d.score || 0;
  const pct = ((score + 100) / 200 * 100).toFixed(1);
  el('score-fill').style.left = `calc(${pct}% - 6px)`;
  el('score-val').textContent = (score >= 0 ? '+' : '') + score.toFixed(0);

  // Signal badge
  const sigEl = el('signal-badge');
  if (d.signal === 'buy')  { sigEl.textContent = '📈 매수'; sigEl.className = 'badge badge-buy'; }
  else if (d.signal === 'sell') { sigEl.textContent = '📉 매도'; sigEl.className = 'badge badge-sell'; }
  else { sigEl.textContent = '⏸ 관망'; sigEl.className = 'badge badge-hold'; }

  // Recommendation
  const rec = d.recommendation || d;
  if (rec) {
    el('rec-action').textContent = rec.action === 'buy' ? '✅ 매수 추천' : rec.action === 'sell' ? '🔴 매도 추천' : '⏸ 관망';
    el('rec-reasons').textContent = (rec.reasons || []).join(' · ');
  }
}

// ─── Arbitrage config ─────────────────────────────────────────────────────────
async function updateArbitrageConfig() {
  const cfg = {
    min_profit_pct: parseFloat(val('arb-min-profit')) || 0.3,
    trade_amount_krw: parseFloat(val('arb-amount')) || 1000000,
    auto_trade: el('arb-auto').checked,
  };
  try {
    await fetch(`${API}/api/kimchi/config`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(cfg) });
    toast(cfg.auto_trade ? '자동 차익거래 활성화!' : '자동 차익거래 비활성화', cfg.auto_trade ? 'green' : 'yellow');
  } catch(e) { toast('설정 저장 실패', 'red'); }
}

// ─── Strategy config ──────────────────────────────────────────────────────────
async function saveAutoConfig() {
  const cfg = {
    symbol: val('auto-symbol'),
    interval: val('auto-interval'),
    base_invest_ratio: parseFloat(val('auto-base-ratio')) / 100,
    max_invest_ratio: parseFloat(val('auto-max-ratio')) / 100,
    stop_loss_pct: parseFloat(val('auto-stoploss')),
    take_profit_pct: parseFloat(val('auto-takeprofit')),
    trailing_stop_pct: parseFloat(val('auto-trailing')),
    min_score_buy: parseFloat(val('auto-buy-score')),
    max_score_sell: parseFloat(val('auto-sell-score')),
    trade_cooldown: parseInt(val('auto-cooldown')),
  };
  try {
    await fetch(`${API}/api/strategy/auto/config`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(cfg) });
    toast('자동 전략 저장됨!', 'green');
  } catch(e) { toast('저장 실패', 'red'); }
}

async function saveUserConfig() {
  const cfg = {
    name: '내 전략',
    buy_rsi_below: parseFloat(val('u-buy-rsi')),
    buy_macd_cross: el('u-buy-macd').checked,
    buy_bb_below: el('u-buy-bb').checked,
    buy_score_threshold: parseFloat(val('u-buy-score')),
    sell_rsi_above: parseFloat(val('u-sell-rsi')),
    sell_macd_cross: el('u-sell-macd').checked,
    stop_loss_pct: parseFloat(val('u-stoploss')),
    take_profit_pct: parseFloat(val('u-takeprofit')),
    use_trailing_stop: true,
    trailing_stop_pct: parseFloat(val('u-trailing')),
    base_invest_ratio: parseFloat(val('u-base-ratio')) / 100,
    max_total_ratio: parseFloat(val('u-max-ratio')) / 100,
    dca_levels: [
      {drop_pct: 3,  invest_ratio: 0.05},
      {drop_pct: 5,  invest_ratio: 0.10},
      {drop_pct: 8,  invest_ratio: 0.15},
      {drop_pct: 12, invest_ratio: 0.20},
    ],
    trade_cooldown_sec: 300,
    interval: '15m',
  };
  try {
    await fetch(`${API}/api/strategy/user/config`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(cfg) });
    toast('사용자 전략 저장됨!', 'green');
  } catch(e) { toast('저장 실패', 'red'); }
}

// ─── Bot control ──────────────────────────────────────────────────────────────
async function startBot() {
  const seed = parseFloat(val('seed-krw')) || 1000000;
  try {
    const d = await fetch(`${API}/api/bot/start?seed_krw=${seed}`, { method: 'POST' }).then(r => r.json());
    el('start-btn').disabled = true;
    el('stop-btn').disabled = false;
    setEl('bot-status', '● 봇 실행중', 'badge badge-on');
    toast(d.dry_run ? '봇 시작 (모의거래)' : '봇 시작 (실거래!)', d.dry_run ? 'yellow' : 'green');
  } catch(e) { toast('봇 시작 실패: ' + e.message, 'red'); }
}

async function stopBot() {
  try {
    await fetch(`${API}/api/bot/stop`, { method: 'POST' });
    el('start-btn').disabled = false;
    el('stop-btn').disabled = true;
    setEl('bot-status', '봇 정지', 'badge badge-off');
    toast('봇 정지됨', 'yellow');
  } catch(e) {}
}

function toggleRealMode() {
  const isReal = el('real-mode').checked;
  const badge = el('dry-run-badge');
  if (isReal) {
    badge.textContent = '⚠ 실거래';
    badge.className = 'badge badge-off';
    if (!confirm('실거래 모드로 전환합니다. 실제 자금이 사용됩니다. 계속할까요?')) {
      el('real-mode').checked = false;
      badge.textContent = '모의거래';
      badge.className = 'badge badge-warn';
    }
  } else {
    badge.textContent = '모의거래';
    badge.className = 'badge badge-warn';
  }
}

// ─── Trades & PnL ─────────────────────────────────────────────────────────────
async function loadTrades() {
  try {
    const trades = await fetch(`${API}/api/trades?limit=30`).then(r => r.json());
    const log = el('trade-log');
    if (!trades.length) { log.innerHTML = '<div class="trade-log-empty">거래 내역이 없습니다.</div>'; return; }
    log.innerHTML = trades.map(t => `
      <div class="trade-item ${t.side}">
        <span class="ti-side ${t.side}">${t.side === 'buy' ? '매수' : '매도'}</span>
        <span class="ti-price">${fmt(t.price)}₩</span>
        <span>${fmtN(t.qty, 6)} BTC</span>
        <span>${fmt(t.amount_krw)}₩</span>
        ${t.pnl ? `<span class="ti-pnl ${t.pnl > 0 ? 'pos' : 'neg'}">${t.pnl > 0 ? '+' : ''}${fmt(t.pnl)}₩</span>` : '<span></span>'}
        <span class="ti-time">${tsToStr(t.timestamp)}</span>
        ${t.dry_run ? '<span style="color:#f5c842;font-size:10px">모의</span>' : '<span style="color:#00d084;font-size:10px">실거래</span>'}
      </div>
    `).join('');
  } catch(e) {}
}

async function loadPnl() {
  try {
    const d = await fetch(`${API}/api/pnl`).then(r => r.json());
    el('pnl-total').textContent = d.total_trades || 0;
    el('pnl-wins').textContent = d.wins || 0;
    el('pnl-losses').textContent = d.losses || 0;
    el('pnl-winrate').textContent = (d.win_rate || 0).toFixed(1) + '%';
    const netPnl = d.net_pnl || 0;
    el('pnl-net').textContent = (netPnl >= 0 ? '+' : '') + fmt(netPnl) + '₩';
    el('pnl-net').className = netPnl >= 0 ? 'green' : 'red';
    el('pnl-arb').textContent = '+' + fmt(d.arb_profit || 0) + '₩';
  } catch(e) {}
}

// ─── Setup modal ──────────────────────────────────────────────────────────────
async function saveSetup() {
  const cfg = {
    upbit_key: val('upbit-key'),
    upbit_secret: val('upbit-secret'),
    bybit_key: val('bybit-key'),
    bybit_secret: val('bybit-secret'),
    dry_run: el('modal-dry-run').checked,
  };
  const msg = el('setup-msg');
  try {
    const d = await fetch(`${API}/api/setup`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(cfg) }).then(r => r.json());
    msg.textContent = '✅ 연결됨 | ' + (d.dry_run ? '모의거래 모드' : '실거래 모드');
    msg.className = 'msg success';
    msg.classList.remove('hidden');
    toast('API 연결 완료!', 'green');
    setTimeout(() => closeModal('setup-modal'), 1500);
  } catch(e) {
    msg.textContent = '❌ 연결 실패: ' + e.message;
    msg.className = 'msg error';
    msg.classList.remove('hidden');
  }
}

async function loadStatus() {
  try {
    const d = await fetch(`${API}/api/status`).then(r => r.json());
    if (d.bot_running) {
      el('start-btn').disabled = true;
      el('stop-btn').disabled = false;
      setEl('bot-status', '● 봇 실행중', 'badge badge-on');
    }
    if (!d.dry_run) {
      el('dry-run-badge').textContent = '⚠ 실거래';
      el('dry-run-badge').className = 'badge badge-off';
    }
  } catch(e) {}
}

// ─── Tab switching ────────────────────────────────────────────────────────────
function switchTab(tab) {
  ['auto', 'user'].forEach(t => {
    el(t + '-tab').classList.toggle('hidden', t !== tab);
  });
  document.querySelectorAll('.tab-btn').forEach((btn, i) => {
    btn.classList.toggle('active', (i === 0 && tab === 'auto') || (i === 1 && tab === 'user'));
  });
}

// ─── Modal ────────────────────────────────────────────────────────────────────
function openModal(id)  { el(id).classList.remove('hidden'); }
function closeModal(id) { el(id).classList.add('hidden'); }

// ─── Toast ────────────────────────────────────────────────────────────────────
let toastTimer = null;
function toast(msg, type = 'green') {
  const t = el('toast');
  t.textContent = msg;
  t.style.borderLeftColor = type === 'green' ? 'var(--green)' : type === 'red' ? 'var(--red)' : 'var(--yellow)';
  t.classList.remove('hidden');
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add('hidden'), 3000);
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
const el = id => document.getElementById(id);
const val = id => (el(id) || {}).value || '';

function setEl(id, text, cls) {
  const e = el(id);
  if (!e) return;
  e.textContent = text;
  if (cls) e.className = cls;
}

function setText(id, text, cls) {
  const e = el(id);
  if (!e) return;
  e.textContent = text;
  if (cls) e.className = cls;
}

function fmt(n) {
  if (n == null || isNaN(n)) return '—';
  return Math.round(n).toLocaleString('ko-KR');
}
function fmtShort(n) {
  if (n >= 1e8) return (n/1e8).toFixed(1) + '억';
  if (n >= 1e4) return (n/1e4).toFixed(0) + '만';
  return n.toFixed(0);
}
function fmtN(n, dec = 2) {
  if (n == null || isNaN(n)) return '—';
  return Number(n).toFixed(dec);
}

function tsLabel(ts) {
  const s = String(ts);
  if (s.length === 14) return s.substring(8, 10) + ':' + s.substring(10, 12);
  return new Date(ts).toLocaleTimeString('ko-KR', {hour:'2-digit', minute:'2-digit'});
}
function tsToStr(ts) {
  return new Date(ts * 1000).toLocaleString('ko-KR', {month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit'});
}

function rsiColor(v) {
  if (v < 30) return 'ind-val green';
  if (v > 70) return 'ind-val red';
  return 'ind-val';
}
function stochColor(v) {
  if (v < 20) return 'ind-val green';
  if (v > 80) return 'ind-val red';
  return 'ind-val';
}
function trendText(t) {
  return { strong_up: '🚀 강한 상승', up: '📈 상승', sideways: '➡ 횡보', down: '📉 하락', strong_down: '💥 강한 하락' }[t] || t;
}

// ─── Math helpers for chart ────────────────────────────────────────────────────
function computeEMA(arr, period) {
  const k = 2 / (period + 1);
  const result = [];
  let ema = arr[0];
  for (let i = 0; i < arr.length; i++) {
    if (i === 0) { result.push(null); continue; }
    ema = arr[i] * k + ema * (1 - k);
    result.push(i >= period ? ema : null);
  }
  return result;
}
function computeBB(arr, period, mult = 2) {
  const upper = [], lower = [];
  for (let i = 0; i < arr.length; i++) {
    if (i < period - 1) { upper.push(null); lower.push(null); continue; }
    const slice = arr.slice(i - period + 1, i + 1);
    const mean = slice.reduce((a,b) => a+b, 0) / period;
    const std = Math.sqrt(slice.reduce((s,v) => s + (v-mean)**2, 0) / period);
    upper.push(mean + mult * std);
    lower.push(mean - mult * std);
  }
  return { upper, lower };
}
