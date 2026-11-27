import { ApiError, request } from './apiClient';

function mockFetch(status: number, body: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status })),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('request', () => {
  it('returns body when success is true', async () => {
    mockFetch(200, { success: true, message: 'ok' });
    await expect(request('/line/1')).resolves.toEqual({ success: true, message: 'ok' });
    expect(fetch).toHaveBeenCalledWith('/api/line/1', expect.anything());
  });

  it('throws ApiError with backend message on failure', async () => {
    mockFetch(404, { success: false, message: 'car not found: 99하9999' });
    await expect(request('/car/99하9999')).rejects.toMatchObject({
      name: 'ApiError',
      status: 404,
      message: 'car not found: 99하9999',
    });
  });

  it('throws ApiError when server is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    await expect(request('/line/1')).rejects.toBeInstanceOf(ApiError);
  });
});
