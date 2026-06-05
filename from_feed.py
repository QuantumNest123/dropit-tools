#!/usr/bin/env python3
"""Кандидаты в каталог из ленты tg-feed + источников Дроп IT.

Идея: tg-feed каждый день сваливает в incoming.md/processed.md посты из каналов,
где часто мелькают GitHub-репозитории. Плюс Дроп IT (ai-channel) копит в queue.json
огромный слой веб-источников (Hacker News, HF-статьи, GitHub Trending, западные
ньюсрумы, RU-медиа) — там репозиториев ещё больше. Этот скрипт достаёт ссылки на
репозитории из ВСЕХ этих источников, выкидывает уже добавленные, и печатает список
«вот что можно добавить». Ничего не качает и не меняет — только показывает.

  python3 from_feed.py            # показать кандидатов
  python3 from_feed.py --cmds     # сразу готовые команды add.py для копипаста
  python3 from_feed.py --feed-only  # только tg-feed, без очереди Дроп IT
"""
import os
import re
import json
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "catalog.json")
# tg-feed лежит рядом в Cours/tools/tg-feed
FEED_DIR = os.path.abspath(os.path.join(HERE, "..", "tools", "tg-feed"))
# ai-channel (Дроп IT) — его queue.json копит веб-источники (HN/HF/trending/ньюсрумы)
AI_CHANNEL = os.path.abspath(os.path.join(HERE, "..", "ai-channel"))

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
    ap = argparse.ArgumentParser(description="Кандидаты в каталог из ленты tg-feed + Дроп IT.")
    ap.add_argument("--cmds", action="store_true", help="печатать готовые команды add.py")
    ap.add_argument("--feed-only", action="store_true",
                    help="только tg-feed, без очереди Дроп IT и tools-harvest")
    args = ap.parse_args()

    # Источники сканирования: моя лента (tg-feed) + накопленный слой Дроп IT.
    # queue.json/claude_tools_inbox.json читаем как сырой текст — _scan() сам выдернет
    # все github.com/owner/repo из полей links/source/src_id, JSON-структура не важна.
    sources = [
        os.path.join(FEED_DIR, "incoming.md"),
        os.path.join(FEED_DIR, "processed.md"),
    ]
    if not args.feed_only:
        sources += [
            os.path.join(FEED_DIR, "claude_tools_inbox.json"),  # tools-harvest «для проектов»
            os.path.join(AI_CHANNEL, "queue.json"),             # HN/HF/trending/ньюсрумы
        ]

    text = ""
    for p in sources:
        if os.path.exists(p):
            text += "\n" + open(p, encoding="utf-8").read()
    if not text.strip():
        print(f"⚠️  Не нашёл источников (tg-feed: {FEED_DIR}).")
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
