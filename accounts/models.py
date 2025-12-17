"""
ユーザー・団体・選手モデル
"""
from auditlog.registry import auditlog
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models


class UserManager(BaseUserManager):
    """カスタムユーザーマネージャー"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('メールアドレスは必須です')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_admin', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    カスタムユーザーモデル
    - 管理者 (Superuser): 日体大マネージャー。全権限を持つ。
    - 一般ユーザー (User): 参加団体の監督・代表者、または個人参加選手。
    """
    # 団体分類
    ORGANIZATION_TYPE_CHOICES = [
        ('university', '大学'),
        ('highschool', '高校'),
        ('corporate', '実業団'),
        ('club', 'クラブ'),
        ('other', 'その他'),
    ]
    
    username = None  # usernameを無効化
    email = models.EmailField('メールアドレス', unique=True)
    
    # プロフィール情報
    full_name = models.CharField('氏名', max_length=100)
    full_name_kana = models.CharField('フリガナ', max_length=100)
    phone = models.CharField(
        '電話番号',
        max_length=15,
        validators=[RegexValidator(r'^[\d-]+$', '電話番号は数字とハイフンのみ使用できます')]
    )
    
    # 団体分類（大学、クラブ、個人など）
    organization_type = models.CharField(
        '団体分類',
        max_length=20,
        choices=ORGANIZATION_TYPE_CHOICES,
        default='individual'
    )
    
    # 所属団体略称（個人参加ユーザー用）
    affiliation_name = models.CharField('所属団体略称', max_length=50, blank=True)
    
    # 権限区分
    is_admin = models.BooleanField('管理者権限', default=False)
    
    # 監督名（団体用）
    coach_name = models.CharField('監督名', max_length=100, blank=True)
    
    # 連絡責任者名（団体用）
    contact_person = models.CharField('連絡責任者名', max_length=100, blank=True)
    
    # 住所情報（団体用）
    postal_code = models.CharField('郵便番号', max_length=8, blank=True)
    address = models.CharField('住所', max_length=200, blank=True)
    
    # 所属団体（団体代表者の場合）
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='所属団体'
    )
    
    # 個人参加の場合
    is_individual = models.BooleanField('個人参加', default=False)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'full_name_kana']
    
    class Meta:
        verbose_name = 'ユーザー'
        verbose_name_plural = 'ユーザー'
        ordering = ['full_name_kana']
    
    def __str__(self):
        return f"{self.full_name} ({self.email})"
    
    @property
    def display_name(self):
        if self.organization:
            return f"{self.organization.name} - {self.full_name}"
        return self.full_name


class Organization(models.Model):
    """
    団体モデル
    大学名、代表者情報、連絡先
    """
    name = models.CharField(
        '団体名', max_length=100, unique=True,
        help_text='正式名称で入力。例: 日本体育大学'
    )
    name_kana = models.CharField(
        '団体名（フリガナ）', max_length=100,
        help_text='全角カタカナで入力。例: ニッポンタイイクダイガク'
    )
    short_name = models.CharField(
        '略称', max_length=20, blank=True,
        help_text='短縮名。例: 日体大、早稲田、中大'
    )
    
    # 代表者情報
    representative_name = models.CharField('代表者氏名', max_length=100)
    representative_email = models.EmailField('代表者メールアドレス')
    representative_phone = models.CharField(
        '代表者電話番号',
        max_length=15,
        validators=[RegexValidator(r'^[\d-]+$', '電話番号は数字とハイフンのみ使用できます')]
    )
    
    # 住所情報
    postal_code = models.CharField('郵便番号', max_length=8, blank=True)
    address = models.CharField('住所', max_length=200, blank=True)
    
    # 陸連登録情報
    jaaf_code = models.CharField('陸連登録コード', max_length=20, blank=True)
    
    # メタ情報
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    is_active = models.BooleanField('有効', default=True)
    
    class Meta:
        verbose_name = '団体'
        verbose_name_plural = '団体'
        ordering = ['name_kana']
    
    def __str__(self):
        return self.name


class Athlete(models.Model):
    """
    選手マスタモデル
    代表者は所属選手を一度登録すれば、以降の大会でリストから選択可能
    """
    GENDER_CHOICES = [
        ('M', '男子'),
        ('F', '女子'),
    ]
    
    GRADE_CHOICES = [
        ('', '---'),
        ('1', '1年'),
        ('2', '2年'),
        ('3', '3年'),
        ('4', '4年'),
        ('M1', '修士1年'),
        ('M2', '修士2年'),
        ('D1', '博士1年'),
        ('D2', '博士2年'),
        ('D3', '博士3年'),
    ]
    
    # 所属
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='athletes',
        verbose_name='所属団体',
        null=True,
        blank=True
    )
    
    # 個人参加の場合のユーザー紐付け
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='athletes',
        verbose_name='登録ユーザー',
        null=True,
        blank=True
    )
    
    # 基本情報（漢字）
    last_name = models.CharField(
        '姓（漢字）', max_length=50,
        help_text='例: 山田'
    )
    first_name = models.CharField(
        '名（漢字）', max_length=50,
        help_text='例: 太郎'
    )
    last_name_kana = models.CharField(
        '姓（カナ）', max_length=50,
        help_text='全角カタカナで入力。例: ヤマダ'
    )
    first_name_kana = models.CharField(
        '名（カナ）', max_length=50,
        help_text='全角カタカナで入力。例: タロウ'
    )
    
    # 基本情報（ローマ字）
    last_name_en = models.CharField(
        '姓（ローマ字）', max_length=50, blank=True,
        help_text='大文字で入力。例: YAMADA'
    )
    first_name_en = models.CharField(
        '名（ローマ字）', max_length=50, blank=True,
        help_text='先頭のみ大文字。例: Taro'
    )
    
    # 属性
    gender = models.CharField(
        '性別', max_length=1, choices=GENDER_CHOICES,
        help_text='男子または女子を選択'
    )
    birth_date = models.DateField(
        '生年月日',
        help_text='形式: YYYY-MM-DD（例: 2000-04-01）'
    )
    
    # 学年（高校生・大学生用）
    grade = models.CharField(
        '学年', max_length=5, choices=GRADE_CHOICES, blank=True,
        help_text='学生の場合は学年を選択。社会人は空欄のOK'
    )
    
    # 陸連登録情報（必須）
    registered_pref = models.CharField(
        '登録陸協',
        max_length=10,
        default='',
        help_text='例: 東京、神奈川'
    )
    jaaf_id = models.CharField(
        'JAAF ID',
        max_length=20,
        default='',
        help_text='陸連登録番号（公認申請に必須）'
    )
    
    # 国籍（WAランキング申請に必須）
    NATIONALITY_CHOICES = [
        ('JPN', '日本 (JPN)'),
        ('KEN', 'ケニア (KEN)'),
        ('ETH', 'エチオピア (ETH)'),
        ('KOR', '韓国 (KOR)'),
        ('CHN', '中国 (CHN)'),
        ('USA', 'アメリカ (USA)'),
        ('GBR', 'イギリス (GBR)'),
        ('UGA', 'ウガンダ (UGA)'),
        ('TAN', 'タンザニア (TAN)'),
        ('MAR', 'モロッコ (MAR)'),
    ]
    
    nationality = models.CharField(
        '国籍',
        max_length=3,
        choices=NATIONALITY_CHOICES,
        default='JPN',
        help_text='IOC国コード（3文字）'
    )
    
    # メタ情報
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    is_active = models.BooleanField('有効', default=True)
    
    class Meta:
        verbose_name = '選手'
        verbose_name_plural = '選手'
        ordering = ['last_name_kana', 'first_name_kana']
    
    def __str__(self):
        org_name = self.organization.short_name if self.organization else "個人"
        return f"{self.last_name} {self.first_name} ({org_name})"
    
    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}"
    
    @property
    def full_name_kana(self):
        return f"{self.last_name_kana} {self.first_name_kana}"
    
    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )


# django-auditlog登録
auditlog.register(User, exclude_fields=['password', 'last_login'])
auditlog.register(Organization)
auditlog.register(Athlete)
