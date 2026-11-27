import { Button, Text } from '@/components/atoms';
import { FuelLineCard } from '@/components/organisms';
import { usePolling } from '@/hooks/usePolling';
import { LINE_NUMS, useLineStore } from '@/stores/useLineStore';
import styles from './DashboardPage.module.css';

const POLL_INTERVAL_MS = 3000;

export function DashboardPage() {
  // 조회에 실패해도 에러 문구는 띄우지 않는다. 데이터가 없는 라인은 카드에 "정보 없음"으로 표시된다.
  const { lines, loading, fetchLines } = useLineStore();
  usePolling(fetchLines, POLL_INTERVAL_MS);

  return (
    <section className={styles.page}>
      <div className={styles.toolbar}>
        <div>
          <Text as="h2" size="xl" bold>
            주유 라인 현황
          </Text>
          <Text size="sm" muted>
            {POLL_INTERVAL_MS / 1000}초마다 자동으로 갱신됩니다.
          </Text>
        </div>
        <Button variant="secondary" onClick={fetchLines} disabled={loading}>
          새로고침
        </Button>
      </div>

      <div className={styles.grid}>
        {LINE_NUMS.map((n) => (
          <FuelLineCard key={n} lineNum={n} line={lines[n]} />
        ))}
      </div>
    </section>
  );
}
