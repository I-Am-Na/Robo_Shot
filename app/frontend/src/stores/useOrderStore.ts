import { create } from 'zustand';
import { orderFuelType } from '@/services/carService';
import { buildPaymentUrl } from '@/services/paymentService';
import { listenOnce, stopListening } from '@/services/speechRecognition';
import { parseOrder, type ParsedOrder } from '@/utils/parseOrder';

/**
 * 음성 주문 단계
 * idle       : 주문 대기 (ready 차량이 생기면 시작)
 * listening  : 마이크로 듣는 중
 * processing : 인식 결과 처리·유종 저장 중
 * retry      : 유종/금액을 알아듣지 못함 → 다시 말해야 함
 * qr         : 결제 QR 표시
 */
export type OrderPhase = 'idle' | 'listening' | 'processing' | 'retry' | 'qr';

interface OrderState {
  /** 주문 받는 차량 (현재 ready 차량) */
  carNum: string | null;
  phase: OrderPhase;
  transcript: string | null;
  order: ParsedOrder | null;
  paymentUrl: string | null;
  error: string | null;
  /** 주문 받을 차량을 바꾼다. 같은 차량이면 진행 상태를 유지한다. */
  setCar: (carNum: string | null) => void;
  /** 마이크로 한 번 듣고 처리한다. 처리 후 단계를 돌려준다. */
  listen: () => Promise<OrderPhase>;
  /** 인식된(또는 직접 입력한) 문장을 처리한다. */
  submit: (text: string) => Promise<OrderPhase>;
}

const initial = { phase: 'idle' as OrderPhase, transcript: null, order: null, paymentUrl: null, error: null };

export const useOrderStore = create<OrderState>((set, get) => ({
  carNum: null,
  ...initial,

  setCar: (carNum) => {
    if (get().carNum === carNum) return;
    stopListening();
    set({ carNum, ...initial });
  },

  listen: async () => {
    if (!get().carNum) return get().phase;
    set({ phase: 'listening', error: null });
    try {
      const text = await listenOnce();
      return await get().submit(text);
    } catch (e) {
      set({ phase: 'retry', error: e instanceof Error ? e.message : String(e) });
      return 'retry';
    }
  },

  submit: async (text) => {
    const carNum = get().carNum;
    if (!carNum) return get().phase;
    set({ phase: 'processing', transcript: text, error: null });

    const order = parseOrder(text);
    if (!order) {
      set({ phase: 'retry', error: '유종(휘발유/경유)과 금액(예: 5만원)을 함께 말씀해주세요.' });
      return 'retry';
    }

    try {
      await orderFuelType(carNum, order.fuelType); // 유종만 DB에 저장
    } catch (e) {
      set({ phase: 'retry', error: `유종 저장 실패: ${e instanceof Error ? e.message : String(e)}` });
      return 'retry';
    }
    // 다른 차량으로 바뀌었으면 결과를 버린다.
    if (get().carNum !== carNum) return get().phase;

    set({ phase: 'qr', order, paymentUrl: buildPaymentUrl(carNum, order.fuelType, order.amount) });
    return 'qr';
  },
}));
