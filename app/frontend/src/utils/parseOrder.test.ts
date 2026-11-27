import { formatWon, parseAmount, parseFuelType, parseOrder } from './parseOrder';

describe('parseAmount', () => {
  it.each([
    ['5만원', 50000],
    ['5만 원', 50000],
    ['오만원', 50000],
    ['삼만 오천원', 35000],
    ['3만5천원', 35000],
    ['50,000원', 50000],
    ['50000원', 50000],
    ['십만원', 100000],
    ['만원', 10000],
    ['이만 삼천 오백원', 23500],
    ['15만원', 150000],
  ])('%s → %d', (text, expected) => {
    expect(parseAmount(`휘발유 ${text} 넣어주세요`)).toBe(expected);
  });

  it('returns null without 원', () => {
    expect(parseAmount('휘발유 가득')).toBeNull();
  });
});

describe('parseFuelType', () => {
  it.each([
    ['휘발유 5만원', '휘발유'],
    ['가솔린으로 3만원', '휘발유'],
    ['경유, 5만원', '경유'],
    ['디젤 오만원', '경유'],
  ])('%s → %s', (text, expected) => {
    expect(parseFuelType(text)).toBe(expected);
  });

  it('returns null when both or none are mentioned', () => {
    expect(parseFuelType('휘발유 말고 경유')).toBeNull();
    expect(parseFuelType('5만원 넣어주세요')).toBeNull();
  });
});

describe('parseOrder', () => {
  it('parses "휘발유, 5만원"', () => {
    expect(parseOrder('휘발유, 5만원')).toEqual({ fuelType: '휘발유', amount: 50000 });
  });

  it('returns null when fuel type or amount is missing', () => {
    expect(parseOrder('5만원이요')).toBeNull();
    expect(parseOrder('휘발유요')).toBeNull();
  });
});

it('formatWon', () => {
  expect(formatWon(50000)).toBe('50,000원');
});
