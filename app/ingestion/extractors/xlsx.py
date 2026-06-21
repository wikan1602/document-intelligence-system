import io

from openpyxl import load_workbook

from app.ingestion.extractors.base import BaseExtractor, ExtractedChunk

ROWS_PER_CHUNK = 50  # grouping per N baris


class XLSXExtractor(BaseExtractor):
    """
    Ekstrak konten XLSX per sheet, dikelompokkan setiap ROWS_PER_CHUNK baris.
    Menyimpan sheet_name dan row_range untuk source tracing.
    """

    def extract(self, file_bytes: bytes, filename: str) -> list[ExtractedChunk]:
        wb = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        chunks: list[ExtractedChunk] = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows_data: list[str] = []
            row_num = 0

            for row in ws.iter_rows(values_only=True):
                row_num += 1
                cell_texts = [str(c) for c in row if c is not None]
                if cell_texts:
                    rows_data.append(" | ".join(cell_texts))

                # Flush setiap ROWS_PER_CHUNK baris
                if len(rows_data) >= ROWS_PER_CHUNK:
                    start = row_num - len(rows_data) + 1
                    end = row_num
                    chunks.append(
                        ExtractedChunk(
                            text="\n".join(rows_data),
                            sheet_name=sheet_name,
                            row_range=f"{start}-{end}",
                            metadata={"filename": filename},
                        )
                    )
                    rows_data = []

            # Flush sisa baris
            if rows_data:
                start = row_num - len(rows_data) + 1
                chunks.append(
                    ExtractedChunk(
                        text="\n".join(rows_data),
                        sheet_name=sheet_name,
                        row_range=f"{start}-{row_num}",
                        metadata={"filename": filename},
                    )
                )

        wb.close()
        return chunks
