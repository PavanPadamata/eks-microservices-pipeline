// Constant request rate against the api, which calls the worker for every request.
// Each request costs the worker ~WORK_MS of CPU, so RATE drives CPU and therefore the HPAs.
import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';
const RATE = parseInt(__ENV.RATE || '40');
const DURATION = __ENV.DURATION || '240s';

export const options = {
  scenarios: {
    steady: {
      executor: 'constant-arrival-rate',   // fixed req/s regardless of latency
      rate: RATE,
      timeUnit: '1s',
      duration: DURATION,
      preAllocatedVUs: 50,
      maxVUs: 300,
    },
  },
  // Illustrative pass/fail lines (same 500 ms as the p95 alert), not tuned SLOs.
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
  },
};

export default function () {
  const n = Math.floor(Math.random() * 1000);
  const res = http.get(`${BASE_URL}/compute?n=${n}`);
  check(res, {
    'status is 200': (r) => r.status === 200,
    'result is correct': (r) => r.status === 200 && r.json('result') === (n * (n + 1) * (2 * n + 1)) / 6,
  });
}
