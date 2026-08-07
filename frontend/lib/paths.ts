/**
 * Prefix đường dẫn public asset khi deploy dưới basePath (GitHub Pages /NOVARIS).
 * next/image + metadata icons không luôn tự nối basePath khi `images.unoptimized`.
 */
export function assetPath(path: string): string {
  const base = (process.env.NEXT_PUBLIC_BASE_PATH ?? "").replace(/\/$/, "");
  if (!path.startsWith("/")) return path;
  if (!base) return path;
  return `${base}${path}`;
}
