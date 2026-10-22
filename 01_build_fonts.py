# -*- coding: utf-8 -*-
import os
import shutil
import sys
import zipfile
from contextlib import closing
from typing import Any, Iterable

from fontTools.ttLib import TTCollection, TTFont

#: 本文の表示を壊す GSUB 機能タグ。
#: Noto Sans JP は 'dlig' (Discretionary Ligatures) にカタカナ・単位の組文字を定義しており、
#: 「グラム」→「㌘」、「株式会社」→「㈱」のように語の一部が 1 文字へ潰れる。Windows の
#: フォントエンジンが 'dlig' を適用する画面では「更新プログラム」が「更新プロ㌘」になる
#: (Issue #3)。置き換え対象の MS 系システムフォントは 'dlig' を持たないため、互換性の
#: 観点でも削除する。'liga' は fi/fl など語を壊さない合字のみなので残す。
UNWANTED_GSUB_FEATURES = ("dlig",)

#: 組文字 (CJK 互換文字 U+3200-U+33FF) のコードポイント範囲。この範囲の文字は
#: 「グラム」→「㌘」のように語の一部を 1 文字へ潰す合字の置換先になる。
SQUARE_LIGATURE_RANGES = ((0x3200, 0x33FF),)


def remove_gsub_features(font: TTFont, feature_tags: tuple[str, ...]) -> list[str]:
    """GSUB から指定タグの機能を削除する。

    機能レコードを削除すると FeatureList の添字が詰まるため、各 LangSys が持つ
    FeatureIndex / ReqFeatureIndex と、可変フォントの FeatureVariations が持つ
    FeatureIndex も張り替える。削除した機能だけが参照していた lookup は
    未参照のまま残す。どの機能からも参照されない lookup はシェーピングで適用されず、
    LookupList の添字を全張り替えする方が既存の参照を壊すリスクが大きいため。

    Args:
        font: 対象フォント
        feature_tags: 削除する GSUB 機能タグ

    Returns:
        実際に削除した機能タグのリスト (対象が無ければ空)
    """
    if "GSUB" not in font:
        return []

    gsub = font["GSUB"].table
    feature_list = gsub.FeatureList
    if feature_list is None or not feature_list.FeatureRecord:
        return []
    old_records = feature_list.FeatureRecord
    keep_indices = [i for i, r in enumerate(old_records) if r.FeatureTag not in feature_tags]
    removed = sorted({r.FeatureTag for r in old_records if r.FeatureTag in feature_tags})
    if not removed:
        return []

    index_map = {old_index: new_index for new_index, old_index in enumerate(keep_indices)}
    # 件数フィールド (FeatureCount / SubstitutionCount 等) は fontTools なら保存時に配列長から
    # 書き出されるが、実装差異で古い値が残らないよう明示的にも更新しておく。
    for script_record in gsub.ScriptList.ScriptRecord:
        script = script_record.Script
        lang_sys_list = [] if script.DefaultLangSys is None else [script.DefaultLangSys]
        lang_sys_list += [record.LangSys for record in script.LangSysRecord]
        for lang_sys in lang_sys_list:
            lang_sys.FeatureIndex = [
                index_map[index] for index in lang_sys.FeatureIndex if index in index_map
            ]
            lang_sys.FeatureCount = len(lang_sys.FeatureIndex)
            if lang_sys.ReqFeatureIndex != 0xFFFF:
                lang_sys.ReqFeatureIndex = index_map.get(lang_sys.ReqFeatureIndex, 0xFFFF)

    # 可変フォントは条件ごとに機能を差し替える (FeatureVariations)。LangSys と同じく
    # 機能の添字を持つため、張り替えないと削除後の添字と食い違う。
    feature_variations = getattr(gsub, "FeatureVariations", None)
    if feature_variations is not None:
        kept_variations = []
        for variation in feature_variations.FeatureVariationRecord:
            table_substitution = variation.FeatureTableSubstitution
            kept_substitutions = []
            for substitution in table_substitution.SubstitutionRecord:
                if substitution.FeatureIndex not in index_map:
                    continue
                substitution.FeatureIndex = index_map[substitution.FeatureIndex]
                kept_substitutions.append(substitution)
            # 差し替え先をすべて失った条件は、適用しても何も変わらないため削除する。
            if not kept_substitutions:
                continue
            table_substitution.SubstitutionRecord = kept_substitutions
            table_substitution.SubstitutionCount = len(kept_substitutions)
            kept_variations.append(variation)
        feature_variations.FeatureVariationRecord = kept_variations
        feature_variations.FeatureVariationCount = len(kept_variations)
        # 差し替えが 1 件も残らなければ、空の FeatureVariations を書き出さない。
        if not kept_variations:
            gsub.FeatureVariations = None

    feature_list.FeatureRecord = [old_records[index] for index in keep_indices]
    feature_list.FeatureCount = len(feature_list.FeatureRecord)

    remaining = {r.FeatureTag for r in feature_list.FeatureRecord}
    stale = [tag for tag in feature_tags if tag in remaining]
    if stale:
        raise RuntimeError(f"GSUB 機能を削除できませんでした: {stale}")
    return removed


#: この実行で書き出したフォントのパス。ビルド末尾の検証 (Issue #3) の対象にするため、
#: 保存のたびに記録する。dist/ に残る過去ビルドの生成物や手動配置のファイルを
#: 検証対象に巻き込まないよう、名前を列挙せず実際に保存したものだけを渡す。
generated_font_paths: list[str] = []


def save_font(font: TTFont | TTCollection, path: str) -> None:
    """フォントを保存し、検証対象として記録する。

    Args:
        font: 保存するフォント (TTF) またはフォントコレクション (TTC)
        path: 出力先パス
    """
    font.save(path)
    generated_font_paths.append(path)


def _square_glyphs(font: TTFont) -> set[str]:
    """組文字 (CJK 互換文字) に対応するグリフ名を集める。"""
    cmap = font.getBestCmap()
    if not cmap:
        return set()
    return {
        cmap[code]
        for low, high in SQUARE_LIGATURE_RANGES
        for code in range(low, high + 1)
        if code in cmap
    }


#: 文脈依存 lookup (5 / 6 / 8) が置換を委譲するレコードの入れ物。fontTools の
#: otTables で文書化されている属性名だけを使う (内部構造のリフレクション走査はしない)。
_CONTEXT_RULE_SET_ATTRS = ("SubRuleSet", "SubClassSet", "ChainSubRuleSet", "ChainSubClassSet")
_CONTEXT_RULE_ATTRS = ("SubRule", "SubClassRule", "ChainSubRule", "ChainSubClassRule")


def _contextual_lookup_indices(table: object) -> list[int]:
    """文脈依存 subtable が委譲する先の lookup 添字を集める。

    文脈依存 lookup は置換を他の lookup へ委譲するため、参照先まで辿らないと合字の
    置換先を見落とす。format 1/2 は規則集合 (SubRuleSet など)、format 3 は subtable
    直下に SubstLookupRecord を持つ。
    """
    found: list[int] = []

    def collect(records: Iterable[Any] | None) -> None:
        for record in records or []:
            index = getattr(record, "LookupListIndex", None)
            if isinstance(index, int):
                found.append(index)

    collect(getattr(table, "SubstLookupRecord", None))
    for set_attr in _CONTEXT_RULE_SET_ATTRS:
        for rule_set in getattr(table, set_attr, None) or []:
            if rule_set is None:
                continue
            for rule_attr in _CONTEXT_RULE_ATTRS:
                for rule in getattr(rule_set, rule_attr, None) or []:
                    collect(getattr(rule, "SubstLookupRecord", None))
    return found


def _live_ligature_targets(font: TTFont) -> dict[str, tuple[str, int]]:
    """機能から参照される lookup が生成する合字グリフを、由来と共に集める。

    起点は FeatureList の全機能 (ScriptList からの到達性では絞らない)。aalt / salt の
    ように既定で無効な機能も、アプリが明示的に有効化すれば適用されるため、検証では
    「適用され得る」と保守的にみなす。可変フォントの FeatureVariations が差し替える
    機能も起点に含める。どの機能からも参照されない lookup だけは、どのシェーパも
    適用しないため対象外とする (削除した 'dlig' が残した lookup を検出しない)。

    Returns:
        合字グリフ名 -> (由来の機能タグ, 生成した lookup の添字)
    """
    if "GSUB" not in font:
        return {}

    gsub = font["GSUB"].table
    feature_list = getattr(gsub, "FeatureList", None)
    if feature_list is None or not feature_list.FeatureRecord:
        return {}

    lookups = getattr(gsub, "LookupList", None)
    if lookups is None or not lookups.Lookup:
        return {}
    lookup_list = lookups.Lookup

    # lookup 添字 -> そこへ至る機能タグ (エラーメッセージで原因を特定できるようにする)
    origin: dict[int, str] = {}
    for record in feature_list.FeatureRecord:
        for index in record.Feature.LookupListIndex:
            origin.setdefault(index, record.FeatureTag)
    feature_variations = getattr(gsub, "FeatureVariations", None)
    if feature_variations is not None:
        for variation in feature_variations.FeatureVariationRecord:
            for substitution in variation.FeatureTableSubstitution.SubstitutionRecord:
                for index in substitution.Feature.LookupListIndex:
                    origin.setdefault(index, "FeatureVariations")

    targets: dict[str, tuple[str, int]] = {}
    pending = list(origin)
    visited: set[int] = set()
    while pending:
        index = pending.pop()
        if index in visited or not 0 <= index < len(lookup_list):
            continue
        visited.add(index)
        tag = origin.get(index, "-")
        for subtable in lookup_list[index].SubTable:
            # Extension lookup (7) は実体の subtable を包む。
            inner = getattr(subtable, "ExtSubTable", subtable)
            for ligatures in getattr(inner, "ligatures", {}).values():
                for ligature in ligatures:
                    targets.setdefault(ligature.LigGlyph, (tag, index))
            for referenced in _contextual_lookup_indices(inner):
                origin.setdefault(referenced, tag)
                pending.append(referenced)
    return targets


def _assert_no_unwanted_features(font: TTFont, path: str, feature_tags: tuple[str, ...]) -> None:
    """削除対象の GSUB 機能タグが残っていないことを確認する。"""
    if "GSUB" not in font:
        return
    feature_list = getattr(font["GSUB"].table, "FeatureList", None)
    if feature_list is None or not feature_list.FeatureRecord:
        return
    tags = {record.FeatureTag for record in feature_list.FeatureRecord}
    leftover = [tag for tag in feature_tags if tag in tags]
    if leftover:
        raise RuntimeError(f"{os.path.basename(path)} に GSUB 機能 {leftover} が残っています")


def _assert_no_square_ligatures(font: TTFont, path: str) -> None:
    """フォントが組文字へ潰れる合字を残していないことを確認する。"""
    squares = _square_glyphs(font)
    if not squares:
        return
    targets = _live_ligature_targets(font)
    leftover = sorted(glyph for glyph in targets if glyph in squares)
    if not leftover:
        return
    shown = ", ".join(
        f"{glyph} ({targets[glyph][0]} lookup {targets[glyph][1]})" for glyph in leftover[:5]
    )
    suffix = f" ほか {len(leftover) - 5} 件" if len(leftover) > 5 else ""
    raise RuntimeError(f"{os.path.basename(path)} に組文字への合字が残っています: {shown}{suffix}")


def _verify_faces(fonts: list[TTFont], path: str, feature_tags: tuple[str, ...]) -> int:
    """フォント群の GSUB を検証し、フェイス数を返す。"""
    for font in fonts:
        _assert_no_unwanted_features(font, path, feature_tags)
        _assert_no_square_ligatures(font, path)
    return len(fonts)


def verify_no_square_ligatures(paths: list[str], feature_tags: tuple[str, ...]) -> int:
    """保存済みの生成物を読み直し、意図しない GSUB 機能・合字が残っていないことを確認する。

    2 段階で見る。どちらか片方では穴が残るため両方必要。

    1. 削除対象の機能タグ ('dlig') が残っていないこと (README の記述どおり削除されたか)
    2. 機能から参照される合字の置換先が組文字 (U+3200-U+33FF) でないこと。タグ名に
       依存しないため、Noto 側で合字が 'calt' など別タグへ移っても再発を検出できる。

    Args:
        paths: 検証するフォントファイル (.ttc / .ttf)
        feature_tags: 残っていてはならない GSUB 機能タグ

    Returns:
        検証したフェイス数
    """
    if not paths:
        raise RuntimeError("検証対象のフォントが 1 件もありません")

    checked = 0
    for path in paths:
        # 生成と後始末を 1 か所にまとめ、読み込み途中で失敗しても開いたままにしない。
        if path.lower().endswith(".ttc"):
            with closing(TTCollection(path)) as collection:
                checked += _verify_faces(collection.fonts, path, feature_tags)
        else:
            with closing(TTFont(path)) as font:
                checked += _verify_faces([font], path, feature_tags)
    return checked


#: このブランチの前コミットで付けた公開名。外部スクリプトが import していても壊れない
#: よう別名を残す (本体は verify_no_square_ligatures)。
verify_no_unwanted_gsub_features = verify_no_square_ligatures


def configure_font_metadata(
    base_font_path: str,
    names_dict: dict[int, dict[tuple[int, int, int], str]],
    version: str = "Version 5.32",
    codepage1: int = 0x4002009F,
    codepage2: int = 0xDFD70000,
    family_class: int = 2049,
    panose: dict[str, int] | None = None,
    vendor_id: bytes = b"RICO",
    is_fixed_pitch: int = 0,
    head_flags: int = 0x001B,
) -> TTFont:
    """Windows システムフォントとの完全 GDI 互換性を確保するためのフォントメタデータを設定する。

    Args:
        base_font_path: 元となる Noto フォントのファイルパス (.ttf)
        names_dict: Name テーブルに設定する名前辞書 {nameID: {(platID, encID, langID): name}}
        version: フォントバージョン文字列 (NameID 5)
        codepage1: OS/2 ulCodePageRange1 (CP932/Shift_JIS 等のコードページ指定)
        codepage2: OS/2 ulCodePageRange2
        family_class: OS/2 sFamilyClass (GDI 互換のファミリークラス)
        panose: OS/2 Panose テーブル属性の辞書
        vendor_id: OS/2 achVendID (ベンダー識別子)
        is_fixed_pitch: post isFixedPitch (等幅フォントフラグ)
        head_flags: head flags フラグ値

    Returns:
        メタデータ調整済みの TTFont オブジェクト
    """
    font = TTFont(base_font_path)

    # 1. Clean and set Name Table
    name_table = font["name"]
    name_table.names = [
        r for r in name_table.names if r.nameID not in [1, 2, 3, 4, 5, 6, 16, 17, 25]
    ]

    # Set Version (NameID 5)
    name_table.setName(version, 5, 3, 1, 0x0409)
    name_table.setName(version, 5, 3, 1, 0x0411)
    name_table.setName(version, 5, 3, 10, 0x0409)
    name_table.setName(version, 5, 3, 10, 0x0411)
    name_table.setName(version, 5, 1, 0, 0x0000)

    for name_id, val_entries in names_dict.items():
        for (plat_id, enc_id, lang_id), val in val_entries.items():
            name_table.setName(val, name_id, plat_id, enc_id, lang_id)

    # 2. Configure OS/2 Table for 100% GDI Compatibility
    if "OS/2" in font:
        os2 = font["OS/2"]
        os2.ulCodePageRange1 = codepage1
        os2.ulCodePageRange2 = codepage2
        os2.sFamilyClass = family_class
        os2.achVendID = vendor_id
        if panose:
            for p_attr, p_val in panose.items():
                setattr(os2.panose, p_attr, p_val)

    # 3. Configure Post Table
    if "post" in font:
        font["post"].isFixedPitch = is_fixed_pitch

    # 4. Configure Head Table
    if "head" in font:
        font["head"].flags = head_flags

    # 5. Configure Gasp Table (Force ClearType / Anti-aliasing for all sizes)
    if "gasp" in font:
        font["gasp"].gaspRange = {65535: 15}

    # 6. Remove GSUB features that collapse words into square ligatures (Issue #3)
    remove_gsub_features(font, UNWANTED_GSUB_FEATURES)

    # 7. Remove STAT table if present
    if "STAT" in font:
        del font["STAT"]

    return font


def ensure_extracted_fonts(base_dir):
    """Check if extracted_noto_fonts contains required fonts.
    If missing, automatically extract from ZIP files placed in base_dir.
    If ZIP files are also missing, display an informative error and exit.
    """
    extracted_dir = os.path.join(base_dir, "extracted_noto_fonts")

    font_zips = {
        "Noto_Sans_JP": {
            "zip_names": ["Noto_Sans_JP.zip", "NotoSansJP.zip"],
            "check_file": os.path.join("Noto_Sans_JP", "static", "NotoSansJP-Regular.ttf"),
            "url": "https://fonts.google.com/specimen/Noto+Sans+JP",
        },
        "Noto_Sans": {
            "zip_names": ["Noto_Sans.zip", "NotoSans.zip"],
            "check_file": os.path.join("Noto_Sans", "static", "NotoSans-Regular.ttf"),
            "url": "https://fonts.google.com/specimen/Noto+Sans",
        },
        "Noto_Sans_Mono": {
            "zip_names": ["Noto_Sans_Mono.zip", "NotoSansMono.zip"],
            "check_file": os.path.join("Noto_Sans_Mono", "static", "NotoSansMono-Regular.ttf"),
            "url": "https://fonts.google.com/specimen/Noto+Sans+Mono",
        },
    }

    missing_fonts = []
    for font_key, info in font_zips.items():
        check_path = os.path.join(extracted_dir, info["check_file"])
        if not os.path.exists(check_path):
            missing_fonts.append(font_key)

    if not missing_fonts:
        return

    print("[*] 原本フォントの存在を確認・展開中...")
    missing_zips = []
    for font_key in missing_fonts:
        info = font_zips[font_key]
        found_zip = None
        for zname in info["zip_names"]:
            candidate = os.path.join(base_dir, zname)
            if os.path.exists(candidate):
                found_zip = candidate
                break

        if found_zip:
            target_extract = os.path.join(extracted_dir, font_key)
            os.makedirs(target_extract, exist_ok=True)
            print(f"    - {os.path.basename(found_zip)} を {target_extract} に自動展開中...")
            with zipfile.ZipFile(found_zip, "r") as zf:
                zf.extractall(target_extract)
        else:
            missing_zips.append((font_key, info["zip_names"][0], info["url"]))

    if missing_zips:
        print("\n" + "=" * 65)
        print("【エラー】原本フォント（Google Fonts）が見つかりません。")
        print("以下のURLからフォントファミリー（ZIP）をダウンロードし、")
        print(f"プロジェクトのルートディレクトリ ({base_dir}) に配置してください。\n")
        for font_key, zip_name, url in missing_zips:
            print(f"  - {font_key}:")
            print(f"      配置ファイル名: {zip_name}")
            print(f"      ダウンロードURL: {url}")
        print("=" * 65 + "\n")
        sys.exit(1)


def check_uv_environment():
    """Verify that script is executed under an active virtual environment or uv."""
    in_venv = (sys.prefix != getattr(sys, "base_prefix", sys.prefix)) or bool(
        os.environ.get("VIRTUAL_ENV")
    )
    if not in_venv:
        print("\n" + "=" * 65)
        print("【注意】本スクリプトの実行には uv が必須です。")
        print("依存関係の整合性を保つため、以下のコマンドで実行してください：\n")
        print("    uv run 01_build_fonts.py")
        print("=" * 65 + "\n")
        sys.exit(1)


def main():
    check_uv_environment()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ensure_extracted_fonts(base_dir)

    noto_jp = os.path.join(base_dir, "extracted_noto_fonts", "Noto_Sans_JP", "static")
    noto_en = os.path.join(base_dir, "extracted_noto_fonts", "Noto_Sans", "static")
    noto_mono = os.path.join(base_dir, "extracted_noto_fonts", "Noto_Sans_Mono", "static")

    dist_dir = os.path.join(base_dir, "dist")
    os.makedirs(dist_dir, exist_ok=True)
    out_dir = dist_dir
    generated_font_paths.clear()

    print("==================================================")
    print(" Building 100% GDI-Compatible Windows System Fonts")
    print("==================================================")

    jp_reg = os.path.join(noto_jp, "NotoSansJP-Regular.ttf")
    jp_med = os.path.join(noto_jp, "NotoSansJP-Medium.ttf")
    jp_bld = os.path.join(noto_jp, "NotoSansJP-Bold.ttf")
    jp_lit = os.path.join(noto_jp, "NotoSansJP-Light.ttf")

    # 1. MS Gothic & MS UI Gothic & MS PGothic (msgothic.ttc)
    print("\n[1/8] Generating fully compatible msgothic.ttc...")
    panose_gothic = {
        "bFamilyType": 2,
        "bSerifStyle": 11,
        "bWeight": 6,
        "bProportion": 9,
        "bContrast": 7,
        "bStrokeVariation": 2,
        "bArmStyle": 5,
        "bLetterForm": 8,
        "bMidline": 2,
        "bXHeight": 4,
    }
    panose_ui = {
        "bFamilyType": 2,
        "bSerifStyle": 11,
        "bWeight": 6,
        "bProportion": 0,
        "bContrast": 7,
        "bStrokeVariation": 2,
        "bArmStyle": 5,
        "bLetterForm": 8,
        "bMidline": 2,
        "bXHeight": 4,
    }

    msg_0 = configure_font_metadata(
        jp_reg,
        {
            1: {
                (3, 1, 0x409): "MS Gothic",
                (3, 1, 0x411): "\uff2d\uff33 \u30b4\u30b7\u30c3\u30af",
                (3, 10, 0x409): "MS Gothic",
                (3, 10, 0x411): "\uff2d\uff33 \u30b4\u30b7\u30c3\u30af",
                (1, 0, 0x0000): "MS Gothic",
            },
            2: {
                (3, 1, 0x409): "Regular",
                (3, 1, 0x411): "\u6a19\u6e96",
                (3, 10, 0x409): "Regular",
                (3, 10, 0x411): "\u6a19\u6e96",
                (1, 0, 0x0000): "Regular",
            },
            3: {
                (3, 1, 0x409): "Microsoft:MS Gothic",
                (3, 10, 0x409): "Microsoft:MS Gothic",
            },
            4: {
                (3, 1, 0x409): "MS Gothic",
                (3, 1, 0x411): "\uff2d\uff33 \u30b4\u30b7\u30c3\u30af",
                (3, 10, 0x409): "MS Gothic",
                (3, 10, 0x411): "\uff2d\uff33 \u30b4\u30b7\u30c3\u30af",
                (1, 0, 0x0000): "MS Gothic",
            },
            6: {
                (3, 1, 0x409): "MS-Gothic",
                (3, 1, 0x411): "MS-Gothic",
                (3, 10, 0x409): "MS-Gothic",
                (3, 10, 0x411): "MS-Gothic",
                (1, 0, 0x0000): "MS-Gothic",
            },
        },
        version="Version 5.32",
        codepage1=0x4002009F,
        codepage2=0xDFD70000,
        family_class=2049,
        panose=panose_gothic,
        vendor_id=b"RICO",
        is_fixed_pitch=1,
    )
    msg_1 = configure_font_metadata(
        jp_reg,
        {
            1: {
                (3, 1, 0x409): "MS UI Gothic",
                (3, 1, 0x411): "MS UI Gothic",
                (3, 10, 0x409): "MS UI Gothic",
                (3, 10, 0x411): "MS UI Gothic",
                (1, 0, 0x0000): "MS UI Gothic",
            },
            2: {
                (3, 1, 0x409): "Regular",
                (3, 1, 0x411): "\u6a19\u6e96",
                (3, 10, 0x409): "Regular",
                (3, 10, 0x411): "\u6a19\u6e96",
                (1, 0, 0x0000): "Regular",
            },
            3: {
                (3, 1, 0x409): "Microsoft:MS UI Gothic",
                (3, 10, 0x409): "Microsoft:MS UI Gothic",
            },
            4: {
                (3, 1, 0x409): "MS UI Gothic",
                (3, 1, 0x411): "MS UI Gothic",
                (3, 10, 0x409): "MS UI Gothic",
                (3, 10, 0x411): "MS UI Gothic",
                (1, 0, 0x0000): "MS UI Gothic",
            },
            6: {
                (3, 1, 0x409): "MS-UIGothic",
                (3, 1, 0x411): "MS-UIGothic",
                (3, 10, 0x409): "MS-UIGothic",
                (3, 10, 0x411): "MS-UIGothic",
                (1, 0, 0x0000): "MS-UIGothic",
            },
        },
        version="Version 5.32",
        codepage1=0x4002009F,
        codepage2=0xDFD70000,
        family_class=2049,
        panose=panose_ui,
        vendor_id=b"RICO",
        is_fixed_pitch=0,
    )
    msg_2 = configure_font_metadata(
        jp_reg,
        {
            1: {
                (3, 1, 0x409): "MS PGothic",
                (3, 1, 0x411): "\uff2d\uff33 \uff30\u30b4\u30b7\u30c3\u30af",
                (3, 10, 0x409): "MS PGothic",
                (3, 10, 0x411): "\uff2d\uff33 \uff30\u30b4\u30b7\u30c3\u30af",
                (1, 0, 0x0000): "MS PGothic",
            },
            2: {
                (3, 1, 0x409): "Regular",
                (3, 1, 0x411): "\u6a19\u6e96",
                (3, 10, 0x409): "Regular",
                (3, 10, 0x411): "\u6a19\u6e96",
                (1, 0, 0x0000): "Regular",
            },
            3: {
                (3, 1, 0x409): "Microsoft:MS PGothic",
                (3, 10, 0x409): "Microsoft:MS PGothic",
            },
            4: {
                (3, 1, 0x409): "MS PGothic",
                (3, 1, 0x411): "\uff2d\uff33 \uff30\u30b4\u30b7\u30c3\u30af",
                (3, 10, 0x409): "MS PGothic",
                (3, 10, 0x411): "\uff2d\uff33 \uff30\u30b4\u30b7\u30c3\u30af",
                (1, 0, 0x0000): "MS PGothic",
            },
            6: {
                (3, 1, 0x409): "MS-PGothic",
                (3, 1, 0x411): "MS-PGothic",
                (3, 10, 0x409): "MS-PGothic",
                (3, 10, 0x411): "MS-PGothic",
                (1, 0, 0x0000): "MS-PGothic",
            },
        },
        version="Version 5.32",
        codepage1=0x4002009F,
        codepage2=0xDFD70000,
        family_class=2049,
        panose=panose_ui,
        vendor_id=b"RICO",
        is_fixed_pitch=0,
    )
    ttc_msg = TTCollection()
    ttc_msg.fonts = [msg_0, msg_1, msg_2]
    save_font(ttc_msg, os.path.join(out_dir, "msgothic.ttc"))

    # 2. Meiryo & Meiryo UI
    print("[2/8] Generating meiryo.ttc & meiryob.ttc...")
    panose_meiryo = {
        "bFamilyType": 2,
        "bSerifStyle": 11,
        "bWeight": 6,
        "bProportion": 4,
        "bContrast": 3,
        "bStrokeVariation": 5,
        "bArmStyle": 4,
        "bLetterForm": 4,
        "bMidline": 2,
        "bXHeight": 4,
    }
    m_reg = configure_font_metadata(
        jp_reg,
        {
            1: {(3, 1, 0x409): "Meiryo", (3, 1, 0x411): "\u30e1\u30a4\u30ea\u30aa"},
            2: {
                (3, 1, 0x409): "Regular",
                (3, 1, 0x411): "\u30ec\u30ae\u30e5\u30e9\u30fc",
            },
            3: {(3, 1, 0x409): "Microsoft:Meiryo Regular"},
            4: {(3, 1, 0x409): "Meiryo", (3, 1, 0x411): "\u30e1\u30a4\u30ea\u30aa"},
            6: {(3, 1, 0x409): "Meiryo", (3, 1, 0x411): "Meiryo"},
        },
        version="Version 6.50",
        codepage1=0x6002009F,
        codepage2=0xDFD70000,
        family_class=2048,
        panose=panose_meiryo,
        vendor_id=b"MS  ",
    )
    m_ita = configure_font_metadata(
        jp_reg,
        {
            1: {(3, 1, 0x409): "Meiryo", (3, 1, 0x411): "\u30e1\u30a4\u30ea\u30aa"},
            2: {
                (3, 1, 0x409): "Italic",
                (3, 1, 0x411): "\u30a4\u30bf\u30ea\u30c3\u30af",
            },
            3: {(3, 1, 0x409): "Microsoft:Meiryo Italic"},
            4: {
                (3, 1, 0x409): "Meiryo Italic",
                (
                    3,
                    1,
                    0x411,
                ): "\u30e1\u30a4\u30ea\u30aa \u30a4\u30bf\u30ea\u30c3\u30af",
            },
            6: {(3, 1, 0x409): "Meiryo-Italic", (3, 1, 0x411): "Meiryo-Italic"},
        },
        version="Version 6.50",
        codepage1=0x6002009F,
        codepage2=0xDFD70000,
        family_class=2048,
        panose=panose_meiryo,
        vendor_id=b"MS  ",
    )
    m_ui_reg = configure_font_metadata(
        jp_reg,
        {
            1: {(3, 1, 0x409): "Meiryo UI", (3, 1, 0x411): "Meiryo UI"},
            2: {(3, 1, 0x409): "Regular", (3, 1, 0x411): "Regular"},
            3: {(3, 1, 0x409): "Microsoft:Meiryo UI Regular"},
            4: {(3, 1, 0x409): "Meiryo UI", (3, 1, 0x411): "Meiryo UI"},
            6: {(3, 1, 0x409): "MeiryoUI", (3, 1, 0x411): "MeiryoUI"},
        },
        version="Version 6.50",
        codepage1=0x6002009F,
        codepage2=0xDFD70000,
        family_class=2048,
        panose=panose_meiryo,
        vendor_id=b"MS  ",
    )
    m_ui_ita = configure_font_metadata(
        jp_reg,
        {
            1: {(3, 1, 0x409): "Meiryo UI", (3, 1, 0x411): "Meiryo UI"},
            2: {(3, 1, 0x409): "Italic", (3, 1, 0x411): "Italic"},
            3: {(3, 1, 0x409): "Microsoft:Meiryo UI Italic"},
            4: {(3, 1, 0x409): "Meiryo UI Italic", (3, 1, 0x411): "Meiryo UI Italic"},
            6: {(3, 1, 0x409): "MeiryoUI-Italic", (3, 1, 0x411): "MeiryoUI-Italic"},
        },
        version="Version 6.50",
        codepage1=0x6002009F,
        codepage2=0xDFD70000,
        family_class=2048,
        panose=panose_meiryo,
        vendor_id=b"MS  ",
    )
    ttc_m = TTCollection()
    ttc_m.fonts = [m_reg, m_ita, m_ui_reg, m_ui_ita]
    save_font(ttc_m, os.path.join(out_dir, "meiryo.ttc"))

    panose_meiryo_bold = dict(panose_meiryo)
    panose_meiryo_bold["bWeight"] = 8
    m_bld = configure_font_metadata(
        jp_bld,
        {
            1: {(3, 1, 0x409): "Meiryo", (3, 1, 0x411): "\u30e1\u30a4\u30ea\u30aa"},
            2: {(3, 1, 0x409): "Bold", (3, 1, 0x411): "\u30dc\u30fc\u30eb\u30c9"},
            3: {(3, 1, 0x409): "Microsoft:Meiryo Bold"},
            4: {
                (3, 1, 0x409): "Meiryo Bold",
                (3, 1, 0x411): "\u30e1\u30a4\u30ea\u30aa \u30dc\u30fc\u30eb\u30c9",
            },
            6: {(3, 1, 0x409): "Meiryo-Bold", (3, 1, 0x411): "Meiryo-Bold"},
        },
        version="Version 6.50",
        codepage1=0x6002009F,
        codepage2=0xDFD70000,
        family_class=2048,
        panose=panose_meiryo_bold,
        vendor_id=b"MS  ",
    )
    m_bld_ita = configure_font_metadata(
        jp_bld,
        {
            1: {(3, 1, 0x409): "Meiryo", (3, 1, 0x411): "\u30e1\u30a4\u30ea\u30aa"},
            2: {
                (3, 1, 0x409): "Bold Italic",
                (
                    3,
                    1,
                    0x411,
                ): "\u30dc\u30fc\u30eb\u30c9 \u30a4\u30bf\u30ea\u30c3\u30af",
            },
            3: {(3, 1, 0x409): "Microsoft:Meiryo Bold Italic"},
            4: {
                (3, 1, 0x409): "Meiryo Bold Italic",
                (
                    3,
                    1,
                    0x411,
                ): "\u30e1\u30a4\u30ea\u30aa \u30dc\u30fc\u30eb\u30c9 \u30a4\u30bf\u30ea\u30c3\u30af",
            },
            6: {(3, 1, 0x409): "Meiryo-BoldItalic", (3, 1, 0x411): "Meiryo-BoldItalic"},
        },
        version="Version 6.50",
        codepage1=0x6002009F,
        codepage2=0xDFD70000,
        family_class=2048,
        panose=panose_meiryo_bold,
        vendor_id=b"MS  ",
    )
    m_ui_bld = configure_font_metadata(
        jp_bld,
        {
            1: {(3, 1, 0x409): "Meiryo UI", (3, 1, 0x411): "Meiryo UI"},
            2: {(3, 1, 0x409): "Bold", (3, 1, 0x411): "Bold"},
            3: {(3, 1, 0x409): "Microsoft:Meiryo UI Bold"},
            4: {(3, 1, 0x409): "Meiryo UI Bold", (3, 1, 0x411): "Meiryo UI Bold"},
            6: {(3, 1, 0x409): "MeiryoUI-Bold", (3, 1, 0x411): "MeiryoUI-Bold"},
        },
        version="Version 6.50",
        codepage1=0x6002009F,
        codepage2=0xDFD70000,
        family_class=2048,
        panose=panose_meiryo_bold,
        vendor_id=b"MS  ",
    )
    m_ui_bld_ita = configure_font_metadata(
        jp_bld,
        {
            1: {(3, 1, 0x409): "Meiryo UI", (3, 1, 0x411): "Meiryo UI"},
            2: {(3, 1, 0x409): "Bold Italic", (3, 1, 0x411): "Bold Italic"},
            3: {(3, 1, 0x409): "Microsoft:Meiryo UI Bold Italic"},
            4: {
                (3, 1, 0x409): "Meiryo UI Bold Italic",
                (3, 1, 0x411): "Meiryo UI Bold Italic",
            },
            6: {
                (3, 1, 0x409): "MeiryoUI-BoldItalic",
                (3, 1, 0x411): "MeiryoUI-BoldItalic",
            },
        },
        version="Version 6.50",
        codepage1=0x6002009F,
        codepage2=0xDFD70000,
        family_class=2048,
        panose=panose_meiryo_bold,
        vendor_id=b"MS  ",
    )
    ttc_mb = TTCollection()
    ttc_mb.fonts = [m_bld, m_bld_ita, m_ui_bld, m_ui_bld_ita]
    save_font(ttc_mb, os.path.join(out_dir, "meiryob.ttc"))

    # 3. Yu Gothic
    print("[3/8] Generating Yu Gothic TTCs...")
    panose_yg = {
        "bFamilyType": 2,
        "bSerifStyle": 11,
        "bWeight": 6,
        "bProportion": 4,
        "bContrast": 2,
        "bStrokeVariation": 2,
        "bArmStyle": 2,
        "bLetterForm": 2,
        "bMidline": 2,
        "bXHeight": 4,
    }

    def make_yg(src, name_en, name_ja, ps_name, weight="Regular"):
        return configure_font_metadata(
            src,
            {
                1: {(3, 1, 0x409): name_en, (3, 1, 0x411): name_ja},
                2: {(3, 1, 0x409): weight, (3, 1, 0x411): weight},
                3: {(3, 1, 0x409): f"Microsoft:{name_en}"},
                4: {
                    (3, 1, 0x409): f"{name_en} {weight}",
                    (3, 1, 0x411): f"{name_ja} {weight}",
                },
                6: {(3, 1, 0x409): ps_name, (3, 1, 0x411): ps_name},
            },
            version="Version 1.90",
            codepage1=0x6002009F,
            codepage2=0xDFD70000,
            family_class=2048,
            panose=panose_yg,
            vendor_id=b"MS  ",
        )

    ttc_ygr = TTCollection()
    ttc_ygr.fonts = [
        make_yg(
            jp_reg,
            "Yu Gothic",
            "\u6e38\u30b4\u30b7\u30c3\u30af",
            "YuGothic-Regular",
            "Regular",
        ),
        make_yg(
            jp_lit,
            "Yu Gothic UI Semilight",
            "Yu Gothic UI Semilight",
            "YuGothicUI-Semilight",
            "Regular",
        ),
    ]
    save_font(ttc_ygr, os.path.join(out_dir, "YuGothR.ttc"))

    ttc_ygm = TTCollection()
    ttc_ygm.fonts = [
        make_yg(
            jp_med,
            "Yu Gothic Medium",
            "\u6e38\u30b4\u30b7\u30c3\u30af Medium",
            "YuGothic-Medium",
            "Regular",
        ),
        make_yg(jp_reg, "Yu Gothic UI", "Yu Gothic UI", "YuGothicUI-Regular", "Regular"),
    ]
    save_font(ttc_ygm, os.path.join(out_dir, "YuGothM.ttc"))

    ttc_ygb = TTCollection()
    ttc_ygb.fonts = [
        make_yg(
            jp_bld,
            "Yu Gothic",
            "\u6e38\u30b4\u30b7\u30c3\u30af",
            "YuGothic-Bold",
            "Bold",
        ),
        make_yg(jp_bld, "Yu Gothic UI", "Yu Gothic UI", "YuGothicUI-Bold", "Bold"),
        make_yg(
            jp_med,
            "Yu Gothic UI Semibold",
            "Yu Gothic UI Semibold",
            "YuGothicUI-Semibold",
            "Regular",
        ),
    ]
    save_font(ttc_ygb, os.path.join(out_dir, "YuGothB.ttc"))

    ttc_ygl = TTCollection()
    ttc_ygl.fonts = [
        make_yg(
            jp_lit,
            "Yu Gothic Light",
            "\u6e38\u30b4\u30b7\u30c3\u30af Light",
            "YuGothic-Light",
            "Regular",
        ),
        make_yg(
            jp_lit,
            "Yu Gothic UI Light",
            "Yu Gothic UI Light",
            "YuGothicUI-Light",
            "Regular",
        ),
    ]
    save_font(ttc_ygl, os.path.join(out_dir, "YuGothL.ttc"))

    # 4. MS Mincho
    print("[4/8] Generating msmincho.ttc...")
    panose_mincho = {
        "bFamilyType": 2,
        "bSerifStyle": 2,
        "bWeight": 6,
        "bProportion": 9,
        "bContrast": 4,
        "bStrokeVariation": 2,
        "bArmStyle": 5,
        "bLetterForm": 8,
        "bMidline": 2,
        "bXHeight": 4,
    }
    msm_0 = configure_font_metadata(
        jp_reg,
        {
            1: {(3, 1, 0x409): "MS Mincho", (3, 1, 0x411): "\uff2d\uff33 \u660e\u671d"},
            2: {(3, 1, 0x409): "Regular", (3, 1, 0x411): "\u6a19\u6e96"},
            3: {(3, 1, 0x409): "Microsoft:MS Mincho"},
            4: {(3, 1, 0x409): "MS Mincho", (3, 1, 0x411): "\uff2d\uff33 \u660e\u671d"},
            6: {(3, 1, 0x409): "MS-Mincho", (3, 1, 0x411): "MS-Mincho"},
        },
        version="Version 5.32",
        codepage1=0x4002009F,
        codepage2=0xDFD70000,
        family_class=2049,
        panose=panose_mincho,
        vendor_id=b"RICO",
        is_fixed_pitch=1,
    )
    panose_pmincho = dict(panose_mincho)
    panose_pmincho["bProportion"] = 0
    msm_1 = configure_font_metadata(
        jp_reg,
        {
            1: {
                (3, 1, 0x409): "MS PMincho",
                (3, 1, 0x411): "\uff2d\uff33 \uff30\u660e\u671d",
            },
            2: {(3, 1, 0x409): "Regular", (3, 1, 0x411): "\u6a19\u6e96"},
            3: {(3, 1, 0x409): "Microsoft:MS PMincho"},
            4: {
                (3, 1, 0x409): "MS PMincho",
                (3, 1, 0x411): "\uff2d\uff33 \uff30\u660e\u671d",
            },
            6: {(3, 1, 0x409): "MS-PMincho", (3, 1, 0x411): "MS-PMincho"},
        },
        version="Version 5.32",
        codepage1=0x4002009F,
        codepage2=0xDFD70000,
        family_class=2049,
        panose=panose_pmincho,
        vendor_id=b"RICO",
        is_fixed_pitch=0,
    )
    ttc_msm = TTCollection()
    ttc_msm.fonts = [msm_0, msm_1]
    save_font(ttc_msm, os.path.join(out_dir, "msmincho.ttc"))

    # 5. Segoe UI
    print("[5/8] Generating Segoe UI TTFs...")
    en_reg = os.path.join(noto_en, "NotoSans-Regular.ttf")
    en_bld = os.path.join(noto_en, "NotoSans-Bold.ttf")
    en_ita = os.path.join(noto_en, "NotoSans-Italic.ttf")
    en_bi = os.path.join(noto_en, "NotoSans-BoldItalic.ttf")
    en_lit = os.path.join(noto_en, "NotoSans-Light.ttf")
    en_sb = os.path.join(noto_en, "NotoSans-SemiBold.ttf")

    segoe_defs = [
        ("segoeui.ttf", en_reg, "Segoe UI", "Regular", "Segoe UI", "SegoeUI"),
        ("segoeuib.ttf", en_bld, "Segoe UI", "Bold", "Segoe UI Bold", "SegoeUI-Bold"),
        (
            "segoeuii.ttf",
            en_ita,
            "Segoe UI",
            "Italic",
            "Segoe UI Italic",
            "SegoeUI-Italic",
        ),
        (
            "segoeuiz.ttf",
            en_bi,
            "Segoe UI",
            "Bold Italic",
            "Segoe UI Bold Italic",
            "SegoeUI-BoldItalic",
        ),
        (
            "segoeuil.ttf",
            en_lit,
            "Segoe UI Light",
            "Regular",
            "Segoe UI Light",
            "SegoeUI-Light",
        ),
        (
            "segoeuisl.ttf",
            en_lit,
            "Segoe UI Semilight",
            "Regular",
            "Segoe UI Semilight",
            "SegoeUI-Semilight",
        ),
        (
            "seguisb.ttf",
            en_sb,
            "Segoe UI Semibold",
            "Regular",
            "Segoe UI Semibold",
            "SegoeUI-Semibold",
        ),
    ]
    for fname, src, fam, sub, full, ps in segoe_defs:
        f = configure_font_metadata(
            src,
            {
                1: {(3, 1, 0x409): fam},
                2: {(3, 1, 0x409): sub},
                3: {(3, 1, 0x409): f"Microsoft:{full}"},
                4: {(3, 1, 0x409): full},
                6: {(3, 1, 0x409): ps},
            },
            version="Version 5.38",
            codepage1=0x2000019F,
            codepage2=0x00000000,
            family_class=2049,
            vendor_id=b"MS  ",
        )
        save_font(f, os.path.join(out_dir, fname))

    # 6. Arial, Calibri, Tahoma, Verdana
    print("[6/8] Generating Arial, Calibri, Tahoma, Verdana TTFs...")
    en_li = os.path.join(noto_en, "NotoSans-LightItalic.ttf")
    other_en = [
        ("arial.ttf", en_reg, "Arial", "Regular", "Arial", "ArialMT"),
        ("arialbd.ttf", en_bld, "Arial", "Bold", "Arial Bold", "Arial-BoldMT"),
        ("ariali.ttf", en_ita, "Arial", "Italic", "Arial Italic", "Arial-ItalicMT"),
        (
            "arialbi.ttf",
            en_bi,
            "Arial",
            "Bold Italic",
            "Arial Bold Italic",
            "Arial-BoldItalicMT",
        ),
        ("calibri.ttf", en_reg, "Calibri", "Regular", "Calibri", "Calibri"),
        ("calibrib.ttf", en_bld, "Calibri", "Bold", "Calibri Bold", "Calibri-Bold"),
        (
            "calibrii.ttf",
            en_ita,
            "Calibri",
            "Italic",
            "Calibri Italic",
            "Calibri-Italic",
        ),
        (
            "calibriz.ttf",
            en_bi,
            "Calibri",
            "Bold Italic",
            "Calibri Bold Italic",
            "Calibri-BoldItalic",
        ),
        (
            "calibril.ttf",
            en_lit,
            "Calibri Light",
            "Regular",
            "Calibri Light",
            "Calibri-Light",
        ),
        (
            "calibrili.ttf",
            en_li,
            "Calibri Light",
            "Italic",
            "Calibri Light Italic",
            "Calibri-LightItalic",
        ),
        ("tahoma.ttf", en_reg, "Tahoma", "Regular", "Tahoma", "Tahoma"),
        ("tahomabd.ttf", en_bld, "Tahoma", "Bold", "Tahoma Bold", "Tahoma-Bold"),
        ("verdana.ttf", en_reg, "Verdana", "Regular", "Verdana", "Verdana"),
        ("verdanab.ttf", en_bld, "Verdana", "Bold", "Verdana Bold", "Verdana-Bold"),
        (
            "verdanai.ttf",
            en_ita,
            "Verdana",
            "Italic",
            "Verdana Italic",
            "Verdana-Italic",
        ),
        (
            "verdanaz.ttf",
            en_bi,
            "Verdana",
            "Bold Italic",
            "Verdana Bold Italic",
            "Verdana-BoldItalic",
        ),
    ]
    for fname, src, fam, sub, full, ps in other_en:
        f = configure_font_metadata(
            src,
            {
                1: {(3, 1, 0x409): fam},
                2: {(3, 1, 0x409): sub},
                3: {(3, 1, 0x409): f"Monotype:{full}"},
                4: {(3, 1, 0x409): full},
                6: {(3, 1, 0x409): ps},
            },
            version="Version 7.00",
            codepage1=0x2000019F,
            codepage2=0x00000000,
            family_class=2049,
            vendor_id=b"MONO",
        )
        save_font(f, os.path.join(out_dir, fname))

    # 7. Monospace Fonts
    print("[7/8] Generating Monospace TTFs...")
    mono_reg = os.path.join(noto_mono, "NotoSansMono-Regular.ttf")
    mono_bld = os.path.join(noto_mono, "NotoSansMono-Bold.ttf")

    mono_defs = [
        ("consola.ttf", mono_reg, "Consolas", "Regular", "Consolas", "Consolas"),
        (
            "consolab.ttf",
            mono_bld,
            "Consolas",
            "Bold",
            "Consolas Bold",
            "Consolas-Bold",
        ),
        (
            "consolai.ttf",
            mono_reg,
            "Consolas",
            "Italic",
            "Consolas Italic",
            "Consolas-Italic",
        ),
        (
            "consolaz.ttf",
            mono_bld,
            "Consolas",
            "Bold Italic",
            "Consolas Bold Italic",
            "Consolas-BoldItalic",
        ),
        (
            "CascadiaMono.ttf",
            mono_reg,
            "Cascadia Mono",
            "Regular",
            "Cascadia Mono Regular",
            "CascadiaMono-Roman",
        ),
        (
            "CascadiaCode.ttf",
            mono_reg,
            "Cascadia Code",
            "Regular",
            "Cascadia Code Regular",
            "CascadiaCode-Roman",
        ),
        (
            "cour.ttf",
            mono_reg,
            "Courier New",
            "Regular",
            "Courier New",
            "CourierNewPSMT",
        ),
        (
            "courbd.ttf",
            mono_bld,
            "Courier New",
            "Bold",
            "Courier New Bold",
            "CourierNewPS-BoldMT",
        ),
        (
            "couri.ttf",
            mono_reg,
            "Courier New",
            "Italic",
            "Courier New Italic",
            "CourierNewPS-ItalicMT",
        ),
        (
            "courbi.ttf",
            mono_bld,
            "Courier New",
            "Bold Italic",
            "Courier New Bold Italic",
            "CourierNewPS-BoldItalicMT",
        ),
    ]
    for fname, src, fam, sub, full, ps in mono_defs:
        f = configure_font_metadata(
            src,
            {
                1: {(3, 1, 0x409): fam},
                2: {(3, 1, 0x409): sub},
                3: {(3, 1, 0x409): f"Monotype:{full}"},
                4: {(3, 1, 0x409): full},
                6: {(3, 1, 0x409): ps},
            },
            version="Version 7.00",
            codepage1=0x2000019F,
            codepage2=0x00000000,
            family_class=2049,
            vendor_id=b"MONO",
            is_fixed_pitch=1,
        )
        save_font(f, os.path.join(out_dir, fname))

    # 削除した GSUB 機能が生成物に残っていないことを確認する (Issue #3)。
    # 将来 Noto 側の GSUB が変わって削除が空振りすると「プロ㌘」が再発するため、
    # 沈黙して成功させず、ここで落とす。C:\Temp へのコピーより前に実行し、
    # 検証に落ちたフォントが配布先へ流れないようにする。
    # 対象はこの実行で保存したフォントのみ (save_font が記録したパス)。
    # dist/ に残る過去ビルドの生成物や手動配置のファイルは対象外になる。
    # タグ名の不在だけでなく「組文字へ潰れる合字が適用され得るか」も見るので、
    # Noto 側で合字が別タグへ移っても再発を検出できる。
    tags = " / ".join(UNWANTED_GSUB_FEATURES)
    checked = verify_no_square_ligatures(generated_font_paths, UNWANTED_GSUB_FEATURES)
    print(f"\n[check] GSUB 機能 {tags} の不在と組文字合字なしを確認: {checked} フェイス")

    # 8. Sync generated fonts and bat scripts to C:\Temp if present
    temp_dir = r"C:\Temp"
    if os.path.exists(temp_dir):
        print("\n[8/8] Syncing fonts and execution bat scripts to C:\\Temp...")
        for f in os.listdir(dist_dir):
            if f.endswith(".ttf") or f.endswith(".ttc"):
                shutil.copy2(os.path.join(dist_dir, f), os.path.join(temp_dir, f))
        bats = [
            "02_replace_fonts.bat",
            "03_clear_font_cache.bat",
            "04_restore_all_fonts.bat",
            "05_restore_msgothic_only.bat",
        ]
        for b in bats:
            src_b = os.path.join(base_dir, b)
            if os.path.exists(src_b):
                shutil.copy2(src_b, os.path.join(temp_dir, b))
                print(f"  Deployed {b} -> C:\\Temp\\{b}")

    print("\n[SUCCESS] All 100% GDI-compatible fonts generated in dist/!")
    if os.path.exists(temp_dir):
        print("          Synced to C:\\Temp for easy WinRE execution.")
    print("          Ready for execution via C:\\Temp\\02_replace_fonts.bat in WinRE.")


if __name__ == "__main__":
    main()
