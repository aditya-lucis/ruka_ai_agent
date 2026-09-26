from pathlib import Path
import pypdf

class PdfTool:
    def extract_text(self, path: str | Path) -> str:
        reader = pypdf.PdfReader(path)
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t: text += t + "\n"
        return text
