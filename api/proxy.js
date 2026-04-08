export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, x-avito-path, x-target-api');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const targetApi = req.headers['x-target-api'] || 'avito';

  let targetUrl;
  if (targetApi === 'anthropic') {
    targetUrl = 'https://api.anthropic.com/v1/messages';
  } else {
    const avitoPath = req.headers['x-avito-path'] || '/token';
    targetUrl = 'https://api.avito.ru' + avitoPath;
  }

  try {
    const fetchOptions = { method: req.method, headers: {} };

    if (targetApi === 'anthropic') {
      fetchOptions.headers['x-api-key'] = process.env.ANTHROPIC_API_KEY;
      fetchOptions.headers['anthropic-version'] = '2023-06-01';
      fetchOptions.headers['Content-Type'] = 'application/json';
      fetchOptions.body = JSON.stringify(req.body);
    } else {
      if (req.headers.authorization) fetchOptions.headers['Authorization'] = req.headers.authorization;
      if (req.method === 'POST' || req.method === 'PUT') {
        const ct = req.headers['content-type'] || 'application/json';
        fetchOptions.headers['Content-Type'] = ct;
        if (ct.includes('x-www-form-urlencoded')) {
          fetchOptions.body = Object.entries(req.body || {})
            .map(([k,v]) => encodeURIComponent(k)+'='+encodeURIComponent(v)).join('&');
        } else {
          fetchOptions.body = JSON.stringify(req.body);
        }
      }
    }

    const response = await fetch(targetUrl, fetchOptions);
    const data = await response.json();
    res.status(response.status).json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}