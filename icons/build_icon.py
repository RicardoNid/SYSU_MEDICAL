import os
import os.path as osp

def change_color(svg_path):
    with open(svg_path, 'r+') as icon:
        content = icon.read()
        new_content = content.replace('#FFFFFF', '#000000')
        icon.seek(0)
        icon.truncate()
        icon.write(new_content)

for file in [file for file in os.listdir(os.curdir) if file.endswith('.svg')]:
    print(osp.join(os.curdir, file))
    change_color(osp.join(os.curdir, file))
