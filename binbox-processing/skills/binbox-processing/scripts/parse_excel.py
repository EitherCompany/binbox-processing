#!/usr/bin/env python3
"""
체험단 엑셀 파싱 스크립트
- 3pl N (네이버) / 3pl C (쿠팡) 체험단 엑셀에서 주문번호 + CJ송장번호 추출
- 송장번호 하이픈 제거 및 12자리 정규화
"""

import openpyxl
import json
import os
import re
import sys
import argparse


def normalize_waybill(wybl_str):
    """송장번호 정규화: 하이픈 제거, 숫자만 추출"""
    if not wybl_str:
        return ''
    return re.sub(r'[^0-9]', '', str(wybl_str).strip())


def detect_mall(filename):
    """파일명으로 쇼핑몰 판별"""
    fname = os.path.basename(filename).lower()
    if '3pl n' in fname or 'n 체험단' in fname:
        return 'naver'
    elif '3pl c' in fname or 'c 체험단' in fname:
        return 'coupang'
    return 'unknown'


def parse_single_file(filepath):
    """단일 엑셀 파일 파싱"""
    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active

    # 1행 헤더 읽기
    header_row = list(ws.iter_rows(min_row=1, max_row=1, values_only=True))[0]
    headers = [str(h).strip() if h else '' for h in header_row]

    # 컬럼 인덱스 매핑
    col_map = {}
    for idx, h in enumerate(headers):
        h_lower = h.lower().replace(' ', '')
        if '주문번호' in h:
            col_map['ordNo'] = idx
        elif 'cj' in h_lower and '송장' in h:
            col_map['wyblNo'] = idx
        elif h == '체험단 이름':
            col_map['name'] = idx
        elif h == '체험단 전화번호':
            col_map['phone'] = idx
        elif h == '체험단 주소':
            col_map['address'] = idx
        elif '상품 메모' in h or '상품메모' in h:
            col_map['product'] = idx
        elif '선택 옵션' in h or '선택옵션' in h:
            col_map['option'] = idx

    mall = detect_mall(filepath)
    fname = os.path.basename(filepath)
    orders = []

    for row in ws.iter_rows(min_row=2, values_only=True):
        vals = list(row)
        if not vals or all(v is None for v in vals):
            continue

        ord_no = str(vals[col_map.get('ordNo', 0)]).strip() if col_map.get('ordNo') is not None else ''
        if not ord_no or ord_no == 'None':
            continue

        wybl_raw = str(vals[col_map.get('wyblNo', -1)]) if col_map.get('wyblNo') is not None and col_map['wyblNo'] < len(vals) else ''
        wybl_no = normalize_waybill(wybl_raw)

        order = {
            'ordNo': ord_no,
            'wyblNo': wybl_no,
            'wyblRaw': wybl_raw.strip() if wybl_raw != 'None' else '',
            'name': str(vals[col_map['name']]).strip() if col_map.get('name') is not None and col_map['name'] < len(vals) and vals[col_map['name']] else '',
            'phone': str(vals[col_map['phone']]).strip() if col_map.get('phone') is not None and col_map['phone'] < len(vals) and vals[col_map['phone']] else '',
            'address': str(vals[col_map['address']]).strip() if col_map.get('address') is not None and col_map['address'] < len(vals) and vals[col_map['address']] else '',
            'product': str(vals[col_map['product']]).strip() if col_map.get('product') is not None and col_map['product'] < len(vals) and vals[col_map['product']] else '',
            'option': str(vals[col_map['option']]).strip() if col_map.get('option') is not None and col_map['option'] < len(vals) and vals[col_map['option']] else '',
            'file': fname,
            'mall': mall
        }
        orders.append(order)

    wb.close()
    return orders


def main():
    parser = argparse.ArgumentParser(description='체험단 엑셀 파싱')
    parser.add_argument('--input-dir', required=False, help='엑셀 파일들이 있는 디렉토리')
    parser.add_argument('--files', nargs='+', required=False, help='개별 엑셀 파일 경로들')
    parser.add_argument('--output', required=True, help='출력 JSON 경로')
    args = parser.parse_args()

    files_to_parse = []

    if args.files:
        files_to_parse = args.files
    elif args.input_dir:
        for f in os.listdir(args.input_dir):
            if f.endswith('.xlsx') and ('3pl' in f.lower() or '체험단' in f.lower()):
                files_to_parse.append(os.path.join(args.input_dir, f))
    else:
        print("ERROR: --input-dir 또는 --files 중 하나를 지정하세요", file=sys.stderr)
        sys.exit(1)

    if not files_to_parse:
        print("ERROR: 파싱할 엑셀 파일이 없습니다", file=sys.stderr)
        sys.exit(1)

    all_orders = []
    by_file = {}
    errors = []

    for fpath in sorted(files_to_parse):
        try:
            orders = parse_single_file(fpath)
            all_orders.extend(orders)
            by_file[os.path.basename(fpath)] = len(orders)
        except Exception as e:
            errors.append({'file': os.path.basename(fpath), 'error': str(e)})

    # 송장번호 없는 주문 체크
    no_wybl = [o for o in all_orders if not o['wyblNo']]

    result = {
        'total': len(all_orders),
        'orders': all_orders,
        'by_file': by_file,
        'no_waybill_count': len(no_wybl),
        'errors': errors
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 요약 출력
    print(f"총 {len(all_orders)}건 추출 ({len(files_to_parse)}개 파일)")
    for fname, cnt in by_file.items():
        print(f"  {fname}: {cnt}건")
    if no_wybl:
        print(f"⚠️ 송장번호 없는 주문: {len(no_wybl)}건")
    if errors:
        print(f"❌ 오류 파일: {len(errors)}개")
        for e in errors:
            print(f"  {e['file']}: {e['error']}")


if __name__ == '__main__':
    main()
