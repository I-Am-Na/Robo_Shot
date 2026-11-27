import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Badge, Button, Text } from '@/components/atoms';
import { InfoRow } from '@/components/molecules';
import { pay } from '@/services/paymentService';
import type { FuelType } from '@/types/api';
import { formatWon } from '@/utils/parseOrder';
import styles from './PaymentPage.module.css';

const FUEL_TYPES: FuelType[] = ['휘발유', '경유'];

/** 결제 QR로 열리는 테스트 결제 페이지. 결제 완료를 서버에 알리면 로봇이 주유를 시작한다. */
export function PaymentPage() {
  const [params] = useSearchParams();
  const [state, setState] = useState<'idle' | 'paying' | 'paid' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);

  const car = params.get('car');
  const fuel = params.get('fuel') as FuelType | null;
  const amount = Number(params.get('amount'));
  const valid = Boolean(car && fuel && FUEL_TYPES.includes(fuel) && amount > 0);

  const submit = async () => {
    if (!valid) return;
    setState('paying');
    setError(null);
    try {
      const ok = await pay(car!, fuel!, amount);
      setState(ok ? 'paid' : 'error');
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setState('error');
    }
  };

  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <div className={styles.header}>
          <Text as="h1" size="lg" bold>
            Robo_Shot 결제
          </Text>
          <Badge tone="warning">테스트</Badge>
        </div>

        {!valid ? (
          <Text muted>결제 정보가 올바르지 않습니다. QR을 다시 찍어주세요.</Text>
        ) : (
          <>
            <div>
              <InfoRow label="차량번호" value={car} />
              <InfoRow label="유종" value={fuel} />
              <InfoRow label="금액" value={formatWon(amount)} />
            </div>

            {state === 'paid' ? (
              <div className={styles.done} role="status">
                <Text bold>결제가 완료되었습니다</Text>
                <Text size="sm">곧 주유를 시작합니다. (테스트 결제 — 실제 결제는 이루어지지 않았습니다)</Text>
              </div>
            ) : (
              <>
                {state === 'error' && (
                  <div className={styles.fail} role="alert">
                    <Text size="sm">결제에 실패했습니다: {error ?? '알 수 없는 오류'}</Text>
                  </div>
                )}
                <Button onClick={submit} disabled={state === 'paying'}>
                  {state === 'paying' ? '결제 중…' : `${formatWon(amount)} 결제하기`}
                </Button>
              </>
            )}
          </>
        )}
      </section>
    </main>
  );
}
