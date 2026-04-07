# FontAgent Vault

이 폴더는 `FontAgent`의 레퍼런스 학습 데이터를 옵시디언 볼트 친화 구조로 저장하는 기본 위치입니다.

기본 구조:

- `Fonts/<medium>/<surface>/*.md`
- `Fonts/<medium>/<surface>/_assets/*.png`
- `Fonts/<medium>/<surface>/_raw/*.json`
- `Fonts/_index/font-references.md`

용도:

- 초기 트렌드 카테고리별 폰트 사용 레퍼런스 저장
- 이후 주기적 incremental 학습 누적
- 나중에 벡터화/인덱싱할 때 frontmatter + 원본 추출 데이터 재사용

기본 CLI:

```bash
python3 -m fontagent.cli --root /Users/jleavens_macmini/Projects/fontagent reference-vault
python3 -m fontagent.cli --root /Users/jleavens_macmini/Projects/fontagent list-reference-packs
python3 -m fontagent.cli --root /Users/jleavens_macmini/Projects/fontagent learn-reference-pack --pack trend-korean-brand-display --continue-on-error
```
