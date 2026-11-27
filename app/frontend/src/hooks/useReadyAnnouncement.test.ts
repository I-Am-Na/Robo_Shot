import { renderHook } from '@testing-library/react';
import type { CarItem } from '@/types/api';
import { useReadyAnnouncement } from './useReadyAnnouncement';

const car = (car_num: string, status: string | null, status_updated_at: string | null = null): CarItem => ({
  car_num,
  is_line: true,
  line_num: 1,
  fuel_type: null,
  status,
  updated_at: '2026-11-27T10:00:00',
  status_updated_at,
});

function setup(initial: CarItem[], enabled = true) {
  const announce = vi.fn();
  const hook = renderHook(
    ({ cars, on }: { cars: CarItem[]; on: boolean }) => useReadyAnnouncement(cars, true, on, announce),
    { initialProps: { cars: initial, on: enabled } },
  );
  return { announce, rerender: (cars: CarItem[], on = enabled) => hook.rerender({ cars, on }) };
}

describe('useReadyAnnouncement', () => {
  it('does not announce cars already ready on first load', () => {
    const { announce } = setup([car('11가1111', 'ready', 't1')]);
    expect(announce).not.toHaveBeenCalled();
  });

  it('announces once when a car becomes ready', () => {
    const { announce, rerender } = setup([car('11가1111', null)]);
    rerender([car('11가1111', 'ready', 't1')]);
    rerender([car('11가1111', 'ready', 't1')]); // 다음 polling에도 같은 ready
    expect(announce).toHaveBeenCalledTimes(1);
    expect(announce.mock.calls[0][0].car_num).toBe('11가1111');
  });

  it('announces waiting car when it is promoted to ready', () => {
    const { announce, rerender } = setup([car('11가1111', 'ready', 't1'), car('22나2222', 'waiting', 't2')]);
    rerender([car('11가1111', 'done', 't3'), car('22나2222', 'ready', 't3')]);
    expect(announce).toHaveBeenCalledTimes(1);
    expect(announce.mock.calls[0][0].car_num).toBe('22나2222');
  });

  it('announces again when the same car is ready on a later visit', () => {
    const { announce, rerender } = setup([car('11가1111', null)]);
    rerender([car('11가1111', 'ready', 't1')]);
    rerender([car('11가1111', 'done', 't2')]);
    rerender([car('11가1111', 'ready', 't9')]);
    expect(announce).toHaveBeenCalledTimes(2);
  });

  it('can watch another status (paid)', () => {
    const announce = vi.fn();
    const { rerender } = renderHook(
      ({ cars }: { cars: CarItem[] }) => useReadyAnnouncement(cars, true, true, announce, 'paid'),
      { initialProps: { cars: [car('11가1111', 'ready', 't1')] } },
    );
    rerender({ cars: [car('11가1111', 'paid', 't2')] });
    rerender({ cars: [car('11가1111', 'paid', 't2')] });
    expect(announce).toHaveBeenCalledTimes(1);
  });

  it('does not announce while disabled', () => {
    const { announce, rerender } = setup([car('11가1111', null)], false);
    rerender([car('11가1111', 'ready', 't1')], false);
    rerender([car('11가1111', 'ready', 't1')], true); // 켜도 이미 지나간 ready는 안내 안 함
    expect(announce).not.toHaveBeenCalled();
  });
});
