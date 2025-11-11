/**

 * 鋼結構設計系統 - 設計系統專用JavaScript (非模組化版本)

 * 最後更新: 2023/08/15

 */


// 確保全局對象存在

window.DesignSystem = window.DesignSystem || {

    showNotification: function (msg, type) {

        console.log(`[${type}] ${msg}`);

    }

};


// DOM載入後初始化

document.addEventListener('DOMContentLoaded', function () {

// 柱形狀變更

    const columnShape = document.getElementById('column_shape');

    if (columnShape) {

        columnShape.addEventListener('change', handleColumnShapeChange);

        handleColumnShapeChange.call(columnShape);

    }


// 自定義輸入切換

    document.getElementById('custom_input')?.addEventListener('change', handleCustomInputToggle);


// 銲接部位選項

    if (columnShape) {

        columnShape.addEventListener('change', updateWeldLocationOptions);

        updateWeldLocationOptions.call(columnShape);

    }


// 止滑榫

    document.getElementById('anti_slip')?.addEventListener('change', handleAntiSlipToggle);


// 無限大平面

    const infinitePlane = document.getElementById('infinite_plane');

    if (infinitePlane) {

        infinitePlane.addEventListener('change', handleInfinitePlaneToggle);

        handleInfinitePlaneToggle.call(infinitePlane);

    }


// 鋼筋選項

    document.getElementById('tension_rebar')?.addEventListener('change', handleTensionRebarToggle);

    document.getElementById('shear_rebar')?.addEventListener('change', handleShearRebarToggle);


// 執行按鈕

    document.getElementById('execute-btn')?.addEventListener('click', function () {

        const missingFields = validateForm();

        const messageDiv = document.getElementById('validation-message');


        if (missingFields.length > 0) {

            messageDiv.innerHTML = `

<div class="alert alert-error">

<strong>以下必填欄位未完成：</strong>

<ul>${missingFields.map(f => `<li>${f}</li>`).join('')}</ul>

</div>

`;

            messageDiv.style.display = 'block';

            return;

        }


        if (typeof window.performCalculation === 'function') {

            window.performCalculation();

        } else {

            console.error('performCalculation 未定義');

            DesignSystem.showNotification('系統錯誤: 計算功能不可用', 'error');

        }

    });

});


// 柱形狀變更處理

function handleColumnShapeChange() {

    const hBeamSection = document.getElementById('h-beam-inputs');

    if (hBeamSection) {

        hBeamSection.style.display = this.value === 'H-beam' ? 'block' : 'none';

    }


    if (this.value !== 'H-beam') {

        document.getElementById('custom_input').checked = false;

        document.getElementById('h-beam-custom').style.display = 'none';

        document.getElementById('h_beam_spec').value = '';


        document.querySelectorAll('#h-beam-custom input').forEach(input => {

            input.value = '';

        });

    }

}


// 自定義輸入切換

function handleCustomInputToggle() {

    const customDiv = document.getElementById('h-beam-custom');

    const specSelect = document.getElementById('h_beam_spec');


    if (customDiv && specSelect) {

        customDiv.style.display = this.checked ? 'flex' : 'none';

        specSelect.disabled = this.checked;


        if (!this.checked) {

            document.querySelectorAll('#h-beam-custom input').forEach(input => {

                input.value = '';

            });

        } else {

            specSelect.value = '';

        }

    }

}


// 更新銲接部位選項

function updateWeldLocationOptions() {

    const isHBeam = this.value === 'H-beam';

    document.getElementById('weld-outer-option').style.display = isHBeam ? 'block' : 'none';

    document.getElementById('weld-both-option').style.display = isHBeam ? 'block' : 'none';


    if (!isHBeam) {

        document.getElementById('weld_all').checked = true;

    }

}


// 止滑榫切換

function handleAntiSlipToggle() {

    document.getElementById('anti_slip_message').style.display =

        this.checked ? 'block' : 'none';

}


// 無限大平面切換

function handleInfinitePlaneToggle() {

    const isChecked = this.checked;


    document.querySelectorAll('.concrete-input').forEach(input => {

        if (input.id !== 'concrete_fc') {

            input.disabled = isChecked;

            input.classList.toggle('bg-light', isChecked);

        }

    });


    document.querySelectorAll('.concrete-label').forEach(label => {

        if (label.htmlFor !== 'concrete_fc') {

            label.classList.toggle('disabled-label', isChecked);

        }

    });


    if (isChecked) {

        ['concrete_x', 'concrete_y', 'concrete_thickness', 'grout_thickness'].forEach(id => {

            document.getElementById(id).value = '';

        });

    }

}


// 鋼筋切換處理

function handleTensionRebarToggle() {

    toggleRebarSection('tension_rebar_details', 'tension_rebar_size', 'tension_rebar_qty', this.checked);

}


function handleShearRebarToggle() {

    toggleRebarSection('shear_rebar_details', 'shear_rebar_size', 'shear_rebar_qty', this.checked);

}


function toggleRebarSection(detailsId, sizeId, qtyId, isChecked) {

    const detailDiv = document.getElementById(detailsId);

    if (detailDiv) {

        detailDiv.style.display = isChecked ? 'flex' : 'none';

        if (!isChecked) {

            document.getElementById(sizeId).value = sizeId.includes('tension') ? '#4' : '#3';

            document.getElementById(qtyId).value = sizeId.includes('tension') ? '4' : '2';

        }

    }

}


// 表單驗證

function validateForm() {

    const validationRules = [

        {id: 'axial_force', name: '軸力 Pu'},

        {id: 'moment_xx', name: 'X向彎矩 MuXX'},

        {id: 'moment_yy', name: 'Y向彎矩 MuYY'},

        {id: 'shear_x', name: 'X向剪力 VuX'},

        {id: 'shear_y', name: 'Y向剪力 VuY'},

        {id: 'yield_strength', name: '降伏強度 Fy'},

        {id: 'elastic_modulus', name: '彈性模數 Es'},

        {id: 'eccentricity_x', name: 'X方向偏心距離 ex'},

        {id: 'eccentricity_y', name: 'Y方向偏心距離 ey'},

        {

            id: 'baseplate_x',

            name: '基板X方向尺寸',

            condition: () => !document.getElementById('infinite_plane').checked

        }

    ];


    const missingFields = validationRules

        .filter(rule => {

            const element = document.getElementById(rule.id);

            const shouldValidate = !rule.condition || rule.condition();

            return shouldValidate && element && element.required && !element.value.trim();

        })

        .map(rule => rule.name);


// 標記無效欄位

    validationRules.forEach(rule => {

        const element = document.getElementById(rule.id);

        if (element) {

            element.classList.toggle(
                'is-invalid',

                missingFields.includes(rule.name)
            );

        }

    });


    return missingFields;

}