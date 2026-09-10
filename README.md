# Windows 主要システムフォント一括置き換え (Noto Font Upserter)

Windows 11 / 10 の主要なシステムフォント（日本語・英語・等幅）を、Google Noto フォントファミリー（Noto Sans JP、Noto Sans、Noto Sans Mono）に一括置き換えするツールセットです。

> [!CAUTION]
>
> ## ⚠️ 【重要】免責事項・システムフォント変更に伴うリスクについて
>
> 本ツールは Windows のシステムフォント（`C:\Windows\Fonts`）を直接書き換えます。システムの根幹に関わる領域を変更するため、**必ず以下のリスクを理解した上で、自己責任（At Your Own Risk）にてご使用ください**。
>
> 1. **表示崩れ・互換性リスク**:
>    - 多くのフォントメトリクスやテーブルを偽装・互換化していますが、特定のレガシーアプリケーションやプロプライエタリな描画エンジンを採用しているソフトウェアでは、文字の重なり、見切れ、ダイアログのはみ出し等が発生する可能性があります。
> 2. **Windows Update による影響**:
>    - Windows Update（特に月例の累積更新プログラムや大型アップデート）の適用時に、純正フォントに勝手に戻されたり、予期せぬ不整合が生じる場合があります。
> 3. **BitLocker 回復キーの確認必須**:
>    - ドライブ暗号化（BitLocker）が有効な環境では、回復環境（WinRE）でコマンドプロンプトを起動する際に **48桁の BitLocker 回復キー** の入力を求められることがあります。あらかじめMicrosoftアカウント等で回復キーを確認・控えてから作業してください。
> 4. **バックアップの事前作成**:
>    - 万が一の不具合や起動障害に備え、作業前に必ず **「システムの復元ポイントの作成」** または **重要データの外部バックアップ** を行ってください。
> 5. **免責事項**:
>    - 本ツールの使用によって生じたいかなる損害（OSの動作不良、データの消失、業務の中断など）に関しても、作者は一切の責任を負いません。

---

## 🚀 特徴

1. **完全 GDI 互換（脱・文字化け「■」）**:
   - 古い Windows ダイアログ（MS Shell Dlg / GDI）が要求する `OS/2` コードページテーブル（CP932/Shift_JIS、OEM）、Panose 値、ファミリークラスを 100% 互換化。
   - レガシー描画エンジンによる欧文フォント（Bahnschrift）への誤フォールバックを防止し、すべてのコントロールで確実に日本語を表示します。

2. **アンチエイリアス強制（脱・ギザギザビットマップ）**:
   - `gasp` テーブルを最適化（全サイズ ClearType 強制）し、本物の MS UI Gothic のような 9pt での荒いドット絵ビットマップを表示させず、**常に滑らかで美しい Noto Sans JP のアウトライン** でレンダリングします。

3. **主要フォントを完全網羅**:
   - 日本語: メイリオ (Meiryo / Meiryo UI)、游ゴシック (Yu Gothic / Yu Gothic UI)、ＭＳ ゴシック (MS Gothic / MS PGothic / MS UI Gothic)、ＭＳ 明朝 (MS Mincho / MS PMincho)
   - 英語: Segoe UI, Arial, Calibri, Tahoma, Verdana
   - 等幅: Consolas, Cascadia Mono / Code, Courier New

---

## 📁 構成と役割

```text
windows-noto-system-fonts/
├── README.md                      # 本マニュアル
├── LICENSE                        # ライセンス（MIT License）
├── GEMINI.md                      # エージェント規則
├── pyproject.toml                 # プロジェクト設定・依存関係定義 (uv/ruff/mypy/pyright)
├── 01_build_fonts.py              # 完全互換フォント生成 兼 スクリプトデプロイ
├── 02_replace_fonts.bat           # システムフォント置き換えバッチ
├── 03_clear_font_cache.bat        # フォントキャッシュクリアバッチ
├── 04_restore_all_fonts.bat       # 全フォント一括ロールバックバッチ
├── 05_restore_msgothic_only.bat   # msgothic.ttc のみ緊急ロールバックバッチ
├── .pre-commit-config.yaml        # 静的解析 & Gate 1 AIレビュー設定
├── .ame-review/                   # AME AI Review System 設定・プロンプト
├── .github/workflows/             # CI / PR レビュー ワークフロー
├── Noto_Sans_JP.zip               # 【要配置】Google Fonts原本ZIP（※Git除外）
├── Noto_Sans.zip                  # 【要配置】Google Fonts原本ZIP（※Git除外）
├── Noto_Sans_Mono.zip             # 【要配置】Google Fonts原本ZIP（※Git除外）
├── dist/                          # 生成された全フォントファイル（※生成物・Git除外）
└── extracted_noto_fonts/          # 自動展開フォントデータ（※Git除外）
```

> **※スクリプト・フォントの配置について**:
> `01_build_fonts.py` を実行すると、生成されたフォントはすべて `dist/` に出力されます。また、回復環境（WinRE）で実行しやすいよう、`C:\Temp` が存在する場合はフォントバイナリおよびバッチスクリプト群（`02_` 〜 `05_`）が **`C:\Temp` に自動デプロイ・同期** されます。

---

## 🛠️ 前提条件

本ツールの実行には、高速な Python パッケージマネージャー **[uv](https://docs.astral.sh/uv/) が必須** です。事前にインストールしてください：

```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# または winget
winget install --id=astral-sh.uv
```

プロジェクトの依存関係の初期化：

```powershell
uv sync
```

---

## 🛠️ 作業手順

### ステップ 0: 原本フォント（Google Fonts）のダウンロードと配置

ライセンス保護およびリポジトリ容量節約のため、フォントバイナリは同梱していません。
初回実行前に、Google Fonts 公式サイトから以下の **3 つのフォントファミリー（ZIP）** をダウンロードし、**プロジェクトのルートディレクトリにそのまま配置** してください：

| フォントファミリー | ダウンロードURL | 配置するZIPファイル名 |
| :--- | :--- | :--- |
| **Noto Sans JP** | [Google Fonts: Noto Sans JP](https://fonts.google.com/specimen/Noto+Sans+JP) | `Noto_Sans_JP.zip` |
| **Noto Sans** | [Google Fonts: Noto Sans](https://fonts.google.com/specimen/Noto+Sans) | `Noto_Sans.zip` |
| **Noto Sans Mono** | [Google Fonts: Noto Sans Mono](https://fonts.google.com/specimen/Noto+Sans+Mono) | `Noto_Sans_Mono.zip` |

> [!TIP]
> 各ページの右上にある **「Download family」** ボタンから ZIP ファイルを取得できます。
> **手動で解凍する必要はありません。** ZIP ファイルをプロジェクトルートに置いておけば、次のステップ 1 でスクリプトが自動的に検出・展開します。

### ステップ 1: フォント生成 ＆ スクリプト配置

PowerShell またはコマンドプロンプトで以下を実行します：

```powershell
uv run 01_build_fonts.py
```

> `dist/` にフォントが生成され、`C:\Temp` に実行用バッチファイル（`02_replace_fonts.bat` 等）が配置されます。

### ステップ 2: Windows 回復環境（WinRE）で置き換え実行

稼働中の Windows ではフォントがロックされているため、回復環境から置き換えます：

1. スタートメニューの電源アイコンを開き、**`Shift` キーを押しながら「再起動」** をクリックします。
2. 青い画面で **「トラブルシューティング」→「詳細オプション」→「コマンド プロンプト」** を選択します。
3. 黒いコマンドプロンプト画面が開いたら、以下の **1行だけ** を入力して Enter を押します：

   ```cmd
   C:\Temp\02_replace_fonts.bat
   ```

   ※`C:\Temp\02_replace_fonts.bat` が自動的に本プロジェクトの `dist/` フォルダ内のフォントを検出して `C:\Windows\Fonts` へ安全に上書きコピーします（元フォントは `.bak` に自動バックアップされます）。
4. 完了後、`exit` と入力して通常通り Windows を起動します。

### ステップ 3: フォントキャッシュのクリア

Windows が通常起動したら：

1. **`C:\Temp\03_clear_font_cache.bat`**（またはプロジェクト直下の同ファイル）を右クリックし、**「管理者として実行」** します。
2. PC をもう一度再起動します。
   （これでシステム全体のフォントが滑らかな Noto Sans JP に生まれ変わります！）

---

## 🔄 元に戻す手順（ロールバック）

万が一元の純正フォントに戻したい場合：

1. `Shift` ＋再起動から回復環境の「コマンド プロンプト」を起動します。
2. 以下のいずれかを実行します：
   - 全フォントを戻す場合: `C:\Temp\04_restore_all_fonts.bat`
   - msgothic だけ戻す場合: `C:\Temp\05_restore_msgothic_only.bat`
3. 再起動後、`03_clear_font_cache.bat` を管理者実行して完了です。
