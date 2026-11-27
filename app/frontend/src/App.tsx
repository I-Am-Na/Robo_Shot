import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { MainLayout } from '@/components/templates';
import { DashboardPage } from '@/pages/DashboardPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { PaymentPage } from '@/pages/PaymentPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<MainLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
        {/* 결제 QR로 휴대폰에서 여는 페이지. 대시보드 헤더 없이 단독으로 보인다. */}
        <Route path="/pay" element={<PaymentPage />} />
      </Routes>
    </BrowserRouter>
  );
}
