"""
accounts ビュー
"""
import logging

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

try:
    from django_ratelimit.decorators import ratelimit
    from django_ratelimit.exceptions import Ratelimited
    RATELIMIT_AVAILABLE = True
except ImportError:
    RATELIMIT_AVAILABLE = False

from .forms import (
    AthleteForm,
    LoginForm,
    OrganizationRegistrationForm,
    UserProfileForm,
    UserRegistrationForm,
)
from .models import Athlete

security_logger = logging.getLogger('security')


def ratelimit_handler(request, exception):
    """レート制限超過時のハンドラ"""
    security_logger.warning(
        f"Rate limit exceeded: IP={request.META.get('REMOTE_ADDR')}, "
        f"Path={request.path}"
    )
    return HttpResponse(
        'アクセス回数の上限を超えました。しばらく待ってから再試行してください。',
        status=429
    )


class CustomLoginView(LoginView):
    """ログインビュー（レート制限付き）"""
    form_class = LoginForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def dispatch(self, request, *args, **kwargs):
        # POSTリクエスト時のみレート制限を適用
        if request.method == 'POST' and RATELIMIT_AVAILABLE:
            # デコレータを動的に適用
            @ratelimit(key='ip', rate='5/m', method='POST', block=True)
            def rate_limited_dispatch(req, *a, **kw):
                return super(CustomLoginView, self).dispatch(req, *a, **kw)
            try:
                return rate_limited_dispatch(request, *args, **kwargs)
            except Ratelimited:
                return ratelimit_handler(request, None)
        return super().dispatch(request, *args, **kwargs)


class CustomLogoutView(LogoutView):
    """ログアウトビュー"""
    next_page = 'accounts:login'


def register(request):
    """ユーザー登録ビュー"""
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        org_form = OrganizationRegistrationForm(request.POST)
        registration_type = request.POST.get('registration_type', 'individual')
        
        if registration_type == 'organization':
            # 団体登録時は別フィールドから担当者情報を取得
            full_name_org = request.POST.get('full_name_org', '')
            full_name_kana_org = request.POST.get('full_name_kana_org', '')
            phone_org = request.POST.get('phone_org', '')
            
            # user_formのデータを上書きするためにmutable化
            user_form_data = request.POST.copy()
            user_form_data['full_name'] = full_name_org
            user_form_data['full_name_kana'] = full_name_kana_org
            user_form_data['phone'] = phone_org
            user_form = UserRegistrationForm(user_form_data)
            
            if user_form.is_valid() and org_form.is_valid():
                with transaction.atomic():
                    # 団体を作成
                    organization = org_form.save()
                    # ユーザーを作成
                    user = user_form.save(commit=False)
                    user.organization = organization
                    user.is_individual = False
                    user.save()
                    
                    login(request, user)
                    messages.success(request, '団体登録が完了しました。')
                    return redirect('competitions:dashboard')
        else:
            if user_form.is_valid():
                user = user_form.save(commit=False)
                user.is_individual = True
                user.save()
                
                login(request, user)
                messages.success(request, '個人登録が完了しました。')
                return redirect('competitions:dashboard')
    else:
        user_form = UserRegistrationForm()
        org_form = OrganizationRegistrationForm()
    
    return render(request, 'accounts/register.html', {
        'user_form': user_form,
        'org_form': org_form,
    })


@login_required
def profile(request):
    """プロフィール表示"""
    return render(request, 'accounts/profile.html', {
        'user': request.user,
    })


@login_required
def profile_edit(request):
    """プロフィール編集"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'プロフィールを更新しました。')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'accounts/profile_edit.html', {'form': form})


@login_required
def athlete_list(request):
    """選手一覧"""
    if request.user.organization:
        athletes = Athlete.objects.filter(organization=request.user.organization, is_active=True)
    elif request.user.is_individual:
        athletes = Athlete.objects.filter(user=request.user, is_active=True)
    else:
        athletes = Athlete.objects.none()
    
    return render(request, 'accounts/athlete_list.html', {'athletes': athletes})


@login_required
def athlete_create(request):
    """選手登録"""
    if request.method == 'POST':
        form = AthleteForm(request.POST)
        if form.is_valid():
            athlete = form.save(commit=False)
            if request.user.organization:
                athlete.organization = request.user.organization
            else:
                athlete.user = request.user
            athlete.save()
            messages.success(request, f'{athlete.full_name}を登録しました。')
            return redirect('accounts:athlete_list')
    else:
        form = AthleteForm()
    
    return render(request, 'accounts/athlete_form.html', {
        'form': form,
        'title': '選手登録',
    })


@login_required
def athlete_edit(request, pk):
    """選手編集"""
    if request.user.organization:
        athlete = get_object_or_404(Athlete, pk=pk, organization=request.user.organization)
    else:
        athlete = get_object_or_404(Athlete, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = AthleteForm(request.POST, instance=athlete)
        if form.is_valid():
            form.save()
            messages.success(request, f'{athlete.full_name}の情報を更新しました。')
            return redirect('accounts:athlete_list')
    else:
        form = AthleteForm(instance=athlete)
    
    return render(request, 'accounts/athlete_form.html', {
        'form': form,
        'athlete': athlete,
        'title': '選手編集',
    })


@login_required
def athlete_delete(request, pk):
    """選手削除（論理削除）"""
    if request.user.organization:
        athlete = get_object_or_404(Athlete, pk=pk, organization=request.user.organization)
    else:
        athlete = get_object_or_404(Athlete, pk=pk, user=request.user)
    
    if request.method == 'POST':
        athlete.is_active = False
        athlete.save()
        messages.success(request, f'{athlete.full_name}を削除しました。')
        return redirect('accounts:athlete_list')
    
    return render(request, 'accounts/athlete_confirm_delete.html', {'athlete': athlete})


@login_required
def athlete_bulk_template(request):
    """選手一括登録用Excelテンプレートダウンロード"""
    from django.http import HttpResponse

    from .athlete_import import generate_athlete_template
    
    content = generate_athlete_template()
    response = HttpResponse(
        content,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="athlete_template.xlsx"'
    return response


@login_required
def athlete_bulk_upload(request):
    """選手一括登録（アップロード・プレビュー）"""
    from .athlete_import import AthleteExcelImporter
    
    if request.method == 'POST':
        if 'file' not in request.FILES:
            messages.error(request, 'ファイルを選択してください。')
            return redirect('accounts:athlete_bulk_upload')
        
        file = request.FILES['file']
        
        # ファイル拡張子チェック
        if not file.name.endswith(('.xlsx', '.xls')):
            messages.error(request, 'Excelファイル（.xlsx または .xls）をアップロードしてください。')
            return redirect('accounts:athlete_bulk_upload')
        
        # ファイルサイズチェック（5MB以下）
        if file.size > 5 * 1024 * 1024:
            messages.error(request, 'ファイルサイズは5MB以下にしてください。')
            return redirect('accounts:athlete_bulk_upload')
        
        # Excelを解析
        importer = AthleteExcelImporter(request.user)
        parsed_athletes, global_errors = importer.parse_excel(file.read())
        
        if global_errors:
            for error in global_errors:
                messages.error(request, error)
            return redirect('accounts:athlete_bulk_upload')
        
        # セッションに解析結果を保存
        # birth_dateをシリアライズ可能な形式に変換
        serialized_athletes = []
        for athlete in parsed_athletes:
            athlete_copy = athlete.copy()
            if 'birth_date' in athlete_copy and athlete_copy['birth_date']:
                athlete_copy['birth_date'] = athlete_copy['birth_date'].isoformat()
            serialized_athletes.append(athlete_copy)
        
        request.session['bulk_athletes'] = serialized_athletes
        
        valid_count = sum(1 for a in parsed_athletes if a.get('valid'))
        error_count = len(parsed_athletes) - valid_count
        existing_count = sum(1 for a in parsed_athletes if a.get('existing_id'))
        
        return render(request, 'accounts/athlete_bulk_preview.html', {
            'athletes': parsed_athletes,
            'valid_count': valid_count,
            'error_count': error_count,
            'existing_count': existing_count,
            'total_count': len(parsed_athletes),
        })
    
    return render(request, 'accounts/athlete_bulk_upload.html')


@login_required
def athlete_bulk_register(request):
    """選手一括登録（確定処理）"""
    from datetime import date

    from .athlete_import import AthleteExcelImporter
    
    if request.method != 'POST':
        return redirect('accounts:athlete_bulk_upload')
    
    # セッションから解析結果を取得
    serialized_athletes = request.session.get('bulk_athletes')
    if not serialized_athletes:
        messages.error(request, 'アップロードされたデータがありません。再度アップロードしてください。')
        return redirect('accounts:athlete_bulk_upload')
    
    # birth_dateをデシリアライズ
    parsed_athletes = []
    for athlete in serialized_athletes:
        athlete_copy = athlete.copy()
        if 'birth_date' in athlete_copy and athlete_copy['birth_date']:
            athlete_copy['birth_date'] = date.fromisoformat(athlete_copy['birth_date'])
        parsed_athletes.append(athlete_copy)
    
    # 登録実行
    importer = AthleteExcelImporter(request.user)
    skip_existing = request.POST.get('skip_existing', 'true') == 'true'
    
    try:
        imported, skipped = importer.import_athletes(parsed_athletes, skip_existing=skip_existing)
        
        # セッションをクリア
        del request.session['bulk_athletes']
        
        if imported:
            messages.success(request, f'{len(imported)}名の選手を登録しました。')
        if skipped:
            skipped_valid = [s for s in skipped if s.get('valid') and s.get('existing_id')]
            if skipped_valid:
                messages.info(request, f'{len(skipped_valid)}名は既に登録済みのためスキップしました。')
        
        return redirect('accounts:athlete_list')
    
    except Exception as e:
        messages.error(request, f'登録中にエラーが発生しました: {str(e)}')
        return redirect('accounts:athlete_bulk_upload')


@login_required
def athlete_csv_template(request):
    """選手登録用CSVテンプレートダウンロード（JAAF形式）"""
    from .athlete_import import generate_jaaf_csv_template
    
    content = generate_jaaf_csv_template()
    response = HttpResponse(
        content,
        content_type='text/csv; charset=utf-8-sig'
    )
    response['Content-Disposition'] = 'attachment; filename="athlete_template_jaaf.csv"'
    return response
