from PIL import Image, ImageDraw
import os


def create_icon(size, color, output_path):
    """创建简单的圆形图标"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 绘制圆形背景
    draw.ellipse([0, 0, size, size], fill=color)

    # 绘制用户图标（简单示例）
    if size >= 192:
        # 在较大图标上绘制更详细的图形
        draw.ellipse([size // 4, size // 4, 3 * size // 4, 3 * size // 4], fill=(255, 255, 255))

    img.save(output_path)
    print(f"创建图标: {output_path} ({size}x{size})")


# 确保public目录存在
os.makedirs('public', exist_ok=True)

# 创建不同尺寸的图标
icon_sizes = [(16, (102, 126, 234)), (32, (102, 126, 234)),
              (64, (102, 126, 234)), (128, (102, 126, 234)),
              (192, (102, 126, 234)), (512, (102, 126, 234))]

for size, color in icon_sizes:
    if size == 16:
        filename = 'public/favicon.ico'
    elif size == 192:
        filename = 'public/logo192.png'
    elif size == 512:
        filename = 'public/logo512.png'
    else:
        continue

    create_icon(size, color, filename)