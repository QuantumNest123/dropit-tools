#!/usr/bin/env python3
"""Добавить инструмент в каталог Дроп IT по ссылке.

Идея: кидаешь ссылку на GitHub — скрипт сам подтягивает карточку (название,
описание, звёзды, язык, теги) через официальный GitHub API. Никакого скрейпинга.
Ты только ставишь категорию и галочку «кому» (себе тоже / только людям).

Примеры:
  python3 add.py https://github.com/unclecode/crawl4ai --cat scraping --aud me
  python3 add.py https://github.com/ollama/ollama --cat ai-text --aud public --desc "Запуск нейросетей локально на своём компе."
  python3 add.py https://example-tool.com --name "Some Tool" --cat other --aud public --desc "..."

Флаги:
  --cat    категория (ключ из catalog.json: ai-text/ai-image/agents/scraping/dev-tools/skills/other)
  --aud    кому: me (тащим и к себе, и в каталог) | public (только в каталог). По умолчанию public.
  --desc   описание ПО-РУССКИ одной строкой (если не задано — берётся английское с GitHub как заглушка)
  --name   имя (нужно только для НЕ-гитхабовских ссылок)
  --no-build  не пересобирать README после добавления

GITHUB_TOKEN в окружении (необязательно) поднимает лимит API с 60 до 5000 запросов/час.
"""
import os
import re
import sys
import json
import time
import argparse
import subprocess
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "catalog.json")


def _load():
    with open(CATALOG, encoding="utf-8") as f:
        return json.load(f)


def _save(data):
    with open(CATALOG, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _today():
    # ВНИМАНИЕ: дату ставим из системы — для каталога это нормально (это не воркфлоу-скрипт)
    return time.strftime("%Y-%m-%d")


def _parse_github(url):
    """Из ссылки на GitHub достаём owner/repo. Возвращает (owner, repo) или None."""
    m = re.search(r"github\.com/([^/\s]+)/([^/\s#?]+)", url)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    repo = re.sub(r"\.git$", "", repo)
    return owner, repo


def _gh_api(owner, repo):
    """Тянем карточку репозитория через GitHub API (чистый JSON, без скрейпинга)."""
    api = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "User-Agent": "dropit-tools-catalog",
        "Accept": "application/vnd.github+json",
    }
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    req = Request(api, headers=headers)
    with urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def _suggest_cat(gh):
    """Грубая автоподсказка категории по тегам/языку — чтобы не вбивать руками каждый раз.
    Пользователь всегда может переопределить флагом --cat."""
    topics = " ".join(gh.get("topics", [])).lower()
    desc = (gh.get("description") or "").lower()
    hay = topics + " " + desc
    table = [
        ("scraping",  ("scrap", "crawl", "spider", "parser", "scraper", "data-extraction")),
        ("agents",    ("agent", "autonomous", "orchestrat", "workflow", "automation", "multi-agent")),
        ("ai-image",  ("image", "diffusion", "comfyui", "stable-diffusion", "video", "text-to-image", "vision")),
        ("ai-text",   ("llm", "gpt", "chatbot", "language-model", "rag", "ollama", "inference")),
        ("skills",    ("prompt", "skill", "awesome", "cheatsheet", "template")),
        ("dev-tools", ("cli", "developer-tools", "devtools", "vscode", "extension", "sdk")),
    ]
    for key, kws in table:
        if any(k in hay for k in kws):
            return key
    return "other"


def main():
    ap = argparse.ArgumentParser(description="Добавить инструмент в каталог Дроп IT по ссылке.")
    ap.add_argument("url", help="ссылка на GitHub-репозиторий (или любой сайт инструмента)")
    ap.add_argument("--cat", help="категория (ключ из catalog.json)")
    ap.add_argument("--aud", choices=["me", "public"], default=None,
                    help="кому: me=и к себе и в каталог, public=только в каталог (по умолчанию public)")
    ap.add_argument("--desc", help="описание ПО-РУССКИ одной строкой")
    ap.add_argument("--name", help="имя (для не-гитхабовских ссылок)")
    ap.add_argument("--no-build", action="store_true", help="не пересобирать README")
    args = ap.parse_args()

    data = _load()
    valid_cats = {c["key"] for c in data["categories"]}
    url = args.url.strip()

    gh = None
    parsed = _parse_github(url)
    if parsed:
        owner, repo = parsed
        try:
            gh = _gh_api(owner, repo)
        except HTTPError as e:
            print(f"⚠️  GitHub API вернул {e.code} для {owner}/{repo} — добавляю как обычную ссылку.")
        except URLError as e:
            print(f"⚠️  Сеть недоступна ({e.reason}) — добавляю по тому, что есть.")

    # КАНОНИЧЕСКИЙ url: GitHub отдаёт html_url уже после редиректа (переименованные репо).
    # Дедупим именно по нему — иначе старая ссылка и новая создают дубль (баг 2026-06-04).
    canon = (gh.get("html_url") if gh else url).rstrip("/")
    existing = next((t for t in data["tools"]
                     if t["url"].rstrip("/") in (canon, url.rstrip("/"))), None)

    if gh:
        name = args.name or (existing or {}).get("name") or gh.get("name") or f"{owner}/{repo}"
        url = gh.get("html_url", url)
        en_desc = (gh.get("description") or "").strip()
        entry = {
            "name": name,
            "url": url,
            "category": args.cat or (existing or {}).get("category") or _suggest_cat(gh),
            "desc_ru": args.desc or (existing or {}).get("desc_ru") or en_desc,
            "audience": args.aud or (existing or {}).get("audience") or "public",
            "stars": gh.get("stargazers_count", 0),
            "lang": gh.get("language") or "",
            "source": "github",
            "added": (existing or {}).get("added") or _today(),
        }
    else:
        name = args.name or (existing or {}).get("name") or re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
        entry = {
            "name": name,
            "url": url,
            "category": args.cat or (existing or {}).get("category") or "other",
            "desc_ru": args.desc or (existing or {}).get("desc_ru") or "",
            "audience": args.aud or (existing or {}).get("audience") or "public",
            "stars": (existing or {}).get("stars", 0),
            "lang": (existing or {}).get("lang", ""),
            "source": "web",
            "added": (existing or {}).get("added") or _today(),
        }

    if entry["category"] not in valid_cats:
        print(f"⚠️  Категория «{entry['category']}» не из списка {sorted(valid_cats)} — ставлю other.")
        entry["category"] = "other"

    if existing:
        data["tools"][data["tools"].index(existing)] = entry
        action = "обновлён"
    else:
        data["tools"].append(entry)
        action = "добавлен"
    _save(data)

    star = f" · ★ {entry['stars']}" if entry["stars"] else ""
    aud = "⭐ себе+каталог" if entry["audience"] == "me" else "каталог"
    print(f"✅ {action}: {entry['name']} [{entry['category']}, {aud}]{star}")
    if not entry["desc_ru"]:
        print("   ⚠️  без русского описания — добавь флагом --desc, чтобы в каталоге было по-русски.")

    if not args.no_build:
        try:
            subprocess.run([sys.executable, os.path.join(HERE, "build_readme.py")], check=True)
        except Exception as e:
            print(f"   (README не пересобрался: {e} — запусти build_readme.py вручную)")


if __name__ == "__main__":
    main()
