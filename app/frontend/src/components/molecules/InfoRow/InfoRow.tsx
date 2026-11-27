import type { ReactNode } from 'react';
import { Text } from '@/components/atoms';
import styles from './InfoRow.module.css';

export interface InfoRowProps {
  label: string;
  value: ReactNode;
}

/** 라벨 + 값 한 줄. */
export function InfoRow({ label, value }: InfoRowProps) {
  return (
    <div className={styles.row}>
      <Text size="sm" muted>
        {label}
      </Text>
      <Text size="sm" bold>
        {value}
      </Text>
    </div>
  );
}
