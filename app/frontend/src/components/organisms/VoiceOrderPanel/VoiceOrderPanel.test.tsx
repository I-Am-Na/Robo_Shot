import { fireEvent, render, screen } from '@testing-library/react';
import { VoiceOrderPanel, type VoiceOrderPanelProps } from './VoiceOrderPanel';

const props = (over: Partial<VoiceOrderPanelProps> = {}): VoiceOrderPanelProps => ({
  carNum: '11가1111',
  phase: 'idle',
  transcript: null,
  error: null,
  order: null,
  paymentUrl: null,
  canListen: true,
  onListen: vi.fn(),
  ...over,
});

describe('VoiceOrderPanel', () => {
  it('shows QR with fuel type and amount', () => {
    render(
      <VoiceOrderPanel
        {...props({
          phase: 'qr',
          order: { fuelType: '휘발유', amount: 50000 },
          paymentUrl: 'http://localhost/pay?car=11',
        })}
      />,
    );
    expect(screen.getByTitle('결제 QR 코드')).toBeInTheDocument();
    expect(screen.getByText('휘발유')).toBeInTheDocument();
    expect(screen.getByText('50,000원')).toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument(); // 개발 모드 아니면 링크 없음
  });

  it('shows payment page link in dev mode', () => {
    render(
      <VoiceOrderPanel
        {...props({
          phase: 'qr',
          order: { fuelType: '휘발유', amount: 50000 },
          paymentUrl: 'http://localhost/pay?car=11',
          showTextInput: true,
          onSubmitText: vi.fn(),
        })}
      />,
    );
    expect(screen.getByRole('link', { name: /결제 페이지 열기/ })).toHaveAttribute('href', 'http://localhost/pay?car=11');
  });

  it('shows transcript and retry message', () => {
    render(<VoiceOrderPanel {...props({ phase: 'retry', transcript: '그냥요', error: '다시 말씀해주세요.' })} />);
    expect(screen.getByText(/그냥요/)).toBeInTheDocument();
    expect(screen.getByText('다시 말씀해주세요.')).toBeInTheDocument();
  });

  it('calls onListen and onSubmitText', () => {
    const onListen = vi.fn();
    const onSubmitText = vi.fn();
    render(<VoiceOrderPanel {...props({ onListen, onSubmitText, showTextInput: true })} />);
    fireEvent.click(screen.getByRole('button', { name: '말하기' }));
    expect(onListen).toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText('주문 직접 입력'), { target: { value: '경유 3만원' } });
    fireEvent.click(screen.getByRole('button', { name: '입력' }));
    expect(onSubmitText).toHaveBeenCalledWith('경유 3만원');
  });
});
