import type {
  BaseResponse,
  CarDetail,
  CarGetResponse,
  CarItem,
  CarListResponse,
  CarVisitResponse,
  CompleteFuelingResponse,
  FuelType,
  LineNum,
} from '@/types/api';
import { request } from './apiClient';

/** 차량 목록(최근 감지 순). 대시보드 polling에서 사용. */
export async function listCars(limit = 50): Promise<CarItem[]> {
  const res = await request<CarListResponse>(`/car?limit=${limit}`);
  return res.cars;
}

/** 차량 진입(YOLO가 보내는 요청과 같음). 처리 후 상태를 돌려준다. */
export async function visitCar(carNum: string, lineNum: LineNum, isLine: boolean): Promise<CarVisitResponse> {
  return request<CarVisitResponse>('/car', {
    method: 'PUT',
    body: JSON.stringify({ car_num: carNum, is_line: isLine, line_num: lineNum }),
  });
}

/** 음성 주문에서 인식한 유종 저장. ready 차량만 가능하다. 금액은 저장하지 않는다. */
export async function orderFuelType(carNum: string, fuelType: FuelType): Promise<void> {
  await request<BaseResponse>(`/car/${encodeURIComponent(carNum)}/fuel-type`, {
    method: 'PUT',
    body: JSON.stringify({ fuel_type: fuelType }),
  });
}

/** 주유 완료. 다음 대기 차량이 ready가 되면 그 차량번호를 돌려준다. */
export async function completeFueling(carNum: string): Promise<string | null> {
  const res = await request<CompleteFuelingResponse>(`/car/${encodeURIComponent(carNum)}/complete`, {
    method: 'PUT',
  });
  return res.next_car_num;
}

export async function getCar(carNum: string): Promise<CarDetail> {
  const res = await request<CarGetResponse>(`/car/${encodeURIComponent(carNum)}`);
  if (!res.car) throw new Error('차량 정보가 없습니다.');
  return res.car;
}
