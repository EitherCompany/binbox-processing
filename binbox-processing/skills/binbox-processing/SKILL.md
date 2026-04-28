# 빈박스(체험단) 주문 자동 처리

> **최종 실전 검증**: 2026-04-28 (375건 전체 성공, 누락 0건)
> **누적 처리**: 04-20~04-28, 8일간 3,000건+ 처리

## 개요

체험단 주문(빈박스)은 CJ택배 운송장이 이미 배정된 상태로 들어온다.
사용자가 체험단 엑셀 파일(개수 가변)을 업로드하면, 사방넷 관리자 사이트에서
전체 파이프라인을 자동으로 실행하고, 원본 엑셀 대비 크로스체킹 결과를 리포트한다.

## 사용자 정보

- 사방넷 로그인: eithercompany / dlejzja7801!
- 서비스코드: 159514
- svcAcntId: mw159514
- 쇼핑몰: shop0075(쿠팡), shop0055(스마트스토어)

## 전체 처리 흐름

```
1. 엑셀 파싱 → shmaOrdNo(쇼핑몰주문번호) + wyblNo(CJ송장번호) 추출
2. 사방넷 로그인 확인
3. 주문서수집(자동) 실행 + 3분 대기 (필수!)
4. 주문서확정관리 → 일괄확정 (품번매핑 포함)
5. 주문서확인처리 → 상태변경(001→002)
6. ordMapping 구축 → shmaOrdNo ↔ 사방넷 내부 ordNo 매핑
7. CJ운송장 대량입력 (updateLargeWaybillInput API)
8. 쇼핑몰운송장송신 (검증된 4단계 패턴)
9. 크로스체킹 → 원본 vs 사방넷 처리결과 대조, 누락건 리포트
```

---

## 절대 금지사항 (실전 사고에서 도출)

이 금지사항은 04-20~04-28 실전에서 실제 사고나 반복 실패를 겪고 도출된 것이다.
위반 시 수백~수천 건의 주문이 쇼핑몰에 미전송되는 등 심각한 문제가 발생한다.

1. **강제전환 절대 금지**: `updateMallWaybillTransmitForce`, `setForceChange` API 호출 금지.
   실제 쇼핑몰(쿠팡/네이버)에 전송하지 않고 사방넷 내부 상태만 변경한다.
   04-20에 이 API를 사용하여 1,198건이 쇼핑몰에 미전송되는 사고가 발생했다.

2. **sendWybl() 사용 금지**: `comp.sendWybl()` 메서드는 네트워크 요청을 만들지 않는 no-op이다.
   04-21에 검증됨. 반드시 아래 Step 8의 mallWaybillTransmitPopup 패턴만 사용한다.

3. **setTimeout 금지**: 비동기 대기에 `setTimeout` 사용 금지.
   setTimeout 콜백 결과를 Claude가 읽으러 가지 않아 멈춤이 발생한다.
   대신 window 변수에 결과 저장 후 즉시 다음 javascript_tool 호출에서 확인.

4. **searchData 사용 금지**: API body에 `searchData`가 아닌 `comp.sbForm`을 deep clone하여 사용.
   searchData로 API 호출 시 code 10000 에러 발생.

5. **Content-Type 직접 설정 금지 (FormData 전송 시)**: FormData를 보낼 때 Content-Type 헤더를
   직접 설정하면 boundary가 누락된다. 브라우저가 자동 설정하도록 해야 한다.

6. **부분 처리 금지**: 빈박스를 140건씩 끊어서 처리하지 않는다. 전체 건수가 수집될 때까지
   기다린 후 한 번에 파이프라인을 돌린다. 부분 처리 시 2번째 바퀴에서 컨텍스트 소진,
   API 재디버깅으로 매번 3시간+ 소요 패턴 반복. ordMapping 건수도 엑셀 건수와 반드시 일치시킨 후 다음 단계 진행.

---

## 핵심 기술 패턴

### Clean iframe XHR 패턴 (모든 API 호출에 필수)

Chrome 확장프로그램(Claude in Chrome 등)이 XMLHttpRequest를 monkey-patch하여
FormData 전송이 깨지거나 API 응답이 손상된다.
**모든** 사방넷 API 호출은 반드시 이 패턴을 사용한다:

```javascript
async function getCleanXHR() {
  if (window.__cleanIframe && window.__cleanIframe.contentWindow) {
    try {
      const test = window.__cleanIframe.contentWindow.XMLHttpRequest;
      if (test) return test;
    } catch(e) { /* iframe 파괴됨 */ }
  }
  const iframe = document.createElement('iframe');
  iframe.style.display = 'none';
  iframe.src = 'about:blank';
  document.body.appendChild(iframe);
  await new Promise(r => {
    let c = 0;
    const poll = () => {
      c++;
      if ((iframe.contentWindow && iframe.contentWindow.XMLHttpRequest) || c > 50) r();
      else requestAnimationFrame(poll);
    };
    poll();
  });
  window.__cleanIframe = iframe;
  return iframe.contentWindow.XMLHttpRequest;
}
```

**페이지 이동 시 iframe 초기화 필수**: `window.location.hash`를 변경하면 기존 iframe이
파괴될 수 있다. 이동 후 반드시 `window.__cleanIframe = null`로 초기화한다.

### 인증 토큰

```javascript
const token = document.querySelector('#app').__vue__.$store.getters.token;
window.__token = token;
```

**토큰 갱신 패턴 (code 10000 발생 시)**:
페이지 새로고침 후에도 code 10000이 반복되면, UI의 "검색" 버튼을 클릭한다.
Vue 프레임워크가 내부적으로 토큰을 갱신하고, 이후 store에서 가져온 토큰이 정상 작동한다.
1. 해당 페이지의 검색 버튼 find → click
2. 3초 대기
3. `app.$store.getters.token` 재취득

### Vue 컴포넌트 탐색

```javascript
function findByFile(root, keyword) {
  if (!root) return null;
  const file = root.$options && root.$options.__file;
  if (file && file === keyword) return root;
  if (root.$children) {
    for (const c of root.$children) {
      const f = findByFile(c, keyword);
      if (f) return f;
    }
  }
  return null;
}
const app = document.querySelector('#app').__vue__;
```

### 대용량 데이터 브라우저 주입

javascript_tool로 주입할 수 있는 데이터 크기에는 한계가 있다 (약 5,000자에서 truncation).
35KB 이상 데이터는 반드시 청크로 분할하여 주입한다:

```
1단계: bash에서 JSON을 여러 파일로 분할 저장 (/tmp/chunk1.json, /tmp/chunk2.json, ...)
2단계: 각 파일의 내용을 Read 도구로 읽어 별도의 javascript_tool 호출로 브라우저에 주입
  - window.__data_chunk1 = {...};
  - window.__data_chunk2 = {...};
3단계: 브라우저에서 Object.assign으로 병합
  - window.__fullData = Object.assign({}, window.__data_chunk1, window.__data_chunk2);
```

---

## Step 1: 체험단 엑셀 파싱

### 엑셀 구조 (두 가지 유형)

**3pl N (네이버 스마트스토어) 체험단:**
- 파일명 패턴: `3pl N 체험단 {브랜드}_{날짜}-{hash}.xlsx`
- 주문번호 = 네이버 주문번호 (예: 2026041462326801)
- 송장 = "CJ대한통운 송장" 컬럼 (예: 6974-9792-0824, 하이픈 포함)

**3pl C (쿠팡) 체험단:**
- 파일명 패턴: `3pl C 체험단 {상품명} {날짜}_{timestamp}-{hash}.xlsx`
- 주문번호 = 쿠팡 주문번호 (예: 20100184052866)
- 송장 = "CJ대한통운 송장" 컬럼

### 파싱 실행

```bash
python3 <skill-path>/scripts/parse_excel.py \
  --input-dir <업로드_디렉토리> \
  --output /tmp/binbox_orders.json
```

### 파싱 후 wyblMap 생성

파싱 결과에서 shmaOrdNo → wyblNo 매핑 딕셔너리를 추가 생성:

```python
import json
with open('/tmp/binbox_orders.json') as f:
    data = json.load(f)
wybl_map = {o['ordNo']: o['wyblNo'] for o in data['orders'] if o['wyblNo']}
with open('/tmp/binbox_wyblmap.json', 'w') as f:
    json.dump(wybl_map, f)
```

이 wyblMap은 이후 모든 단계에서 빈박스 필터링과 운송장 매핑에 사용된다.

---

## Step 2: 사방넷 로그인 확인

사방넷은 **반드시 `https://www.sabangnet.co.kr/`** 에서 로그인한다.
`sbadmin03.sabangnet.co.kr`로 직접 접속하면 세션 문제가 발생한다.

로그인 확인:
```javascript
const app = document.querySelector('#app');
const loggedIn = app && app.__vue__ && app.__vue__.$store.getters.token;
```

---

## Step 3: 주문서수집(자동) 실행 (필수!)

**파이프라인 시작 전 반드시 주문서수집을 실행하고 3분 이상 대기해야 한다.**

04-28에 주문수집 미실행으로 16건(375건 중)이 누락된 사고가 발생했다.
30초~1분 대기는 부족하며, 3분은 기다려야 모든 주문이 안정적으로 수집된다.

### 주문수집 날짜 범위 규칙

빈박스 처리 시 주문서수집의 범위는 "마지막으로 처리한 날의 다음 날 ~ 오늘"이다.

**평일 기본 패턴:**
- 월요일: 금~월 (3일치, 주말 포함)
- 화~금: 전날~당일 (1일치)

**공휴일/임시공휴일 고려:**
- 빨간날이 끼어 있으면 그 날도 포함하여 수집 범위를 넓힌다.

### 실행 후 확인

1. 주문서수집(자동) 페이지에서 수집 실행
2. **3분 이상 대기**
3. 수집 완료 시점이 당일인지 반드시 확인
4. 확인 후 주문확정으로 넘어감

---

## Step 4: 주문서확정관리 (일괄확정)

```javascript
window.location.hash = '#/order/order-decide';
window.__cleanIframe = null;
```

1. 컴포넌트 찾기: `findByFile(app, 'order-decide.vue')`
2. 검색 실행 (오늘 날짜)
3. `comp.popItemBatchMapping()` → 일괄품번매핑 팝업

일부 주문이 품번매핑 실패할 수 있다 (신규 상품 등).
매핑 실패 건수를 사용자에게 보고하고, 수동 매핑을 요청한다.

---

## Step 5: 주문서확인처리 (001→002)

### 방법 A: API 직접 호출 (04-22 검증, 329건 성공)

**엔드포인트**: `POST /prod-api/customer/order/OrderConfirm/exeOrderConfirmOrderStatusChange`

```javascript
const body = {
  orderStatus: "002",
  selectData: "1",
  songClear: "",
  orderCancelReason: "",
  claimContent: "",
  list: found.map(o => ({
    ordNo: o.ordNo,
    ordStsCd: "001",
    ordStsCdList: ["001", "007"],
    shmaId: o.shmaId || "shop0075",
    shmaOrdNo: o.shmaOrdNo,
    ordInputDivCd: o.ordInputDivCd || "01",
    svcAcntId: "mw159514",
    ordStsTpDivCd: o.ordStsTpDivCd || "N",
    songClear: null,
    claimClear: null,
    changeClaimContent: null,
    prdNo: null,
    skuNo: null
  })),
  selectListSize: found.length,
  searchListSize: found.length,
  allPartnerId: "mw159514",    // 필수! 없으면 에러
  svcAcntId: "mw159514",
  fnlChgUserId: "eithercompany",
  fnlChgIp4a: "59.7.45.135",
  fnlChgPrgmNm: "order-confirm-order-status-change-popup",
  fstRegsUserId: "eithercompany",
  fstRegsIp4a: "59.7.45.135",
  fstRegsPrgmNm: "order-confirm-order-status-change-popup"
};
```

**핵심 포인트**:
- `allPartnerId: "mw159514"` — 없으면 "주문서 상태변경 실패" 에러
- `selectListSize` = list 배열 길이와 동일 — 없으면 "선택된 주문서 개수 비교 시 비정상"
- `ordStsCdList: ["001", "007"]` — 반드시 배열
- songClear, claimClear, changeClaimContent, prdNo, skuNo는 반드시 null
- 한 번에 전체 건수 처리 가능 (329건 한 번에 성공 확인)

### 방법 B: UI 자동화

```javascript
window.location.hash = '#/order/order-confirm';
window.__cleanIframe = null;

const middle = findByFile(app, 'order-confirm-vue-middle.vue');
middle.sbForm.ordStsCd = '001';
middle.sbForm.startDate = 'YYYYMMDD';
middle.sbForm.endDate = 'YYYYMMDD';
middle.goSearch();

// 다음 호출에서: 전체 선택 → 상태변경 팝업
// middle.handleSelectionChange(middle.gridData);
// findByFile(app, 'order-confirm-vue-middle-bottom.vue').popOpenOrderConfirmOrderStatusChange();
```

### 방법 C: 사용자 수동 (1~2분)

A, B 실패 시: "주문서확인처리에서 검색 → 전체 선택 → 주문상태변경 → 주문확인 클릭해주세요"

---

## Step 6: ordMapping 구축 (shmaOrdNo → ordNo)

CJ운송장 API는 **사방넷 내부 ordNo**를 사용한다 (shmaOrdNo 아님!).

```javascript
const middle = findByFile(app, 'order-confirm-vue-middle.vue');
const sbForm = JSON.parse(JSON.stringify(middle.sbForm));
sbForm.mode = 'search';
sbForm.ordStsCd = '002';
sbForm.searchDateType = 'ORD_DT';
sbForm.pageSize = 2000;  // 2000건씩 페이지네이션

xhr.open('POST', '.../prod-api/customer/order/OrderConfirm/searchOrders', true);
// 응답: data.orderList[].ordNo(내부), data.orderList[].shmaOrdNo(쇼핑몰)
```

빈박스 필터 + uploadData 생성:
```javascript
const binboxSet = new Set(Object.keys(wyblMap));
const uploadData = orderList
  .filter(o => binboxSet.has(o.shmaOrdNo))
  .map(o => ({ ordNo: String(o.ordNo), wyblNo: wyblMap[o.shmaOrdNo] }));
```

**ordMapping 건수 검증**: 반드시 엑셀 원본 건수와 일치시킨 후 다음 단계 진행.
04-22에 335건 중 330건만 매핑되어 5건이 누락된 적 있음. 날짜 범위를 좁게 잡아 검색 속도 최적화.

---

## Step 7: CJ운송장 대량입력 (04-21 검증 완료)

### SheetJS 로딩

```javascript
if (!window.XLSX) {
  const s = document.createElement('script');
  s.src = 'https://cdn.sheetjs.com/xlsx-0.20.1/package/dist/xlsx.full.min.js';
  document.head.appendChild(s);
}
```

### 페이지 이동 + 업로드

```javascript
window.location.hash = '#/order/waybill-input-large';
window.__cleanIframe = null;
```

```javascript
const rows = uploadData.map(d => [String(d.ordNo), String(d.wyblNo), '', '', '003']);
const ws = XLSX.utils.aoa_to_sheet(rows);
Object.keys(ws).forEach(key => { if (key[0] !== '!') ws[key].t = 's'; });
const wb = XLSX.utils.book_new();
XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');
const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
const blob = new Blob([wbout], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
const file = new File([blob], 'waybill_cj.xlsx', { type: blob.type });

const formData = new FormData();
formData.append('file', file, 'waybill_cj.xlsx');
formData.append('pcscpCd', '003');
formData.append('exclFormSrno', '-99');
formData.append('exclFormDivCd', '08');
formData.append('fnlChgUserId', 'eithercompany');
formData.append('fnlChgIp4a', '59.7.45.135');
formData.append('fnlChgPrgmNm', 'waybill-input-large');

const xhr = new CleanXHR();
xhr.open('POST', '.../prod-api/customer/order/waybill/updateLargeWaybillInput', true);
xhr.setRequestHeader('Authorization', token);
// Content-Type 절대 직접 설정 안 함!
xhr.send(formData);
```

---

## Step 8: 쇼핑몰운송장송신 (04-21 검증된 4단계 패턴)

sendWybl()은 no-op이고, 강제전환은 절대 금지. 아래가 유일한 방법이다.

```javascript
window.location.hash = '#/mall/mall-waybill-transmit';
window.__cleanIframe = null;
```

### 모달 hide 차단 (필수!)

mallWaybillTransmitPopup() 호출 시 모달이 생성 후 즉시 사라진다.
내부 컴포넌트가 mounted 후 $modal.hide()를 자동 호출하는 것으로 추정.
반드시 popup 호출 전에 hide를 차단한다:

```javascript
const comp = findByFile(app, 'mall-waybill-transmit.vue');
comp.__origHide = comp.$modal.hide;
comp.$modal.hide = function() {};  // 빈 함수로 대체
```

### 8-1: getWaybillTransmitInfo

```javascript
xhr.open('POST', '.../prod-api/customer/mall/MallWaybillTransmit/getWaybillTransmitInfo', true);
xhr.send(JSON.stringify({ svcAcntId: 'mw159514', ordNoList: ordNoList.map(Number) }));
// → window.__sendDatas = response.data.list
```

### 8-2: mallWaybillTransmitPopup

```javascript
comp.mallWaybillTransmitPopup(window.__sendDatas, 'N');
```

### 8-3: iframe name 설정 (다음 javascript_tool 호출에서)

```javascript
for (const f of document.querySelectorAll('iframe')) {
  if (f.src && f.src.includes('127.0.0.1:8181')) { f.name = 'mallWayBillSong'; break; }
}
```

### 8-4: form.submit()

```javascript
for (const f of document.querySelectorAll('form')) {
  if (f.target === 'mallWayBillSong' && f.action.includes('127.0.0.1')) { f.submit(); break; }
}
```

### 배치 전송 후 폴링 확인 (고정 대기 금지!)

form.submit() 후 고정 sleep 대신 폴링으로 전송완료를 확인한다.
04-24에 고정 대기 패턴으로 79건 누락 발생.

```
for each batch:
  1. getWaybillTransmitInfo
  2. $modal.hide 차단 → mallWaybillTransmitPopup → iframe name → form.submit
  3. 폴링 루프: 3초 간격으로 getMallWaybillTransmitLists 조회
     → 해당 배치의 ordNo들이 전부 '전송완료'가 될 때까지 대기
     → 최대 60초 타임아웃
  4. DOM 정리 (모달/iframe/form 제거)
  5. 다음 배치
```

### 배치 간 DOM 정리 (필수!)

이전 배치의 모달과 iframe을 완전히 제거한 후 다음 배치 시작:

```javascript
document.querySelectorAll('.vm--overlay, .vm--modal, .vm--container').forEach(el => el.remove());
document.querySelectorAll('iframe[src*="127.0.0.1"], iframe[name="mallWayBillSong"]').forEach(el => el.remove());
document.querySelectorAll('form[target="mallWayBillSong"]').forEach(el => el.remove());
```

### 배치 분할 기준

- 160건 이하: 1배치
- 160~320건: 2배치 (160+나머지)
- 320건 이상: 160건씩 분할

### 결과 확인

```javascript
// getMallWaybillTransmitLists (comp.sbForm deep clone 필수!)
// wyblTrnmErrMsg === '전송완료' 확인
```

---

## Step 9: 크로스체킹

원본 shmaOrdNo Set vs 전송완료 shmaOrdNo Set 대조.
누락 건 있으면 파일별 그룹핑 상세 리포트 + 엑셀 생성.

---

## 에러 처리

| 증상 | 원인 | 해결 |
|------|------|------|
| code 10000 | 토큰 만료 또는 body 형식 | UI 검색 클릭 → 토큰 재취득, comp.sbForm deep clone |
| API 500 | 서버 불안정 | UI 우회 또는 사용자 수동 |
| 운송장 fail > 0 | 이미 입력 또는 ordNo 불일치 | ordMapping 확인 |
| 보안프로그램 연결 실패 | 127.0.0.1:8181 미실행 | 사용자에게 실행 요청 |
| iframe 파괴 | 페이지 이동 | `__cleanIframe = null` 후 재생성 |
| 데이터 truncation | JS 주입 크기 제한 | 청크 분할 주입 |
| 모달 즉시 닫힘 | $modal.hide 자동 호출 | hide를 빈 함수로 대체 |
| 배치 간 전송 실패 | 이전 DOM 잔존 | 모달/iframe/form 제거 후 재시도 |

---

## 빈박스 vs 실배송 구분 규칙

- **쿠팡 빈박스**: 배송지 주소에 `%` 문자 포함
- **네이버 빈박스**: 배송메시지에 "문 앞에 놓아주세요!" 포함
- **최종 확인**: 체험단 엑셀의 주문번호 크로스체킹
