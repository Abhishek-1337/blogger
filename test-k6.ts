import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 1,
  duration: '30s',
};
const data = {
    query: "Difference between extraordinary people vs average people?"
}
export default function () {
  const response = http.post('http://127.0.0.1:8000/blog/enqueue',
    JSON.stringify(data),
    {
        headers: 
        { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${__ENV.TOKEN}`

         },
    }
  );
  const body = response.json() as { task_id?: string }
  check(response, {
    'status is 202': (r:any) => r.status === 202 && body.task_id !== undefined,
    'response time below 500ms': (r:any) => r.timings.duration < 500,
  });

  sleep(1);
}