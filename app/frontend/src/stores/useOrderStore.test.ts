import { useOrderStore } from './useOrderStore';

vi.mock('@/services/carService', () => ({ orderFuelType: vi.fn().mockResolvedValue(undefined) }));
vi.mock('@/services/speechRecognition', () => ({
  listenOnce: vi.fn(),
  stopListening: vi.fn(),
}));

import { orderFuelType } from '@/services/carService';
import { listenOnce } from '@/services/speechRecognition';

beforeEach(() => {
  vi.clearAllMocks();
  useOrderStore.setState({ carNum: null });
  useOrderStore.getState().setCar('11가1111');
});

describe('useOrderStore', () => {
  it('saves fuel type and builds payment url from "휘발유, 5만원"', async () => {
    const phase = await useOrderStore.getState().submit('휘발유, 5만원');
    expect(phase).toBe('qr');
    expect(orderFuelType).toHaveBeenCalledWith('11가1111', '휘발유');
    const s = useOrderStore.getState();
    expect(s.order).toEqual({ fuelType: '휘발유', amount: 50000 });
    const url = new URL(s.paymentUrl!);
    expect(url.pathname).toBe('/pay');
    expect(Object.fromEntries(url.searchParams)).toEqual({ car: '11가1111', fuel: '휘발유', amount: '50000' });
  });

  it('asks again when it cannot understand', async () => {
    expect(await useOrderStore.getState().submit('그냥 넣어주세요')).toBe('retry');
    expect(orderFuelType).not.toHaveBeenCalled();
    expect(useOrderStore.getState().error).toContain('유종');
  });

  it('listens with microphone then processes', async () => {
    vi.mocked(listenOnce).mockResolvedValueOnce('경유 삼만원');
    expect(await useOrderStore.getState().listen()).toBe('qr');
    expect(useOrderStore.getState().order).toEqual({ fuelType: '경유', amount: 30000 });
  });

  it('goes to retry on recognition error', async () => {
    vi.mocked(listenOnce).mockRejectedValueOnce(new Error('말소리가 들리지 않았습니다.'));
    expect(await useOrderStore.getState().listen()).toBe('retry');
    expect(useOrderStore.getState().error).toBe('말소리가 들리지 않았습니다.');
  });

  it('resets when ready car changes', async () => {
    await useOrderStore.getState().submit('휘발유 5만원');
    useOrderStore.getState().setCar('22나2222');
    const s = useOrderStore.getState();
    expect([s.carNum, s.phase, s.paymentUrl, s.order]).toEqual(['22나2222', 'idle', null, null]);
  });
});
