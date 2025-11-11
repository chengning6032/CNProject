// static/js/Wind_TW/main.js (完整替換)

document.addEventListener('DOMContentLoaded', () => {

    // ======================================================
    // 區域 1: 元素獲取
    // ======================================================
    const countySelect = document.getElementById('county-select');
    const townSelect = document.getElementById('town-select');
    const windSpeedDisplay = document.getElementById('wind-speed-display');
    const topoSelectX = document.getElementById('topo-select-x');
    const topoDetailsX = document.getElementById('topo-details-x');
    const topoSelectY = document.getElementById('topo-select-y');
    const topoDetailsY = document.getElementById('topo-details-y');
    const roofShapeSelect = document.getElementById('roof-shape-select');
    const eaveHeightGroup = document.getElementById('eave-height-group');
    const ridgeHeightGroup = document.getElementById('ridge-height-group');
    const buildingHeightOptionsGroup = document.getElementById('building-height-options-group');
    const manualHeightInputGroup = document.getElementById('manual-height-input-group');
    const ridgeDirectionGroup = document.getElementById('ridge-direction-group');
    const hipRoofOptionsGroup = document.getElementById('hip-roof-options-group');
    const hipTopPlaneGroup = document.getElementById('hip-top-plane-group');
    const hipRidgeOptionsGroup = document.getElementById('hip-ridge-options-group');
    const spanCountGroup = document.getElementById('span-count-group');
    const irregularSawtoothContainer = document.getElementById('sawtooth-irregular-table-container');
    const archedRoofOptionsGroup = document.getElementById('arched-roof-options-group');
    const sawtoothValidationError = document.getElementById('sawtooth-validation-error');
    const buildingDimsGroup = document.getElementById('building-dims-group');
    const ridgeHeightLabel = document.getElementById('ridge-height-label');
    const ridgeDirectionLabel = document.getElementById('ridge-direction-label');
    const spanCountInput = document.getElementById('span-count-input');
    const buildingDimXInput = document.getElementById('building-dim-x-input');
    const buildingDimYInput = document.getElementById('building-dim-y-input');
    const hipTopTypeRadios = document.querySelectorAll('input[name="hip_top_type"]');
    const ridgeDirectionRadios = document.querySelectorAll('input[name="ridge_direction"]');
    const buildingHeightModeRadios = document.querySelectorAll('input[name="building_height_mode"]');
    const overhangOptionsGroup = document.getElementById('overhang-options-group');
    const fnModeRadios = document.querySelectorAll('input[name="fn_mode"]');
    const manualFnInputGroup = document.getElementById('manual-fn-input-group');
    const gableDetailRadios = document.querySelectorAll('input[name="simplify_gable"]');
    const lowRiseRadios = document.querySelectorAll('input[name="calculation_method"]');
    const lowRiseEligibilityNotice = document.getElementById('low-rise-eligibility-notice');
    // ** 核心修改: 獲取新的合併選項 **
    const asce7CandCRadios = document.querySelectorAll('input[name="use_asce7_c_and_c"]');

    const calculateButton = document.getElementById('calculate-button');
    const resultsModal = document.getElementById('results-modal');
    const resultsModalBody = document.getElementById('results-modal-body');
    const reportButtonModal = document.getElementById('report-button-modal');
    const closeResultsModalBtn = document.getElementById('close-results-modal-btn');
    const topoModal = document.getElementById('topo-modal');
    const heightModal = document.getElementById('height-modal');
    const fnModal = document.getElementById('fn-modal');
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]') ? document.querySelector('[name=csrfmiddlewaretoken]').value : '';
    let lastSuccessfulData = null;

    const angleDisplayGroupSingle = document.getElementById('angle-display-group-single');
    const angleDisplayGroupHip = document.getElementById('angle-display-group-hip');
    const angleDisplayTheta = document.getElementById('angle-display-theta');
    const angleDisplayHip = document.getElementById('angle-display-hip');
    const geometryAngleWarning = document.getElementById('geometry-angle-warning');

    const buildingSchematicContainer = document.getElementById('building-schematic-container');
    const buildingSchematicImg = document.getElementById('building-schematic-img');

    // ======================================================
    // 區域 2: UI 互動邏輯
    // ======================================================

    function updateBuildingSchematicImage() {
        if (!roofShapeSelect || !buildingSchematicContainer || !buildingSchematicImg) return;
        const shape = roofShapeSelect.value;
        const hasOverhang = document.querySelector('input[name="has_overhang"]:checked')?.value === 'true';
        let ridgeDirection = '';
        if (shape === 'hip') {
            ridgeDirection = document.querySelector('input[name="ridge_direction_hip"]:checked')?.value;
        } else {
            ridgeDirection = document.querySelector('input[name="ridge_direction"]:checked')?.value;
        }
        let imageName = null;
        if (shape === 'flat') {
            imageName = 'Flat_roof_building.png';
        } else {
            const supportedShapes = ['gable', 'hip', 'arched', 'shed', 'sawtooth_uniform'];
            if (supportedShapes.includes(shape) && ridgeDirection) {
                const shapeCapitalized = shape.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join('_');
                const overhangSuffix = (shape === 'gable' || shape === 'hip') && hasOverhang ? '_overhang' : '';
                imageName = `${shapeCapitalized}_roof_${ridgeDirection}_ridge${overhangSuffix}_building.png`;
            }
        }

        if (imageName) {
            buildingSchematicImg.src = `/static/img/color/${imageName}`;
            buildingSchematicImg.alt = `示意圖: ${shape} 屋頂, ${ridgeDirection}向屋脊${hasOverhang ? ', 有懸挑' : ''}`;
            buildingSchematicContainer.style.display = 'block';
        } else {
            buildingSchematicContainer.style.display = 'none';
            buildingSchematicImg.src = '';
            buildingSchematicImg.alt = '建築幾何示意圖';
        }
    }

    function calculateAndDisplayAngles() {
        const roofShape = roofShapeSelect.value;
        const eaveHeight = parseFloat(document.getElementById('eave-height-input').value) || 0;
        const ridgeHeight = parseFloat(document.getElementById('ridge-height-input').value) || eaveHeight;
        const dimX = parseFloat(buildingDimXInput.value) || 0;
        const dimY = parseFloat(buildingDimYInput.value) || 0;
        const ridgeDirection = document.querySelector('input[name="ridge_direction"]:checked')?.value;
        let theta = 0;
        let theta_x = 0;
        let theta_y = 0;

        if (ridgeHeight > eaveHeight) {
            const delta_h = ridgeHeight - eaveHeight;
            if (roofShape === 'hip') {
                const topType = document.querySelector('input[name="hip_top_type"]:checked').value;
                if (topType === 'plane') {
                    const planeDimX = parseFloat(document.getElementById('hip-plane-x-input').value) || 0;
                    const planeDimY = parseFloat(document.getElementById('hip-plane-y-input').value) || 0;
                    if (dimY > planeDimY) theta_x = Math.atan(delta_h / ((dimY - planeDimY) / 2)) * (180 / Math.PI);
                    if (dimX > planeDimX) theta_y = Math.atan(delta_h / ((dimX - planeDimX) / 2)) * (180 / Math.PI);
                } else {
                    const ridgeDirHip = document.querySelector('input[name="ridge_direction_hip"]:checked').value;
                    const ridgeLength = parseFloat(document.getElementById('hip-ridge-length-input').value) || 0;
                    if (ridgeDirHip === 'X') {
                        if (dimY > 0) theta_x = Math.atan(delta_h / (dimY / 2)) * (180 / Math.PI);
                        if (dimX > ridgeLength) theta_y = Math.atan(delta_h / ((dimX - ridgeLength) / 2)) * (180 / Math.PI);
                    } else {
                        if (dimX > 0) theta_y = Math.atan(delta_h / (dimX / 2)) * (180 / Math.PI);
                        if (dimY > ridgeLength) theta_x = Math.atan(delta_h / ((dimY - ridgeLength) / 2)) * (180 / Math.PI);
                    }
                }
            } else {
                let base_width = (ridgeDirection === 'X') ? dimY : dimX;
                if (roofShape === "sawtooth_uniform") {
                    const numSpans = parseInt(spanCountInput.value) || 1;
                    base_width /= numSpans;
                }
                if (base_width > 0) {
                    if (roofShape === 'shed') {
                        theta = Math.atan(delta_h / base_width) * (180 / Math.PI);
                    } else if (['gable', 'arched', 'sawtooth_uniform'].includes(roofShape)) {
                        const half_base = base_width / 2;
                        if (half_base > 0) theta = Math.atan(delta_h / half_base) * (180 / Math.PI);
                    }
                }
            }
        }
        angleDisplayTheta.textContent = `${theta.toFixed(2)}°`;
        angleDisplayHip.textContent = `θx: ${theta_x.toFixed(2)}°, θy: ${theta_y.toFixed(2)}°`;

        return {theta, theta_x, theta_y};
    }

    if (countySelect) {
        countySelect.addEventListener('change', () => {
            const selectedCounty = countySelect.value;
            townSelect.innerHTML = '<option value="">(請先選擇縣市)</option>';
            townSelect.disabled = true;
            windSpeedDisplay.textContent = '---';
            if (selectedCounty) {
                const towns = windSpeedsData.filter(record => record.county === selectedCounty).map(record => record.town);
                townSelect.innerHTML = '<option value="">--- 請選擇 ---</option>';
                towns.forEach(town => {
                    const option = document.createElement('option');
                    option.value = town;
                    option.textContent = town;
                    townSelect.appendChild(option);
                });
                townSelect.disabled = false;
                if (towns.length === 1) {
                    townSelect.value = towns[0];
                    townSelect.dispatchEvent(new Event('change'));
                }
            }
        });
    }

    if (townSelect) {
        townSelect.addEventListener('change', () => {
            const selectedCounty = countySelect.value;
            const selectedTown = townSelect.value;
            if (selectedCounty && selectedTown) {
                const record = windSpeedsData.find(r => r.county === selectedCounty && r.town === selectedTown);
                windSpeedDisplay.textContent = record ? `${record.speed} m/s` : '---';
            } else {
                windSpeedDisplay.textContent = '---';
            }
        });
    }

    function toggleTopoDetailsVisibility(selectElement, detailsContainer) {
        if (!selectElement || !detailsContainer) return;
        detailsContainer.style.display = selectElement.value !== 'not_considered' ? 'flex' : 'none';
    }

    if (topoSelectX) topoSelectX.addEventListener('change', () => toggleTopoDetailsVisibility(topoSelectX, topoDetailsX));
    if (topoSelectY) topoSelectY.addEventListener('change', () => toggleTopoDetailsVisibility(topoSelectY, topoDetailsY));

    function setupModal(triggerId, modalId) {
        const modal = document.getElementById(modalId);
        const openLink = document.getElementById(triggerId);
        const closeButton = modal ? modal.querySelector('.close-button') : null;
        if (!modal || !openLink || !closeButton) return;
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

    setupModal('show-topo-modal-link', 'topo-modal');
    setupModal('show-height-modal-link', 'height-modal');
    setupModal('show-fn-modal-link', 'fn-modal');

    const allConditionalGroups = [
        eaveHeightGroup, ridgeHeightGroup, buildingHeightOptionsGroup, manualHeightInputGroup, ridgeDirectionGroup, hipRoofOptionsGroup,
        hipTopPlaneGroup, hipRidgeOptionsGroup, spanCountGroup, irregularSawtoothContainer, buildingDimsGroup, overhangOptionsGroup,
        archedRoofOptionsGroup, angleDisplayGroupSingle, angleDisplayGroupHip
    ];

    function updateGeometryInputs() {
        if (!roofShapeSelect) return;
        allConditionalGroups.forEach(group => {
            if (group) group.style.display = 'none';
        });
        if (sawtoothValidationError) sawtoothValidationError.style.display = 'none';
        const selectedShape = roofShapeSelect.value;
        if (eaveHeightGroup) eaveHeightGroup.style.display = 'flex';
        if (buildingDimsGroup) buildingDimsGroup.style.display = 'flex';
        if (selectedShape !== 'flat') {
            if (buildingHeightOptionsGroup) buildingHeightOptionsGroup.style.display = 'flex';
            updateBuildingHeightInputs();
            if (overhangOptionsGroup) overhangOptionsGroup.style.display = 'flex';
        }
        switch (selectedShape) {
            case 'gable':
            case 'shed':
                if (ridgeHeightGroup) ridgeHeightGroup.style.display = 'flex';
                if (ridgeDirectionGroup) ridgeDirectionGroup.style.display = 'flex';
                if (angleDisplayGroupSingle) angleDisplayGroupSingle.style.display = 'flex';
                if (ridgeHeightLabel) ridgeHeightLabel.textContent = '屋脊高 (m):';
                if (ridgeDirectionLabel) ridgeDirectionLabel.textContent = '屋脊方向:';
                break;
            case 'hip':
                if (ridgeHeightGroup) ridgeHeightGroup.style.display = 'flex';
                if (hipRoofOptionsGroup) hipRoofOptionsGroup.style.display = 'flex';
                if (angleDisplayGroupHip) angleDisplayGroupHip.style.display = 'flex';
                if (ridgeHeightLabel) ridgeHeightLabel.textContent = '屋脊高 (m):';
                if (ridgeDirectionGroup) ridgeDirectionGroup.style.display = 'none';
                updateHipRoofOptions();
                break;
            case 'arched':
                if (ridgeHeightGroup) ridgeHeightGroup.style.display = 'flex';
                if (ridgeDirectionGroup) ridgeDirectionGroup.style.display = 'flex';
                if (archedRoofOptionsGroup) archedRoofOptionsGroup.style.display = 'flex';
                if (angleDisplayGroupSingle) angleDisplayGroupSingle.style.display = 'flex';
                if (ridgeHeightLabel) ridgeHeightLabel.textContent = '拱頂高 (m):';
                if (ridgeDirectionLabel) ridgeDirectionLabel.textContent = '拱頂軸線方向:';
                break;
            case 'sawtooth_uniform':
                if (ridgeHeightGroup) ridgeHeightGroup.style.display = 'flex';
                if (spanCountGroup) spanCountGroup.style.display = 'flex';
                if (ridgeDirectionGroup) ridgeDirectionGroup.style.display = 'flex';
                if (angleDisplayGroupSingle) angleDisplayGroupSingle.style.display = 'flex';
                if (ridgeHeightLabel) ridgeHeightLabel.textContent = '屋脊高 (m):';
                if (ridgeDirectionLabel) ridgeDirectionLabel.textContent = '屋脊方向:';
                break;
            case 'sawtooth_irregular':
                if (spanCountGroup) spanCountGroup.style.display = 'flex';
                if (irregularSawtoothContainer) irregularSawtoothContainer.style.display = 'block';
                if (ridgeDirectionGroup) ridgeDirectionGroup.style.display = 'flex';
                if (ridgeDirectionLabel) ridgeDirectionLabel.textContent = '屋脊方向:';
                generateSawtoothTable();
                break;
        }
        calculateAndDisplayAngles();
        updateBuildingSchematicImage();
    }

    function updateBuildingHeightInputs() {
        if (!manualHeightInputGroup) return;
        manualHeightInputGroup.style.display = (document.querySelector('input[name="building_height_mode"]:checked').value === 'manual') ? 'flex' : 'none';
    }

    function updateHipRoofOptions() {
        if (!hipRoofOptionsGroup || !hipTopPlaneGroup || !ridgeDirectionGroup) return;
        const selectedHipType = document.querySelector('input[name="hip_top_type"]:checked').value;
        if (selectedHipType === 'plane') {
            hipTopPlaneGroup.style.display = 'flex';
            ridgeDirectionGroup.style.display = 'none';
        } else {
            hipTopPlaneGroup.style.display = 'none';
            hipRidgeOptionsGroup.style.display = 'flex';
            if (ridgeDirectionLabel) {
                ridgeDirectionLabel.textContent = '屋脊方向:';
            }
        }
    }

    function generateSawtoothTable() {
        if (!spanCountInput || !irregularSawtoothContainer) return;
        const count = parseInt(spanCountInput.value) || 0;
        const existingHeights = Array.from(document.querySelectorAll('.sawtooth-ridge-height')).map(input => input.value);
        const existingWidths = Array.from(document.querySelectorAll('.sawtooth-span-width')).map(input => input.value);
        irregularSawtoothContainer.innerHTML = '';
        if (count > 0) {
            let tableHTML = '<table class="sawtooth-table"><thead><tr><th>跨</th><th>屋脊高 (m)</th><th>跨距 (m)</th></tr></thead><tbody>';
            for (let i = 1; i <= count; i++) {
                const height = existingHeights[i - 1] || '12';
                const width = existingWidths[i - 1] || '10';
                tableHTML += `<tr><td>#${i}</td><td><input type="number" class="sawtooth-ridge-height" value="${height}"></td><td><input type="number" class="sawtooth-span-width" value="${width}"></td></tr>`;
            }
            tableHTML += '</tbody></table>';
            irregularSawtoothContainer.innerHTML = tableHTML;
            document.querySelectorAll('.sawtooth-span-width, .sawtooth-ridge-height').forEach(input => {
                input.addEventListener('input', () => {
                    validateSawtoothSpans();
                    calculateAndDisplayAngles();
                });
            });
            validateSawtoothSpans();
        }
    }

    function validateSawtoothSpans() {
        if (!roofShapeSelect || !sawtoothValidationError || !buildingDimXInput || !buildingDimYInput) return;
        if (roofShapeSelect.value !== 'sawtooth_irregular') {
            sawtoothValidationError.style.display = 'none';
            return;
        }
        const ridgeDirectionRadio = document.querySelector('input[name="ridge_direction"]:checked');
        if (!ridgeDirectionRadio) return;
        const ridgeDirection = ridgeDirectionRadio.value;
        const targetDimensionInput = (ridgeDirection === 'X') ? buildingDimYInput : buildingDimXInput;
        const targetDimension = parseFloat(targetDimensionInput.value);
        let currentSum = 0;
        document.querySelectorAll('.sawtooth-span-width').forEach(input => {
            currentSum += parseFloat(input.value) || 0;
        });
        if (isNaN(targetDimension)) {
            sawtoothValidationError.style.display = 'none';
            return;
        }
        if (Math.abs(currentSum - targetDimension) > 0.001 && currentSum > 0) {
            sawtoothValidationError.textContent = `錯誤：各跨距總和 (${currentSum.toFixed(2)} m) 不等於垂直屋脊方向的建築尺寸 (${targetDimension.toFixed(2)} m)。`;
            sawtoothValidationError.style.display = 'block';
        } else {
            sawtoothValidationError.style.display = 'none';
        }
    }

    function updateFnInputs() {
        if (!manualFnInputGroup) return;
        manualFnInputGroup.style.display = (document.querySelector('input[name="fn_mode"]:checked').value === 'manual') ? 'flex' : 'none';
    }

    function checkLowRiseEligibility() {
        if (!lowRiseEligibilityNotice) return false;
        const roofShape = roofShapeSelect.value;
        const eaveHeight = parseFloat(document.getElementById('eave-height-input').value) || 0;
        const ridgeHeight = parseFloat(document.getElementById('ridge-height-input').value) || eaveHeight;
        const dimX = parseFloat(buildingDimXInput.value) || 0;
        const dimY = parseFloat(buildingDimYInput.value) || 0;
        let h = eaveHeight;
        if (roofShape !== 'flat' && ridgeHeight > eaveHeight) {
            const base_width = (document.querySelector('input[name="ridge_direction"]:checked')?.value === 'X') ? dimY : dimX;
            const delta_h = ridgeHeight - eaveHeight;
            let theta = 0;
            if (base_width > 0 && delta_h > 0) {
                theta = Math.atan(delta_h / (base_width / 2)) * (180 / Math.PI);
            }
            if (theta >= 10) {
                h = (eaveHeight + ridgeHeight) / 2;
            }
        }
        const conditions = {
            isLowEnough: h <= 18,
            isRigid: (h / Math.sqrt(dimX * dimY) < 3) && (dimX > 0 && dimY > 0),
            isProportional: (dimX / dimY >= 0.2 && dimX / dimY <= 5) && (dimY / dimX >= 0.2 && dimY / dimX <= 5),
            isSymmetric: ['flat', 'gable', 'hip'].includes(roofShape)
        };
        const allMet = Object.values(conditions).every(Boolean);
        if (allMet) {
            lowRiseEligibilityNotice.textContent = '✓ 您的建築符合低矮建築條件，可選用簡化法。';
            lowRiseEligibilityNotice.className = 'eligibility-notice eligible';
            lowRiseRadios.forEach(radio => radio.disabled = false);
        } else {
            lowRiseEligibilityNotice.textContent = '✗ 您的建築不符合低矮建築條件，必須使用通用法。';
            lowRiseEligibilityNotice.className = 'eligibility-notice not-eligible';
            document.querySelector('input[name="calculation_method"][value="general"]').checked = true;
            lowRiseRadios.forEach(radio => radio.disabled = true);
        }
        return allMet;
    }

    function updateGableDetailOptions() {
        const selectedShape = roofShapeSelect.value;
        const isGableApplicable = ['gable', 'shed', 'sawtooth_uniform', 'sawtooth_irregular', 'arched'].includes(selectedShape);
        gableDetailRadios.forEach(radio => {
            if (selectedShape === 'hip' || selectedShape === 'flat' || !isGableApplicable) {
                radio.disabled = true;
                document.querySelector('input[name="simplify_gable"][value="false"]').checked = true;
            } else {
                radio.disabled = false;
            }
        });
    }

    // ** 核心修改: 重構 updateAsce7Options 函式 **
    function updateAsce7Options() {
        if (!roofShapeSelect) return;
        const asce7RadioGroup = document.getElementById('asce7-radio-group');
        if (!asce7RadioGroup) return;

        const geometryWarningEl = document.getElementById('geometry-angle-warning');
        const asce7CommentEl = asce7RadioGroup.parentElement.nextElementSibling;

        if (geometryWarningEl) {
            geometryWarningEl.textContent = '';
            geometryWarningEl.style.display = 'none';
        }
        if (asce7CommentEl && asce7CommentEl.querySelector('.angle-warning-text')) {
            asce7CommentEl.querySelector('.angle-warning-text').remove();
        }

        const selectedShape = roofShapeSelect.value;
        const {theta, theta_x, theta_y} = calculateAndDisplayAngles();

        let isRoofTypeSupported = !['sawtooth_irregular'].includes(selectedShape);
        let roofMessage = '';
        let angleExceeded = false;
        let warningMessage = '';

        if (isRoofTypeSupported) {
            switch (selectedShape) {
                case 'gable':
                case 'sawtooth_uniform':
                case 'hip':
                    const max_theta = (selectedShape === 'hip') ? Math.max(theta_x || 0, theta_y || 0) : theta;
                    if (max_theta > 45) {
                        angleExceeded = true;
                        warningMessage = `警告：屋頂角度 (${max_theta.toFixed(1)}°) > 45°，C&C計算將採用牆面風壓係數。`;
                    }
                    break;
                case 'shed':
                    if (theta > 30) {
                        angleExceeded = true;
                        warningMessage = `警告：單斜屋頂角度 (${theta.toFixed(1)}°) > 30°，將採用牆面風壓係數計算。`;
                    }
                    break;
            }
        } else {
            roofMessage = '該屋頂類型暫不支援 ASCE 7-16 C&C 計算。';
        }

        // 控制選項是否可用
        asce7CandCRadios.forEach(radio => radio.disabled = !isRoofTypeSupported);

        if (!isRoofTypeSupported) {
            if (asce7CommentEl.querySelector('.angle-warning-text')) {
                asce7CommentEl.querySelector('.angle-warning-text').remove();
            }
            document.querySelector('input[name="use_asce7_c_and_c"][value="false"]').checked = true;
        }

        if (angleExceeded) {
            if (geometryWarningEl) {
                geometryWarningEl.textContent = warningMessage;
                geometryWarningEl.style.display = 'block';
                geometryWarningEl.style.color = '#e63946';
            }
        }
    }

    if (roofShapeSelect) roofShapeSelect.addEventListener('change', updateGeometryInputs);
    if (buildingHeightModeRadios) buildingHeightModeRadios.forEach(radio => radio.addEventListener('change', updateBuildingHeightInputs));
    if (hipTopTypeRadios) hipTopTypeRadios.forEach(radio => radio.addEventListener('change', updateHipRoofOptions));
    if (spanCountInput) {
        spanCountInput.addEventListener('input', () => {
            if (roofShapeSelect && roofShapeSelect.value === 'sawtooth_irregular') generateSawtoothTable();
            calculateAndDisplayAngles();
        });
    }
    if (ridgeDirectionRadios) ridgeDirectionRadios.forEach(radio => radio.addEventListener('input', validateSawtoothSpans));
    if (buildingDimXInput) buildingDimXInput.addEventListener('input', validateSawtoothSpans);
    if (buildingDimYInput) buildingDimYInput.addEventListener('input', validateSawtoothSpans);
    if (fnModeRadios) fnModeRadios.forEach(radio => radio.addEventListener('change', updateFnInputs));

    const angleCalculationTriggers = [
        roofShapeSelect, document.getElementById('eave-height-input'),
        document.getElementById('ridge-height-input'), buildingDimXInput, buildingDimYInput,
        ...document.querySelectorAll('input[name="ridge_direction"]'),
        ...document.querySelectorAll('input[name="hip_top_type"]'),
        document.getElementById('hip-plane-x-input'), document.getElementById('hip-plane-y-input'),
        ...document.querySelectorAll('input[name="ridge_direction_hip"]'),
        document.getElementById('hip-ridge-length-input'), spanCountInput
    ];

    const schematicUpdateTriggers = [
        roofShapeSelect, ...document.querySelectorAll('input[name="has_overhang"]'),
        ...document.querySelectorAll('input[name="ridge_direction"]'), ...document.querySelectorAll('input[name="ridge_direction_hip"]')
    ];

    schematicUpdateTriggers.forEach(element => {
        if (element) element.addEventListener('input', updateBuildingSchematicImage);
    });

    const eligibilityCheckTriggers = [...angleCalculationTriggers];

    angleCalculationTriggers.forEach(element => {
        if (element) {
            element.addEventListener('input', () => {
                calculateAndDisplayAngles();
                updateAsce7Options();
            });
        }
    });

    eligibilityCheckTriggers.forEach(element => {
        if (element) element.addEventListener('input', checkLowRiseEligibility);
    });

    if (roofShapeSelect) roofShapeSelect.addEventListener('input', updateGableDetailOptions);

    updateGeometryInputs();
    toggleTopoDetailsVisibility(topoSelectX, topoDetailsX);
    toggleTopoDetailsVisibility(topoSelectY, topoDetailsY);
    updateFnInputs();
    checkLowRiseEligibility();
    updateAsce7Options();
    calculateAndDisplayAngles();
    updateBuildingSchematicImage();

    // ======================================================
    // 區域 3: API 呼叫與結果處理 (無變更)
    // ======================================================
    if (calculateButton) {
        calculateButton.addEventListener('click', () => {
            const windSpeedValue = windSpeedDisplay ? windSpeedDisplay.textContent : '---';
            if (!windSpeedValue || windSpeedValue.trim() === '---') {
                alert("錯誤：未選擇工址地點或未取得基本設計風速。");
                return;
            }
            if (resultsModalBody) resultsModalBody.innerHTML = '<p class="placeholder-text">計算中，請稍候...</p>';
            lastSuccessfulData = null;
            let sawtoothDetails = [];
            if (roofShapeSelect.value === 'sawtooth_irregular') {
                const heightInputs = document.querySelectorAll('.sawtooth-ridge-height');
                const widthInputs = document.querySelectorAll('.sawtooth-span-width');
                for (let i = 0; i < heightInputs.length; i++) {
                    sawtoothDetails.push({ridge_height: heightInputs[i].value, span_width: widthInputs[i].value});
                }
            }
            const useAsce7RoofInput = document.querySelector('input[name="use_asce7_16_roof"]');

            const formData = {
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
                roofShape: roofShapeSelect.value,
                eaveHeight: document.getElementById('eave-height-input').value,
                ridgeHeight: document.getElementById('ridge-height-input').value,
                has_overhang: document.querySelector('input[name="has_overhang"]:checked') ? document.querySelector('input[name="has_overhang"]:checked').value === 'true' : false,
                buildingHeightMode: document.querySelector('input[name="building_height_mode"]:checked').value,
                manualHeight: document.getElementById('manual-height-input').value,
                ridgeDirection: document.querySelector('input[name="ridge_direction"]:checked') ? document.querySelector('input[name="ridge_direction"]:checked').value : null,
                buildingDimX: document.getElementById('building-dim-x-input').value,
                buildingDimY: document.getElementById('building-dim-y-input').value,
                sawtoothDetails: sawtoothDetails,
                hipRoofOptions: {
                    topType: document.querySelector('input[name="hip_top_type"]:checked') ? document.querySelector('input[name="hip_top_type"]:checked').value : 'ridge',
                    ridgeDirection: document.querySelector('input[name="ridge_direction_hip"]:checked') ? document.querySelector('input[name="ridge_direction_hip"]:checked').value : 'X',
                    ridgeLength: document.getElementById('hip-ridge-length-input').value,
                    planeDimX: document.getElementById('hip-plane-x-input').value,
                    planeDimY: document.getElementById('hip-plane-y-input').value
                },
                sawtooth_uniform_span_count: document.getElementById('span-count-input').value,
                sawtooth_irregular_details: sawtoothDetails,
                enclosureStatus: document.getElementById('enclosure-status-select').value,
                importanceFactor: document.getElementById('importance-factor-select').value.split('_')[0],
                dampingRatio: document.getElementById('damping-ratio-select').value.split('_')[0],
                fnMode: document.querySelector('input[name="fn_mode"]:checked').value,
                fnX: document.getElementById('fn-x-input').value,
                fnY: document.getElementById('fn-y-input').value,
                ft: document.getElementById('fn-t-input').value,
                segmentHeight: document.getElementById('segment-height-input').value,
                simplifyGable: document.querySelector('input[name="simplify_gable"]:checked').value === 'true',
                calculationMethod: document.querySelector('input[name="calculation_method"]:checked').value,
                use_asce7_c_and_c: document.querySelector('input[name="use_asce7_c_and_c"]:checked') ? document.querySelector('input[name="use_asce7_c_and_c"]:checked').value === 'true' : false,
                is_at_ground_level: document.querySelector('input[name="is_at_ground_level"]:checked') ? document.querySelector('input[name="is_at_ground_level"]:checked').value === 'true' : false,
            };

            fetch('/windTW/calculate/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrftoken},
                body: JSON.stringify(formData)
            })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(errData => {
                            throw new Error(errData.message || `伺服器錯誤: ${response.status}`);
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.status === 'success') {
                        lastSuccessfulData = {inputs: formData, results: data};
                        displayGeneralResults(data);
                    } else {
                        if (resultsModalBody) resultsModalBody.innerHTML = `<p class="result-message error">計算失敗: ${data.message}</p>`;
                    }
                    showResultsModal();
                })
                .catch(error => {
                    console.error('Fetch Error:', error);
                    const errorMessage = (error instanceof Error) ? error.message : String(error);
                    if (resultsModalBody) resultsModalBody.innerHTML = `<p class="result-message error">請求錯誤: ${errorMessage}</p>`;
                    showResultsModal();
                });
        });
    }

    // ======================================================
    // 區域 4: 結果顯示與報告書邏輯 (無變更)
    // ======================================================
    if (reportButtonModal) {
        reportButtonModal.addEventListener('click', () => {
            if (!lastSuccessfulData) {
                alert("沒有可用的計算結果可生成報告。");
                return;
            }
            const currentCounty = document.getElementById('county-select').value;
            const currentTown = document.getElementById('town-select').value;
            const inputs = lastSuccessfulData.inputs;
            const results = lastSuccessfulData.results;
            const firstCaseKey = Object.keys(results.general_data_cases)[0];
            const summaryData = results.general_data_cases[firstCaseKey]?.summary || {};
            const params = new URLSearchParams({
                county: currentCounty, town: currentTown, v10c: inputs.v10c || 0,
                terrain: inputs.terrain || 'C', topo_x_type: inputs.topoX.type,
                topo_x_h: inputs.topoX.H, topo_x_lh: inputs.topoX.Lh, topo_x_x: inputs.topoX.x,
                topo_y_type: inputs.topoY.type, topo_y_h: inputs.topoY.H, topo_y_lh: inputs.topoY.Lh,
                topo_y_x: inputs.topoY.x, dim_x: inputs.buildingDimX || 0,
                dim_y: inputs.buildingDimY || 0, roof_shape: inputs.roofShape || 'flat',
                eave_height: inputs.eaveHeight || 0, ridge_height: inputs.ridgeHeight || 0,
                calculated_h: results.calculated_h || inputs.eaveHeight,
                theta: summaryData.theta !== undefined ? summaryData.theta : '0',
                theta_x: summaryData.theta_X !== undefined ? summaryData.theta_X : '0',
                theta_y: summaryData.theta_Y !== undefined ? summaryData.theta_Y : '0',
                ridge_direction: inputs.roofShape === 'hip' ? inputs.hipRoofOptions.ridgeDirection : inputs.ridgeDirection,
                ridge_length: inputs.roofShape === 'hip' ? inputs.hipRoofOptions.ridgeLength : 'N/A',
                has_overhang: inputs.has_overhang, num_spans: inputs.sawtooth_uniform_span_count || 1,
                enclosure_status: inputs.enclosureStatus, importance_factor: inputs.importanceFactor,
                damping_ratio: inputs.dampingRatio, fn_x: inputs.fnX, fn_y: inputs.fnY, ft: inputs.ft,
                use_asce7_c_and_c: inputs.use_asce7_c_and_c,
            });
            const reportUrl = `/windTW/report/?${params.toString()}`;
            window.open(reportUrl, '_blank', 'width=900,height=800,scrollbars=yes,resizable=yes');
        });
    }

    function displayGeneralResults(data) {
        if (!resultsModalBody) return;
        const generalDataCases = data.general_data_cases;
        if (!generalDataCases || Object.keys(generalDataCases).length === 0) {
            resultsModalBody.innerHTML = '<p class="result-message error">收到的通用法結果數據格式不正確。</p>';
            return;
        }
        const calculatedH = data.calculated_h;
        const allCaseIds = Object.keys(generalDataCases);
        const hasTopoX = allCaseIds.filter(id => id.startsWith('X_')).length > 1;
        const hasTopoY = allCaseIds.filter(id => id.startsWith('Y_')).length > 1;
        let html = `
            <style>
                .results-table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }
                .results-table th, .results-table td { padding: 8px 12px; border: 1px solid #ddd; text-align: left; }
                .results-table th { background-color: #f2f8fa; font-weight: bold; width: 35%; }
                .results-table td { background-color: #ffffff; }
                .results-table .header-row { background-color: #457b9d; color: white; font-size: 16px; text-align: center; }
                .case-title { font-size: 18px; color: #1d3557; margin-top: 25px; margin-bottom: 10px; padding-bottom: 5px; border-bottom: 2px solid #a8dadc; }
            </style>
            <h4>通用參數</h4>
            <table class="results-table">
                <tr><th>建築物高度 h (m)</th><td>${calculatedH ? calculatedH.toFixed(2) : 'N/A'}</td></tr>
            </table>`;
        const buildCaseTable = (caseId, windwardKey, sidewindKey) => {
            const caseData = generalDataCases[caseId];
            if (!caseData || Object.keys(caseData).length === 0) return '';
            const summary = caseData.summary || {};
            const windwardData = caseData[windwardKey] || {};
            const sidewindData = caseData[sidewindKey] || {};
            const formatRoofCp = (roofCp) => {
                if (!roofCp || Object.keys(roofCp).length === 0) return 'N/A';
                return Object.entries(roofCp).map(([key, value]) => `${key}: ${value.toFixed(2)}`).join('<br>');
            };
            return `
                <table class="results-table">
                    <tr><th>內風壓係數 GCpi</th><td colspan="2">${summary.gcpi ? summary.gcpi.join(', ') : 'N/A'}</td></tr>
                </table>
                <table class="results-table">
                    <thead>
                        <tr><th class="header-row" colspan="3">主軸向分析結果</th></tr>
                        <tr>
                            <th>參數項目</th>
                            <th>順風向</th>
                            <th>橫風向</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><th>地形係數 Kzt</th><td>${windwardData.kzt !== undefined ? windwardData.kzt.toFixed(3) : 'N/A'}</td><td>${sidewindData.kzt !== undefined ? sidewindData.kzt.toFixed(3) : 'N/A'}</td></tr>
                        <tr><th>建築物類型</th><td>${windwardData.rigidity || 'N/A'}</td><td>${sidewindData.rigidity || 'N/A'}</td></tr>
                        <tr><th>陣風反應因子 G/Gf</th><td>${windwardData.G_factor !== undefined ? windwardData.G_factor.toFixed(3) : 'N/A'}</td><td>${sidewindData.G_factor !== undefined ? sidewindData.G_factor.toFixed(3) : 'N/A'}</td></tr>
                        <tr><th>L / B</th><td>${windwardData.L_over_B !== undefined ? windwardData.L_over_B.toFixed(3) : 'N/A'}</td><td>${sidewindData.L_over_B !== undefined ? sidewindData.L_over_B.toFixed(3) : 'N/A'}</td></tr>
                        <tr><th>h / L</th><td>${windwardData.h_over_L !== undefined ? windwardData.h_over_L.toFixed(3) : 'N/A'}</td><td>${sidewindData.h_over_L !== undefined ? sidewindData.h_over_L.toFixed(3) : 'N/A'}</td></tr>
                        <tr><th>h / B</th><td>${windwardData.h_over_B !== undefined ? windwardData.h_over_B.toFixed(3) : 'N/A'}</td><td>${sidewindData.h_over_B !== undefined ? sidewindData.h_over_B.toFixed(3) : 'N/A'}</td></tr>
                        <tr><th>牆面迎風面 Cp</th><td>${windwardData.wall_cp_windward !== undefined ? windwardData.wall_cp_windward.toFixed(2) : 'N/A'}</td><td>${sidewindData.wall_cp_windward !== undefined ? sidewindData.wall_cp_windward.toFixed(2) : 'N/A'}</td></tr>
                        <tr><th>牆面背風面 Cp</th><td>${windwardData.wall_cp_leeward !== undefined ? windwardData.wall_cp_leeward.toFixed(2) : 'N/A'}</td><td>${sidewindData.wall_cp_leeward !== undefined ? sidewindData.wall_cp_leeward.toFixed(2) : 'N/A'}</td></tr>
                        <tr><th>牆面側風面 Cp</th><td>${windwardData.wall_cp_side !== undefined ? windwardData.wall_cp_side.toFixed(2) : 'N/A'}</td><td>${sidewindData.wall_cp_side !== undefined ? sidewindData.wall_cp_side.toFixed(2) : 'N/A'}</td></tr>
                        <tr><th>屋頂 Cp</th><td>${formatRoofCp(windwardData.roof_cp)}</td><td>${formatRoofCp(sidewindData.roof_cp)}</td></tr>
                    </tbody>
                </table>
            `;
        };
        if (hasTopoX) {
            if (generalDataCases['X_positive']) {
                html += `<h3 class="case-title">風向：+X向風</h3>`;
                html += buildCaseTable('X_positive', 'X_dir', 'Y_dir');
            }
            if (generalDataCases['X_negative']) {
                html += `<h3 class="case-title">風向：-X向風</h3>`;
                html += buildCaseTable('X_negative', 'X_dir', 'Y_dir');
            }
        } else {
            if (generalDataCases['X_positive']) {
                html += `<h3 class="case-title">風向：±X向風</h3>`;
                html += buildCaseTable('X_positive', 'X_dir', 'Y_dir');
            }
        }
        if (hasTopoY) {
            if (generalDataCases['Y_positive']) {
                html += `<h3 class="case-title">風向：+Y向風</h3>`;
                html += buildCaseTable('Y_positive', 'Y_dir', 'X_dir');
            }
            if (generalDataCases['Y_negative']) {
                html += `<h3 class="case-title">風向：-Y向風</h3>`;
                html += buildCaseTable('Y_negative', 'Y_dir', 'X_dir');
            }
        } else {
            if (generalDataCases['Y_positive']) {
                html += `<h3 class="case-title">風向：±Y向風</h3>`;
                html += buildCaseTable('Y_positive', 'Y_dir', 'X_dir');
            }
        }
        resultsModalBody.innerHTML = html;
    }

    // ======================================================
    // 區域 5: 結果 Modal 的關閉邏輯 (無變更)
    // ======================================================
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
});