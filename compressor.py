"""
Bill Compressor - Compresses PDF/PNG files to max 200KB and creates a ZIP.
No external dependencies required (no Poppler/Ghostscript).
"""

import os
import io
import zipfile
import tempfile
import shutil
from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter

MAX_SIZE_KB = 200
MAX_SIZE_BYTES = MAX_SIZE_KB * 1024


def compress_image_data(
    image_data: bytes,
    target_size: int,
    min_quality: int = 25
) -> bytes:
    """Compress image bytes to target size."""
    try:
        img = Image.open(io.BytesIO(image_data))
    except Exception:
        return image_data
    
    if img.mode == 'RGBA':
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')
    
    quality = 80
    scale = 1.0
    best_result = image_data
    
    while quality >= min_quality and scale >= 0.3:
        if scale < 1.0:
            new_size = (max(1, int(img.width * scale)), 
                        max(1, int(img.height * scale)))
            resized = img.resize(new_size, Image.Resampling.LANCZOS)
        else:
            resized = img
        
        buffer = io.BytesIO()
        resized.save(buffer, format='JPEG', quality=quality, optimize=True)
        result = buffer.getvalue()
        best_result = result
        
        if len(result) <= target_size:
            return result
        
        if quality > 40:
            quality -= 10
        else:
            quality -= 5
            scale -= 0.1
    
    return best_result


def compress_image_file(input_path: str, output_path: str) -> bool:
    """Compress PNG/JPG file to target size."""
    with open(input_path, 'rb') as f:
        data = f.read()
    
    compressed = compress_image_data(data, MAX_SIZE_BYTES)
    
    with open(output_path, 'wb') as f:
        f.write(compressed)
    
    return len(compressed) <= MAX_SIZE_BYTES


def extract_and_compress_pdf_images(reader: PdfReader, target_total: int) -> dict:
    """Extract images from PDF, compress them, return mapping."""
    images_info = []
    
    for page_num, page in enumerate(reader.pages):
        if '/XObject' not in page.get('/Resources', {}):
            continue
        
        xobjects = page['/Resources']['/XObject'].get_object()
        
        for obj_name in xobjects:
            xobj = xobjects[obj_name]
            if xobj.get('/Subtype') == '/Image':
                try:
                    width = int(xobj.get('/Width', 0))
                    height = int(xobj.get('/Height', 0))
                    
                    if width > 0 and height > 0:
                        data = xobj.get_data()
                        images_info.append({
                            'page': page_num,
                            'name': obj_name,
                            'data': data,
                            'size': len(data),
                            'width': width,
                            'height': height
                        })
                except Exception:
                    continue
    
    if not images_info:
        return {}
    
    total_image_size = sum(img['size'] for img in images_info)
    
    if total_image_size <= target_total:
        return {}
    
    compressed_images = {}
    target_per_image = target_total // len(images_info)
    target_per_image = max(target_per_image, 10 * 1024)
    
    for img_info in images_info:
        compressed = compress_image_data(
            img_info['data'],
            target_per_image,
            min_quality=20
        )
        
        key = (img_info['page'], img_info['name'])
        compressed_images[key] = compressed
    
    return compressed_images


def compress_pdf(input_path: str, output_path: str) -> bool:
    """Compress PDF by compressing streams and embedded images."""
    original_size = os.path.getsize(input_path)
    
    if original_size <= MAX_SIZE_BYTES:
        shutil.copy(input_path, output_path)
        return True
    
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        
        for page in reader.pages:
            page.compress_content_streams()
            writer.add_page(page)
        
        writer.add_metadata(reader.metadata or {})
        
        buffer = io.BytesIO()
        writer.write(buffer)
        
        if buffer.tell() <= MAX_SIZE_BYTES:
            with open(output_path, 'wb') as f:
                f.write(buffer.getvalue())
            return True
        
        reader2 = PdfReader(input_path)
        writer2 = PdfWriter()
        
        target_image_size = MAX_SIZE_BYTES - 20 * 1024
        compressed_images = extract_and_compress_pdf_images(reader2, target_image_size)
        
        for page_num, page in enumerate(reader2.pages):
            if '/XObject' in page.get('/Resources', {}):
                xobjects = page['/Resources']['/XObject'].get_object()
                
                for obj_name in xobjects:
                    key = (page_num, obj_name)
                    if key in compressed_images:
                        try:
                            xobj = xobjects[obj_name].get_object()
                            
                            new_img = Image.open(io.BytesIO(compressed_images[key]))
                            
                            img_buffer = io.BytesIO()
                            new_img.save(img_buffer, format='JPEG', quality=50)
                            
                        except Exception:
                            pass
            
            page.compress_content_streams()
            writer2.add_page(page)
        
        buffer2 = io.BytesIO()
        writer2.write(buffer2)
        
        with open(output_path, 'wb') as f:
            f.write(buffer2.getvalue())
        
        final_size = os.path.getsize(output_path)
        
        if final_size > MAX_SIZE_BYTES and final_size > original_size * 0.5:
            with open(output_path, 'wb') as f:
                f.write(buffer.getvalue())
        
        return os.path.getsize(output_path) <= MAX_SIZE_BYTES
        
    except Exception as e:
        shutil.copy(input_path, output_path)
        return os.path.getsize(output_path) <= MAX_SIZE_BYTES


def compress_file(input_path: str, output_dir: str) -> tuple[str, bool, int]:
    """
    Compress a single file.
    Returns: (output_path, success, final_size_kb)
    """
    path = Path(input_path)
    ext = path.suffix.lower()
    
    if ext == '.pdf':
        output_path = os.path.join(output_dir, path.stem + '.pdf')
        success = compress_pdf(input_path, output_path)
    elif ext in ('.png', '.jpg', '.jpeg'):
        output_path = os.path.join(output_dir, path.stem + '.jpg')
        success = compress_image_file(input_path, output_path)
    else:
        return ('', False, 0)
    
    if os.path.exists(output_path):
        final_size = os.path.getsize(output_path) // 1024
    else:
        final_size = 0
    
    return (output_path, success, final_size)


def process_files(
    file_paths: list[str],
    output_zip_path: str,
    progress_callback: callable = None
) -> dict:
    """
    Process all files: compress and create ZIP.
    Returns stats dict with success/fail counts.
    """
    stats = {
        'total': len(file_paths),
        'success': 0,
        'failed': 0,
        'details': []
    }
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        for i, file_path in enumerate(file_paths):
            filename = os.path.basename(file_path)
            
            if progress_callback:
                progress_callback(i + 1, len(file_paths), filename)
            
            try:
                output_path, success, size_kb = compress_file(file_path, temp_dir)
                
                if success and output_path:
                    stats['success'] += 1
                    status = f"OK ({size_kb} Ko)"
                else:
                    stats['failed'] += 1
                    status = f"Trop gros ({size_kb} Ko)"
                
                stats['details'].append((filename, status))
                
            except Exception as e:
                stats['failed'] += 1
                stats['details'].append((filename, f"Erreur: {str(e)[:30]}"))
        
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file)
                zf.write(file_path, file)
        
        stats['zip_size_kb'] = os.path.getsize(output_zip_path) // 1024
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    return stats
