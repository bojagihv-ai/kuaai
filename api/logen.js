// Vercel Serverless Function - 로젠택배 배송조회 API Proxy
// CORS 우회를 위한 서버사이드 프록시

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    const { trackingNumbers, customerId } = req.method === 'POST' ? req.body : req.query;

    if (!trackingNumbers || !Array.isArray(trackingNumbers) || trackingNumbers.length === 0) {
      return res.status(400).json({ error: '송장번호가 필요합니다.' });
    }

    // 로젠택배 공식 Open API - 화물추적 최종상태 조회
    const body = {
      userId: customerId || '33253401',
      data: trackingNumbers.map(no => ({ slipNo: String(no) })),
    };

    const resp = await fetch(
      'https://openapi.ilogen.com/lrm02b-edi/edi/inquiryCargoTrackingMultiLast',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }
    );

    const data = await resp.json();
    return res.status(resp.status).json(data);
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
}
