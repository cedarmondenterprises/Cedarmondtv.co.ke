from io import BytesIO
from pathlib import Path
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

def optimize_article_image(article):
    if not article.image or article.image._committed:
        return
    article.image.open('rb')
    with Image.open(article.image) as original:
        picture=ImageOps.exif_transpose(original).convert('RGB')
        picture.thumbnail((1800,1800))
        output=BytesIO(); picture.save(output,'WEBP',quality=85)
        stem=Path(article.image.name).stem
        article.image.save(stem+'.webp',ContentFile(output.getvalue()),save=False)
        picture.thumbnail((640,640))
        output=BytesIO(); picture.save(output,'WEBP',quality=80)
        article.thumbnail.save(stem+'.webp',ContentFile(output.getvalue()),save=False)
