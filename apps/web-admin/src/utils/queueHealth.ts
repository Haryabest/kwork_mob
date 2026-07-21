export function isPgQueueSynced(
  pgQueued: number,
  redis: { normal: number; high: number },
): boolean {
  const redisTotal = (redis.normal ?? 0) + (redis.high ?? 0);
  return pgQueued === redisTotal;
}
