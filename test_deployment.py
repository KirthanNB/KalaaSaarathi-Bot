# test_links.py
import os

# Check what links are currently in index.html
with open('out/index.html', 'r') as f:
    content = f.read()
    
# Count product links with and without .html
html_links = content.count('/product/') - content.count('/product/.html')
no_html_links = content.count('href="/product/') - content.count('.html')

print(f"Product links with .html: {html_links}")
print(f"Product links without .html: {no_html_links}")

# Check if target="_blank" exists
target_blank_count = content.count('target="_blank"')
print(f"target='_blank' links: {target_blank_count}")