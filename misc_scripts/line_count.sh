#!/bin/bash

# Check if a directory is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

# The directory to search in
search_dir="$1"

# Find all .py, .html, and .js files and count their lines
total_lines=$(find "$search_dir" \( -name "*.py" -o -name "*.html" -o -name "*.js" \) -type f -print0 | xargs -0 wc -l | awk '{total += $1} END {print total}')

echo "Total number of lines in Python, HTML, and JavaScript files: $total_lines"

# Count lines for each file type separately
python_lines=$(find "$search_dir" -name "*.py" -type f -print0 | xargs -0 wc -l | awk '{total += $1} END {print total}')
html_lines=$(find "$search_dir" -name "*.html" -type f -print0 | xargs -0 wc -l | awk '{total += $1} END {print total}')
js_lines=$(find "$search_dir" -name "*.js" -type f -print0 | xargs -0 wc -l | awk '{total += $1} END {print total}')

echo "Breakdown:"
echo "Python files: $python_lines lines"
echo "HTML files: $html_lines lines"
echo "JavaScript files: $js_lines lines"