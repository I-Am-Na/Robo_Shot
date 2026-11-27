import type { FuelType } from '@/types/api';

export interface ParsedOrder {
  fuelType: FuelType;
  amount: number; // 원
}

const FUEL_KEYWORDS: Record<FuelType, string[]> = {
  휘발유: ['휘발유', '가솔린', '일반유'],
  경유: ['경유', '디젤'],
};

const DIGIT: Record<string, number> = {
  영: 0, 공: 0, 일: 1, 이: 2, 삼: 3, 사: 4, 오: 5, 육: 6, 칠: 7, 팔: 8, 구: 9,
};
const SMALL_UNIT: Record<string, number> = { 십: 10, 백: 100, 천: 1000 };

export function parseFuelType(text: string): FuelType | null {
  const found = (Object.keys(FUEL_KEYWORDS) as FuelType[]).filter((fuel) =>
    FUEL_KEYWORDS[fuel].some((k) => text.includes(k)),
  );
  // 둘 다 나오면("휘발유 말고 경유") 판단하지 않는다.
  return found.length === 1 ? found[0] : null;
}

/**
 * 금액 표현을 원 단위 숫자로 바꾼다.
 * "5만원", "5만 원", "오만원", "삼만 오천원", "3만5천원", "50,000원", "50000원", "십만원"
 */
export function parseAmount(text: string): number | null {
  // 금액 부분만 남긴다: 숫자·한글 숫자·단위·쉼표·공백
  const match = text.match(/[0-9,영공일이삼사오육칠팔구십백천만\s]+원/);
  if (!match) return null;
  const expr = match[0].replace(/원$/, '').replace(/[\s,]/g, '');
  if (!expr) return null;

  let total = 0; // 만 단위로 확정된 값
  let section = 0; // 만 아래(천·백·십·일) 누적
  let num = 0; // 지금 읽는 숫자
  let hasNum = false;

  for (let i = 0; i < expr.length; i++) {
    const ch = expr[i];
    if (/[0-9]/.test(ch)) {
      let j = i;
      while (j < expr.length && /[0-9]/.test(expr[j])) j++;
      num = Number(expr.slice(i, j));
      hasNum = true;
      i = j - 1;
    } else if (ch in DIGIT) {
      num = DIGIT[ch];
      hasNum = true;
    } else if (ch in SMALL_UNIT) {
      section += (hasNum ? num : 1) * SMALL_UNIT[ch];
      num = 0;
      hasNum = false;
    } else if (ch === '만') {
      total += (section + (hasNum ? num : 0) || 1) * 10000;
      section = 0;
      num = 0;
      hasNum = false;
    } else {
      return null;
    }
  }
  const amount = total + section + (hasNum ? num : 0);
  return amount > 0 ? amount : null;
}

export function parseOrder(text: string): ParsedOrder | null {
  const fuelType = parseFuelType(text);
  const amount = parseAmount(text);
  if (!fuelType || !amount) return null;
  return { fuelType, amount };
}

export function formatWon(amount: number): string {
  return `${amount.toLocaleString('ko-KR')}원`;
}
