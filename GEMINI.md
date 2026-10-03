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
  - レビューシステムの参照は hub（`AME-Team/AME-AI-Review-System`）の移動メジャータグ `v0`（CI）と、`.pre-commit-config.yaml` に `#sha256=` 付きで固定した wheel（Gate 1、現在 v0.2.16）である。CI は自動追随し、Gate 1 の wheel は `ame-ai-reviewer sync` で更新する（差分確認は `sync --check`）。リリース直後は両者の版がずれ得る。
  - ラッパの `checks: read` は Gate 2 が PR の check runs を読むための権限で、欠けると外部 CI ゲートが無言で無効化される。`review_reply.yml` には前置 `if` を置かない（自己除外・コマンド除外・メンション判定は upstream が行う）。`review_command.yml` のジョブ `if` は維持する。
