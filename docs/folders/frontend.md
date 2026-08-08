# frontend/

**Owner:** Nguyễn Thị Ánh Ngọc + Đỗ Ngọc Tân
**Vai trò:** Next.js 15 + Tailwind — **chỉ hiển thị** số backend trả về.
**Disclaimer:** mọi khu vực kết quả phải có [`../disclaimer.md`](../disclaimer.md).

## Nhiệm vụ

- Console 5+ khu vực: overview, data, regime, scenarios, risk, quantum, report…
- Run selector, theme, tables — sort/filter client-side trên data API.
- Deploy Pages (static) qua `.github/workflows/deploy-pages.yml`.

## Cây chính

```text
frontend/
  app/(console)/{overview,data,regime,scenarios,risk,quantum,report}/
  app/layout.tsx, page.tsx, globals.css
  lib/          # types từ OpenAPI, API client
  public/
```

## Được làm

- UI/UX, copy, loading/error states.
- Gọi API; hiển thị gate status, solver identity, limitations.
- `yarn types` sau khi backend đổi schema (nếu có script).

## Không được làm

- Tính CVaR, ranking, QUBO, materiality trên client (CLAUDE quy tắc 10).
- Tuyên bố quantum advantage / “khuyến nghị đầu tư” trên UI.
- Giấu `actual_solver=exact` khi user chọn QAOA mà timeout.

## Context cho Claude

```bash
cd frontend && yarn install && yarn dev
cd frontend && yarn types   # nếu có script sinh types từ OpenAPI
cd frontend && yarn build:pages   # GitHub Pages
```

Docker cùng backend:

```bash
docker compose up --build
```

- Artifact là nguồn sự thật nếu UI lệch số.
- UAT cases tối thiểu: workflow-v2 §17.4.
- Design: theo shell hiện có; không thêm chatbot / biểu đồ ngoài phạm vi đã định.

## Không cần test Python

Kiểm tra thủ công / Playwright nếu team có; typecheck qua build (`yarn build`).
