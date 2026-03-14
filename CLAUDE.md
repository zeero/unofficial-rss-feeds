# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

RSS フィードを提供していないウェブサイト向けの非公式 RSS フィード生成プロジェクト。現在は以下のサービスに対応:
- **Anthropic News**: AI研究とClaude関連のニュース
- **OpenAI ChatGPT Release Notes**: ChatGPTのリリースノートとアップデート
- **Claude Code Commits**: anthropics/claude-code GitHubリポジトリのコミット履歴
- **ハナレグミ Live News**: ハナレグミ公式サイトのライブ情報

## 開発コマンド

### 環境セットアップ
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### RSS フィード生成（ローカル実行）
```bash
python scripts/generate_anthropic_rss.py      # → dist/anthropic-news.xml
python scripts/generate_openai_rss.py         # → dist/openai-releases.xml
python scripts/generate_claude_code_rss.py    # → dist/claude-code.xml（最新30件を保持）
python scripts/generate_hanaregumi_rss.py     # → dist/hanaregumi-live.xml
```

### テスト実行
```bash
python -m pytest tests/ -v                          # 全テスト
python -m pytest tests/common/ -v                   # 共通機能テスト
python -m pytest tests/anthropic/ -v                # Anthropic固有テスト
python -m pytest tests/openai/ -v                   # OpenAI固有テスト
python -m pytest -m "unit" -v                       # ユニットテストのみ
python -m pytest -m "integration" -v                # 統合テストのみ
python -m pytest -m "selenium" -v                   # Seleniumテストのみ
python -m pytest -m "not slow" -v                   # 高速テストのみ
python -m pytest tests/common/test_rss_generation.py -v  # 単一ファイル
```

pytest マーカーは `pytest.ini` に定義済み（`--strict-markers` 有効）。未定義マーカーを `-m` に渡すとエラーになる。

## アーキテクチャ

### スクリプト分類：Seleniumあり vs なし

| スクリプト | 取得方法 | Selenium |
|---|---|---|
| `generate_anthropic_rss.py` | Next.js JSONデータ → DOM フォールバック | ✅ 必要 |
| `generate_openai_rss.py` | HTML構造解析（h1/h2/p/ul） | ✅ 必要 |
| `generate_claude_code_rss.py` | GitHub API | ❌ 不要 |
| `generate_hanaregumi_rss.py` | 静的HTML（BeautifulSoup） | ❌ 不要 |

Selenium系スクリプトのワークフローはChromeを自動インストールする。Selenium不要スクリプトは `requests` + `BeautifulSoup` のみで動作する。

### RSS生成の共通パターン

全スクリプトが `xml.etree.ElementTree` で RSS 2.0 XML を生成する（`feedgen` 等の外部ライブラリは使わない）。

**差分更新（claude-code のみ）**: 既存XMLから既出SHAを読み込み、新規コミットのみ追加してマージ・截断する。他スクリプトは毎回フル生成。

**翻訳処理（Anthropic・OpenAI）**: キーワード置換は長い単語から順に処理し、部分一致競合（`news`→`ニュース` と `new`→`新しい`）を回避する。

### GitHub Actions ワークフロー

| ファイル | cron (UTC) | Chrome |
|---|---|---|
| `rss-anthropic-news.yml` | 毎日 23:00 | ✅ |
| `rss-openai-releases.yml` | 毎日 23:00 | ✅ |
| `rss-claude-code.yml` | 毎日 23:00 | ❌ |
| `rss-hanaregumi-live.yml` | 毎日 03:00（JST 12:00） | ❌ |

全ワークフローは `workflow_dispatch` による手動実行にも対応。生成した `dist/` をそのまま GitHub Pages にデプロイする。

### テスト構造

```
tests/
├── conftest.py              # 共通フィクスチャ
├── common/                  # 全サービス共通機能（RSS生成・翻訳・日付処理）
├── anthropic/               # Selenium スクレイピング・統合テスト
└── openai/                  # HTML構造解析・統合テスト
```

新しいRSSサービスを追加する場合は `tests/<service>/` を作成し、共通機能は `tests/common/` を再利用する。
