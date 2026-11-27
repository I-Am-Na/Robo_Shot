import { render, screen } from '@testing-library/react';
import { FuelLineCard } from './FuelLineCard';

describe('FuelLineCard', () => {
  it('shows fueling state and car number', () => {
    render(
      <FuelLineCard
        lineNum={1}
        line={{ line_num: 1, is_fueling: true, car_num: '12가3456', updated_at: '2026-11-27T10:00:00' }}
      />,
    );
    expect(screen.getByText('1번 라인')).toBeInTheDocument();
    expect(screen.getByText('주유 중')).toBeInTheDocument();
    expect(screen.getByText('12가3456')).toBeInTheDocument();
  });

  it('shows idle state', () => {
    render(<FuelLineCard lineNum={2} line={{ line_num: 2, is_fueling: false, car_num: null, updated_at: null }} />);
    expect(screen.getByText('대기')).toBeInTheDocument();
  });

  it('shows placeholder when data is missing', () => {
    render(<FuelLineCard lineNum={2} />);
    expect(screen.getByText('정보 없음')).toBeInTheDocument();
  });
});
