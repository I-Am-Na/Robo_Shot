// 백엔드(FastAPI) 응답 타입. 백엔드 schemas.py와 맞춘다.

export type FuelType = '휘발유' | '경유';
export type LineNum = 1 | 2;

export interface BaseResponse {
  success: boolean;
  message: string;
}

export interface FuelLine {
  line_num: LineNum;
  is_fueling: boolean;
  car_num: string | null;
  updated_at: string | null;
}

export interface FuelLineGetResponse extends BaseResponse {
  line: FuelLine | null;
}

/** GET /car 목록의 한 행 */
export interface CarItem {
  car_num: string;
  is_line: boolean;
  line_num: LineNum;
  fuel_type: FuelType | null;
  /** 'ready'(주유 준비) | 'paid'(결제 완료·주유 중) | 'waiting'(대기) | 'done'(완료) | null */
  status: string | null;
  updated_at: string;
  status_updated_at: string | null;
}

export interface CarListResponse extends BaseResponse {
  cars: CarItem[];
}

export interface CarVisitResponse extends BaseResponse {
  /** created | updated */
  message: string;
  status: string | null;
}

export interface CompleteFuelingResponse extends BaseResponse {
  next_car_num: string | null;
}

export interface CarDetail {
  car_num: string;
  is_line: boolean;
  line_num: LineNum;
  fuel_type: FuelType | null;
  updated_at: string;
  visit_count: number;
}

export interface CarGetResponse extends BaseResponse {
  car: CarDetail | null;
}
