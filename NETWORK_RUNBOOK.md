# FontAgent Network Runbook

외부 네트워크가 가능한 세션에서 바로 실행할 작업만 정리한 문서입니다.

## 목표

- 눈누 라이브 HTML 수집
- 상세 페이지 다운로드 링크 확인
- 실제 설치 가능한 폰트 카탈로그 확장

## 준비

```bash
cd /Users/jleavens_macmini/Projects/fontagent
python3 -m fontagent.cli --root /Users/jleavens_macmini/Projects/fontagent init
```

## 1. 라이브 Noonnu 스냅샷 가져오기

```bash
python3 -m fontagent.cli --root /Users/jleavens_macmini/Projects/fontagent fetch-noonnu \
  --listing-url https://noonnu.cc/ \
  --output-dir /Users/jleavens_macmini/Projects/fontagent/examples/noonnu_snapshot \
  --limit 30
```

확인할 경로:

- `/Users/jleavens_macmini/Projects/fontagent/examples/noonnu_snapshot/listing.html`
- `/Users/jleavens_macmini/Projects/fontagent/examples/noonnu_snapshot/details/*.html`

## 2. 브라우저가 필요한 다운로드 식별

```bash
python3 -m fontagent.cli --root /Users/jleavens_macmini/Projects/fontagent resolve-download maruburi
python3 -m fontagent.cli --root /Users/jleavens_macmini/Projects/fontagent prepare-browser-task maruburi \
  --output-dir /Users/jleavens_macmini/Projects/fontagent/examples/browser_tasks
```

## 3. 웹 UI

```bash
python3 -m fontagent.cli --root /Users/jleavens_macmini/Projects/fontagent serve --port 8123
```

브라우저:

- `http://127.0.0.1:8123`

UI에서 가능한 것:

- 검색
- 추천
- SVG 미리보기
- 설치 시도
- CSS export
- Remotion export
- resolve-download
- browser task 생성

## 4. 체크 포인트

- 눈누 실제 상세 HTML이 fixture와 얼마나 다른지
- 다운로드 버튼이 direct 링크인지, redirect인지, JS 실행이 필요한지
- zip 다운로드 시 내부 폰트 파일 확장자 구조
- 라이선스 요약 텍스트가 현재 파서로 충분히 잡히는지

## 5. 외부 네트워크가 필요한 이유

- `fetch-noonnu`: 라이브 HTML 가져오기
- 실제 폰트 파일 설치: 다운로드 URL 접근
- browser task 처리: 최종 파일 링크 추출
