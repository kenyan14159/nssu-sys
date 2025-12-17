"""
ファイルアップロード検証ユーティリティ
"""
import os

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

# 許可されるファイル拡張子
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif']
ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf']
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS + ALLOWED_DOCUMENT_EXTENSIONS

# 許可されるMIMEタイプ
ALLOWED_MIME_TYPES = {
    '.jpg': ['image/jpeg'],
    '.jpeg': ['image/jpeg'],
    '.png': ['image/png'],
    '.gif': ['image/gif'],
    '.pdf': ['application/pdf'],
}

# 最大ファイルサイズ (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024


@deconstructible
class FileValidator:
    """ファイルアップロードのバリデーター"""
    
    def __init__(self, max_size=MAX_FILE_SIZE, allowed_extensions=None):
        self.max_size = max_size
        self.allowed_extensions = allowed_extensions or ALLOWED_EXTENSIONS
    
    def __call__(self, file):
        # ファイルサイズチェック
        if file.size > self.max_size:
            max_mb = self.max_size / (1024 * 1024)
            raise ValidationError(
                f'ファイルサイズが大きすぎます。{max_mb:.1f}MB以下のファイルをアップロードしてください。'
            )
        
        # 拡張子チェック
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in self.allowed_extensions:
            allowed = ', '.join(self.allowed_extensions)
            raise ValidationError(
                f'許可されていないファイル形式です。対応形式: {allowed}'
            )
        
        # MIMEタイプチェック（簡易版）
        content_type = getattr(file, 'content_type', None)
        if content_type and ext in ALLOWED_MIME_TYPES:
            if content_type not in ALLOWED_MIME_TYPES[ext]:
                raise ValidationError(
                    'ファイルの内容と拡張子が一致しません。正しいファイルをアップロードしてください。'
                )
        
        return file
    
    def __eq__(self, other):
        return (
            isinstance(other, FileValidator) and
            self.max_size == other.max_size and
            self.allowed_extensions == other.allowed_extensions
        )


def validate_image_file(file):
    """画像ファイル専用バリデーター"""
    validator = FileValidator(
        max_size=MAX_FILE_SIZE,
        allowed_extensions=ALLOWED_IMAGE_EXTENSIONS
    )
    return validator(file)


def validate_receipt_image(file):
    """振込明細画像のバリデーター"""
    validator = FileValidator(
        max_size=MAX_FILE_SIZE,
        allowed_extensions=ALLOWED_IMAGE_EXTENSIONS + ['.pdf']
    )
    return validator(file)
