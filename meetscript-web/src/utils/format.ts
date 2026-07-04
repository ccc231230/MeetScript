/**
 * Format milliseconds to human-readable time string.
 * e.g., 3661000 → "1:01:01"
 */
export function formatDuration(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  if (h > 0) {
    return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }
  return `${m}:${String(s).padStart(2, '0')}`;
}

/**
 * Format a timestamp string to local date string.
 */
export function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}

/**
 * Format a timestamp string to local datetime string.
 */
export function formatDateTime(isoString: string): string {
  return new Date(isoString).toLocaleString('zh-CN');
}

/**
 * Format number with locale string (thousands separator).
 */
export function formatNumber(n: number): string {
  return n.toLocaleString('zh-CN');
}

/**
 * Format bytes to human-readable size.
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

/**
 * Format cost in Yuan.
 */
export function formatCost(cost: number): string {
  return `¥${cost.toFixed(6)}`;
}

/**
 * Format a percentage with 1 decimal.
 */
export function formatPercent(value: number, total: number): string {
  if (total === 0) return '0%';
  return `${((value / total) * 100).toFixed(1)}%`;
}
