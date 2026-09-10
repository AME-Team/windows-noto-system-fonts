# Workspace Rules

## 重要規則（制約事項）

- **Cドライブ直下への勝手なディレクトリ作成の禁止**:
  ユーザーからの明示的な指示がない限り、Cドライブ直下（`C:\`）やルートディレクトリに勝手に新規ディレクトリやファイルを作成してはならない。
- **ファイル配置場所の厳守**:
  作業用ファイルや一時ファイルは、ユーザーが指定したパス（`C:\Temp`）または本ワークスペース内のみに配置すること。

## 🛠️ 開発・実行ルール (uv 必須)

- **Python パッケージマネージャー**:
  - 本プロジェクトでは **`uv` の使用が必須** です。
  - スクリプト実行: `uv run 01_build_fonts.py`
  - 静的解析・Lint: `uv run ruff check`, `uv run mypy 01_build_fonts.py`, `uv run pyright 01_build_fonts.py`
  - 依存関係の同期: `uv sync`
- **Dual-Gate レビューラウンド**:
  - コミット時は必ず Gate 1（pre-commit）を通過させること（`SKIP=` や `--no-verify` の使用は厳禁）。
  - PR 作成後は `/request-review` コメントで Gate 2（CI AI レビュー）を呼び出し、未解決スレッドがゼロになるまで対応を完遂すること。
