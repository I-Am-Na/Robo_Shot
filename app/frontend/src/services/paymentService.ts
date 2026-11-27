import type { BaseResponse, FuelType } from '@/types/api';
import { request } from './apiClient';

/**
 * 결제 QR에 넣을 테스트 결제 링크.
 * 휴대폰으로 찍으려면 PC의 IP 주소로 접속할 수 있어야 하므로
 * VITE_PUBLIC_BASE_URL (예: http://192.168.0.10:5173) 을 설정한다. 없으면 현재 접속 주소를 쓴다.
 * 실제 결제사 연동 시 이 함수만 결제사 링크를 돌려주도록 바꾸면 된다.
 */
export function buildPaymentUrl(carNum: string, fuelType: FuelType, amount: number): string {
  const base = import.meta.env.VITE_PUBLIC_BASE_URL || window.location.origin;
  const params = new URLSearchParams({ car: carNum, fuel: fuelType, amount: String(amount) });
  return `${base.replace(/\/$/, '')}/pay?${params.toString()}`;
}

/**
 * 결제 완료를 서버에 알린다. 성공하면 true.
 * 서버는 차량을 paid로 바꾸고, 로봇은 GET /robot/task polling으로 받아 주유를 시작한다.
 */
export async function pay(carNum: string, fuelType: FuelType, amount: number): Promise<boolean> {
  const res = await request<BaseResponse>(`/car/${encodeURIComponent(carNum)}/pay`, {
    method: 'PUT',
    body: JSON.stringify({ fuel_type: fuelType, amount }),
  });
  return res.success;
}
