"""Assemble kb/_pages/NNN.md (one transcribed photo each) into one Markdown file per source document.

Each page file starts with a small header (photo, source, page, pages, kind). Pages are grouped by
`source`, ordered by page number, and written to kb/<slug>.md with the pages present and missing.
kb/ is gitignored: the content is internal material and this repo is public.

    uv run python scripts/assemble_kb.py
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

KB = Path(__file__).resolve().parents[1] / "kb"
PAGES = KB / "_pages"

# source path -> (slug, title, one-line summary)
DOCS = {
    "4.HTVH/Homecare/aec2c073-142c-48d7-b761-dde0c105ba92.pdf": (
        "homecare",
        "HOMECARE — Chương trình hỗ trợ CBNV mua nhà (Techcombank – Masterise – One Mount)",
        "Mục tiêu, 3 lớp chính sách, HomeCare 1/2/3, ưu đãi theo dự án, hành trình, đầu mối liên hệ, FAQ.",
    ),
    "4.HTVH/Homecare/Phu-luc-Han-muc-vay-uu-dai-CTV2-CTV3-Han-muc-Homec.pdf": (
        "phu-luc-han-muc-vay-ctv2-ctv3",
        "Phụ lục hạn mức vay ưu đãi CTV2, CTV3 và hạn mức Homecare",
        "Hạn mức cho vay CTV2/CTV3 theo cấp bậc (hiện tại và thay đổi), hạn mức CTV2 áp dụng Homecare.",
    ),
    "4.HTVH/MAG/d36bb7d3-cb0b-45b5-b9a3-7ec1439e3d9e.pdf": (
        "masteri-khung-chien-luoc-thuong-hieu",
        "Masteri — Khung chiến lược thương hiệu (khách hàng Affluent & Henrys)",
        "Chân dung 'Upgraded Living Pursuers': nhân khẩu học, lối sống, hành vi.",
    ),
    "4.HTVH/MAG/cda14c2f-b934-4292-81ba-dabd4aa2d5bc.pdf": (
        "lumiere-brand-strategy",
        "Lumière — Brand Strategy (khách hàng Henrys & EHNWIs)",
        "Chân dung 'Enrichment Experience Pursuer': nhân khẩu học, lối sống, hành vi.",
    ),
    "4.HTVH/OMG/c112ea03-5dc6-4e77-bfb0-b4137d81c942.pdf": (
        "gioi-thieu-one-mount-group",
        "Giới thiệu One Mount Group",
        "Tầm nhìn/sứ mệnh, cơ cấu tổ chức, OneHousing, OMD/VinShop, OMC/VinID/OneU, giải pháp thanh toán.",
    ),
    "4.HTVH/OMG/5499c618-3875-4db6-99d0-d48e961e4677.pdf": (
        "techcombank-va-he-sinh-thai-2025",
        "Techcombank & Hệ sinh thái — Tài liệu giới thiệu (TP.HCM, 04/2025)",
        "Techcombank (hành trình, chiến lược, thành tựu, lãnh đạo, cộng đồng), Masterise Group/Homes, One Mount và các giải thưởng.",
    ),
    "4.HTVH/strategy/f8543154-4848-4526-adab-c3829f9fe77f.pdf": (
        "cam-nang-thuong-hieu-techcombank",
        "Cẩm nang thương hiệu Techcombank (xuất bản 3/2023)",
        "Tầm nhìn, sứ mệnh, lời hứa 'Vượt trội hơn mỗi ngày', tính cách thương hiệu, biểu tượng, màu sắc, phông chữ.",
    ),
    "4.HTVH/strategy/57c946f6-242d-45e5-a37d-98794211a498.pdf": (
        "chien-luoc-5-nam-2026-2030",
        "Techcombank 5-Year Strategy 2026–2030 (English deck)",
        "Kết quả 2021–2025, 3 trụ cột, bối cảnh, tham vọng 65 tỷ USD 2030, 8 chiến lược, lộ trình chuyển đổi.",
    ),
    "word/hanh-trinh-van-hoa-H1-2026.docx": (
        "hanh-trinh-van-hoa-H1-2026",
        "Hành trình văn hóa Hệ sinh thái H1.2026 — Facts & Achievements",
        "One Culture, AI, học tập, tuân thủ & lãnh đạo, well-being, vinh danh, định hướng & sự kiện H2.2026.",
    ),
    "word/notebook-chien-luoc-va-cam-nang.docx": (
        "tom-tat-chien-luoc-va-cam-nang",
        "Tóm tắt: Chiến lược 5 năm 2026–2030 và Cẩm nang thương hiệu",
        "Bản tóm tắt tiếng Việt của hai tài liệu trên (có chú thích nguồn).",
    ),
    "word/notebook-wepro-bctc-H1-2026.docx": (
        "tom-tat-wepro-bctc-H1-2026",
        "Tóm tắt wePRO — Báo cáo tài chính Techcombank nửa đầu 2026",
        "Vĩ mô 6M26, kết quả tài chính Q1 và 6T/2026, cơ cấu tổ chức, kinh doanh số, giải thưởng, quản lý rủi ro.",
    ),
    "word/notebook-ban-tin-noi-bo.docx": (
        "tom-tat-ban-tin-noi-bo",
        "Tóm tắt bản tin nội bộ (Techcombank Care 2026, One AI, Thuế TNCN, tuyển dụng, Chạm Yêu Thương, Panasonic, TCGI)",
        "8 bản tin nội bộ đầu 2026.",
    ),
    "word/notebook-wepro-AI.docx": (
        "tom-tat-wepro-AI",
        "Tóm tắt wePRO – AI (tháng 6/2026): khen thưởng AI và công cụ AI",
        "AI Spot Award, Breakthrough Bonus, HRConnect/Joule, AI Transformer Agent, Smartie 3.0.",
    ),
}


def read(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    _, head, body = text.split("---\n", 2)
    meta = dict(line.split(": ", 1) for line in head.strip().splitlines())
    return meta, body.strip()


def pages_of(value: str) -> list[int]:
    nums = [int(n) for n in re.findall(r"\d+", value)]
    return list(range(nums[0], nums[-1] + 1)) if nums else []


def main() -> None:
    groups: dict[str, list[tuple[int, str, dict, str]]] = defaultdict(list)
    for path in sorted(PAGES.glob("*.md")):
        meta, body = read(path)
        first = (pages_of(meta["page"]) or [0])[0]
        groups[meta["source"]].append((first, meta["photo"], meta, body))

    index = []
    for source, items in groups.items():
        slug, title, summary = DOCS[source]
        items.sort(key=lambda it: (it[0], it[1]))
        total = int(items[0][2]["pages"])
        seen = sorted({p for _, _, meta, _ in items for p in pages_of(meta["page"])})
        missing = [p for p in range(1, total + 1) if p not in seen]
        lines = [
            f"# {title}",
            "",
            f"- **Nguồn:** `{source}` ({total} trang)",
            f"- **Có trong kho:** trang {', '.join(map(str, seen))}",
            f"- **Thiếu:** {('trang ' + ', '.join(map(str, missing))) if missing else 'không'}"
            + (" — câu hỏi về các trang này không trả lời được từ kho." if missing else ""),
            f"- **Nội dung:** {summary}",
            "",
        ]
        for first, photo, meta, body in items:
            body = re.sub(r"^(#+) ", lambda m: "#" * (len(m.group(1)) + 2) + " ", body, flags=re.M)
            lines += [f"## Trang {meta['page']}", f"<!-- ảnh {photo} -->", "", body, ""]
        (KB / f"{slug}.md").write_text("\n".join(lines), encoding="utf-8")
        index.append((slug, title, total, len(seen), missing, summary))

    out = [
        "# Kho kiến thức wePRO — mục lục",
        "",
        "Chép lại từ 152 ảnh chụp tài liệu (không lưu ảnh). Mỗi tệp là một tài liệu gốc; mỗi mục `## Trang N`",
        "là một trang. Thuật ngữ và chữ viết tắt: [glossary.md](glossary.md).",
        "",
        "| Tài liệu | Trang có / tổng | Thiếu | Nội dung |",
        "|---|---|---|---|",
    ]
    for slug, title, total, have, missing, summary in index:
        miss = ", ".join(map(str, missing)) if missing else "—"
        out.append(f"| [{title}]({slug}.md) | {have}/{total} | {miss} | {summary} |")
    (KB / "INDEX.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{len(index)} documents, {sum(len(v) for v in groups.values())} photos")


if __name__ == "__main__":
    main()
