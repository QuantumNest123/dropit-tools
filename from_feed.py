#!/usr/bin/env python3
"""Кандидаты в каталог из ленты tg-feed.

Идея: tg-feed каждый день сваливает в incoming.md/processed.md посты из каналов,
где часто мелькают GitHub-репозитории. Этот скрипт достаёт оттуда все ссылки на
репозитории, выкидывает уже добавленные, и печатает список «вот что можно добавить».
Ничего не качает и не меняет — только показывает. Дальше ты сам решаешь и зовёшь add.py.

  python3 from_feed.py            # показать кандидатов
  python3 from_feed.py --cmds     # сразу готовые команды add.py для копипаста
"""
import os
import re
import json
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "catalog.json")
# tg-feed лежит рядом в Cours/tools/tg-feed
FEED_DIR = os.path.abspath(os.path.join(HERE, "..", "tools", "tg-feed"))

# мусорные «репо», которые на деле не инструменты
SKIP = {"sponsors", "topics", "features", "about", "pricing", "marketplace",
        "settings", "login", "join", "apps", "collections", "trending"}


def _known_urls():
    try:
        d = json.load(open(CATALOG, encoding="utf-8"))
        return {t["url"].rstrip("/").lower() for t in d.get("tools", [])}
    except Exception:
        return set()


def _scan(text):
    """Все github.com/owner/repo из текста → нормализованные ссылки (owner/repo)."""
    found = {}
    for m in re.finditer(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", text):
        owner, repo = m.group(1), m.group(2)
        repo = re.sub(r"[.,);:]+$", "", re.sub(r"\.git$", "", repo))
        if owner.lower() in SKIP or repo.lower() in SKIP:
            continue
        found[f"{owner}/{repo}".lower()] = f"https://github.com/{owner}/{repo}"
    return found


def main():
    ap = argparse.ArgumentParser(description="Кандидаты в каталог из ленты tg-feed.")
    ap.add_argument("--cmds", action="store_true", help="печатать готовые команды add.py")
    args = ap.parse_args()

    text = ""
    for fn in ("incoming.md", "processed.md"):
        p = os.path.join(FEED_DIR, fn)
        if os.path.exists(p):
            text += "\n" + open(p, encoding="utf-8").read()
    if not text.strip():
        print(f"⚠️  Не нашёл ленту в {FEED_DIR} (incoming.md/processed.md).")
        return

    cand = _scan(text)
    known = _known_urls()
    fresh = {k: v for k, v in cand.items() if v.rstrip("/").lower() not in known}

    if not fresh:
        print("✅ Новых репозиториев в ленте нет — каталог уже всё покрывает.")
        return

    print(f"🔎 Кандидатов в каталог (из tg-feed, ещё не добавлены): {len(fresh)}\n")
    for url in sorted(fresh.values()):
        if args.cmds:
            print(f'python3 add.py {url} --cat other --aud public --desc "..."')
        else:
            print(f"  • {url}")
    if not args.cmds:
        print("\nДобавить нужное:  python3 add.py <ссылка> --cat <раздел> --aud me|public --desc \"…\"")
        print("Или сразу команды:  python3 from_feed.py --cmds")


if __name__ == "__main__":
    main()
