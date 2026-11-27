// 브라우저 내장 음성 인식(Web Speech API, 크롬 지원) 래퍼.
// 크롬은 음성을 Google 서버로 보내 인식하므로 인터넷 연결이 필요하다.

interface RecognitionResultEvent {
  results: ArrayLike<ArrayLike<{ transcript: string }>>;
}

interface RecognitionErrorEvent {
  error: string;
}

interface Recognition {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  continuous: boolean;
  onresult: ((e: RecognitionResultEvent) => void) | null;
  onerror: ((e: RecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  abort: () => void;
}

type RecognitionCtor = new () => Recognition;

function getCtor(): RecognitionCtor | undefined {
  if (typeof window === 'undefined') return undefined;
  const w = window as unknown as { SpeechRecognition?: RecognitionCtor; webkitSpeechRecognition?: RecognitionCtor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition;
}

export function isRecognitionSupported(): boolean {
  return getCtor() !== undefined;
}

const ERROR_MESSAGES: Record<string, string> = {
  'no-speech': '말소리가 들리지 않았습니다.',
  'audio-capture': '마이크를 찾을 수 없습니다.',
  'not-allowed': '마이크 권한이 없습니다. 브라우저 주소창에서 마이크를 허용해주세요.',
  network: '음성 인식 서버에 연결할 수 없습니다 (인터넷 필요).',
};

let current: Recognition | null = null;

/** 한 문장을 듣고 인식한 텍스트를 돌려준다. */
export function listenOnce(): Promise<string> {
  const Ctor = getCtor();
  if (!Ctor) return Promise.reject(new Error('이 브라우저는 음성 인식을 지원하지 않습니다. 크롬을 사용해주세요.'));

  current?.abort();
  const recognition = new Ctor();
  current = recognition;
  recognition.lang = 'ko-KR';
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  recognition.continuous = false;

  return new Promise((resolve, reject) => {
    let settled = false;
    recognition.onresult = (e) => {
      settled = true;
      resolve(e.results[0]?.[0]?.transcript ?? '');
    };
    recognition.onerror = (e) => {
      if (settled) return;
      settled = true;
      reject(new Error(ERROR_MESSAGES[e.error] ?? `음성 인식 오류: ${e.error}`));
    };
    recognition.onend = () => {
      if (current === recognition) current = null;
      if (!settled) {
        settled = true;
        reject(new Error(ERROR_MESSAGES['no-speech']));
      }
    };
    recognition.start();
  });
}

export function stopListening(): void {
  current?.abort();
  current = null;
}
