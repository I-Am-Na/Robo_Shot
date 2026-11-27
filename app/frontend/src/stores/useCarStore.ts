import { create } from 'zustand';
import { completeFueling, listCars, visitCar } from '@/services/carService';
import type { CarItem, LineNum } from '@/types/api';

interface CarState {
  cars: CarItem[];
  loading: boolean;
  /** 마지막으로 조회에 성공한 시각 */
  lastFetchedAt: Date | null;
  error: string | null;
  /** 주유 완료 요청 중인 차량번호 */
  completing: string | null;
  /** 차량 진입 요청 중 여부 */
  entering: boolean;
  /** 직전 진입/완료 요청 결과 문구 (테스트 패널 표시용) */
  lastAction: string | null;
  fetchCars: () => Promise<void>;
  complete: (carNum: string) => Promise<void>;
  enter: (carNum: string, lineNum: LineNum, isLine: boolean) => Promise<void>;
}

const errorMessage = (e: unknown) => (e instanceof Error ? e.message : String(e));

export const useCarStore = create<CarState>((set, get) => ({
  cars: [],
  loading: false,
  lastFetchedAt: null,
  error: null,
  completing: null,
  entering: false,
  lastAction: null,
  fetchCars: async () => {
    set({ loading: true });
    try {
      const cars = await listCars();
      set({ cars, loading: false, error: null, lastFetchedAt: new Date() });
    } catch (e) {
      // 실패해도 직전 목록은 그대로 두고 화면에 에러 문구는 띄우지 않는다.
      set({ loading: false, error: errorMessage(e) });
    }
  },
  complete: async (carNum) => {
    set({ completing: carNum });
    try {
      const next = await completeFueling(carNum);
      set({ lastAction: `${carNum} 주유 완료 → 다음 차량: ${next ?? '없음'}` });
    } catch (e) {
      set({ error: errorMessage(e), lastAction: `${carNum} 완료 실패: ${errorMessage(e)}` });
    } finally {
      set({ completing: null });
      await get().fetchCars();
    }
  },
  enter: async (carNum, lineNum, isLine) => {
    set({ entering: true });
    try {
      const res = await visitCar(carNum, lineNum, isLine);
      set({ lastAction: `${carNum} (${lineNum}번 라인) → ${res.message}, 상태: ${res.status ?? '-'}` });
    } catch (e) {
      set({ error: errorMessage(e), lastAction: `${carNum} 진입 실패: ${errorMessage(e)}` });
    } finally {
      set({ entering: false });
      await get().fetchCars();
    }
  },
}));
