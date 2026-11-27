import { Badge, Text } from '@/components/atoms';
import { InfoRow } from '@/components/molecules';
import type { FuelLine, LineNum } from '@/types/api';
import styles from './FuelLineCard.module.css';

export interface FuelLineCardProps {
  lineNum: LineNum;
  line?: FuelLine;
}

function formatTime(iso: string | null | undefined) {
  if (!iso) return '-';
  return new Date(iso).toLocaleString('ko-KR', { hour12: false });
}

/** 주유 라인 1개의 상태 카드. 데이터는 props로만 받는다. */
export function FuelLineCard({ lineNum, line }: FuelLineCardProps) {
  const fueling = line?.is_fueling ?? false;

  return (
    <article className={styles.card} aria-label={`${lineNum}번 라인`}>
      <header className={styles.header}>
        <Text as="h2" size="lg" bold>
          {lineNum}번 라인
        </Text>
        {line ? (
          <Badge tone={fueling ? 'warning' : 'success'}>{fueling ? '주유 중' : '대기'}</Badge>
        ) : (
          <Badge>정보 없음</Badge>
        )}
      </header>
      <InfoRow label="차량번호" value={line?.car_num ?? '-'} />
      <InfoRow label="상태 변경" value={formatTime(line?.updated_at)} />
    </article>
  );
}
