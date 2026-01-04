"""
Bill Compressor - Compresses PDF/PNG/JPG files to max 200KB.
Uses pymupdf for PDF rendering (no external dependencies).
"""

import os
import io
import zipfile
import shutil
from pathlib import Path

from PIL import Image
import fitz  # pymupdf

MAX_SIZE_KB = 200
MAX_SIZE_BYTES = MAX_SIZE_KB * 1024


def compress_image_to_target(
    img: Image.Image,
    target_size: int,
    min_quality: int = 20,
    min_scale: float = 0.25
) -> bytes:
    """Compress PIL Image to target size by reducing quality and dimensions."""
    if img.mode == 'RGBA':
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')
    
    original_width, original_height = img.size
    quality = 85
    scale = 1.0
    best_result = None
    
    while quality >= min_quality and scale >= min_scale:
        if scale < 1.0:
            new_size = (
                max(1, int(original_width * scale)),
                max(1, int(original_height * scale))
            )
            resized = img.resize(new_size, Image.Resampling.LANCZOS)
        else:
            resized = img
        
        buffer = io.BytesIO()
        resized.save(buffer, format='JPEG', quality=quality, optimize=True)
        result = buffer.getvalue()
        best_result = result
        
        if len(result) <= target_size:
            return result
        
        if quality > 50:
            quality -= 10
        elif quality > 30:
            quality -= 5
            scale -= 0.05
        else:
            quality -= 5
            scale -= 0.1
    
    return best_result


def compress_image_file(input_path: str, output_path: str) -> bool:
    """Compress image file to max 200KB."""
    img = Image.open(input_path)
    compressed = compress_image_to_target(img, MAX_SIZE_BYTES)
    
    with open(output_path, 'wb') as f:
        f.write(compressed)
    
    return len(compressed) <= MAX_SIZE_BYTES


def compress_pdf_file(input_path: str, output_path: str) -> bool:
    """
    Compress PDF by rendering pages as images and creating new PDF.
    This is aggressive but guarantees size reduction.
    """
    original_size = os.path.getsize(input_path)
    
    if original_size <= MAX_SIZE_BYTES:
        shutil.copy(input_path, output_path)
        return True
    
    try:
        doc = fitz.open(input_path)
        num_pages = len(doc)
        
        if num_pages == 0:
            shutil.copy(input_path, output_path)
            return False
        
        target_per_page = (MAX_SIZE_BYTES - 5000) // num_pages
        target_per_page = max(target_per_page, 15000)
        
        dpi = 150
        if original_size > 2 * 1024 * 1024:
            dpi = 100
        if original_size > 5 * 1024 * 1024:
            dpi = 72
        
        compressed_pages = []
        
        for page_num in range(num_pages):
            page = doc[page_num]
            
            zoom = dpi / 72
            matrix = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix)
            
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            compressed = compress_image_to_target(
                img,
                target_per_page,
                min_quality=25,
                min_scale=0.3
            )
            
            compressed_img = Image.open(io.BytesIO(compressed))
            compressed_pages.append(compressed_img)
        
        doc.close()
        
        if len(compressed_pages) == 1:
            compressed_pages[0].save(output_path, format='PDF')
        else:
            compressed_pages[0].save(
                output_path,
                format='PDF',
                save_all=True,
                append_images=compressed_pages[1:]
            )
        
        final_size = os.path.getsize(output_path)
        
        if final_size > MAX_SIZE_BYTES:
            target_per_page = (MAX_SIZE_BYTES - 5000) // num_pages
            target_per_page = max(target_per_page, 8000)
            
            doc = fitz.open(input_path)
            compressed_pages = []
            
            for page_num in range(num_pages):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(0.8, 0.8))
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                compressed = compress_image_to_target(
                    img,
                    target_per_page,
                    min_quality=20,
                    min_scale=0.2
                )
                
                compressed_img = Image.open(io.BytesIO(compressed))
                compressed_pages.append(compressed_img)
            
            doc.close()
            
            if len(compressed_pages) == 1:
                compressed_pages[0].save(output_path, format='PDF')
            else:
                compressed_pages[0].save(
                    output_path,
                    format='PDF',
                    save_all=True,
                    append_images=compressed_pages[1:]
                )
        
        return os.path.getsize(output_path) <= MAX_SIZE_BYTES
        
    except Exception as e:
        shutil.copy(input_path, output_path)
        return False


def compress_file(input_path: str, output_dir: str) -> tuple[str, bool, int, int]:
    """
    Compress a single file.
    Returns: (output_path, success, original_size_kb, final_size_kb)
    """
    path = Path(input_path)
    ext = path.suffix.lower()
    original_size = os.path.getsize(input_path) // 1024
    
    if ext == '.pdf':
        output_path = os.path.join(output_dir, path.name)
        success = compress_pdf_file(input_path, output_path)
    elif ext in ('.png', '.jpg', '.jpeg'):
        output_path = os.path.join(output_dir, path.stem + '.jpg')
        success = compress_image_file(input_path, output_path)
    else:
        return ('', False, original_size, 0)
    
    final_size = os.path.getsize(output_path) // 1024 if os.path.exists(output_path) else 0
    return (output_path, success, original_size, final_size)


def process_files(
    file_paths: list[str],
    output_folder: str,
    output_zip_path: str,
    progress_callback: callable = None
) -> dict:
    """
    Process all files: compress to output_folder and create ZIP.
    Returns stats dict.
    """
    stats = {
        'total': len(file_paths),
        'success': 0,
        'failed': 0,
        'details': []
    }
    
    os.makedirs(output_folder, exist_ok=True)
    
    for i, file_path in enumerate(file_paths):
        filename = os.path.basename(file_path)
        
        if progress_callback:
            progress_callback(i + 1, len(file_paths), filename)
        
        try:
            output_path, success, orig_kb, final_kb = compress_file(
                file_path, output_folder
            )
            
            if success:
                stats['success'] += 1
                status = f"OK: {orig_kb} Ko -> {final_kb} Ko"
            else:
                stats['failed'] += 1
                status = f"Trop gros: {orig_kb} Ko -> {final_kb} Ko"
            
            stats['details'].append((filename, status))
            
        except Exception as e:
            stats['failed'] += 1
            stats['details'].append((filename, f"Erreur: {str(e)[:40]}"))
    
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename in os.listdir(output_folder):
            file_path = os.path.join(output_folder, filename)
            if os.path.isfile(file_path):
                zf.write(file_path, filename)
    
    stats['zip_size_kb'] = os.path.getsize(output_zip_path) // 1024
    stats['output_folder'] = output_folder
    
    return stats
