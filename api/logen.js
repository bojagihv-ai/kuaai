// Vercel Serverless Function - 로젠택배 배송조회 Proxy
// tracker.delivery API 사용 (CORS 우회)

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    const { trackingNumbers } = req.method === 'POST' ? req.body : req.query;

    if (!trackingNumbers || !Array.isArray(trackingNumbers) || trackingNumbers.length === 0) {
      return res.status(400).json({ error: '송장번호가 필요합니다.' });
    }

    // 각 송장번호별로 tracker.delivery API 호출
    const results = {};

    await Promise.all(
      trackingNumbers.map(async (no) => {
        try {
          const resp = await fetch(
            `https://apis.tracker.delivery/carriers/kr.logen/tracks/${encodeURIComponent(no)}`,
            {
              headers: { 'Accept': 'application/json' },
              signal: AbortSignal.timeout(8000),
            }
          );
          const data = await resp.json();

          if (data.message) {
            // 조회 불가 (아직 스캔 전)
            results[no] = { status: '배송준비', lastUpdate: '-', location: '', events: [] };
          } else {
            // 정상 응답 - 이벤트 기반 데이터
            const events = (data.events || data.progresses || []).map(e => ({
              time: e.time || e.timeString || '',
              status: e.status?.name || e.description || '',
              location: e.location?.name || '',
            }));
            const last = events[events.length - 1] || {};
            results[no] = {
              status: last.status || '조회중',
              lastUpdate: last.time || '-',
              location: last.location || '',
              events,
            };
          }
        } catch {
          results[no] = { status: '배송준비', lastUpdate: '-', location: '', events: [] };
        }
      })
    );

    return res.status(200).json({ data: results });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
}
