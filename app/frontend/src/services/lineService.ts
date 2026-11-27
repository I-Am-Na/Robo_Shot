import type { FuelLine, FuelLineGetResponse, LineNum } from '@/types/api';
import { request } from './apiClient';

export async function getFuelLine(lineNum: LineNum): Promise<FuelLine> {
  const res = await request<FuelLineGetResponse>(`/line/${lineNum}`);
  if (!res.line) throw new Error(`line ${lineNum} 정보가 없습니다.`);
  return res.line;
}
