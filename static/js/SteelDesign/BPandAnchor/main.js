// static/js/SteelDesign/BPandAnchor/main.js (全新重构版)

document.addEventListener('DOMContentLoaded', () => {

    // --- 1. 元素獲取和變數聲明 ---
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    let lastSuccessfulResults = null;
    let lastSuccessfulInputs = null;
    let lastSuccessfulLoads = null;
    let currentUnitSystem = 'imperial'; // [核心新增] 全局状态变量

    let isUserAuthenticated = false;
    const authStatusElement = document.getElementById('user-auth-status');
    if (authStatusElement) {
        try {
            isUserAuthenticated = JSON.parse(authStatusElement.textContent);
        } catch (e) {
            console.error('無法解析使用者認證狀態:', e);
        }
    }

    const uiControls = {
        colShapeSelect: document.getElementById('col-shape-select'),
        plateShapeSelect: document.getElementById('plate-shape-select'),
        boltLayoutSelect: document.getElementById('bolt-layout-select'),
        anchorInstallTypeSelect: document.getElementById('anchor-install-type-select'),
        anchorStructuralTypeSelect: document.getElementById('anchor-structural-type-select'),
        boltDiameterInput: document.getElementById('bolt-diameter-input'),
        anchorEhInput: document.getElementById('anchor-eh-input'),
        hasHoleRadios: document.querySelectorAll('input[name="has_hole"]'),
        holeOptionsContainer: document.getElementById('hole-options-container'),
        holeValidationWarning: null, // 我們將動態創建這個元素
        holeShapeSelect: document.getElementById('hole-shape-select'),
        pedestalShapeSelect: document.getElementById('pedestal-shape-select'),
        hasSupplementaryReinfRadios: document.querySelectorAll('input[name="has_supplementary_reinf"]'),
        supplementaryRebarSizeSelect: document.getElementById('supplementary-rebar-size-select'),
        supplementaryRebarSpacingInput: document.getElementById('supplementary-rebar-spacing-input'),
        isLightweightRadios: document.querySelectorAll('input[name="is_lightweight"]'),
        concreteWcInput: document.getElementById('concrete-wc-input'),
        fcInput: document.getElementById('fc-input'), // 新增
        ecInput: document.getElementById('ec-input'),   // 新增
        lambdaAInput: document.getElementById('lambda-a-input'), // 新增
        fcValidationWarning: document.getElementById('fc-validation-warning'), // 新增
    };

    const tableControls = {
        loadsTableBody: document.querySelector('#loads-table tbody'),
        addLoadComboBtn: document.getElementById('add-load-combo-btn'),
        customBoltTableBody: document.querySelector('#custom-bolt-table tbody'),
        addBoltRowBtn: document.getElementById('add-bolt-row-btn'),
    };

    const mainActions = {
        calculateButton: document.getElementById('calculate-button'),
        resultsModal: document.getElementById('results-modal'),
        resultsModalBody: document.getElementById('results-modal-body'),
        closeResultsModalBtn: document.getElementById('close-results-modal-btn'),
        reportButtonModal: document.getElementById('report-button-modal'),
        previewContainer: document.getElementById('realtime-preview-container'),
        excelFileInput: document.getElementById('excel-file-input'),
    };

    let loadComboCounter = 0;

    const unitSystemRadios = document.querySelectorAll('input[name="unit-system"]');
    // [核心新增] 单位转换系统
    // ==========================================================
    const CONVERSION_FACTORS = {
        // 长度
        IN_TO_CM: 2.54,
        // 面积
        IN2_TO_CM2: 2.54 * 2.54,
        // 力
        KIP_TO_TF: 0.453592,
        // 弯矩
        KIP_IN_TO_TF_M: 0.453592 * 0.0254,
        // 应力
        KSI_TO_KGF_CM2: 70.307,
        PSI_TO_KGF_CM2: 0.070307,
    };
    const DENSITY_CONVERSION = 16.0185; // lb/ft^3 to kg/m^3
    const WC_VALUES = {
        imperial: {light: 115.0, normal: 150.0},
        mks: {light: 1840.0, normal: 2400.0}
    };
    const UNIT_LABELS = {
        imperial: {
            'density': '(lb/ft³)',
            'length-in': '(in)',
            'area-in2': '(in²)',
            'force': '(kips)',
            'moment': '(kip-in)',
            'stress-ksi': '(ksi)',
            'stress-psi': '(psi)',
        },
        mks: {
            'density': '(kg/m³)',
            'length-in': '(cm)',
            'area-in2': '(cm²)',
            'force': '(tf)',
            'moment': '(tf-m)',
            'stress-ksi': '(kgf/cm²)',
            'stress-psi': '(kgf/cm²)',
        }
    };

    /**
     * 切换整个页面的单位制
     * @param {string} toSystem - 'imperial' 或 'mks'
     */
    function switchUnitSystem(toSystem) {
        currentUnitSystem = toSystem;
        // 1. 更新所有单位标签
        document.querySelectorAll('[data-unit]').forEach(el => {
            const unitType = el.dataset.unit;
            if (UNIT_LABELS[toSystem] && UNIT_LABELS[toSystem][unitType]) {
                el.textContent = UNIT_LABELS[toSystem][unitType];
            }
        });

        // 2. 更新所有带 data-value-imperial 属性的输入框的值
        document.querySelectorAll('input[data-value-imperial]').forEach(input => {
            const imperialValue = parseFloat(input.dataset.valueImperial);
            if (isNaN(imperialValue)) return;

            let mksValue;
            let digits = 3; // 默认保留的小数位数

            // 根据单位类型进行转换
            const unitType = findUnitTypeForInput(input);

            if (toSystem === 'mks') {
                switch (unitType) {
                    case 'length-in':
                        mksValue = imperialValue * CONVERSION_FACTORS.IN_TO_CM;
                        digits = 2;
                        break;
                    case 'area-in2':
                        mksValue = imperialValue * CONVERSION_FACTORS.IN2_TO_CM2;
                        digits = 3;
                        break;
                    case 'stress-ksi':
                        mksValue = imperialValue * CONVERSION_FACTORS.KSI_TO_KGF_CM2;
                        digits = 1;
                        break;
                    case 'stress-psi':
                        mksValue = imperialValue * CONVERSION_FACTORS.PSI_TO_KGF_CM2;
                        digits = 1;
                        break;
                    case 'density': // 新增
                        mksValue = imperialValue * DENSITY_CONVERSION;
                        digits = 0;
                        break;
                    default:
                        mksValue = imperialValue;
                        break; // 未知类型不转换
                }
                input.value = mksValue.toFixed(digits);
            } else { // imperial
                input.value = imperialValue.toFixed(input.id === 'fc-input' ? 0 : 3); // 恢复英制预设值
            }
        });
        updateConcreteWeight();
    }

    /**
     * 辅助函数：根据 input 元素找到其对应的单位类型
     * @param {HTMLElement} inputEl
     */
    function findUnitTypeForInput(inputEl) {
        const parentGroup = inputEl.closest('.input-group');
        if (parentGroup) {
            const unitSpan = parentGroup.querySelector('[data-unit]');
            if (unitSpan) {
                return unitSpan.dataset.unit;
            }
        }
        return null;
    }

    // [核心新增] 用於更新混凝土單位重的函式
    function updateConcreteWeight() {
        const isLightweight = document.querySelector('input[name="is_lightweight"]:checked').value === 'true';
        const wcInput = uiControls.concreteWcInput;

        if (currentUnitSystem === 'imperial') {
            const val = isLightweight ? WC_VALUES.imperial.light : WC_VALUES.imperial.normal;
            wcInput.value = val.toFixed(1);
            wcInput.dataset.valueImperial = val.toFixed(1); // 更新英制基準值
        } else { // mks
            const val = isLightweight ? WC_VALUES.mks.light : WC_VALUES.mks.normal;
            wcInput.value = val.toFixed(0);
            // 同時更新英制基準值，以便切換回去
            const imperialVal = isLightweight ? WC_VALUES.imperial.light : WC_VALUES.imperial.normal;
            wcInput.dataset.valueImperial = imperialVal.toFixed(1);
        }
    }

    // [核心新增] 自動計算混凝土彈性模數 Ec 的函式
    function calculateEc() {
        // 1. 獲取當前單位制下的 wc 和 fc 值
        const wc = parseFloat(uiControls.concreteWcInput.value);
        const fc = parseFloat(uiControls.fcInput.value);

        if (isNaN(wc) || isNaN(fc)) {
            uiControls.ecInput.value = ''; // 如果輸入不完整，清空 Ec
            return;
        }

        let ec;

        if (currentUnitSystem === 'imperial') {
            // 英制公式: Ec = wc^1.5 * 33 * sqrt(fc')  (psi)
            // wc 單位是 lb/ft³, fc' 單位是 psi
            // Ec 結果是 psi，但我們的輸入框單位是 ksi，所以要除以 1000
            ec = (Math.pow(wc, 1.5) * 33 * Math.sqrt(fc)) / 1000.0;
            uiControls.ecInput.value = ec.toFixed(2);
            // 同時更新英制基準值
            uiControls.ecInput.dataset.valueImperial = ec.toFixed(2);

        } else { // mks
            // MKS 制公式: Ec = wc^1.5 * 1.5 * sqrt(fc') (kgf/cm^2)
            // wc 單位是 kg/m³, fc' 單位是 kgf/cm^2
            // Ec 結果是 kgf/cm^2，但我們的輸入框單位是 ksi 轉換來的，所以要先轉回 ksi 再更新
            ec = Math.pow(wc, 1.5) * 1.5 * Math.sqrt(fc);
            uiControls.ecInput.value = ec.toFixed(1); // MKS 模式下顯示 kgf/cm^2

            // 同時計算並更新英制基準值
            const wc_imperial = parseFloat(uiControls.concreteWcInput.dataset.valueImperial);
            const fc_imperial = parseFloat(uiControls.fcInput.dataset.valueImperial);
            if (!isNaN(wc_imperial) && !isNaN(fc_imperial)) {
                const ec_imperial = (Math.pow(wc_imperial, 1.5) * 33 * Math.sqrt(fc_imperial)) / 1000.0;
                uiControls.ecInput.dataset.valueImperial = ec_imperial.toFixed(2);
            }
        }
    }

    // [核心新增] 自動計算 Lambda_a 的函式
    function calculateLambdaA() {
        const wc = parseFloat(uiControls.concreteWcInput.value);
        if (isNaN(wc)) {
            uiControls.lambdaAInput.value = '1.0';
            return;
        }

        let lambda = 1.0;
        if (currentUnitSystem === 'imperial') {
            if (wc <= 100) {
                lambda = 0.75;
            } else if (wc > 100 && wc <= 135) {
                // 注意：您提供的公式 0.0075 * wc 應該是錯誤的，ACI 318-19 (19.2.4.2) 公式為 0.85
                // 這裡暫時使用 0.85。如果是自訂公式，請修改此處。
                // 且 lambda 不應小於 0.75
                lambda = Math.min(Math.max(0.0075 * wc, 0.75), 1.0); // 假設您的公式是正確的
            } else { // wc > 135
                lambda = 1.0;
            }
        } else { // mks
            if (wc <= 1600) {
                lambda = 0.75;
            } else if (wc > 1600 && wc <= 2160) {
                // 假設 MKS 下也有類似的線性插值公式
                lambda = Math.min(Math.max(0.00046875 * wc, 0.75), 1.0); // (0.0075 / 16.0185) * wc
            } else { // wc > 2160
                lambda = 1.0;
            }
        }

        // 根據規範，lambda_a = lambda，除非有其他特殊情況
        const lambda_a = lambda * 1.0;
        uiControls.lambdaAInput.value = lambda_a.toFixed(2);
    }

    // [核心新增] 驗證 f'c 輸入值的函式
    function validateFc() {
        const fc = parseFloat(uiControls.fcInput.value);
        const installType = uiControls.anchorInstallTypeSelect.value;
        const warningEl = uiControls.fcValidationWarning;

        if (isNaN(fc)) {
            warningEl.style.display = 'none';
            return;
        }

        let limit = 0;
        let unit = '';

        if (currentUnitSystem === 'imperial') {
            limit = (installType === 'cast-in') ? 10000 : 8000;
            unit = 'psi';
        } else { // mks
            limit = (installType === 'cast-in') ? 700 : 560;
            unit = 'kgf/cm²';
        }

        if (fc > limit) {
            warningEl.textContent = `警告: 根據 規範第 17.3.1 節，用於此錨栓安裝方式的 f'c 不應超過 ${limit} ${unit}。`;
            warningEl.style.display = 'block';
        } else {
            warningEl.style.display = 'none';
        }
    }


    // [核心修正] 在切換主單位制後，也要重新計算 Ec
    unitSystemRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            switchUnitSystem(e.target.value);
            calculateEc();
            calculateLambdaA();
            validateFc();
        });
    });


    // ==========================================================
    // ==== A. UI 更新與互動函式 ====
    // ==========================================================

    /**
     * 根據下拉選單的選擇，動態顯示或隱藏對應的輸入區塊。
     */

    /**
     * 驗證開孔尺寸是否在管柱內部 (Tube/Pipe)
     */
    function validateHoleInTube() {
        const colShape = uiControls.colShapeSelect.value;
        const hasHole = document.querySelector('input[name="has_hole"]:checked').value === 'true';
        const holeShape = uiControls.holeShapeSelect.value;
        const validationContainer = document.getElementById('hole-validation-warning'); // 我們需要在 HTML 中新增這個容器

        // 如果不是管柱、沒有開孔或驗證容器不存在，則不執行
        if (!['Tube', 'Pipe'].includes(colShape) || !hasHole || !validationContainer) {
            if (validationContainer) validationContainer.style.display = 'none';
            return;
        }

        let is_valid = true;
        let error_message = '';

        if (colShape === 'Tube') {
            const H = parseFloat(document.getElementById('col-h-tube-input').value);
            const B = parseFloat(document.getElementById('col-b-tube-input').value);
            const t = parseFloat(document.getElementById('col-t-tube-input').value);

            if (isNaN(H) || isNaN(B) || isNaN(t)) return;

            const inner_h = H - 2 * t;
            const inner_b = B - 2 * t;

            if (holeShape === 'rectangle') {
                const n_hole = parseFloat(document.getElementById('hole-n-input').value);
                const b_hole = parseFloat(document.getElementById('hole-b-input').value);
                if (isNaN(n_hole) || isNaN(b_hole)) return;

                if (n_hole > inner_h || b_hole > inner_b) {
                    is_valid = false;
                    error_message = `開孔尺寸 (${b_hole}x${n_hole}) 不得大於管柱內部空心尺寸 (${inner_b.toFixed(2)}x${inner_h.toFixed(2)})。`;
                }
            } else { // circle or octagon hole in tube
                const r_hole = parseFloat(document.getElementById('hole-radius-input').value);
                if (isNaN(r_hole)) return;

                if (2 * r_hole > Math.min(inner_h, inner_b)) {
                    is_valid = false;
                    error_message = `開孔直徑 (${2 * r_hole}) 不得大於管柱內部空心短邊 (${Math.min(inner_h, inner_b).toFixed(2)})。`;
                }
            }
        } else if (colShape === 'Pipe') {
            const D = parseFloat(document.getElementById('col-d-pipe-input').value);
            const t = parseFloat(document.getElementById('col-t-pipe-input').value);
            if (isNaN(D) || isNaN(t)) return;

            const inner_d = D - 2 * t;

            if (holeShape === 'rectangle') {
                const n_hole = parseFloat(document.getElementById('hole-n-input').value);
                const b_hole = parseFloat(document.getElementById('hole-b-input').value);
                if (isNaN(n_hole) || isNaN(b_hole)) return;

                // 檢查矩形對角線是否小於圓管內徑
                if (Math.sqrt(n_hole ** 2 + b_hole ** 2) > inner_d) {
                    is_valid = false;
                    error_message = `矩形開孔的對角線長度不得大於圓管內徑 (${inner_d.toFixed(2)})。`;
                }
            } else { // circle or octagon hole in pipe
                const r_hole = parseFloat(document.getElementById('hole-radius-input').value);
                if (isNaN(r_hole)) return;

                if (2 * r_hole > inner_d) {
                    is_valid = false;
                    error_message = `開孔直徑 (${2 * r_hole}) 不得大於圓管內徑 (${inner_d.toFixed(2)})。`;
                }
            }
        }

        // 根據驗證結果顯示或隱藏錯誤訊息
        if (is_valid) {
            validationContainer.style.display = 'none';
        } else {
            validationContainer.textContent = `幾何錯誤: ${error_message}`;
            validationContainer.style.display = 'block';
        }
    }

    // [核心新增] 用於驗證 eh 值的函式
    function validateEh() {
        const da = parseFloat(uiControls.boltDiameterInput.value);
        const eh = parseFloat(uiControls.anchorEhInput.value);
        const warningEl = document.getElementById('eh-validation-warning');

        if (isNaN(da) || isNaN(eh)) {
            warningEl.style.display = 'none';
            return;
        }

        const lowerBound = 3 * da;
        const upperBound = 4.5 * da;

        if (eh < lowerBound || eh > upperBound) {
            warningEl.textContent = `警告: 依規範 eₕ 應介於 ${lowerBound.toFixed(3)} in 與 ${upperBound.toFixed(3)} in 之間。`;
            warningEl.style.display = 'block';
        } else {
            warningEl.style.display = 'none';
        }
    }

    function updateDynamicSections() {
        // --- 1. 處理鋼柱相關的顯示 ---
        const selectedColShape = uiControls.colShapeSelect.value;
        document.querySelectorAll('.col-params-group').forEach(el => el.style.display = 'none');
        document.getElementById(`col-params-${selectedColShape.toLowerCase()}`).style.display = 'block';

        // --- 2. 處理基礎版形狀相關的顯示 ---
        const selectedPlateShape = uiControls.plateShapeSelect.value;
        document.querySelectorAll('.plate-params-group').forEach(el => el.style.display = 'none');
        document.getElementById(selectedPlateShape === 'rectangle' ? 'plate-params-rectangle' : 'plate-params-radial').style.display = 'block';

        // --- 3. 處理錨栓佈置相關的顯示 ---
        const selectedBoltLayout = uiControls.boltLayoutSelect.value;
        document.querySelectorAll('.bolt-layout-group').forEach(el => el.style.display = 'none');
        document.getElementById(`bolt-layout-${selectedBoltLayout.toLowerCase()}`).style.display = 'block';

        // --- 4. 處理墩柱形狀相關的顯示 ---
        const selectedPedestalShape = uiControls.pedestalShapeSelect.value;
        document.querySelectorAll('.pedestal-params-group').forEach(el => el.style.display = 'none');
        document.getElementById(`pedestal-params-${selectedPedestalShape.toLowerCase()}`).style.display = 'block';

        // --- 5. 處理錨栓類型相關的顯示 (預埋 vs 後置) ---
        const installType = uiControls.anchorInstallTypeSelect.value;
        const castInOptions = document.getElementById('cast-in-anchor-options');
        if (installType === 'cast-in') {
            castInOptions.style.display = 'flex';
            const structuralType = uiControls.anchorStructuralTypeSelect.value;
            document.getElementById('headed-anchor-params').style.display = (structuralType === 'headed') ? 'block' : 'none';
            document.getElementById('hooked-anchor-params').style.display = (structuralType === 'hooked') ? 'block' : 'none';
            if (structuralType === 'hooked') validateEh();
        } else {
            castInOptions.style.display = 'none';
        }

        // 【核心新增】6. 更新辅助钢筋输入区的可见性和禁用状态
        const hasSupplementaryReinf = document.querySelector('input[name="has_supplementary_reinf"]:checked').value === 'true';
        const reinfOptionsContainer = document.getElementById('supplementary-reinf-options');
        if (hasSupplementaryReinf) {
            reinfOptionsContainer.style.display = 'flex';
            uiControls.supplementaryRebarSizeSelect.disabled = false;
            uiControls.supplementaryRebarSpacingInput.disabled = false;
        } else {
            reinfOptionsContainer.style.display = 'none';
            uiControls.supplementaryRebarSizeSelect.disabled = true;
            uiControls.supplementaryRebarSpacingInput.disabled = true;
        }

        // --- 7. 【核心重構】處理開孔相關的顯示與聯動 ---
        const hasHoleYesRadio = document.querySelector('input[name="has_hole"][value="true"]');
        const hasHoleNoRadio = document.querySelector('input[name="has_hole"][value="false"]');

        if (selectedColShape === 'H-Shape') {
            // 如果是 H 型鋼，強制禁用開孔
            hasHoleNoRadio.checked = true;
            hasHoleYesRadio.disabled = true;
            uiControls.holeOptionsContainer.style.display = 'none';
        } else {
            // 如果不是 H 型鋼，解除禁用
            hasHoleYesRadio.disabled = false;
            // 然後，根據 radio 按鈕的選擇來決定是否顯示開孔選項
            const hasHole = hasHoleNoRadio.checked === false;
            uiControls.holeOptionsContainer.style.display = hasHole ? 'flex' : 'none';
            if (hasHole) {
                const selectedHoleShape = uiControls.holeShapeSelect.value;
                document.querySelectorAll('.hole-params-group').forEach(el => el.style.display = 'none');
                document.getElementById(selectedHoleShape === 'rectangle' ? 'hole-params-rectangle' : 'hole-params-radial').style.display = 'block';
            }
        }

        // --- 8. 在所有 UI 更新的最後，呼叫一次驗證 ---
        validateHoleInTube();

    }

    /**
     * 新增荷載組合行。
     */
    function addLoadComboRow(p = '', mx = '', my = '', vx = '', vy = '', tz = '') {
        loadComboCounter++;
        const row = tableControls.loadsTableBody.insertRow();
        row.innerHTML = `<td>${loadComboCounter}</td><td><input type="number" class="load-input" data-field="p_applied" value="${p}"></td><td><input type="number" class="load-input" data-field="mx_applied" value="${mx}"></td><td><input type="number" class="load-input" data-field="my_applied" value="${my}"></td><td><input type="number" class="load-input" data-field="vx_applied" value="${vx}"></td><td><input type="number" class="load-input" data-field="vy_applied" value="${vy}"></td><td><input type="number" class="load-input" data-field="tz_applied" value="${tz}"></td><td><button type="button" class="remove-row-btn">移除</button></td>`;
        row.querySelectorAll('input.load-input').forEach(el => {
            el.addEventListener('change', debouncedUpdatePreview);
            el.addEventListener('input', debouncedUpdatePreview);
        });
    }

    /**
     * 新增自訂錨栓座標行。
     */
    function addBoltRow(x = '', y = '') {
        const rowCount = tableControls.customBoltTableBody.rows.length;
        const row = tableControls.customBoltTableBody.insertRow();
        row.innerHTML = `<td>${rowCount + 1}</td><td><input type="number" class="custom-bolt-x" value="${x}"></td><td><input type="number" class="custom-bolt-y" value="${y}"></td><td><button type="button" class="remove-row-btn">移除</button></td>`;
        row.querySelectorAll('input').forEach(el => {
            el.addEventListener('change', debouncedUpdatePreview);
            el.addEventListener('input', debouncedUpdatePreview);
        });
    }

    // ==========================================================
    // ==== B. 即時預覽繪圖核心函式 ====
    // ==========================================================
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    function updatePreview() {
        // 【核心修正】在函数内部重新获取一次容器，确保它存在
        const previewContainer = document.getElementById('realtime-preview-container');
        if (!previewContainer) return;

        const inputs = collectAllInputs();
        if (!inputs || !inputs.pedestal_params) {
            previewContainer.innerHTML = '<p style="color: #6c757d; text-align: center; padding: 20px;">输入数据不完整，无法生成预览。</p>';
            return;
        }

        // --- A. 准备 Plotly 需要的数据 (Data) 和布局 (Layout) ---

        const shapes = [];
        const {e_x = 0, e_y = 0} = inputs.plate_params; // 提前获取偏心值

        // 1a. 墩柱 (Pedestal)
        if (inputs.pedestal_params.shape === 'rectangle') {
            const {B = 30, N = 50} = inputs.pedestal_params;
            shapes.push({
                type: 'rect',
                x0: -B / 2, y0: -N / 2, x1: B / 2, y1: N / 2,
                fillcolor: '#E9ECEF', line: {color: '#adb5bd', width: 1.5},
                layer: 'below' // 确保墩柱在最底层
            });
        } else {
            const {D = 40} = inputs.pedestal_params;
            shapes.push({
                type: 'circle',
                x0: -D / 2, y0: -D / 2, x1: D / 2, y1: D / 2,
                fillcolor: '#E9ECEF', line: {color: '#adb5bd', width: 1.5},
                layer: 'below'
            });
        }

        // 1b. 基础版 (Base Plate)
        if (inputs.plate_params.shape === 'rectangle') {
            const {B = 20, N = 25} = inputs.plate_params;
            shapes.push({
                type: 'rect',
                x0: -B / 2 + e_x, y0: -N / 2 + e_y, x1: B / 2 + e_x, y1: N / 2 + e_y,
                fillcolor: 'rgba(2, 117, 216, 0.1)', line: {color: '#0275d8', width: 2},
                layer: 'below'
            });
        } else { // Circle or Octagon
            const {outer_radius = 12} = inputs.plate_params;
            if (inputs.plate_params.shape === 'circle') {
                shapes.push({
                    type: 'circle',
                    x0: -outer_radius + e_x, y0: -outer_radius + e_y, x1: outer_radius + e_x, y1: outer_radius + e_y,
                    fillcolor: 'rgba(2, 117, 216, 0.1)', line: {color: '#0275d8', width: 2},
                    layer: 'below'
                });
            } else { // Octagon
                const path = Array.from({length: 9}, (_, i) => {
                    const angle = Math.PI / 8 + (i * Math.PI / 4);
                    return `${outer_radius * Math.cos(angle) + e_x},${outer_radius * Math.sin(angle) + e_y}`;
                }).join(' L ');
                shapes.push({
                    type: 'path',
                    path: 'M ' + path + ' Z',
                    fillcolor: 'rgba(2, 117, 216, 0.1)', line: {color: '#0275d8', width: 2},
                    layer: 'below'
                });
            }
        }

        // 1c. 开孔 (Hole) - 如果有的话
        if (inputs.plate_params.has_hole) {
            if (inputs.plate_params.hole_shape === 'rectangle') {
                const {b = 0, n = 0} = inputs.plate_params;
                shapes.push({
                    type: 'rect',
                    x0: -b / 2 + e_x, y0: -n / 2 + e_y, x1: b / 2 + e_x, y1: n / 2 + e_y,
                    fillcolor: '#FFFFFF', // 用白色填充来模拟“挖空”
                    line: {color: '#adb5bd', width: 1, dash: 'dot'},
                    layer: 'above' // 确保开孔在基础版之上
                });
            }
            // ===== START: 核心新增区域 =====
            else { // Circle or Octagon for hole
                const {inner_radius = 0} = inputs.plate_params;
                if (inner_radius > 0) {
                    if (inputs.plate_params.hole_shape === 'circle') {
                        shapes.push({
                            type: 'circle',
                            x0: -inner_radius + e_x,
                            y0: -inner_radius + e_y,
                            x1: inner_radius + e_x,
                            y1: inner_radius + e_y,
                            fillcolor: '#FFFFFF',
                            line: {color: '#adb5bd', width: 1, dash: 'dot'},
                            layer: 'above'
                        });
                    } else { // Octagon for hole
                        const path = Array.from({length: 9}, (_, i) => {
                            const angle = Math.PI / 8 + (i * Math.PI / 4);
                            return `${inner_radius * Math.cos(angle) + e_x},${inner_radius * Math.sin(angle) + e_y}`;
                        }).join(' L ');
                        shapes.push({
                            type: 'path',
                            path: 'M ' + path + ' Z',
                            fillcolor: '#FFFFFF',
                            line: {color: '#adb5bd', width: 1, dash: 'dot'},
                            layer: 'above'
                        });
                    }
                }
            }
            // ===== END: 核心新增区域 =====
        }

        // 2. 定义锚栓数据 (Traces)
        const boltCoords = getBoltCoordinates(inputs.plate_params, inputs.bolt_params);
        const boltsTrace = {
            x: boltCoords.map(c => c[0] + e_x),
            y: boltCoords.map(c => c[1] + e_y),
            mode: 'markers',
            type: 'scatter',
            marker: {
                color: '#f0ad4e',
                size: 10,
                line: {color: '#d9534f', width: 1.5}
            },
            name: 'Anchors'
        };
        const data = [boltsTrace];

        // 3. 定义布局 (Layout)
        let viewWidth, viewHeight;
        if (inputs.pedestal_params.shape === 'rectangle') {
            viewWidth = inputs.pedestal_params.B || 30;
            viewHeight = inputs.pedestal_params.N || 50;
        } else {
            viewWidth = viewHeight = inputs.pedestal_params.D || 40;
        }
        // 确保 viewWidth/Height 不是 NaN
        if (isNaN(viewWidth) || isNaN(viewHeight)) return;

        const range_x = [-viewWidth * 0.6, viewWidth * 0.6];
        const range_y = [-viewHeight * 0.6, viewHeight * 0.6];

        const layout = {
            margin: {l: 20, r: 20, b: 20, t: 40},
            xaxis: {range: range_x, showgrid: true, zeroline: true, gridcolor: '#eee', zerolinecolor: '#ccc'},
            yaxis: {
                range: range_y,
                scaleanchor: "x",
                scaleratio: 1,
                showgrid: true,
                zeroline: true,
                gridcolor: '#eee',
                zerolinecolor: '#ccc'
            },
            shapes: shapes,
            showlegend: false,
            paper_bgcolor: '#FFFFFF', // 设置图表背景为白色
            plot_bgcolor: '#FFFFFF', // 设置绘图区域背景为白色
            // title: {text: '即時幾何預覽', font: {size: 16, color: '#1d3557'}}
        };

        // B. 绘制或更新图形
        Plotly.newPlot(mainActions.previewContainer, data, layout, {responsive: true, displayModeBar: false});
    }

    const debouncedUpdatePreview = debounce(updatePreview, 250); // 延迟 250毫秒

    // ==========================================================
    // ==== C. 資料收集與後端通訊 ====
    // ==========================================================

    /**
     * 收集頁面上所有的輸入值，並打包成一個結構化的物件。
     */
    function collectAllInputs() {
        try {
            // [核心修正] 在函式開頭讀取單位系統
            const currentUnitSystem = document.querySelector('input[name="unit-system"]:checked').value || 'imperial';

            // 一个辅助函数，用于根据单位制获取正确的数值
            const getValueInImperial = (elementId, unitType) => {
                const el = document.getElementById(elementId);
                // 安全检查：如果元素不存在或被禁用，则不尝试读取
                if (!el || el.disabled) return null;

                let value = parseFloat(el.value);
                if (isNaN(value)) return null;

                if (currentUnitSystem === 'mks') {
                    switch (unitType) {
                        case 'length-in':
                            return value / CONVERSION_FACTORS.IN_TO_CM;
                        case 'area-in2':
                            return value / CONVERSION_FACTORS.IN2_TO_CM2;
                        case 'stress-ksi':
                            return value / CONVERSION_FACTORS.KSI_TO_KGF_CM2;
                        case 'stress-psi':
                            return value / CONVERSION_FACTORS.PSI_TO_KGF_CM2;
                        default:
                            return value;
                    }
                }
                return value;
            };

            // Plate Params
            const plate_shape = uiControls.plateShapeSelect.value;
            let plate_params = {
                shape: plate_shape,
                tp_in: getValueInImperial('plate-tp-input', 'length-in'),
                fy_ksi: getValueInImperial('plate-fy-input', 'stress-ksi'),
                e_x: getValueInImperial('plate-ex-input', 'length-in') || 0,
                e_y: getValueInImperial('plate-ey-input', 'length-in') || 0,
                has_hole: document.querySelector('input[name="has_hole"]:checked').value === 'true'
            };
            if (plate_shape === 'rectangle') {
                plate_params.N = getValueInImperial('plate-n-input', 'length-in');
                plate_params.B = getValueInImperial('plate-b-input', 'length-in');
            } else {
                plate_params.outer_radius = getValueInImperial('plate-radius-input', 'length-in');
            }
            if (plate_params.has_hole) {
                plate_params.hole_shape = uiControls.holeShapeSelect.value;
                if (plate_params.hole_shape === 'rectangle') {
                    plate_params.n = getValueInImperial('hole-n-input', 'length-in');
                    plate_params.b = getValueInImperial('hole-b-input', 'length-in');
                } else {
                    plate_params.inner_radius = getValueInImperial('hole-radius-input', 'length-in');
                }
            }

            // Pedestal Params
            const pedestal_shape = uiControls.pedestalShapeSelect.value;
            let pedestal_params = {
                shape: pedestal_shape,
                h: getValueInImperial('pedestal-h-input', 'length-in'),
                longitudinal_rebar_size: document.getElementById('pedestal-rebar-size-select').value
            };
            if (pedestal_shape === 'rectangle') {
                pedestal_params.N = getValueInImperial('pedestal-n-input', 'length-in');
                pedestal_params.B = getValueInImperial('pedestal-b-input', 'length-in');
            } else {
                pedestal_params.D = getValueInImperial('pedestal-d-input', 'length-in');
            }

            // Bolt Params
            const bolt_layout_mode = uiControls.boltLayoutSelect.value;
            let bolt_params = {
                layout_mode: bolt_layout_mode,
                diameter: getValueInImperial('bolt-diameter-input', 'length-in'),
                threads_per_inch: null,
                Abrg_in2: null,
                eh_in: null
            };
            const anchor_install_type = uiControls.anchorInstallTypeSelect.value;
            if (anchor_install_type === 'cast-in') {
                const anchor_structural_type = uiControls.anchorStructuralTypeSelect.value;
                if (anchor_structural_type === 'headed') {
                    bolt_params.threads_per_inch = parseInt(document.getElementById('bolt-tpi-input').value) || null;
                    bolt_params.Abrg_in2 = getValueInImperial('anchor-abrg-input', 'area-in2');
                } else { // hooked
                    bolt_params.eh_in = getValueInImperial('anchor-eh-input', 'length-in');
                }
            }

            if (bolt_layout_mode === 'grid') {
                bolt_params.edge_dist_X = getValueInImperial('bolt-edge-x-input', 'length-in');
                bolt_params.edge_dist_Y = getValueInImperial('bolt-edge-y-input', 'length-in');
                bolt_params.num_inserted_X = parseInt(document.getElementById('bolt-num-x-input').value);
                bolt_params.num_inserted_Y = parseInt(document.getElementById('bolt-num-y-input').value);
            } else if (bolt_layout_mode === 'circular') {
                bolt_params.count = parseInt(document.getElementById('bolt-count-input').value);
                bolt_params.radius = getValueInImperial('bolt-radius-input', 'length-in');
                bolt_params.start_angle = parseFloat(document.getElementById('bolt-start-angle-input').value);
            } else { // Custom
                let coords = [];
                tableControls.customBoltTableBody.querySelectorAll('tr').forEach(row => {
                    const x_val = parseFloat(row.querySelector('.custom-bolt-x').value);
                    const y_val = parseFloat(row.querySelector('.custom-bolt-y').value);
                    if (!isNaN(x_val) && !isNaN(y_val)) {
                        if (currentUnitSystem === 'mks') {
                            coords.push([x_val / CONVERSION_FACTORS.IN_TO_CM, y_val / CONVERSION_FACTORS.IN_TO_CM]);
                        } else {
                            coords.push([x_val, y_val]);
                        }
                    }
                });
                bolt_params.coordinates = coords;
            }

            // Column Params
            const col_shape = uiControls.colShapeSelect.value;
            let column_params = {type: col_shape};
            if (col_shape === 'H-Shape') {
                column_params.d = getValueInImperial('col-d-input', 'length-in');
                column_params.bf = getValueInImperial('col-bf-input', 'length-in');
                column_params.tf = getValueInImperial('col-tf-input', 'length-in');
                column_params.tw = getValueInImperial('col-tw-input', 'length-in');
            } else if (col_shape === 'Tube') {
                column_params.H = getValueInImperial('col-h-tube-input', 'length-in');
                column_params.B = getValueInImperial('col-b-tube-input', 'length-in');
                column_params.t = getValueInImperial('col-t-tube-input', 'length-in');
            } else if (col_shape === 'Pipe') {
                column_params.D = getValueInImperial('col-d-pipe-input', 'length-in');
                column_params.t = getValueInImperial('col-t-pipe-input', 'length-in');
            }

            // Materials
            const materials = {
                plate_fy_ksi: getValueInImperial('plate-fy-input', 'stress-ksi'),
                bolt_fya_ksi: getValueInImperial('bolt-fya-input', 'stress-ksi'),
                bolt_futa_ksi: getValueInImperial('bolt-futa-input', 'stress-ksi'),
                es_ksi: getValueInImperial('es-input', 'stress-ksi'),
                fc_psi: getValueInImperial('fc-input', 'stress-psi'),
                ec_ksi: getValueInImperial('ec-input', 'stress-ksi'),
            };

            const has_supplementary_reinf = document.querySelector('input[name="has_supplementary_reinf"]:checked').value === 'true';

            // Anchor Check Params
            const anchor_check_params = {
                h_ef: getValueInImperial('anchor-hef-input', 'length-in'),
                anchor_install_type: uiControls.anchorInstallTypeSelect.value,
                anchor_structural_type: uiControls.anchorStructuralTypeSelect.value,
                is_cracked: document.querySelector('input[name="is_cracked"]:checked').value === 'true',
                is_lightweight: document.querySelector('input[name="is_lightweight"]:checked').value === 'true',
                lambda_a: parseFloat(document.getElementById('lambda-a-input').value) || 1.0, // 新增此行
                has_supplementary_reinf: has_supplementary_reinf,
                supplementary_rebar_size: has_supplementary_reinf ? uiControls.supplementaryRebarSizeSelect.value : null,
                supplementary_rebar_spacing: has_supplementary_reinf ? getValueInImperial('supplementary-rebar-spacing-input', 'length-in') : null
            };

            // [核心修正] 確保 unit_system 在回傳物件的最外層
            return {
                unit_system: currentUnitSystem,
                materials: materials,
                column_params: column_params,
                plate_params: plate_params,
                bolt_params: bolt_params,
                pedestal_params: pedestal_params,
                anchor_check_params: anchor_check_params,
            };

        } catch (e) {
            console.error("收集输入数据时出错:", e);
            return null;
        }
    }

    /**
     * 根據參數計算錨栓座標 (前端模擬，用於繪圖)。
     */
    // --- 辅助函数：根据参数计算锚栓坐标 ---
    function getBoltCoordinates(plate_params, bolt_params) {
        if (bolt_params.layout_mode === 'custom') {
            return bolt_params.coordinates || [];
        }

        let coords = [];
        if (bolt_params.layout_mode === 'grid') {
            // --- [核心修正] ---
            let x_max, y_max;
            if (plate_params.shape === 'rectangle') {
                x_max = (plate_params.B || 0) / 2;
                y_max = (plate_params.N || 0) / 2;
            } else { // Circle or Octagon
                x_max = plate_params.outer_radius || 0;
                y_max = plate_params.outer_radius || 0;
            }
            // --- [修正结束] ---

            const blpx = x_max - (bolt_params.edge_dist_X || 0);
            const blpy = y_max - (bolt_params.edge_dist_Y || 0);

            if (blpx < 0 || blpy < 0) return []; // 边距过大，无法布置

            const num_x = parseInt(bolt_params.num_inserted_X) || 0;
            const num_y = parseInt(bolt_params.num_inserted_Y) || 0;

            const xCoords = Array.from({length: num_x + 2}, (_, i) => -blpx + i * (2 * blpx / (num_x + 1)));
            const yCoords = Array.from({length: num_y + 2}, (_, i) => -blpy + i * (2 * blpy / (num_y + 1)));

            const coordSet = new Set();
            // 添加顶部和底部的行
            xCoords.forEach(x => {
                coordSet.add(`${x.toFixed(4)},${yCoords[0].toFixed(4)}`); // 底行
                coordSet.add(`${x.toFixed(4)},${yCoords[yCoords.length - 1].toFixed(4)}`); // 顶行
            });
            // 添加左侧和右侧的列 (不包括角点，因为已经添加过了)
            yCoords.slice(1, -1).forEach(y => {
                coordSet.add(`${xCoords[0].toFixed(4)},${y.toFixed(4)}`); // 左列
                coordSet.add(`${xCoords[xCoords.length - 1].toFixed(4)},${y.toFixed(4)}`); // 右列
            });

            coords = Array.from(coordSet).map(s => s.split(',').map(Number));

        } else if (bolt_params.layout_mode === 'circular') {
            const num_bolts = bolt_params.count;
            const radius = bolt_params.radius;
            const start_angle_deg = bolt_params.start_angle;
            for (let i = 0; i < num_bolts; i++) {
                const angle = (start_angle_deg + (i * 360 / num_bolts)) * Math.PI / 180;
                coords.push([radius * Math.cos(angle), radius * Math.sin(angle)]);
            }
        }
        return coords;
    }

    /**
     * 處理“計算”按鈕點擊事件，發送 AJAX 請求到後端。
     */
    function handleCalculateClick() {
        // ==========================================================
        // ==== START: 【核心新增】在點擊時進行權限檢查 ====
        // ==========================================================
        if (!isUserAuthenticated) {
            if (confirm("此功能需要登入會員才能使用。\n\n是否要立即前往登入或註冊？")) {
                // 如果使用者點擊 "確定"，跳轉到登入頁面
                // 確保您的 accounts app 的 URL name 是 'login'
                window.location.href = "/OLi/accounts/login/"; // 直接使用硬編碼的 URL 比較穩固
            }
            return; // 阻止執行後續的計算邏輯
        }
        // ==========================================================
        // ==== END: 核心新增 ====
        // ==========================================================


        const allInputs = collectAllInputs();
        if (!allInputs) {
            alert("輸入數據不完整或有誤，無法計算。請檢查所有欄位是否已正確填寫。");
            return;
        }
        lastSuccessfulInputs = allInputs;

        const all_loads = [];
        let conversionError = false;
        tableControls.loadsTableBody.querySelectorAll('tr').forEach((row, index) => {
            const load_combo = {id: index + 1};
            row.querySelectorAll('.load-input').forEach(input => {
                let value = parseFloat(input.value);
                if (isNaN(value)) {
                    value = 0;
                }

                if (currentUnitSystem === 'mks') {
                    const field = input.dataset.field;
                    if (field.includes('p_') || field.includes('v_')) {
                        value /= CONVERSION_FACTORS.KIP_TO_TF;
                    } else if (field.includes('m_') || field.includes('t_')) {
                        value /= CONVERSION_FACTORS.KIP_IN_TO_TF_M;
                    }
                }
                load_combo[input.dataset.field] = value;
            });
            all_loads.push(load_combo);
        });

        lastSuccessfulLoads = all_loads;

        const formData = {
            loads_combinations: all_loads,
            ...allInputs
        };

        console.log("Form Data to be sent (always in imperial):", formData);

        mainActions.resultsModalBody.innerHTML = '<p class="placeholder-text">計算中，請稍候...</p>';
        mainActions.resultsModal.style.display = 'flex';
        document.body.classList.add('modal-open');

        fetch('/OLi/steel/BPandAnchor/calculate/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
            body: JSON.stringify(formData)
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    lastSuccessfulResults = data.results;
                    // [核心修改] 將結果的顯示也包裹在 try...catch 中
                    try {
                        mainActions.resultsModalBody.innerHTML = displayFormattedResults(data.results);
                    } catch (displayError) {
                        console.error("Error displaying results:", displayError);
                        mainActions.resultsModalBody.innerHTML = `<p class="result-message error">結果顯示時發生錯誤，請檢查控制台。</p>`;
                    }

                    // ==========================================================
                    // ==== START: 【核心新增】根據權限啟用/禁用報告書按鈕 ====
                    // ==========================================================
                    if (mainActions.reportButtonModal) {
                        const canGenerate = data.can_generate_report; // 讀取後端傳來的權限狀態

                        if (canGenerate) {
                            mainActions.reportButtonModal.disabled = false;
                            mainActions.reportButtonModal.title = "製作報告書";
                        } else {
                            mainActions.reportButtonModal.disabled = true;
                            mainActions.reportButtonModal.title = "您尚未購買此模組或訂閱已到期，無法製作報告書。";
                        }
                    }
                    // ==========================================================
                    // ==== END: 權限啟用/禁用邏輯 ====
                    // ==========================================================
                } else {
                    mainActions.resultsModalBody.innerHTML = `<p class="result-message error">計算失敗: ${data.message}</p><pre>${data.traceback || ''}</pre>`;
                    lastSuccessfulResults = null;
                    lastSuccessfulLoads = null;
                    if (mainActions.reportButtonModal) {
                        mainActions.reportButtonModal.disabled = true;
                        mainActions.reportButtonModal.title = "計算失敗，無法製作報告書。";
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                mainActions.resultsModalBody.innerHTML = `<p class="result-message error">請求錯誤，請檢查後端服務是否正常。</p>`;
                lastSuccessfulResults = null;
                lastSuccessfulLoads = null;
                if (mainActions.reportButtonModal) {
                    mainActions.reportButtonModal.disabled = true;
                    mainActions.reportButtonModal.title = "請求錯誤，無法製作報告書。";
                }
            });
    }

    // ==========================================================
    // ==== D. 結果顯示與報告生成 ====
    // ==========================================================

    /**
     * 將後端回傳的 JSON 結果格式化為 HTML。
     */
    function displayFormattedResults(results) {
        // --- Helper Functions ---
        const formatNumber = (num, digits = 3) => {
            if (num === null || num === undefined) return 'N/A';
            return typeof num === 'number' ? num.toFixed(digits) : String(num);
        };
        const formatCheckResult = (result) => {
            if (!result) return '<span>N/A</span>';
            const status = String(result).toUpperCase();
            const className = status === 'PASS' ? 'pass' : (status === 'FAIL' ? 'fail' : '');
            return `<span class="${className}">${status}</span>`;
        };

        const createEnvelopeCheckTable = (title, envelopeData) => {
            if (!envelopeData || !envelopeData.details || envelopeData.details.result === 'N/A') {
                const message = envelopeData?.details?.message || '未計算或不適用';
                return `
                <h4 class="result-subsection-title">${title}</h4>
                <p class="check-message">${message}</p>
            `;
            }

            const checkData = envelopeData.details;
            const comboId = envelopeData.combo_id;

            let demandValue = null;
            let capacityValue = null;
            let demandUnit = '';
            let capacityUnit = '';

            if ('Bu' in checkData && 'phi_Bn' in checkData) { // 承壓
                demandValue = checkData.Bu;
                capacityValue = checkData.phi_Bn;
                if (currentUnitSystem === 'mks') {
                    demandValue *= CONVERSION_FACTORS.KIP_TO_TF;
                    capacityValue *= CONVERSION_FACTORS.KIP_TO_TF;
                    demandUnit = ' tf';
                    capacityUnit = ' tf';
                } else {
                    demandUnit = ' kips';
                    capacityUnit = ' kips';
                }
            } else if ('max_Mu' in checkData && 'phi_Mn' in checkData) { // 彎曲
                demandValue = checkData.max_Mu;
                capacityValue = checkData.phi_Mn;
                if (currentUnitSystem === 'mks') {
                    demandValue *= CONVERSION_FACTORS.KIP_IN_TO_TF_M;
                    capacityValue *= CONVERSION_FACTORS.KIP_IN_TO_TF_M;
                    demandUnit = ' tf-m/m';
                    capacityUnit = ' tf-m/m';
                } else {
                    demandUnit = ' kip-in/in';
                    capacityUnit = ' kip-in/in';
                }
            } else { // 錨栓
                demandValue = checkData.demand;
                capacityValue = checkData.capacity;
                // ... (根據 title 判斷單位) ...
                if (currentUnitSystem === 'mks') {
                    demandValue *= CONVERSION_FACTORS.KIP_TO_TF;
                    capacityValue *= CONVERSION_FACTORS.KIP_TO_TF;
                    demandUnit = ' tf';
                    capacityUnit = ' tf';
                } else {
                    demandUnit = ' kips';
                    capacityUnit = ' kips';
                }
            }

            return `
            <h4 class="result-subsection-title">${title}</h4>
            <table class="results-table">
                <tbody>
                    <tr>
                        <td>控制組合 (Controlling Combo)</td>
                        <td><b># ${comboId}</b></td>
                    </tr>
                    <tr><td>需求 (Demand)</td><td>${formatNumber(demandValue)}${demandUnit}</td></tr>
                    <tr><td>容量 (Capacity)</td><td>${formatNumber(capacityValue)}${capacityUnit}</td></tr>
                    <tr><td>D/C Ratio</td><td><b>${formatNumber(checkData.dc_ratio)}</b></td></tr>
                    <tr><td>檢核結果</td><td>${formatCheckResult(checkData.result)}</td></tr>
                    ${checkData.message ? `<tr><td>備註</td><td colspan="2" class="check-message">${checkData.message}</td></tr>` : ''}
                </tbody>
            </table>
        `;
        };

        let html = `
        <style>
            .results-wrapper { font-size: 14px; line-height: 1.6; }
            .result-section-title { font-size: 18px; color: #1d3557; margin-top: 25px; margin-bottom: 15px; padding-bottom: 8px; border-bottom: 2px solid #a8dadc; }
            .result-subsection-title { font-size: 16px; font-weight: bold; color: #457b9d; margin-top: 20px; margin-bottom: 10px; }
            .results-table { width: 100%; border-collapse: collapse; margin-bottom: 15px; }
            .results-table td { padding: 8px; border: 1px solid #e0e0e0; vertical-align: top; }
            .results-table tr td:first-child { font-weight: 500; background-color: #f8f9fa; width: 40%; }
            .pass { color: #2a9d8f; font-weight: bold; }
            .fail { color: #e63946; font-weight: bold; }
            .check-message { font-size: 13px; color: #6c757d; font-style: italic; }
        </style>
        <div class="results-wrapper">
    `;

        html += `<h3 class="result-section-title">最不利情況包絡檢核 (Envelope Check)</h3>`;

        // --- 基礎版檢核 ---
        html += `<h3 class="result-section-title">基礎版檢核</h3>`;
        html += createEnvelopeCheckTable("混凝土承壓檢核", results.concrete_bearing);
        html += createEnvelopeCheckTable("基礎版彎曲檢核", results.plate_bending);

        // --- 錨栓拉力檢核 ---
        html += `<h3 class="result-section-title">錨栓拉力檢核 (Tension)</h3>`;
        html += createEnvelopeCheckTable("鋼材拉力強度 (Nsa)", results.anchor_nsa);
        html += createEnvelopeCheckTable("拔出強度 (Npn)", results.anchor_npn);
        html += createEnvelopeCheckTable("混凝土拉破強度 (Ncb) - 單根", results.anchor_ncb_single);
        html += createEnvelopeCheckTable("混凝土拉破強度 (Ncbg) - 群組", results.anchor_ncbg_group);
        html += createEnvelopeCheckTable("側向脹破強度 (Nsb) - 單根", results.anchor_nsb_single);
        html += createEnvelopeCheckTable("側向脹破強度 (Nsbg) - 群組", results.anchor_nsbg_group);

        // --- 錨栓剪力檢核 ---
        html += `<h3 class="result-section-title">錨栓剪力檢核 (Shear)</h3>`;
        html += createEnvelopeCheckTable("鋼材剪力強度 (Vsa)", results.anchor_vsa);
        html += createEnvelopeCheckTable("混凝土剪破強度 (Vcb) - 單根最不利", results.anchor_vcb_single);
        html += createEnvelopeCheckTable("混凝土剪破強度 (Vcbg) - X向群組", results.anchor_vcbg_group_x);
        html += createEnvelopeCheckTable("混凝土剪破強度 (Vcbg) - Y向群組", results.anchor_vcbg_group_y);
        html += createEnvelopeCheckTable("混凝土撬破強度 (Vcp) - 單根", results.anchor_vcp_single);
        html += createEnvelopeCheckTable("混凝土撬破強度 (Vcpg) - 群組", results.anchor_vcpg_group);

        html += `</div>`;
        return html;
    }

    /**
     * 處理“製作報告書”按鈕點擊事件。
     */
    function handleReportClick() {
        if (!lastSuccessfulResults) {
            alert("没有可用的計算結果可生成报告。");
            return;
        }

        // [核心修改] 不再建立表單，而是直接在新分頁中打開報告 URL
        // 伺服器會從 session 中讀取需要的資料
        window.open('/OLi/steel/BPandAnchor/report/', '_blank');
    }

    function handleExcelFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();

        reader.onload = function (e) {
            try {
                const data = new Uint8Array(e.target.result);
                const workbook = XLSX.read(data, {type: 'array'});
                const firstSheetName = workbook.SheetNames[0];
                const worksheet = workbook.Sheets[firstSheetName];
                const jsonData = XLSX.utils.sheet_to_json(worksheet, {header: 1});

                if (jsonData.length > 0) { // 只要有数据就行
                    // 决定是否清除现有行
                    if (tableControls.loadsTableBody.rows.length > 0) {
                        const confirmClear = confirm("汇入 Excel 将会覆盖当前的荷载组合，您确定要继续吗？");
                        if (!confirmClear) {
                            event.target.value = ''; // 重置 file input
                            return;
                        }
                    }

                    // 清空所有现有行
                    tableControls.loadsTableBody.innerHTML = '';
                    loadComboCounter = 0;

                    // 假设第一行是表头 (如果有的话)，从第二行开始读取，或者如果没有表头，就从第一行开始
                    // 简单起见，我们假设文件不包含表头
                    jsonData.forEach(rowData => {
                        if (rowData.length > 0) { // 确保不是空行
                            const p = rowData[0] || 0;
                            const mx = rowData[1] || 0;
                            const my = rowData[2] || 0;
                            const vx = rowData[3] || 0;
                            const vy = rowData[4] || 0;
                            const tz = rowData[5] || 0;
                            addLoadComboRow(p, mx, my, vx, vy, tz);
                        }
                    });

                    alert(`成功匯入 ${jsonData.length} 組荷載組合！`);
                } else {
                    alert('Excel 文件中没有找到数据。');
                }
            } catch (error) {
                console.error("处理 Excel 文件时出错:", error);
                alert("讀取 Excel 文件失敗，請確認檔案格式是否正確。");
            } finally {
                event.target.value = '';
            }
        };
        reader.onerror = function (error) { /* ... */
        };
        reader.readAsArrayBuffer(file);
    }

    // ==========================================================
    // ==== E. 程式初始化與事件綁定 ====
    // ==========================================================
    // 绑定所有 UI 控制元素的 change 事件
    Object.values(uiControls).forEach(elOrNodeList => {
        if (NodeList.prototype.isPrototypeOf(elOrNodeList)) {
            elOrNodeList.forEach(el => el.addEventListener('change', updateDynamicSections));
        } else if (elOrNodeList) {
            elOrNodeList.addEventListener('change', updateDynamicSections);
        }
    });

    // 【核心修正】绑定所有输入框的 input 事件到 debounced 版本的函式
    document.querySelectorAll('.main-layout-grid input, .main-layout-grid select').forEach(el => {
        if (el.id === 'bolt-diameter-input' || el.id === 'anchor-eh-input') {
            el.addEventListener('input', validateEh);
        }
        if (el.tagName === 'SELECT' || el.type === 'radio') {
            el.addEventListener('change', updatePreview); // 切换时立即更新
        }
        el.addEventListener('input', debouncedUpdatePreview); // 输入时防抖更新
    });

    // [核心新增] 綁定輕質混凝土選項的 change 事件
    uiControls.isLightweightRadios.forEach(radio => {
        radio.addEventListener('change', () => {
            updateConcreteWeight();
            calculateEc();
            calculateLambdaA(); // 在更新 wc 後計算 Lambda_a
        });
    });

    uiControls.concreteWcInput.addEventListener('input', () => {
        calculateEc();
        calculateLambdaA(); // wc 變動時計算 Lambda_a
    });

    uiControls.fcInput.addEventListener('input', () => {
        calculateEc();
        validateFc(); // f'c 變動時進行驗證
    });
    // 錨栓安裝方式改變時，也要驗證 f'c
    uiControls.anchorInstallTypeSelect.addEventListener('change', validateFc);


    // 绑定按钮点击事件
    tableControls.addLoadComboBtn.addEventListener('click', () => {
        addLoadComboRow();
        debouncedUpdatePreview();
    });
    tableControls.addBoltRowBtn.addEventListener('click', () => {
        addBoltRow();
        debouncedUpdatePreview();
    });
    mainActions.calculateButton.addEventListener('click', handleCalculateClick);
    // 【核心新增】頁面載入時，根據登入狀態設定按鈕的初始樣式
    if (!isUserAuthenticated) {
        mainActions.calculateButton.style.backgroundColor = '#adb5bd'; // 灰色
        mainActions.calculateButton.style.cursor = 'pointer'; // 保持可點擊的鼠標樣式
        mainActions.calculateButton.title = '請先登入以使用分析功能';
    }
    if (mainActions.reportButtonModal) mainActions.reportButtonModal.addEventListener('click', handleReportClick);

    // 表格的事件代理
    tableControls.loadsTableBody.addEventListener('click', (e) => {
        if (e.target.classList.contains('remove-row-btn') && tableControls.loadsTableBody.rows.length > 1) {
            e.target.closest('tr').remove();
            tableControls.loadsTableBody.querySelectorAll('tr').forEach((row, index) => {
                row.cells[0].textContent = index + 1;
            });
            debouncedUpdatePreview();
        }
    });
    tableControls.customBoltTableBody.addEventListener('click', (e) => {
        if (e.target.classList.contains('remove-row-btn')) {
            e.target.closest('tr').remove();
            tableControls.customBoltTableBody.querySelectorAll('tr').forEach((row, index) => {
                row.cells[0].textContent = index + 1;
            });
            debouncedUpdatePreview();
        }
    });

    if (mainActions.excelFileInput) {
        mainActions.excelFileInput.addEventListener('change', handleExcelFileSelect);
    }

    // Modal 关闭逻辑
    if (mainActions.closeResultsModalBtn && mainActions.resultsModal) {
        const closeModal = () => {
            mainActions.resultsModal.style.display = 'none';
            document.body.classList.remove('modal-open');
        }
        mainActions.closeResultsModalBtn.addEventListener('click', closeModal);
        mainActions.resultsModal.addEventListener('click', e => {
            if (e.target === mainActions.resultsModal) closeModal();
        });
    }

    uiControls.boltDiameterInput.addEventListener('input', validateEh);
    uiControls.anchorEhInput.addEventListener('input', validateEh);

    // 【核心新增】為所有與開孔驗證相關的輸入框，綁定 input 事件
    const validationInputs = [
        'col-h-tube-input', 'col-b-tube-input', 'col-t-tube-input',
        'col-d-pipe-input', 'col-t-pipe-input',
        'hole-n-input', 'hole-b-input', 'hole-radius-input'
    ];
    validationInputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', validateHoleInTube);
        }
    });
    // 當切換開孔形狀時，也要觸發驗證
    if (uiControls.holeShapeSelect) {
        uiControls.holeShapeSelect.addEventListener('change', validateHoleInTube);
    }

    // 1. 讀取 HTML 中預設選中的單位制
    const defaultUnitSystem = document.querySelector('input[name="unit-system"]:checked').value;


    // 2. 根據預設值，手動呼叫一次 switchUnitSystem 來更新整個頁面
    switchUnitSystem(defaultUnitSystem);


    // --- 页面初始载入 ---
    updateDynamicSections();
    addLoadComboRow(-90.0, 300, 440.04, 63.0, 30.0, 30.0);
    addBoltRow(6.25, 8.75);
    addBoltRow(6.25, -8.75);
    addBoltRow(-6.25, 8.75);
    addBoltRow(-6.25, -8.75);


    setTimeout(() => {
        updatePreview();
        // calculateEc();
        // calculateLambdaA(); // 頁面載入時計算一次 Lambda_a
        // validateFc();     // 頁面載入時驗證一次 f'c
    }, 0);

    if (mainActions.reportButtonModal) mainActions.reportButtonModal.disabled = true;

    // 4. [可選但建議] 稍微調整單位制切換的事件監聽器
    unitSystemRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            // switchUnitSystem 內部已經更新了 currentUnitSystem
            switchUnitSystem(e.target.value);
            // 這些函式現在會使用最新的 currentUnitSystem 來計算
            calculateEc();
            calculateLambdaA();
            validateFc();
        });
    });
});