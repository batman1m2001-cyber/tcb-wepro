"""Build kb/: one Markdown file per source document, plus INDEX.md.

Sources:
- photos, transcribed by hand to kb/_pages/NNN.md and kb/_pages2/NNN.md (a header gives source and
  page); grouped by source, ordered by page;
- Word files in newdata/*.docx, converted with their headings and tables;
- internal posts in newdata/*.txt (separated by =====), with previews and copies dropped
  (a post whose 8-word shingles are >=90% inside a longer post, or >=75% when it ends "… Xem thêm");
- PDFs in newdata/*.pdf, text extracted page by page;
- documents written by hand in kb/_docs/*.md (e.g. a PDF whose text layer is broken), copied as is.

Two short wave-1 summaries are dropped because a longer version of the same notebook arrived in
wave 2 (SUPERSEDED). kb/ and newdata/ are gitignored: internal material, public repo.

    uv run --with pypdf --with python-docx python scripts/build_kb.py
"""

from __future__ import annotations

import itertools
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

KB = Path(__file__).resolve().parents[1] / "kb"
ROOT = KB.parent
PAGE_DIRS = [KB / "_pages", KB / "_pages2"]
NEW = ROOT / "newdata"
HAND = KB / "_docs"
SUPERSEDED = {"word/notebook-ban-tin-noi-bo.docx", "word/notebook-wepro-AI.docx"}

# source path -> (slug, title, one-line summary)
DOCS = {
    "newdata/ban-tin-techcomworld-603-635.pdf": (
        "ban-tin-techcomworld-603-635",
        "Tổng hợp bản tin TechcomWorld số 603–635 (23/01–18/09/2026)",
        "Từng số bản tin: kết quả kinh doanh, sản phẩm, AI, hệ sinh thái, sự kiện, nhân vật, giải thưởng.",
    ),
    "newdata/ban-tin-noi-bo-chi-tiet.pdf": (
        "ban-tin-noi-bo-chi-tiet",
        "Bản tin nội bộ đầu 2026 — bản chi tiết (Techcombank Care, One AI, Thuế TNCN, tuyển dụng, Chạm Yêu Thương, Panasonic, TCGI)",
        "Bản đầy đủ của 9 bản tin nội bộ; thay cho bản tóm tắt ngắn ở đợt 1.",
    ),
    "newdata/wepro-AI-chi-tiet.pdf": (
        "wepro-AI-chi-tiet",
        "wePRO – AI (chi tiết): AI Spot Award, Breakthrough Bonus, HRConnect/Joule, AI Transformer Agent, Smartie 3.0",
        "Bản đầy đủ 8 trang; thay cho bản tóm tắt ngắn ở đợt 1.",
    ),
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


def nest(body: str, by: int = 2) -> str:
    """Push a page's own headings below the document's `## Trang N`."""
    return re.sub(r"^(#+) ", lambda m: "#" * min(len(m.group(1)) + by, 6) + " ", body, flags=re.M)


def photo_docs() -> list[tuple[str, str, str, str]]:
    groups: dict[str, list[tuple[int, str, dict, str]]] = defaultdict(list)
    for d in PAGE_DIRS:
        for path in sorted(d.glob("*.md")):
            meta, body = read(path)
            first = (pages_of(meta["page"]) or [0])[0]
            groups[meta["source"]].append((first, meta["photo"], meta, body))
    out = []
    for source, items in groups.items():
        if source in SUPERSEDED:
            continue
        slug, title, summary = DOCS[source]
        items.sort(key=lambda it: (it[0], it[1]))
        total = int(items[0][2]["pages"])
        seen = sorted({p for _, _, meta, _ in items for p in pages_of(meta["page"])})
        missing = [p for p in range(1, total + 1) if p not in seen]
        word = "Phần" if source.startswith("newdata/") else "Trang"
        lines = [f"# {title}", "", f"- **Nguồn:** `{source}` — chép tay từ ảnh chụp màn hình"]
        if word == "Trang":
            lines.append(f"- **Có:** trang {', '.join(map(str, seen))} / {total}")
            if missing:
                lines.append(
                    f"- **Thiếu:** trang {', '.join(map(str, missing))} — không trả lời được từ kho."
                )
        lines += [f"- **Nội dung:** {summary}", ""]
        for _, photo, meta, body in items:
            lines += [f"## {word} {meta['page']}", f"<!-- ảnh {photo} -->", "", nest(body), ""]
        cover = f"{len(seen)}/{total}" + (
            f", thiếu {', '.join(map(str, missing))}" if missing else ""
        )
        out.append((slug, title, cover if word == "Trang" else f"{total} phần", "\n".join(lines)))
    return out


def docx_md(path: Path) -> str:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    d = Document(path)
    out = []
    for el in d.element.body.iterchildren():
        tag = el.tag.split("}")[1]
        if tag == "p":
            p = Paragraph(el, d)
            t = p.text.strip()
            if not t:
                continue
            try:
                style = (p.style.name or "").lower()
            except Exception:
                style = ""
            numbered = (
                el.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numPr")
                is not None
            )
            if style.startswith("heading"):
                out.append("#" * min(int(re.sub(r"\D", "", style) or 1) + 1, 6) + " " + t)
            elif style.startswith("title"):
                out.append("## " + t)
            elif "list" in style or numbered:
                out.append("- " + t)
            else:
                out.append(t)
        elif tag == "tbl":
            rows = [
                [c.text.strip().replace("\n", " ").replace("|", "/") for c in r.cells]
                for r in Table(el, d).rows
            ]
            if rows:
                out.append(
                    "\n".join(
                        ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])]
                        + ["| " + " | ".join(r) + " |" for r in rows[1:]]
                    )
                )
    return "\n\n".join(out)


def word_docs() -> list[tuple[str, str, str, str]]:
    out = []
    for path in sorted(NEW.glob("*.docx")):
        slug = path.stem
        title = slug.replace("-", " ")
        body = docx_md(path)
        text = f"# {title}\n\n- **Nguồn:** `newdata/{path.name}` (Word)\n\n{body}\n"
        out.append((slug, title, f"{len(body.split())} từ", text))
    return out


def norm(t: str) -> str:
    t = unicodedata.normalize("NFC", t).lower()
    t = re.sub(r"(ẩn bớt|xem thêm)", " ", t)
    return re.sub(r"[^\w]+", " ", t).strip()


def shingles(t: str, k: int = 8) -> set[str]:
    w = norm(t).split()
    return {" ".join(w[i : i + k]) for i in range(max(1, len(w) - k + 1))}


def post_docs() -> tuple[list[tuple[str, str, str, str]], list[str]]:
    posts = []
    for path in sorted(NEW.glob("*.txt")):
        for i, p in enumerate(re.split(r"\n=+\n", path.read_text(encoding="utf-8"))):
            if p.strip():
                posts.append((path.name, i, p.strip()))
    sh = [shingles(p) for *_, p in posts]
    drop: dict[int, str] = {}
    for a, b in itertools.combinations(range(len(posts)), 2):
        small, big = (a, b) if len(posts[a][2]) <= len(posts[b][2]) else (b, a)
        share = len(sh[small] & sh[big]) / len(sh[small])
        preview = re.search(r"(…|\.\.\.)\s*Xem thêm\s*$", posts[small][2]) is not None
        if share >= 0.9 or (share >= 0.75 and preview):
            drop[small] = (
                f"{posts[small][0]} #{posts[small][1]} → giữ {posts[big][0]} #{posts[big][1]} ({share:.2f})"
            )
    out = []
    for name in sorted({f for f, *_ in posts}):
        kept = [(i, p) for k, (f, i, p) in enumerate(posts) if f == name and k not in drop]
        lines = [
            f"# Bài đăng nội bộ — {name[:-4]}",
            "",
            f"- **Nguồn:** `newdata/{name}` ({len(kept)} bài sau khi bỏ bản trùng)",
            "",
        ]
        for i, p in kept:
            p = re.sub(r"\s*(…\s*)?(Xem thêm|Ẩn bớt)\s*$", "", p)
            first = p.splitlines()[0].strip()[:90]
            lines += [f"## Bài {i + 1} — {first}", "", p, ""]
        slug = "bai-dang-" + name[:-4].lower().replace("_", "-")
        out.append((slug, f"Bài đăng nội bộ — {name[:-4]}", f"{len(kept)} bài", "\n".join(lines)))
    return out, sorted(drop.values())


def pdf_docs() -> list[tuple[str, str, str, str]]:
    from pypdf import PdfReader

    out = []
    for path in sorted(NEW.glob("*.pdf")):
        r = PdfReader(path)
        lines = [
            f"# {path.stem}",
            "",
            f"- **Nguồn:** `newdata/{path.name}` ({len(r.pages)} trang), trích văn bản tự động; bảng có thể lệch cột.",
            "",
        ]
        for i, page in enumerate(r.pages, 1):
            t = re.sub(
                r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", (page.extract_text() or "").strip())
            )
            if len(t) >= 30:
                lines += [f"## Trang {i}", "", t, ""]
        out.append((path.stem, path.stem, f"{len(r.pages)} trang", "\n".join(lines)))
    return out


def main() -> None:
    for old in KB.glob("*.md"):
        if old.name not in ("glossary.md", "PROJECT_INSTRUCTIONS.md"):
            old.unlink()
    docs = photo_docs() + word_docs()
    posts, dropped = post_docs()
    docs += posts + pdf_docs()
    for path in sorted(HAND.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = text.splitlines()[0].lstrip("# ").strip()
        docs.append((path.stem, title, "chép tay", text))
    for slug, _, _, text in docs:
        (KB / f"{slug}.md").write_text(text, encoding="utf-8")
    idx = [
        "# Kho kiến thức wePRO — mục lục",
        "",
        "Mỗi tệp là một tài liệu gốc. Ảnh chụp đã được chép thành chữ (không lưu ảnh). Thuật ngữ: [glossary.md](glossary.md).",
        'Bản tóm tắt ngắn "bản tin nội bộ" và "wePRO – AI" của đợt 1 đã được thay bằng bản chi tiết của đợt 2.',
        "",
        "| Tài liệu | Phạm vi |",
        "|---|---|",
    ] + [f"| [{title}]({slug}.md) | {cover} |" for slug, title, cover, _ in docs]
    idx += ["", f"## Bài đăng đã bỏ vì trùng ({len(dropped)})", ""] + [f"- {d}" for d in dropped]
    (KB / "INDEX.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    print(f"{len(docs)} documents; {len(dropped)} duplicate posts dropped")


if __name__ == "__main__":
    main()
