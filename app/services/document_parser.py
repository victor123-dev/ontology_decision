import os
from typing import Union
from PyPDF2 import PdfReader
from docx import Document

class DocumentParser:
    """文档解析服务"""
    
    def parse(self, file_path: str) -> str:
        """解析文档并返回文本内容"""
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            return self._parse_pdf(file_path)
        elif file_extension == '.docx':
            return self._parse_docx(file_path)
        elif file_extension == '.txt':
            return self._parse_txt(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_extension}")
    
    def _parse_pdf(self, file_path: str) -> str:
        """解析PDF文件"""
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    
    def _parse_docx(self, file_path: str) -> str:
        """解析Word文档"""
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    
    def _parse_txt(self, file_path: str) -> str:
        """解析文本文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()