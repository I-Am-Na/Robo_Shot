import type { BaseResponse } from '@/types/api';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * fetch 래퍼. 백엔드는 실패 시 { success: false, message } 를 돌려주므로
 * HTTP 에러이거나 success=false면 ApiError를 던진다.
 */
export async function request<T extends BaseResponse>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    });
  } catch {
    throw new ApiError('서버에 연결할 수 없습니다.', 0);
  }

  const body = (await res.json().catch(() => null)) as T | null;
  if (!res.ok || !body?.success) {
    throw new ApiError(body?.message ?? `요청 실패 (${res.status})`, res.status);
  }
  return body;
}
