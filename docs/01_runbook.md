# 운영 런북 — 로젠 x 카페24 송장 매니저

## 1. 최초 설치 체크리스트 (초보자 기준)

### 1-1. 카페24 개발자센터 앱 생성

- [ ] https://developers.cafe24.com 로그인
- [ ] **내 앱 관리** → **앱 만들기**
- [ ] App URL: `https://03030.co.kr/`
- [ ] Redirect URI: `https://03030.co.kr/`
- [ ] **권한(Scope) 설정** — 아래 4개 반드시 체크:
  - `mall.read_order` (주문 읽기)
  - `mall.read_shipping` (배송 읽기)
  - `mall.write_shipping` (배송 쓰기)
  - `mall.write_order` (주문 쓰기) ← **필수! 이게 없으면 송장등록 실패**
- [ ] Client ID, Client Secret 메모

### 1-2. OAuth 인증 (토큰 발급)

아래 URL을 **브라우저에 복사 → 접속 → 권한 허용**:

```
https://bojagi1928.cafe24api.com/api/v2/oauth/authorize?response_type=code&client_id=***CLIENT_ID***&state=&redirect_uri=https://03030.co.kr/&scope=mall.read_order,mall.read_shipping,mall.write_shipping,mall.write_order
```

- 리다이렉트된 URL에서 `?code=XXXXXX` 부분이 **인증 코드**
- 인증 코드는 **30초 이내** 사용해야 함 (만료 빠름)

토큰 교환 (터미널/PowerShell):
```bash
curl -X POST "https://bojagi1928.cafe24api.com/api/v2/oauth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Authorization: Basic $(echo -n '***CLIENT_ID***:***CLIENT_SECRET***' | base64)" \
  -d "grant_type=authorization_code&code=여기에_코드&redirect_uri=https://03030.co.kr/"
```

응답에서 `access_token`, `refresh_token` 메모.

### 1-3. 웹 앱 설정

- [ ] https://kuaai.vercel.app/logen-cafe24.html 접속
- [ ] **설정** 탭에서 입력:

| 필드 | 값 |
|---|---|
| 쇼핑몰 ID | `bojagi1928` |
| Client ID | `***` (개발자센터에서 복사) |
| Client Secret | `***` (개발자센터에서 복사) |
| Access Token | `***` (토큰 교환 응답) |
| Refresh Token | `***` (토큰 교환 응답) |
| 로젠 고객코드 | `***` |
| 보내는 사람 | `***` |

- [ ] **카페24 설정 저장** 클릭
- [ ] **로젠 설정 저장** 클릭
- [ ] 연동 상태: `카페24: 연결됨` 확인

---

## 2. 환경/버전 정보

| 항목 | 값 |
|---|---|
| 호스팅 | Vercel (자동 배포: GitHub main 브랜치) |
| 카페24 API 버전 | `2025-12-01` |
| 카페24 Mall ID | `bojagi1928` |
| 배송조회 API | tracker.delivery (V1 REST, 무료) |
| 로젠 WEB-EDI | https://logis.ilogen.com |
| 엑셀 파싱 | SheetJS (xlsx) v0.20.1 CDN |
| 브라우저 | Chrome / Edge 권장 |
| 도메인 | kuaai.vercel.app |

---

## 3. 설정값 목록

### 카페24 API

| 키 | 값 | localStorage 키 |
|---|---|---|
| Mall ID | `bojagi1928` | `lc_cafe24_mall_id` |
| Client ID | `***` | `lc_cafe24_client_id` |
| Client Secret | `***` | `lc_cafe24_client_secret` |
| Access Token | `***` (2시간 유효) | `lc_cafe24_token` |
| Refresh Token | `***` (2주 유효) | `lc_cafe24_refresh_token` |
| API Version | `2025-12-01` | (코드에 하드코딩) |
| Scopes | `mall.read_order,mall.read_shipping,mall.write_shipping,mall.write_order` | — |

### 카페24 API 고정값 (코드에 하드코딩)

| 키 | 값 | 비고 |
|---|---|---|
| shipping_company_code | `0004` | 로젠택배 (카페24 등록 코드) |
| status | `standby` | 배송대기 상태 |
| order_status (조회) | `N20` | 배송준비중 |
| shop_no | `1` | 기본 쇼핑몰 |

### 로젠택배

| 키 | 값 | localStorage 키 |
|---|---|---|
| 고객코드 | `***` | `lc_logen_customer_code` |
| 보내는분 | `***` | `lc_logen_sender_name` |
| 연락처 | `***` | `lc_logen_sender_tel` |
| 주소 | `***` | `lc_logen_sender_addr` |
| 우편번호 | `***` | `lc_logen_sender_zipcode` |

---

## 4. 매일 운영 루틴 (송장처리 플로우)

### 매일 아침 (주문 처리)

```
1. kuaai.vercel.app/logen-cafe24.html 접속
2. [주문 조회] 탭 클릭
3. 기간 설정 (보통 오늘~어제) → '주문 가져오기' 클릭
4. 미발송 주문이 테이블에 표시됨
5. 전체 선택 (또는 개별 선택) → '선택 주문 → 송장 발급 탭으로' 클릭
```

### 로젠 EDI 처리

```
6. [송장 발급] 탭 → '로젠 EDI 엑셀 다운로드' 클릭
7. 다운로드된 엑셀 파일을 로젠 WEB-EDI에 업로드
   - logis.ilogen.com 접속 → 로그인 → EDI 접수
8. 로젠에서 운송장번호 배정 완료 후 결과 엑셀 다운로드
```

### 카페24 송장 등록

```
9. [송장 등록] 탭 → '방법 1: 로젠 결과 파일 업로드' 에 엑셀 드래그앤드롭
10. 파싱된 데이터 확인 (주문번호, 수령인, 송장번호)
11. '카페24에 송장번호 일괄 등록' 클릭
12. 각 건별 성공/실패 표시 확인
13. 카페24 관리자에서 '배송대기관리'로 이동 확인
```

### 배송 추적 (필요시)

```
14. [배송 조회] 탭 → '전체 배송현황 조회' 클릭
15. 각 송장의 현재 배송 상태 확인
    - 배송준비: 아직 택배사 스캔 전
    - 집하/간선상차: 택배 이동 중
    - 배달완료: 수령 완료
```

---

## 5. 장애 발생 시 대응 — 에러별 증상/원인/해결

### 5-1. "실 API 연동 필요" / 데모 데이터만 표시

| 항목 | 내용 |
|---|---|
| **증상** | 주문 조회 시 데모 데이터만 나오고 실제 주문이 안 나옴 |
| **체크 1** | 설정 탭에서 Access Token이 입력되어 있는지 확인 |
| **체크 2** | `file:///` 주소로 접속하고 있지 않은지 확인 → `kuaai.vercel.app` 사용 |
| **체크 3** | Access Token이 만료(2시간)됐는지 확인 → Refresh Token으로 자동 갱신 |

### 5-2. "Failed to fetch" / 네트워크 에러

| 항목 | 내용 |
|---|---|
| **증상** | API 호출 시 "Failed to fetch" 에러 |
| **체크 1** | 인터넷 연결 확인 |
| **체크 2** | Mall ID가 정확한지 확인 (`bojagi1928`) |
| **체크 3** | Vercel 배포 상태 확인 (kuaai.vercel.app 접속 가능?) |

### 5-3. DNS_PROBE_FINISHED_NXDOMAIN

| 항목 | 내용 |
|---|---|
| **증상** | `xxx.cafe24api.com` 접속 불가 |
| **원인** | Mall ID를 도메인(예: `03030`)으로 입력함 |
| **해결** | 카페24 Mall ID는 **카페24 쇼핑몰 ID** (예: `bojagi1928`) |

### 5-4. "invalid_scope" 에러

| 항목 | 내용 |
|---|---|
| **증상** | OAuth 인증 시 `invalid_scope` 에러 |
| **원인** | 존재하지 않는 scope 이름 사용 |
| **해결** | 정확한 scope: `mall.read_order,mall.read_shipping,mall.write_shipping,mall.write_order` |

### 5-5. "insufficient_scope" 에러

| 항목 | 내용 |
|---|---|
| **증상** | 송장등록 시 403 에러 + "insufficient_scope" |
| **원인** | `mall.write_order` 권한이 앱에 없거나 토큰에 포함 안 됨 |
| **체크 1** | 카페24 개발자센터 → 앱 → 권한에 `mall.write_order` 추가 |
| **체크 2** | 권한 추가 후 **반드시 재인증** (새 scope로 토큰 재발급) |

### 5-6. "No API found" (404)

| 항목 | 내용 |
|---|---|
| **증상** | 송장등록 API 호출 시 404 에러 |
| **원인** | `fulfillments` 엔드포인트 사용 (API v2025-12-01에서 삭제됨) |
| **해결** | `shipments` 엔드포인트 사용 — 코드에 이미 반영됨 |

### 5-7. "unregistered delivery company" (422)

| 항목 | 내용 |
|---|---|
| **증상** | 송장등록 시 "It is an unregistered delivery company" |
| **원인** | `shipping_company_code`가 카페24에 등록된 코드와 불일치 |
| **해결** | 로젠택배 코드 = **`0004`** (0014 아님). 코드에 이미 반영됨 |
| **확인 방법** | 카페24 API로 등록된 택배사 조회: `GET /api/v2/admin/shipping` 응답의 `shipping_company_type` 확인 |

### 5-8. "status is a required field" (422)

| 항목 | 내용 |
|---|---|
| **증상** | 송장등록 시 "[Order status] is a required field" |
| **원인** | request body에 `status` 필드 누락 |
| **해결** | `status: 'standby'` 추가 — 코드에 이미 반영됨 |

### 5-9. 로젠 엑셀 파싱 0건

| 항목 | 내용 |
|---|---|
| **증상** | 로젠 결과 엑셀 업로드 시 "0건의 데이터를 읽었습니다" |
| **원인** | 로젠 WEB-EDI 엑셀의 특수 구조 (제목행 + 병합셀 + 서브헤더 + 합계) |
| **해결** | 헤더 자동감지 로직으로 '운송장번호' 컬럼 위치 탐색 — 코드에 반영됨 |

### 5-10. 헤더 행이 데이터로 표시됨

| 항목 | 내용 |
|---|---|
| **증상** | 테이블 첫 번째 행에 "주문번호 / 이름 / 물품명 / 운송장번호" 가 데이터로 나옴 |
| **원인** | 로젠 엑셀의 서브헤더(컬럼명) 행이 데이터로 처리됨 |
| **해결** | `!/^\d+$/.test(trackingNo)` — 숫자가 아닌 운송장번호 행은 필터링 |

### 5-11. 배송조회 "데모 수령인" 표시

| 항목 | 내용 |
|---|---|
| **증상** | 배송조회 탭에서 모든 항목이 "데모 수령인" + 랜덤 상태 |
| **원인** | 로젠 웹사이트 직접 호출 → CORS 차단 → 데모 데이터 fallback |
| **해결** | Vercel 프록시(`/api/logen`)를 통해 tracker.delivery API 사용 |

### 5-12. Refresh Token 만료

| 항목 | 내용 |
|---|---|
| **증상** | 모든 API 호출이 401 에러. 자동 갱신도 실패 |
| **원인** | Refresh Token 2주 유효기간 만료 |
| **해결** | OAuth 인증을 처음부터 다시 수행 (위 1-2 절차) |
| **재발방지** | 2주마다 최소 1회는 앱을 사용하여 토큰이 갱신되도록 함 |
