import { AxiosError } from 'axios';
import { describe, expect, it } from 'vitest';
import { getApiError } from './api';

describe('getApiError', () => {
  it('возвращает строковый detail из ответа API', () => {
    const err = new AxiosError('Request failed');
    err.response = { data: { detail: 'Недостаточно прав' } } as never;
    expect(getApiError(err)).toBe('Недостаточно прав');
  });

  it('склеивает массив ошибок валидации', () => {
    const err = new AxiosError('Unprocessable');
    err.response = {
      data: { detail: [{ msg: 'field required' }, { msg: 'invalid email' }] },
    } as never;
    expect(getApiError(err)).toBe('field required, invalid email');
  });

  it('обрабатывает обычные Error', () => {
    expect(getApiError(new Error('boom'))).toBe('boom');
  });

  it('фолбэк для неизвестных значений', () => {
    expect(getApiError('strange')).toBe('Ошибка запроса');
  });
});
