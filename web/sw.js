self.addEventListener('fetch', e => e.respondWith(fetch(e.request).catch(() => new Response('Offline', {status: 503}))));
