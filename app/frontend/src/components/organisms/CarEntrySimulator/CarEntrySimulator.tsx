import { useState, type FormEvent } from 'react';
import { Button, Input, Text } from '@/components/atoms';
import type { LineNum } from '@/types/api';
import styles from './CarEntrySimulator.module.css';

export interface CarEntryValues {
  carNum: string;
  lineNum: LineNum;
  isLine: boolean;
}

export interface CarEntrySimulatorProps {
  onEnter: (values: CarEntryValues) => void;
  disabled?: boolean;
  /** 직전 요청 결과 문구 (예: "11가1111 → ready") */
  result?: string | null;
}

/** 개발용: YOLO 대신 차량 진입(PUT /car)을 보낸다. */
export function CarEntrySimulator({ onEnter, disabled, result }: CarEntrySimulatorProps) {
  const [carNum, setCarNum] = useState('');
  const [lineNum, setLineNum] = useState<LineNum>(1);
  const [isLine, setIsLine] = useState(true);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const value = carNum.trim();
    if (!value) return;
    onEnter({ carNum: value, lineNum, isLine });
  };

  return (
    <form className={styles.panel} onSubmit={submit} aria-label="차량 진입 테스트">
      <div className={styles.title}>
        <Text size="sm" bold>
          차량 진입 테스트
        </Text>
        <Text size="sm" muted>
          YOLO 대신 PUT /car 요청을 보냅니다 (개발 모드에서만 보임)
        </Text>
      </div>

      <div className={styles.fields}>
        <Input
          aria-label="차량번호"
          placeholder="차량번호 (예: 11가1111)"
          value={carNum}
          onChange={(e) => setCarNum(e.target.value)}
          maxLength={20}
        />

        <div className={styles.segment} role="radiogroup" aria-label="라인">
          {([1, 2] as const).map((n) => (
            <button
              key={n}
              type="button"
              role="radio"
              aria-checked={lineNum === n}
              className={lineNum === n ? styles.segmentOn : styles.segmentOff}
              onClick={() => setLineNum(n)}
            >
              {n}번 라인
            </button>
          ))}
        </div>

        <label className={styles.check}>
          <input type="checkbox" checked={isLine} onChange={(e) => setIsLine(e.target.checked)} />
          <Text size="sm">라인 정상 진입</Text>
        </label>

        <Button type="submit" disabled={disabled || !carNum.trim()}>
          진입
        </Button>
      </div>

      {result && (
        <Text size="sm" muted>
          {result}
        </Text>
      )}
    </form>
  );
}
