/* =============================================================================
   日体大競技会 管理画面カスタムJavaScript
   初心者向けヘルプ機能・警告強化
   ============================================================================= */

document.addEventListener('DOMContentLoaded', function() {
    
    // =========================================================================
    // 0. サイドバーをデフォルトで展開状態にする
    // =========================================================================
    function expandSidebarByDefault() {
        // サイドバーを折りたたんだ状態のクラスを削除
        const body = document.body;
        if (body.classList.contains('sidebar-collapse')) {
            body.classList.remove('sidebar-collapse');
        }
        
        // LocalStorageのサイドバー状態をクリア（常に展開）
        localStorage.removeItem('jazzmin.sidebar-toggle');
        localStorage.removeItem('jazzmin:sidebar-toggle');
        localStorage.removeItem('adminlte-sidebar-toggle');
    }
    
    // サイドバー展開を実行
    expandSidebarByDefault();
    
    
    // =========================================================================
    // 0-1. インライン追加ボタンの修正（Jazzmin互換性対策）
    // =========================================================================
    function fixInlineAddButtons() {
        // インラインの「追加」リンクを探す
        document.querySelectorAll('.add-row a, .inline-group .add-row a').forEach(function(addLink) {
            // 既にイベントが設定されている場合はスキップ
            if (addLink.dataset.fixedInline) return;
            addLink.dataset.fixedInline = 'true';
            
            addLink.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                // インラインのプレフィックスを取得
                var inlineGroup = this.closest('.inline-group');
                if (!inlineGroup) return;
                
                var prefix = inlineGroup.id.replace(/-group$/, '');
                var totalForms = document.querySelector('#id_' + prefix + '-TOTAL_FORMS');
                if (!totalForms) return;
                
                var currentCount = parseInt(totalForms.value);
                var maxForms = document.querySelector('#id_' + prefix + '-MAX_NUM_FORMS');
                var maxNum = maxForms ? parseInt(maxForms.value) : 1000;
                
                if (currentCount >= maxNum) {
                    alert('これ以上追加できません。');
                    return;
                }
                
                // 最後の行を複製
                var rows = inlineGroup.querySelectorAll('.inline-related:not(.empty-form)');
                var emptyRow = inlineGroup.querySelector('.inline-related.empty-form');
                var templateRow = emptyRow || rows[rows.length - 1];
                
                if (!templateRow) return;
                
                var newRow = templateRow.cloneNode(true);
                newRow.classList.remove('empty-form');
                newRow.classList.remove('last-related');
                newRow.style.display = '';
                
                // IDと名前を更新
                newRow.innerHTML = newRow.innerHTML.replace(
                    new RegExp('__prefix__|' + prefix + '-\\d+', 'g'),
                    prefix + '-' + currentCount
                );
                
                // フォームをクリア
                newRow.querySelectorAll('input:not([type="hidden"]), select, textarea').forEach(function(field) {
                    if (field.type === 'checkbox') {
                        field.checked = field.defaultChecked;
                    } else {
                        field.value = '';
                    }
                });
                
                // 削除チェックボックスをリセット
                newRow.querySelectorAll('input[name$="-DELETE"]').forEach(function(cb) {
                    cb.checked = false;
                });
                
                // 行を挿入
                var tbody = inlineGroup.querySelector('tbody');
                if (tbody) {
                    tbody.appendChild(newRow);
                } else {
                    var addRowTr = this.closest('.add-row');
                    if (addRowTr) {
                        addRowTr.parentNode.insertBefore(newRow, addRowTr);
                    }
                }
                
                // カウントを更新
                totalForms.value = currentCount + 1;
                
                // 新しい行にもイベントを適用
                applyEventListeners();
            });
        });
    }
    
    function applyEventListeners() {
        // 入力フィールドのフォーカス時にハイライト
        document.querySelectorAll('.inline-group input, .inline-group select, .inline-group textarea').forEach(function(input) {
            if (input.dataset.focusApplied) return;
            input.dataset.focusApplied = 'true';
            input.addEventListener('focus', function() {
                this.style.borderColor = '#007bff';
                this.style.boxShadow = '0 0 0 3px rgba(0, 123, 255, 0.15)';
            });
            input.addEventListener('blur', function() {
                this.style.borderColor = '';
                this.style.boxShadow = '';
            });
        });
    }
    
    // 初期実行
    fixInlineAddButtons();
    applyEventListeners();
    
    // MutationObserverで動的に追加される要素を監視
    var observer = new MutationObserver(function(mutations) {
        fixInlineAddButtons();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    
    // =========================================================================
    // 0-2. フィールドセットをデフォルトで展開（個人情報、所属情報、権限設定）
    // =========================================================================
    const expandFieldsets = ['個人情報', '所属情報', '権限設定'];
    document.querySelectorAll('fieldset.collapsed').forEach(function(fieldset) {
        const legend = fieldset.querySelector('h2, legend');
        if (legend) {
            const text = legend.textContent.trim();
            if (expandFieldsets.some(name => text.includes(name))) {
                fieldset.classList.remove('collapsed');
                // AdminLTE/Jazzminのカードの場合
                const card = fieldset.closest('.card');
                if (card) {
                    card.classList.remove('collapsed-card');
                    const cardBody = card.querySelector('.card-body');
                    if (cardBody) {
                        cardBody.style.display = 'block';
                    }
                }
            }
        }
    });
    
    // Jazzminのタブ形式の場合、対象タブをアクティブに
    document.querySelectorAll('.nav-tabs .nav-link').forEach(function(tab) {
        const text = tab.textContent.trim();
        if (expandFieldsets.some(name => text.includes(name))) {
            // 最初のタブのみアクティブにする処理はスキップ
        }
    });
    
    // =========================================================================
    // 1. 削除ボタンに確認ダイアログを追加
    // =========================================================================
    const deleteButtons = document.querySelectorAll('.deletelink, a[href*="delete"], input[value*="削除"]');
    deleteButtons.forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            const confirmed = confirm(
                '本当に削除しますか？\n\n' +
                'この操作は取り消すことができません。\n' +
                '関連するデータも一緒に削除される可能性があります。'
            );
            if (!confirmed) {
                e.preventDefault();
                return false;
            }
        });
    });
    
    // =========================================================================
    // 2. 検索フィールドにプレースホルダーを追加
    // =========================================================================
    const searchInputs = document.querySelectorAll('#searchbar input[type="text"], #changelist-search input[type="text"]');
    searchInputs.forEach(function(input) {
        // ページのURLからモデルを判定してプレースホルダーを設定
        const url = window.location.pathname;
        let placeholder = '検索キーワードを入力...';
        
        if (url.includes('/athlete/')) {
            placeholder = '選手名、フリガナ、JAAF ID、団体名で検索...';
        } else if (url.includes('/user/')) {
            placeholder = 'メールアドレス、氏名、団体名で検索...';
        } else if (url.includes('/organization/')) {
            placeholder = '団体名、フリガナ、代表者名で検索...';
        } else if (url.includes('/competition/')) {
            placeholder = '大会名、会場名で検索...';
        } else if (url.includes('/race/')) {
            placeholder = '種目名、大会名で検索...';
        } else if (url.includes('/entry/')) {
            placeholder = '選手名、団体名、種目名で検索...';
        } else if (url.includes('/payment/')) {
            placeholder = '振込名義、団体名で検索...';
        } else if (url.includes('/heat/')) {
            placeholder = '種目名、大会名で検索...';
        } else if (url.includes('/news/')) {
            placeholder = 'タイトル、本文で検索...';
        }
        
        input.setAttribute('placeholder', placeholder);
    });
    
    // =========================================================================
    // 3. 必須フィールドにマークを追加
    // =========================================================================
    const requiredFields = document.querySelectorAll('.required label, label.required');
    requiredFields.forEach(function(label) {
        if (!label.innerHTML.includes('*')) {
            label.innerHTML += ' <span style="color: #dc3545; font-weight: bold;">*</span>';
        }
    });
    
    // =========================================================================
    // 4. フォーム送信前の確認
    // =========================================================================
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        // 削除フォームの場合は追加の警告
        if (form.action && form.action.includes('delete')) {
            form.addEventListener('submit', function(e) {
                const confirmed = confirm(
                    '【最終確認】\n\n' +
                    'この削除操作は元に戻せません！\n' +
                    '本当に実行しますか？'
                );
                if (!confirmed) {
                    e.preventDefault();
                    return false;
                }
            });
        }
    });
    
    // =========================================================================
    // 5. ヘルプテキストのスタイリング
    // =========================================================================
    // ヘルプテキストは元のまま表示（絵文字は追加しない）
    
    // =========================================================================
    // 6. 入力フィールドのフォーカス時にハイライト
    // =========================================================================
    const inputs = document.querySelectorAll('input, select, textarea');
    inputs.forEach(function(input) {
        input.addEventListener('focus', function() {
            this.style.borderColor = '#007bff';
            this.style.boxShadow = '0 0 0 3px rgba(0, 123, 255, 0.15)';
        });
        
        input.addEventListener('blur', function() {
            this.style.borderColor = '';
            this.style.boxShadow = '';
        });
    });
    
    // =========================================================================
    // 7. 空のテーブル行にメッセージを表示
    // =========================================================================
    const tables = document.querySelectorAll('#result_list tbody');
    tables.forEach(function(tbody) {
        if (tbody.children.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = '<td colspan="100" style="text-align: center; padding: 40px; color: #666;">' +
                '<i class="fas fa-inbox" style="font-size: 48px; color: #ddd; display: block; margin-bottom: 15px;"></i>' +
                'データがありません。右上の「追加」ボタンから新規作成してください。</td>';
            tbody.appendChild(row);
        }
    });
    
    // =========================================================================
    // 8. 成功メッセージを自動で消す（5秒後）
    // =========================================================================
    const successMessages = document.querySelectorAll('.messagelist li.success');
    successMessages.forEach(function(msg) {
        setTimeout(function() {
            msg.style.transition = 'opacity 0.5s ease';
            msg.style.opacity = '0';
            setTimeout(function() {
                msg.remove();
            }, 500);
        }, 5000);
    });
    
    // =========================================================================
    // 9. タブレット・スマホでの操作性向上
    // =========================================================================
    if (window.innerWidth < 768) {
        // サイドバーのトグルボタンを目立たせる
        const sidebarToggle = document.querySelector('[data-widget="pushmenu"]');
        if (sidebarToggle) {
            sidebarToggle.style.fontSize = '24px';
            sidebarToggle.style.padding = '15px';
        }
    }
    
    // =========================================================================
    // 10. ツールチップの初期化（Bootstrap使用時）
    // =========================================================================
    if (typeof $ !== 'undefined' && $.fn.tooltip) {
        $('[data-toggle="tooltip"]').tooltip();
    }
    
    // =========================================================================
    // 11. 日付フィールドに今日の日付をセットするボタン
    // =========================================================================
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(function(input) {
        const today = new Date().toISOString().split('T')[0];
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.innerHTML = '今日';
        btn.style.cssText = 'margin-left: 10px; padding: 5px 10px; font-size: 12px; cursor: pointer; border: 1px solid #ddd; border-radius: 4px; background: #f8f9fa;';
        btn.addEventListener('click', function() {
            input.value = today;
        });
        input.parentNode.insertBefore(btn, input.nextSibling);
    });
    
    // =========================================================================
    // 12. 秒数入力フィールドに分秒変換ヘルプを追加（申告タイム等のみ）
    // =========================================================================
    // 秒単位の入力フィールドのみを対象（TimeFieldは除外）
    const secondsFields = document.querySelectorAll('input[name="declared_time"], input[name="personal_best"], input[name="standard_time"]');
    secondsFields.forEach(function(input) {
        // 入力時にリアルタイム変換表示
        const display = document.createElement('div');
        display.style.cssText = 'margin-top: 5px; font-size: 14px; color: #007bff; font-weight: bold;';
        input.parentNode.appendChild(display);
        
        input.addEventListener('input', function() {
            const seconds = parseFloat(this.value);
            if (!isNaN(seconds) && seconds > 0) {
                const minutes = Math.floor(seconds / 60);
                const secs = (seconds % 60).toFixed(2);
                display.innerHTML = minutes + '分' + secs + '秒';
            } else {
                display.innerHTML = '';
            }
        });
    });
    
    console.log('日体大競技会管理画面カスタムJSが読み込まれました');
});
