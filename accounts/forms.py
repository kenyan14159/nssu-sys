"""
accounts フォーム
"""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Athlete, Organization, User


class LoginForm(AuthenticationForm):
    """ログインフォーム"""
    username = forms.EmailField(
        label='メールアドレス',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@example.com',
            'autofocus': True
        })
    )
    password = forms.CharField(
        label='パスワード',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'パスワード'
        })
    )


class UserRegistrationForm(UserCreationForm):
    """ユーザー登録フォーム"""
    
    class Meta:
        model = User
        fields = ['email', 'full_name', 'full_name_kana', 'phone', 'organization_type', 
                  'affiliation_name', 'coach_name', 'contact_person', 'postal_code', 'address',
                  'password1', 'password2']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@example.com'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'full_name_kana': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'organization_type': forms.Select(attrs={'class': 'form-select'}),
            'affiliation_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例: ○○大学'}),
            'coach_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '123-4567'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['class'] = 'form-control'
        # 個人登録時のみ所属団体略称が必須
        self.fields['affiliation_name'].required = False
        # organization_typeは団体登録時のみ必須
        self.fields['organization_type'].required = False
        # 団体用フィールドはオプション
        self.fields['coach_name'].required = False
        self.fields['contact_person'].required = False
        self.fields['postal_code'].required = False
        self.fields['address'].required = False


class OrganizationRegistrationForm(forms.ModelForm):
    """団体登録フォーム"""
    
    class Meta:
        model = Organization
        fields = [
            'name', 'name_kana', 'short_name',
            'representative_name', 'representative_email', 'representative_phone',
            'postal_code', 'address', 'jaaf_code'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例: ○○大学陸上競技部'}),
            'name_kana': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例: マルマルダイガクリクジョウキョウギブ'}),
            'short_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例: ○○大'}),
            'representative_name': forms.TextInput(attrs={'class': 'form-control'}),
            'representative_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'representative_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '123-4567'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'jaaf_code': forms.TextInput(attrs={'class': 'form-control'}),
        }


class AthleteForm(forms.ModelForm):
    """選手登録フォーム"""
    
    NATIONALITY_CHOICES = [
        ('JPN', '日本'),
        ('USA', 'アメリカ'),
        ('KEN', 'ケニア'),
        ('ETH', 'エチオピア'),
        ('GBR', 'イギリス'),
        ('CHN', '中国'),
        ('KOR', '韓国'),
        ('OTHER', 'その他'),
    ]
    
    PREF_CHOICES = [
        ('', '---'),
        ('北海道', '北海道'),
        ('青森', '青森'),
        ('岩手', '岩手'),
        ('宮城', '宮城'),
        ('秋田', '秋田'),
        ('山形', '山形'),
        ('福島', '福島'),
        ('茨城', '茨城'),
        ('栃木', '栃木'),
        ('群馬', '群馬'),
        ('埼玉', '埼玉'),
        ('千葉', '千葉'),
        ('東京', '東京'),
        ('神奈川', '神奈川'),
        ('新潟', '新潟'),
        ('富山', '富山'),
        ('石川', '石川'),
        ('福井', '福井'),
        ('山梨', '山梨'),
        ('長野', '長野'),
        ('岐阜', '岐阜'),
        ('静岡', '静岡'),
        ('愛知', '愛知'),
        ('三重', '三重'),
        ('滋賀', '滋賀'),
        ('京都', '京都'),
        ('大阪', '大阪'),
        ('兵庫', '兵庫'),
        ('奈良', '奈良'),
        ('和歌山', '和歌山'),
        ('鳥取', '鳥取'),
        ('島根', '島根'),
        ('岡山', '岡山'),
        ('広島', '広島'),
        ('山口', '山口'),
        ('徳島', '徳島'),
        ('香川', '香川'),
        ('愛媛', '愛媛'),
        ('高知', '高知'),
        ('福岡', '福岡'),
        ('佐賀', '佐賀'),
        ('長崎', '長崎'),
        ('熊本', '熊本'),
        ('大分', '大分'),
        ('宮崎', '宮崎'),
        ('鹿児島', '鹿児島'),
        ('沖縄', '沖縄'),
    ]
    
    nationality = forms.ChoiceField(
        choices=NATIONALITY_CHOICES,
        initial='JPN',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='国籍'
    )
    
    registered_pref = forms.ChoiceField(
        choices=PREF_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='登録陸協'
    )
    
    class Meta:
        model = Athlete
        fields = [
            'last_name', 'first_name', 'last_name_kana', 'first_name_kana',
            'last_name_en', 'first_name_en',
            'gender', 'birth_date', 'grade',
            'registered_pref', 'jaaf_id', 'nationality'
        ]
        widgets = {
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例: 山田'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例: 太郎'}),
            'last_name_kana': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例: ヤマダ'}),
            'first_name_kana': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例: タロウ'}),
            'last_name_en': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例: YAMADA'}),
            'first_name_en': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例: Taro'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'grade': forms.Select(attrs={'class': 'form-select'}),
            'jaaf_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例: 12345678'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 登録陸協とJAAF IDを必須に
        self.fields['registered_pref'].required = True
        self.fields['jaaf_id'].required = True
        # ローマ字と学年はオプション
        self.fields['last_name_en'].required = False
        self.fields['first_name_en'].required = False
        self.fields['grade'].required = False


class UserProfileForm(forms.ModelForm):
    """プロフィール編集フォーム"""
    
    class Meta:
        model = User
        fields = ['full_name', 'full_name_kana', 'phone']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'full_name_kana': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }
