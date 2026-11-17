from io import BytesIO
from pathlib import Path
from django.core.files.base import ContentFile
from PIL import Image, ImageOps
from imagekit import ImageSpec
from imagekit.processors import ResizeToFit

class ArticleImageSpec(ImageSpec):
    processors = [ResizeToFit(1800, 1800, upscale=False)]
    format = "WEBP"
    options = {"quality":85}

class CardImageSpec(ImageSpec):
    processors = [ResizeToFit(640, 640, upscale=False)]
    format = "WEBP"
    options = {"quality":80}


def optimize_article_image(article):
    if not article.image:
        article.thumbnail = ''
        return
    if article.image._committed: return
    from django.core.exceptions import ValidationError
    if article.image.size > 8 * 1024 * 1024:
        raise ValidationError('Images must be 8 MB or smaller.')
    article.image.open('rb')
    with Image.open(article.image) as original:
        picture=ImageOps.exif_transpose(original).convert('RGB')
        source=BytesIO(); picture.save(source,'PNG'); source.seek(0)
        output=ArticleImageSpec(source=source).generate()
        stem=Path(article.image.name).stem
        article.image.save(stem+'.webp',ContentFile(output.read()),save=False)
        source.seek(0)
        output=CardImageSpec(source=source).generate()
        article.thumbnail.save(stem+'.webp',ContentFile(output.read()),save=False)
