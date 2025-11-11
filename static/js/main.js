/**
 * 鋼結構設計系統 - 主JavaScript檔案
 * 版本：2023/08/28
 * 修改重點：
 * 1. 加強 H 型鋼標準型號驗證
 * 2. 只在按下執行按鈕時顯示驗證錯誤
 * 3. 完整保留無限大平面特殊處理
 */

// 設計系統核心功能
window.DesignSystem = window.DesignSystem || {
    // 顯示通知
    showNotification: function (message, type = 'info') {
        try {
            const existingNoti = document.querySelector('.notification');
            if (existingNoti) existingNoti.remove();

            const notification = document.createElement('div');
            notification.className = `notification notification-${type}`;
            notification.innerHTML = message.includes('<') || message.includes('\n')
                ? `<pre>${message}</pre>`
                : `<p>${message}</p>`;
            document.body.appendChild(notification);

            setTimeout(() => {
                notification.classList.add('fade-out');
                setTimeout(() => notification.remove(), 300);
            }, 5000);
        } catch (e) {
            console.error('通知顯示錯誤:', e);
        }
    },

    // 顯示欄位錯誤
    showFieldError: function (input, message = '此為必填欄位') {
        try {
            input.classList.add('is-invalid');

            let errorMsg = input.nextElementSibling;
            if (errorMsg && errorMsg.classList.contains('invalid-feedback')) {
                errorMsg.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`; // 更新內容並添加圖標
            } else {
                errorMsg = document.createElement('div');
                errorMsg.className = 'invalid-feedback';
                errorMsg.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`; // 新建時也添加圖標
                input.parentNode.insertBefore(errorMsg, input.nextElementSibling);
            }
        } catch (e) {
            console.error('顯示欄位錯誤失敗:', e);
        }
    },

    // 清除欄位錯誤
    clearFieldError: function (input) {
        try {
            input.classList.remove('is-invalid');
            const errorMsg = input.nextElementSibling;
            if (errorMsg && errorMsg.classList.contains('invalid-feedback')) {
                errorMsg.remove();
            }
        } catch (e) {
            console.error('清除欄位錯誤失敗:', e);
        }
    },

    // 清除所有錯誤狀態
    clearAllErrors: function () {
        document.querySelectorAll('.is-invalid').forEach(input => {
            input.classList.remove('is-invalid');
        });
        document.querySelectorAll('.invalid-feedback').forEach(msg => {
            msg.remove();
        });

        // 清除右側的驗證訊息
        const validationMsg = document.getElementById('validation-message');
        if (validationMsg) {
            validationMsg.innerHTML = '';
            validationMsg.classList.remove('show');
        }
    },

    // ***** 新增或移動到此處：手機版漢堡菜單切換 *****
    initMobileMenu: function () {
        const hamburger = document.querySelector('.hamburger');
        const navMenu = document.querySelector('.nav-menu');

        if (hamburger && navMenu) {
            hamburger.addEventListener('click', () => {
                hamburger.classList.toggle('active');
                navMenu.classList.toggle('active');
            });

            // 點擊菜單項後自動關閉
            document.querySelectorAll('.nav-item a').forEach(item => {
                item.addEventListener('click', () => {
                    hamburger.classList.remove('active');
                    navMenu.classList.remove('active');
                });
            });
        }
    },

    // ***** 新增或移動到此處：初始化導航欄 *****
    initNavbar: function () {
        this.initMobileMenu(); // 在 DesignSystem 內部調用自己的方法

        // 當前頁面高亮 (如果您的頁面結構需要)
        const currentPage = window.location.pathname.split('/').pop() || 'index.html';
        document.querySelectorAll('.nav-item').forEach(item => {
            const link = item.querySelector('a');
            if (link && link.getAttribute('href') && link.getAttribute('href').includes(currentPage)) {
                item.classList.add('active');
            } else {
                item.classList.remove('active'); // 確保移除其他非當前頁面的 active 類
            }
        });
    },

    // 添加載重行
    addLoadRow: function () {
        const tableBody = document.querySelector('#load-table tbody');
        const newRow = document.createElement('tr');
        newRow.className = 'load-row';
        const rowCount = tableBody.querySelectorAll('.load-row').length + 1;

        newRow.innerHTML = `
            <td><input type="text" class="form-control load-name" name="load_name[]" value="組合${rowCount}" required></td>
            <td><input type="number" class="form-control load-axial-force" name="axial_force[]" step="0.01" value="0" required></td>
            <td><input type="number" class="form-control load-moment-xx" name="moment_xx[]" step="0.01" value="0" required></td>
            <td><input type="number" class="form-control load-moment-yy" name="moment_yy[]" step="0.01" value="0" required></td>
            <td><input type="number" class="form-control load-shear-x" name="shear_x[]" step="0.01" value="0" required></td>
            <td><input type="number" class="form-control load-shear-y" name="shear_y[]" step="0.01" value="0" required></td>
            <td><input type="number" class="form-control load-torque-z" name="torque_z[]" step="0.01" value="0"></td>
            <td>
                <button type="button" class="btn btn-danger btn-icon remove-row" title="移除此載重組合">
                    &times;
                </button>
            </td>
        `;
        tableBody.appendChild(newRow);

        // 為新行中的輸入框添加 input 事件監聽器以清除錯誤
        newRow.querySelectorAll('.form-control').forEach(input => {
            input.addEventListener('input', () => DesignSystem.clearFieldError(input));
        });
    },

    // 初始化載重表格的事件監聽器
    initLoadTable: function () {
        const addLoadRowBtn = document.getElementById('add-load-row');
        if (addLoadRowBtn) {
            addLoadRowBtn.addEventListener('click', DesignSystem.addLoadRow);
        }

        // 使用事件委託處理移除按鈕
        document.querySelector('#load-table tbody').addEventListener('click', (event) => {
            if (event.target.classList.contains('remove-row')) {
                const row = event.target.closest('.load-row');
                if (row) {
                    // 確保至少保留一行
                    if (document.querySelectorAll('#load-table tbody .load-row').length > 1) {
                        row.remove();
                    } else {
                        DesignSystem.showNotification('至少需要一個載重組合。', 'error');
                    }
                }
            }
        });


        // 為所有初始載重行中的輸入框添加 input 事件監聽器
        document.querySelectorAll('#load-table .form-control').forEach(input => {
            input.addEventListener('input', () => DesignSystem.clearFieldError(input));
        });
    },
    // 其他表單邏輯初始化 (假設這個函數會調用 initLoadTable)
    initFormLogic: function () {
        // ... 其他表單相關的初始化 ...
        this.initLoadTable(); // 調用載重表格初始化
        // ...
    },
    initCalculation: function () {
        // ... 計算按鈕綁定等 ...
        const executeBtn = document.getElementById('execute-btn');
        if (executeBtn) {
            executeBtn.addEventListener('click', this.validateAndSubmitForm);
        }
    },

    // 驗證單個欄位 (加強版)
    validateField: function (input, showError = false) {
        try {
            // 無限大平面特殊處理
            const isInfinitePlaneField = ['concrete_x', 'concrete_y', 'concrete_thickness', 'grout_thickness'].includes(input.id);
            const isInfinitePlaneChecked = document.getElementById('infinite_plane')?.checked;

            if (isInfinitePlaneField && isInfinitePlaneChecked) {
                this.clearFieldError(input);
                return true;
            }

            // H型鋼標準型號特殊處理
            if (input.id === 'h_beam_spec') {
                const isHBeam = document.getElementById('column_shape')?.value === 'H-beam';
                const isCustomInputChecked = document.getElementById('custom_input')?.checked;

                if (isHBeam && !isCustomInputChecked) {
                    const isEmpty = input.value === '' || input.value === '-- 請選擇標準型號 --';

                    if (isEmpty) {
                        if (showError) {
                            this.showFieldError(input, '請選擇標準型號或勾選自行輸入尺寸');
                        }
                        return false;
                    }
                }
            }

            // 一般欄位驗證
            const isEmpty = input.type === 'checkbox' ? !input.checked :
                input.type === 'radio' ? !document.querySelector(`[name="${input.name}"]:checked`) :
                    !input.value.trim();

            if (isEmpty && input.required) {
                if (showError) {
                    this.showFieldError(input);
                }
                return false;
            } else {
                this.clearFieldError(input);
                return true;
            }
        } catch (e) {
            console.error('欄位驗證錯誤:', e);
            return true;
        }
    }
};

// ==================== 頁面初始化 ====================

document.addEventListener('DOMContentLoaded', function () {
    try {
        initDynamicForms();
        bindCalculateButton();
        initTooltips();

        // 初始化無限大平面狀態
        const infinitePlane = document.getElementById('infinite_plane');
        if (infinitePlane) {
            infinitePlane.addEventListener('change', handleInfinitePlaneToggle);
            handleInfinitePlaneToggle.call(infinitePlane);
        }

        // 初始化柱形狀狀態
        const columnShape = document.getElementById('column_shape');
        if (columnShape) {
            columnShape.addEventListener('change', handleColumnShapeChange);
            handleColumnShapeChange.call(columnShape);
        }
    } catch (e) {
        console.error('頁面初始化錯誤:', e);
        DesignSystem.showNotification('系統初始化失敗', 'error');
    }
});

// ==================== 表單交互邏輯 ====================

// 柱形狀變更處理 (完整版)
function handleColumnShapeChange() {
    try {
        const isHBeam = this.value === 'H-beam';
        const hBeamSection = document.getElementById('h-beam-inputs');

        if (hBeamSection) {
            hBeamSection.style.display = isHBeam ? 'block' : 'none';
        }

        // 更新銲接部位選項
        updateWeldLocationOptions.call(this);

        // 重置相關輸入
        if (!isHBeam) {
            document.getElementById('h_beam_spec').value = '-- 請選擇標準型號 --';
            document.getElementById('custom_input').checked = false;
            const customDiv = document.getElementById('h-beam-custom');
            if (customDiv) customDiv.style.display = 'none';

            // 清除錯誤狀態
            DesignSystem.clearFieldError(document.getElementById('h_beam_spec'));
            document.querySelectorAll('#h-beam-custom input').forEach(input => {
                DesignSystem.clearFieldError(input);
            });
        }
    } catch (e) {
        console.error('柱形狀變更處理錯誤:', e);
    }
}

// 自定義輸入切換 (完整版)
function handleCustomInputToggle() {
    try {
        const customDiv = document.getElementById('h-beam-custom');
        const specSelect = document.getElementById('h_beam_spec');

        if (customDiv && specSelect) {
            const isChecked = this.checked;
            customDiv.style.display = isChecked ? 'flex' : 'none';
            specSelect.disabled = isChecked;

            // 切換 required 屬性
            if (isChecked) {
                specSelect.removeAttribute('required');
                document.querySelectorAll('#h-beam-custom input').forEach(input => {
                    input.setAttribute('required', 'true');
                });

                // 清除標準型號的錯誤狀態
                DesignSystem.clearFieldError(specSelect);
            } else {
                specSelect.setAttribute('required', 'true');
                document.querySelectorAll('#h-beam-custom input').forEach(input => {
                    input.removeAttribute('required');
                    input.value = '';
                    DesignSystem.clearFieldError(input);
                });
            }
        }
    } catch (e) {
        console.error('自定義輸入切換錯誤:', e);
    }
}

// 更新銲接部位選項
function updateWeldLocationOptions() {
    try {
        const isHBeam = this.value === 'H-beam';
        document.getElementById('weld-outer-option').style.display = isHBeam ? 'block' : 'none';
        document.getElementById('weld-both-option').style.display = isHBeam ? 'block' : 'none';

        if (!isHBeam) {
            document.getElementById('weld_all').checked = true;
        }
    } catch (e) {
        console.error('更新銲接部位選項錯誤:', e);
    }
}

// 無限大平面切換 (完整版)
function handleInfinitePlaneToggle() {
    try {
        const isChecked = this.checked;
        const concreteInputs = ['concrete_x', 'concrete_y', 'concrete_thickness', 'grout_thickness'];

        concreteInputs.forEach(id => {
            const input = document.getElementById(id);
            if (input) {
                input.disabled = isChecked;
                input.required = !isChecked;
                DesignSystem.clearFieldError(input);
                if (isChecked) input.value = '';
            }
        });

        document.querySelectorAll('.concrete-label').forEach(label => {
            label.classList.toggle('disabled-label', isChecked);
        });
    } catch (e) {
        console.error('無限大平面切換錯誤:', e);
    }
}

// 鋼筋切換處理
function toggleRebarSection(detailsId, sizeId, qtyId, isChecked) {
    try {
        const detailDiv = document.getElementById(detailsId);
        if (detailDiv) {
            detailDiv.style.display = isChecked ? 'flex' : 'none';

            const sizeInput = document.getElementById(sizeId);
            const qtyInput = document.getElementById(qtyId);

            if (sizeInput) sizeInput.required = isChecked;
            if (qtyInput) qtyInput.required = isChecked;

            if (!isChecked) {
                if (sizeInput) {
                    sizeInput.value = sizeId.includes('tension') ? '#4' : '#3';
                    DesignSystem.clearFieldError(sizeInput);
                }
                if (qtyInput) {
                    qtyInput.value = sizeId.includes('tension') ? '4' : '2';
                    DesignSystem.clearFieldError(qtyInput);
                }
            }
        }
    } catch (e) {
        console.error('鋼筋切換處理錯誤:', e);
    }
}

// 初始化動態表單
function initDynamicForms() {
    try {
        // 鋼筋選項
        const tensionRebar = document.getElementById('tension_rebar');
        if (tensionRebar) {
            tensionRebar.addEventListener('change', function () {
                toggleRebarSection('tension_rebar_details', 'tension_rebar_size', 'tension_rebar_qty', this.checked);
            });
            // 初始化狀態
            toggleRebarSection('tension_rebar_details', 'tension_rebar_size', 'tension_rebar_qty', tensionRebar.checked);
        }

        const shearRebar = document.getElementById('shear_rebar');
        if (shearRebar) {
            shearRebar.addEventListener('change', function () {
                toggleRebarSection('shear_rebar_details', 'shear_rebar_size', 'shear_rebar_qty', this.checked);
            });
            // 初始化狀態
            toggleRebarSection('shear_rebar_details', 'shear_rebar_size', 'shear_rebar_qty', shearRebar.checked);
        }

        // 自定義輸入切換
        const customInput = document.getElementById('custom_input');
        if (customInput) {
            customInput.addEventListener('change', handleCustomInputToggle);
            // 初始化狀態
            handleCustomInputToggle.call(customInput);
        }
    } catch (e) {
        console.error('動態表單初始化錯誤:', e);
    }
}

// ==================== 驗證與計算 ====================

// 顯示美觀的驗證訊息
function showValidationMessage(missingFields) {
    try {
        const validationDiv = document.getElementById('validation-message');
        if (!validationDiv) return;

        if (missingFields.length > 0) {
            // 按表單區塊分組
            const groupedFields = {};
            missingFields.forEach(field => {
                if (!groupedFields[field.section]) {
                    groupedFields[field.section] = [];
                }
                groupedFields[field.section].push(field.name);
            });

            // 構建HTML
            let html = `
            <div class="alert">
                <div class="alert-title">
                    <svg viewBox="0 0 24 24">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                    </svg>
                    <span>以下必填欄位未完成</span>
                </div>
                <ul class="missing-fields">`;

            // 添加分組欄位
            for (const [section, fields] of Object.entries(groupedFields)) {
                html += `
                <li>
                    <strong>${section}</strong>
                    <span class="field-section">${fields.join('、')}</span>
                </li>`;
            }

            html += `</ul></div>`;

            validationDiv.innerHTML = html;
            validationDiv.classList.add('show');

            // 滾動到驗證訊息
            validationDiv.scrollIntoView({behavior: 'smooth', block: 'nearest'});
        } else {
            validationDiv.innerHTML = '';
            validationDiv.classList.remove('show');
        }
    } catch (e) {
        console.error('顯示驗證訊息錯誤:', e);
    }
}

// 收集所有未填欄位 (完整版)
function collectMissingFields() {
    const missingFields = [];
    try {
        const formSections = {
            'design-form': '載重條件',
            'column-form': '柱',
            'baseplate-form': '柱基板',
            'anchor-form': '錨栓',
            'concrete-form': '混凝土基座',
            'rebar-form': '錨栓鋼筋'
        };

        const isInfinitePlaneChecked = document.getElementById('infinite_plane')?.checked;

        // 檢查所有表單
        for (const [formId, sectionName] of Object.entries(formSections)) {
            const form = document.getElementById(formId);
            if (form) {
                form.querySelectorAll('[required]').forEach(input => {
                    // 跳過無限大平面相關欄位
                    if (isInfinitePlaneChecked && ['concrete_x', 'concrete_y', 'concrete_thickness', 'grout_thickness'].includes(input.id)) {
                        return;
                    }

                    const isValid = DesignSystem.validateField(input, true);

                    if (!isValid && input.offsetParent !== null) {
                        const label = input.labels?.[0]?.textContent?.trim() ||
                            input.previousElementSibling?.textContent?.trim() ||
                            input.getAttribute('placeholder') ||
                            input.name;

                        // 特殊處理標準型號的錯誤訊息
                        let errorName = label.replace('：', '').replace(/<sub>.*?<\/sub>/g, '').trim();
                        if (input.id === 'h_beam_spec') {
                            errorName = 'H型鋼標準型號';
                        }

                        missingFields.push({
                            section: sectionName,
                            name: errorName,
                            inputId: input.id
                        });
                    }
                });
            }
        }
    } catch (e) {
        console.error('收集未填欄位錯誤:', e);
    }

    return missingFields;
}

function bindCalculateButton() {
    const executeBtn = document.getElementById('execute-btn');
    if (executeBtn) {
        executeBtn.addEventListener('click', async function (e) {
            e.preventDefault();

            try {
                // 清除舊狀態
                clearAllValidationErrors();
                showLoading(true);

                // 執行計算
                await performCalculation();

            } catch (error) {
                // 錯誤處理已在 performCalculation 中完成
                console.error('計算流程錯誤:', error);
            } finally {
                showLoading(false);
            }
        });
    }
}

//
// 執行計算 (完整版)
// 修改後的 performCalculation()
// function performCalculation() {
//     try {
//         showLoading(true);
//
//         // 1. 收集表單數據
//         const formData = collectFormData();
//
//         // 2. 使用現有驗證系統
//         const missingFields = collectMissingFields();
//         if (missingFields.length > 0) {
//             showLoading(false);
//             showValidationMessage(missingFields);
//             const firstInvalid = document.querySelector('.is-invalid');
//             if (firstInvalid) firstInvalid.focus();
//             return Promise.reject(new Error("表單驗證失敗"));
//         }
//
//         // 3. 發送 AJAX 請求
//         return fetch('/steel/baseplate/cal_baseplate/', {
//             method: 'POST',
//             headers: {
//                 'Content-Type': 'application/json',
//                 'X-CSRFToken': getCSRFToken(),
//             },
//             body: JSON.stringify(formData),
//         })
//             .then(handleResponse)
//             .catch(handleError);
//
//     } catch (error) {
//         showLoading(false);
//         DesignSystem.showNotification(`系統錯誤: ${error.message}`, 'error');
//         return Promise.reject(error);
//     }
// }
function performCalculation() {
    // 先清除所有舊的錯誤狀態
    clearAllValidationErrors();

    // 檢查是否有未填欄位
    const missingFields = collectMissingFields();
    if (missingFields.length > 0) {
        showValidationMessage(missingFields);
        DesignSystem.showNotification('請填寫所有必填欄位', 'error');
        return Promise.reject(new Error('表單驗證失敗'));
    }

    // 發送請求...
    return fetch('/steel/baseplate/cal_baseplate/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify(collectFormData()),
    })
        .then(response => {
            if (!response.ok) throw new Error(`HTTP錯誤! 狀態碼: ${response.status}`);
            return response.json();
        })
        .then(data => {
            if (!data.success) throw new Error(data.message || '伺服器返回錯誤');

            // 成功時再次確保清除所有錯誤狀態
            clearAllValidationErrors();

            // 顯示成功訊息和結果
            DesignSystem.showNotification('計算完成', 'success');
            showResults(data.results);

            return data;
        })
        .catch(error => {
            DesignSystem.showNotification(`計算失敗: ${error.message}`, 'error');
            throw error;
        });
}

// 新增響應處理函數
function handleResponse(response) {
    showLoading(false);
    if (!response.ok) {
        throw new Error(`HTTP錯誤! 狀態碼: ${response.status}`);
    }
    return response.json().then(data => {
        if (!data.success) throw new Error(data.message || '伺服器返回錯誤');
        DesignSystem.showNotification('計算完成', 'success');
        showResults(data.results);
        return data;
    });
}

// 新增錯誤處理函數
function handleError(error) {
    showLoading(false);
    console.error('請求錯誤:', error);
    const message = error.message.startsWith('HTTP') ?
        '伺服器連接錯誤' : `計算錯誤: ${error.message}`;
    DesignSystem.showNotification(message, 'error');
    throw error;
}

// 顯示加載狀態
function showLoading(show) {
    try {
        const loader = document.getElementById('loading-overlay');

        if (show) {
            if (!loader) {
                const overlay = document.createElement('div');
                overlay.id = 'loading-overlay';
                overlay.innerHTML = `
                    <div class="loader"></div>
                    <p>計算中...</p>
                `;
                document.body.appendChild(overlay);
            }
        } else if (loader) {
            loader.classList.add('fade-out-loader');
            setTimeout(() => loader.remove(), 300);
        }
    } catch (e) {
        console.error('加載狀態顯示錯誤:', e);
    }
}

// 顯示示例結果
function showSampleResults() {
    try {
        const resultContainer = document.createElement('div');
        resultContainer.className = 'card result-card';
        resultContainer.innerHTML = `
            <h3>計算結果</h3>
            <p><strong>基板厚度:</strong> 32.5 mm</p>
            <p><strong>錨栓直徑:</strong> 20 mm</p>
            <p><strong>混凝土承載力:</strong> 245 kN/m²</p>
            <p><strong>安全係數:</strong> 2.1</p>
        `;

        const mainArea = document.querySelector('.main-area');
        if (mainArea) {
            mainArea.appendChild(resultContainer);
            resultContainer.scrollIntoView({behavior: 'smooth'});
        }
    } catch (e) {
        console.error('顯示結果錯誤:', e);
    }
}

// 工具提示系統
function initTooltips() {
    try {
        const tooltips = document.querySelectorAll('[data-tooltip]');

        function showTooltip() {
            const tooltipText = this.getAttribute('data-tooltip');
            if (!tooltipText) return;

            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.textContent = tooltipText;
            document.body.appendChild(tooltip);

            const rect = this.getBoundingClientRect();
            tooltip.style.left = `${rect.left + window.scrollX}px`;
            tooltip.style.top = `${rect.bottom + window.scrollY + 5}px`;

            window.currentTooltip = tooltip;
        }

        function hideTooltip() {
            if (window.currentTooltip) {
                window.currentTooltip.remove();
                window.currentTooltip = null;
            }
        }

        tooltips.forEach(el => {
            el.addEventListener('mouseenter', showTooltip);
            el.addEventListener('mouseleave', hideTooltip);
        });
    } catch (e) {
        console.error('工具提示初始化錯誤:', e);
    }
}

function collectFormData() {
    const formData = {};

    // 遍歷所有表單（載重、柱、基板、錨栓、混凝土、鋼筋）
    const forms = [
        document.getElementById('design-form'),   // 載重
        document.getElementById('column-form'),     // 柱
        document.getElementById('baseplate-form'),  // 基板
        document.getElementById('anchor-form'),     // 錨栓
        document.getElementById('concrete-form'),   // 混凝土
        document.getElementById('rebar-form'),      // 鋼筋
    ];

    forms.forEach(form => {
        if (!form) return;

        // 收集 input, select, textarea 的值
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            if (input.name && !input.disabled) {
                if (input.type === 'checkbox') {
                    formData[input.name] = input.checked;
                } else if (input.type === 'radio') {
                    if (input.checked) formData[input.name] = input.value;
                } else {
                    formData[input.name] = input.value.trim();
                }
            }
        });
    });

    return formData;
}

function getCSRFToken() {
    const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return csrfInput ? csrfInput.value : '';
}

/**
 * 在右側邊欄顯示計算結果
 * @param {Object} results - 從後端返回的計算結果
 */
function showResults(results) {
    try {
        const container = document.getElementById('result-container');
        if (!container) {
            throw new Error('找不到結果容器');
        }

        // 清空舊結果
        container.innerHTML = '';

        // 檢查是否有有效結果
        if (!results || typeof results !== 'object' || Object.keys(results).length === 0) {
            container.innerHTML = '<div class="alert alert-warning">無有效計算結果</div>';
            return;
        }

        // 創建結果卡片
        const resultCard = document.createElement('div');
        resultCard.className = 'result-card';

        // 構建結果HTML
        let html = `
            <h3 class="result-title">
                <svg class="icon-success" viewBox="0 0 24 24">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                </svg>
                計算結果
            </h3>
            <div class="result-content">
                <table class="result-table">
        `;

        // 添加每個結果項目
        for (const [key, value] of Object.entries(results)) {
            html += `
                <tr>
                    <th>${formatResultKey(key)}</th>
                    <td>${formatResultValue(key, value)}</td>
                </tr>
            `;
        }

        html += `
                </table>
            </div>
            <div class="result-footer">
                <small>${new Date().toLocaleString()}</small>
            </div>
        `;

        resultCard.innerHTML = html;
        container.appendChild(resultCard);

        // 添加動畫效果
        setTimeout(() => {
            resultCard.classList.add('show');
        }, 10);

    } catch (error) {
        console.error('顯示結果錯誤:', error);
        const container = document.getElementById('result-container');
        if (container) {
            container.innerHTML = `
                <div class="alert alert-danger">
                    結果顯示錯誤: ${error.message}
                </div>
            `;
        }
    }
}

/**
 * 格式化結果鍵名 (英文轉中文)
 */
function formatResultKey(key) {
    const keyMap = {
        'thickness': '基板厚度',
        'stress': '混凝土應力',
        'anchor_force': '錨栓受力',
        'deflection': '變形量',
        'safety_factor': '安全係數',
        // 添加更多映射...
    };
    return keyMap[key] || key;
}

/**
 * 格式化結果值 (添加單位)
 */
function formatResultValue(key, value) {
    if (value === null || value === undefined) return 'N/A';

    // 根據鍵名添加單位
    if (key.includes('thickness')) return `${value} mm`;
    if (key.includes('stress') || key.includes('force')) return `${value} MPa`;
    if (key.includes('deflection')) return `${value} mm`;
    if (key.includes('factor')) return value.toFixed(2);

    return value;
}

function clearAllValidationErrors() {
    // 清除所有輸入框的錯誤樣式
    document.querySelectorAll('.is-invalid').forEach(input => {
        input.classList.remove('is-invalid');
        const errorMsg = input.nextElementSibling;
        if (errorMsg && errorMsg.classList.contains('invalid-feedback')) {
            errorMsg.remove();
        }
    });

    // 清除右側的驗證訊息
    const validationMsg = document.getElementById('validation-message');
    if (validationMsg) {
        validationMsg.innerHTML = '';
        validationMsg.classList.remove('show');
    }
}


// 初始化導航欄
// function initNavbar() {
//     initMobileMenu();
//
//     // 當前頁面高亮
//     const currentPage = window.location.pathname.split('/').pop() || 'index.html';
//     document.querySelectorAll('.nav-item').forEach(item => {
//         if (item.querySelector('a').getAttribute('href').includes(currentPage)) {
//             item.classList.add('active');
//         }
//     });
// }

// ... (DesignSystem 對象現有的函數) ...

// 添加載重行
DesignSystem.addLoadRow = function () {
    const tableBody = document.querySelector('#load-table tbody');
    const newRow = document.createElement('tr');
    newRow.className = 'load-row';
    const rowCount = tableBody.querySelectorAll('.load-row').length + 1;

    newRow.innerHTML = `
        <td><input type="text" class="form-control load-name" name="load_name[]" value="組合${rowCount}" required></td>
        <td><input type="number" class="form-control load-axial-force" name="axial_force[]" step="0.01" value="0" required></td>
        <td><input type="number" class="form-control load-moment-xx" name="moment_xx[]" step="0.01" value="0" required></td>
        <td><input type="number" class="form-control load-moment-yy" name="moment_yy[]" step="0.01" value="0" required></td>
        <td><input type="number" class="form-control load-shear-x" name="shear_x[]" step="0.01" value="0" required></td>
        <td><input type="number" class="form-control load-shear-y" name="shear_y[]" step="0.01" value="0" required></td>
        <td><input type="number" class="form-control load-torque-z" name="torque_z[]" step="0.01" value="0"></td>
        <td>
            <button type="button" class="btn btn-danger btn-icon remove-row" title="移除此載重組合">
                <i class="fas fa-times"></i>
            </button>
        </td>
    `;
    tableBody.appendChild(newRow);

    // 為新行中的輸入框添加 input 事件監聽器以清除錯誤
    newRow.querySelectorAll('.form-control').forEach(input => {
        input.addEventListener('input', () => DesignSystem.clearFieldError(input));
    });

    // === 新增以下代碼進行測試 ===
    // 獲取新增的移除按鈕並嘗試強制應用樣式 (這應該不是必要，但用於診斷)
    const newRemoveButton = newRow.querySelector('.remove-row');
    if (newRemoveButton) {
        // 嘗試直接設置圖標的字體大小，看是否有改變
        const icon = newRemoveButton.querySelector('.fas.fa-times');
        if (icon) {
            icon.style.fontSize = '1.2rem'; // 確保和 CSS 定義的一致，或稍微大一點看效果
            icon.style.color = 'white'; // 確保顏色
        }
        // 嘗試直接設置按鈕的寬高
        newRemoveButton.style.width = '32px';
        newRemoveButton.style.height = '32px';
    }
    // =============================
};

// 初始化載重表格的事件監聽器
DesignSystem.initLoadTable = function () {
    const addLoadRowBtn = document.getElementById('add-load-row');
    if (addLoadRowBtn) {
        addLoadRowBtn.addEventListener('click', DesignSystem.addLoadRow);
    }

    // 使用事件委託處理移除按鈕
    document.querySelector('#load-table tbody').addEventListener('click', (event) => {
        if (event.target.classList.contains('remove-row')) {
            const row = event.target.closest('.load-row');
            if (row) {
                // 確保至少保留一行
                if (document.querySelectorAll('#load-table tbody .load-row').length > 1) {
                    row.remove();
                } else {
                    DesignSystem.showNotification('至少需要一個載重組合。', 'error');
                }
            }
        }
    });

    // 為所有初始載重行中的輸入框添加 input 事件監聽器
    document.querySelectorAll('#load-table .form-control').forEach(input => {
        input.addEventListener('input', () => DesignSystem.clearFieldError(input));
    });
};

// 使用事件委託處理移除按鈕
// 使用事件委託處理移除按鈕
document.querySelector('#load-table tbody').addEventListener('click', (event) => {
    // 檢查點擊的元素本身或其父元素是否包含 'remove-row' class
    const removeButton = event.target.closest('.remove-row');
    if (removeButton) { // 如果找到了帶有 remove-row class 的祖先元素 (即按鈕本身)
        const row = removeButton.closest('.load-row'); // 從按鈕向上找到最近的行
        if (row) {
            // 確保至少保留一行
            if (document.querySelectorAll('#load-table tbody .load-row').length > 1) {
                row.remove();
            } else {
                DesignSystem.showNotification('至少需要一個載重組合。', 'error');
            }
        }
    }
});


// 確保在 DOM 加載完成後初始化所有邏輯
document.addEventListener('DOMContentLoaded', () => {
    DesignSystem.initNavbar(); // 現在 initNavbar 是 DesignSystem 的方法
    DesignSystem.initFormLogic();
    DesignSystem.initCalculation();
    DesignSystem.clearAllErrors(); // 頁面加載時清除所有錯誤

    // 如果您希望頁面加載時默認就有一行載重組合，可以調用一次
    // 由於 HTML 中已經有一行，通常不需要再次調用
    // DesignSystem.addLoadRow();
});

