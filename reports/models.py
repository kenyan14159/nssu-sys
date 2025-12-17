"""
帳票出力用モデル・ユーティリティ（追加テーブルは不要だが、reports.pyに分離）
"""
from django.db import models


class ReportLog(models.Model):
    """
    帳票出力ログ
    """
    REPORT_TYPES = [
        ('csv_startlist', 'スタートリストCSV'),
        ('pdf_rollcall', '点呼用PDF'),
        ('pdf_program', 'プログラム原稿PDF'),
        ('pdf_all', '全データPDF'),
    ]
    
    report_type = models.CharField('帳票種別', max_length=20, choices=REPORT_TYPES)
    competition = models.ForeignKey(
        'competitions.Competition',
        on_delete=models.CASCADE,
        related_name='report_logs',
        verbose_name='大会'
    )
    race = models.ForeignKey(
        'competitions.Race',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='report_logs',
        verbose_name='種目'
    )
    
    generated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='report_logs',
        verbose_name='出力者'
    )
    generated_at = models.DateTimeField('出力日時', auto_now_add=True)
    
    file_path = models.CharField('ファイルパス', max_length=500, blank=True)
    
    class Meta:
        verbose_name = '帳票出力ログ'
        verbose_name_plural = '帳票出力ログ'
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"{self.get_report_type_display()} - {self.generated_at}"
