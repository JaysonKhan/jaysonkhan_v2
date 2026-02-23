from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.admin.views.decorators import staff_member_required
from PIL import Image
import os
import uuid
import io

@staff_member_required
def upload_media_view(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        
        # Validations
        if not file.content_type.startswith('image/') and not file.content_type.startswith('video/'):
            return JsonResponse({'error': 'Unsupported file type. Only images and videos are allowed.'}, status=400)
            
        ext = os.path.splitext(file.name)[1].lower()
        new_filename = f"{uuid.uuid4().hex}{ext}"
        
        if file.content_type.startswith('image/'):
            try:
                img = Image.open(file)
                # Resize if > 1920x1920
                img.thumbnail((1920, 1920))
                # Optional format
                img_format = img.format if img.format else "JPEG"
                temp = io.BytesIO()
                # Optimize image
                img.save(temp, format=img_format, optimize=True)
                temp.seek(0)
                file_path = default_storage.save(f"uploads/rich_content/{new_filename}", ContentFile(temp.read()))
            except Exception as e:
                file_path = default_storage.save(f"uploads/rich_content/{new_filename}", file)
        else:
            file_path = default_storage.save(f"uploads/rich_content/{new_filename}", file)

        url = default_storage.url(file_path)
        return JsonResponse({'location': url})
        
    return JsonResponse({'error': 'Invalid request'}, status=400)
