import type { NextConfig } from "next";
import path from "path";

/**
 * GitHub Pages chỉ serve file tĩnh → bật static export khi GITHUB_PAGES=true.
 *
 * Project site URL mặc định: https://<user>.github.io/<repo>/
 * → basePath phải khớp tên repo (NOVARIS). Override bằng NEXT_BASE_PATH=""
 * nếu dùng custom domain hoặc user/org site (root).
 */
const isGitHubPages = process.env.GITHUB_PAGES === "true";
const rawBasePath = process.env.NEXT_BASE_PATH ?? (isGitHubPages ? "/NOVARIS" : "");
const basePath = rawBasePath.replace(/\/$/, "");

const nextConfig: NextConfig = {
  // Cho client + metadata dùng chung basePath (Images / favicon)
  env: {
    NEXT_PUBLIC_BASE_PATH: basePath,
  },
  turbopack: {
    root: path.join(__dirname),
  },
  ...(isGitHubPages
    ? {
        output: "export" as const,
        // GH Pages map /overview/ → overview/index.html
        trailingSlash: true,
        // next/image optimizer cần Node server — tắt khi export
        images: { unoptimized: true },
        ...(basePath
          ? {
              basePath,
              assetPrefix: basePath,
            }
          : {}),
      }
    : {}),
};

export default nextConfig;
