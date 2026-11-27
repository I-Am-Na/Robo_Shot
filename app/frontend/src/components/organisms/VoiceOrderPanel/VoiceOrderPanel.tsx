import { useState, type FormEvent } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { Badge, Button, Input, Text } from '@/components/atoms';
import { InfoRow } from '@/components/molecules';
import type { OrderPhase } from '@/stores/useOrderStore';
import { formatWon, type ParsedOrder } from '@/utils/parseOrder';
import styles from './VoiceOrderPanel.module.css';

export interface VoiceOrderPanelProps {
  carNum: string;
  phase: OrderPhase;
  transcript: string | null;
  error: string | null;
  order: ParsedOrder | null;
  paymentUrl: string | null;
  /** 마이크 사용 가능 여부 */
  canListen: boolean;
  onListen: () => void;
  /** 직접 입력 칸 표시 (개발용) */
  showTextInput?: boolean;
  onSubmitText?: (text: string) => void;
}

const PHASE_BADGE: Record<OrderPhase, { label: string; tone: 'neutral' | 'success' | 'warning' | 'danger' }> = {
  idle: { label: '주문 대기', tone: 'neutral' },
  listening: { label: '듣는 중…', tone: 'warning' },
  processing: { label: '처리 중…', tone: 'warning' },
  retry: { label: '다시 말씀해주세요', tone: 'danger' },
  qr: { label: '결제 대기', tone: 'success' },
};

/** 주유 준비 차량의 음성 주문 → 결제 QR. 데이터와 동작은 props로만 받는다. */
export function VoiceOrderPanel({
  carNum,
  phase,
  transcript,
  error,
  order,
  paymentUrl,
  canListen,
  onListen,
  showTextInput,
  onSubmitText,
}: VoiceOrderPanelProps) {
  const [text, setText] = useState('');
  const badge = PHASE_BADGE[phase];
  const busy = phase === 'listening' || phase === 'processing';

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim() || !onSubmitText) return;
    onSubmitText(text.trim());
    setText('');
  };

  return (
    <section className={styles.panel} aria-label="음성 주문">
      <header className={styles.header}>
        <div>
          <Text size="sm" muted>
            음성 주문
          </Text>
          <Text as="h3" size="lg" bold>
            {carNum}
          </Text>
        </div>
        <Badge tone={badge.tone}>{badge.label}</Badge>
      </header>

      {phase === 'qr' && order && paymentUrl ? (
        <div className={styles.qr}>
          <div className={styles.qrImage}>
            <QRCodeSVG value={paymentUrl} size={176} marginSize={2} title="결제 QR 코드" />
          </div>
          <div className={styles.qrInfo}>
            <Text bold>QR 코드로 결제해주세요</Text>
            <InfoRow label="유종" value={order.fuelType} />
            <InfoRow label="금액" value={formatWon(order.amount)} />
            <Text size="sm" muted>
              테스트 결제 링크입니다
            </Text>
            {showTextInput && (
              <a className={styles.payLink} href={paymentUrl} target="_blank" rel="noreferrer">
                PC에서 결제 페이지 열기 ↗
              </a>
            )}
          </div>
        </div>
      ) : (
        <div className={styles.body}>
          <Text size="sm" muted>
            예: “휘발유, 5만원” · “경유 삼만 오천원”
          </Text>
          {transcript && (
            <Text size="sm">
              인식된 말: <strong>“{transcript}”</strong>
            </Text>
          )}
          {error && (
            <Text size="sm">
              <span className={styles.error}>{error}</span>
            </Text>
          )}
          <div className={styles.actions}>
            {canListen ? (
              <Button onClick={onListen} disabled={busy}>
                {phase === 'listening' ? '듣는 중…' : '말하기'}
              </Button>
            ) : (
              <Text size="sm" muted>
                이 브라우저는 음성 인식을 지원하지 않습니다 (크롬 권장)
              </Text>
            )}
          </div>
        </div>
      )}

      {showTextInput && onSubmitText && phase !== 'qr' && (
        <form className={styles.textForm} onSubmit={submit}>
          <Input
            aria-label="주문 직접 입력"
            placeholder="마이크 없이 테스트: 휘발유 5만원"
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={busy}
          />
          <Button type="submit" variant="secondary" disabled={busy || !text.trim()}>
            입력
          </Button>
        </form>
      )}
    </section>
  );
}
