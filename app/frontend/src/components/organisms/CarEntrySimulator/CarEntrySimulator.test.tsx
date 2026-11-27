import { fireEvent, render, screen } from '@testing-library/react';
import { CarEntrySimulator } from './CarEntrySimulator';

describe('CarEntrySimulator', () => {
  it('submits car number, selected line and is_line', () => {
    const onEnter = vi.fn();
    render(<CarEntrySimulator onEnter={onEnter} />);

    fireEvent.change(screen.getByLabelText('차량번호'), { target: { value: ' 22나2222 ' } });
    fireEvent.click(screen.getByRole('radio', { name: '2번 라인' }));
    fireEvent.click(screen.getByRole('button', { name: '진입' }));

    expect(onEnter).toHaveBeenCalledWith({ carNum: '22나2222', lineNum: 2, isLine: true });
  });

  it('can send not-in-line entry', () => {
    const onEnter = vi.fn();
    render(<CarEntrySimulator onEnter={onEnter} />);
    fireEvent.change(screen.getByLabelText('차량번호'), { target: { value: '11가1111' } });
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: '진입' }));
    expect(onEnter).toHaveBeenCalledWith({ carNum: '11가1111', lineNum: 1, isLine: false });
  });

  it('disables submit when car number is empty', () => {
    render(<CarEntrySimulator onEnter={vi.fn()} />);
    expect(screen.getByRole('button', { name: '진입' })).toBeDisabled();
  });
});
