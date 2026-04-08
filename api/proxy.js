export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, x-avito-path, x-target-api');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const targetApi = req.headers['x-target-api'] || 'avito';

  // AI запросы — используем Anthropic API с ключом из env или напрямую
  if (targetApi === 'anthropic') {
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      // Если ключа нет — генерируем простой шаблонный текст
      const body = req.body;
      const userMsg = body?.messages?.[0]?.content || '';
      const isTitle = userMsg.includes('заголовка');
      
      let result;
      if (isTitle) {
        result = '1. Отличный товар в хорошем состоянии (47 симв.)\n2. Продаю срочно — выгодная цена (38 симв.)\n3. Проверенный товар, торг уместен (35 симв.)';
      } else {
        const nameMatch = userMsg.match(/Товар: ([^.]+)/);
        const priceMatch = userMsg.match(/Цена: ([^.]+)/);
        const name = nameMatch ? nameMatch[1].trim() : 'Товар';
        const price = priceMatch ? priceMatch[1].trim() : '';
        result = `🔥 Продаю ${name}!

Отличное состояние, всё работает идеально. Полный комплект, всё оригинальное.

✅ Проверен перед продажей
✅ Документы в наличии
✅ Быстрая передача

Цена: ${price}. Торг при осмотре. Звоните — отвечу на все вопросы!`;
      }
      
      return res.status(200).json({
        content: [{ type: 'text', text: result }]
      });
    }

    // Есть ключ — используем настоящий API
    try {
      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'x-api-key': apiKey,
          'anthropic-version': '2023-06-01',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(req.body)
      });
      const data = await response.json();
      return res.status(response.status).json(data);
    } catch (err) {
      return res.status(500).json({ error: err.message });
    }
  }

  // Авито запросы
  const avitoPath = req.headers['x-avito-path'] || '/token';
  const avitoUrl = 'https://api.avito.ru' + avitoPath;

  try {
    const fetchOptions = { method: req.method, headers: {} };
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

    const response = await fetch(avitoUrl, fetchOptions);
    const data = await response.json();
    res.status(response.status).json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}