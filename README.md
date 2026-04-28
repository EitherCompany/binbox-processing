# binbox-processing

빈박스(체험단) 주문 자동 처리 플러그인 for Claude Cowork.

## 기능

체험단 엑셀 파일(N개)을 업로드하면 사방넷에서 전체 파이프라인을 자동 실행합니다:

1. 엑셀 파싱 (주문번호 + CJ송장번호 추출)
2. 주문서수집 실행 + 3분 대기
3. 주문서확정관리 (일괄확정)
4. 주문서확인처리 (001→002)
5. CJ운송장 대량입력
6. 쇼핑몰운송장송신 (4단계 검증 패턴)
7. 크로스체킹 + 결과 리포트

## 스킬

- **binbox-processing**: 체험단 주문 자동 처리 파이프라인
- **plugin-github-sync**: 플러그인 편집 시 GitHub 자동 동기화

## 설치

```
/plugin install binbox-processing@EitherCompany
```

## 업데이트

```
/plugin update binbox-processing@EitherCompany
```

## 실전 검증

- 2026-04-20 ~ 04-28: 8일간 누적 3,000건+ 처리
- 쿠팡/네이버 스마트스토어 지원
- 04-21 이후 100% 전송완료 달성

## 라이선스

MIT
