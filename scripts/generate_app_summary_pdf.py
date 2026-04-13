from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepInFrame,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf"
OUTPUT_PATH = OUTPUT_DIR / "bay_delivery_quote_copilot_one_page_summary.pdf"


def _styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TitleBar",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=24,
            textColor=colors.white,
            alignment=TA_LEFT,
            spaceAfter=0,
        ),
        "subtitle": ParagraphStyle(
            "SubtitleBar",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=11,
            textColor=colors.HexColor("#E8EEF2"),
            alignment=TA_LEFT,
            spaceAfter=0,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11.2,
            leading=12.5,
            textColor=colors.HexColor("#12344D"),
            spaceBefore=0,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.7,
            leading=11,
            textColor=colors.HexColor("#1F2D3D"),
            spaceBefore=0,
            spaceAfter=3,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.6,
            leading=9.2,
            textColor=colors.HexColor("#4A6572"),
            spaceBefore=0,
            spaceAfter=0,
        ),
        "bullet": ParagraphStyle(
            "BulletBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=10.5,
            textColor=colors.HexColor("#1F2D3D"),
            leftIndent=0,
            firstLineIndent=0,
            spaceBefore=0,
            spaceAfter=0,
        ),
        "code": ParagraphStyle(
            "CodeBody",
            parent=styles["BodyText"],
            fontName="Courier",
            fontSize=7.4,
            leading=8.8,
            textColor=colors.HexColor("#263238"),
            spaceBefore=0,
            spaceAfter=0,
        ),
    }


def _bullet_paragraphs(items: list[str], style: ParagraphStyle) -> list[Paragraph]:
    return [
        Paragraph(
            item,
            ParagraphStyle(
                f"{style.name}Bullet",
                parent=style,
                leftIndent=13,
                firstLineIndent=0,
                bulletIndent=3,
                spaceBefore=0,
                spaceAfter=2,
            ),
            bulletText="•",
        )
        for item in items
    ]


def _left_column(styles: dict[str, ParagraphStyle]):
    return [
        Paragraph("What It Is", styles["section"]),
        Paragraph(
            "Bay Delivery Quote Copilot is a FastAPI web app for Bay Delivery in North Bay, Ontario. "
            "It combines public quote intake with internal ops tools for approvals, job handling, uploads, and backups.",
            styles["body"],
        ),
        Spacer(1, 5),
        Paragraph("Who It’s For", styles["section"]),
        Paragraph(
            "Primary persona (inferred from repo evidence): a Bay Delivery operator/dispatcher managing accepted quotes, "
            "job approvals, scheduling, and admin review. Customers also use the public quote flow.",
            styles["body"],
        ),
        Spacer(1, 5),
        Paragraph("What It Does", styles["section"]),
        *_bullet_paragraphs(
            [
                "Serves a public homepage and quote form at <font name='Courier'>/</font> and <font name='Courier'>/quote</font>.",
                "Calculates estimates for haul-away, scrap pickup, small move, item delivery, and demolition using config-backed pricing rules.",
                "Captures customer accept/decline decisions, then collects preferred booking date, time window, and notes.",
                "Lets customers upload up to 5 job photos; uploads go to Google Drive when configured, with OCR attempted via local Tesseract.",
                "Provides admin screens for quotes, quote requests, jobs, uploads, audit history, and a mobile admin view.",
                "Schedules, reschedules, starts, completes, and cancels jobs; Google Calendar sync is a mirror, not the source of truth.",
                "Supports JSON DB export/import, Drive snapshots/restores, security headers, rate limits, and Basic Auth for admin APIs.",
            ],
            styles["bullet"],
        ),
    ]


def _right_column(styles: dict[str, ParagraphStyle]):
    return [
        Paragraph("How It Works", styles["section"]),
        *_bullet_paragraphs(
            [
                "<b>UI + API:</b> <font name='Courier'>app/main.py</font> serves static HTML/CSS/JS from <font name='Courier'>static/</font> and exposes quote, booking, upload, admin, backup, and audit endpoints.",
                "<b>Pricing path:</b> quote requests flow through <font name='Courier'>app/services/quote_service.py</font> into <font name='Courier'>app/quote_engine.py</font>, which reads rules from <font name='Courier'>config/business_profile.json</font>.",
                "<b>Persistence:</b> <font name='Courier'>app/storage.py</font> writes quotes, quote_requests, jobs, attachments, screenshot_assistant_analyses, and admin_audit_log to SQLite at <font name='Courier'>app/data/bay_delivery.sqlite3</font> unless <font name='Courier'>BAYDELIVERY_DB_PATH</font> overrides it.",
                "<b>Workflow:</b> customer acceptance creates a quote request; admin approval creates a job via <font name='Courier'>booking_service</font>; <font name='Courier'>job_scheduling_service</font> writes DB state first, then mirrors schedule changes to Google Calendar.",
                "<b>Optional integrations:</b> <font name='Courier'>app/gdrive.py</font> handles Drive uploads and backups; <font name='Courier'>app/services/screenshot_assistant_service.py</font> combines OCR/text extraction with existing pricing logic for read-only guidance.",
                "<b>Deployment evidence:</b> <font name='Courier'>render.yaml</font> defines a Render web service running <font name='Courier'>uvicorn app.main:app</font> with a persistent disk mounted at <font name='Courier'>/var/data</font>.",
            ],
            styles["bullet"],
        ),
        Spacer(1, 6),
        Paragraph("How To Run", styles["section"]),
        *_bullet_paragraphs(
            [
                "<font name='Courier'>py -3.11 -m venv .venv</font>",
                "<font name='Courier'>.\\.venv\\Scripts\\Activate.ps1</font>",
                "<font name='Courier'>python -m pip install --upgrade pip</font>",
                "<font name='Courier'>pip install -r requirements.txt</font>",
                "<font name='Courier'>uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload</font>",
                "Open <font name='Courier'>http://127.0.0.1:8000/</font>. Optional admin credentials are present in repo root <font name='Courier'>.env</font>; Google Drive/Calendar env setup steps are <b>Not found in repo</b> as a single local run guide.",
            ],
            styles["code"],
        ),
        Spacer(1, 8),
        Paragraph(
            "Evidence used: README.md, render.yaml, app/main.py, app/storage.py, app/services/*.py, "
            "app/gdrive.py, app/gcalendar.py, config/business_profile.json, static/*.html, scripts/smoke_test.py.",
            styles["small"],
        ),
    ]


def _draw_page(canvas, doc):
    page_width, page_height = landscape(letter)
    margin_x = 0.55 * inch
    title_h = 0.95 * inch
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#163B50"))
    canvas.rect(0, page_height - title_h, page_width, title_h, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 22)
    canvas.drawString(margin_x, page_height - 0.42 * inch, "Bay Delivery Quote Copilot")
    canvas.setFont("Helvetica", 9.2)
    canvas.setFillColor(colors.HexColor("#E8EEF2"))
    canvas.drawString(
        margin_x,
        page_height - 0.68 * inch,
        "One-page repo-based app summary generated from code, config, static assets, and deployment files.",
    )
    canvas.restoreState()


def build_pdf() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    styles = _styles()
    page_width, page_height = landscape(letter)
    margin = 0.55 * inch
    gap = 0.34 * inch
    title_h = 0.95 * inch
    usable_top = page_height - title_h - margin + 0.05 * inch
    col_width = (page_width - (margin * 2) - gap) / 2
    col_height = usable_top - margin

    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=landscape(letter),
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )

    left_story = _left_column(styles)
    right_story = _right_column(styles)

    def draw(canvas, doc):
        _draw_page(canvas, doc)
        x_left = margin
        x_right = margin + col_width + gap
        y = margin

        for x in (x_left, x_right):
            canvas.saveState()
            canvas.setFillColor(colors.HexColor("#F7FAFC"))
            canvas.roundRect(x, y, col_width, col_height, 10, stroke=0, fill=1)
            canvas.setStrokeColor(colors.HexColor("#D7E3EA"))
            canvas.roundRect(x, y, col_width, col_height, 10, stroke=1, fill=0)
            canvas.restoreState()

        left_frame = KeepInFrame(col_width - 18, col_height - 18, left_story, mode="shrink")
        right_frame = KeepInFrame(col_width - 18, col_height - 18, right_story, mode="shrink")

        left_w, left_h = left_frame.wrapOn(canvas, col_width - 18, col_height - 18)
        right_w, right_h = right_frame.wrapOn(canvas, col_width - 18, col_height - 18)

        left_frame.drawOn(canvas, x_left + 9, y + col_height - 9 - left_h)
        right_frame.drawOn(canvas, x_right + 9, y + col_height - 9 - right_h)

    doc.build([Spacer(1, 1)], onFirstPage=draw)
    return OUTPUT_PATH


if __name__ == "__main__":
    path = build_pdf()
    print(path)
