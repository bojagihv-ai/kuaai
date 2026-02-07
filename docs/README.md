# docs/ — 카페24 + 로젠택배 송장 자동등록 프로그램 문서

## 문서 목차

| # | 문서 | 설명 | 대상 |
|---|---|---|---|
| 0 | [00_overview.md](./00_overview.md) | 프로젝트 개요, 시스템 아키텍처, 핵심 결정 | 전체 파악 |
| 1 | [01_runbook.md](./01_runbook.md) | 설치 체크리스트, 매일 운영 루틴, 장애 대응 | 운영자/초보자 |
| 2 | [02_debug_journal.md](./02_debug_journal.md) | 개발 타임라인, 에러 Top 10, 결정적 깨달음 | 개발자/디버깅 |

## 빠른 참조

### 문제 발생 시 체크 순서

```
1. 토큰 만료? → 설정 탭에서 Refresh Token 확인 → 2주 지나면 재인증
2. CORS 에러? → kuaai.vercel.app 에서 접속하고 있는지 확인
3. 송장등록 실패? → 01_runbook.md 5-5 ~ 5-8 확인
4. 엑셀 파싱 0건? → 01_runbook.md 5-9 ~ 5-10 확인
5. 배송조회 안 됨? → 01_runbook.md 5-11 확인
```

### 핵심 설정값 (민감정보 마스킹)

| 항목 | 값 |
|---|---|
| Mall ID | `bojagi1928` |
| API Version | `2025-12-01` |
| 택배사 코드 (로젠) | `0004` |
| 배송 상태값 | `standby` |
| 필수 Scopes | `mall.read_order, mall.read_shipping, mall.write_shipping, mall.write_order` |

### 파일 구조

```
kuaai/
├── logen-cafe24.html    # 메인 UI (5탭 SPA)
├── logen-cafe24.js      # 클라이언트 로직
├── logen-cafe24.css     # 스타일
├── api/
│   ├── cafe24.js        # 카페24 API 프록시 (Vercel Serverless)
│   └── logen.js         # 배송조회 프록시 (tracker.delivery)
├── vercel.json          # Vercel 라우팅
└── docs/
    ├── README.md         # 이 파일
    ├── 00_overview.md    # 프로젝트 개요
    ├── 01_runbook.md     # 운영 런북
    └── 02_debug_journal.md # 디버그 저널
```

---

*최종 업데이트: 2026-02-07*
*작성: Claude Code (Anthropic)*
