// static/js/Wind_TW/main_open.js (修正並簡化後的版本)

document.addEventListener('DOMContentLoaded', () => {
    // ======================================================
    // 區域 1: 元素獲取
    // ======================================================
    const countySelect = document.getElementById('county-select'),
        townSelect = document.getElementById('town-select'),
        windSpeedDisplay = document.getElementById('wind-speed-display');
    const topoSelectX = document.getElementById('topo-select-x'),
        topoDetailsX = document.getElementById('topo-details-x');
    const topoSelectY = document.getElementById('topo-select-y'),
        topoDetailsY = document.getElementById('topo-details-y');
    const fnModeRadios = document.querySelectorAll('input[name="fn_mode"]'),
        manualFnInputGroup = document.getElementById('manual-fn-input-group');
    const calculateButton = document.getElementById('calculate-button'),
        resultsModal = document.getElementById('results-modal'),
        resultsModalBody = document.getElementById('results-modal-body'),
        reportButtonModal = document.getElementById('report-button-modal'),
        closeResultsModalBtn = document.getElementById('close-results-modal-btn');
    const enclosureStatusSelect = document.getElementById('enclosure-status-select');
    const allGeometrySections = document.querySelectorAll('.geometry-section');
    const shedHridgeInput = document.getElementById('shed-hridge-input'),
        shedHeaveInput = document.getElementById('shed-heave-input'),
        shedRidgeDirectionRadios = document.querySelectorAll('input[name="shed_ridge_direction"]'),
        shedBxInput = document.getElementById('shed-bx-input'),
        shedByInput = document.getElementById('shed-by-input'),
        shedThetaDisplay = document.getElementById('shed-theta-display'),
        shedBlockageSelect = document.getElementById('shed-blockage-select'),
        shedAngleWarning = document.getElementById('shed-angle-warning');
    const pitchedHridgeInput = document.getElementById('pitched-hridge-input'),
        pitchedHeaveInput = document.getElementById('pitched-heave-input'),
        pitchedRidgeDirectionRadios = document.querySelectorAll('input[name="pitched_ridge_direction"]'),
        pitchedBxInput = document.getElementById('pitched-bx-input'),
        pitchedByInput = document.getElementById('pitched-by-input'),
        pitchedThetaDisplay = document.getElementById('pitched-theta-display'),
        pitchedBlockageSelect = document.getElementById('pitched-blockage-select'),
        pitchedAngleWarning = document.getElementById('pitched-angle-warning');
    const troughedHridgeInput = document.getElementById('troughed-hridge-input'),
        troughedHeaveInput = document.getElementById('troughed-heave-input'),
        troughedRidgeDirectionRadios = document.querySelectorAll('input[name="troughed_ridge_direction"]'),
        troughedBxInput = document.getElementById('troughed-bx-input'),
        troughedByInput = document.getElementById('troughed-by-input'),
        troughedThetaDisplay = document.getElementById('troughed-theta-display'),
        troughedBlockageSelect = document.getElementById('troughed-blockage-select'),
        troughedAngleWarning = document.getElementById('troughed-angle-warning');
    const solidSignBhInput = document.getElementById('solid-sign-bh-input'),
        solidSignBvInput = document.getElementById('solid-sign-bv-input'),
        solidSignDInput = document.getElementById('solid-sign-d-input'),
        solidSignOpeningRatioInput = document.getElementById('solid-sign-opening-ratio-input'),
        solidSignOpeningWarning = document.getElementById('solid-sign-opening-warning'),
        solidSignHasCornerRadios = document.querySelectorAll('input[name="solid_sign_has_corner"]'),
        solidSignCornerDetails = document.getElementById('solid-sign-corner-details'),
        solidSignLrInput = document.getElementById('solid-sign-lr-input');
    const hollowSignBhInput = document.getElementById('hollow-sign-bh-input'),
        hollowSignBvInput = document.getElementById('hollow-sign-bv-input'),
        hollowSignDInput = document.getElementById('hollow-sign-d-input'),
        hollowSignOpeningRatioInput = document.getElementById('hollow-sign-opening-ratio-input'),
        hollowSignOpeningWarning = document.getElementById('hollow-sign-opening-warning'),
        hollowQzModeRadios = document.querySelectorAll('input[name="hollow_qz_mode"]'),
        hollowAutoLayerDetails = document.getElementById('hollow-auto-layer-details'),
        hollowManualInputDetails = document.getElementById('hollow-manual-input-details'),
        addHollowRowBtn = document.getElementById('add-hollow-row-btn'),
        hollowManualTableBody = document.querySelector('#hollow-manual-table tbody');
    const chimneyHeightInput = document.getElementById('chimney-height-input'),
        chimneyShapeSelect = document.getElementById('chimney-shape-select'),
        chimneyOptionsSquare = document.getElementById('chimney-options-square'),
        chimneyOptionsCircular = document.getElementById('chimney-options-circular'),
        chimneyDInput = document.getElementById('chimney-d-input'),
        chimneyDtopInput = document.getElementById('chimney-dtop-input'),
        chimneyDbotInput = document.getElementById('chimney-dbot-input'),
        chimneyLayerHeightInput = document.getElementById('chimney-layer-height-input');
    const trussShapeRadios = document.querySelectorAll('input[name="truss_shape"]'),
        addTrussRowBtn = document.getElementById('add-truss-row-btn'),
        trussManualTableBody = document.querySelector('#truss-manual-table tbody');
    const wtHeightInput = document.getElementById('wt-height-input'),
        wtClearanceInput = document.getElementById('wt-clearance-input'),
        wtLayerHeightInput = document.getElementById('wt-layer-height-input'),
        wtShapeSelect = document.getElementById('wt-shape-select'),
        wtOptionsSquare = document.getElementById('wt-options-square'),
        wtOptionsCircular = document.getElementById('wt-options-circular'),
        wtDInput = document.getElementById('wt-d-input'),
        wtDtopInput = document.getElementById('wt-dtop-input'),
        wtDbotInput = document.getElementById('wt-dbot-input'),
        wtDAvgDisplay = document.getElementById('wt-d-avg-display');
    const supportStructureSection = document.getElementById('support-structure-section'),
        supportStructureInputs = document.getElementById('support-structure-inputs'),
        supportStructureNotice = document.getElementById('support-structure-notice'),
        supportShapeSelect = document.getElementById('support-shape-select'),
        supportOptionsRectangular = document.getElementById('support-options-rectangular'),
        supportOptionsTriangular = document.getElementById('support-options-triangular');
    const waterTowerSupportSection = document.getElementById('water-tower-support-section'),
        wtSupportTypeSelect = document.getElementById('wt-support-type-select'),
        wtSupportTrussDetails = document.getElementById('wt-support-truss-details'),
        wtTrussShapeRadios = document.querySelectorAll('input[name="wt_truss_shape"]'),
        wtTrussDiagonalWindOption = document.getElementById('wt-truss-diagonal-wind-option'),
        addWtTrussRowBtn = document.getElementById('add-wt-truss-row-btn'),
        wtTrussManualTableBody = document.querySelector('#wt-truss-manual-table tbody');
    const streetLightArmShapeRadios = document.querySelectorAll('input[name="sl_arm_shape"]');
    const streetLightArmStraightDetails = document.getElementById('street-light-arm-straight-details');
    const streetLightArmCurvedDetails = document.getElementById('street-light-arm-curved-details');
    const supportHeightDisplay = document.getElementById('support-height-display');
    const allHeaveInputs = document.querySelectorAll('#shed-heave-input, #pitched-heave-input, #troughed-heave-input');
    const allDInputs = document.querySelectorAll('#solid-sign-d-input, #hollow-sign-d-input');

    // ==== ▼▼▼ START: 【核心新增 1/3】獲取示意圖相關元素 ▼▼▼ ====
    const solidSignNormalDirectionRadios = document.querySelectorAll('input[name="solid_sign_normal_direction"]');
    const geometrySketchSection = document.getElementById('geometry-sketch-section');
    // ==== ▲▲▲ END: 【核心新增 1/3】 ▲▲▲ ====

    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    let lastSuccessfulData = null;

    // ==== ▼▼▼ START: 【核心新增 2/3】更新幾何示意圖的函式 ▼▼▼ ====
    function updateGeometrySketch() {
        if (!enclosureStatusSelect || !geometrySketchSection) return;

        const selectedType = enclosureStatusSelect.value;
        let imagePath = null;
        let altText = "幾何示意圖";

        // 根據建築類型決定顯示的圖片
        if (selectedType === 'solid-sign') {
            const normalDirection = document.querySelector('input[name="solid_sign_normal_direction"]:checked').value;
            if (normalDirection === 'X') {
                imagePath = '/static/img/color/Open_SolidSigns_faceX.png';
                altText = "實體標示物，法向量為 X 方向";
            } else if (normalDirection === 'Y') {
                imagePath = '/static/img/color/Open_SolidSigns_faceY.png';
                altText = "實體標示物，法向量為 Y 方向";
            }
        }
        // 未來可以在此處為其他建築類型加入 else if 判斷
        // else if (selectedType === 'shed-roof') { ... }

        // 更新 DOM
        const container = geometrySketchSection.querySelector('.input-container');
        if (imagePath) {
            container.innerHTML = `<img src="${imagePath}" alt="${altText}" style="max-width: 100%; height: auto; border-radius: 5px;">`;
            geometrySketchSection.style.display = 'flex';
        } else {
            container.innerHTML = '<p>此建築類型暫無示意圖</p>';
            // 確保在沒有示意圖時，區塊仍然可見 (除非您想隱藏它)
            geometrySketchSection.style.display = 'flex';
        }
    }


    const validationState = {
        isShedAngleValid: true,
        isPitchedAngleValid: true,
        isTroughedAngleValid: true,
    };

    // ==== ▼▼▼ START: 【核心新增】Tab 切換邏輯 ▼▼▼ ====
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            tabContents.forEach(content => {
                if (content.id === button.dataset.target) {
                    content.classList.add('active');
                } else {
                    content.classList.remove('active');
                }
            });
        });
    });

    // ==== ▲▲▲ END: 【核心新增】 ▲▲▲ ====

    function updateCalculateButtonState() {
        // const isAllValid = Object.values(validationState).every(isValid => isValid);
    }


    // ======================================================
    // 區域 2: UI 互動邏輯
    // ======================================================

    // --- 地點與風速選擇 ---
    if (countySelect) {
        countySelect.addEventListener('change', () => {
            const selectedCounty = countySelect.value;
            townSelect.innerHTML = '<option value="">(請先選擇縣市)</option>';
            townSelect.disabled = true;
            windSpeedDisplay.textContent = '---';
            if (selectedCounty) {
                const towns = [...new Set(windSpeedsData.filter(record => record.county === selectedCounty).map(record => record.town))];
                townSelect.innerHTML = '<option value="">--- 請選擇 ---</option>';
                towns.forEach(town => {
                    const option = document.createElement('option');
                    option.value = town;
                    option.textContent = town;
                    townSelect.appendChild(option);
                });
                townSelect.disabled = false;
            }
        });
    }
    if (townSelect) {
        townSelect.addEventListener('change', () => {
            const selectedCounty = countySelect.value;
            const selectedTown = townSelect.value;
            windSpeedDisplay.textContent = '---';
            if (selectedCounty && selectedTown) {
                const record = windSpeedsData.find(r => r.county === selectedCounty && r.town === selectedTown);
                if (record) windSpeedDisplay.textContent = `${record.speed} m/s`;
            }
        });
    }

    // --- 地形參數顯示 ---
    function toggleTopoDetailsVisibility(selectElement, detailsContainer) {
        if (!selectElement || !detailsContainer) return;
        detailsContainer.style.display = selectElement.value !== 'not_considered' ? 'flex' : 'none';
    }

    if (topoSelectX) topoSelectX.addEventListener('change', () => toggleTopoDetailsVisibility(topoSelectX, topoDetailsX));
    if (topoSelectY) topoSelectY.addEventListener('change', () => toggleTopoDetailsVisibility(topoSelectY, topoDetailsY));


    // --- 頻率輸入模式 ---
    function updateFnInputs() {
        if (!manualFnInputGroup) return;
        manualFnInputGroup.style.display = (document.querySelector('input[name="fn_mode"]:checked').value === 'manual') ? 'flex' : 'none';
    }

    if (fnModeRadios) fnModeRadios.forEach(radio => radio.addEventListener('change', updateFnInputs));
    updateFnInputs();

    // --- 實體標示物內部邏輯 ---
    function validateOpeningRatio() {
        if (!solidSignOpeningRatioInput || !solidSignOpeningWarning) return;
        const ratio = parseFloat(solidSignOpeningRatioInput.value) || 0;
        if (ratio >= 30) {
            solidSignOpeningWarning.style.display = 'block';
        } else {
            solidSignOpeningWarning.style.display = 'none';
        }
    }

    function toggleCornerDetails() {
        if (!solidSignCornerDetails) return;
        const hasCorner = document.querySelector('input[name="solid_sign_has_corner"]:checked').value;
        solidSignCornerDetails.style.display = (hasCorner === 'yes') ? 'flex' : 'none';
    }

    // --- 為實體標示物的新輸入欄位綁定事件 ---
    if (solidSignOpeningRatioInput) {
        solidSignOpeningRatioInput.addEventListener('input', validateOpeningRatio);
    }
    if (solidSignHasCornerRadios) {
        solidSignHasCornerRadios.forEach(radio => {
            radio.addEventListener('change', toggleCornerDetails);
        });
    }


    function calculateRoofAngle(hRidge, hEave, bX, bY, ridgeDir, displayElem, isSymmetrical) {
        const deltaH = hRidge - hEave;
        const base = (ridgeDir === 'X') ? bY : bX;
        const effectiveBase = isSymmetrical ? base / 2 : base;
        let angleDeg = 0.0;
        if (deltaH > 0 && effectiveBase > 0) {
            angleDeg = Math.atan(deltaH / effectiveBase) * (180 / Math.PI);
            displayElem.textContent = `${angleDeg.toFixed(2)} °`;
        } else {
            displayElem.textContent = '0.00 °';
        }
        return angleDeg; // 回傳計算出的角度值
    }

    // 建立一個通用的驗證處理函式
    function handleAngleValidation(calculatorFunc, warningElem, validationKey) {
        const angle = calculatorFunc();
        // 移除 isSymmetrical 參數，因為它不再需要
        const angleLimit = validationKey.includes('Shed') ? 45 : 45; // Shed roof 也是 45
        const isValid = angle <= angleLimit;

        if (warningElem) {
            warningElem.style.display = isValid ? 'none' : 'block';
            if (!isValid) {
                warningElem.textContent = `警告：屋頂角度 ${angle.toFixed(1)}° > ${angleLimit}°，將改採實體招牌模型計算總風力。`;
            }
        }

        validationState[validationKey] = true; // ** 永遠設為 true，允許計算 **
        updateCalculateButtonState();
    }

    const getValues = (inputs) => inputs.map(el => el ? (el.type === 'radio' ? document.querySelector(`input[name="${el.name}"]:checked`).value : el.value) : null);
    const calculateShedRoofAngle = () => calculateRoofAngle(...getValues([shedHridgeInput, shedHeaveInput, shedBxInput, shedByInput, shedRidgeDirectionRadios[0]]), shedThetaDisplay, false);
    const calculatePitchedRoofAngle = () => calculateRoofAngle(...getValues([pitchedHridgeInput, pitchedHeaveInput, pitchedBxInput, pitchedByInput, pitchedRidgeDirectionRadios[0]]), pitchedThetaDisplay, true);
    const calculateTroughedRoofAngle = () => calculateRoofAngle(...getValues([troughedHridgeInput, troughedHeaveInput, troughedBxInput, troughedByInput, troughedRidgeDirectionRadios[0]]), troughedThetaDisplay, true);
    const shedInputs = [shedHridgeInput, shedHeaveInput, shedBxInput, shedByInput, ...shedRidgeDirectionRadios];
    shedInputs.forEach(el => el?.addEventListener('input', () => handleAngleValidation(calculateShedRoofAngle, shedAngleWarning, 'isShedAngleValid')));
    const pitchedInputs = [pitchedHridgeInput, pitchedHeaveInput, pitchedBxInput, pitchedByInput, ...pitchedRidgeDirectionRadios];
    pitchedInputs.forEach(el => el?.addEventListener('input', () => handleAngleValidation(calculatePitchedRoofAngle, pitchedAngleWarning, 'isPitchedAngleValid')));
    const troughedInputs = [troughedHridgeInput, troughedHeaveInput, troughedBxInput, troughedByInput, ...troughedRidgeDirectionRadios];
    troughedInputs.forEach(el => el?.addEventListener('input', () => handleAngleValidation(calculateTroughedRoofAngle, troughedAngleWarning, 'isTroughedAngleValid')));

    // --- 煙囪內部邏輯 ---
    function updateChimneyInputs() {
        if (!chimneyShapeSelect || !chimneyOptionsSquare || !chimneyOptionsCircular) return;
        const selectedShape = chimneyShapeSelect.value;
        chimneyOptionsSquare.style.display = ['square-normal', 'square-diagonal', 'hexagonal', 'octagonal'].includes(selectedShape) ? 'flex' : 'none';
        chimneyOptionsCircular.style.display = selectedShape === 'circular' ? 'flex' : 'none';
    }

    if (chimneyShapeSelect) chimneyShapeSelect.addEventListener('change', updateChimneyInputs);


    // --- 中空標示物內部 UI 邏輯 ---
    function validateHollowOpeningRatio() {
        if (!hollowSignOpeningRatioInput || !hollowSignOpeningWarning) return;
        const ratio = parseFloat(hollowSignOpeningRatioInput.value) || 0;
        hollowSignOpeningWarning.style.display = (ratio < 30) ? 'block' : 'none';
    }

    function toggleHollowQzDetails() {
        if (!hollowAutoLayerDetails || !hollowManualInputDetails) return;
        const mode = document.querySelector('input[name="hollow_qz_mode"]:checked').value;
        hollowAutoLayerDetails.style.display = (mode === 'auto') ? 'flex' : 'none';
        hollowManualInputDetails.style.display = (mode === 'manual') ? 'flex' : 'none';
    }

    function addHollowManualRow(name = '', height = '', area = '') {
        if (!hollowManualTableBody) return;
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><input type="text" class="manual-name" value="${name}" placeholder="例如：A1"></td>
            <td><input type="number" class="manual-height" value="${height}" step="0.1"></td>
            <td><input type="number" class="manual-area" value="${area}" step="0.1"></td>
            <td><button type="button" class="delete-row-btn">×</button></td>
        `;
        hollowManualTableBody.appendChild(row);
    }

    if (hollowSignOpeningRatioInput) hollowSignOpeningRatioInput.addEventListener('input', validateHollowOpeningRatio);
    if (hollowQzModeRadios) hollowQzModeRadios.forEach(radio => radio.addEventListener('change', toggleHollowQzDetails));
    if (addHollowRowBtn) addHollowRowBtn.addEventListener('click', () => addHollowManualRow());
    if (hollowManualTableBody) {
        hollowManualTableBody.addEventListener('click', (e) => {
            if (e.target.classList.contains('delete-row-btn')) e.target.closest('tr').remove();
        });
    }

    // --- 桁架高塔內部 UI 邏輯 ---
    function addTrussManualRow(tableBody, name = '', height = '', area = '') {
        if (!tableBody) return;
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><input type="text" class="manual-name" value="${name}" placeholder="例如：底段 (0-20m)"></td>
            <td><input type="number" class="manual-height" value="${height}" step="0.1" placeholder="例如：10"></td>
            <td><input type="number" class="manual-area" value="${area}" step="0.1" placeholder="例如：15.5"></td>
            <td><button type="button" class="delete-row-btn">×</button></td>
        `;
        tableBody.appendChild(row);
    }

    // ==== ▼▼▼ START: 【核心修正】讓新增按鈕能對應到正確的表格 ▼▼▼ ====
    document.querySelectorAll('.add-row-button').forEach(button => {
        // 我們只對具有 data-table-id 的按鈕 (即桁架表格的按鈕) 進行操作
        if (button.dataset.tableId) {
            button.addEventListener('click', () => {
                const tableBody = document.querySelector(`#${button.dataset.tableId} tbody`);
                if (tableBody) {
                    addTrussManualRow(tableBody);
                } else {
                    console.error(`Could not find table body for selector: #${button.dataset.tableId} tbody`);
                }
            });
        }
    });

    document.querySelectorAll('.input-table tbody').forEach(tbody => {
        tbody.addEventListener('click', (e) => {
            if (e.target.classList.contains('delete-row-btn')) {
                e.target.closest('tr').remove();
            }
        });
    });
    // ==== ▲▲▲ END: 【核心修正】 ▲▲▲ ====


    if (addTrussRowBtn) addTrussRowBtn.addEventListener('click', () => addTrussManualRow());
    if (trussManualTableBody) {
        trussManualTableBody.addEventListener('click', (e) => {
            if (e.target.classList.contains('delete-row-btn')) e.target.closest('tr').remove();
        });
    }


    // --- 水塔內部 UI 邏輯 ---
    function updateWaterTowerSupportVisibility() {
        if (!wtClearanceInput || !waterTowerSupportSection) return;
        const clearance = parseFloat(wtClearanceInput.value) || 0;
        waterTowerSupportSection.style.display = (clearance > 0) ? 'flex' : 'none';
    }

    // (本體部分，與煙囪邏輯幾乎相同，只是選擇器不同)
    function updateWaterTowerInputs() {
        if (!wtShapeSelect || !wtOptionsSquare || !wtOptionsCircular) return;
        const selectedShape = wtShapeSelect.value;
        wtOptionsSquare.style.display = ['square-normal', 'square-diagonal', 'hexagonal', 'octagonal'].includes(selectedShape) ? 'flex' : 'none';
        wtOptionsCircular.style.display = selectedShape === 'circular' ? 'flex' : 'none';
    }

    function calculateWaterTowerAverageDiameter() {
        if (!wtDtopInput || !wtDbotInput || !wtDAvgDisplay) return;
        const dTop = parseFloat(wtDtopInput.value) || 0;
        const dBot = parseFloat(wtDbotInput.value) || 0;
        const avg = (dTop + dBot) / 2;
        wtDAvgDisplay.textContent = `${avg.toFixed(3)} m`;
    }

    // (支撐結構部分)
    function toggleWaterTowerSupportDetails() {
        if (!wtSupportTypeSelect || !wtSupportTrussDetails) return;
        const supportType = wtSupportTypeSelect.value;
        wtSupportTrussDetails.style.display = (supportType === 'truss') ? 'block' : 'none';
    }


    function addWtTrussManualRow(name = '', height = '', area = '') {
        if (!wtTrussManualTableBody) return;
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><input type="text" class="manual-name" value="${name}" placeholder="例如：支撐架 (0-12m)"></td>
            <td><input type="number" class="manual-height" value="${height}" step="0.1" placeholder="例如：6"></td>
            <td><input type="number" class="manual-area" value="${area}" step="0.1" placeholder="例如：18.2"></td>
            <td><button type="button" class="delete-row-btn">×</button></td>
        `;
        wtTrussManualTableBody.appendChild(row);
    }

    function toggleWtTrussDiagonalOption() {
        const wtTrussDiagonalWindOption = document.getElementById('wt-truss-diagonal-wind-option');
        if (!wtTrussDiagonalWindOption) return;
        const shape = document.querySelector('input[name="wt_truss_shape"]:checked').value;
        wtTrussDiagonalWindOption.style.display = (shape === 'square') ? 'flex' : 'none';
    }

    if (wtClearanceInput) wtClearanceInput.addEventListener('input', updateWaterTowerSupportVisibility);
    if (wtShapeSelect) wtShapeSelect.addEventListener('change', updateWaterTowerInputs);
    if (wtDtopInput) wtDtopInput.addEventListener('input', calculateWaterTowerAverageDiameter);
    if (wtDbotInput) wtDbotInput.addEventListener('input', calculateWaterTowerAverageDiameter);
    if (wtSupportTypeSelect) wtSupportTypeSelect.addEventListener('change', toggleWaterTowerSupportDetails);
    if (wtTrussShapeRadios) wtTrussShapeRadios.forEach(r => r.addEventListener('change', toggleWtTrussDiagonalOption));
    if (addWtTrussRowBtn) addWtTrussRowBtn.addEventListener('click', () => addWtTrussManualRow());
    if (wtTrussManualTableBody) {
        wtTrussManualTableBody.addEventListener('click', (e) => {
            if (e.target.classList.contains('delete-row-btn')) e.target.closest('tr').remove();
        });
    }

    // --- 支撐結構內部邏輯 ---
    function updateSupportInputs() {
        if (!supportShapeSelect || !supportOptionsRectangular || !supportOptionsTriangular) return;
        const selectedShape = supportShapeSelect.value;
        supportOptionsRectangular.style.display = ['rectangular-column', 'h-beam'].includes(selectedShape) ? 'flex' : 'none';
        supportOptionsTriangular.style.display = selectedShape === 'triangular-column' ? 'flex' : 'none';
    }

    // ==== ▼▼▼ START: 【核心新增】處理路燈內部選項切換的函式 ▼▼▼ ====
    function updateStreetLightArmInputs() {
        if (!streetLightArmShapeRadios.length) return;
        const selectedShape = document.querySelector('input[name="sl_arm_shape"]:checked').value;
        if (streetLightArmStraightDetails) {
            streetLightArmStraightDetails.style.display = (selectedShape === 'straight') ? 'flex' : 'none';
        }
        if (streetLightArmCurvedDetails) {
            streetLightArmCurvedDetails.style.display = (selectedShape === 'curved') ? 'flex' : 'none';
        }
    }

    // ==== ▲▲▲ END: 【核心新增】 ▲▲▲ ====

    function updateSupportHeight() {
        if (!enclosureStatusSelect || !supportHeightDisplay) return;

        const selectedType = enclosureStatusSelect.value;
        let heightValue = null;

        if (['shed-roof', 'pitched-free-roof', 'troughed-free-roof'].includes(selectedType)) {
            // 根據 selectedType 動態找到對應的 heave 輸入框
            const prefix = selectedType.split('-')[0];
            const heaveInput = document.getElementById(`${prefix}-heave-input`);
            if (heaveInput) {
                heightValue = heaveInput.value;
            }
        } else if (['solid-sign', 'hollow-sign'].includes(selectedType)) {
            // 根據 selectedType 動態找到對應的 d 輸入框
            const prefix = selectedType.split('-')[0];
            const dInput = document.getElementById(`${prefix}-sign-d-input`);
            if (dInput) {
                heightValue = dInput.value;
            }
        }

        // 統一更新顯示
        if (heightValue !== null && heightValue.trim() !== '') {
            supportHeightDisplay.textContent = `${parseFloat(heightValue).toFixed(2)} m`;
        } else {
            supportHeightDisplay.textContent = '---';
        }
    }

    function masterUpdateDisplay() {
        if (!enclosureStatusSelect) return;
        const selectedType = enclosureStatusSelect.value;
        allGeometrySections.forEach(section => {
            section.style.display = section.id === `geometry-section-${selectedType.replace(/_/g, '-')}` ? 'flex' : 'none';
        });
        const needsSupportSection = ['shed-roof', 'pitched-free-roof', 'troughed-free-roof', 'solid-sign', 'hollow-sign'].includes(selectedType);
        const supportStructureSection = document.getElementById('support-structure-section');
        const supportStructureInputs = document.getElementById('support-structure-inputs');
        const supportStructureNotice = document.getElementById('support-structure-notice');

        if (supportStructureSection) supportStructureSection.style.display = needsSupportSection ? 'flex' : 'none';
        if (supportStructureInputs) supportStructureInputs.style.display = 'flex'; // 只要父容器顯示，它就應該顯示
        if (supportStructureNotice) supportStructureNotice.style.display = 'none'; // 通常不需要顯示

        const isWaterTower = selectedType === 'water-tower';
        if (waterTowerSupportSection) waterTowerSupportSection.style.display = isWaterTower ? 'flex' : 'none';


        // ==== ▼▼▼ START: 新增 fnx/fny 連動邏輯 ▼▼▼ ====
        const fnXInput = document.getElementById('fn-x-input');
        const fnYInput = document.getElementById('fn-y-input');
        if (selectedType === 'chimney') {
            fnYInput.disabled = true;
            fnYInput.value = fnXInput.value; // 確保選擇時立即同步
        } else {
            fnYInput.disabled = false;
        }
        // ==== ▲▲▲ END: 新增 fnx/fny 連動邏輯 ▲▲▲ ====

        if (selectedType === 'street-light') {
            updateStreetLightArmInputs(); // 初始化路燈的內部選項
        } else if (selectedType === 'chimney') {
            updateChimneyInputs();
            // ==== 【核心修正 2】: 移除對不存在函式的呼叫 ====
        } else if (selectedType === 'shed-roof' || selectedType === 'pitched-free-roof' || selectedType === 'troughed-free-roof') {
            updateSupportInputs();
        } else if (selectedType === 'solid-sign') {
            validateOpeningRatio();
            toggleCornerDetails();
            updateSupportInputs();
        } else if (selectedType === 'hollow-sign') {
            validateHollowOpeningRatio();
            toggleHollowQzDetails();
            updateSupportInputs();
        } else if (selectedType === 'truss-tower') {
            // 只有當桁架區塊可見時，才檢查並新增預設行
            const trussTableBodyX = document.querySelector('#truss-manual-table-x tbody');
            if (trussTableBodyX && trussTableBodyX.rows.length === 0) {
                addManualInputRow(trussTableBodyX, 'X向構件', '10', '20');
            }
            const trussTableBodyY = document.querySelector('#truss-manual-table-y tbody');
            if (trussTableBodyY && trussTableBodyY.rows.length === 0) {
                addManualInputRow(trussTableBodyY, 'Y向構件', '10', '22');
            }
        } else if (selectedType === 'water-tower') {
            updateWaterTowerInputs();
            calculateWaterTowerAverageDiameter();
            updateWaterTowerSupportVisibility();
            toggleWaterTowerSupportDetails();
            toggleWtTrussDiagonalOption(); // 確保呼叫已定義的函式
            if (wtTrussManualTableBody.rows.length === 0) {
                addWtTrussManualRow('構件名稱', '6', '15');
            }
        }
        updateGeometrySketch();
        updateSupportHeight();

        handleAngleValidation(calculateShedRoofAngle, shedAngleWarning, 'isShedAngleValid');
        handleAngleValidation(calculatePitchedRoofAngle, pitchedAngleWarning, 'isPitchedAngleValid');
        handleAngleValidation(calculateTroughedRoofAngle, troughedAngleWarning, 'isTroughedAngleValid');
    }

    const fnXInput = document.getElementById('fn-x-input');
    const fnYInput = document.getElementById('fn-y-input');
    if (fnXInput && fnYInput && enclosureStatusSelect) {
        fnXInput.addEventListener('input', () => {
            if (enclosureStatusSelect.value === 'chimney') {
                fnYInput.value = fnXInput.value;
            }
        });
    }

    if (enclosureStatusSelect) {
        enclosureStatusSelect.addEventListener('change', masterUpdateDisplay);
    }

    if (solidSignNormalDirectionRadios) {
        solidSignNormalDirectionRadios.forEach(radio => {
            radio.addEventListener('change', updateGeometrySketch);
        });
    }


    allHeaveInputs.forEach(input => {
        if (input) input.addEventListener('input', updateSupportHeight);
    });
    allDInputs.forEach(input => {
        if (input) input.addEventListener('input', updateSupportHeight);
    });


    // ==== ▼▼▼ START: 【核心新增】為路燈的 radio buttons 綁定事件監聽器 ▼▼▼ ====
    if (streetLightArmShapeRadios) {
        streetLightArmShapeRadios.forEach(radio => radio.addEventListener('change', updateStreetLightArmInputs));
    }
    // ==== ▲▲▲ END: 【核心新增】 ▲▲▲ ====


    // --- 頁面載入時的初始化呼叫 ---
    function initializeUI() {
        toggleTopoDetailsVisibility(topoSelectX, topoDetailsX);
        toggleTopoDetailsVisibility(topoSelectY, topoDetailsY);
        updateFnInputs();
        masterUpdateDisplay();
        updateSupportHeight();

        handleAngleValidation(calculateShedRoofAngle, shedAngleWarning, 'isShedAngleValid');
        handleAngleValidation(calculatePitchedRoofAngle, pitchedAngleWarning, 'isPitchedAngleValid');
        handleAngleValidation(calculateTroughedRoofAngle, troughedAngleWarning, 'isTroughedAngleValid');

        // 為尚未在 masterUpdateDisplay 中初始化的表格新增預設行區域 3
        if (hollowManualTableBody.rows.length === 0) {
            addHollowManualRow('構件XX', '10.5', '20');
        }

        // ==== ▼▼▼ START: 【核心修正】為兩個桁架表格新增預設行 ▼▼▼ ====
        const trussTableBodyX = document.querySelector('#truss-manual-table-x tbody');
        if (trussTableBodyX && trussTableBodyX.rows.length === 0) {
            addTrussManualRow(trussTableBodyX, 'X向構件', '10', '20');
        }

        const trussTableBodyY = document.querySelector('#truss-manual-table-y tbody');
        if (trussTableBodyY && trussTableBodyY.rows.length === 0) {
            addTrussManualRow(trussTableBodyY, 'Y向構件', '10', '22');
        }
        // ==== ▲▲▲ END: 【核心修正】 ▲▲▲ ====
    }

    initializeUI();


    // ======================================================
    // 區域 3: API 呼叫與結果處理
    // ======================================================
    if (calculateButton) {
        calculateButton.addEventListener('click', () => {
            const windSpeedValue = windSpeedDisplay ? windSpeedDisplay.textContent : '---';
            if (!windSpeedValue || windSpeedValue.trim() === '---') {
                alert("錯誤：未選擇工址地點或未取得基本設計風速。");
                return;
            }

            if (resultsModalBody) resultsModalBody.innerHTML = '<p class="placeholder-text">計算中，請稍候...</p>';
            if (reportButtonModal) reportButtonModal.disabled = true;
            lastSuccessfulData = null;

            // --- 建立通用的 formData ---
            let formData = {
                v10c: parseFloat(windSpeedDisplay.textContent) || 0,
                terrain: document.getElementById('terrain-select').value,
                topoX: {
                    type: document.getElementById('topo-select-x').value,
                    H: document.getElementById('topo-h-x').value,
                    Lh: document.getElementById('topo-lh-x').value,
                    x: document.getElementById('topo-x-x').value
                },
                topoY: {
                    type: document.getElementById('topo-select-y').value,
                    H: document.getElementById('topo-h-y').value,
                    Lh: document.getElementById('topo-lh-y').value,
                    x: document.getElementById('topo-x-y').value
                },
                enclosureStatus: document.getElementById('enclosure-status-select').value,
                importanceFactor: document.getElementById('importance-factor-select').value.split('_')[0],
                dampingRatio: document.getElementById('damping-ratio-select').value.split('_')[0],
                fnMode: document.querySelector('input[name="fn_mode"]:checked').value,
                fnX: document.getElementById('fn-x-input').value,
                fnY: document.getElementById('fn-y-input').value,
                ft: document.getElementById('fn-t-input').value,
                geometryData: {}
            };

            const selectedType = formData.enclosureStatus;

            // --- 根據建築物類型，填充 geometryData ---
            if (selectedType === 'shed-roof' || selectedType === 'pitched-free-roof' || selectedType === 'troughed-free-roof' || selectedType === 'solid-sign' || selectedType === 'hollow-sign') {

                const supportData = {
                    shape: document.getElementById('support-shape-select').value,
                    h: parseFloat(supportHeightDisplay.textContent) || 0,
                    dtop_x: parseFloat(document.getElementById('support-dtop-x-input').value) || 0,
                    dbot_x: parseFloat(document.getElementById('support-dbot-x-input').value) || 0,
                    dtop_y: parseFloat(document.getElementById('support-dtop-y-input').value) || 0,
                    dbot_y: parseFloat(document.getElementById('support-dbot-y-input').value) || 0,
                    layer_height: parseFloat(document.getElementById('support-layer-height-input').value) || 2.0
                };

                if (selectedType.includes('roof')) {
                    const prefix = selectedType.split('-')[0]; // 'shed', 'pitched', 'troughed'
                    formData.geometryData = {
                        roof: {
                            h_ridge: parseFloat(document.getElementById(`${prefix}-hridge-input`).value) || 0,
                            h_eave: parseFloat(document.getElementById(`${prefix}-heave-input`).value) || 0,
                            ridge_direction: document.querySelector(`input[name="${prefix}_ridge_direction"]:checked`).value,
                            b_x: parseFloat(document.getElementById(`${prefix}-bx-input`).value) || 0,
                            b_y: parseFloat(document.getElementById(`${prefix}-by-input`).value) || 0,
                            theta: parseFloat(document.getElementById(`${prefix}-theta-display`).textContent) || 0,
                            blockage: document.getElementById(`${prefix}-blockage-select`).value
                        },
                        support: supportData
                    };
                } else if (selectedType.includes('sign')) {
                    const prefix = selectedType.split('-')[0]; // 'solid', 'hollow'
                    let signData = {
                        b_h: parseFloat(document.getElementById(`${prefix}-sign-bh-input`).value) || 0,
                        b_v: parseFloat(document.getElementById(`${prefix}-sign-bv-input`).value) || 0,
                        d: parseFloat(document.getElementById(`${prefix}-sign-d-input`).value) || 0,
                        normal_direction: document.querySelector(`input[name="${prefix}_sign_normal_direction"]:checked`).value,
                        opening_ratio: parseFloat(document.getElementById(`${prefix}-sign-opening-ratio-input`).value) || 0,
                    };
                    if (selectedType === 'solid-sign') {
                        signData.has_corner = document.querySelector('input[name="solid_sign_has_corner"]:checked').value === 'yes';
                        signData.lr = parseFloat(document.getElementById('solid-sign-lr-input').value) || 0;
                    }
                    if (selectedType === 'hollow-sign') {
                        signData.qz_mode = document.querySelector('input[name="hollow_qz_mode"]:checked').value;
                        signData.layer_height = parseFloat(document.getElementById('hollow-layer-height-input').value) || 2.0;
                        const manualInputs = [];
                        document.querySelectorAll('#hollow-manual-table tbody tr').forEach(row => {
                            const name = row.querySelector('.manual-name').value;
                            const height = parseFloat(row.querySelector('.manual-height').value);
                            const area = parseFloat(row.querySelector('.manual-area').value);
                            if (name && !isNaN(height) && !isNaN(area)) {
                                manualInputs.push({name, height, area});
                            }
                        });
                        signData.manual_inputs = manualInputs;
                    }
                    formData.geometryData = {
                        sign: signData,
                        support: supportData
                    };
                }
            } else if (selectedType === 'chimney') {
                formData.geometryData = {
                    h: parseFloat(document.getElementById('chimney-height-input').value) || 0,
                    shape: document.getElementById('chimney-shape-select').value,
                    D: parseFloat(document.getElementById('chimney-d-input').value) || 0,
                    D_top: parseFloat(document.getElementById('chimney-dtop-input').value) || 0,
                    D_bot: parseFloat(document.getElementById('chimney-dbot-input').value) || 0,
                    roughness: document.getElementById('chimney-roughness-select').value,
                    layer_height: parseFloat(document.getElementById('chimney-layer-height-input').value) || 2.0
                };
            } else if (selectedType === 'truss-tower') {
                const manualInputsX = [];
                document.querySelectorAll('#truss-manual-table-x tbody tr').forEach(row => {
                    const name = row.querySelector('.manual-name').value;
                    const height = parseFloat(row.querySelector('.manual-height').value);
                    const area = parseFloat(row.querySelector('.manual-area').value);
                    if (name && !isNaN(height) && !isNaN(area)) {
                        manualInputsX.push({name, height, area});
                    }
                });
                const manualInputsY = [];
                document.querySelectorAll('#truss-manual-table-y tbody tr').forEach(row => {
                    const name = row.querySelector('.manual-name').value;
                    const height = parseFloat(row.querySelector('.manual-height').value);
                    const area = parseFloat(row.querySelector('.manual-area').value);
                    if (name && !isNaN(height) && !isNaN(area)) {
                        manualInputsY.push({name, height, area});
                    }
                });
                formData.geometryData = {
                    shape: document.querySelector('input[name="truss_shape"]:checked').value,
                    solidity_ratio: parseFloat(document.getElementById('truss-solidity-ratio-input').value) || 0,
                    member_shape: document.querySelector('input[name="truss_member_shape"]:checked').value,
                    manual_inputs_x: manualInputsX,
                    manual_inputs_y: manualInputsY
                };
            } else if (selectedType === 'water-tower') {
                const clearanceHeight = parseFloat(document.getElementById('wt-clearance-input').value) || 0;
                let supportData = null;
                if (clearanceHeight > 0) {
                    const supportType = document.getElementById('wt-support-type-select').value;
                    if (supportType === 'truss') {
                        const manualInputs = [];
                        document.querySelectorAll('#wt-truss-manual-table tbody tr').forEach(row => {
                            const name = row.querySelector('.manual-name').value;
                            const height = parseFloat(row.querySelector('.manual-height').value);
                            const area = parseFloat(row.querySelector('.manual-area').value);
                            if (name && !isNaN(height) && !isNaN(area)) {
                                manualInputs.push({name, height, area});
                            }
                        });
                        supportData = {
                            shape: document.querySelector('input[name="wt_truss_shape"]:checked').value,
                            solidity_ratio: parseFloat(document.getElementById('wt-truss-solidity-ratio-input').value) || 0,
                            member_shape: document.querySelector('input[name="wt_truss_member_shape"]:checked').value,
                            manual_inputs: manualInputs
                        };
                    }
                }
                formData.geometryData = {
                    body: {
                        h: (parseFloat(document.getElementById('wt-height-input').value) || 0) - clearanceHeight,
                        C: clearanceHeight,
                        shape: document.getElementById('wt-shape-select').value,
                        D: parseFloat(document.getElementById('wt-d-input').value) || 0,
                        D_top: parseFloat(document.getElementById('wt-dtop-input').value) || 0,
                        D_bot: parseFloat(document.getElementById('wt-dbot-input').value) || 0,
                        roughness: document.getElementById('wt-roughness-select').value,
                        layer_height: parseFloat(document.getElementById('wt-layer-height-input').value) || 2.0
                    },
                    support: {
                        type: supportData ? 'truss' : 'none',
                        truss_params: supportData
                    }
                };
            }

            // --- 發送請求 ---
            fetch('/windTW/calculate_open/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrftoken},
                body: JSON.stringify(formData)
            })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(err => {
                            throw new Error(err.message);
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.status === 'success') {
                        lastSuccessfulData = {inputs: formData, results: data};
                        if (reportButtonModal) reportButtonModal.disabled = false;
                        displayOpenBuildingResults(data);
                    } else {
                        resultsModalBody.innerHTML = `<p class="result-message error">計算失敗: ${data.message}</p>`;
                    }
                    showResultsModal();
                })
                .catch(error => {
                    console.error('Fetch Error:', error);
                    resultsModalBody.innerHTML = `<p class="result-message error">請求錯誤: ${error.message}</p>`;
                    showResultsModal();
                });
        });
    }

    // ======================================================
    // 區域 4 & 5: 結果顯示與報告書邏輯
    // ======================================================
    if (reportButtonModal) {
        reportButtonModal.addEventListener('click', () => {
            if (!lastSuccessfulData) {
                alert("沒有可用的計算結果可生成報告。");
                return;
            }

            const inputs = lastSuccessfulData.inputs;
            const results = lastSuccessfulData.results;
            const currentCounty = document.getElementById('county-select').value;
            const currentTown = document.getElementById('town-select').value;

            const params = new URLSearchParams({
                county: currentCounty,
                town: currentTown,
                v10c: inputs.v10c,
                terrain: inputs.terrain,
                topo_x_type: inputs.topoX.type,
                topo_x_h: inputs.topoX.H,
                topo_x_lh: inputs.topoX.Lh,
                topo_x_x: inputs.topoX.x,
                topo_y_type: inputs.topoY.type,
                topo_y_h: inputs.topoY.H,
                topo_y_lh: inputs.topoY.Lh,
                topo_y_x: inputs.topoY.x,
                enclosureStatus: inputs.enclosureStatus,
                importanceFactor: inputs.importanceFactor,
                dampingRatio: inputs.dampingRatio,
                fnX: inputs.fnX,
                fnY: inputs.fnY,
                calculated_h: results.calculated_h || 0,
            });

            if (['shed-roof', 'pitched-free-roof', 'troughed-free-roof'].includes(inputs.enclosureStatus)) {
                const geo = inputs.geometryData.roof;
                params.append('geo_h_ridge', geo.h_ridge);
                params.append('geo_h_eave', geo.h_eave);
                params.append('geo_ridge_direction', geo.ridge_direction);
                params.append('geo_b_x', geo.b_x);
                params.append('geo_b_y', geo.b_y);
                params.append('geo_theta', geo.theta);
                params.append('geo_blockage', geo.blockage);
            } else if (inputs.enclosureStatus === 'chimney') {
                const geo = inputs.geometryData;
                params.append('geo_shape', geo.shape);
                params.append('geo_d_top', geo.D_top);
                params.append('geo_d_bot', geo.D_bot);
                params.append('geo_roughness', geo.roughness);
                params.append('geo_d', geo.D);
            } else if (inputs.enclosureStatus === 'solid-sign' || inputs.enclosureStatus === 'hollow-sign') {
                const geo = inputs.geometryData.sign;
                params.append('geo_b_h', geo.b_h);
                params.append('geo_b_v', geo.b_v);
                params.append('geo_d', geo.d);
                params.append('geo_normal_direction', geo.normal_direction);
                params.append('geo_opening_ratio', geo.opening_ratio);
                if (inputs.enclosureStatus === 'solid-sign') {
                    params.append('geo_has_corner', geo.has_corner ? 'yes' : 'no');
                    params.append('geo_lr', geo.lr);
                }
                if (inputs.enclosureStatus === 'hollow-sign') {
                    params.append('geo_qz_mode', geo.qz_mode);
                }
                const supportGeo = inputs.geometryData.support;
                if (supportGeo) {
                    params.append('support_shape', supportGeo.shape);
                    params.append('support_h', supportGeo.h);
                    params.append('support_dtop_x', supportGeo.dtop_x);
                    params.append('support_dbot_x', supportGeo.dbot_x);
                    params.append('support_dtop_y', supportGeo.dtop_y);
                    params.append('support_dbot_y', supportGeo.dbot_y);
                }
            } else if (inputs.enclosureStatus === 'truss-tower') {
                const geo = inputs.geometryData;
                params.append('geo_shape', geo.shape);
                params.append('geo_solidity_ratio', geo.solidity_ratio);
                params.append('geo_member_shape', geo.member_shape);
                params.append('geo_manual_inputs_x', JSON.stringify(geo.manual_inputs_x));
                params.append('geo_manual_inputs_y', JSON.stringify(geo.manual_inputs_y));
            }

            const reportUrl = `/windTW/report_open/?${params.toString()}`;
            window.open(reportUrl, '_blank', 'width=900,height=800,scrollbars=yes,resizable=yes');
        });
    }

    function renderRoofResults(roofRes, roofType) {
        let html = `<h4>${roofType} 主風力抵抗系統 (MWFRS)</h4>`;

        if (roofRes.solid_sign_method_results) {
            const ssr = roofRes.solid_sign_method_results;
            html += `<p class="validation-error" style="text-align: left; width: 100%; margin-bottom: 15px;">${ssr.message}</p>`;
            html += `<table class="results-table"><tbody>
                <tr><th>計算模型</th><td>實體招牌 (Solid Sign)</td></tr>
                <tr><th>風力係數 C<sub>f</sub></th><td>${ssr.cf.toFixed(3)}</td></tr>
                <tr><th>陣風反應因子 G/Gf</th><td>${ssr.gust_factor.toFixed(3)}</td></tr>
                <tr><th>參考風壓 q<sub>z</sub></th><td>${ssr.q_h_for_sign.toFixed(2)} kgf/m²</td></tr>
                <tr style="background-color: #d4edda; color: #155724;"><th style="font-weight: bold;">總水平風力 F</th><td style="font-weight: bold; font-size: 1.1em;">${ssr.total_force.toFixed(2)} kgf</td></tr>
            </tbody></table>`;
        } else {
            const perp = roofRes.roof_pressure_perpendicular || roofRes.roof_pressure_perpendicular_note4;
            if (perp) {
                const main = perp.main_params;
                html += `<p><strong>風向垂直於屋脊${roofRes.roof_pressure_perpendicular_note4 ? ' (依據 Note 4)' : ''}:</strong></p>`;
                if (main) html += `<p class="calc-basis">計算基於: q(h)=${main.q_h.toFixed(2)} kgf/m², G/Gf=${main.gust_factor.toFixed(3)} (${main.rigidity})</p>`;
                html += `<ul style="list-style-position: inside;">`;
                if (perp.gamma_0) {
                    html += `<li>風向角 γ=0°: p<sub>NW</sub>=${perp.gamma_0.cnw_a.toFixed(2)} (A) / ${perp.gamma_0.cnw_b.toFixed(2)} (B), p<sub>NL</sub>=${perp.gamma_0.cnl_a.toFixed(2)} (A) / ${perp.gamma_0.cnl_b.toFixed(2)} (B)</li>`;
                    html += `<li>風向角 γ=180°: p<sub>NW</sub>=${perp.gamma_180.cnw_a.toFixed(2)} (A) / ${perp.gamma_180.cnw_b.toFixed(2)} (B), p<sub>NL</sub>=${perp.gamma_180.cnl_a.toFixed(2)} (A) / ${perp.gamma_180.cnl_b.toFixed(2)} (B)</li>`;
                } else if (perp.pressures) {
                    html += `<li>p<sub>NW</sub>=${perp.pressures.cnw_a.toFixed(2)} (A) / ${perp.pressures.cnw_b.toFixed(2)} (B)</li>`;
                    html += `<li>p<sub>NL</sub>=${perp.pressures.cnl_a.toFixed(2)} (A) / ${perp.pressures.cnl_b.toFixed(2)} (B)</li>`;
                }
                html += `</ul>`;
            }

            const para = roofRes.roof_pressure_parallel;
            if (para) {
                const main = para.main_params;
                html += `<p style="margin-top:10px;"><strong>風向平行於屋脊:</strong></p>`;
                if (main) html += `<p class="calc-basis">計算基於: q(h)=${main.q_h.toFixed(2)} kgf/m², G/Gf=${main.gust_factor.toFixed(3)} (${main.rigidity})</p>`;
                html += `<ul style="list-style-position: inside;">`;
                if (para.zones.lt_h) html += `<li>區域 (< h): p<sub>N</sub>=${para.zones.lt_h.cn_a.toFixed(2)} (A) / ${para.zones.lt_h.cn_b.toFixed(2)} (B)</li>`;
                if (para.zones.gt_h_lt_2h) html += `<li>區域 (>h, <2h): p<sub>N</sub>=${para.zones.gt_h_lt_2h.cn_a.toFixed(2)} (A) / ${para.zones.gt_h_lt_2h.cn_b.toFixed(2)} (B)</li>`;
                if (para.zones.gt_2h) html += `<li>區域 (>2h): p<sub>N</sub>=${para.zones.gt_2h.cn_a.toFixed(2)} (A) / ${para.zones.gt_2h.cn_b.toFixed(2)} (B)</li>`;
                html += `</ul>`;
            }
        }
        return html;
    }

    // ** 渲染函式: 支撐結構 (通用) **
    function renderSupportResults(supportResults) {
        let html = '';
        // console.log("哈囉你好嗎", supportResults.cf_x_wind)
        if (supportResults && Object.keys(supportResults).length > 0) {
            html += `<hr style="margin: 20px 0;"><h4>支撐結構風力</h4>`;
            if (supportResults.x_wind) {
                const resX = supportResults.x_wind;
                html += `<p><strong>X 向風作用:</strong> F = <strong>${resX.force.toFixed(2)} kgf</strong> <br><small>(Cf=${resX.cf.toFixed(3)}, G/Gf=${resX.g_factor.toFixed(3)}, q(z)=${resX.q_z.toFixed(2)}, Area=${resX.area.toFixed(2)}m², ${resX.rigidity})</small></p>`;
            }
            if (supportResults.y_wind) {
                const resY = supportResults.y_wind;
                html += `<p><strong>Y 向風作用:</strong> F = <strong>${resY.force.toFixed(2)} kgf</strong> <br><small>(Cf=${resY.cf.toFixed(3)}, G/Gf=${resY.g_factor.toFixed(3)}, q(z)=${resY.q_z.toFixed(2)}, Area=${resY.area.toFixed(2)}m², ${resY.rigidity})</small></p>`;
            }
        }
        return html;
    }

    function displayOpenBuildingResults(data) {
        if (!resultsModalBody) return;

        let resultHTML = `<p class="result-message success">計算成功！</p>`;
        const cases = data.data_by_case;
        console.log(cases)

        for (const caseId in cases) {
            if (cases.hasOwnProperty(caseId)) {
                const res = cases[caseId];
                if (!res) continue;

                resultHTML += `<hr style="margin: 20px 0; border-top: 2px solid #457b9d;">`;
                resultHTML += `<h3 style="background-color: #e0e0e0; padding: 8px; border-radius: 4px;">工況: ${caseId}</h3>`;

                // --- 渲染主要結構的結果 ---
                if (res.shed_roof_results) {
                    resultHTML += renderRoofResults(res.shed_roof_results, '單斜式屋頂');
                } else if (res.pitched_roof_results) {
                    resultHTML += renderRoofResults(res.pitched_roof_results, 'Pitched Roof');
                } else if (res.troughed_roof_results) {
                    resultHTML += renderRoofResults(res.troughed_roof_results, 'Troughed Roof');
                } else if (res.hollow_sign_results) {
                    const hollowRes = res.hollow_sign_results;
                    resultHTML += `<h4>中空標示物風力計算結果</h4><p>實體率 φ = <strong>${hollowRes.solidity_ratio.toFixed(3)}</strong></p><p>風力係數 C<sub>f</sub> = <strong>${hollowRes.cf_value.toFixed(3)}</strong></p><p style="font-size: 1.2em; color: #e63946;">總設計風力 F = <strong>${hollowRes.total_force.toFixed(2)} kgf</strong></p>`;
                    if (hollowRes.details && hollowRes.details.length > 0) {
                        resultHTML += `<h5 style="margin-top:15px;">計算細節</h5><table class="results-table"><thead><tr><th>分層/構材</th><th>高度範圍 (m)</th><th>有效高度 z (m)</th><th>風壓 q(z) (kgf/m²)</th><th>作用面積 (m²)</th><th>風力 (kgf)</th></tr></thead><tbody>`;
                        hollowRes.details.forEach(detail => {
                            resultHTML += `<tr><td>${detail.layer}</td><td>${detail.z_range}</td><td>${detail.z_eff.toFixed(2)}</td><td>${detail.q_z.toFixed(2)}</td><td>${detail.area.toFixed(2)}</td><td>${detail.force.toFixed(2)}</td></tr>`;
                        });
                        resultHTML += `</tbody></table>`;
                    }
                } else if (res.chimney_results) {
                    const cRes = res.chimney_results;
                    resultHTML += `<h4>煙囪風力計算結果</h4><p style="font-size: 1.2em; color: #e63946;">總設計風力 F = <strong>${cRes.total_force.toFixed(2)} kgf</strong></p>`;
                    if (cRes.details && cRes.details.length > 0) {
                        resultHTML += `<h5 style="margin-top:15px;">計算細節</h5><table class="results-table"><thead><tr><th>分段高度 (m)</th><th>中心高度 z (m)</th><th>風壓 q(z) (kgf/m²)</th><th>風力係數 C<sub>f</sub></th><th>投影面積 A<sub>f</sub> (m²)</th><th>風力 (kgf)</th></tr></thead><tbody>`;
                        cRes.details.forEach(detail => {
                            resultHTML += `<tr><td>${detail.z_range}</td><td>${detail.z_eff.toFixed(2)}</td><td>${detail.q_z.toFixed(2)}</td><td>${detail.cf.toFixed(3)}</td><td>${detail.area.toFixed(2)}</td><td>${detail.force.toFixed(2)}</td></tr>`;
                        });
                        resultHTML += `</tbody></table>`;
                    }
                } else if (res.water_tower_results) {
                    const wtRes = res.water_tower_results;
                    if (wtRes.body_results) {
                        resultHTML += `<h4>水塔本體風力計算結果</h4><p>風力係數 C<sub>f</sub> = <strong>${wtRes.body_results.cf.toFixed(3)}</strong></p><p style="font-size: 1.2em; color: #e63946;">總設計風力 F = <strong>${wtRes.body_results.total_force.toFixed(2)} kgf</strong></p>`;
                        if (wtRes.body_results.details && wtRes.body_results.details.length > 0) {
                            resultHTML += `<h5 style="margin-top:15px;">本體計算細節</h5><table class="results-table"><thead><tr><th>分段高度 (m)</th><th>中心高度 z (m)</th><th>風壓 q(z) (kgf/m²)</th><th>投影面積 A<sub>f</sub> (m²)</th><th>風力 (kgf)</th></tr></thead><tbody>`;
                            wtRes.body_results.details.forEach(detail => {
                                resultHTML += `<tr><td>${detail.z_range}</td><td>${detail.z_eff.toFixed(2)}</td><td>${detail.q_z.toFixed(2)}</td><td>${detail.area.toFixed(2)}</td><td>${detail.force.toFixed(2)}</td></tr>`;
                            });
                            resultHTML += `</tbody></table>`;
                        }
                    }
                } else if (res.truss_tower_results) {
                    const trussRes = res.truss_tower_results;
                    resultHTML += `<h4>桁架高塔風力計算</h4><p>基礎 C<sub>f</sub>=${trussRes.cf_normal.toFixed(3)}, 對角線修正 C=${trussRes.correction_factor.toFixed(3)}, 設計 C<sub>f,diag</sub>=<strong>${trussRes.cf_diagonal.toFixed(3)}</strong>, G=<strong>${trussRes.gust_factor.toFixed(3)}</strong></p>`;
                    if (trussRes.details && trussRes.details.length > 0) {
                        resultHTML += `<h5 style="margin-top:15px;">設計風力計算細節</h5><table class="results-table"><thead><tr><th>構材</th><th>z(m)</th><th>A<sub>f</sub>(m²)</th><th>K(z)</th><th>K<sub>zt</sub></th><th>q(z)</th><th>F(t)</th><th>FxC(t)</th></tr></thead><tbody>`;
                        trussRes.details.forEach(detail => {
                            resultHTML += `<tr><td>${detail.name}</td><td>${detail.z_eff.toFixed(2)}</td><td>${detail.area.toFixed(2)}</td><td>${detail.K_z.toFixed(3)}</td><td>${detail.Kzt.toFixed(3)}</td><td>${detail.q_z.toFixed(2)}</td><td>${(detail.force_normal / 1000).toFixed(3)}</td><td style="font-weight: bold;">${(detail.force_diagonal / 1000).toFixed(3)}</td></tr>`;
                        });
                        resultHTML += `</tbody><tfoot><tr style="background-color: #f8f9fa;"><th colspan="6">總計 (t)</th><td>${(trussRes.total_force_normal / 1000).toFixed(3)}</td><td style="font-weight: bold;">${(trussRes.total_force_diagonal / 1000).toFixed(3)}</td></tr></tfoot></table>`;
                    }
                }

                // --- 統一的支撐結構渲染 ---
                let supportResults = null;
                if (res.support_force_results) {
                    supportResults = res.support_force_results;
                } else {
                    for (const key in res) {
                        if (res[key] && res[key].support_force_results) {
                            supportResults = res[key].support_force_results;
                            break;
                        }
                    }
                }

                resultHTML += renderSupportResults(supportResults);
            }
        }
        resultsModalBody.innerHTML = resultHTML;
    }


    function setupModal(triggerId, modalId) {
        const modal = document.getElementById(modalId);
        const openLink = document.getElementById(triggerId);
        if (!openLink) return; // 如果 trigger 不存在，直接返回
        const closeButton = modal ? modal.querySelector('.close-button') : null;
        if (!modal || !closeButton) return;

        openLink.addEventListener('click', (event) => {
            event.preventDefault();
            modal.style.display = 'flex';
            document.body.classList.add('modal-open');
        });
        const closeModal = () => {
            modal.style.display = 'none';
            if (!document.querySelector('.modal[style*="display: flex"]')) {
                document.body.classList.remove('modal-open');
            }
        };
        closeButton.addEventListener('click', closeModal);
        modal.addEventListener('click', (event) => {
            if (event.target === modal) closeModal();
        });
    }


// **修正點**: 移除對不存在的 'show-height-modal-link' 的呼叫
    setupModal('show-topo-modal-link', 'topo-modal');
    setupModal('show-fn-modal-link', 'fn-modal');

    const showResultsModal = () => {
        if (resultsModal) {
            resultsModal.style.display = 'flex';
            document.body.classList.add('modal-open');
        }
    };
    const closeResultsModal = () => {
        if (resultsModal) {
            resultsModal.style.display = 'none';
            if (!document.querySelector('.modal[style*="display: flex"]')) {
                document.body.classList.remove('modal-open');
            }
        }
    };

    if (closeResultsModalBtn) {
        closeResultsModalBtn.addEventListener('click', closeResultsModal);
    }
    if (resultsModal) {
        resultsModal.addEventListener('click', (event) => {
            if (event.target === resultsModal) {
                closeResultsModal();
            }
        });
    }
    setupModal('show-hollow-qz-modal-link', 'hollow-qz-modal');


// ======================================================
// ==== END: 修正区域 4 & 5 ====
// ======================================================

})
;