import { Badge, Button, Text } from '@/components/atoms';
import type { BadgeTone } from '@/components/atoms';
import type { CarItem } from '@/types/api';
import styles from './CarStatusTable.module.css';

export interface CarStatusTableProps {
  cars: CarItem[];
  /** ready/paid 차량의 "주유 완료" 버튼을 눌렀을 때. 없으면 버튼을 숨긴다. */
  onComplete?: (carNum: string) => void;
  /** 완료 요청 중인 차량번호 (버튼 비활성화용) */
  completing?: string | null;
}

const STATUS_LABEL: Record<string, { label: string; tone: BadgeTone }> = {
  ready: { label: '주유 준비', tone: 'success' },
  paid: { label: '결제 완료 · 주유 중', tone: 'success' },
  waiting: { label: '대기', tone: 'warning' },
  done: { label: '완료', tone: 'neutral' },
};

function StatusBadge({ status }: { status: string | null }) {
  if (!status) return <Badge>-</Badge>;
  const known = STATUS_LABEL[status];
  return <Badge tone={known?.tone ?? 'neutral'}>{known?.label ?? status}</Badge>;
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleString('ko-KR', { hour12: false });
}

/** 차량 목록과 상태 표. 데이터는 props로만 받는다. */
export function CarStatusTable({ cars, onComplete, completing }: CarStatusTableProps) {
  if (cars.length === 0) {
    return (
      <div className={styles.empty}>
        <Text muted>감지된 차량이 없습니다.</Text>
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>차량번호</th>
            <th>라인</th>
            <th>상태</th>
            <th>유종</th>
            <th>마지막 감지</th>
            {onComplete && <th aria-label="작업" />}
          </tr>
        </thead>
        <tbody>
          {cars.map((car) => (
            <tr key={car.car_num}>
              <td className={styles.carNum}>{car.car_num}</td>
              <td>{car.line_num}번</td>
              <td>
                <StatusBadge status={car.status} />
              </td>
              <td>{car.fuel_type ?? '-'}</td>
              <td className={styles.muted}>{formatTime(car.updated_at)}</td>
              {onComplete && (
                <td className={styles.action}>
                  {(car.status === 'ready' || car.status === 'paid') && (
                    <Button
                      variant="secondary"
                      onClick={() => onComplete(car.car_num)}
                      disabled={completing === car.car_num}
                    >
                      주유 완료
                    </Button>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
