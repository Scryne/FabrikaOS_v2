import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';

import { useSimdi } from './useSimdi';

describe('useSimdi', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('başlangıçta şimdiyi verir ve aralıkta bir ilerler', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-11-03T08:00:00Z'));
    const { result } = renderHook(() => useSimdi(60_000));
    expect(result.current).toBe(Date.parse('2026-11-03T08:00:00Z'));

    act(() => {
      vi.advanceTimersByTime(60_000);
    });
    expect(result.current).toBe(Date.parse('2026-11-03T08:01:00Z'));
  });
});
