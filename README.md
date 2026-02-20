[🇰🇷 한국어](./README.ko.md) | 🇺🇸 English

# kmathbraille ⠿

> Standard Python library for translating LaTeX math expressions
> into Korean Braille  
> (as specified in the Ministry of Culture, Sports and Tourism Notice No. 2024-5.)  

by [Qualia Bridge](https://www.linkedin.com/in/boram0905)

---

## ✨ Why kmathbraille?

In Korea, visually impaired students often cannot access
math education in Braille.
Existing tools lack accuracy, transparency, and extensibility.

kmathbraille is built by someone who sits at a rare intersection:

- 📖 Braille specialist  
- 📊 Statistics & Data Science M.S.  
- 📈 Data visualization developer  

---

## 🚧 Status

Currently in active development (stealth mode).
Star this repo to follow along!

### Roadmap
- [x] v0.1 — Basic arithmetic (+, -, *, /) & parentheses
- [x] v0.2 — Fractions (`\frac`) & mixed numbers
- [x] v0.3 — Exponents & subscripts (`^`, `_`)
- [x] v0.4 — Square roots (`\sqrt`)
- [x] v0.5 — Trigonometric functions
- [x] v1.0 — PyPI release 🚀
- [ ] v1.1 — Full validation of Alphabetic Braille using in Korea
- [ ] v2.0 — To be continued
- [ ] v3.0 — To be continued

---

## 📦 Installation

You can install it via your terminal using the following command:  

```bash
pip install kmathbraille
```

After installation, you can use it in your Python code as follows:  

```python
from kmathbraille import to_braille as tb

print(tb(r"\frac{1}{2}"))  # Output: ⠼⠃⠌⠼⠁ (Fractions)
print(tb(r"x^{2}"))        # Output: ⠭⠘⠼⠃ (Exponents & subscripts)
print(tb(r"\sqrt{2}"))     # Output: ⠜⠼⠃ (Square roots)
print(tb(r"\sin{x}"))      # Output: ⠖⠎⠭ (Trigonometric functions)
```

---

## 🤝 Contributing

Contributions welcome!
Especially from Braille specialists and math educators.

---

## 📄 License

MIT License © 2026 Qualia Bridge
