"""
╔══════════════════════════════════════════════════════════════════╗
║          kobraille - LaTeX 수학 수식 → 한국 점자 변환기           ║
║                       v3  (Visitor 패턴 적용)                    ║
╚══════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
★ 이 파일의 전체 흐름 (4단계)

  [입력] "2 + 3 * 4"  ← 사람이 쓰는 LaTeX 수식
      │
      ▼
  ① LEXER (어휘 분석기)
      문자열을 "단어(Token)" 단위로 잘라냄
      → [NUMBER(2), PLUS(+), NUMBER(3), STAR(*), NUMBER(4), EOF]
      │
      ▼
  ② PARSER (구문 분석기)
      Token들을 수학 구조(트리)로 조립. 우선순위 자동 처리.
      →       BinaryOpNode(+)      ← "+"는 우선순위가 낮아서 루트
              ├─ NumberNode(2)
              └─ BinaryOpNode(*)   ← "*"는 우선순위가 높아서 먼저 묶임
                  ├─ NumberNode(3)
                  └─ NumberNode(4)
      │
      ▼
  ③ AST (추상 구문 트리)
      위의 트리 구조 자체. 수식의 "의미"를 담은 데이터.
      │
      ▼
  ④ VISITOR (방문자)
      트리를 돌아다니며 원하는 작업을 수행.
      → BrailleVisitor  : 점자 문자열 생성  ← 지금 구현된 것
      → DebugVisitor    : 수식 구조 확인용  ← 지금 구현된 것
      → MathMLVisitor   : MathML 변환       ← 나중에 쉽게 추가 가능
      │
      ▼
  [출력] "⠼⠃⠐⠖⠼⠉⠐⠦⠼⠙"  ← 한국 점자

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
★ v2(AST)에서 v3(Visitor)로 바뀐 이유

  v2에서는 to_braille() 함수 하나에 점자 변환 로직이 전부 들어있었음.
  → 나중에 "점자 말고 MathML로도 변환하고 싶다"면? 코드 전체를 뜯어야 함.

  v3에서는 변환 로직을 Visitor 클래스로 분리.
  → MathMLVisitor 클래스 하나만 새로 만들면 됨. 기존 코드 수정 없음!
  → 이것이 Visitor 패턴의 핵심 장점 (확장에 열려있고, 수정에 닫혀있음)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
★ 한국 수학 점자 규정 근거: KS X 1107 (2023)

  수표  ⠼  : 점 3-4-5-6   숫자 블록이 시작될 때 앞에 붙임
  0~9  → 각 숫자별 점자 (DIGIT_MAP 참조)
  +   ⠐⠖  : 점 5, 점 2-3-5    덧셈
  -   ⠐⠤  : 점 5, 점 3-6      뺄셈
  ×   ⠐⠦  : 점 5, 점 2-3-6    곱셈
  ÷   ⠐⠲  : 점 5, 점 2-5-6    나눗셈
  (   ⠦   : 점 2-3-6          왼쪽 괄호
  )   ⠴   : 점 2-4-5-6        오른쪽 괄호
"""

# ── 외부 라이브러리 불러오기 ────────────────────────────────────────
# (모두 파이썬 기본 내장 라이브러리라서 따로 설치할 필요 없어요)

from __future__ import annotations   # 타입 힌트를 문자열로 쓸 수 있게 해줌 (Python 3.7+ 호환)
from dataclasses import dataclass     # @dataclass 데코레이터: __init__ 등을 자동 생성
from enum import Enum, auto           # Enum: 이름 있는 상수 집합 / auto: 값을 자동 배정
from typing import Optional           # Optional[X] = "X 또는 None"
from abc import ABC, abstractmethod   # ABC: 추상 클래스 / abstractmethod: 반드시 구현해야 하는 메서드


# ══════════════════════════════════════════════════════════════════
# PART 1. LEXER  (문자열 → 토큰 리스트)
#
# ★ "Lexer"란 무엇인가?
#   사람이 문장을 읽을 때 먼저 단어를 인식하듯이,
#   컴퓨터가 수식을 읽을 때 먼저 의미 있는 조각(Token)을 인식하는 역할.
#
# ★ 예시:
#   "12 + 3" 입력
#   → '1','2' 를 묶어서 NUMBER("12") 토큰
#   → ' ' 공백은 무시
#   → '+' 를 PLUS 토큰
#   → ' ' 공백은 무시
#   → '3' 을 NUMBER("3") 토큰
#   → 입력 끝 → EOF 토큰
#   최종: [NUMBER("12"), PLUS("+"), NUMBER("3"), EOF("")]
# ══════════════════════════════════════════════════════════════════

class TokenType(Enum):
    """
    ★ 토큰의 "종류"를 나타내는 열거형(Enum).

    Enum이란? 이름 있는 상수들의 집합.
    예) TokenType.PLUS 는 "이 토큰은 더하기 기호"라는 의미.
    auto()는 1, 2, 3... 숫자를 자동으로 배정해줌 (숫자 값 자체는 중요하지 않음).
    """
    NUMBER  = auto()   # 숫자  예) "0", "42", "100"
    PLUS    = auto()   # 더하기 기호  "+"
    MINUS   = auto()   # 빼기 기호    "-"
    STAR    = auto()   # 곱하기 기호  "*"
    SLASH   = auto()   # 나누기 기호  "/"
    LPAREN  = auto()   # 왼쪽 괄호    "("
    RPAREN  = auto()   # 오른쪽 괄호  ")"
    EOF     = auto()   # 입력의 끝 (End Of File) — 더 읽을 문자가 없음


@dataclass   # 이 데코레이터가 있으면 __init__, __repr__ 등을 자동으로 만들어줌
class Token:
    """
    ★ 하나의 토큰(Token)을 표현하는 데이터 클래스.

    Token은 두 가지 정보를 가짐:
      type  : 이 토큰이 무엇인지 (종류)
      value : 원본 문자열 그대로

    예)
      Token(type=TokenType.NUMBER, value="42")   ← 숫자 42
      Token(type=TokenType.PLUS,   value="+")    ← 더하기
      Token(type=TokenType.EOF,    value="")     ← 입력 끝
    """
    type:  TokenType   # 토큰의 종류
    value: str         # 원본 문자열 값

    def __repr__(self):
        """출력할 때 읽기 쉽게: Token(NUMBER, '42')"""
        return f"Token({self.type.name}, {self.value!r})"


class LexError(Exception):
    """
    Lexer가 처리할 수 없는 문자를 만났을 때 발생하는 오류.
    예) "@", "#" 같이 수식에서 지원하지 않는 문자
    """
    pass


class Lexer:
    """
    ★ LEXER 클래스: LaTeX 문자열을 Token 리스트로 변환

    처리 규칙:
      1. '$' 는 LaTeX 수식 구분자이므로 먼저 제거.
         예) "$3 + 5$" → "3 + 5"
      2. 공백(' ', 탭 등)은 수식에서 의미 없으므로 무시.
      3. 연속된 숫자는 하나의 NUMBER 토큰으로 묶음.
         예) '1', '2', '3' → NUMBER("123")
      4. 알 수 없는 문자는 LexError를 발생.

    사용 예:
      tokens = Lexer("3 + 5").tokenize()
      # → [Token(NUMBER,'3'), Token(PLUS,'+'), Token(NUMBER,'5'), Token(EOF,'')]
    """

    # ── 클래스 변수: 단일 문자 → TokenType 변환 테이블 ─────────────
    # 딕셔너리({}): 키(key)로 값(value)을 빠르게 찾는 자료구조
    _CHAR_MAP: dict[str, TokenType] = {
        "+": TokenType.PLUS,
        "-": TokenType.MINUS,
        "*": TokenType.STAR,
        "/": TokenType.SLASH,
        "(": TokenType.LPAREN,
        ")": TokenType.RPAREN,
    }

    def __init__(self, text: str):
        """
        Lexer를 초기화.
        text: 변환할 LaTeX 수식 문자열
        """
        self.text = text.replace("$", "").strip()  # '$' 제거 후 앞뒤 공백 제거
        self.pos  = 0   # 현재 읽고 있는 위치 (인덱스, 0부터 시작)

    # ── 내부 헬퍼 메서드 (Lexer 내부에서만 사용) ───────────────────

    def _current(self) -> Optional[str]:
        """
        현재 위치의 문자를 반환.
        입력 끝에 도달했으면 None을 반환.

        예) text="abc", pos=1 → 'b' 반환
            text="abc", pos=3 → None 반환 (끝 지남)
        """
        return self.text[self.pos] if self.pos < len(self.text) else None

    def _advance(self):
        """현재 위치를 한 칸 앞으로 이동 (다음 문자로 넘어감)."""
        self.pos += 1

    def _skip_whitespace(self):
        """
        공백 문자들을 모두 건너뜀.
        isspace()는 ' ', '\t', '\n' 등을 공백으로 인식.
        """
        while self._current() and self._current().isspace():
            self._advance()

    def _read_number(self) -> Token:
        """
        현재 위치부터 숫자가 아닌 문자가 나올 때까지 읽어서 NUMBER 토큰 반환.

        예) text="123+4", pos=0 이면
            '1', '2', '3' 읽고 '+' 에서 멈춤
            → Token(NUMBER, "123") 반환
        """
        start = self.pos                          # 숫자 시작 위치 저장
        while self._current() and self._current().isdigit():
            self._advance()                       # 숫자인 동안 계속 전진
        return Token(TokenType.NUMBER, self.text[start:self.pos])  # 시작~현재 범위 잘라냄

    # ── 메인 메서드 ────────────────────────────────────────────────

    def tokenize(self) -> list[Token]:
        """
        ★ 전체 문자열을 읽어서 Token 리스트를 반환하는 메인 메서드.

        반환값: list[Token]
          마지막 원소는 항상 Token(EOF, "") 임.

        사용 예:
          Lexer("3 + 5").tokenize()
          → [Token(NUMBER,'3'), Token(PLUS,'+'), Token(NUMBER,'5'), Token(EOF,'')]
        """
        tokens: list[Token] = []

        while True:  # 무한 루프 (break 또는 return으로 탈출)

            self._skip_whitespace()   # 1. 공백 건너뜀
            ch = self._current()      # 2. 현재 문자 확인

            if ch is None:
                # 3a. 입력 끝 → EOF 토큰 추가하고 루프 종료
                tokens.append(Token(TokenType.EOF, ""))
                break

            elif ch.isdigit():
                # 3b. 숫자 → 연속된 숫자 모두 읽어서 NUMBER 토큰 생성
                tokens.append(self._read_number())

            elif ch in self._CHAR_MAP:
                # 3c. +, -, *, /, (, ) 중 하나 → 바로 토큰으로 변환
                tokens.append(Token(self._CHAR_MAP[ch], ch))
                self._advance()   # 이 문자는 처리했으니 다음으로

            else:
                # 3d. 그 외 문자 → 지원하지 않음, 오류 발생
                raise LexError(
                    f"지원하지 않는 문자: {ch!r}  "
                    f"(위치 {self.pos}/{len(self.text)}, "
                    f"전체 입력: {self.text!r})\n"
                    f"현재 지원: 숫자(0-9), +, -, *, /, (, )"
                )

        return tokens


# ══════════════════════════════════════════════════════════════════
# PART 2. AST 노드  (트리를 구성하는 블록들)
#
# ★ "AST(Abstract Syntax Tree, 추상 구문 트리)"란?
#   수식의 수학적 구조를 나무(Tree) 모양으로 표현한 것.
#   "추상적"이라는 말은 괄호 같은 시각적 표현은 버리고
#   수학적 의미만 담는다는 뜻.
#
# ★ 나무(Tree) 구조란?
#   뿌리(Root)에서 시작해서 가지(Branch)를 통해 잎(Leaf)으로 뻗음.
#   - 잎(Leaf) 노드: 자식이 없는 노드 → NumberNode (숫자)
#   - 가지(Branch) 노드: 자식을 가진 노드 → BinaryOpNode, GroupNode
#
# ★ 예시: "2 + 3 * 4" 의 AST
#
#          BinaryOpNode(op="+")    ← 루트 (뿌리): + 는 우선순위가 낮아서
#          │                                       마지막에 계산됨
#          ├─[L] NumberNode("2")   ← 잎: 숫자 2
#          │
#          └─[R] BinaryOpNode(op="*")  ← 가지: * 는 우선순위 높아서 먼저
#                │
#                ├─[L] NumberNode("3")  ← 잎: 숫자 3
#                └─[R] NumberNode("4")  ← 잎: 숫자 4
#
# ★ 노드의 종류:
#   NumberNode   : 숫자 하나 (잎)
#   BinaryOpNode : 연산자 + 왼쪽 피연산자 + 오른쪽 피연산자 (가지)
#   GroupNode    : 괄호로 묶인 식 (가지)
#
# ★ accept(visitor) 메서드:
#   Visitor 패턴의 핵심. 각 노드가 "나 이런 타입이야, 그에 맞게 처리해"라고
#   Visitor에게 알려주는 역할. (PART 4에서 자세히 설명)
# ══════════════════════════════════════════════════════════════════

@dataclass
class NumberNode:
    """
    ★ 숫자 리터럴 노드 (잎 노드)

    트리에서 더 이상 쪼개지지 않는 가장 기본 단위.
    자식 노드가 없음.

    예) "42" → NumberNode(value="42")
        "0"  → NumberNode(value="0")

    나중에 확장할 때:
      DecimalNode (소수점 숫자) 추가 → NumberNode를 참고해서 만들면 됨
    """
    value: str   # 숫자 문자열 그대로 저장 (예: "0", "42", "100")

    def __repr__(self):
        return f"NumberNode({self.value})"

    def accept(self, visitor: "NodeVisitor"):
        """
        ★ Visitor를 받아들이는 메서드 (Visitor 패턴 핵심)

        "나는 NumberNode야"를 Visitor에게 알리고,
        Visitor의 visit_number(self) 메서드를 호출.

        이렇게 하면 Visitor는 노드 타입을 isinstance()로 매번 확인하지 않아도 됨.
        노드가 직접 "내 타입에 맞는 메서드를 호출해줘"라고 말하는 방식.
        """
        return visitor.visit_number(self)


@dataclass
class BinaryOpNode:
    """
    ★ 이항 연산 노드 (가지 노드)

    피연산자가 2개(왼쪽, 오른쪽)인 연산을 표현.
    +, -, *, / 연산이 여기에 해당.

    예) "3 + 5"   → BinaryOpNode(op="+", left=NumberNode("3"), right=NumberNode("5"))
        "2 * 4"   → BinaryOpNode(op="*", left=NumberNode("2"), right=NumberNode("4"))
        "10 / 2"  → BinaryOpNode(op="/", left=NumberNode("10"), right=NumberNode("2"))

    나중에 확장할 때:
      \frac → BinaryOpNode(op="frac", left=분자노드, right=분모노드) 처럼 활용 가능
    """
    op:    str     # 연산자 문자: "+", "-", "*", "/"
    left:  object  # 왼쪽 피연산자 (NumberNode, BinaryOpNode, GroupNode 모두 가능)
    right: object  # 오른쪽 피연산자 (마찬가지)

    def __repr__(self):
        return f"BinaryOpNode({self.op!r}, {self.left!r}, {self.right!r})"

    def accept(self, visitor: "NodeVisitor"):
        """visit_binary_op(self) 호출"""
        return visitor.visit_binary_op(self)


@dataclass
class GroupNode:
    """
    ★ 괄호 그룹 노드 (가지 노드)

    수학적으로는 괄호 안의 식과 동일하지만,
    점자로 변환할 때 괄호 기호(⠦ ⠴)를 붙여야 하므로 별도 노드로 관리.

    예) "(3 + 5)" → GroupNode(expr=BinaryOpNode("+", NumberNode("3"), NumberNode("5")))

    ★ 이 노드가 나중에 어떻게 활용될 수 있나?
      - \frac{분자}{분모}: 분자와 분모 각각을 GroupNode로 처리
      - \sqrt{내용}: 근호 안을 GroupNode로 처리
      이런 식으로 재활용 가능!
    """
    expr: object   # 괄호 안의 수식 (모든 노드 타입 가능)

    def __repr__(self):
        return f"GroupNode({self.expr!r})"

    def accept(self, visitor: "NodeVisitor"):
        """visit_group(self) 호출"""
        return visitor.visit_group(self)


# ══════════════════════════════════════════════════════════════════
# PART 3. PARSER  (토큰 리스트 → AST 트리)
#
# ★ "Parser"란?
#   Lexer가 만든 Token 리스트를 문법 규칙에 따라 AST 트리로 조립하는 역할.
#   사람으로 치면 "단어들을 읽어서 문장 구조를 파악하는" 역할.
#
# ★ "Recursive Descent(재귀 하강)" 방식:
#   함수가 서로를 호출하는 방식으로 파싱.
#   우선순위를 함수 호출 계층으로 표현 → 코드가 문법과 1:1 대응됨.
#
# ★ 연산자 우선순위를 함수 계층으로 표현하는 방법:
#
#   [규칙] "낮은 우선순위 함수가 높은 우선순위 함수를 호출한다"
#
#   parse_expr()    +, -  처리   (우선순위 낮음)  ← 가장 먼저 호출됨
#     └─ parse_term()   *, /  처리   (우선순위 높음)
#          └─ parse_factor()  숫자,(괄호) 처리 (우선순위 최고) ← 가장 나중에 호출됨
#
#   예) "2 + 3 * 4" 파싱 과정:
#     parse_expr() 시작
#       parse_term() 호출 → parse_factor() → 숫자 2 반환
#       (term 레벨에서 *가 없으므로) 2를 반환
#     '+' 발견 → 오른쪽을 위해 parse_term() 다시 호출
#       parse_factor() → 숫자 3 반환
#       '*' 발견 → parse_factor() → 숫자 4 반환
#       BinaryOpNode(*, 3, 4) 반환  ← 곱셈이 먼저 묶임!
#     BinaryOpNode(+, 2, BinaryOpNode(*, 3, 4)) 반환
#
# ★ 문법 (BNF 표기법으로 정리):
#   expr   → term   ( ('+' | '-') term   )*
#   term   → factor ( ('*' | '/') factor )*
#   factor → NUMBER
#           | '(' expr ')'
#
#   읽는 법:
#   → : "다음과 같이 구성된다"
#   ( ... )* : "0번 이상 반복"
#   '|' : "또는"
# ══════════════════════════════════════════════════════════════════

class ParseError(Exception):
    """
    Parser가 문법 오류를 만났을 때 발생하는 오류.
    예) 괄호가 닫히지 않음, 연산자 뒤에 숫자가 없음 등
    """
    pass


class Parser:
    """
    ★ PARSER 클래스: Token 리스트를 AST로 변환

    사용 예:
      tokens = Lexer("3 + 5").tokenize()
      ast    = Parser(tokens).parse()
    """

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens   # Lexer가 만들어준 Token 리스트
        self.pos    = 0        # 현재 읽고 있는 Token 위치 (0부터 시작)

    # ── 내부 헬퍼 메서드 ────────────────────────────────────────────

    def _current(self) -> Token:
        """현재 위치의 Token을 반환 (소비하지 않고 그냥 봄)."""
        return self.tokens[self.pos]

    def _peek_type(self) -> TokenType:
        """현재 Token의 타입만 확인 (소비 없이). 조건 분기에 자주 사용."""
        return self.tokens[self.pos].type

    def _eat(self, expected: TokenType) -> Token:
        """
        현재 Token이 expected 타입인지 확인하고, 맞으면 소비(다음으로 이동).
        타입이 다르면 ParseError 발생.

        '먹는다(eat)'는 표현 = "이 토큰을 처리하고 넘어간다"는 파싱 용어.

        예) _eat(TokenType.LPAREN)
            → 현재 토큰이 '('이면 소비하고 반환
            → 다른 토큰이면 에러: "괄호를 기대했는데 다른 게 왔어!"
        """
        tok = self._current()
        if tok.type != expected:
            raise ParseError(
                f"문법 오류!\n"
                f"  기대한 토큰: {expected.name}\n"
                f"  실제 토큰:   {tok.type.name} ({tok.value!r})\n"
                f"  힌트: 수식을 다시 확인해주세요."
            )
        self.pos += 1   # 소비: 다음 토큰으로 이동
        return tok

    def _advance(self) -> Token:
        """
        현재 Token을 소비하고 반환 (타입 확인 없이).
        _eat과 달리 타입 검사를 하지 않음.
        이미 타입을 확인한 상황(while 조건에서 확인 등)에서 사용.
        """
        tok = self._current()
        self.pos += 1
        return tok

    # ── 문법 규칙 메서드 (핵심!) ────────────────────────────────────

    def parse(self) -> object:
        """
        ★ 파싱의 진입점 (가장 먼저 호출하는 메서드)

        전체 수식을 파싱하고, 마지막에 EOF 토큰이 있는지 확인.
        EOF가 없으면 수식이 완전히 파싱되지 않은 것 → 에러.

        사용:
          ast = Parser(tokens).parse()
        """
        tree = self.parse_expr()    # 수식 파싱 시작 (덧셈/뺄셈 레벨부터)
        self._eat(TokenType.EOF)    # 모든 토큰을 소비했는지 확인
        return tree

    def parse_expr(self) -> object:
        """
        ★ 덧셈/뺄셈 처리 (우선순위: 낮음)

        문법: expr → term ( ('+' | '-') term )*

        동작 방식:
          1. 먼저 parse_term()으로 왼쪽 피연산자를 파싱
          2. '+' 또는 '-'가 오는 동안 반복:
             a. 연산자 소비
             b. parse_term()으로 오른쪽 피연산자 파싱
             c. BinaryOpNode 생성
          3. 결과 반환

        ★ 좌결합(Left-associative)이란?
          "1 + 2 + 3"을 "(1 + 2) + 3"으로 파싱하는 것.
          while 루프 덕분에 자연스럽게 좌결합이 됨.
          (오른쪽에서 쌓이는 게 아니라 왼쪽부터 차례로 묶임)
        """
        node = self.parse_term()   # 먼저 */를 처리하는 parse_term 호출

        # +나 -가 계속 오는 동안 반복해서 왼쪽부터 묶어나감
        while self._peek_type() in (TokenType.PLUS, TokenType.MINUS):
            op_tok = self._advance()         # '+' 또는 '-' 토큰 소비
            right  = self.parse_term()       # 오른쪽 피연산자 파싱
            # 지금까지 만든 node를 왼쪽에 두고, 새 오른쪽을 붙여서 새 노드 생성
            node   = BinaryOpNode(op=op_tok.value, left=node, right=right)

        return node

    def parse_term(self) -> object:
        """
        ★ 곱셈/나눗셈 처리 (우선순위: 높음)

        문법: term → factor ( ('*' | '/') factor )*

        parse_expr보다 먼저 (더 깊이) 호출되기 때문에
        같은 수식에서 *, / 가 +, - 보다 먼저 묶이게 됨.
        → 이것이 연산자 우선순위 구현의 핵심!

        예) "2 + 3 * 4" 에서
          parse_expr이 parse_term을 호출 → 3 * 4가 먼저 묶임
          그 결과를 가지고 parse_expr이 2 + (3*4) 를 만듦
        """
        node = self.parse_factor()   # 가장 높은 우선순위인 parse_factor 호출

        while self._peek_type() in (TokenType.STAR, TokenType.SLASH):
            op_tok = self._advance()
            right  = self.parse_factor()
            node   = BinaryOpNode(op=op_tok.value, left=node, right=right)

        return node

    def parse_factor(self) -> object:
        """
        ★ 숫자와 괄호 처리 (우선순위: 최고)

        문법: factor → NUMBER
                      | '(' expr ')'

        두 가지 경우:
          1. 숫자 → NumberNode 생성하고 반환 (가장 단순한 경우)
          2. '(' → 괄호 안의 수식을 parse_expr부터 다시 파싱 (재귀!)
             이때 괄호 안은 우선순위가 초기화되므로
             (2+3)*4 에서 2+3이 먼저 계산되는 효과를 냄.

        ★ 재귀(Recursion)란?
          함수가 자기 자신을 다시 호출하는 것.
          parse_factor 안에서 parse_expr를 호출하고,
          parse_expr는 다시 parse_factor를 호출하는 구조.
          괄호가 중첩될수록 더 깊이 재귀가 일어남.
        """
        tok = self._current()   # 현재 토큰을 봄 (소비 안 함)

        if tok.type == TokenType.NUMBER:
            # 숫자 → NumberNode 생성
            self._advance()                  # 숫자 토큰 소비
            return NumberNode(value=tok.value)

        elif tok.type == TokenType.LPAREN:
            # '(' → 괄호 안 내용을 파싱하고 GroupNode로 감쌈
            self._eat(TokenType.LPAREN)      # '(' 소비 (없으면 에러)
            inner = self.parse_expr()        # ★ 재귀: 괄호 안을 처음부터 파싱
            self._eat(TokenType.RPAREN)      # ')' 소비 (없으면 에러 — 괄호 안 닫힘)
            return GroupNode(expr=inner)

        else:
            # 숫자도 '('도 아닌 것이 왔음 → 수식 문법 오류
            raise ParseError(
                f"문법 오류!\n"
                f"  숫자(NUMBER) 또는 '('를 기대했지만,\n"
                f"  {tok.type.name}({tok.value!r})이 왔습니다.\n"
                f"  힌트: 연산자(+,-,*,/) 앞뒤에 숫자가 있는지 확인하세요."
            )


# ══════════════════════════════════════════════════════════════════
# PART 4. VISITOR 패턴
#
# ★ "Visitor 패턴"이란?
#   트리 구조(AST)는 건드리지 않고,
#   "트리에서 무엇을 할 것인가"를 별도 클래스(Visitor)에 담는 설계 방식.
#
# ★ 왜 Visitor 패턴을 쓰는가? (v2 AST vs v3 Visitor 비교)
#
#   v2 방식 (함수 하나에 모든 로직):
#     def to_braille(node):
#         if isinstance(node, NumberNode): ...점자 변환...
#         elif isinstance(node, BinaryOpNode): ...점자 변환...
#     → 나중에 MathML 변환도 하고 싶다면? to_mathml() 함수를 새로 만들어야 함.
#       코드가 늘어날수록 각 함수마다 모든 노드 타입을 처리해야 해서 복잡해짐.
#
#   v3 방식 (Visitor 패턴):
#     class BrailleVisitor:
#         def visit_number(node): ...점자 변환...
#         def visit_binary_op(node): ...점자 변환...
#
#     class MathMLVisitor:    ← 새로운 변환이 필요하면 클래스만 추가!
#         def visit_number(node): ...MathML 변환...
#         def visit_binary_op(node): ...MathML 변환...
#     → AST 코드(NumberNode, BinaryOpNode 등)는 전혀 건드릴 필요 없음!
#
# ★ 동작 원리 (Double Dispatch):
#
#   보통: visitor.visit(node) → visitor가 node 타입을 isinstance로 확인
#   Visitor 패턴: node.accept(visitor) → node가 자신의 타입에 맞는 메서드 호출
#
#   예) NumberNode가 accept(visitor) 호출:
#     → visitor.visit_number(self) 호출
#     → Visitor는 NumberNode임을 이미 알고 처리
#
#   이를 "Double Dispatch(이중 디스패치)"라고 부름:
#     1차 dispatch: node.accept(visitor) 호출 (어떤 노드인지)
#     2차 dispatch: visitor.visit_number() 호출 (어떤 Visitor인지)
# ══════════════════════════════════════════════════════════════════

class NodeVisitor(ABC):
    """
    ★ 모든 Visitor의 부모 클래스 (추상 클래스)

    ABC = Abstract Base Class (추상 기반 클래스)
      → "이 클래스 자체로는 사용 못 하고, 반드시 상속받아서 써야 해"를 의미.

    @abstractmethod = "이 메서드는 자식 클래스에서 반드시 구현해야 함"
      → 구현 안 하면 파이썬이 에러를 내줌. 실수를 방지하는 안전장치.

    새로운 Visitor를 만들고 싶으면:
      1. NodeVisitor를 상속받음 (class MyVisitor(NodeVisitor):)
      2. 아래 3개 메서드를 구현

    예) 나중에 MathML Visitor를 만들고 싶다면:
      class MathMLVisitor(NodeVisitor):
          def visit_number(self, node): return f"<mn>{node.value}</mn>"
          def visit_binary_op(self, node): ...
          def visit_group(self, node): ...
    """

    @abstractmethod
    def visit_number(self, node: NumberNode):
        """NumberNode를 방문했을 때 실행할 로직 (반드시 구현)"""
        pass

    @abstractmethod
    def visit_binary_op(self, node: BinaryOpNode):
        """BinaryOpNode를 방문했을 때 실행할 로직 (반드시 구현)"""
        pass

    @abstractmethod
    def visit_group(self, node: GroupNode):
        """GroupNode를 방문했을 때 실행할 로직 (반드시 구현)"""
        pass


class BrailleVisitor(NodeVisitor):
    """
    ★ 한국 점자 변환 Visitor
    NodeVisitor를 상속받아 한국 수학 점자(KS X 1107)로 변환하는 클래스.

    ★ 수표(⠼) 처리 전략:
      수표는 "숫자 블록이 새로 시작할 때" 붙여야 함.
      예) "3 + 5" → ⠼⠉ + ⠼⠑  (각 숫자마다 수표)
          "13"   → ⠼⠁⠉        (연속 숫자는 수표 하나만)

      이를 위해 need_indicator 플래그를 사용:
        True  = "지금 만나는 첫 숫자에 수표를 붙여야 함"
        False = "이미 수표가 붙었으니 붙이지 않아도 됨"

      - 수식 시작: True (첫 숫자에 수표 필요)
      - 연산자 다음: True (새 숫자 블록 시작)
      - 괄호 안 시작: True (새 숫자 블록 시작)
    """

    # ── 점자 변환 테이블 (KS X 1107 기준) ──────────────────────────

    NUMBER_INDICATOR = "⠼"   # 수표: 점 3-4-5-6, 숫자 블록 앞에 붙임

    DIGIT_MAP: dict[str, str] = {
        # 숫자 → 점자 (점 번호는 점자 배치상의 위치)
        "0": "⠚",   # 점 2-4-5
        "1": "⠁",   # 점 1
        "2": "⠃",   # 점 1-2
        "3": "⠉",   # 점 1-4
        "4": "⠙",   # 점 1-4-5
        "5": "⠑",   # 점 1-5
        "6": "⠋",   # 점 1-2-4
        "7": "⠛",   # 점 1-2-4-5
        "8": "⠓",   # 점 1-2-5
        "9": "⠊",   # 점 2-4
    }

    OP_MAP: dict[str, str] = {
        # 연산자 → 점자 (KS X 1107)
        "+": "⠢",   # 덧셈:  점 26
        "-": "⠔",   # 뺄셈:  점 35
        "*": "⠡",   # 곱셈:  점 16
        "/": "⠌⠌",   # 나눗셈: 점 34, 점 34
    }

    LPAREN_BRAILLE = "⠦"   # 왼쪽 괄호: 점 2-3-6
    RPAREN_BRAILLE = "⠴"   # 오른쪽 괄호: 점 2-4-5-6

    # ── 변환 시작점 ─────────────────────────────────────────────────

    def convert(self, node: object) -> str:
        """
        ★ 변환의 진입점. 루트 노드에 이 메서드를 호출하면 됩니다.

        need_indicator=True로 시작 → 수식의 첫 숫자에 수표가 붙음.

        사용:
          result = BrailleVisitor().convert(ast)
        """
        return self._visit(node, need_indicator=True)

    def _visit(self, node: object, need_indicator: bool) -> str:
        """
        ★ 내부 재귀 변환 메서드.

        need_indicator 값을 들고 노드를 방문.
        직접 호출하는 것보다 convert()를 통해 사용하는 것을 권장.

        need_indicator:
          True  → 이 노드(또는 하위 첫 번째 숫자)에 수표 필요
          False → 수표 불필요 (이미 붙었거나 숫자 블록 내부)
        """
        # 현재 need_indicator를 담은 임시 Visitor를 만들어 accept에 전달
        return node.accept(_ContextVisitor(self, need_indicator))

    # ── NodeVisitor 추상 메서드 구현 ────────────────────────────────
    # 아래는 단독 호출 시 기본 동작 (need_indicator=True 기본값 사용)
    # 실제 변환 로직은 _ContextVisitor에 있음

    def visit_number(self, node: NumberNode) -> str:
        return self._number_to_braille(node.value, with_indicator=True)

    def visit_binary_op(self, node: BinaryOpNode) -> str:
        left  = self._visit(node.left,  need_indicator=True)
        op    = self.OP_MAP[node.op]
        right = self._visit(node.right, need_indicator=True)
        return left + op + right

    def visit_group(self, node: GroupNode) -> str:
        inner = self._visit(node.expr, need_indicator=True)
        return self.LPAREN_BRAILLE + inner + self.RPAREN_BRAILLE

    # ── 점자 변환 헬퍼 ──────────────────────────────────────────────

    def _number_to_braille(self, num_str: str, with_indicator: bool) -> str:
        """
        숫자 문자열을 점자로 변환.

        예)
          "42", with_indicator=True  → "⠼⠙⠃"  (수표⠼ + 4⠙ + 2⠃)
          "42", with_indicator=False → "⠙⠃"    (수표 없이 4⠙ + 2⠃)
        """
        indicator = self.NUMBER_INDICATOR if with_indicator else ""
        # DIGIT_MAP에서 각 숫자 문자를 점자로 변환하고 이어 붙임
        digits    = "".join(self.DIGIT_MAP[d] for d in num_str)
        return indicator + digits


class _ContextVisitor(NodeVisitor):
    """
    ★ 컨텍스트(need_indicator) 정보를 담은 내부 Visitor.

    BrailleVisitor가 재귀 호출할 때 need_indicator 값을 전달하기 위한
    헬퍼 클래스. 외부에서 직접 사용할 필요 없음.

    이름 앞의 _ (언더스코어) = "이 클래스는 내부 구현용이라 외부에서 쓰지 마세요"
    라는 파이썬 관례.
    """

    def __init__(self, parent: BrailleVisitor, need_indicator: bool):
        self.parent         = parent          # 실제 변환 로직이 있는 BrailleVisitor
        self.need_indicator = need_indicator  # 이 컨텍스트에서 수표 필요 여부

    def visit_number(self, node: NumberNode) -> str:
        """
        숫자 노드 방문.
        need_indicator에 따라 수표를 붙이거나 붙이지 않음.
        """
        return self.parent._number_to_braille(
            node.value,
            with_indicator=self.need_indicator
        )

    def visit_binary_op(self, node: BinaryOpNode) -> str:
        """
        이항 연산 노드 방문.

        ★ 수표 전달 규칙:
          왼쪽 피연산자:
            → 현재 need_indicator 그대로 전달
            → 수식 시작이면 True (수표 붙임), 아니면 False

          오른쪽 피연산자:
            → 항상 need_indicator=True
            → 연산자 다음엔 항상 새 숫자 블록이 시작되므로

          예) "3 + 5"에서
            왼쪽 3: need_indicator=True  → ⠼⠉ (수표 포함)
            오른쪽 5: need_indicator=True → ⠼⠑ (수표 포함)
            결과: ⠼⠉⠐⠖⠼⠑
        """
        left  = self.parent._visit(node.left,  need_indicator=self.need_indicator)
        op    = self.parent.OP_MAP[node.op]
        right = self.parent._visit(node.right, need_indicator=True)  # 항상 True!
        return left + op + right

    def visit_group(self, node: GroupNode) -> str:
        """
        괄호 그룹 노드 방문.
        괄호 기호(⠦ ⠴)로 감싸고, 괄호 안 첫 숫자에도 수표를 붙임.

        예) "(3 + 5)"
          → ⠦ (왼쪽 괄호) + ⠼⠉⠐⠖⠼⠑ (3+5 점자) + ⠴ (오른쪽 괄호)
          → "⠦⠼⠉⠐⠖⠼⠑⠴"
        """
        inner = self.parent._visit(node.expr, need_indicator=True)  # 괄호 안도 수표 필요
        return self.parent.LPAREN_BRAILLE + inner + self.parent.RPAREN_BRAILLE


class DebugVisitor(NodeVisitor):
    """
    ★ 디버그용 Visitor (개발할 때 유용!)

    AST를 사람이 읽기 쉬운 수식 문자열로 재구성.
    점자 결과가 이상할 때 AST 구조가 올바른지 확인하는 용도.

    BrailleVisitor와 완전히 독립적 — Visitor 패턴 덕분에
    AST 코드 수정 없이 새로운 기능 추가가 얼마나 쉬운지 보여주는 예시.

    예) BinaryOpNode(+, NumberNode(2), BinaryOpNode(*, 3, 4))
        → "(2 + (3 * 4))"  ← 우선순위 구조가 괄호로 명확히 보임
    """

    def visit_number(self, node: NumberNode) -> str:
        """숫자 노드 → 숫자 문자열 그대로 반환"""
        return node.value

    def visit_binary_op(self, node: BinaryOpNode) -> str:
        """이항 연산 노드 → (왼쪽 op 오른쪽) 형태로 반환. 괄호로 구조 명시."""
        left  = node.left.accept(self)
        right = node.right.accept(self)
        return f"({left} {node.op} {right})"   # 모든 연산을 괄호로 감싸서 구조 명확히

    def visit_group(self, node: GroupNode) -> str:
        """괄호 그룹 노드 → [내용] 형태 (일반 괄호 ()와 구분하기 위해 [] 사용)"""
        inner = node.expr.accept(self)
        return f"[{inner}]"


# ══════════════════════════════════════════════════════════════════
# PART 5. 전체 파이프라인 편의 함수
# ══════════════════════════════════════════════════════════════════

def latex_to_korean_braille(latex: str) -> str:
    """
    ★ 메인 변환 함수: LaTeX 문자열 → 한국 점자 문자열

    Lexer → Parser → BrailleVisitor 를 내부적으로 순서대로 실행.
    이 함수 하나만 호출하면 모든 변환이 완료됨.

    Args:
      latex (str): LaTeX 수식 문자열.
                   '$' 기호를 포함해도 됨 (자동 제거).

    Returns:
      str: 한국 수학 점자 유니코드 문자열.

    Raises:
      LexError:   지원하지 않는 문자가 있을 때
      ParseError: 수식 문법이 올바르지 않을 때

    사용 예:
      latex_to_korean_braille("3 + 5")        → "⠼⠉⠐⠖⠼⠑"
      latex_to_korean_braille("(2+3)*4")      → "⠦⠼⠃⠐⠖⠼⠉⠴⠐⠦⠼⠙"
      latex_to_korean_braille("$7 - 3 + 1$")  → "⠼⠛⠐⠤⠼⠉⠐⠖⠼⠁"
    """
    # ① 문자열 → Token 리스트
    tokens = Lexer(latex).tokenize()

    # ② Token 리스트 → AST 트리
    ast = Parser(tokens).parse()

    # ③ AST 트리 → 한국 점자 문자열
    visitor = BrailleVisitor()
    return visitor.convert(ast)


# ══════════════════════════════════════════════════════════════════
# PART 6. AST 시각화 헬퍼 (개발용)
# ══════════════════════════════════════════════════════════════════

def print_ast(node: object, indent: int = 0, label: str = ""):
    """
    ★ AST를 터미널에 나무(Tree) 형태로 출력하는 디버그 함수.

    결과가 이상할 때 AST 구조를 육안으로 확인하는 용도.

    Args:
      node   : 출력할 AST 노드 (루트 노드를 넘기면 트리 전체 출력)
      indent : 들여쓰기 깊이 (0부터 시작, 재귀 호출 시 자동 증가)
      label  : 이 노드의 역할 표시 ("L"=왼쪽, "R"=오른쪽, "inner"=괄호 안)

    출력 예시:
      BinaryOpNode(op='+')
        [L] NumberNode(2)
        [R] BinaryOpNode(op='*')
          [L] NumberNode(3)
          [R] NumberNode(4)
    """
    prefix = "  " * indent                    # 들여쓰기: 깊이 × 2칸
    tag    = f"[{label}] " if label else ""   # "L", "R", "inner" 라벨

    if isinstance(node, NumberNode):
        print(f"{prefix}{tag}NumberNode({node.value})")

    elif isinstance(node, BinaryOpNode):
        print(f"{prefix}{tag}BinaryOpNode(op={node.op!r})")
        print_ast(node.left,  indent + 1, "L")      # 왼쪽 자식 (들여쓰기 +1)
        print_ast(node.right, indent + 1, "R")      # 오른쪽 자식

    elif isinstance(node, GroupNode):
        print(f"{prefix}{tag}GroupNode  ← 괄호 묶음")
        print_ast(node.expr, indent + 1, "inner")   # 괄호 안 내용


# ══════════════════════════════════════════════════════════════════
# PART 7. 데모 실행
#
# 이 파일을 직접 실행하면 (python latex_to_korean_braille.py)
# 아래 테스트 케이스들이 실행됩니다.
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    debug_visitor = DebugVisitor()   # 수식 구조 확인용

    test_cases = [
        # (입력 수식,                설명)
        ("42",                  "단순 숫자"),
        ("3 + 5",               "덧셈"),
        ("10 - 2",              "뺄셈"),
        ("6 * 7",               "곱셈"),
        ("8 / 4",               "나눗셈"),
        ("2 + 3 * 4",           "★ 우선순위: 곱셈 먼저 → 2+(3*4)"),
        ("10 - 6 / 2",          "★ 우선순위: 나눗셈 먼저 → 10-(6/2)"),
        ("(2 + 3) * 4",         "★ 괄호로 우선순위 변경"),
        ("2 * (3 + 4)",         "오른쪽 괄호"),
        ("(1 + 2) * (3 + 4)",   "양쪽 괄호"),
        ("(10 - 2) / (2 + 2)",  "나눗셈과 괄호"),
        ("$7 - 3 + 1$",         "LaTeX $ 포함"),
    ]

    for latex, desc in test_cases:
        print(f"\n{'━'*64}")
        print(f"  [{desc}]")
        print(f"  입력     : {latex!r}")

        # ① 토큰 목록 출력
        tokens = Lexer(latex).tokenize()
        print(f"  토큰     : {tokens}")

        # ② AST 트리 출력
        ast = Parser(tokens).parse()
        print("  AST 트리 :")
        print_ast(ast, indent=4)

        # ③ DebugVisitor: 수식 구조를 읽기 쉽게 재구성
        debug_str = ast.accept(debug_visitor)
        print(f"  수식구조  : {debug_str}  ← 괄호로 우선순위 확인 가능")

        # ④ BrailleVisitor: 최종 점자 변환
        braille = BrailleVisitor().convert(ast)
        print(f"  점자     : {braille}")
