/**
 * section_properties/static/section_properties/js/main.js
 */

document.addEventListener('DOMContentLoaded', function () {
    bindEvents();
    toggleInputFields();
});

let cachedData = null;

function bindEvents() {
    const typeSelect = document.getElementById('sectionTypeSelect');
    if (typeSelect) {
        typeSelect.addEventListener('change', toggleInputFields);
    }

    const inputs = document.querySelectorAll('.section-input');
    inputs.forEach(input => {
        input.addEventListener('input', () => {
            calculateAndDraw(true);
        });
    });

    const unitRadios = document.querySelectorAll('input[name="resultUnit"]');
    unitRadios.forEach(radio => {
        radio.addEventListener('change', renderResults);
    });

    const calcBtn = document.getElementById('calculate-button');
    if (calcBtn) {
        calcBtn.addEventListener('click', () => calculateAndDraw(false));
    }
}

function toggleInputFields() {
    const typeSelect = document.getElementById('sectionTypeSelect');
    if (!typeSelect) return;
    const type = typeSelect.value;

    document.querySelectorAll('.shape-group').forEach(el => el.style.display = 'none');
    const activeGroup = document.getElementById(`inputs-${type}`);
    if (activeGroup) {
        activeGroup.style.display = 'block';
    }
    calculateAndDraw(true);
}

function getSectionData() {
    const type = document.getElementById('sectionTypeSelect').value;
    let data = {type: type};
    let isValid = true;

    const getValue = (suffix) => {
        const el = document.getElementById(`inp_${type}_${suffix}`);
        if (!el) return 0;
        const val = parseFloat(el.value);
        if (isNaN(val) || val <= 0) isValid = false;
        return val;
    };

    if (type === 'H') {
        data.h = getValue('h');
        data.tw = getValue('tw');

        // 新增的非對稱參數
        data.bft = getValue('bft');
        data.tft = getValue('tft');
        data.bfb = getValue('bfb');
        data.tfb = getValue('tfb');

        const rEl = document.getElementById('inp_H_r');
        const rVal = parseFloat(rEl ? rEl.value : 0);
        data.r = (isNaN(rVal) || rVal < 0) ? 0 : rVal;
    } else if (type === 'Channel') {
        data.h = getValue('h');
        data.tw = getValue('tw');

        // 兼容舊版 bf (若 HTML 尚未更新 dom ID)
        const oldBf = document.getElementById('inp_Channel_bf') ? parseFloat(document.getElementById('inp_Channel_bf').value) : 0;
        const bftEl = document.getElementById('inp_Channel_bft');
        const bfbEl = document.getElementById('inp_Channel_bfb');
        data.bft = bftEl ? parseFloat(bftEl.value) : oldBf;
        data.bfb = bfbEl ? parseFloat(bfbEl.value) : oldBf;

        // 兼容舊版 tf
        const oldTf = document.getElementById('inp_Channel_tf') ? parseFloat(document.getElementById('inp_Channel_tf').value) : 0;
        const tftEl = document.getElementById('inp_Channel_tft');
        const tfbEl = document.getElementById('inp_Channel_tfb');
        data.tft = tftEl ? parseFloat(tftEl.value) : oldTf;
        data.tfb = tfbEl ? parseFloat(tfbEl.value) : oldTf;

        // r
        const rEl = document.getElementById('inp_Channel_r');
        const rVal = parseFloat(rEl ? rEl.value : 0);
        data.r = (isNaN(rVal) || rVal < 0) ? 0 : rVal;
    } else if (type === 'T') {
        data.h = getValue('h');
        data.bf = getValue('bf');
        data.tw = getValue('tw');
        data.tf = getValue('tf');

        // 讀取圓角 r
        const rEl = document.getElementById('inp_T_r');
        const rVal = parseFloat(rEl ? rEl.value : 0);
        data.r = (isNaN(rVal) || rVal < 0) ? 0 : rVal;
    } else if (type === 'C') {
        data.h = getValue('h');
        data.t = getValue('t');

        // 讀取上下翼板 (bt, bb)
        // 嘗試讀取新 ID，若無則讀舊 ID (b)，再無則為 0
        const oldB = document.getElementById('inp_C_b') ? parseFloat(document.getElementById('inp_C_b').value) : 0;
        const btEl = document.getElementById('inp_C_bt');
        const bbEl = document.getElementById('inp_C_bb');

        data.bt = (btEl && !isNaN(parseFloat(btEl.value))) ? parseFloat(btEl.value) : oldB;
        data.bb = (bbEl && !isNaN(parseFloat(bbEl.value))) ? parseFloat(bbEl.value) : oldB;

        // 讀取上下唇 (ct, cb)
        const oldC = document.getElementById('inp_C_c') ? parseFloat(document.getElementById('inp_C_c').value) : 0;
        const ctEl = document.getElementById('inp_C_ct');
        const cbEl = document.getElementById('inp_C_cb');

        data.ct = (ctEl && !isNaN(parseFloat(ctEl.value))) ? parseFloat(ctEl.value) : oldC;
        data.cb = (cbEl && !isNaN(parseFloat(cbEl.value))) ? parseFloat(cbEl.value) : oldC;

        const rEl = document.getElementById('inp_C_r');
        const rVal = parseFloat(rEl ? rEl.value : 0);
        data.r = (isNaN(rVal) || rVal < 0) ? 0 : rVal;

        // 簡單驗證
        if (data.h <= 0 || data.t <= 0) isValid = false;
    } else if (type === 'Z') {
        data.h = getValue('h');
        data.t = getValue('t');

        // 兼容舊版 b
        const oldB = document.getElementById('inp_Z_b') ? parseFloat(document.getElementById('inp_Z_b').value) : 0;
        const btEl = document.getElementById('inp_Z_bt');
        const bbEl = document.getElementById('inp_Z_bb');
        data.bt = (btEl && !isNaN(parseFloat(btEl.value))) ? parseFloat(btEl.value) : oldB;
        data.bb = (bbEl && !isNaN(parseFloat(bbEl.value))) ? parseFloat(bbEl.value) : oldB;

        // 兼容舊版 c
        const oldC = document.getElementById('inp_Z_c') ? parseFloat(document.getElementById('inp_Z_c').value) : 0;
        const ctEl = document.getElementById('inp_Z_ct');
        const cbEl = document.getElementById('inp_Z_cb');
        data.ct = (ctEl && !isNaN(parseFloat(ctEl.value))) ? parseFloat(ctEl.value) : oldC;
        data.cb = (cbEl && !isNaN(parseFloat(cbEl.value))) ? parseFloat(cbEl.value) : oldC;

        // r
        const rEl = document.getElementById('inp_Z_r');
        const rVal = parseFloat(rEl ? rEl.value : 0);
        data.r = (isNaN(rVal) || rVal < 0) ? 0 : rVal;

        if (data.h <= 0 || data.t <= 0) isValid = false;
    } else if (type === 'L') {
        data.h = getValue('h');
        data.b = getValue('b');
        // 讀取不等厚參數，為了相容舊版邏輯，若沒填則取 t (雖然 HTML 已改)
        const tvEl = document.getElementById('inp_L_tv');
        const thEl = document.getElementById('inp_L_th');
        // 若 HTML 還沒更新 dom ID，嘗試抓舊的 t
        const oldT = document.getElementById('inp_L_t') ? parseFloat(document.getElementById('inp_L_t').value) : 0;

        data.tv = tvEl ? parseFloat(tvEl.value) : oldT;
        data.th = thEl ? parseFloat(thEl.value) : oldT;

        if (data.tv <= 0 || data.th <= 0) isValid = false;

        const rEl = document.getElementById('inp_L_r');
        const rVal = parseFloat(rEl ? rEl.value : 0);
        data.r = (isNaN(rVal) || rVal < 0) ? 0 : rVal;
    } else if (type === 'Pipe') {
        data.d = getValue('d');
        data.t = getValue('t');
    } else if (type === 'Box') {
        data.h = getValue('h');
        data.b = getValue('b');
        data.t = getValue('t');

        const rEl = document.getElementById('inp_Box_r');
        const rVal = parseFloat(rEl ? rEl.value : 0);
        data.r = (isNaN(rVal) || rVal < 0) ? 0 : rVal;
    }

    if (!isValid) return null;
    return data;
}

function calculateAndDraw(onlyDraw = false) {
    const data = getSectionData();
    const canvas = document.getElementById('sectionCanvas');
    const ctx = canvas.getContext('2d');

    if (!data) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        return;
    }

    // --- 繪圖邏輯分配 ---
    switch (data.type) {
        case 'H':
            // 修改這一行，加入 data.r
            drawHSection(data.h, data.tw, data.bft, data.tft, data.bfb, data.tfb, data.r);
            break;
        case 'Channel':
            drawChannelSection(data.h, data.tw, data.bft, data.bfb, data.tft, data.tfb, data.r);
            break;
        case 'C':
            drawCSection(data.h, data.t, data.bt, data.bb, data.ct, data.cb, data.r);
            break;
        case 'L':
            drawAngleSection(data.h, data.b, data.tv, data.th, data.r);
            break;
        case 'T':
            drawTSection(data.h, data.bf, data.tw, data.tf, data.r);
            break;
        case 'Z':
            drawZSection(data.h, data.t, data.bt, data.bb, data.ct, data.cb, data.r);
            break;
        case 'Pipe':
            drawPipeSection(data.d, data.t);
            break;
        case 'Box':
            drawBoxSection(data.h, data.b, data.t, data.r);
            break;
        default:
            ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    if (!onlyDraw) {
        fetchData(data);
    }
}

// --- 通用：設置畫布與縮放 ---
function setupCanvas(w, h_dim) {
    const canvas = document.getElementById('sectionCanvas');
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    const maxDim = Math.max(w, h_dim);
    if (maxDim === 0) return null;

    // 縮放比例 (留 20% 邊距)
    const scale = (Math.min(width, height) * 0.8) / maxDim;
    const cx = width / 2;
    const cy = height / 2;

    ctx.beginPath();
    ctx.fillStyle = '#dfe6e9';
    ctx.strokeStyle = '#2c3e50';
    ctx.lineWidth = 2;

    return {ctx, cx, cy, scale};
}

// --- 1. H Section ---
// drawHSection(h, tw, bft, tft, bfb, tfb, r)
function drawHSection(h, tw, bft, tft, bfb, tfb, r = 0) {
    // 找出最大寬度以決定縮放
    const maxW = Math.max(bft, bfb);
    const {ctx, cx, cy, scale} = setupCanvas(maxW, h) || {};
    if (!ctx) return;

    const _h = h * scale;
    const _tw = tw * scale;
    const _bft = bft * scale; // 上翼板寬
    const _tft = tft * scale; // 上翼板厚
    const _bfb = bfb * scale; // 下翼板寬
    const _tfb = tfb * scale; // 下翼板厚

    // 圓角半徑限制 (取最小值以免繪圖錯誤)
    // 需同時檢查上側空間與下側空間
    const spaceTop = (_bft - _tw) / 2;
    const spaceBot = (_bfb - _tw) / 2;
    const webH = _h - _tft - _tfb;
    const maxR = Math.min(spaceTop, spaceBot, webH / 2);
    const _r = Math.min(r * scale, maxR);

    const topY = cy - _h / 2;
    const botY = cy + _h / 2;

    // 定義各個關鍵 X 座標 (以中心 cx 為基準)
    // 左邊是減，右邊是加
    const topL = cx - _bft / 2;
    const topR = cx + _bft / 2;
    const botL = cx - _bfb / 2;
    const botR = cx + _bfb / 2;
    const webL = cx - _tw / 2;
    const webR = cx + _tw / 2;

    const flangeTopInnerY = topY + _tft;
    const flangeBotInnerY = botY - _tfb;

    ctx.beginPath();

    // 1. 上翼板: 左上 -> 右上 -> 右下
    ctx.moveTo(topL, topY);
    ctx.lineTo(topR, topY);
    ctx.lineTo(topR, flangeTopInnerY);

    // 2. 右上圓角 (上翼板下緣 -> 腹板右側)
    // 控制點 (webR, flangeTopInnerY)
    ctx.arcTo(webR, flangeTopInnerY, webR, cy, _r);

    // 3. 右下圓角 (腹板右側 -> 下翼板上緣)
    // 控制點 (webR, flangeBotInnerY)
    ctx.arcTo(webR, flangeBotInnerY, botR, flangeBotInnerY, _r);

    // 4. 下翼板: 右上 -> 右下 -> 左下 -> 左上
    ctx.lineTo(botR, flangeBotInnerY);
    ctx.lineTo(botR, botY);
    ctx.lineTo(botL, botY);
    ctx.lineTo(botL, flangeBotInnerY);

    // 5. 左下圓角 (下翼板上緣 -> 腹板左側)
    // 控制點 (webL, flangeBotInnerY)
    ctx.arcTo(webL, flangeBotInnerY, webL, cy, _r);

    // 6. 左上圓角 (腹板左側 -> 上翼板下緣)
    // 控制點 (webL, flangeTopInnerY)
    ctx.arcTo(webL, flangeTopInnerY, topL, flangeTopInnerY, _r);

    // 7. 回到上翼板左下
    ctx.lineTo(topL, flangeTopInnerY);

    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // 標註
    ctx.fillStyle = '#2d3436';
    ctx.font = '14px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(`H=${h}`, cx + maxW / 2 + 20, cy);
    if (bft === bfb) {
        ctx.fillText(`B=${bft}`, cx, topY - 10);
    } else {
        ctx.fillText(`Bt=${bft}`, cx, topY - 10);
        ctx.fillText(`Bb=${bfb}`, cx, botY + 20);
    }
}

// --- 2. Channel Section (槽鋼, 支援不等寬 bft/bfb, 不等厚 tft/tfb 與圓角 r) ---
function drawChannelSection(h, tw, bft, bfb, tft, tfb, r = 0) {
    // 找出最大寬度以決定縮放 (Canvas 寬度需容納最寬的翼板)
    const maxW = Math.max(bft, bfb);
    const {ctx, cx, cy, scale} = setupCanvas(maxW, h) || {};
    if (!ctx) return;

    const _h = h * scale;
    const _tw = tw * scale;
    const _bft = bft * scale;
    const _bfb = bfb * scale;
    const _tft = tft * scale;
    const _tfb = tfb * scale;

    // 限制圓角最大值
    const webClearH = _h - _tft - _tfb;
    // 上下翼板的淨寬可能不同，取最小的來限制 r
    const flangeClearTop = _bft - _tw;
    const flangeClearBot = _bfb - _tw;
    const maxR = Math.min(flangeClearTop, flangeClearBot, webClearH / 2);
    const _r = Math.min(r * scale, maxR);

    // 座標定義：開口向右
    // 為了視覺平衡，將腹板背部設為最左側基準，但整體圖形居中
    // 整個圖形的寬度是 maxW, 高度是 h
    // 左上角基準點 (leftX, topY)
    const leftX = cx - maxW / 2;
    const topY = cy - _h / 2;
    const botY = topY + _h;

    // 關鍵 X 座標
    const webInnerX = leftX + _tw;
    const topTipX = leftX + _bft;
    const botTipX = leftX + _bfb;

    // 關鍵 Y 座標
    const flangeTopInnerY = topY + _tft;
    const flangeBotInnerY = botY - _tfb;

    ctx.beginPath();

    // 1. 左上角 (腹板背部頂端)
    ctx.moveTo(leftX, topY);

    // 2. 右上角 (上翼板尖端)
    ctx.lineTo(topTipX, topY);

    // 3. 上翼板內側尖端 (垂直向下)
    ctx.lineTo(topTipX, flangeTopInnerY);

    // 4. 上翼板內側水平 -> 上圓角
    // 目標：連到腹板
    // 控制點：(webInnerX, flangeTopInnerY)
    // 結束方向：向下
    ctx.arcTo(webInnerX, flangeTopInnerY, webInnerX, cy, _r);

    // 5. 腹板內側向下 -> 下圓角
    // 控制點：(webInnerX, flangeBotInnerY)
    // 結束方向：向右 (下翼板方向)
    ctx.arcTo(webInnerX, flangeBotInnerY, botTipX, flangeBotInnerY, _r);

    // 6. 下翼板內側水平 -> 尖端
    ctx.lineTo(botTipX, flangeBotInnerY);

    // 7. 下翼板尖端 (垂直向下)
    ctx.lineTo(botTipX, botY);

    // 8. 左下角 (腹板背部底端)
    ctx.lineTo(leftX, botY);

    // 9. 回到起點
    ctx.lineTo(leftX, topY);

    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // 標註
    ctx.fillStyle = '#2d3436';
    ctx.font = '14px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(`H=${h}`, leftX - 15, cy);

    // 分別標註上下寬度
    if (bft === bfb) {
        ctx.fillText(`B=${bft}`, cx, topY - 10);
    } else {
        ctx.fillText(`Bt=${bft}`, leftX + _bft / 2, topY - 10);
        ctx.fillText(`Bb=${bfb}`, leftX + _bfb / 2, botY + 20);
    }
}

// --- 3. C Section (冷軋 C 型鋼, 全參數化, 內外圓角) ---
function drawCSection(h, t, bt, bb, ct, cb, r = 0) {
    const maxW = Math.max(bt, bb);
    const {ctx, cx, cy, scale} = setupCanvas(maxW, h) || {};
    if (!ctx) return;

    const _h = h * scale;
    const _t = t * scale;
    const _bt = bt * scale;
    const _bb = bb * scale;
    const _ct = ct * scale;
    const _cb = cb * scale;

    // 內半徑 r, 外半徑 R = r + t
    const _r_in = r * scale;
    const _r_out = _r_in + _t;

    // 座標定義 (Canvas Y 向下為正)
    // 為了美觀，將腹板背部置於左側，整體置中
    // 總寬 maxW, 總高 h
    const xLeft = cx - maxW / 2;
    const yTop = cy - _h / 2;
    const yBot = yTop + _h;

    // 圓角中心點計算
    // 左上圓心 (外R參考點)
    const cTL_x = xLeft + _r_out;
    const cTL_y = yTop + _r_out;

    // 左下圓心
    const cBL_x = xLeft + _r_out;
    const cBL_y = yBot - _r_out;

    // 右上圓心 (翼板-唇)
    const cTR_x = xLeft + _bt - _r_out;
    const cTR_y = yTop + _r_out;

    // 右下圓心 (翼板-唇)
    const cBR_x = xLeft + _bb - _r_out;
    const cBR_y = yBot - _r_out;

    ctx.beginPath();

    // === 1. 外輪廓 (順時針) ===
    // 起點：上唇外側頂端 (假設唇是直的)
    // 唇外緣 X = xLeft + _bt
    // 唇外緣頂 Y = yTop + _ct

    // 從上唇尖端開始
    ctx.moveTo(xLeft + _bt, yTop + _ct);

    // 1-1. 上唇外側向上
    ctx.lineTo(xLeft + _bt, yTop + _r_out);

    // 1-2. 右上外圓角 (上唇 -> 上翼板)
    // 圓心 (cTR_x, cTR_y), 0度 -> 270度 (逆時針畫? 不, 順時針是 0 -> -90)
    // Canvas arc(x, y, r, start, end) 預設順時針
    // 0 是 3點鐘方向, -PI/2 是 12點鐘
    ctx.arc(cTR_x, cTR_y, _r_out, 0, 1.5 * Math.PI, true);

    // 1-3. 上翼板外側向左
    ctx.lineTo(cTL_x, yTop);

    // 1-4. 左上外圓角 (上翼板 -> 腹板)
    // 270度 (1.5PI) -> 180度 (PI)
    ctx.arc(cTL_x, cTL_y, _r_out, 1.5 * Math.PI, Math.PI, true);

    // 1-5. 腹板外側向下
    ctx.lineTo(xLeft, cBL_y);

    // 1-6. 左下外圓角 (腹板 -> 下翼板)
    // 180度 (PI) -> 90度 (0.5PI)
    ctx.arc(cBL_x, cBL_y, _r_out, Math.PI, 0.5 * Math.PI, true);

    // 1-7. 下翼板外側向右
    ctx.lineTo(cBR_x, yBot);

    // 1-8. 右下外圓角 (下翼板 -> 下唇)
    // 90度 (0.5PI) -> 0度
    ctx.arc(cBR_x, cBR_y, _r_out, 0.5 * Math.PI, 0, true);

    // 1-9. 下唇外側向上到尖端
    ctx.lineTo(xLeft + _bb, yBot - _cb);

    // 1-10. 下唇尖端連到內側 (厚度)
    ctx.lineTo(xLeft + _bb - _t, yBot - _cb);

    // === 2. 內輪廓 (逆時針回去) ===
    // 2-1. 下唇內側向下
    ctx.lineTo(xLeft + _bb - _t, yBot - _r_out); // 走到內圓角起點

    // 2-2. 右下內圓角 (半徑 _r_in)
    // 圓心不變 (cBR_x, cBR_y), 0度 -> 90度 (順時針? 不, 我們要逆時針回去)
    // 0 -> 0.5PI (false = 順時針, 預設 false)
    ctx.arc(cBR_x, cBR_y, _r_in, 0, 0.5 * Math.PI, false);

    // 2-3. 下翼板內側向左
    ctx.lineTo(cBL_x, yBot - _t);

    // 2-4. 左下內圓角
    // 90度 -> 180度
    ctx.arc(cBL_x, cBL_y, _r_in, 0.5 * Math.PI, Math.PI, false);

    // 2-5. 腹板內側向上
    ctx.lineTo(xLeft + _t, cTL_y);

    // 2-6. 左上內圓角
    // 180度 -> 270度
    ctx.arc(cTL_x, cTL_y, _r_in, Math.PI, 1.5 * Math.PI, false);

    // 2-7. 上翼板內側向右
    ctx.lineTo(cTR_x, yTop + _t);

    // 2-8. 右上內圓角
    // 270度 -> 360度 (0)
    ctx.arc(cTR_x, cTR_y, _r_in, 1.5 * Math.PI, 0, false);

    // 2-9. 上唇內側向下
    ctx.lineTo(xLeft + _bt - _t, yTop + _ct);

    // 2-10. 閉合 (回到上唇外側尖端)
    ctx.closePath();

    ctx.fill();
    ctx.stroke();

    // 標註
    ctx.fillStyle = '#2d3436';
    ctx.font = '14px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(`H=${h}`, xLeft - 15, cy);
    if (bt === bb) ctx.fillText(`B=${bt}`, cx, yTop - 10);
    else {
        ctx.fillText(`Bt=${bt}`, xLeft + _bt / 2, yTop - 10);
        ctx.fillText(`Bb=${bb}`, xLeft + _bb / 2, yBot + 20);
    }
}

// --- 4. Angle Section (L型) ---
function drawAngleSection(h, b, tv, th, r = 0) {
    const {ctx, cx, cy, scale} = setupCanvas(b, h) || {};
    if (!ctx) return;

    const _h = h * scale;
    const _b = b * scale;
    const _tv = tv * scale;
    const _th = th * scale;

    // 限制圓角最大值
    const maxR = Math.min(_h - _th, _b - _tv);
    const _r = Math.min(r * scale, maxR);

    // 定義邊界框 (Bounding Box) 左上角
    const x0 = cx - _b / 2;
    const y0 = cy - _h / 2;

    // 關鍵座標點
    const outerCornerX = x0;
    const outerCornerY = y0 + _h;

    const topTipX = x0;
    const topTipY = y0;

    const topInnerX = x0 + _tv;
    const topInnerY = y0;

    const rightTipX = x0 + _b;
    const rightTipY = outerCornerY;

    const rightInnerX = x0 + _b;
    const rightInnerY = outerCornerY - _th;

    // 內角交點 (圓角控制點)
    const innerCornerX = x0 + _tv;
    const innerCornerY = outerCornerY - _th;

    ctx.beginPath();

    // 1. 外側角落 (左下)
    ctx.moveTo(outerCornerX, outerCornerY);

    // 2. 垂直肢外側向上 -> 頂端
    ctx.lineTo(topTipX, topTipY);

    // 3. 垂直肢頂端 -> 內側
    ctx.lineTo(topInnerX, topInnerY);

    // 4. 垂直肢內側向下 -> 圓角
    // 使用 arcTo 連接 "垂直內側線" 與 "水平內側線"
    // 控制點：內直角交點 (innerCornerX, innerCornerY)
    // 結束方向點：水平肢內側 (rightInnerX, innerCornerY)
    ctx.arcTo(innerCornerX, innerCornerY, rightInnerX, innerCornerY, _r);

    // 5. 水平肢內側向右 -> 末端
    ctx.lineTo(rightInnerX, rightInnerY);

    // 6. 水平肢末端 -> 下方
    ctx.lineTo(rightTipX, rightTipY);

    // 7. 回到起點 (外側角落)
    ctx.lineTo(outerCornerX, outerCornerY);

    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // 標註
    ctx.fillStyle = '#2d3436';
    ctx.font = '14px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(`H=${h}`, x0 - 15, cy);
    ctx.fillText(`B=${b}`, cx, outerCornerY + 15);
}

// --- 5. T Section (支援圓角 r) ---
function drawTSection(h, bf, tw, tf, r = 0) {
    const {ctx, cx, cy, scale} = setupCanvas(bf, h) || {};
    if (!ctx) return;

    const _h = h * scale;
    const _bf = bf * scale;
    const _tw = tw * scale;
    const _tf = tf * scale;

    // 限制最大顯示半徑，避免繪圖破裂
    // 限制條件：r 不能超過 (翼板寬的一半減去腹板厚的一半) 且 不能超過 (腹板高度)
    const maxR = Math.min((_bf - _tw) / 2, _h - _tf);
    const _r = Math.min(r * scale, maxR);

    // 座標定義 (Canvas y 軸向下為正)
    // T型鋼通常上方是翼板，下方是腹板
    const topY = cy - _h / 2;
    const botY = cy + _h / 2;
    const leftX = cx - _bf / 2;
    const rightX = cx + _bf / 2;

    // 腹板邊界
    const webLeftX = cx - _tw / 2;
    const webRightX = cx + _tw / 2;

    // 翼板下緣 Y
    const flangeBotY = topY + _tf;

    ctx.beginPath();

    // 1. 上翼板左上起點
    ctx.moveTo(leftX, topY);

    // 2. 上翼板右上
    ctx.lineTo(rightX, topY);

    // 3. 上翼板右下 (垂直向下)
    ctx.lineTo(rightX, flangeBotY);

    // 4. 下翼板右側 -> 腹板右側 (圓角)
    // 起點目前在 (rightX, flangeBotY)
    // 目標是往左畫到腹板，再往下轉
    // 控制點：腹板與翼板交點 (webRightX, flangeBotY)
    // 結束方向：沿著腹板向下
    ctx.arcTo(webRightX, flangeBotY, webRightX, botY, _r);

    // 5. 腹板右側向下到底
    ctx.lineTo(webRightX, botY);

    // 6. 腹板底部 (由右向左)
    ctx.lineTo(webLeftX, botY);

    // 7. 腹板左側向上 -> 下翼板左側 (圓角)
    // 控制點：(webLeftX, flangeBotY)
    // 結束方向：沿著翼板向左
    ctx.arcTo(webLeftX, flangeBotY, leftX, flangeBotY, _r);

    // 8. 下翼板左側 (回到最左邊)
    ctx.lineTo(leftX, flangeBotY);

    // 9. 回到起點 (上翼板左下 -> 左上)
    ctx.lineTo(leftX, topY);

    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // 尺寸標註
    ctx.fillStyle = '#2d3436';
    ctx.font = '14px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(`H = ${h}`, cx + _bf / 2 + 20, cy);
    ctx.fillText(`Bf = ${bf}`, cx, topY - 10);
}

// --- 6. Z Section (冷軋 Z 型鋼, 修正繪圖路徑) ---
function drawZSection(h, t, bt, bb, ct, cb, r = 0) {
    const maxW = Math.max(bt, bb) * 1.5;
    const { ctx, cx, cy, scale } = setupCanvas(maxW, h) || {};
    if (!ctx) return;

    const _h = h * scale;
    const _t = t * scale;
    const _bt = bt * scale;
    const _bb = bb * scale;
    const _ct = ct * scale;
    const _cb = cb * scale;

    const _r_in = r * scale;
    const _r_out = _r_in + _t;

    // 座標定義 (Canvas Y 向下為正)
    const webLeftX = cx - _t / 2;
    const webRightX = cx + _t / 2;
    const topY = cy - _h / 2;
    const botY = cy + _h / 2;

    // 圓心計算
    // 左上外 (腹板-上翼板)
    const cTL_out_x = webLeftX + _r_out;
    const cTL_out_y = topY + _r_out;
    // 右上外 (上翼板-上唇)
    const cTR_out_x = webLeftX + _bt - _r_out;
    const cTR_out_y = topY + _r_out;
    // 右下外 (腹板-下翼板)
    const cBR_out_x = webRightX - _r_out;
    const cBR_out_y = botY - _r_out;
    // 左下外 (下翼板-下唇)
    const cBL_out_x = webRightX - _bb + _r_out;
    const cBL_out_y = botY - _r_out;

    // 內圓心 (偏移 t)
    const cTR_in_x = webRightX + _r_in; // 上翼板-腹板
    const cTR_in_y = topY + _t + _r_in;
    const cBL_in_x = webLeftX - _r_in; // 下翼板-腹板
    const cBL_in_y = botY - _t - _r_in;

    // 上唇內圓心
    const cTopLip_in_x = webLeftX + _bt - _t - _r_in;
    const cTopLip_in_y = topY + _t + _r_in;
    // 下唇內圓心
    const cBotLip_in_x = webRightX - _bb + _t + _r_in;
    const cBotLip_in_y = botY - _t - _r_in;

    ctx.beginPath();

    // 1. 上唇內尖 (起點)
    ctx.moveTo(webLeftX + _bt - _t, topY + _ct);

    // 2. 上唇內側 -> 上翼板內 (內圓角)
    // 圓心 (cTopLip_in_x, cTR_out_y) 注意: 內外圓心在唇的部分是同心的
    // 0 -> -0.5PI (順時針? 不，逆時針)
    // Canvas: 0(右) -> 1.5PI(上)
    ctx.lineTo(webLeftX + _bt - _t, topY + _r_out);
    ctx.arc(webLeftX + _bt - _r_out, topY + _r_out, _r_in, 0, 1.5 * Math.PI, true);

    // 3. 上翼板內側 -> 腹板右 (內圓角)
    // 圓心 cTR_in_x, cTR_in_y
    // 1.5PI(上) -> 1.0PI(左)
    ctx.lineTo(cTR_in_x, topY + _t);
    ctx.arc(cTR_in_x, cTR_in_y, _r_in, 1.5 * Math.PI, Math.PI, true);

    // 4. 腹板右側 -> 下翼板外 (外圓角)
    // 圓心 cBR_out_x, cBR_out_y
    // 0(右) -> 0.5PI(下)
    ctx.lineTo(webRightX, botY - _r_out);
    ctx.arc(cBR_out_x, cBR_out_y, _r_out, 0, 0.5 * Math.PI, false); // 順時針

    // 5. 下翼板外 -> 下唇外 (外圓角)
    // 圓心 cBL_out_x, cBL_out_y
    // 0.5PI(下) -> 1.0PI(左)
    ctx.lineTo(cBL_out_x, botY);
    ctx.arc(cBL_out_x, cBL_out_y, _r_out, 0.5 * Math.PI, Math.PI, false); // 順時針

    // 6. 下唇外尖
    ctx.lineTo(webRightX - _bb, botY - _cb);

    // 7. 過厚度 -> 下唇內尖
    ctx.lineTo(webRightX - _bb + _t, botY - _cb);

    // 8. 下唇內 -> 下翼板內 (內圓角)
    // 圓心 (cBotLip_in_x, cBL_out_y)
    // 1.0PI(左) -> 0.5PI(下) -> 逆時針回去?
    // 我們現在是從下唇往回走。
    // 180(左) -> 270(上/ Canvas 1.5PI) ??
    // 下唇向上。轉右。
    // 1.0PI -> 1.5PI ?? 不，下唇向上走，轉右。
    // 是從 PI (左) 轉到 1.5PI (上)? 不對
    // 圓心在右側。角度從 PI 轉到 0.5PI (下)
    ctx.lineTo(webRightX - _bb + _t, botY - _r_out);
    ctx.arc(webRightX - _bb + _r_out, botY - _r_out, _r_in, Math.PI, 0.5 * Math.PI, true); // 逆時針

    // 9. 下翼板內 -> 腹板左 (內圓角)
    // 圓心 cBL_in_x, cBL_in_y
    // 0.5PI(下) -> 0(右)
    ctx.lineTo(cBL_in_x, botY - _t);
    ctx.arc(cBL_in_x, cBL_in_y, _r_in, 0.5 * Math.PI, 0, true); // 逆時針

    // 10. 腹板左 -> 上翼板外 (外圓角)
    // 圓心 cTL_out_x, cTL_out_y
    // 1.0PI(左) -> 1.5PI(上)
    ctx.lineTo(webLeftX, topY + _r_out);
    ctx.arc(cTL_out_x, cTL_out_y, _r_out, Math.PI, 1.5 * Math.PI, false); // 順時針

    // 11. 上翼板外 -> 上唇外 (外圓角)
    // 圓心 cTR_out_x, cTR_out_y
    // 1.5PI(上) -> 2.0PI(右)
    ctx.lineTo(cTR_out_x, topY);
    ctx.arc(cTR_out_x, cTR_out_y, _r_out, 1.5 * Math.PI, 0, false); // 順時針

    // 12. 上唇外尖
    ctx.lineTo(webLeftX + _bt, topY + _ct);

    // 13. 回到起點
    ctx.lineTo(webLeftX + _bt - _t, topY + _ct);

    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // 標註
    ctx.fillStyle = '#2d3436';
    ctx.textAlign = 'center';
    ctx.fillText(`H=${h}`, cx, cy);
}

// --- 7. Pipe (Round Tube) ---
function drawPipeSection(d, t) {
    const {ctx, cx, cy, scale} = setupCanvas(d, d) || {};
    if (!ctx) return;

    const _d = d * scale;
    const _t = t * scale;
    const _ri = (_d - 2 * _t) / 2;

    // Outer Circle
    ctx.beginPath();
    ctx.arc(cx, cy, _d / 2, 0, 2 * Math.PI);
    ctx.closePath();

    // Inner Circle (Hole) - Draw counter-clockwise to create hole
    ctx.arc(cx, cy, _ri, 0, 2 * Math.PI, true);
    ctx.closePath();

    ctx.fill("evenodd"); // Important for holes
    ctx.stroke();

    // Draw outer stroke again cleanly
    ctx.beginPath();
    ctx.arc(cx, cy, _d / 2, 0, 2 * Math.PI);
    ctx.stroke();
}

// --- 8. Box (Rect Tube, 支援圓角) ---
function drawBoxSection(h, b, t, r = 0) {
    const { ctx, cx, cy, scale } = setupCanvas(b, h) || {};
    if (!ctx) return;

    const _h = h * scale;
    const _b = b * scale;
    const _t = t * scale;

    const _r_in = r * scale;
    const _r_out = _r_in + _t;

    // 限制圓角最大值 (避免超過寬高的一半)
    // 這裡只限制繪圖顯示，後端有自己的限制
    const maxR = Math.min(_b/2, _h/2);
    const use_r_out = Math.min(_r_out, maxR);
    const use_r_in = Math.max(0, use_r_out - _t);

    // 左上角座標
    const x = cx - _b / 2;
    const y = cy - _h / 2;
    const w = _b;
    const h_dim = _h; // 避免變數名衝突

    ctx.beginPath();

    // === 1. 外輪廓 (順時針) ===
    // 從上邊中間開始
    ctx.moveTo(x + w/2, y);

    // 右上圓角
    ctx.arcTo(x + w, y, x + w, y + h_dim, use_r_out);

    // 右下圓角
    ctx.arcTo(x + w, y + h_dim, x, y + h_dim, use_r_out);

    // 左下圓角
    ctx.arcTo(x, y + h_dim, x, y, use_r_out);

    // 左上圓角
    ctx.arcTo(x, y, x + w, y, use_r_out);

    // 閉合
    ctx.closePath();

    // === 2. 內輪廓 (逆時針) ===
    // 這樣 fill() 才能挖洞
    // 內圈座標
    const xi = x + _t;
    const yi = y + _t;
    const wi = w - 2*_t;
    const hi = h_dim - 2*_t;

    if (wi > 0 && hi > 0) {
        // 從上邊中間開始 (逆時針)
        ctx.moveTo(xi + wi/2, yi);

        // 左上內圓角 (逆時針: 上 -> 左)
        // arcTo 控制點 (xi, yi), 結束點 (xi, yi+hi)
        ctx.arcTo(xi, yi, xi, yi + hi, use_r_in);

        // 左下內圓角
        ctx.arcTo(xi, yi + hi, xi + wi, yi + hi, use_r_in);

        // 右下內圓角
        ctx.arcTo(xi + wi, yi + hi, xi + wi, yi, use_r_in);

        // 右上內圓角
        ctx.arcTo(xi + wi, yi, xi, yi, use_r_in);

        ctx.closePath();
    }

    ctx.fill("evenodd"); // 確保挖洞
    ctx.stroke();

    // 標註
    ctx.fillStyle = '#2d3436';
    ctx.textAlign = 'center';
    ctx.fillText(`H=${h}`, x - 15, cy);
    ctx.fillText(`B=${b}`, cx, y - 10);
}

// --- AJAX & Results ---
function fetchData(dataPayload) {
    const form = document.getElementById('sectionForm');
    const apiUrl = form.getAttribute('data-api-url');
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    const csrftoken = csrfInput ? csrfInput.value : '';
    const btn = document.getElementById('calculate-button');
    if (btn.innerText !== "計算中..." && btn.innerText !== "計算完成") {
        btn.dataset.originalText = btn.innerText;
    }
    const originalText = btn.dataset.originalText || "開始計算";

    // 2. 設定按鈕狀態
    btn.innerText = "計算中...";
    btn.disabled = true;
    btn.style.opacity = "0.7"; // 視覺上變淡

    fetch(apiUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify(dataPayload)
    })
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            if (data.success) {
                cachedData = data.data;
                renderResults();

                // 3. 成功提示 (顯示 "計算完成" 0.5秒)
                btn.innerText = "計算完成";
                setTimeout(() => {
                    btn.innerText = originalText;
                    btn.disabled = false;
                    btn.style.opacity = "1";
                }, 500);
            } else {
                alert('計算錯誤: ' + data.error);
                // 失敗時立即恢復
                btn.innerText = originalText;
                btn.disabled = false;
                btn.style.opacity = "1";
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('發生連線錯誤，請稍後再試。');
            // 錯誤時立即恢復
            btn.innerText = originalText;
            btn.disabled = false;
            btn.style.opacity = "1";
        });
}

function renderResults() {
    if (!cachedData) return;
    const unitRadio = document.querySelector('input[name="resultUnit"]:checked');
    const unit = unitRadio ? unitRadio.value : 'mm';

    let f_len = 1, f_area = 1, f_mod = 1, f_in = 1, f_warp = 1;
    if (unit === 'cm') {
        f_len = 10;
        f_area = 100;
        f_mod = 1000;
        f_in = 10000;
        f_warp = 1000000;
    }

    updateVal('res-area', cachedData.area, f_area);
    updateVal('res-cx', cachedData.cx, f_len);
    updateVal('res-cy', cachedData.cy, f_len);
    updateVal('res-pcx', cachedData.pcx, f_len);
    updateVal('res-pcy', cachedData.pcy, f_len);
    updateVal('res-ixx', cachedData.ixx, f_in);
    updateVal('res-iyy', cachedData.iyy, f_in);
    updateVal('res-ixy', cachedData.ixy, f_in);
    updateVal('res-rx', cachedData.rx, f_len);
    updateVal('res-ry', cachedData.ry, f_len);
    updateVal('res-sx-top', cachedData.sx_top, f_mod);
    updateVal('res-sx-bot', cachedData.sx_bot, f_mod);
    updateVal('res-sy-right', cachedData.sy_right, f_mod);
    updateVal('res-sy-left', cachedData.sy_left, f_mod);
    updateVal('res-zx', cachedData.zx, f_mod);
    updateVal('res-zy', cachedData.zy, f_mod);
    updateVal('res-cw', cachedData.cw, f_warp);
    updateVal('res-j', cachedData.j, f_in);
    updateVal('res-rts', cachedData.rts, f_len);
    updateUnitLabels(unit);
}

function updateVal(id, value, divisor) {
    const el = document.getElementById(id);
    if (el) el.innerText = (value / divisor).toLocaleString('en-US', {
        maximumFractionDigits: 3,
        minimumFractionDigits: 0
    });
}

function updateUnitLabels(unit) {
    const text = (unit === 'cm') ? 'cm' : 'mm';
    document.querySelectorAll('.unit-area').forEach(e => e.innerText = `${text}²`);
    document.querySelectorAll('.unit-inertia').forEach(e => e.innerText = `${text}⁴`);
    document.querySelectorAll('.unit-len').forEach(e => e.innerText = `${text}`);
    document.querySelectorAll('.unit-modulus').forEach(e => e.innerText = `${text}³`);
    document.querySelectorAll('.unit-warp').forEach(e => e.innerText = `${text}⁶`);
}