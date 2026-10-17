/** Merge an HTTP snapshot without overwriting newer stream events or resurrecting removed items. */
export function mergeSnapshot<T>(
  current: T[],
  snapshot: T[],
  versions: Record<string, number>,
  requestedSeq: number,
  key: (item: T) => string,
  belongs: (item: T) => boolean,
): T[] {
  const result = new Map(current.map((item) => [key(item), item]));
  const incoming = new Set(snapshot.map(key));
  for (const item of current)
    if (
      belongs(item) &&
      !incoming.has(key(item)) &&
      (versions[key(item)] || 0) <= requestedSeq
    )
      result.delete(key(item));
  for (const item of snapshot)
    if ((versions[key(item)] || 0) <= requestedSeq) result.set(key(item), item);
  return [...result.values()];
}
