"""PDF report generator with Cyrillic support via fpdf2 + DejaVuSans."""

import os
import uuid
from fpdf import FPDF

FONTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "fonts")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reports")


class ReportPDF:
    def __init__(self, title: str):
        self.pdf = FPDF()
        self.pdf.set_auto_page_break(auto=True, margin=20)

        arial_path = os.path.join(FONTS_DIR, "ArialUnicode.ttf")

        if os.path.exists(arial_path):
            self.pdf.add_font("ArialUni", "", arial_path, uni=True)
            self.pdf.add_font("ArialUni", "B", arial_path, uni=True)
            self.font = "ArialUni"
        else:
            self.font = "Helvetica"

        self.title = title

    def add_title_page(self, subtitle: str = "", date: str = "", prepared_by: str = "MWS AI"):
        self.pdf.add_page()
        self.pdf.set_font(self.font, "B", 24)
        self.pdf.ln(40)
        self.pdf.cell(0, 15, self.title, ln=True, align="C")
        if subtitle:
            self.pdf.set_font(self.font, "", 14)
            self.pdf.cell(0, 10, subtitle, ln=True, align="C")
        self.pdf.ln(20)
        self.pdf.set_draw_color(59, 130, 246)
        self.pdf.line(60, self.pdf.get_y(), 150, self.pdf.get_y())
        self.pdf.ln(15)
        self.pdf.set_font(self.font, "", 11)
        self.pdf.set_text_color(100, 100, 100)
        if date:
            self.pdf.cell(0, 8, date, ln=True, align="C")
        self.pdf.cell(0, 8, f"Подготовлено: {prepared_by}", ln=True, align="C")
        self.pdf.cell(0, 8, "Конфиденциально", ln=True, align="C")
        self.pdf.set_text_color(0, 0, 0)

    def add_section(self, heading: str, text: str):
        self.pdf.set_font(self.font, "B", 14)
        self.pdf.set_text_color(26, 43, 74)
        self.pdf.ln(5)
        self.pdf.cell(0, 10, heading, ln=True)
        self.pdf.set_draw_color(59, 130, 246)
        self.pdf.line(10, self.pdf.get_y(), 60, self.pdf.get_y())
        self.pdf.ln(3)
        self.pdf.set_font(self.font, "", 10)
        self.pdf.set_text_color(30, 41, 59)
        self.pdf.multi_cell(0, 6, text)
        self.pdf.ln(3)

    def add_bullet_list(self, items: list[str]):
        self.pdf.set_font(self.font, "", 10)
        self.pdf.set_text_color(30, 41, 59)
        for item in items:
            self.pdf.cell(5)
            self.pdf.cell(5, 6, chr(8226))
            self.pdf.multi_cell(0, 6, f" {item}")
        self.pdf.ln(3)

    def add_metrics_box(self, metrics: dict[str, str]):
        self.pdf.set_fill_color(240, 244, 248)
        self.pdf.set_draw_color(59, 130, 246)
        y_start = self.pdf.get_y()
        self.pdf.rect(10, y_start, 190, 8 + len(metrics) * 8, style="DF")
        self.pdf.ln(4)
        for key, val in metrics.items():
            self.pdf.set_font(self.font, "B", 10)
            self.pdf.cell(60, 7, f"  {key}:", ln=False)
            self.pdf.set_font(self.font, "", 10)
            self.pdf.cell(0, 7, str(val), ln=True)
        self.pdf.ln(5)

    def add_table(self, headers: list[str], rows: list[list[str]]):
        n_cols = len(headers)
        col_w = 190 / n_cols

        self.pdf.set_font(self.font, "B", 9)
        self.pdf.set_fill_color(26, 43, 74)
        self.pdf.set_text_color(255, 255, 255)
        for h in headers:
            self.pdf.cell(col_w, 8, h, border=1, align="C", fill=True)
        self.pdf.ln()

        self.pdf.set_font(self.font, "", 9)
        self.pdf.set_text_color(30, 41, 59)
        for i, row in enumerate(rows):
            if i % 2 == 0:
                self.pdf.set_fill_color(240, 244, 248)
            else:
                self.pdf.set_fill_color(255, 255, 255)
            for cell_val in row:
                self.pdf.cell(col_w, 7, str(cell_val), border=1, align="C", fill=True)
            self.pdf.ln()
        self.pdf.ln(5)

    def add_risk_flags(self, flags: list[dict]):
        self.pdf.set_font(self.font, "B", 12)
        self.pdf.set_text_color(239, 68, 68)
        self.pdf.cell(0, 10, "Выявленные флаги", ln=True)
        self.pdf.set_text_color(30, 41, 59)

        for flag in flags:
            severity_icon = "!!!" if flag.get("severity") == "high" else "!!" if flag.get("severity") == "medium" else "OK"
            self.pdf.set_font(self.font, "B", 10)
            self.pdf.cell(0, 7, f"[{severity_icon}] {flag['parameter']}", ln=True)
            self.pdf.set_font(self.font, "", 9)
            self.pdf.cell(0, 6, f"  Проект: {flag['project_value']}  |  Рынок: {flag['market_range']}", ln=True)
            self.pdf.multi_cell(0, 5, f"  {flag['comment']}")
            self.pdf.ln(3)

    def add_footer(self):
        self.pdf.set_y(-20)
        self.pdf.set_font(self.font, "", 8)
        self.pdf.set_text_color(150, 150, 150)
        self.pdf.cell(0, 8, "Corporate Copilot Hub | MWS AI | Конфиденциально", align="C")

    def save(self) -> tuple[str, str]:
        """Save PDF and return (report_id, file_path)."""
        os.makedirs(REPORTS_DIR, exist_ok=True)
        report_id = str(uuid.uuid4())[:8]
        path = os.path.join(REPORTS_DIR, f"{report_id}.pdf")
        self.pdf.output(path)
        return report_id, path
