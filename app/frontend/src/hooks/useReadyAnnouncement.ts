import { useEffect, useRef } from 'react';
import type { CarItem } from '@/types/api';

const statusKey = (car: CarItem) => `${car.car_num}@${car.status_updated_at ?? ''}`;

/**
 * polling으로 받은 차량 목록에서 새로 status(기본 ready)가 된 차량이 있으면 announce를 한 번 호출한다.
 *
 * - 같은 상태 변화는 한 번만 안내한다 (차량번호 + 상태 변경 시각 기준).
 *   다음 방문에서 다시 그 상태가 되면 상태 변경 시각이 달라지므로 다시 안내한다.
 * - 처음 불러온 목록에 이미 그 상태인 차량은 안내하지 않는다 (새로고침 시 반복 방지).
 * - enabled가 false인 동안 생긴 변화도 안내하지 않는다.
 */
export function useReadyAnnouncement(
  cars: CarItem[],
  loaded: boolean,
  enabled: boolean,
  announce: (car: CarItem) => void,
  status: string = 'ready',
) {
  const seen = useRef<Set<string> | null>(null);

  useEffect(() => {
    if (!loaded) return;
    const keys = cars.filter((c) => c.status === status).map(statusKey);

    if (seen.current === null) {
      seen.current = new Set(keys);
      return;
    }

    for (const car of cars) {
      if (car.status !== status) continue;
      const key = statusKey(car);
      if (seen.current.has(key)) continue;
      seen.current.add(key);
      if (enabled) announce(car);
    }
  }, [cars, loaded, enabled, announce, status]);
}
