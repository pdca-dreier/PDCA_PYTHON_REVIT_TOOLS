import os
import textwrap
import tkinter as tk
from tkinter import filedialog, messagebox
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from openpyxl import Workbook
from datetime import datetime
from io import BytesIO

def select_folder():
    """Open a file dialog to select a folder containing PDF files."""
    root = tk.Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory()
    if not folder_selected:
        messagebox.showerror("Error", "No folder selected.")
        return None
    return folder_selected

def count_pages(pdf_path):
    """Count the number of pages in a PDF file."""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            return len(reader.pages)
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return None

def create_excel(toc, output_path):
    """Create an Excel file with PDF file names, their starting page in the combined PDF, and their page counts."""
    wb = Workbook()
    ws = wb.active
    ws.title = "PDF Table of Contents"
    ws.append(["PDF File Name", "Starting Page", "Number of Pages"])

    for entry in toc:
        ws.append([entry[0], entry[1], entry[2]])

    # Set column widths
    ws.column_dimensions['A'].width = 40
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 15

    wb.save(output_path)

def create_cover_page(title):
    """Create a cover page PDF with the given title."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    title = title.replace('.pdf', '')  # Remove file extension
    title_lines = textwrap.wrap(title, width=40)  # Wrap title text to maintain margins

    c.setFont("Helvetica", 36)
    y = height / 2 + (len(title_lines) * 18)  # Adjust starting y position based on number of lines
    for line in title_lines:
        text_width = c.stringWidth(line, "Helvetica", 36)
        c.drawString((width - text_width) / 2, y, line)
        y -= 36  # Move to next line position

    c.showPage()
    c.save()
    buffer.seek(0)
    return PdfReader(buffer)

def add_page_numbers(pdf_writer, output_path, folder_name):
    """Add page numbers to the PDF file."""
    buffer = BytesIO()
    temp_writer = PdfWriter()

    for i, page in enumerate(pdf_writer.pages):
        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=A4)
        can.setFont("Helvetica", 8)
        can.setFillColor(colors.darkblue)
        # Position the page number at the bottom right corner with prefix
        page_number_text = f"{folder_name}-{i + 1}"
        can.drawRightString(A4[0] - 10 * mm, 10 * mm, page_number_text)
        can.save()

        packet.seek(0)
        overlay = PdfReader(packet)
        page.merge_page(overlay.pages[0])
        temp_writer.add_page(page)

    with open(output_path, 'wb') as f:
        temp_writer.write(f)

def combine_pdfs(pdf_paths, output_path, folder_name):
    """Combine multiple PDF files into a single PDF and create a table of contents."""
    pdf_writer = PdfWriter()
    toc = []
    current_page = 1  # Start page numbering from 1

    for pdf in pdf_paths:
        try:
            # Create cover page
            title = os.path.basename(pdf)
            cover_reader = create_cover_page(title)
            pdf_writer.add_page(cover_reader.pages[0])
            current_page += 1

            with open(pdf, 'rb') as f:
                reader = PdfReader(f)
                num_pages = len(reader.pages)
                for page in reader.pages:
                    pdf_writer.add_page(page)
                toc.append((title.replace('.pdf', ''), current_page, num_pages))
                current_page += num_pages
        except Exception as e:
            print(f"Error processing {pdf}: {e}")

    add_page_numbers(pdf_writer, output_path, folder_name)

    return toc

def main():
    folder = select_folder()
    if not folder:
        return

    folder_name = os.path.basename(folder)
    current_date = datetime.now().strftime('%Y%m%d')

    pdf_files = [f for f in os.listdir(folder) if f.lower().endswith('.pdf')]
    if not pdf_files:
        messagebox.showerror("Error", "No PDF files found in the selected folder.")
        return

    pdf_files.sort()  # Sort PDF files by name

    pdf_paths = [os.path.join(folder, pdf) for pdf in pdf_files]

    combined_pdf_path = os.path.join(folder, f'{current_date}_{folder_name}.pdf')
    toc = combine_pdfs(pdf_paths, combined_pdf_path, folder_name)

    # Sort the table of contents by file name
    toc.sort()

    excel_output_path = os.path.join(folder, f'{current_date}_{folder_name}_Table_of_Content.xlsx')
    create_excel(toc, excel_output_path)

    print(f"PDF page counts and table of contents saved to {excel_output_path}")
    print(f"Combined PDF saved to {combined_pdf_path}")

if __name__ == "__main__":
    main()