# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

RSS フィードを提供していないウェブサイト向けの非公式 RSS フィード生成プロジェクト。現在は Anthropic ニュース用の RSS フィードを生成している。

## 開発コマンド

### 環境セットアップ
```bash
# 仮想環境作成とアクティベート
python3 -m venv venv
source venv/bin/activate

# 依存関係のインストール
pip install -r requirements.txt
```

### RSS フィード生成（ローカル実行）
```bash
python scripts/generate_anthropic_rss.py
```
生成されたファイル: `dist/anthropic-news.xml`

### テスト実行
```bash
# 全テスト実行
python -m pytest tests/ -v

# カテゴリ別テスト実行
python -m pytest tests/common/ -v      # 共通機能テスト
python -m pytest tests/anthropic/ -v  # Anthropic固有テスト

# マーカー別テスト実行
python -m pytest -m "common" -v       # 共通機能マーカー
python -m pytest -m "anthropic" -v    # Anthropic固有マーカー
python -m pytest -m "not slow" -v     # 高速テストのみ

# 単一テストファイル実行
python -m pytest tests/common/test_rss_generation.py -v
```

## アーキテクチャ

### 拡張可能なテスト構造
プロジェクトは将来の RSS サービス追加を想定した階層構造を採用:

```
tests/
├── conftest.py              # 共通フィクスチャと設定
├── common/                  # 全RSSサービス共通機能
│   └── test_rss_generation.py  # RSS生成、翻訳、日付処理
└── anthropic/              # Anthropic固有機能
    ├── test_anthropic_scraping.py    # Seleniumスクレイピング
    └── test_anthropic_integration.py # 統合テスト
```

新しいRSSサービス（例: OpenAI、Google AI）を追加する場合は、`tests/openai/`、`tests/google/` ディレクトリを作成し、共通機能は `tests/common/` を再利用する。

### GitHub Actions ワークフロー
- `.github/workflows/rss-anthropic-news.yml`: RSS フィード生成とGitHub Pagesへのデプロイを自動化
- Seleniumのために Chrome ブラウザを自動インストール
- 手動実行（workflow_dispatch）または定期実行（cron）で実行可能
- 生成されたRSSファイルは`dist/`ディレクトリに保存され、GitHub Pagesで公開される

### RSS生成アーキテクチャ
`scripts/generate_anthropic_rss.py` は以下の段階的処理を実行:

1. **Selenium WebDriver設定**: ヘッドレスChromeでJavaScript対応
2. **記事抽出**: 
   - 第一段階: Next.js JSON データからの構造化抽出
   - フォールバック: DOM解析による記事リンク抽出
3. **翻訳処理**: 優先順位付きキーワード置換（部分一致問題を回避）
4. **RSS生成**: RSS 2.0準拠のXML出力

### 技術的特徴
- **動的コンテンツ対応**: Seleniumを使用してJavaScript読み込み後のコンテンツをキャプチャ
- **堅牢なフォールバック**: ChromeDriverManager → システムChrome → JSON抽出 → DOM解析の多段階フォールバック
- **翻訳最適化**: 長い単語から順に置換することで「news」→「ニュース」と「new」→「新しい」の競合を回避

## 技術スタック
- Python 3.11
- Selenium: 動的コンテンツスクレイピング
- BeautifulSoup4: HTML パージング
- webdriver-manager: Chrome ドライバー自動管理
- pytest: テストフレームワーク（42テストケース、93%成功率）

## コミュニケーションガイドライン
- コミュニケーションは常に日本語で
- 各文の末尾に感情を表す絵文字をつけてください