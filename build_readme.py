#!/usr/bin/env python3
"""Собирает README.md (страницу-каталог) из catalog.json.

Группирует инструменты по категориям (в порядке из catalog.json), внутри —
по звёздам. ⭐ помечает то, чем пользуемся сами. Запускается автоматически
после add.py, либо вручную: python3 build_readme.py
"""
import os
import json

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "catalog.json")
README = os.path.join(HERE, "README.md")


def _stars(n):
    """12345 → '12.3k', 980 → '980'."""
    if not n:
        return ""
    if n >= 1000:
        return f"{n/1000:.1f}k".replace(".0k", "k")
    return str(n)


def _anchor(name):
    """GitHub-якорь из заголовка: нижний регистр, не-буквы/цифры → дефис."""
    a = name.lower()
    out = []
    for ch in a:
        if ch.isalnum():
            out.append(ch)
        elif ch in " -_":
            out.append("-")
        # эмодзи и пунктуацию выкидываем
    return "".join(out).strip("-")


def build():
    with open(CATALOG, encoding="utf-8") as f:
        data = json.load(f)

    tools = data.get("tools", [])
    cats = data.get("categories", [])
    by_cat = {c["key"]: [] for c in cats}
    for t in tools:
        by_cat.setdefault(t.get("category", "other"), []).append(t)

    total = len(tools)
    mine = sum(1 for t in tools if t.get("audience") == "me")

    L = []
    L.append(f"# 🟢 {data['title']}")
    L.append("")
    L.append(f"> {data['subtitle']}")
    L.append(f">")
    L.append(f"> Канал: **[Дроп IT]({data['channel']})** · в каталоге **{total}** инструментов · ⭐ — чем пользуемся сами")
    L.append("")

    # оглавление — только непустые категории
    toc = []
    for c in cats:
        items = by_cat.get(c["key"], [])
        if items:
            toc.append(f"[{c['name']}](#{_anchor(c['name'])})")
    if toc:
        L.append("**Разделы:** " + " · ".join(toc))
        L.append("")
    L.append("---")
    L.append("")

    for c in cats:
        items = by_cat.get(c["key"], [])
        if not items:
            continue
        items.sort(key=lambda t: t.get("stars", 0), reverse=True)
        L.append(f"## {c['name']}")
        L.append("")
        for t in items:
            star = " ⭐" if t.get("audience") == "me" else ""
            meta = []
            if t.get("lang"):
                meta.append(f"`{t['lang']}`")
            s = _stars(t.get("stars", 0))
            if s:
                meta.append(f"★ {s}")
            tail = (" · " + " · ".join(meta)) if meta else ""
            desc = t.get("desc_ru") or "_описание скоро_"
            L.append(f"- **[{t['name']}]({t['url']})**{star} — {desc}{tail}")
        L.append("")

    L.append("---")
    L.append("")
    L.append("### Нашёл крутой инструмент?")
    L.append(f"Кинь ссылку в [Дроп IT]({data['channel']}) — лучшее проверим и добавим сюда.")
    L.append("")
    L.append("_Каталог ведётся вручную и пополняется из новостей канала. Без рекламы — только то, что реально полезно._")
    L.append("")

    with open(README, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"📄 README собран: {total} инструментов в {sum(1 for c in cats if by_cat.get(c['key']))} разделах ({mine} ⭐ своих).")


if __name__ == "__main__":
    build()
