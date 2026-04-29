# 플러그인 GitHub 자동 동기화 스킬 (plugin-github-sync · v1.0.1)

`binbox-processing` 플러그인의 어떤 파일이든 편집됐을 때 **같은 세션 안에서 GitHub 레포까지 자동 푸시 + 릴리스 태그**까지 완결한다.

**이 스킬은 새 플러그인 프로젝트를 만들 때 레포 구조·marketplace.json 템플릿의 레퍼런스로도 활용된다.**

---

## 자동 트리거 조건

플러그인 내 다음 중 하나라도 변경되면 **별도 지시 없이 이 절차 착수**:

- `.claude-plugin/plugin.json` · `marketplace.json` 편집
- `skills/*/SKILL.md` 편집 또는 신규 스킬 추가
- `skills/*/references/*` · `skills/*/scripts/*` 편집
- `README.md` 편집
- 새 스킬 폴더 추가·기존 스킬 폴더 삭제

**Why**: 로컬 수정으로 끝내지 말고 타 PC 반영을 위해 무조건 레포 푸시까지 완결해야 한다. 어느 PC에서든 플러그인 편집 시 동일하게 자동 푸시 가능.

---

## 고정 상수

- **레포**: `EitherCompany/binbox-processing` (Private)
- **레포 URL**: https://github.com/EitherCompany/binbox-processing
- **PAT 저장 위치**: 노션 "👮 이창근" 페이지
  - pageId: `1d8d9e75-0367-80b3-9f32-e82210a58e20`
  - 본문에 `github_pat_...` 형태로 저장됨
- **PAT 범위**: EitherCompany org · repo · Fine-grained
- **기본 브랜치**: `main`

**PAT는 이 플러그인에 절대 하드코딩 금지** — secret scanning이 push 자체를 차단. 항상 런타임 노션 조회로 주입.

---

## 레포 구조

```
<repo>/
├── .claude-plugin/marketplace.json          ← 루트. version bump 필수
├── README.md · .gitignore
└── binbox-processing/                       ← 실제 플러그인 폴더
    ├── .claude-plugin/plugin.json            ← version bump 필수
    ├── README.md
    └── skills/
        ├── sabangnet-waybill/                ← 스킬 (이전 binbox-processing, v1.2.0에서 rename)
        │   ├── SKILL.md
        │   ├── references/
        │   │   └── sabangnet-api.md
        │   └── scripts/
        │       └── parse_excel.py
        └── plugin-github-sync/
            └── SKILL.md
```

**두 version 필드 모두 bump 필수** (`marketplace.json` · `plugin.json`) — 하나만 bump하면 불일치.

---

## 새 플러그인 프로젝트 생성 시 참고 (레퍼런스 템플릿)

다른 프로젝트에서 "이 플러그인 참고해서 만들어"라고 요청하면 아래 템플릿을 사용한다.

### marketplace.json 템플릿 (루트 `.claude-plugin/marketplace.json`)

**⚠️ 이 형식을 정확히 따르지 않으면 Cowork 마켓플레이스 등록이 실패한다.**

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "<레포이름>",
  "version": "1.0.0",
  "description": "<플러그인 한 줄 설명>",
  "owner": {
    "name": "EitherCompany",
    "email": "ghgh404@gmail.com",
    "url": "https://github.com/EitherCompany"
  },
  "plugins": [
    {
      "name": "<플러그인이름>",
      "description": "<상세 설명>",
      "version": "1.0.0",
      "author": {
        "name": "이창근 (이더컴퍼니)"
      },
      "source": "./<플러그인이름>",
      "category": "productivity",
      "keywords": ["keyword1", "keyword2"]
    }
  ]
}
```

**필수 요소** (하나라도 빠지면 마켓플레이스 등록 실패):
- `$schema`: `"https://anthropic.com/claude-code/marketplace.schema.json"`
- `owner`: `name`, `email`, `url` 세 필드 모두
- `plugins`: 배열 형태, 각 항목에 `name`, `source`, `version` 필수
- `plugins[].source`: `"./<플러그인폴더명>"` 형태 — 레포 내 플러그인 폴더 경로

### plugin.json 템플릿 (`<플러그인이름>/.claude-plugin/plugin.json`)

```json
{
  "name": "<플러그인이름>",
  "version": "1.0.0",
  "description": "<상세 설명>",
  "author": {
    "name": "이창근 (이더컴퍼니)",
    "email": "ghgh404@gmail.com"
  },
  "homepage": "https://github.com/EitherCompany/<레포이름>",
  "repository": "https://github.com/EitherCompany/<레포이름>",
  "license": "MIT",
  "keywords": ["keyword1", "keyword2"]
}
```

### 새 레포 생성 절차

```bash
# 1. GitHub API로 Private 레포 생성
curl -sS -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/user/repos \
  -d '{"name":"<레포이름>","private":true,"auto_init":false}'

# 2. 로컬에서 파일 구조 생성 → git init → push
# 3. Cowork 마켓플레이스 추가 URL (`.git` 없이!):
#    https://github.com/EitherCompany/<레포이름>
```

### plugin-github-sync 스킬 복제

새 플러그인에도 자동 동기화 스킬을 넣으려면:
1. 이 SKILL.md를 복사
2. "고정 상수" 섹션의 레포명만 변경
3. Step 4, 7, 8의 URL을 새 레포로 변경
4. Step 9의 `/plugin update` 명령을 새 플러그인명으로 변경

---

## 자동 실행 절차 (9단계)

### Step 1 — PAT 조회 (노션에서)

```
notion-fetch(id: "1d8d9e75-0367-80b3-9f32-e82210a58e20")
```

응답 본문에서 `github_pat_...` 패턴을 정규표현식으로 추출:
```python
import re
match = re.search(r'github_pat_[A-Za-z0-9_]+', page_body)
token = match.group(0)
```

노션에서 PAT 발견 안 되면 그때만 창근님께 한 줄로 요청: "GitHub 동기화 시작, PAT 요청드립니다".

### Step 2 — 로컬 변경본 확인

편집한 파일 목록을 확인하고, 커밋 메시지에 반영할 요약 준비.

### Step 3 — 버전 bump (필수)

**두 곳 모두** 같은 버전으로:
- `.claude-plugin/marketplace.json` (루트)
- `binbox-processing/.claude-plugin/plugin.json` (플러그인 내부)

버전 규칙 (semver):
- **patch (x.y.N)**: 문구 수정, 버그 픽스, 오타 교정
- **minor (x.Y.0)**: 새 정책·스킬·기능 추가
- **major (X.0.0)**: 구조 변경

### Step 4 — git clone (임시 디렉토리)

```bash
TOKEN="github_pat_..."
rm -rf /tmp/repo-clone
git clone --depth 1 "https://x-access-token:${TOKEN}@github.com/EitherCompany/binbox-processing.git" /tmp/repo-clone
```

### Step 5 — 변경본 덮어쓰기

```bash
cp -rf /tmp/<build>/plugin-rebuild/. /tmp/repo-clone/binbox-processing/
```

루트 `.claude-plugin/marketplace.json`도 갱신.

### Step 6 — Secret 검사 (push 전 필수)

```bash
grep -r "github_pat_\|password.*=.*['\"]\|api_key" /tmp/repo-clone --exclude-dir=.git | head
```

PAT나 하드코딩된 secret 발견되면 **푸시 중단 → 창근님에게 알림**.

### Step 7 — 커밋 · 태그 · 푸시

```bash
cd /tmp/repo-clone
git config user.email "ghgh404@gmail.com"
git config user.name "이창근"
git add -A
git commit -m "v<N>.<M>.<K>: <한 줄 요약>"
git tag v<N>.<M>.<K>
git push origin main
git push origin v<N>.<M>.<K>
```

### Step 8 — GitHub 릴리스 생성

```bash
curl -sS -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/repos/EitherCompany/binbox-processing/releases \
  -d '{
    "tag_name":"v<N>.<M>.<K>",
    "name":"v<N>.<M>.<K> — <한 줄 요약>",
    "body":"## 변경사항\n\n- ...\n\n## 설치·업데이트\n\n`/plugin update binbox-processing@EitherCompany`",
    "draft":false,
    "prerelease":false
  }'
```

### Step 9 — 정리 · 보고

```bash
rm -rf /tmp/repo-clone  # PAT 잔존 방지
```

창근님에게 전달:
- 커밋 URL
- 릴리스 URL
- 변경 요약
- 타 PC 반영 명령: `/plugin update binbox-processing@EitherCompany`

---

## 금지 사항

1. **GitHub 웹 UI 자동화 편집 금지** — `git push` 경로만 허용
2. **PAT를 플러그인·커밋·로그에 노출 금지** — 노션에서만 조회, 사용 후 bash 변수 폐기
3. **한 버전 필드만 bump 금지** — `marketplace.json`과 `plugin.json` 둘 다 동기 bump
4. **marketplace.json에 `plugins` 배열 누락 금지** — 단순 name/version 구조는 마켓플레이스 등록 실패

---

## 완료 기준

- [ ] 노션에서 PAT 자동 조회 완료
- [ ] `marketplace.json` + `plugin.json` 동기 버전 bump
- [ ] Secret 검사 통과
- [ ] `git push origin main` + `git push origin v<N>.<M>.<K>` 성공
- [ ] GitHub 릴리스 생성 성공
- [ ] `/tmp/repo-clone` 정리
- [ ] 커밋·릴리스 URL 창근님에게 공유
