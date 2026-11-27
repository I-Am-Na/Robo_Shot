import { Outlet } from 'react-router-dom';
import { Header } from '@/components/organisms';
import styles from './MainLayout.module.css';

/** 모든 페이지 공통 뼈대: 상단 Header + 본문 영역. */
export function MainLayout() {
  return (
    <div className={styles.layout}>
      <Header />
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
