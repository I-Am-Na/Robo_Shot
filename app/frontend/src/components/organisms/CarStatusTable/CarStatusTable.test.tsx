import { fireEvent, render, screen } from '@testing-library/react';
import type { CarItem } from '@/types/api';
import { CarStatusTable } from './CarStatusTable';

const car = (over: Partial<CarItem>): CarItem => ({
  car_num: '12가3456',
  is_line: true,
  line_num: 1,
  fuel_type: null,
  status: null,
  updated_at: '2026-11-27T10:00:00',
  status_updated_at: null,
  ...over,
});

describe('CarStatusTable', () => {
  it('shows ready status as 주유 준비', () => {
    render(<CarStatusTable cars={[car({ status: 'ready', fuel_type: '경유' })]} />);
    expect(screen.getByText('12가3456')).toBeInTheDocument();
    expect(screen.getByText('주유 준비')).toBeInTheDocument();
    expect(screen.getByText('경유')).toBeInTheDocument();
  });

  it('shows waiting and done labels', () => {
    render(
      <CarStatusTable
        cars={[car({ car_num: '22나2222', status: 'waiting' }), car({ car_num: '33다3333', status: 'done' })]}
      />,
    );
    expect(screen.getByText('대기')).toBeInTheDocument();
    expect(screen.getByText('완료')).toBeInTheDocument();
  });

  it('shows complete button only for ready car', () => {
    const onComplete = vi.fn();
    render(
      <CarStatusTable
        cars={[car({ car_num: '11가1111', status: 'ready' }), car({ car_num: '22나2222', status: 'waiting' })]}
        onComplete={onComplete}
      />,
    );
    const buttons = screen.getAllByRole('button', { name: '주유 완료' });
    expect(buttons).toHaveLength(1);
    fireEvent.click(buttons[0]);
    expect(onComplete).toHaveBeenCalledWith('11가1111');
  });

  it('shows unknown status as raw text', () => {
    render(<CarStatusTable cars={[car({ status: 'something' })]} />);
    expect(screen.getByText('something')).toBeInTheDocument();
  });

  it('shows empty message when no cars', () => {
    render(<CarStatusTable cars={[]} />);
    expect(screen.getByText('감지된 차량이 없습니다.')).toBeInTheDocument();
  });
});
