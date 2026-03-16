"""PDF Generator for Value Proposition Canvas documents."""

from datetime import datetime
from io import BytesIO
from typing import List

from fpdf import FPDF


class CanvasPDFGenerator:
    """Generates PDF documents from Value Proposition Canvas data."""

    # Color scheme (matching document_generator.py)
    PRIMARY = (79, 70, 229)
    SUCCESS = (16, 185, 129)
    WARNING = (245, 158, 11)
    TEXT = (31, 41, 55)
    GRAY_400 = (156, 163, 175)
    GRAY_500 = (107, 114, 128)
    LIGHT_BG = (243, 244, 246)

    def generate(self, job_description: str, pain_points: List[str],
                 gain_points: List[str], title: str = "Value Proposition Canvas") -> BytesIO:
        """Generate a PDF document. Thread-safe: all state is local."""
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        # Title
        pdf.set_font("Helvetica", "B", 24)
        pdf.set_text_color(*self.PRIMARY)
        pdf.cell(0, 14, title, align="C", new_x="LMARGIN", new_y="NEXT")

        # Subtitle
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*self.GRAY_500)
        pdf.cell(0, 8, "Work Process Analysis", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(8)

        # Job Description section
        self._section_heading(pdf, "Job Description")
        pdf.set_font("Helvetica", "I", 11)
        pdf.set_text_color(*self.TEXT)
        pdf.set_x(15)
        pdf.multi_cell(0, 6, job_description, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)

        # Pain Points section
        self._section_heading(pdf, f"Pain Points ({len(pain_points)} identified)")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*self.GRAY_500)
        pdf.set_x(15)
        pdf.cell(0, 5, "Obstacles, frustrations, and risks in your work:", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        self._numbered_list(pdf, pain_points, self.WARNING)
        pdf.ln(4)

        # Gain Points section
        self._section_heading(pdf, f"Gain Points ({len(gain_points)} identified)")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*self.GRAY_500)
        pdf.set_x(15)
        pdf.cell(0, 5, "Outcomes and benefits you desire:", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        self._numbered_list(pdf, gain_points, self.SUCCESS)
        pdf.ln(6)

        # Summary
        self._section_heading(pdf, "Summary")
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*self.TEXT)
        pdf.set_x(15)
        summary = (
            f"This canvas captures your work profile with:\n"
            f"  - 1 clearly defined job description\n"
            f"  - {len(pain_points)} distinct pain points\n"
            f"  - {len(gain_points)} unique gain points"
        )
        pdf.multi_cell(0, 6, summary, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(10)

        # Footer
        self._footer(pdf)

        buffer = BytesIO()
        pdf.output(buffer)
        buffer.seek(0)
        return buffer

    def _section_heading(self, pdf: FPDF, text: str):
        """Add a section heading."""
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*self.PRIMARY)
        pdf.set_x(10)
        pdf.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    def _numbered_list(self, pdf: FPDF, items: List[str], number_color: tuple):
        """Add a numbered list of items."""
        for i, item in enumerate(items, 1):
            pdf.set_x(15)
            # Number
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*number_color)
            num_text = f"{i}. "
            pdf.cell(pdf.get_string_width(num_text) + 1, 6, num_text)
            # Text
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*self.TEXT)
            # Calculate remaining width for multi_cell
            remaining_width = pdf.w - pdf.get_x() - pdf.r_margin
            pdf.multi_cell(remaining_width, 6, item, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

    def _footer(self, pdf: FPDF):
        """Add footer with timestamp."""
        pdf.set_draw_color(*self.GRAY_400)
        pdf.line(20, pdf.get_y(), pdf.w - 20, pdf.get_y())
        pdf.ln(4)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*self.GRAY_400)
        date_str = datetime.now().strftime("%B %d, %Y at %H:%M")
        pdf.cell(0, 5, f"Generated on {date_str}", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 5, "Work Process Reflection Canvas", align="C", new_x="LMARGIN", new_y="NEXT")
