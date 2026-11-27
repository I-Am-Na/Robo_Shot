import { fireEvent, render, screen } from '@testing-library/react';
import { Button } from './Button';

describe('Button', () => {
  it('renders label and handles click', () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>새로고침</Button>);
    fireEvent.click(screen.getByRole('button', { name: '새로고침' }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('does not fire click when disabled', () => {
    const onClick = vi.fn();
    render(
      <Button onClick={onClick} disabled>
        새로고침
      </Button>,
    );
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).not.toHaveBeenCalled();
  });
});
