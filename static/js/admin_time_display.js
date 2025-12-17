/**
 * 管理画面用 タイム表示スクリプト
 * 秒数入力欄の横に分秒表示を追加
 */
(function() {
    'use strict';
    
    // 秒を分秒形式に変換
    function formatTimeDisplay(seconds) {
        if (isNaN(seconds) || seconds === '' || seconds === null) {
            return '';
        }
        const totalSeconds = parseFloat(seconds);
        const minutes = Math.floor(totalSeconds / 60);
        const secs = totalSeconds % 60;
        // 秒の小数点以下2桁まで表示
        const secsFormatted = secs.toFixed(2).padStart(5, '0');
        return minutes + '分' + secsFormatted + '秒';
    }
    
    // 表示要素を作成または更新
    function updateTimeDisplay(input) {
        const displayId = input.id + '_display';
        let display = document.getElementById(displayId);
        
        if (!display) {
            display = document.createElement('span');
            display.id = displayId;
            display.style.marginLeft = '8px';
            display.style.padding = '4px 8px';
            display.style.backgroundColor = '#d4edda';
            display.style.border = '1px solid #c3e6cb';
            display.style.borderRadius = '4px';
            display.style.fontWeight = 'bold';
            display.style.color = '#155724';
            display.style.fontSize = '13px';
            display.style.verticalAlign = 'middle';
            display.style.display = 'inline-block';
            input.parentNode.insertBefore(display, input.nextSibling);
        }
        
        const formatted = formatTimeDisplay(input.value);
        if (formatted) {
            display.textContent = '= ' + formatted;
            display.style.display = 'inline-block';
        } else {
            display.style.display = 'none';
        }
    }
    
    // 初期化
    function init() {
        // declared_time と personal_best のフィールドを対象に
        const targetFields = ['id_declared_time', 'id_personal_best'];
        
        targetFields.forEach(function(fieldId) {
            const input = document.getElementById(fieldId);
            if (input) {
                // 初期表示
                updateTimeDisplay(input);
                
                // 入力時に更新
                input.addEventListener('input', function() {
                    updateTimeDisplay(this);
                });
                
                // フォーカス時にも更新（矢印キーでの変更対応）
                input.addEventListener('change', function() {
                    updateTimeDisplay(this);
                });
            }
        });
    }
    
    // DOMContentLoaded で初期化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
