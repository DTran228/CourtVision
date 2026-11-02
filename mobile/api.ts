export type Connection = { url: string; token: string };
export type Outcome = 'made' | 'missed' | 'unknown';
export type ReviewEvent = { id: string; contact_seconds: number; outcome: Outcome; provenance?: string };
export type Summary = { candidates: number; makes: number; misses: number; unknown: number; review_complete: boolean; fg_percent: number | null };
export type Job = { id: string; status: 'queued' | 'running' | 'succeeded' | 'failed'; stage: string; attempt: number; processed: number | null; total: number | null; error: { type: string; message: string } | null; session_id: string | null; dispatch_intent: number };
export type Session = { id: string; revision: number; automatic: { events: (ReviewEvent & { reason: string })[]; summary: Summary; timebase: { duration_seconds: number } }; review: { events: ReviewEvent[]; complete: boolean }; review_summary: Summary };
export type SessionRow = { id: string; automatic_summary: Summary; review_summary: Summary; revision: number };

export function base(connection: Connection) {
  const url = connection.url.trim().replace(/\/$/, '');
  if (!/^https?:\/\/[^\s]+$/.test(url)) throw new Error('Set a valid backend URL, e.g. http://192.168.1.10:8000');
  return url;
}

export function auth(connection: Connection): Record<string, string> {
  return connection.token ? { Authorization: `Bearer ${connection.token}` } : {};
}

export async function request<T>(connection: Connection, path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`${base(connection)}${path}`, {
      ...init, signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...auth(connection), ...init.headers },
    });
    const body = await response.json();
    if (!response.ok) throw new Error(`${response.status}: ${typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)}`);
    return body as T;
  } finally { clearTimeout(timer); }
}

// Native React Native accepts {uri} as raw request body; it reads the local file.
// It is deliberately not FormData: /videos accepts streamed raw video bytes.
export function upload(connection: Connection, uri: string, mime: string, onProgress: (bytes: number) => void) {
  const xhr = new XMLHttpRequest();
  const promise = new Promise<{ id: string }>((resolve, reject) => {
    xhr.open('POST', `${base(connection)}/videos`);
    xhr.timeout = 180000;
    xhr.setRequestHeader('Content-Type', mime);
    Object.entries(auth(connection)).forEach(([k, v]) => xhr.setRequestHeader(k, v));
    xhr.upload.onprogress = event => onProgress(event.loaded);
    xhr.onload = () => {
      try {
        const value = JSON.parse(xhr.responseText);
        if (xhr.status < 200 || xhr.status >= 300) reject(new Error(`${xhr.status}: ${JSON.stringify(value.detail)}`));
        else resolve(value);
      } catch { reject(new Error('Backend returned an invalid upload response')); }
    };
    xhr.onerror = () => reject(new Error('Upload connection failed; check LAN address and backend'));
    xhr.ontimeout = () => reject(new Error('Upload timed out'));
    xhr.onabort = () => reject(new Error('Upload canceled'));
    xhr.send({ uri } as unknown as XMLHttpRequestBodyInit);
  });
  return { promise, cancel: () => xhr.abort() };
}
