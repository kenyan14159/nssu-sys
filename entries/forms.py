"""
entries フォーム
"""
from django import forms
from django.core.exceptions import ValidationError

from accounts.models import Athlete
from competitions.models import Race

from .models import Entry


class EntryForm(forms.ModelForm):
    """エントリーフォーム"""
    declared_time_str = forms.CharField(
        label='申告タイム',
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '例: 14:30.00',
            'pattern': r'\d{1,2}:\d{2}\.\d{2}'
        }),
        help_text='分:秒.00 の形式で入力（例: 14:30.00）'
    )
    
    personal_best_str = forms.CharField(
        label='自己ベスト',
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '例: 14:00.00',
        }),
        help_text='分:秒.00 の形式で入力'
    )
    
    class Meta:
        model = Entry
        fields = ['athlete', 'note']
        widgets = {
            'athlete': forms.Select(attrs={'class': 'form-select'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        self.race = kwargs.pop('race', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 選手の選択肢を絞り込む
        if self.user:
            if self.user.organization:
                self.fields['athlete'].queryset = Athlete.objects.filter(
                    organization=self.user.organization,
                    is_active=True
                )
            else:
                self.fields['athlete'].queryset = Athlete.objects.filter(
                    user=self.user,
                    is_active=True
                )
            
            # 性別でフィルタ（種目が設定されている場合）
            if self.race and self.race.gender != 'X':
                self.fields['athlete'].queryset = self.fields['athlete'].queryset.filter(
                    gender=self.race.gender
                )
    
    def clean_declared_time_str(self):
        time_str = self.cleaned_data.get('declared_time_str')
        try:
            return Entry.time_to_seconds(time_str)
        except ValidationError as e:
            raise e
    
    def clean_personal_best_str(self):
        time_str = self.cleaned_data.get('personal_best_str')
        if not time_str:
            raise ValidationError('自己ベストを入力してください。')
        try:
            return Entry.time_to_seconds(time_str)
        except ValidationError as e:
            raise e
    
    def clean(self):
        cleaned_data = super().clean()
        athlete = cleaned_data.get('athlete')
        declared_time = cleaned_data.get('declared_time_str')
        
        # 種目との整合性チェック
        if self.race and athlete:
            if self.race.gender != 'X' and athlete.gender != self.race.gender:
                raise ValidationError('選手の性別と種目が一致しません。')
            
            # 重複エントリーチェック
            if Entry.objects.filter(athlete=athlete, race=self.race).exists():
                raise ValidationError('この選手は既にこの種目にエントリーしています。')
            
            # NCG種目の標準記録チェック
            if self.race.is_ncg and self.race.standard_time and declared_time:
                if declared_time > float(self.race.standard_time):
                    standard_time_str = Entry.seconds_to_time(float(self.race.standard_time))
                    declared_time_str = Entry.seconds_to_time(declared_time)
                    raise ValidationError(
                        f'NCG種目への参加には標準記録 ({standard_time_str}) を '
                        f'切っている必要があります。申告タイム: {declared_time_str}'
                    )
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.declared_time = self.cleaned_data['declared_time_str']
        if self.cleaned_data.get('personal_best_str'):
            instance.personal_best = self.cleaned_data['personal_best_str']
        if self.race:
            instance.race = self.race
        if self.user:
            instance.registered_by = self.user
        if commit:
            instance.save()
        return instance


class BulkEntryForm(forms.Form):
    """一括エントリーフォーム"""
    race = forms.ModelChoiceField(
        label='種目',
        queryset=Race.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        self.competition = kwargs.pop('competition', None)
        super().__init__(*args, **kwargs)
        
        if self.competition:
            self.fields['race'].queryset = self.competition.races.filter(is_active=True)


class ExcelUploadForm(forms.Form):
    """Excel一括アップロードフォーム"""
    excel_file = forms.FileField(
        label='Excelファイル',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xls'
        }),
        help_text='テンプレートに従って記入したExcelファイルをアップロードしてください'
    )
    
    def clean_excel_file(self):
        file = self.cleaned_data.get('excel_file')
        if file:
            # ファイルサイズチェック（5MB以下）
            if file.size > 5 * 1024 * 1024:
                raise ValidationError('ファイルサイズは5MB以下にしてください')
            
            # 拡張子チェック
            ext = file.name.split('.')[-1].lower()
            if ext not in ('xlsx', 'xls'):
                raise ValidationError('Excelファイル（.xlsx, .xls）のみアップロード可能です')
        
        return file
