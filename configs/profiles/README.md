# Q-SHIELD Configuration Profiles

**Cap nhat 2026-08-06: team da thong nhat chot `workflow_update` la baseline san pham chinh thuc.**
Day khong con la mot trong hai huong "song song ngang hang" nua — `workflow_update` la dich ma toan
bo 5 package phai build toi; `demo_fast` van giu lai cho vong lap dev/debug nhanh, khong bi xoa.

- `demo_fast.yaml`: scope rut gon, bam theo code hien tai de chay end-to-end som/debug. Trang thai
  `NON_BASELINE_RUN`.
- `workflow_update.yaml`: baseline chinh thuc, chot theo Product docs (mvp_scope, product_requirements,
  user_stories_backlog, acceptance_criteria, rtm). Trang thai `BASELINE_TARGET` — code cho scope nay
  **chua duoc viet xong** (xem `docs/limitations.md` §1 de biet phan nao con thieu o tung package).

## Cach Dung

Trong giai doan hien tai, cac file `configs/universe.yaml`, `configs/scenarios.yaml`,
`configs/risk.yaml`, `configs/quantum.yaml` van la config module dang duoc code doc truc tiep.
Hai profile o day dong vai tro la contract cap cao de:

1. Lam ro run dang thuoc mode nao.
2. Tranh lay thong so cua demo nhanh de danh gia workflow full.
3. Lam checklist cho tung module khi nang cap code.
4. Tao co so sau nay them tham so `--profile demo_fast|workflow_update`.

## Nguyen Tac

Khong tron hai profile trong mot run. Neu chay demo nhanh thi bao cao la `NON_BASELINE_RUN`.
Neu chay workflow update thi moi duoc dung lam baseline/UAT chinh, sau khi cac owner duyet
data source, scenario gate, risk candidate ranking va quantum benchmark.

## Khac Biet Cot Loi

| Hang muc | Demo nhanh | Workflow update |
|---|---:|---:|
| Universe dau vao | 8 ma tam | 30 ma VN30 snapshot |
| Muc dich | Demo end-to-end nhanh | Baseline san pham/UAT |
| Scenarios | 500 mac dinh, co the thu 2,000/5,000 | 2,000 dev / 5,000 final |
| Risk candidate | 8 ma co dinh | Risk chon dynamic top 10 tu 30 ma |
| Action | 1 muc: giam 20% | 4 muc: 0/10/20/30% |
| Quantum variables | K=3 action binary | 10 ma x 2 bit = 20 bit |
| Exact search | nho, de demo | 2^20 = 1,048,576 states |
| Ket qua | Bang chung demo | Bang chung chuan workflow |

## Xem Them

- `configs/provisional/README.md` — override Decision-package / bakeoff (không phải baseline).
- `README.md` (goc repo) — muc "Profile: demo_fast vs workflow_update" giai thich code hien tai
  dang o mode nao.
- `docs/limitations.md` §1 — bang so sanh `workflow_update` (baseline chinh thuc) vs `demo_fast`
  (code hien tai), chi tiet tung thong so con thieu.
- `CLAUDE.md` muc "Dong bang pham vi" — 30 ma VN30/top-10/20-bit da duoc bo khoi danh sach dong
  bang tu 2026-08-06; cac muc con lai (chatbot, CVAE, hardware that,...) van dong bang nhu cu.
- `docs/Structure.md` §1.1, dong `configs/` — vi tri thu muc nay trong cay tong the.
