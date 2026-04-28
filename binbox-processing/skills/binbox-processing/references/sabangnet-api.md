# 사방넷 API 레퍼런스

> 최종 검증일: 2026-04-21

## 기본 정보

- **베이스 URL**: `https://sbadmin03.sabangnet.co.kr/prod-api`
- **로그인 URL**: `https://www.sabangnet.co.kr/` (sbadmin03 직접 접속 금지)
- **인증**: Authorization 헤더에 JWT 토큰 (Bearer 접두사 없음)
- **토큰 획득**: `document.querySelector('#app').__vue__.$store.getters.token`
- **Content-Type**: `application/json` (FormData 제외)
- **svcAcntId**: `mw159514`
- **사용자ID**: `eithercompany`

## Clean XHR 패턴 (필수)

Chrome 확장프로그램이 XMLHttpRequest를 패치하여 FormData와 응답을 손상시킨다.
모든 API 호출에 이 패턴을 사용해야 한다:

```javascript
async function getCleanXHR() {
  if (window.__cleanIframe && window.__cleanIframe.contentWindow) {
    try {
      const test = window.__cleanIframe.contentWindow.XMLHttpRequest;
      if (test) return test;
    } catch(e) { /* iframe destroyed */ }
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

**주의**: 페이지 이동 후 `window.__cleanIframe = null` 필수 (iframe 파괴됨)

## Vue 컴포넌트 탐색

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

## API 엔드포인트

### 주문서확인처리

#### 주문 목록 조회 (04-21 검증)

**주의: 엔드포인트 변경됨**
- 구버전: `getOrderConfirmLists` → 사용 금지
- 신버전: `searchOrders`
- 응답 구조: `data.list` → `data.orderList`

```
POST /customer/order/OrderConfirm/searchOrders
Authorization: {token}
Content-Type: application/json
Body: comp.sbForm의 deep clone (직접 body 구성 금지)
  필수 필드:
    mode: "search"
    ordStsCd: "001" (미확인) 또는 "002" (확인)
    searchDateType: "ORD_DT"
    startDate: "YYYYMMDD"
    endDate: "YYYYMMDD"
    currentPage: 1
    pageSize: 2000

응답: {
  code: 20000,
  data: {
    orderList: [...],          // data.list 아님!
    totAmtSummary: { totCnt: N }
  }
}
```

orderList 주요 필드:
- `ordNo`: 사방넷 내부 주문번호 (숫자)
- `shmaOrdNo`: 쇼핑몰 주문번호 (문자열)
- `shmaId`: 쇼핑몰ID (shop0075=쿠팡, shop0055=스마트스토어)
- `ordStsCd`: 주문 상태 코드
- `clctPrdNm`: 상품명

#### 주문 상태 변경 (001→002) — 불안정

```
POST /customer/order/OrderConfirm/updateOrdStsCd
Body: {
  "svcAcntId": "mw159514",
  "ordNoList": [숫자배열],     // 사방넷 내부 ordNo
  "ordStsCd": "002"
}
```

**경고**: 이 API는 서버 상태에 따라 500 에러 반환 (04-20, 04-21 모두 실패).
UI 자동화 또는 사용자 수동 처리를 우선 사용할 것.

### 운송장입력(대량) — 04-21 검증 완료

```
POST /customer/order/waybill/updateLargeWaybillInput
Authorization: {token}
Content-Type: multipart/form-data (자동 설정 — 직접 설정 금지!)

FormData:
  - file: Excel파일 (.xlsx, SheetJS로 생성)
  - pcscpCd: "003" (CJ택배)
  - exclFormSrno: "-99"
  - exclFormDivCd: "08"
  - fnlChgUserId: "eithercompany"
  - fnlChgIp4a: "59.7.45.135"
  - fnlChgPrgmNm: "waybill-input-large"
```

**엑셀 형식** (5열, 헤더 없음, 모든 셀 t='s'):

| 열 | 내용 | 주의 |
|----|------|------|
| A | 사방넷 내부 ordNo | shmaOrdNo 아님! |
| B | CJ운송장번호 | 12자리 숫자 |
| C | (빈칸) | |
| D | (빈칸) | |
| E | 택배사코드 | 003 |

응답:
```json
{"code":20000,"progress":[{"ordNo":"2134476513","success":true}, ...]}
// 또는: {"code":20000,"total":335,"success":335,"fail":0}
```

### 쇼핑몰운송장송신 — 04-21 검증된 4단계 패턴

#### 전송 대상 조회 (sbForm deep clone 필수!)

```
POST /customer/mall/MallWaybillTransmit/getMallWaybillTransmitLists
Body: comp.sbForm의 deep clone
  필수 필드 오버라이드:
    mode: "search"
    modePath: "list_song"
    searchDateType: "WYBL_INPUT_DT"
    startDate: "YYYYMMDD"
    endDate: "YYYYMMDD"
    pageSize: 500

응답: { code: 20000, data: { list: [...], total: N } }
```

**경고**: 직접 body를 구성하면 code 10000 에러.
반드시 `JSON.parse(JSON.stringify(comp.sbForm))`으로 deep clone 후 필드 오버라이드.

응답 레코드 주요 필드:
- `ordNo`: 사방넷 내부 주문번호
- `shmaOrdNo`: 쇼핑몰 주문번호
- `wyblTrnmErrMsg`: "전송완료" 또는 오류 메시지
- `shmaId`: 쇼핑몰ID

#### 전송 정보 조회 (모달용)

```
POST /customer/mall/MallWaybillTransmit/getWaybillTransmitInfo
Body: {
  "svcAcntId": "mw159514",
  "ordNoList": [숫자배열]     // 200건 이하 권장
}
응답: { code: 20000, data: { list: [...sendDatas...] } }
```

#### 실제 전송 (4단계 — 유일하게 검증된 방법)

```
1. getWaybillTransmitInfo → sendDatas 획득
2. comp.mallWaybillTransmitPopup(sendDatas, 'N') → 모달 오픈
3. iframe[src*="127.0.0.1:8181"].name = 'mallWayBillSong'
4. form[target="mallWayBillSong"].submit() → 보안프로그램 경유 실제 전송
```

#### 절대 금지 API

```
POST /customer/mall/MallWaybillTransmit/updateMallWaybillTransmitForce
→ 강제전환. 쇼핑몰에 실제 전송 안 됨. 사방넷 상태만 변경. 절대 사용 금지.
→ 04-20에 1,198건 미전송 사고 발생.

comp.sendWybl()
→ no-op. 네트워크 요청 생성하지 않음. 04-21 검증됨. 사용 금지.
```

## SheetJS CDN

```
https://cdn.sheetjs.com/xlsx-0.20.1/package/dist/xlsx.full.min.js
```

## 쇼핑몰 코드

| shmaId | 쇼핑몰명 |
|--------|----------|
| shop0075 | 쿠팡 |
| shop0055 | 스마트스토어 (네이버) |

## 주문 상태 코드

| ordStsCd | 상태 |
|----------|------|
| 001 | 미확인 |
| 002 | 확인완료 |
| 003 | 운송장입력 |
