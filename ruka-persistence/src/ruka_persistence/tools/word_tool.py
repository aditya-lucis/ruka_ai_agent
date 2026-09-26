from pathlib import Path
import docx

class WordTool:
    def read_paragraphs(self, path: str | Path) -> list[str]:
        doc = docx.Document(path)
        return [p.text for p in doc.paragraphs if p.text.strip()]
