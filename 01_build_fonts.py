# -*- coding: utf-8 -*-
import os
import sys
import shutil
import zipfile
from fontTools.ttLib import TTFont, TTCollection


def configure_font_metadata(
    base_font_path,
    names_dict,
    version="Version 5.32",
    codepage1=0x4002009F,
    codepage2=0xDFD70000,
    family_class=2049,
    panose=None,
    vendor_id=b"RICO",
    is_fixed_pitch=0,
    head_flags=0x001B,
):
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

    # 6. Remove STAT table if present
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
            "check_file": os.path.join(
                "Noto_Sans_JP", "static", "NotoSansJP-Regular.ttf"
            ),
            "url": "https://fonts.google.com/specimen/Noto+Sans+JP",
        },
        "Noto_Sans": {
            "zip_names": ["Noto_Sans.zip", "NotoSans.zip"],
            "check_file": os.path.join("Noto_Sans", "static", "NotoSans-Regular.ttf"),
            "url": "https://fonts.google.com/specimen/Noto+Sans",
        },
        "Noto_Sans_Mono": {
            "zip_names": ["Noto_Sans_Mono.zip", "NotoSansMono.zip"],
            "check_file": os.path.join(
                "Noto_Sans_Mono", "static", "NotoSansMono-Regular.ttf"
            ),
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
            print(
                f"    - {os.path.basename(found_zip)} を {target_extract} に自動展開中..."
            )
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


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ensure_extracted_fonts(base_dir)

    noto_jp = os.path.join(base_dir, "extracted_noto_fonts", "Noto_Sans_JP", "static")
    noto_en = os.path.join(base_dir, "extracted_noto_fonts", "Noto_Sans", "static")
    noto_mono = os.path.join(
        base_dir, "extracted_noto_fonts", "Noto_Sans_Mono", "static"
    )

    out_dir = os.path.join(base_dir, "dist")
    out_dir = r"C:\Temp"
    os.makedirs(out_dir, exist_ok=True)
    dist_dir = os.path.join(base_dir, "dist")
    os.makedirs(dist_dir, exist_ok=True)

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
    ttc_msg.save(os.path.join(out_dir, "msgothic.ttc"))

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
    ttc_m.save(os.path.join(out_dir, "meiryo.ttc"))

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
    ttc_mb.save(os.path.join(out_dir, "meiryob.ttc"))

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
    ttc_ygr.save(os.path.join(out_dir, "YuGothR.ttc"))

    ttc_ygm = TTCollection()
    ttc_ygm.fonts = [
        make_yg(
            jp_med,
            "Yu Gothic Medium",
            "\u6e38\u30b4\u30b7\u30c3\u30af Medium",
            "YuGothic-Medium",
            "Regular",
        ),
        make_yg(
            jp_reg, "Yu Gothic UI", "Yu Gothic UI", "YuGothicUI-Regular", "Regular"
        ),
    ]
    ttc_ygm.save(os.path.join(out_dir, "YuGothM.ttc"))

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
    ttc_ygb.save(os.path.join(out_dir, "YuGothB.ttc"))

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
    ttc_ygl.save(os.path.join(out_dir, "YuGothL.ttc"))

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
    ttc_msm.save(os.path.join(out_dir, "msmincho.ttc"))

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
        f.save(os.path.join(out_dir, fname))

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
        f.save(os.path.join(out_dir, fname))

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
        f.save(os.path.join(out_dir, fname))

    # 8. Sync execution bat scripts to C:\Temp
    # 8. Sync to dist directory
    for f in os.listdir(out_dir):
        if f.endswith(".ttf") or f.endswith(".ttc"):
            shutil.copy2(os.path.join(out_dir, f), os.path.join(dist_dir, f))

    # 9. Sync bat scripts to C:\Temp
    temp_dir = r"C:\Temp"
    if os.path.exists(temp_dir):
        print("\n[8/8] Syncing execution bat scripts to C:\\Temp...")
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

    print("\n[SUCCESS] All 100% GDI-compatible fonts generated in C:\\Temp and dist/!")
    print("          Ready for execution via C:\\Temp\\02_replace_fonts.bat in WinRE.")


if __name__ == "__main__":
    main()
