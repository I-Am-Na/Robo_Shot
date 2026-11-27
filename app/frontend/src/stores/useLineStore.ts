import { create } from 'zustand';
import { getFuelLine } from '@/services/lineService';
import type { FuelLine, LineNum } from '@/types/api';

export const LINE_NUMS: LineNum[] = [1, 2];

interface LineState {
  lines: Partial<Record<LineNum, FuelLine>>;
  loading: boolean;
  error: string | null;
  fetchLines: () => Promise<void>;
}

export const useLineStore = create<LineState>((set) => ({
  lines: {},
  loading: false,
  error: null,
  fetchLines: async () => {
    set({ loading: true, error: null });
    try {
      const result = await Promise.all(LINE_NUMS.map(getFuelLine));
      set({ lines: Object.fromEntries(result.map((l) => [l.line_num, l])), loading: false });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : String(e), loading: false });
    }
  },
}));
