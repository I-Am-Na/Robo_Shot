import type { ElementType, ReactNode } from 'react';
import styles from './Text.module.css';

type Size = 'sm' | 'md' | 'lg' | 'xl';

export interface TextProps {
  as?: ElementType;
  size?: Size;
  muted?: boolean;
  bold?: boolean;
  children: ReactNode;
}

export function Text({ as: Tag = 'span', size = 'md', muted, bold, children }: TextProps) {
  const classes = [styles.text, styles[size], muted && styles.muted, bold && styles.bold]
    .filter(Boolean)
    .join(' ');
  return <Tag className={classes}>{children}</Tag>;
}
