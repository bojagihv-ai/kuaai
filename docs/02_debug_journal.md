# 디버그 저널 — 카페24 + 로젠 송장 자동등록

## 타임라인 (2026-02-06 ~ 2026-02-07)

| 시점 | 이벤트 | 커밋 |
|---|---|---|
| 02-06 | 로젠 x 카페24 송장 매니저 초기 버전 생성 | `b56460b` |
| 02-07 초반 | 카페24 OAuth 설정 시작. Mall ID 오류 (DNS 에러) | — |
| 02-07 | invalid_scope 에러 → scope 이름 수정 | — |
| 02-07 | 인증 코드 만료 (30초) → 재시도 성공 | — |
| 02-07 | file:// 프로토콜 CORS 차단 → 카페24 FTP 업로드 | — |
| 02-07 | FTP 경로 오류 (/logen/ → /web/logen/) | — |
| 02-07 | CORS 여전히 차단 → Vercel 서버사이드 프록시 생성 | `2ae8795` |
| 02-07 | API 버전 2024-06-01 → 2025-12-01 수정 + 토큰 자동갱신 | `df6822a` |
| 02-07 | GitHub → Vercel 자동 배포 파이프라인 구성 | — |
| 02-07 | 로젠 엑셀 파싱 0건 → 헤더 자동감지 로직 구현 | `5fc8023` |
| 02-07 | 서브헤더 행이 데이터로 표시 → 숫자 필터 추가 | `7b91c3a` |
| 02-07 | fulfillments 404 에러 → shipments 엔드포인트로 변경 | `75e15ef` |
| 02-07 | insufficient_scope → mall.write_order 스코프 추가 | — |
| 02-07 | shipping_company_code 0014 → 0004 수정 + status 필드 추가 | `562faaa` |
| 02-07 | **송장등록 최초 성공** (주문 2건) | — |
| 02-07 | 배송조회 "데모 수령인" → 로젠 Open API 시도 (타임아웃) | `9739aba` |
| 02-07 | tracker.delivery API로 변경 | `0f0b219` |

---

## 막혔던 지점 Top 10

### 1. DNS_PROBE_FINISHED_NXDOMAIN — Mall ID 오류

| 항목 | 내용 |
|---|---|
| **증상** | `03030.cafe24api.com` 접속 시 DNS 에러 |
| **에러** | `DNS_PROBE_FINISHED_NXDOMAIN` |
| **원인** | 도메인 이름(`03030`)을 Mall ID로 사용. 카페24 Mall ID는 카페24 가입 시 생성한 고유 ID |
| **해결** | Mall ID를 `bojagi1928`로 변경 |
| **재현** | 설정 탭 > Mall ID에 `03030` 입력 → 주문 조회 |
| **검증** | Mall ID `bojagi1928` 입력 후 주문 조회 성공 |
| **재발방지** | Mall ID = `{mallid}.cafe24.com`의 `{mallid}` 부분 |

---

### 2. invalid_scope — OAuth 스코프 이름 오류

| 항목 | 내용 |
|---|---|
| **증상** | OAuth 인증 URL 접속 시 `invalid_scope` 에러 페이지로 리다이렉트 |
| **에러** | `error=invalid_scope` |
| **원인** | `mall.write_fulfillment` 등 존재하지 않는 스코프 이름 사용 |
| **해결** | 정확한 스코프: `mall.read_order,mall.read_shipping,mall.write_shipping,mall.write_order` |
| **재현** | OAuth URL의 scope에 `mall.write_fulfillment` 포함 |
| **검증** | 올바른 scope로 인증 → 인증 코드 정상 발급 |
| **재발방지 체크** | 1) 카페24 개발자센터에서 사용 가능한 scope 목록 확인 → 2) 정확한 이름 사용 |

---

### 3. CORS 차단 — 브라우저에서 카페24 API 직접 호출 불가

| 항목 | 내용 |
|---|---|
| **증상** | "Failed to fetch" 에러. 콘솔에 CORS 에러 |
| **에러** | `Access-Control-Allow-Origin` 헤더 없음 |
| **원인** | 카페24 API 서버는 브라우저 CORS 요청을 허용하지 않음 |
| **시도 1 (실패)** | `file:///` 에서 직접 호출 → CORS 차단 |
| **시도 2 (실패)** | `03030.co.kr` (카페24 FTP)에서 호출 → 여전히 CORS 차단 |
| **최종 해결** | Vercel Serverless Function (`/api/cafe24.js`)으로 서버사이드 프록시 구현 |
| **검증** | `kuaai.vercel.app`에서 주문 조회 성공 |
| **핵심 깨달음** | 카페24 API는 **무조건** 서버사이드 프록시 필요. 어떤 도메인에서든 브라우저 직접 호출 불가 |

---

### 4. 로젠 엑셀 파싱 0건 — 특수 엑셀 구조

| 항목 | 내용 |
|---|---|
| **증상** | 로젠 결과 엑셀 업로드 → "0건의 데이터를 읽었습니다" |
| **원인** | 로젠 WEB-EDI 출력 엑셀 구조가 특수함: 제목행 → 병합셀 헤더 → 서브헤더 → 데이터 → 합계행 |
| **SheetJS 동작** | `{header: 1}` 옵션으로 파싱 시 첫 행이 헤더가 아닌 제목행이 됨 |
| **해결** | 전체 행을 스캔하여 '운송장번호' 텍스트가 있는 행을 헤더로 자동 감지 |
| **검증** | 로젠 엑셀 업로드 → 2건 이상 정상 파싱 |
| **핵심 코드** | `if (rowStrs.some(c => c === '운송장번호'))` → 해당 행을 헤더로 설정 |

---

### 5. 서브헤더 행이 데이터로 표시

| 항목 | 내용 |
|---|---|
| **증상** | 테이블 첫 행에 "주문번호 / 이름 / 물품명 / 운송장번호" 텍스트가 데이터로 표시, 등록 시도하면 실패 |
| **원인** | 로젠 엑셀에 컬럼명 서브헤더 행이 있는데 이것이 데이터로 파싱됨 |
| **해결** | 운송장번호가 숫자가 아닌 행은 필터링: `!/^\d+$/.test(trackingNo)` |
| **추가 필터** | `trackingNo === '합계'` 행도 제외 |
| **검증** | 엑셀 업로드 후 테이블에 실제 데이터만 표시 |

---

### 6. fulfillments API 404 — 엔드포인트 변경

| 항목 | 내용 |
|---|---|
| **증상** | 송장등록 시 `{"error":{"code":404,"message":"No API found."}}` |
| **에러** | `POST /api/v2/admin/orders/{id}/fulfillments` → 404 |
| **원인** | 카페24 API v2025-12-01에서 `fulfillments` 엔드포인트가 `shipments`로 변경됨 |
| **해결** | 엔드포인트를 `/shipments`로 변경 |
| **검증** | `POST /api/v2/admin/orders/{id}/shipments` → 정상 응답 |

---

### 7. insufficient_scope — 권한 부족

| 항목 | 내용 |
|---|---|
| **증상** | `{"error":{"code":403,"message":"...insufficient_scope..."}}` |
| **원인** | `mall.write_shipping` 스코프만으로는 `/shipments` 엔드포인트 접근 불가 |
| **해결** | 카페24 앱에 `mall.write_order` 스코프 추가 → **재인증** |
| **검증** | 새 토큰의 `scopes`에 `mall.write_order` 포함 확인 |
| **핵심 깨달음** | 스코프 추가 후 반드시 **재인증**(새 토큰 발급)해야 적용됨. 기존 토큰에는 반영 안 됨 |

---

### 8. 택배사 코드 불일치 — 0014 vs 0004

| 항목 | 내용 |
|---|---|
| **증상** | `{"error":{"code":422,"message":"It is an unregistered delivery company."}}` |
| **원인** | 일반적인 로젠 코드 `0014`가 아니라 해당 쇼핑몰에 등록된 코드가 `0004` |
| **발견 방법** | `GET /api/v2/admin/shipping` → `shipping_company_type[0].shipping_carrier_code` = `"0004"` |
| **해결** | `shipping_company_code: '0004'` |
| **핵심 깨달음** | 택배사 코드는 **쇼핑몰마다 다를 수 있음**. API로 조회해서 확인 필수 |

---

### 9. status 필수 필드 누락

| 항목 | 내용 |
|---|---|
| **증상** | `{"error":{"code":422,"message":"[Order status] is a required field. (parameter.status)"}}` |
| **원인** | `/shipments` POST body에 `status` 필드가 빠져 있음 |
| **해결** | `status: 'standby'` 추가 (배송대기 상태) |
| **검증** | API 호출 성공 + 카페24 관리자에서 주문이 "배송대기관리"로 이동 확인 |

---

### 10. 배송조회 데모 데이터 / fetch failed

| 항목 | 내용 |
|---|---|
| **증상** (1단계) | 모든 항목이 "데모 수령인" + 랜덤 상태 표시 |
| **원인** | 로젠 웹사이트 직접 호출 → CORS → catch에서 데모 데이터 생성 |
| **해결 시도 1** | 로젠 Open API (`openapi.ilogen.com`) → 타임아웃 (기업 IP 등록 필요 추정) |
| **증상** (2단계) | "배송 조회 실패: fetch failed" |
| **최종 해결** | `tracker.delivery` API 사용 (무료, 공개 REST API) |
| **참고** | 방금 등록한 송장은 "배송준비" 표시 (로젠에서 스캔 전까지 데이터 없음) |

---

## 결정적 힌트 / 깨달음

### 1. "카페24 API는 무조건 서버 프록시"
> 카페24 API 서버는 `Access-Control-Allow-Origin`을 반환하지 않는다.
> `file://`, `03030.co.kr`, `localhost` 어디서든 CORS 에러가 발생한다.
> **유일한 해결책**: 서버사이드 프록시 (Vercel Serverless / Express / Cloud Function).

### 2. "스코프 추가 = 재인증"
> 카페24 개발자센터에서 앱 권한(scope)을 추가한 뒤,
> **기존 토큰은 이전 scope만 가지고 있다**.
> 반드시 새 인증 코드 → 새 토큰을 발급받아야 추가된 scope가 적용된다.

### 3. "택배사 코드는 API로 조회"
> 로젠택배의 "일반적인" 코드(0014)와 카페24에 **등록된** 코드(0004)가 다를 수 있다.
> `GET /api/v2/admin/shipping` → `shipping_company_type` 배열에서 확인.

### 4. "fulfillments → shipments"
> 카페24 API v2025-12-01에서 송장등록 엔드포인트가 변경됐다.
> 이전 버전 문서를 참고하면 `fulfillments`로 안내되지만, 최신 버전에서는 404.

### 5. "로젠 엑셀은 보이는 대로가 아니다"
> 로젠 WEB-EDI 출력 엑셀은 병합셀, 다중 헤더, 합계행이 포함된 특수 구조.
> SheetJS로 파싱할 때 `header: 1` (배열모드)로 읽고,
> '운송장번호' 텍스트가 있는 행을 찾아서 그 다음부터 데이터로 처리.

### 6. "status: 'standby'는 필수"
> `/shipments` POST에서 `status`는 필수 파라미터.
> 이 값이 없으면 422 에러.
> `standby` = 배송대기 (카페24에서 "배송대기관리"로 이동).

### 7. "인증 코드는 30초"
> 카페24 OAuth 인증 코드는 극히 짧은 시간 내에 토큰으로 교환해야 한다.
> 인증 코드 받은 직후 **즉시** curl로 교환 실행.

### 8. "order_item_code 자동 조회"
> 로젠 엑셀에는 `order_item_code`가 없다.
> 프록시에서 `orderItemCode`가 비어있으면 주문상세 API를 먼저 호출해서 자동으로 채운다.
> 예: 주문번호 `20260207-0000028` → `order_item_code`: `20260207-0000028-01`
