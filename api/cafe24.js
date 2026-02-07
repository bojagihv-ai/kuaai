// Vercel Serverless Function - Cafe24 API Proxy
// 브라우저 CORS 차단을 우회하기 위한 서버사이드 프록시

export default async function handler(req, res) {
  // CORS 헤더 설정
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    const { action, mallId, token, clientId, clientSecret, refreshToken, ...params } =
      req.method === 'POST' ? req.body : req.query;

    // --- 토큰 갱신 ---
    if (action === 'refresh_token') {
      const credentials = Buffer.from(`${clientId}:${clientSecret}`).toString('base64');
      const resp = await fetch(`https://${mallId}.cafe24api.com/api/v2/oauth/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': `Basic ${credentials}`,
        },
        body: `grant_type=refresh_token&refresh_token=${encodeURIComponent(refreshToken)}`,
      });
      const data = await resp.json();
      return res.status(resp.status).json(data);
    }

    // --- 주문 조회 ---
    if (action === 'get_orders') {
      const { startDate, endDate } = params;
      const queryParams = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
        order_status: 'N20',
        limit: '100',
        embed: 'items,receivers',
      });
      const resp = await fetch(
        `https://${mallId}.cafe24api.com/api/v2/admin/orders?${queryParams}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            'X-Cafe24-Api-Version': '2025-12-01',
          },
        }
      );
      const data = await resp.json();
      return res.status(resp.status).json(data);
    }

    // --- 송장 등록 (배송 처리) ---
    if (action === 'update_shipping') {
      const { orderId, orderItemCode, trackingNo } = params;
      const body = {
        request: {
          shipping_code: 'LOGEN',
          tracking_no: trackingNo,
          status: 'shipping',
          order_item_code: orderItemCode ? [orderItemCode] : undefined,
        },
      };
      const resp = await fetch(
        `https://${mallId}.cafe24api.com/api/v2/admin/orders/${orderId}/fulfillments`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            'X-Cafe24-Api-Version': '2025-12-01',
          },
          body: JSON.stringify(body),
        }
      );
      const data = await resp.json();
      return res.status(resp.status).json(data);
    }

    return res.status(400).json({ error: 'Unknown action' });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
}
