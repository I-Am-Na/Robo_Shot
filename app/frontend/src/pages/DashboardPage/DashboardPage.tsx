import { useCallback, useEffect, useRef, useState } from 'react';
import { Button, Text } from '@/components/atoms';
import { CarEntrySimulator, CarStatusTable, VoiceOrderPanel } from '@/components/organisms';
import { usePolling } from '@/hooks/usePolling';
import { useReadyAnnouncement } from '@/hooks/useReadyAnnouncement';
import {
  FUELING_START_MESSAGE,
  ORDER_RETRY_MESSAGE,
  PAID_MESSAGE,
  PAYMENT_QR_MESSAGE,
  isSpeechSupported,
  speak,
  unlockSpeech,
} from '@/services/speech';
import { isRecognitionSupported } from '@/services/speechRecognition';
import { useCarStore } from '@/stores/useCarStore';
import { useOrderStore, type OrderPhase } from '@/stores/useOrderStore';
import styles from './DashboardPage.module.css';

const POLL_INTERVAL_MS = 3000;
/** 테스트 패널·직접 입력 칸은 개발 서버(npm run dev)에서만 보인다. */
const DEV_TOOLS = import.meta.env.DEV;
/** 알아듣지 못했을 때 자동으로 다시 묻는 횟수 */
const AUTO_RETRY = 2;

export function DashboardPage() {
  // 조회에 실패해도 에러 문구는 띄우지 않고 직전 목록을 유지한다.
  const { cars, loading, lastFetchedAt, fetchCars, complete, completing, enter, entering, lastAction } =
    useCarStore();
  usePolling(fetchCars, POLL_INTERVAL_MS);

  const order = useOrderStore();
  const readyCar = cars.find((c) => c.status === 'ready') ?? null;
  const { setCar } = order;
  useEffect(() => setCar(readyCar?.car_num ?? null), [readyCar?.car_num, setCar]);

  // 음성 안내: 브라우저 정책상 페이지를 열 때마다 한 번 눌러서 켜야 소리가 난다.
  const [voiceOn, setVoiceOn] = useState(false);
  const voiceOnRef = useRef(voiceOn);
  voiceOnRef.current = voiceOn;
  const toggleVoice = () => {
    if (!voiceOn) unlockSpeech();
    setVoiceOn(!voiceOn);
  };
  const say = useCallback(async (text: string) => {
    if (voiceOnRef.current) await speak(text);
  }, []);

  const afterOrder = useCallback(
    async (phase: OrderPhase) => {
      if (phase === 'qr') await say(PAYMENT_QR_MESSAGE);
    },
    [say],
  );

  /** 마이크로 주문을 받는다. 못 알아들으면 AUTO_RETRY번까지 다시 묻는다. */
  const takeOrder = useCallback(async () => {
    const { listen } = useOrderStore.getState();
    let phase = await listen();
    for (let i = 0; phase === 'retry' && i < AUTO_RETRY && voiceOnRef.current; i++) {
      await say(ORDER_RETRY_MESSAGE);
      phase = await listen();
    }
    await afterOrder(phase);
  }, [say, afterOrder]);

  // 차량이 주유 준비(ready)가 되면: 안내 음성 → 마이크로 주문 받기
  const announce = useCallback(async () => {
    await speak(FUELING_START_MESSAGE);
    if (isRecognitionSupported()) await takeOrder();
  }, [takeOrder]);
  useReadyAnnouncement(cars, lastFetchedAt !== null, voiceOn, announce);

  // 휴대폰에서 결제가 끝나 paid가 되면: 결제 완료 안내 (로봇은 GET /robot/task로 받아 주유 시작)
  const announcePaid = useCallback(() => speak(PAID_MESSAGE), []);
  useReadyAnnouncement(cars, lastFetchedAt !== null, voiceOn, announcePaid, 'paid');

  const submitText = async (text: string) => afterOrder(await useOrderStore.getState().submit(text));

  return (
    <section className={styles.page}>
      <div className={styles.toolbar}>
        <div>
          <Text as="h2" size="xl" bold>
            차량 현황
          </Text>
          <Text size="sm" muted>
            {POLL_INTERVAL_MS / 1000}초마다 자동 갱신
            {lastFetchedAt && ` · 마지막 갱신 ${lastFetchedAt.toLocaleTimeString('ko-KR', { hour12: false })}`}
          </Text>
        </div>
        <div className={styles.actions}>
          {isSpeechSupported() && (
            <Button variant={voiceOn ? 'primary' : 'secondary'} onClick={toggleVoice} aria-pressed={voiceOn}>
              {voiceOn ? '음성 안내 켜짐' : '음성 안내 켜기'}
            </Button>
          )}
          <Button variant="secondary" onClick={fetchCars} disabled={loading}>
            새로고침
          </Button>
        </div>
      </div>

      {DEV_TOOLS && (
        <CarEntrySimulator
          onEnter={({ carNum, lineNum, isLine }) => enter(carNum, lineNum, isLine)}
          disabled={entering}
          result={lastAction}
        />
      )}

      {readyCar && order.carNum === readyCar.car_num && (
        <VoiceOrderPanel
          carNum={readyCar.car_num}
          phase={order.phase}
          transcript={order.transcript}
          error={order.error}
          order={order.order}
          paymentUrl={order.paymentUrl}
          canListen={isRecognitionSupported()}
          onListen={takeOrder}
          showTextInput={DEV_TOOLS}
          onSubmitText={submitText}
        />
      )}

      <CarStatusTable cars={cars} onComplete={complete} completing={completing} />
    </section>
  );
}
