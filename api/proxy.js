export default async function handler(req, res) {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  // path: /api/proxy?path=/token
  const avitoPath = req.query.path || '/token';
  const avitoUrl = 'https://api.avito.ru' + avitoPath;

  try {
    const fetchOptions = {
      method: req.method,
      headers: {}
    };

    // Forward Authorization header
    if (req.headers.authorization) {
      fetchOptions.headers['Authorization'] = req.headers.authorization;
    }

    // Forward body for POST/PUT
    if (req.method === 'POST' || req.method === 'PUT') {
      const contentType = req.headers['content-type'] || 'application/json';
      fetchOptions.headers['Content-Type'] = contentType;
      
      if (contentType.includes('x-www-form-urlencoded')) {
        // For token requests
        const body = Object.entries(req.body || {})
          .map(([k, v]) => encodeURIComponent(k) + '=' + encodeURIComponent(v))
          .join('&');
        fetchOptions.body = body;
      } else {
        fetchOptions.body = JSON.stringify(req.body);
      }
    }

    const response = await fetch(avitoUrl, fetchOptions);
    const data = await response.json();
    
    res.status(response.status).json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}