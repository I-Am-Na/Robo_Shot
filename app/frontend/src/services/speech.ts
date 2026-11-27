// 브라우저 내장 음성 합성(Web Speech API) 래퍼.

export const FUELING_START_MESSAGE = '주유를 시작합니다. 유종과 금액을 말씀해주세요';
export const ORDER_RETRY_MESSAGE = '잘 듣지 못했습니다. 유종과 금액을 다시 말씀해주세요';
export const PAYMENT_QR_MESSAGE = '화면의 QR 코드로 결제해주세요';
export const PAID_MESSAGE = '결제가 완료되었습니다. 주유를 시작합니다';

export function isSpeechSupported(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window;
}

function koreanVoice(): SpeechSynthesisVoice | undefined {
  return window.speechSynthesis.getVoices().find((v) => v.lang.toLowerCase().startsWith('ko'));
}

/** 말하기. 다 말하면(또는 실패하면) resolve된다. */
export function speak(text: string): Promise<void> {
  return new Promise((resolve) => {
    if (!isSpeechSupported()) return resolve();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'ko-KR';
    const voice = koreanVoice();
    if (voice) utterance.voice = voice;
    utterance.onend = () => resolve();
    utterance.onerror = () => resolve();
    window.speechSynthesis.speak(utterance);
  });
}

/**
 * 브라우저는 사용자가 한 번 클릭하기 전에는 소리를 막는다.
 * "음성 안내 켜기" 클릭 시 호출해 이후 자동 안내가 나오게 한다.
 */
export function unlockSpeech(): void {
  if (!isSpeechSupported()) return;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(new SpeechSynthesisUtterance(''));
}
