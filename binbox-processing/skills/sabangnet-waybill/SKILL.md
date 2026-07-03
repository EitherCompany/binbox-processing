---
name: sabangnet-waybill
description: 빈박스(체험단) + 실배송 풀필먼트 송장처리 통합 자동화 스킬. 사용자가 엑셀 파일(체험단 또는 발주조회)을 업로드하면, 양식을 자동 감지하여 사방넷(sbadmin03.sabangnet.co.kr)에서 적절한 파이프라인을 실행한다. 체험단 양식이면 빈박스 흐름(주문수집→확정→001→002→CJ송장입력→송신), 발주조회 양식이면 실배송 흐름(ordMapping→001→002→롯데송장입력 덮어쓰기→송신)을 진행하고 크로스체킹까지 완료한다. 반드시 이 스킬을 사용해야 하는 경우는 "빈박스", "체험단", "실배송 송장", "풀필먼트 송장", "송장처리", "운송장 처리", "발주조회 엑셀", "롯데택배 송장", "CJ송장", "송장 등록", "쇼핑몰 송신", "사방넷 송장", "송장 돌려줘" 등 사방넷에서 송장을 등록·송신하는 모든 요청. 사용자가 체험단 엑셀(파일명에 "3pl", "체험단" 포함) 또는 발주조회 엑셀(파일명에 "발주조회" 포함, 암호화)을 업로드하면 이 스킬을 사용할 것.
---

# 빈박스(체험단) + 실배송 풀필먼트 송장처리 통합

> **v1.7.0 (2026-07-03)**: 송신 대기 정책 명문화 — **제출은 단 1회, 클라이언트가 별도 창에서 진행하는 동안 절대 리로드/재투입 금지**. errMsg 빈 값 ≠ stall (완료 시점에만 채워짐). getWaybillTransmitInfo는 송신 전 정보 조회용이라 진행상태 반영 안 됨. 07-03 350건: 4분 무변화를 stall로 오판해 리로드+재투입 → 거의 끝난 송신이 처음부터 다시 돌아 시간 2배 소요 (사용자 강한 불만).
> **v1.6.0 (2026-06-29)**: realship 매칭 안정화 — searchOrders **직접 fetch 금지(401)**, 컴포넌트 `goSearch`+el-table 읽기로 고정. 6000행 cap 시 윈도우 축소/페이지네이션. reload 대비 **localStorage**에 ordNo·ours 저장. 송신은 **전량 한 번에 큐 투입**, stall 시 멈춘 클라이언트 닫고 잔여건만 재투입.
> **v1.5.0 (2026-05-04)**: realship 장바구니/멀티옵션 형제 ordNo 자동 발견 — 같은 phone+name 그룹의 다른 ordNo도 같은 송장 자동 적용 (1주문번호=N상품주문번호 또는 1상품=N옵션 케이스).
> **v1.4.0 (2026-05-04)**: realship 발주조회 16자리 ≠ 사방넷 shmaOrdNo 케이스 해결 — **전화번호+이름 cross-match** 자동 fallback 추가 (스마트스토어 풀필먼트 별도ID 패턴).
> **v1.3.0 (2026-05-04)**: Step 3·9 강화 — **주문수집 기간 자동 확장 (휴일·연휴 대응)** + **최종 누락건 자동 검출 리포트 + 재수집 안내**.
> **v1.1.0 (2026-04-29)**: 실배송 흐름 통합. 발주조회 양식(롯데택배) 자동 감지 + 처리.
> **v1.0.3 검증 누적**: 04-20~05-04, 빈박스 8,000건+ + 실배송 600건+ 처리 (재수집 패턴 검증)

## 개요

이 스킬은 두 가지 양식을 자동 분기하여 처리한다:

| 시나리오 | 입력 양식 | 택배사 | 사방넷 흐름 |
|---|---|---|---|
| **빈박스 (체험단)** | `3pl C/N 체험단_*.xlsx` | CJ택배 (`pcscpCd=003`) | 주문수집 → 확정 → 001→002 → 송장입력 → 송신 |
| **실배송 (풀필먼트)** | `발주조회_*.xlsx` (암호화) | 롯데(현대)택배 (`pcscpCd=002`) | (수집·확정 스킵) → ordMapping → 001→002 → 송장입력(덮어쓰기) → 송신 |

**자동 분기**: Step 1에서 파일명·헤더 검사로 양식을 결정하고 시나리오를 고정한다.

## 사용자 정보

- 사방넷 로그인: eithercompany / dlejzja7801!
- 서비스코드: 159514
- svcAcntId: mw159514
- 쇼핑몰: shop0075(쿠팡), shop0055(스마트스토어)
- **발주조회 엑셀 비밀번호**: `dlejrhddyd1!` (암호화된 .xlsx 복호화용)

## 택배사 코드 (사방넷 pcscpCd)

| 코드 | 택배사 |
|---|---|
| 001 | 대한통운 |
| **002** | **롯데(현대)택배** |
| **003** | **CJ택배** |
| 008 | (다른 택배사 - 풀필먼트 자동 등록 시 잘못 들어감) |

## 전체 처리 흐름 (자동 분기)

```
0. 양식 감지 → SCENARIO = "binbox" | "realship"
1. 엑셀 파싱 → shmaOrdNo + wyblNo 추출
   ├ binbox: 14개 체험단 엑셀 (3pl C/N)
   └ realship: 발주조회 엑셀 (암호 복호화 → 발주조회 시트 파싱)

2. 사방넷 로그인 확인

[binbox 시나리오만]
3. 주문서수집(자동) 실행 + 3분 대기
4. 주문서확정관리 → 일괄확정 (품번매핑 실패 무시)

[공통]
5. 주문서확인처리 → 001→002 (binbox: 신규 전체 / realship: 매칭 + 001 상태만)
6. ordMapping 구축 → shmaOrdNo ↔ 사방넷 내부 ordNo
7. 운송장 대량입력
   ├ binbox: pcscpCd=003 (CJ)
   └ realship: pcscpCd=002 (롯데, 기존 008 위에 덮어쓰기)
8. 쇼핑몰운송장송신 (4단계 패턴 + 폴링)
9. 크로스체킹 → 원본 vs 사방넷 처리결과 대조, 누락건 리포트
```

---

## 절대 금지사항 (실전 사고에서 도출)

1. **강제전환 절대 금지**: `updateMallWaybillTransmitForce`, `setForceChange` API 호출 금지.
   04-20에 이 API로 1,198건이 쇼핑몰에 미전송 사고.

2. **sendWybl() 사용 금지**: `comp.sendWybl()` 메서드는 네트워크 요청을 만들지 않는 no-op이다.
   반드시 Step 8의 mallWaybillTransmitPopup 패턴만 사용.

3. **setTimeout 금지**: 비동기 대기에 `setTimeout` 사용 금지.
   대신 window 변수에 결과 저장 후 즉시 다음 javascript_tool 호출에서 확인.

4. **searchData 사용 금지**: API body에 `searchData`가 아닌 `comp.sbForm`을 deep clone하여 사용.

5. **Content-Type 직접 설정 금지 (FormData 전송 시)**: 브라우저가 자동으로 boundary 설정.

6. **부분 처리 금지**: 전체 건수 수집 후 한 번에 파이프라인 진행. ordMapping 건수도 엑셀 건수와 일치 확인 필수.

7. **송신 제출 후 리로드/재투입 금지 (가장 흔한 사고)**: form.submit()으로 큐 투입이 되면
   로컬 클라이언트가 **별도 창에서** 전량을 알아서 끝까지 보낸다. 진행 중에는 wyblTrnmErrMsg가
   **빈 값으로 유지**되다가 완료 시점에만 '전송완료'로 채워지고, 사방넷 페이지의 LOADING 모달도 정상이다.
   **empty=전량이어도 stall이 아니다.** 350건 기준 10분 이상 걸릴 수 있다. 페이지 리로드나 재투입을 하면
   거의 끝난 송신이 처음부터 다시 시작된다 (07-03 사고). stall 판정은 오직 "클라이언트 창의 진행 번호가
   2분 이상 같은 번호에서 정지"일 때만, 가급적 사용자에게 확인 후 진행.

8. **realship에서 주문수집(자동)·일괄확정 실행 금지**: 실배송은 사방넷에 이미 주문 존재. 새로 수집하면 기존 데이터 깨짐.

---

## 핵심 기술 패턴

### Clean iframe XHR / fetch 패턴

Chrome 확장프로그램이 XMLHttpRequest를 monkey-patch하여 FormData 전송이 깨질 수 있다.
실전에서는 **fetch API**가 더 안정적임이 검증됨 (XHR보다 응답 누락 빈도 낮음).

```javascript
// 권장: fetch API (검증됨)
fetch(url, { method: 'POST', headers: { 'Authorization': token }, body: formData })
  .then(r => r.json()).then(j => { window.__result = j; });
// Content-Type 헤더 직접 설정 금지 (FormData일 때 boundary 자동)
```

XHR이 필요하면 clean iframe 패턴 사용:
```javascript
async function getCleanXHR() {
  if (window.__cleanIframe?.contentWindow?.XMLHttpRequest) return window.__cleanIframe.contentWindow.XMLHttpRequest;
  const iframe = document.createElement('iframe');
  iframe.style.display = 'none'; iframe.src = 'about:blank';
  document.body.appendChild(iframe);
  await new Promise(r => { let c=0; const poll = () => { c++; if ((iframe.contentWindow?.XMLHttpRequest)||c>50) r(); else requestAnimationFrame(poll); }; poll(); });
  window.__cleanIframe = iframe;
  return iframe.contentWindow.XMLHttpRequest;
}
```

페이지 이동 후엔 반드시 `window.__cleanIframe = null`.

### 인증 토큰

```javascript
const token = document.querySelector('#app').__vue__.$store.getters.token;
```

code 10000 발생 시: UI 검색 버튼 클릭 → 3초 대기 → 토큰 재취득.

### Vue 컴포넌트 탐색

```javascript
function findByFile(root, keyword) {
  if (!root) return null;
  const file = root.$options && root.$options.__file;
  if (file && file.includes(keyword)) return root;
  if (root.$children) for (const c of root.$children) { const f = findByFile(c, keyword); if (f) return f; }
  return null;
}
```

### 대용량 데이터 브라우저 주입 (~5KB 초과 시 분할)

bash에서 청크 파일 저장 → Read로 읽어 `window.__chunk1 = {...}` 식으로 별도 호출 → 브라우저에서 `Object.assign({}, ...)`로 병합.

---

## Step 0: 양식 자동 감지

업로드된 파일을 검사하여 시나리오를 결정한다:

```python
import os, glob
files = sorted(glob.glob('/sessions/.../uploads/*.xlsx'))
scenario = None
for f in files:
    name = os.path.basename(f)
    if name.startswith('발주조회'):
        scenario = 'realship'; break
    if '체험단' in name or name.startswith('3pl'):
        scenario = 'binbox'; break
# fallback: 헤더 검사
if not scenario:
    import openpyxl
    wb = openpyxl.load_workbook(files[0])
    headers = [wb.active.cell(1,i).value for i in range(1, 20)]
    if '오더코드' in headers and '판매상품명' in headers: scenario = 'realship'
    elif 'CJ대한통운 송장' in headers: scenario = 'binbox'
```

이후 모든 단계는 `scenario` 값에 따라 분기한다.

---

## Step 1A: 빈박스 엑셀 파싱

### 엑셀 구조

**3pl N (네이버 스마트스토어):** 파일명 `3pl N 체험단 {브랜드}_{날짜}-{hash}.xlsx`, 송장 컬럼 "CJ대한통운 송장".

**3pl C (쿠팡):** 파일명 `3pl C 체험단 {상품명} {날짜}_{ts}-{hash}.xlsx`, 송장 컬럼 "CJ대한통운 송장".

### 파싱 실행

```bash
python3 <skill-path>/scripts/parse_excel.py \
  --input-dir <업로드_디렉토리> \
  --output /tmp/binbox_orders.json \
  --scenario binbox
```

---

## Step 1B: 실배송 (발주조회) 엑셀 파싱

### 엑셀 구조

- 파일명 패턴: `발주조회_{YYYYMMDDHHMMSS}.xlsx` (CDFV2 암호화됨)
- 비밀번호: `dlejrhddyd1!`
- 시트명: "발주조회"
- 핵심 컬럼:
  - 컬럼 4: 송장번호 (롯데, 12자리 예: `410672383645`)
  - 컬럼 5: 회사명 (이더컴퍼니 / 뉴트리정(영양제))
  - 컬럼 7: 판매상품명
  - 컬럼 17: **주문번호** (shmaOrdNo, 16자리 스마트스토어 또는 14자리 쿠팡)

### 멀티 행 케이스

한 주문에 여러 옵션·상품이 들어가면 행이 여러 개로 나뉘되 송장은 동일하다.
unique 주문번호 → 송장번호 매핑이 핵심.

### 누락 발송 케이스 (사방넷에 주문 없음)

배송메시지가 "어제 누락 추가발송", "1세트 추가" 등이고 주소가 비정상(`(어제누락-송장 ...)`)이면
주문번호가 비어있을 수 있다. 별도 처리(MISS_ 키로 분리) 후 사용자에게 보고만 하고 사방넷 처리는 스킵.

### 파싱 실행

```bash
python3 <skill-path>/scripts/parse_excel.py \
  --input-dir <업로드_디렉토리> \
  --output /tmp/realship_orders.json \
  --scenario realship \
  --password 'dlejrhddyd1!'
```

스크립트가 내부적으로 `msoffcrypto-tool`로 복호화 후 파싱.

---

## Step 2: 사방넷 로그인 확인

반드시 `https://www.sabangnet.co.kr/`에서 로그인. `sbadmin03.sabangnet.co.kr` 직접 접속 금지(세션 문제).

```javascript
const loggedIn = !!document.querySelector('#app')?.__vue__?.$store?.getters?.token;
```

---

## Step 3: 주문서수집(자동) 실행 [binbox 전용]

> **realship 시나리오에서는 이 단계를 절대 실행하지 않는다.** 풀필먼트 주문은 이미 사방넷에 수집되어 있다.

### 수집 기간 자동 산정 (필수)

**기본 자동값(전전일~오늘 3일치)을 그대로 쓰지 말 것.** 사방넷의 자동 수집기간은 휴일·연휴를 고려하지 않아 누락이 발생한다.

올바른 방식:
1. **엑셀 파싱 결과의 가장 이른 "체험단 요청일시"** 추출 (`window.__earliestReqDt`)
2. 수집기간을 `(가장 이른 요청일시 - 1일) ~ 오늘`로 **수동 설정**
3. 사방넷 화면 좌측 "수집기간" 입력란을 직접 갱신 (`startDate`, `endDate` 캘린더)

```javascript
// 엑셀 파싱 결과에서 가장 이른 요청일시 도출
const minDt = orders.map(o => o.req_dt).filter(Boolean).sort()[0];
const startDate = new Date(minDt);
startDate.setDate(startDate.getDate() - 1);  // 1일 buffer
const startStr = startDate.toISOString().slice(0,10).replace(/-/g, '');
const endStr = new Date().toISOString().slice(0,10).replace(/-/g, '');
window.__collectStart = startStr;  // 예: '20260430'
window.__collectEnd = endStr;       // 예: '20260504'
```

**왜**: 05-04 사고 사례 — 사방넷 자동값이 5-2~5-4(3일)였는데 휴일(5-1금/5-2토/5-3일) + 4-30 14시 이후 주문이 8건 추가 누락 → 처리 후 재수집 1회 더 필요. 수집기간을 4-30 포함으로 잡으면 첫 회 처리에서 다 잡힘.

**평일/연휴 패턴**:
- 화~금: 전날~당일 (1일치)
- 월요일: 금요일~월요일 (4일치, 주말+근로자의날 등 포함)
- 연휴 직후: 연휴 직전 영업일~당일 (전체 커버)

### 실행

1. 주문서수집(자동) 페이지 → 쇼핑몰 전체선택 → 수집기간 위 산정값으로 입력 → "주문수집(신규+주문확인)" 클릭
2. **3분 이상 대기** (04-28 사고 사례: 미실행으로 16건 누락)
3. 수집 완료 시점이 당일인지 확인

---

## Step 4: 주문서확정관리 (일괄확정) [binbox 전용]

> **realship 시나리오에서는 이 단계를 스킵한다.**

빈박스는 송장이 이미 있으므로 품번매핑 실패와 무관하게 확정만 되면 된다.

```javascript
window.location.hash = '#/order/order-decide';
window.__cleanIframe = null;
```

1. `findByFile(app, 'order-decide.vue')` → 검색
2. `comp.popOpenOrderDecideBundlePrdCodeMapping()` → 일괄품번매핑 모달 → "일괄품번매핑실행"
3. **품번매핑 실패가 다수 있어도 멈추지 말 것** (모달 닫고 바로 다음 단계)
4. `comp.popOpenOrderDecideOrderConfirm()` → 일괄주문확정 모달 → "일괄주문확정" 클릭

---

## Step 5: 주문서확인처리 (001→002) [공통, 분기 있음]

> ⚠️ **검색은 반드시 컴포넌트의 `goSearch`로 — `searchOrders` API를 직접 fetch하지 말 것.**
> 06-29 검증: searchOrders를 직접 fetch하면 Authorization 헤더가 axios와 다르게 처리되어 **401/99999**로 계속 실패한다(반면 상태변경·송장입력·송신 fetch는 같은 토큰으로 정상). 그러니 **매칭만 goSearch로 화면 검색 후 el-table을 읽고**, 나머지(001→002·송장입력·송신)는 fetch로 처리한다.
>
> ⚠️ **sbForm은 날짜·pageSize·currentPage만 최소로 세팅.** `searchKeywordList` 등 다른 필드를 건드리면 **400**이 난다. 안전 세팅: `dateDiv='ORD_DT'; startDate/endDate; pageSize=2000; currentPage=1; searchCondition='cust_nm'; searchKeyword=''`.
>
> ⚠️ **el-table은 ~2000행(서버 cap ~6000)에서 잘린다.** 매칭 대상이 안 잡히면 윈도우(날짜)를 좁히거나 `currentPage`를 올려 goSearch를 반복하며 el-table.data를 누적한다. 06-29 실배송 149건은 6/24~6/29 ORD_DT 페이지1(2002행)에서 전건 직접 매칭됨.
>
> ⚠️ **페이지 reload/navigate 시 window 변수(`__wmap`,`__ourWybls`,`__matched`) 전부 소실.** 같은 도메인 내 네비게이션은 **localStorage**에 ordNo리스트·ours를 저장하면 살아남는다. navigate 전 `localStorage.setItem(...)`, 후 `JSON.parse(localStorage.getItem(...))`.

```javascript
window.location.hash = '#/order/order-confirm';
window.__cleanIframe = null;
```

페이지 이동 후 검색:
```javascript
const middle = findByFile(app, 'order-confirm-vue-middle');
middle.sbForm.ordStsCd = '';        // 001/003 모두 보고 클라이언트에서 필터
middle.sbForm.startDate = '20260427';
middle.sbForm.endDate = '20260429';
middle.sbForm.pageSize = 2000;
middle.sbForm.dateDiv = 'ORD_DT';
middle.goSearch();
```

**시나리오별 필터 (클라이언트에서):**

```javascript
const m2 = findByFile(app, 'order-confirm');
const data = findEl(m2, 'el-table')[0].data;
const wmapKeys = new Set(Object.keys(window.__wmap));
const matched = data.filter(r => wmapKeys.has(r.shmaOrdNo));

// binbox: 모두 001 (신규주문) - 직접 매칭 충분
// realship: 직접 매칭 + cross-match (아래 참조) 둘 다 사용
const found001 = matched.filter(r => r.ordStsCd === '001');
window.__matched = matched;
window.__found001 = found001;
```

### realship 전용: 전화번호+이름 cross-match (필수)

**05-04 사고 검증**: 스마트스토어 풀필먼트 분 355건은 발주조회 16자리(예: `2026043064194041`)와 사방넷 shmaOrdNo(예: `2026043051211581`)가 **서로 다른 ID**다. 풀필먼트가 자체 16자리를 발급하기 때문. 직접 매칭만 쓰면 100% 누락된다.

해결: parser가 출력한 `name` + `phone` 필드를 키로 사방넷 주문에 cross-match.

```javascript
// realship 시나리오 한정
if (window.__scenario === 'realship') {
  // parser가 만든 records: [{shmaOrdNo, wyblNo, name, phone, ...}, ...]
  const records = window.__realshipRecords;
  
  // 사방넷 모든 주문에서 phone(끝 8자리) → row 매핑
  const phoneMap = {};
  data.forEach(r => {
    const ph1 = String(r.ecptRmteHndpnNo || '').replace(/\D/g, '').slice(-8);
    const ph2 = String(r.ecptRmteTelNo || '').replace(/\D/g, '').slice(-8);
    if (ph1) (phoneMap[ph1] = phoneMap[ph1] || []).push(r);
    if (ph2 && ph2 !== ph1) (phoneMap[ph2] = phoneMap[ph2] || []).push(r);
  });
  
  const directSet = new Set(matched.map(r => r.shmaOrdNo));
  const crossMatched = [];
  const unmatched = [];
  for (const rec of records) {
    if (directSet.has(rec.shmaOrdNo)) continue;  // 이미 직접 매칭
    const phoneLast8 = String(rec.phone || '').replace(/\D/g, '').slice(-8);
    const candidates = phoneMap[phoneLast8] || [];
    let found = candidates.find(r => 
      String(r.ecptRmteNm || '').includes(rec.name) || rec.name.includes(String(r.ecptRmteNm || ''))
    );
    if (!found && candidates.length === 1) found = candidates[0];  // 후보 1명이면 phone-only
    if (found) {
      crossMatched.push({...found, _wyblFromExcel: rec.wyblNo});
    } else {
      unmatched.push(rec);
    }
  }
  
  // matched와 합치기 (중복 ordNo 제거)
  const seenOrdNo = new Set(matched.map(r => r.ordNo));
  for (const r of crossMatched) {
    if (!seenOrdNo.has(r.ordNo)) { seenOrdNo.add(r.ordNo); matched.push(r); }
  }
  window.__matched = matched;
  window.__found001 = matched.filter(r => r.ordStsCd === '001');
  window.__realshipUnmatched = unmatched;
  
  console.log(`realship: 직접매칭 ${directSet.size} + cross-match ${crossMatched.length} = 총 ${matched.length}, 미매칭 ${unmatched.length}`);
}
```

**주의**: cross-match된 주문에 대해서는 `_wyblFromExcel` 필드를 따로 저장. Step 6 ordMapping에서 wybl 결정 시 이걸 우선 사용. (직접 매칭은 wmap[shmaOrdNo]가 정답.)

### realship 전용: 형제 ordNo 자동 발견 (장바구니/멀티옵션)

**05-04 추가 검증**: 한 부모 주문번호에 여러 상품주문번호(장바구니) 또는 한 상품에 여러 옵션이 있으면, 사방넷은 **동일 phone+name으로 여러 ordNo로 row를 분리**한다. 발주조회는 송장 1개만 발급하므로 같은 부모의 형제 ordNo들은 송장 미입력 상태로 남는다 (27건 검증 — 100% 누락).

처리(cross-match 직후 추가):

```javascript
if (window.__scenario === 'realship') {
  // 사방넷 모든 스마트스토어/쿠팡 주문에서 phone+name 그룹화
  const groupKey = (r) => {
    const ph1 = String(r.ecptRmteHndpnNo || '').replace(/\D/g, '').slice(-8);
    const ph2 = String(r.ecptRmteTelNo || '').replace(/\D/g, '').slice(-8);
    return (ph1 || ph2) + '|' + String(r.ecptRmteNm || '').trim();
  };
  
  const groups = {};
  data.forEach(r => {
    const k = groupKey(r);
    if (!k.startsWith('|')) (groups[k] = groups[k] || []).push(r);
  });
  
  // 우리가 처리한 ordNo set
  const processedOrdNos = new Set(matched.map(r => r.ordNo));
  // 처리한 ordNo의 group 추적
  const matchedGroupKeys = new Set();
  matched.forEach(r => matchedGroupKeys.add(groupKey(r)));
  
  // 같은 그룹의 미처리 형제 발견
  const siblings = [];
  for (const k of matchedGroupKeys) {
    const group = groups[k] || [];
    const processedInGroup = group.filter(r => processedOrdNos.has(r.ordNo));
    if (processedInGroup.length === 0) continue;
    // 처리된 형제의 wybl을 가져옴
    const procRow = matched.find(m => groupKey(m) === k);
    const wybl = procRow._wyblFromExcel || window.__wmap[procRow.shmaOrdNo];
    if (!wybl) continue;
    
    for (const sib of group) {
      if (processedOrdNos.has(sib.ordNo)) continue;
      if (sib.wyblNo) continue;  // 이미 송장 있는 건 스킵
      siblings.push({...sib, _wyblFromExcel: wybl, _isSibling: true});
    }
  }
  
  // matched에 합치기
  for (const s of siblings) {
    matched.push(s);
    if (s.ordStsCd === '001') window.__found001.push(s);
  }
  window.__matched = matched;
  window.__siblingDiscovered = siblings.length;
  console.log(`형제 ordNo 자동 발견: ${siblings.length}건 추가`);
}
```

**검증된 패턴 (05-04)**:
- 28개 부모 주문 그룹에서 30개 형제 발견
- 그 중 27건이 송장 미입력 → 동일 송장 자동 적용 → 100% 송신 성공
- 같은 shmaOrdNo가 여러 ordNo로 분리된 경우(멀티옵션) 모두 catch

### API 직접 호출 (검증된 방법 A)

```javascript
const found = window.__found001;  // 001 상태인 건만
const body = {
  orderStatus: "002",
  selectData: "1",
  songClear: "", orderCancelReason: "", claimContent: "",
  list: found.map(o => ({
    ordNo: o.ordNo, ordStsCd: "001", ordStsCdList: ["001", "007"],
    shmaId: o.shmaId, shmaOrdNo: o.shmaOrdNo,
    ordInputDivCd: o.ordInputDivCd || "01", svcAcntId: "mw159514",
    ordStsTpDivCd: o.ordStsTpDivCd || "N",
    songClear: null, claimClear: null, changeClaimContent: null, prdNo: null, skuNo: null
  })),
  selectListSize: found.length, searchListSize: found.length,
  allPartnerId: "mw159514", svcAcntId: "mw159514",
  fnlChgUserId: "eithercompany", fnlChgIp4a: "59.7.45.135",
  fnlChgPrgmNm: "order-confirm-order-status-change-popup",
  fstRegsUserId: "eithercompany", fstRegsIp4a: "59.7.45.135",
  fstRegsPrgmNm: "order-confirm-order-status-change-popup"
};
fetch('https://sbadmin03.sabangnet.co.kr/prod-api/customer/order/OrderConfirm/exeOrderConfirmOrderStatusChange', {
  method: 'POST',
  headers: { 'Authorization': token, 'Content-Type': 'application/json;charset=UTF-8' },
  body: JSON.stringify(body)
}).then(r => r.json()).then(j => { window.__statusChangeResult = j; });
```

핵심: `allPartnerId` 필수, `selectListSize === list.length`, `ordStsCdList: ["001", "007"]` 배열, null 필드 보존.

---

## Step 6: ordMapping 구축 [공통]

`window.__matched` 가 이미 ordMapping(shmaOrdNo ↔ ordNo)이다. uploadData 생성:

```javascript
const uploadData = window.__matched.map(o => ({
  ordNo: String(o.ordNo),
  shmaOrdNo: o.shmaOrdNo,
  // realship cross-match 결과면 _wyblFromExcel을 우선 사용
  wyblNo: o._wyblFromExcel || window.__wmap[o.shmaOrdNo]
}));
window.__uploadData = uploadData;
// 검증
console.log(uploadData.every(d => d.wyblNo));  // 반드시 true
```

**realship 주의**: 한 shmaOrdNo가 여러 ordNo로 매칭될 수 있다 (멀티 옵션). 모든 ordNo에 동일 송장 매겨야 함.

---

## Step 7: 운송장 대량입력 [pcscpCd 분기]

```javascript
window.location.hash = '#/order/waybill-input-large';
window.__cleanIframe = null;
```

SheetJS 로딩:
```javascript
if (!window.XLSX || !window.XLSX.utils) {
  delete window.XLSX;
  const s = document.createElement('script');
  s.src = 'https://cdn.sheetjs.com/xlsx-0.20.1/package/dist/xlsx.full.min.js';
  s.onload = () => { window.__xlsxLoaded = true; };
  document.head.appendChild(s);
}
```

업로드 (시나리오별 pcscpCd 다름):
```javascript
const PCSCP = window.__scenario === 'realship' ? '002' : '003';  // 롯데 vs CJ
const rows = window.__uploadData.map(d => [String(d.ordNo), String(d.wyblNo), '', '', PCSCP]);
const ws = XLSX.utils.aoa_to_sheet(rows);
Object.keys(ws).forEach(k => { if (k[0] !== '!') ws[k].t = 's'; });
const wb = XLSX.utils.book_new();
XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');
const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
const blob = new Blob([wbout], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
const file = new File([blob], 'waybill.xlsx', { type: blob.type });

const fd = new FormData();
fd.append('file', file, 'waybill.xlsx');
fd.append('pcscpCd', PCSCP);
fd.append('exclFormSrno', '-99');
fd.append('exclFormDivCd', '08');
fd.append('fnlChgUserId', 'eithercompany');
fd.append('fnlChgIp4a', '59.7.45.135');
fd.append('fnlChgPrgmNm', 'waybill-input-large');

fetch('https://sbadmin03.sabangnet.co.kr/prod-api/customer/order/waybill/updateLargeWaybillInput', {
  method: 'POST', headers: { 'Authorization': token }, body: fd
}).then(r => r.text()).then(t => { window.__waybillResult = JSON.parse(t); });
```

**realship 주의**: 003 상태 + pcscpCd=008(잘못 등록)인 건들은 새 송장으로 **덮어쓰기**된다.
04-29 검증: 132건 중 91건이 합포장번호로 잘못 등록되어 있었지만 롯데 송장으로 정상 덮어쓰기됨 (failCount=0).

---

## Step 8: 쇼핑몰운송장송신 (4단계 패턴) [공통]

```javascript
window.location.hash = '#/mall/mall-waybill-transmit';
window.__cleanIframe = null;
```

### 모달 hide 차단 (필수!)

```javascript
const comp = findByFile(app, 'mall-waybill-transmit');
if (!comp.__origHide) comp.__origHide = comp.$modal.hide;
comp.$modal.hide = function() {};  // 빈 함수
```

### 8-1: getWaybillTransmitInfo

```javascript
fetch('https://sbadmin03.sabangnet.co.kr/prod-api/customer/mall/MallWaybillTransmit/getWaybillTransmitInfo', {
  method: 'POST', headers: { 'Authorization': token, 'Content-Type': 'application/json;charset=UTF-8' },
  body: JSON.stringify({ svcAcntId: 'mw159514', ordNoList: batch.map(Number) })
}).then(r => r.json()).then(j => { window.__sendDatas = j.data?.list || []; });
```

### 8-2: mallWaybillTransmitPopup

```javascript
comp.mallWaybillTransmitPopup(window.__sendDatas, 'N');
```

### 8-3: iframe name + 8-4: form.submit

```javascript
for (const f of document.querySelectorAll('iframe')) {
  if (f.src?.includes('127.0.0.1:8181')) { f.name = 'mallWayBillSong'; break; }
}
for (const f of document.querySelectorAll('form')) {
  if (f.target === 'mallWayBillSong' && f.action.includes('127.0.0.1')) { f.submit(); break; }
}
```

### 폴링 확인 (1~2분 간격, 인내심 있게 — 350건 기준 10분+)

`getMallWaybillTransmitLists` (sbForm deep clone) 조회 → `wyblTrnmErrMsg === '전송완료'` 카운트.
전량 전송완료될 때까지 대기.

**⚠️ getWaybillTransmitInfo로 상태 폴링 금지** — 이 API는 송신 **전** 정보 조회용이라 errMsg에
진행상태가 반영되지 않는다 (송신이 다 끝나도 빈 값으로 보일 수 있음). 상태 확인은
`getMallWaybillTransmitLists` 또는 주문서확인처리 페이지의 wyblTrnmErrMsg로만.

**⚠️ 폴링 결과가 계속 빈 값이어도 리로드/재투입 금지.** 송신은 별도 클라이언트 창에서 진행되고
errMsg는 완료 시점에만 채워진다. 60초 안에 안 끝나는 게 정상이다. 절대 금지사항 7번 참조.

**검색이 좁게 잡히면**: 주문서확인처리 페이지로 이동해서 거기서 wyblTrnmErrMsg를 직접 확인하는 게 더 정확. (mall-waybill-transmit 페이지의 기본 필터가 송신완료된 건을 감춤)

### 송신은 전량 한 번에 큐 투입 (쪼개지 말 것)

**미송신 ordNo 전체를 한 번의 `getWaybillTransmitInfo`(ordNoList=전체) → `mallWaybillTransmitPopup(sd,'N')` 한 번 → iframe name 지정 → form.submit 한 번**으로 전량을 클라이언트 큐에 통째로 넣고 그대로 둔다. 쪼개서 여러 번 투입하면 매 묶음마다 송신 팝업이 떠 화면이 "새로고침처럼" 깜빡이고(사용자 매우 싫어함), 통과 속도는 쿠팡 throttle이 정하므로 어차피 동일하다. 끝날 때 한 번만 크로스체킹.

송신 직전 DOM 정리:
```javascript
document.querySelectorAll('.vm--overlay, .vm--modal, .vm--container').forEach(el => el.remove());
document.querySelectorAll('iframe[src*="127.0.0.1"], iframe[name="mallWayBillSong"]').forEach(el => el.remove());
document.querySelectorAll('form[target="mallWayBillSong"]').forEach(el => el.remove());
```

### 송신 클라이언트 stall 복구 (06-29 검증)

전량 송신 중 클라이언트(127.0.0.1:8181 탭)가 특정 건(예: "N건중 K번째 송신중")에서 쿠팡 throttle로 **멈추는** 경우가 있다(같은 번호가 1~2분 이상 정지). 이때:
1. 멈춘 송신 클라이언트 탭(127.0.0.1:8181)을 **닫는다**.
2. `getMallWaybillTransmitLists`로 우리 송장 중 **`wyblTrnmStsNm`이 성공/완료가 아닌(=송신대기) 잔여 ordNo만** 수집한다.
3. 그 잔여 ordNo만 다시 `getWaybillTransmitInfo`+`mallWaybillTransmitPopup`으로 **재투입** → 새 클라이언트가 깔끔히 끝낸다.

06-29 실배송 157건: #150에서 stall → 멈춘 탭 닫고 잔여 8건만 재투입 → 8건 전부 성공, 최종 157/157 통신성공 0실패.

---

## Step 9: 크로스체킹 + 최종 누락건 리포트 (필수)

**처리 종료 직전에 반드시 실행**. 사용자 요청: "마지막에 누락건만 알려주면 된다." 누락 카테고리를 명확히 분리해서 보고할 것.

### 누락 카테고리 4종

| 카테고리 | 정의 | 사용자 액션 |
|---|---|---|
| **A. 사방넷 미수집** | 엑셀에 있고 wyblNo도 있는데 사방넷에 ordNo로 등록 자체가 안 됨 | **15분~2시간 후 재수집** 또는 mall 측 push 대기 |
| **B. 송신 실패** | 사방넷에 매칭되고 송장 입력했지만 wyblTrnmErrMsg에 에러 | wyblTrnmErrMsg 별도 분류 (취소건/합포장번호 등) |
| **C. MISS_ 누락발송** | 발주조회 엑셀의 "어제 누락 추가발송" 케이스 (사방넷 신규 주문 없음) | 사용자 직접 확인 (주소, 메시지) |
| **D. 송장번호 누락** | 엑셀 행에 송장번호가 없거나 잘못된 형식 | 엑셀 발급처(풀필먼트) 확인 |

### 카테고리 A 자동 검출 (핵심)

```javascript
// 사방넷에서 fst_regs_dt 폭넓게 재검색 (최소 7일치)
const allList = window.__listAll;  // 페이지네이션 누적
const sabangShmaOrdSet = new Set(allList.map(r => String(r.shmaOrdNo)));

const excelKeys = Object.keys(window.__wmap);
const notInSabang = excelKeys.filter(k => !sabangShmaOrdSet.has(k));

// shmaOrdNo 형식별 분류 (16자리=스마트스토어, 13/14자리=쿠팡)
const byLen = {};
notInSabang.forEach(k => { const l = k.length; byLen[l] = (byLen[l]||0)+1; });

window.__missingA = notInSabang;
```

**자릿수별 분포가 중요한 시그널** — 모두 한 자릿수에 몰려있으면 mall 별 sync 지연(예: 스마트스토어만 풀필먼트 자동등록 늦음).

### 카테고리 B 분류

```javascript
const matched = window.__matched;  // 사방넷 매칭된 주문
const failures = matched.filter(r => r.wyblTrnmErrMsg && !r.wyblTrnmErrMsg.includes('전송완료'));

// 에러 메시지별 그룹
const byErr = {};
failures.forEach(r => {
  const key = r.wyblTrnmErrMsg.slice(0, 40);
  byErr[key] = (byErr[key]||0)+1;
});
```

### 최종 리포트 포맷 (사용자 출력)

```
# 📦 [시나리오] [날짜] 처리 결과

| 항목 | 건수 |
|---|---|
| 엑셀 원본 unique | XXXX |
| 사방넷 매칭 | XXXX |
| 송장 입력 성공 | XXXX |
| **송신 완료** | **XXXX** ✅ |

## 누락건 (사용자 확인 필요)

### A. 사방넷 미수집 (재수집 대기): N건
- shmaOrdNo 길이 분포: { 13자리: A, 14자리: B, 16자리: C }
- 사유 추정: {스마트스토어 풀필먼트 sync 지연 / 쿠팡 14시 cutoff 후 휴일 buffer 등}
- 권장 조치: **15분~2시간 후 동일 스킬 재실행** (수집기간을 가장 이른 요청일시-1일로 설정)

### B. 송신 실패: N건
- wyblTrnmErrMsg별 분류
- 주문번호 리스트 (10건만 미리보기)

### C. MISS_ 누락발송: N건
- 별도 처리 불가, 사용자 직접 확인

### D. 송장번호 누락: N건
- 엑셀 발급처 확인 필요
```

### 재처리 안내 (Step 9 종료 시)

A 카테고리가 0이 아니면 사용자에게 명시:
> "사방넷 미수집 N건 — 풀필먼트/mall에서 사방넷으로 push 지연된 건. 15분~2시간 후 같은 스킬을 한 번 더 실행하면 추가 잡힘. 잊지 말 것."

---

## 알려진 함정 (실전 사고에서 도출)

### 휴일 직전 영업일 14시+ 주문 누락 (binbox)

**05-04 사고 검증**: 5-4(월) 처리 시 4-30(목) 14시 이후 주문 89건이 사방넷 1차 cron(11:43)에서 누락됨. 5-1~5-3 휴일이라 사방넷 자동 cron이 주말에 안 도는데, 쿠팡의 14시 daily cutoff 후 주문은 다음 영업일 발송 batch로 분류되어 mall→사방넷 sync가 5-4 15:06 cron까지 지연됨.

- **시그널**: `fstRegsDt` 분포에서 처리 시점(예 11시) 직전까지 잡힌 건 vs 처리 직후(15시) 잡힌 건이 분리됨. 누락된 89건은 모두 4-30 14시 이후 customer 요청.
- **재발 방지**: Step 9에서 사방넷 미수집(카테고리 A) 자동 검출 → 사용자에게 "1~2시간 후 재실행" 안내. Step 3에서 수집기간 폭 확보로도 일부 완화.

### 장바구니/멀티옵션 형제 ordNo 송장 누락 (realship)

**05-04 검증**: 한 주문번호에 여러 상품주문번호(장바구니) 또는 한 상품주문번호에 여러 옵션이 있으면 사방넷은 동일 phone+name으로 여러 ordNo row 생성. 발주조회 풀필먼트는 송장 1개만 발급하므로 형제 ordNo는 송장 미입력으로 남음.

- **신호**: 사방넷에서 같은 phone+name 그룹에 여러 row, 그 중 일부만 송신완료 + 나머지 신규주문/송장 null.
- **조치**: Step 5 cross-match 직후 자동으로 형제 발견 → 동일 송장 적용 → 같은 부모면 송장 1번 = 형제 모두 송신 OK.

### 발주조회 16자리 ID ≠ 사방넷 shmaOrdNo (realship)

**05-04 검증**: 발주조회 16자리 (예: `2026043064194041`)는 풀필먼트가 발급한 자체 ID로, 사방넷이 mall에서 받는 shmaOrdNo (예: `2026043051211581`)와 **다른 형식**이다. 같은 주문이지만 두 시스템이 별도 ID 부여.

- **신호**: 직접 매칭 시 16자리(스마트스토어)는 0건 매칭, 13/14자리(쿠팡)는 정상 매칭.
- **조치**: Step 5에서 **전화번호 끝 8자리 + 받는분 이름**으로 cross-match (위 Step 5 코드 참조). 검증된 패턴 — 355건 중 100% 매칭 성공.
- **fallback**: phone 후보가 1명뿐이면 이름 일치 안 해도 채택 (이름 표기 차이 흡수).

### 풀필먼트 자동 등록의 합포장번호 문제 (realship)

풀필먼트가 자동으로 사방넷에 송장을 등록하는데, 이때 `pcscpCd=008` (다른 택배사 코드)로 합포장번호(예: 681598395383819)를 입력해버리는 경우가 있다. 이 상태로 송신하면 "등록실패송장번호가 유효하지 않습니다" 에러.

**해결**: 발주조회 엑셀의 새 롯데 송장으로 `pcscpCd=002`로 덮어쓰기. updateLargeWaybillInput API가 덮어쓰기를 지원함 (검증됨).

### realship의 누락 발송 케이스

배송메시지 "어제 누락 추가발송", 주소 `(어제누락-송장 ...)`인 행은 사방넷에 신규 주문이 없다. 주문번호도 보통 비어있다. 파싱 시 `MISS_<원송장>` 키로 분리 → 사용자에게 알림만 하고 처리는 스킵.

### 스토어팜 취소건

송신 결과 `wyblTrnmErrMsg`에 "스토어팜 판매관리 - 취소관리 메뉴에서 취소 주문 건인지 확인" 메시지가 뜨는 경우 → 쇼핑몰 측에서 취소된 주문. 사용자가 직접 확인.

### 모달 즉시 닫힘

`mallWaybillTransmitPopup()` 호출 시 모달이 자동으로 hide되는 현상. 반드시 호출 전에 `comp.$modal.hide = function(){}`로 차단.

### setTimeout 콜백 누락

응답을 setTimeout 안에 저장하면 Claude가 읽으러 오지 않아 멈춘다. 직접 window 변수에 쓰고 다음 javascript_tool 호출에서 즉시 확인.

### XHR vs fetch

XHR이 응답을 누락하는 경우가 있음 (특히 운송장 업로드처럼 무거운 요청). fetch로 전환하면 안정적.

---

## 에러 처리

| 증상 | 원인 | 해결 |
|------|------|------|
| code 10000 | 토큰 만료 또는 body 형식 | UI 검색 클릭 → 토큰 재취득 / sbForm deep clone |
| API 500 | 서버 불안정 | UI 우회 또는 사용자 수동 |
| 운송장 fail > 0 | ordNo 불일치 | ordMapping 검증 |
| 모달 즉시 닫힘 | $modal.hide 자동 호출 | hide를 빈 함수로 대체 |
| 페이지 검색 결과 좁음 (132건 중 12건만) | 페이지 기본 필터 | 주문서확인처리에서 직접 확인 |
| 등록실패-합포장번호 | pcscpCd=008 잘못 등록 | 새 송장으로 덮어쓰기 (Step 7) |

---

## 빈박스 vs 실배송 식별 규칙 (참고)

체험단 엑셀 내부 데이터 기준 (이미 양식이 다르므로 보통은 양식만 봐도 충분):

- **쿠팡 빈박스**: 배송지 주소에 `%` 문자 포함
- **네이버 빈박스**: 배송메시지에 "문 앞에 놓아주세요!" 포함
- **실배송**: 위 어느 패턴에도 해당 안 됨 (정상 배송지·메시지)
