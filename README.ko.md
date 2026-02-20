🇰🇷 한국어 | [🇺🇸 English](./README.md)

# kmathbraille ⠿

> LaTeX 수학 수식을 한국 수학 점자로 변환하는 파이썬 라이브러리 입니다.  
> (문화체육관광부고시 제2024-0005호)

by [Qualia Bridge](https://www.linkedin.com/in/iamboram)

---

## ✨ 왜 kmathbraille인가요?

한국의 시각장애 학생들은 점자로 수학 교육에 접근하기 어려운 경우가 많습니다.  
또한 기존 도구들은 정확성, 투명성, 확장성이 부족했습니다.  

kmathbraille은 보기 드문 세 가지를 갖춘 사람이 만들었습니다:  

- 📖 점자 전문가
- 📊 통계 및 데이터사이언스 석사 
- 📈 데이터 시각화 개발자

---

## 🚧 현재 상태

현재 활발히 개발 중입니다 (스텔스 모드).
Star를 눌러 함께 지켜봐 주세요!

### 로드맵
- [x] v0.1 — 사칙연산 (+, -, *, /) 및 괄호
- [x] v0.2 — 분수 (`\frac`) & 대분수
- [x] v0.3 — 지수 및 첨자 (`^`, `_`)
- [x] v0.4 — 제곱근 (`\sqrt`)
- [x] v0.5 — 삼각함수
- [x] v1.0 — PyPI 정식 배포 🚀
- [x] v1.1 — 알파벳 점자 전수 검증
- [ ] v2.0 — to be continued
- [ ] v3.0 — to be continued

---

## 📦 설치

터미널에서 아래 명령어를 통해 설치할 수 있습니다:

```bash
pip install kmathbraille
```
설치 후 파이썬 코드에서 다음과 같이 사용하세요:

```python
from kmathbraille import to_braille as tb

print(tb(r"\frac{1}{2}"))  # 결과: ⠼⠃⠌⠼⠁ (분수)
print(tb(r"x^{2}"))        # 결과: ⠭⠘⠼⠃ (지수)
print(tb(r"\sqrt{2}"))     # 결과: ⠜⠼⠃ (제곱근)
print(tb(r"\sin{x}"))      # 결과: ⠖⠎⠭ (삼각함수)
```

---

## 🤝 기여하기

기여를 환영합니다!
특히 점자 전문가와 수학 교육자분들의 참여를 기다립니다.

---

## 📄 라이선스

MIT License © 2026 Qualia Bridge
