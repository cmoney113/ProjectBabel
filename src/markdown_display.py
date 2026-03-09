"""
Markdown-enabled text display widget
Renders markdown in the response display
"""

from PySide6.QtWidgets import QTextEdit, QScrollArea, QWidget, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor, QColor, QPalette, QFont, QTextCharFormat, QTextBlockFormat


class MarkdownDisplay(QTextEdit):
    """
    A text edit widget that renders markdown content
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMarkdown("")
        self._setup_style()
    
    def _setup_style(self):
        """Setup the style for markdown rendering"""
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1a1f26;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 14px;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
                font-size: 15px;
                line-height: 1.6;
                selection-background-color: #238636;
                selection-color: #ffffff;
            }
            QTextEdit:hover {
                border-color: #484f58;
            }
            QTextEdit:focus {
                border-color: #58a6ff;
            }
        """)

        # Set the palette for dark theme
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor("#1a1f26"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#e6edf3"))
        self.setPalette(palette)
    
    def setMarkdown(self, markdown_text: str):
        """Set markdown content to display"""
        if not markdown_text:
            self.clear()
            return
        
        # Convert markdown to HTML
        html = self._markdown_to_html(markdown_text)
        
        # Set the HTML content
        self.setHtml(html)
        
        # Scroll to top
        self.moveCursor(QTextCursor.MoveOperation.Start)
    
    def _markdown_to_html(self, text: str) -> str:
        """Convert markdown text to styled HTML"""
        import re
        
        # Escape HTML first
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        
        # Process markdown patterns
        lines = text.split('\n')
        html_lines = []
        
        in_code_block = False
        in_list = False
        
        for line in lines:
            # Code blocks
            if line.strip().startswith('```'):
                if in_code_block:
                    html_lines.append('</code></pre>')
                    in_code_block = False
                else:
                    html_lines.append('<pre><code>')
                    in_code_block = True
                continue
            
            if in_code_block:
                html_lines.append(line)
                continue
            
            # Headers
            if line.startswith('### '):
                html_lines.append(f'<h3 style="color: #e6edf3; margin: 16px 0 8px 0;">{line[4:]}</h3>')
                continue
            elif line.startswith('## '):
                html_lines.append(f'<h2 style="color: #e6edf3; margin: 16px 0 8px 0;">{line[3:]}</h2>')
                continue
            elif line.startswith('# '):
                html_lines.append(f'<h1 style="color: #e6edf3; margin: 16px 0 8px 0;">{line[2:]}</h1>')
                continue
            
            # Bullet lists
            if line.strip().startswith('- ') or line.strip().startswith('* '):
                if not in_list:
                    html_lines.append('<ul style="margin: 8px 0; padding-left: 20px;">')
                    in_list = True
                html_lines.append(f'<li style="margin: 4px 0;">{line[2:]}</li>')
                continue
            elif line.strip().startswith('1. ') or line.strip().startswith('2. ') or line.strip().startswith('3. '):
                # Ordered lists - treat as regular text for simplicity
                html_lines.append(f'<p style="margin: 4px 0; padding-left: 20px;">{line}</p>')
                continue
            
            # End list
            if in_list and line.strip() and not line.strip().startswith(('- ', '* ')):
                html_lines.append('</ul>')
                in_list = False
            
            # Inline code
            line = re.sub(r'`([^`]+)`', r'<code style="background-color: #161b22; padding: 2px 6px; border-radius: 4px; font-family: monospace; color: #f0883e;">\1</code>', line)
            
            # Bold
            line = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', line)
            
            # Italic
            line = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', line)
            
            # Links
            line = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color: #58a6ff; text-decoration: none;">\1</a>', line)
            
            # Horizontal rule
            if line.strip() == '---' or line.strip() == '***':
                html_lines.append('<hr style="border: none; border-top: 1px solid #30363d; margin: 16px 0;">')
                continue
            
            # Empty line
            if not line.strip():
                html_lines.append('<br>')
                continue
            
            # Regular paragraph
            html_lines.append(f'<p style="margin: 8px 0;">{line}</p>')
        
        # Close any open list
        if in_list:
            html_lines.append('</ul>')
        
        return '\n'.join(html_lines)
    
    def append_markdown(self, text: str):
        """Append markdown content"""
        # Convert current content to markdown, append, then convert back
        current = self.toMarkdown()
        if current:
            current += "\n\n" + text
        else:
            current = text
        self.setMarkdown(current)


class ScrollableMarkdownDisplay(QScrollArea):
    """
    A scrollable container for MarkdownDisplay
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)

        self.markdown_widget = MarkdownDisplay()
        self.setWidget(self.markdown_widget)
        self.setWidgetResizable(True)
        self.setStyleSheet("""
            QScrollArea {
                background-color: #1a1f26;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
            QScrollArea:hover {
                border-color: #484f58;
            }
            QScrollBar:vertical {
                background-color: #1a1f26;
                width: 12px;
                border-radius: 6px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background-color: #30363d;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #484f58;
            }
            QScrollBar::handle:vertical:pressed {
                background-color: #58a6ff;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
    
    def setMarkdown(self, text: str):
        """Set markdown content"""
        self.markdown_widget.setMarkdown(text)
    
    def append_markdown(self, text: str):
        """Append markdown content"""
        self.markdown_widget.append_markdown(text)
    
    def clear(self):
        """Clear content"""
        self.markdown_widget.clear()

    def toPlainText(self):
        """Get plain text content"""
        return self.markdown_widget.toPlainText()

    def append(self, text: str):
        """Append text (for compatibility with QTextEdit API)"""
        self.markdown_widget.append_markdown(text)

    def verticalScrollBar(self):
        """Get vertical scroll bar"""
        return super().verticalScrollBar()
