// NFR-01 (şartname): tipik liste/okuma uçları p95 < 300 ms.
//
//   k6 run -e API=http://localhost:8000 -e TENANT=demo -e EPOSTA=admin@demo.test \
//          -e PAROLA='Demo1234!' perf/k6/nfr01_liste.js
//
// Tek giriş (setup) — giriş uçları hız sınırlıdır ve NFR-01'in konusu değildir. Her sanal
// kullanıcı ekranların açılışta çağırdığı liste/özet uçlarını sırayla ister; uç başına p95
// eşiği ayrı raporlanır (hangi uç bütçeyi aşıyor, tek bakışta görünsün).
import http from 'k6/http';
import { check, sleep } from 'k6';

const API = __ENV.API || 'http://localhost:8000';
const TENANT = __ENV.TENANT || 'demo';

const UCLAR = [
  '/api/v1/makineler',
  '/api/v1/uretim-verileri',
  '/api/v1/oee/ozet',
  '/api/v1/is-emirleri',
  '/api/v1/malzemeler',
  '/api/v1/stok-hareketleri',
  '/api/v1/stok-bakiyeleri',
  '/api/v1/satinalma-talepleri',
  '/api/v1/satinalma-siparisleri',
  '/api/v1/kalite-kontrolleri',
  '/api/v1/uygunsuzluklar',
  '/api/v1/enerji-tuketimleri',
  '/api/v1/personeller',
  '/api/v1/firmalar',
  '/api/v1/bildirimler',
  '/api/v1/denetim-kayitlari',
];

const esikler = { 'http_req_duration{tur:liste}': ['p(95)<300'], http_req_failed: ['rate<0.01'] };
for (const u of UCLAR) esikler[`http_req_duration{uc:${u}}`] = ['p(95)<300'];

export const options = {
  scenarios: {
    liste: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: '20s', target: Number(__ENV.VU || 20) },
        { duration: __ENV.SURE || '60s', target: Number(__ENV.VU || 20) },
        { duration: '10s', target: 0 },
      ],
    },
  },
  thresholds: esikler,
  summaryTrendStats: ['avg', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export function setup() {
  const r = http.post(
    `${API}/api/v1/kimlik/token`,
    { username: __ENV.EPOSTA, password: __ENV.PAROLA },
    { headers: { 'X-Tenant': TENANT } },
  );
  if (r.status !== 200) throw new Error(`giriş başarısız: ${r.status} ${r.body}`);
  return { token: r.json('data.access_token') };
}

export default function (veri) {
  const basliklar = { Authorization: `Bearer ${veri.token}`, 'X-Tenant': TENANT };
  for (const u of UCLAR) {
    const r = http.get(`${API}${u}`, { headers: basliklar, tags: { tur: 'liste', uc: u } });
    check(r, { '200': (x) => x.status === 200 });
  }
  sleep(0.5);
}
