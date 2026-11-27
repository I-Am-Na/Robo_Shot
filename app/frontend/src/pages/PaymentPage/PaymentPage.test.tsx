import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { PaymentPage } from './PaymentPage';

vi.mock('@/services/paymentService', () => ({ pay: vi.fn() }));
import { pay } from '@/services/paymentService';

const URL_OK = '/pay?car=11%EA%B0%801111&fuel=%ED%9C%98%EB%B0%9C%EC%9C%A0&amount=50000';

const renderAt = (url: string) =>
  render(
    <MemoryRouter initialEntries={[url]}>
      <PaymentPage />
    </MemoryRouter>,
  );

beforeEach(() => vi.clearAllMocks());

describe('PaymentPage', () => {
  it('sends payment to server and shows completion when it returns true', async () => {
    vi.mocked(pay).mockResolvedValueOnce(true);
    renderAt(URL_OK);
    expect(screen.getByText('11가1111')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '50,000원 결제하기' }));
    expect(await screen.findByRole('status')).toHaveTextContent('결제가 완료되었습니다');
    expect(pay).toHaveBeenCalledWith('11가1111', '휘발유', 50000);
  });

  it('shows error and allows retry when payment fails', async () => {
    vi.mocked(pay).mockRejectedValueOnce(new Error('car is not ready'));
    renderAt(URL_OK);
    fireEvent.click(screen.getByRole('button', { name: '50,000원 결제하기' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('car is not ready');
    expect(screen.getByRole('button', { name: '50,000원 결제하기' })).toBeEnabled();
  });

  it('shows error for invalid link', () => {
    renderAt('/pay?car=11');
    expect(screen.getByText(/결제 정보가 올바르지 않습니다/)).toBeInTheDocument();
    expect(pay).not.toHaveBeenCalled();
  });
});
