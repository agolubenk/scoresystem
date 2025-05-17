import os
import re

def update_template_paths(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Обновляем extends
                content = re.sub(
                    r'{%\s*extends\s+[\'"]positions/base\.html[\'"]\s*%}',
                    '{% extends \'base.html\' %}',
                    content
                )
                
                # Обновляем include
                content = re.sub(
                    r'{%\s*include\s+[\'"]positions/([^\'"]+)[\'"]\s*%}',
                    r'{% include \'\1\' %}',
                    content
                )
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

if __name__ == '__main__':
    templates_dir = 'templates'
    update_template_paths(templates_dir) 