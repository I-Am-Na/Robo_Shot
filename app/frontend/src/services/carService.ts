import type { CarDetail, CarGetResponse } from '@/types/api';
import { request } from './apiClient';

export async function getCar(carNum: string): Promise<CarDetail> {
  const res = await request<CarGetResponse>(`/car/${encodeURIComponent(carNum)}`);
  if (!res.car) throw new Error('차량 정보가 없습니다.');
  return res.car;
}
