import os
import uuid
import base64
from PIL import Image
from io import BytesIO


def save_upload_image(file_or_bytes, upload_dir, flow_id, step_order):
    """Save uploaded image file. Returns relative path from upload_dir."""
    flow_dir = os.path.join(upload_dir, str(flow_id))
    os.makedirs(flow_dir, exist_ok=True)

    filename = f"step_{step_order:02d}_{uuid.uuid4().hex[:8]}.png"
    filepath = os.path.join(flow_dir, filename)

    if hasattr(file_or_bytes, 'read'):
        # File-like object from Flask request
        img = Image.open(file_or_bytes)
    elif isinstance(file_or_bytes, bytes):
        img = Image.open(BytesIO(file_or_bytes))
    else:
        raise ValueError("Unsupported image input type")

    # Convert to RGB if needed (handles RGBA, palette, etc.)
    if img.mode in ('RGBA', 'P', 'LA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    img.save(filepath, 'PNG', optimize=True)
    # Return relative path: {flow_id}/{filename}
    return f"{flow_id}/{filename}"


def get_image_base64(upload_dir, image_path):
    """Read image file and return base64 encoded string."""
    full_path = os.path.join(upload_dir, image_path)
    if not os.path.exists(full_path):
        return None
    with open(full_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def compress_image_for_ai(upload_dir, image_path, max_width=1024):
    """Compress image for AI API call to reduce token cost."""
    full_path = os.path.join(upload_dir, image_path)
    if not os.path.exists(full_path):
        return None

    img = Image.open(full_path)
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)

    if img.mode != 'RGB':
        img = img.convert('RGB')

    buffer = BytesIO()
    img.save(buffer, format='JPEG', quality=80)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')
