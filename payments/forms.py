"""
payments フォーム
"""
import os

from django import forms

from .models import Payment


class PaymentUploadForm(forms.ModelForm):
    """振込明細アップロードフォーム"""
    
    # 許可するファイル形式
    ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf']
    ALLOWED_CONTENT_TYPES = [
        'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'application/pdf'
    ]
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
    class Meta:
        model = Payment
        fields = ['receipt_image', 'payment_date', 'payment_amount', 'payer_name']
        widgets = {
            'receipt_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,.pdf'
            }),
            'payment_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'payment_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '振込金額を入力'
            }),
            'payer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '振込名義を入力'
            }),
        }
    
    def clean_receipt_image(self):
        image = self.cleaned_data.get('receipt_image')
        if image:
            # ファイルサイズチェック
            if image.size > self.MAX_FILE_SIZE:
                raise forms.ValidationError(
                    f'ファイルサイズは{self.MAX_FILE_SIZE // (1024*1024)}MB以下にしてください。'
                )
            
            # 拡張子チェック
            ext = os.path.splitext(image.name)[1].lower()
            if ext not in self.ALLOWED_EXTENSIONS:
                allowed = ', '.join(self.ALLOWED_EXTENSIONS)
                raise forms.ValidationError(
                    f'許可されていないファイル形式です。対応形式: {allowed}'
                )
            
            # ファイル形式チェック
            if hasattr(image, 'content_type') and image.content_type not in self.ALLOWED_CONTENT_TYPES:
                raise forms.ValidationError(
                    'JPEG、PNG、GIF、WebP、PDF形式のファイルをアップロードしてください。'
                )
        
        return image


class PaymentReviewForm(forms.Form):
    """入金確認フォーム（管理者用）"""
    action = forms.ChoiceField(
        choices=[('approve', '承認'), ('reject', '却下')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    note = forms.CharField(
        label='メモ',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '却下理由など'
        })
    )


class ParkingRequestForm(forms.Form):
    """駐車場申請フォーム"""
    requested_large_bus = forms.IntegerField(
        label='大型バス（45人乗り以上）',
        min_value=0,
        max_value=10,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 0,
            'max': 10,
        })
    )
    requested_medium_bus = forms.IntegerField(
        label='中型バス・マイクロバス',
        min_value=0,
        max_value=10,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 0,
            'max': 10,
        })
    )
    requested_car = forms.IntegerField(
        label='乗用車',
        min_value=0,
        max_value=20,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 0,
            'max': 20,
        })
    )
    notes = forms.CharField(
        label='備考',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': '特別な要望があれば記入してください'
        })
    )
