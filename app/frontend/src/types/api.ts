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
