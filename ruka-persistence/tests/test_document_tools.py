import pytest
from ruka_persistence.tools.excel_tool import ExcelTool
from ruka_persistence.tools.word_tool import WordTool
from ruka_persistence.tools.pdf_tool import PdfTool

# We will just verify imports and instantiation to ensure structure is correct.
# In a real offline test, we would generate mock excel/word/pdf files.
def test_tools_instantiation():
    assert ExcelTool() is not None
    assert WordTool() is not None
    assert PdfTool() is not None
