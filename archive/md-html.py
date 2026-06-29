#!/usr/bin/env python3
"""
Enhanced Obsidian to HTML converter that preserves frontmatter,
callouts, internal links, tags, and applies beautiful styling.
"""

import re
import yaml
import markdown
from pathlib import Path
import argparse
from datetime import datetime


def parse_frontmatter(content):
    """Extract YAML frontmatter from markdown content."""
    frontmatter = {}
    body = content
    
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1])
                body = parts[2].strip()
            except yaml.YAMLError:
                pass
    
    return frontmatter, body


def convert_obsidian_links(text):
    """Convert [[wiki links]] to HTML links."""
    # Internal links: [[Page]] or [[Page|Display Text]]
    text = re.sub(
        r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]',
        lambda m: f'<a href="#{m.group(1).lower().replace(" ", "-")}" class="internal-link">{m.group(2) or m.group(1)}</a>',
        text
    )
    return text


def convert_obsidian_callouts(text):
    """Convert Obsidian callouts to HTML."""
    callout_pattern = r'> \[!(\w+)\]([+-]?)\s*(.*?)\n((?:>.*?\n)*)'
    
    def replace_callout(match):
        callout_type = match.group(1).lower()
        fold = match.group(2)
        title = match.group(3) or callout_type.capitalize()
        content = match.group(4).replace('> ', '').strip()
        
        return f'''<div class="callout callout-{callout_type}">
    <div class="callout-title">{title}</div>
    <div class="callout-content">{content}</div>
</div>'''
    
    return re.sub(callout_pattern, replace_callout, text, flags=re.MULTILINE)


def convert_tags(text):
    """Convert #tags to styled spans."""
    return re.sub(
        r'(?<!\w)#([\w/-]+)',
        r'<span class="tag">#\1</span>',
        text
    )


def generate_html(frontmatter, body, title):
    """Generate complete HTML document with styling."""
    
    # Process Obsidian-specific syntax
    body = convert_obsidian_callouts(body)
    body = convert_obsidian_links(body)
    body = convert_tags(body)
    
    # Convert markdown to HTML
    md = markdown.Markdown(extensions=['extra', 'codehilite', 'toc', 'tables'])
    html_body = md.convert(body)
    
    # Build frontmatter display
    fm_html = ""
    if frontmatter:
        fm_items = []
        for key, value in frontmatter.items():
            if isinstance(value, list):
                value = ', '.join(str(v) for v in value)
            fm_items.append(f'<div class="fm-item"><strong>{key}:</strong> {value}</div>')
        fm_html = f'<div class="frontmatter">{"".join(fm_items)}</div>'
    
    page_title = frontmatter.get('title', title)
    
    html_template = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <style>
        :root {{
            --bg-primary: #1e1e1e;
            --bg-secondary: #2d2d2d;
            --text-primary: #dcddde;
            --text-secondary: #b9bbbe;
            --accent: #7c3aed;
            --accent-hover: #9333ea;
            --callout-note: #3b82f6;
            --callout-warning: #f59e0b;
            --callout-tip: #10b981;
            --callout-important: #ef4444;
            --callout-info: #06b6d4;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif;
            line-height: 1.6;
            color: var(--text-primary);
            background: var(--bg-primary);
            padding: 20px;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: var(--bg-secondary);
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }}
        
        h1 {{
            color: var(--accent);
            font-size: 2.5em;
            margin-bottom: 20px;
            border-bottom: 3px solid var(--accent);
            padding-bottom: 10px;
        }}
        
        h2 {{
            color: var(--text-primary);
            font-size: 1.8em;
            margin-top: 30px;
            margin-bottom: 15px;
            border-left: 4px solid var(--accent);
            padding-left: 15px;
        }}
        
        h3 {{
            color: var(--text-secondary);
            font-size: 1.4em;
            margin-top: 25px;
            margin-bottom: 12px;
        }}
        
        .frontmatter {{
            background: rgba(124, 58, 237, 0.1);
            border-left: 4px solid var(--accent);
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 6px;
            font-size: 0.95em;
        }}
        
        .fm-item {{
            margin: 8px 0;
            color: var(--text-secondary);
        }}
        
        .fm-item strong {{
            color: var(--accent);
            margin-right: 8px;
        }}
        
        .callout {{
            margin: 20px 0;
            padding: 16px;
            border-radius: 8px;
            border-left: 4px solid;
        }}
        
        .callout-note {{
            background: rgba(59, 130, 246, 0.1);
            border-color: var(--callout-note);
        }}
        
        .callout-warning {{
            background: rgba(245, 158, 11, 0.1);
            border-color: var(--callout-warning);
        }}
        
        .callout-tip {{
            background: rgba(16, 185, 129, 0.1);
            border-color: var(--callout-tip);
        }}
        
        .callout-important {{
            background: rgba(239, 68, 68, 0.1);
            border-color: var(--callout-important);
        }}
        
        .callout-info {{
            background: rgba(6, 182, 212, 0.1);
            border-color: var(--callout-info);
        }}
        
        .callout-title {{
            font-weight: 700;
            margin-bottom: 8px;
            text-transform: uppercase;
            font-size: 0.9em;
            letter-spacing: 0.5px;
        }}
        
        .internal-link {{
            color: var(--accent);
            text-decoration: none;
            border-bottom: 1px dashed var(--accent);
            transition: all 0.2s;
        }}
        
        .internal-link:hover {{
            color: var(--accent-hover);
            border-bottom-style: solid;
        }}
        
        .tag {{
            background: rgba(124, 58, 237, 0.2);
            color: var(--accent);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.9em;
            font-weight: 500;
        }}
        
        code {{
            background: rgba(0, 0, 0, 0.3);
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
            color: #f472b6;
        }}
        
        pre {{
            background: rgba(0, 0, 0, 0.5);
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 20px 0;
        }}
        
        pre code {{
            background: none;
            padding: 0;
            color: var(--text-primary);
        }}
        
        a {{
            color: var(--accent);
            transition: color 0.2s;
        }}
        
        a:hover {{
            color: var(--accent-hover);
        }}
        
        blockquote {{
            border-left: 4px solid var(--accent);
            padding-left: 20px;
            margin: 20px 0;
            color: var(--text-secondary);
            font-style: italic;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        th {{
            background: rgba(124, 58, 237, 0.2);
            color: var(--accent);
            font-weight: 600;
        }}
        
        ul, ol {{
            margin: 15px 0;
            padding-left: 30px;
        }}
        
        li {{
            margin: 8px 0;
        }}
        
        img {{
            max-width: 100%;
            border-radius: 8px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{page_title}</h1>
        {fm_html}
        {html_body}
    </div>
</body>
</html>'''
    
    return html_template


def main():
    parser = argparse.ArgumentParser(
        description='Convert Obsidian markdown to rich HTML with preserved formatting'
    )
    parser.add_argument('input', help='Input markdown file path')
    parser.add_argument('-o', '--output', help='Output HTML file path')
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"Error: File '{input_path}' not found")
        return
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix('.html')
    
    # Read and process the markdown file
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    frontmatter, body = parse_frontmatter(content)
    html = generate_html(frontmatter, body, input_path.stem)
    
    # Write HTML output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✓ Converted '{input_path}' to '{output_path}'")


if __name__ == '__main__':
    main()
