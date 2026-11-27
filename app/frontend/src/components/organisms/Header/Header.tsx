import { NavLink } from 'react-router-dom';
import { Text } from '@/components/atoms';
import styles from './Header.module.css';

export function Header() {
  return (
    <header className={styles.header}>
      <Text as="h1" size="lg" bold>
        Robo_Shot
      </Text>
      <nav className={styles.nav}>
        <NavLink to="/" end className={({ isActive }) => (isActive ? styles.active : styles.link)}>
          대시보드
        </NavLink>
      </nav>
    </header>
  );
}
