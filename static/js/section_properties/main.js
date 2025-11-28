/**
 * section_properties/static/section_properties/js/main.js
 * 工程製圖版 - Z型鋼完美修復 & 標註優化
 */

document.addEventListener('DOMContentLoaded', function () {
    bindEvents();
    resizeCanvas();
    window.addEventListener('resize', () => {
        resizeCanvas();
        calculateAndDraw(true);
    });
    toggleInputFields();
});

let cachedData = null;

function resizeCanvas() {
    const container = document.getElementById('canvasContainer');
    const canvas = document.getElementById('sectionCanvas');
    if (container && canvas) {
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
    }
}

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

function getVal(id) {
    const el = document.getElementById(id);
    const val = parseFloat(el ? el.value : 0);
    return isNaN(val) ? 0 : val;
}

function getSectionData() {
    const type = document.getElementById('sectionTypeSelect').value;
    let data = {type: type};

    if (type === 'H') {
        data.h = getVal('inp_H_h');
        data.tw = getVal('inp_H_tw');
        data.bft = getVal('inp_H_bft');
        data.tft = getVal('inp_H_tft');
        data.bfb = getVal('inp_H_bfb');
        data.tfb = getVal('inp_H_tfb');
        data.r = getVal('inp_H_r');
    } else if (type === 'Channel') {
        data.h = getVal('inp_Channel_h');
        data.tw = getVal('inp_Channel_tw');
        data.bft = getVal('inp_Channel_bft');
        data.tft = getVal('inp_Channel_tft');
        data.bfb = getVal('inp_Channel_bfb');
        data.tfb = getVal('inp_Channel_tfb');
        data.r = getVal('inp_Channel_r');
    } else if (type === 'C') {
        data.h = getVal('inp_C_h');
        data.t = getVal('inp_C_t');
        data.bt = getVal('inp_C_bt');
        data.ct = getVal('inp_C_ct');
        data.bb = getVal('inp_C_bb');
        data.cb = getVal('inp_C_cb');
        data.r = getVal('inp_C_r');
    } else if (type === 'L') {
        data.h = getVal('inp_L_h');
        data.b = getVal('inp_L_b');
        data.tv = getVal('inp_L_tv');
        data.th = getVal('inp_L_th');
        data.r = getVal('inp_L_r');
    } else if (type === 'T') {
        data.h = getVal('inp_T_h');
        data.bf = getVal('inp_T_bf');
        data.tw = getVal('inp_T_tw');
        data.tf = getVal('inp_T_tf');
        data.r = getVal('inp_T_r');
    } else if (type === 'Z') {
        data.h = getVal('inp_Z_h');
        data.t = getVal('inp_Z_t');
        data.bt = getVal('inp_Z_bt');
        data.ct = getVal('inp_Z_ct');
        data.bb = getVal('inp_Z_bb');
        data.cb = getVal('inp_Z_cb');
        data.r = getVal('inp_Z_r');
    } else if (type === 'Pipe') {
        data.d = getVal('inp_Pipe_d');
        data.t = getVal('inp_Pipe_t');
    } else if (type === 'Box') {
        data.h = getVal('inp_Box_h');
        data.b = getVal('inp_Box_b');
        data.t = getVal('inp_Box_t');
        data.r = getVal('inp_Box_r');
    }

    return data;
}

function calculateAndDraw(onlyDraw = false) {
    const data = getSectionData();
    const canvas = document.getElementById('sectionCanvas');
    const ctx = canvas.getContext('2d');

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!data) return;

    switch (data.type) {
        case 'H':
            drawHSection(data);
            break;
        case 'Channel':
            drawChannelSection(data);
            break;
        case 'C':
            drawCSection(data);
            break;
        case 'L':
            drawLSection(data);
            break;
        case 'T':
            drawTSection(data);
            break;
        case 'Z':
            drawZSection(data);
            break;
        case 'Pipe':
            drawPipeSection(data);
            break;
        case 'Box':
            drawBoxSection(data);
            break;
    }

    if (!onlyDraw) fetchData(data);
}

// --- 工程標註與畫布設定 ---

function setupEngineeringCanvas(w_dim, h_dim) {
    const canvas = document.getElementById('sectionCanvas');
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;

    const pX = w * 0.15;
    const pY = h * 0.15;
    const availW = w - pX * 2;
    const availH = h - pY * 2;

    const scale = Math.min(availW / w_dim, availH / h_dim);
    const cx = w / 2;
    const cy = h / 2;

    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#334155';
    ctx.fillStyle = '#e2e8f0';

    return {ctx, cx, cy, scale};
}

function drawDim(ctx, p1, p2, text, offset) {
    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len < 1) return;

    const nx = -dy / len;
    const ny = dx / len;

    const o1 = {x: p1.x + nx * offset, y: p1.y + ny * offset};
    const o2 = {x: p2.x + nx * offset, y: p2.y + ny * offset};

    ctx.save();
    ctx.strokeStyle = '#64748b';
    ctx.fillStyle = '#64748b';
    ctx.lineWidth = 1;
    ctx.font = '12px "JetBrains Mono"';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    const gap = 3;
    const ext = 5;
    ctx.beginPath();
    ctx.moveTo(p1.x + nx * gap, p1.y + ny * gap);
    ctx.lineTo(o1.x + nx * ext, o1.y + ny * ext);
    ctx.moveTo(p2.x + nx * gap, p2.y + ny * gap);
    ctx.lineTo(o2.x + nx * ext, o2.y + ny * ext);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(o1.x, o1.y);
    ctx.lineTo(o2.x, o2.y);
    ctx.stroke();

    drawArrow(ctx, o2, o1);
    drawArrow(ctx, o1, o2);

    let angle = Math.atan2(dy, dx);
    if (angle > Math.PI / 2 || angle < -Math.PI / 2) angle += Math.PI;

    const midX = (o1.x + o2.x) / 2;
    const midY = (o1.y + o2.y) / 2;

    const tw = ctx.measureText(text).width;
    ctx.translate(midX, midY);
    ctx.rotate(angle);
    ctx.fillStyle = 'rgba(255,255,255,0.85)';
    ctx.fillRect(-tw / 2 - 3, -8, tw + 6, 16);
    ctx.fillStyle = '#0f172a';
    ctx.fillText(text, 0, 0);

    ctx.restore();
}

function drawArrow(ctx, tip, tail) {
    const size = 6;
    const angle = Math.atan2(tail.y - tip.y, tail.x - tip.x);
    ctx.beginPath();
    ctx.moveTo(tip.x, tip.y);
    ctx.lineTo(tip.x + size * Math.cos(angle - Math.PI / 6), tip.y + size * Math.sin(angle - Math.PI / 6));
    ctx.lineTo(tip.x + size * Math.cos(angle + Math.PI / 6), tip.y + size * Math.sin(angle + Math.PI / 6));
    ctx.closePath();
    ctx.fill();
}

// --- 繪圖函數 ---

// 1. H Section
function drawHSection(d) {
    const maxW = Math.max(d.bft, d.bfb);
    const {ctx, cx, cy, scale} = setupEngineeringCanvas(maxW, d.h);

    const H = d.h * scale;
    const Bft = d.bft * scale;
    const Bfb = d.bfb * scale;
    const tw = d.tw * scale;
    const tft = d.tft * scale;
    const tfb = d.tfb * scale;
    const maxR = Math.min((Bft - tw) / 2, (Bfb - tw) / 2, (H - tft - tfb) / 2);
    const r = Math.min(d.r * scale, maxR);

    const ty = cy - H / 2;
    const by = cy + H / 2;
    const wxL = cx - tw / 2;
    const wxR = cx + tw / 2;
    const minX = Math.min(cx - Bft / 2, cx - Bfb / 2);

    ctx.beginPath();
    ctx.moveTo(cx - Bft / 2, ty);
    ctx.lineTo(cx + Bft / 2, ty);
    ctx.lineTo(cx + Bft / 2, ty + tft);
    ctx.lineTo(wxR + r, ty + tft);
    ctx.arcTo(wxR, ty + tft, wxR, cy, r);
    ctx.lineTo(wxR, by - tfb - r);
    ctx.arcTo(wxR, by - tfb, wxR + r, by - tfb, r);
    ctx.lineTo(cx + Bfb / 2, by - tfb);
    ctx.lineTo(cx + Bfb / 2, by);
    ctx.lineTo(cx - Bfb / 2, by);
    ctx.lineTo(cx - Bfb / 2, by - tfb);
    ctx.lineTo(wxL - r, by - tfb);
    ctx.arcTo(wxL, by - tfb, wxL, cy, r);
    ctx.lineTo(wxL, ty + tft + r);
    ctx.arcTo(wxL, ty + tft, wxL - r, ty + tft, r);
    ctx.lineTo(cx - Bft / 2, ty + tft);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    const off = 30;
    drawDim(ctx, {x: minX - 40, y: ty}, {x: minX - 40, y: by}, `H=${d.h}`, 0);
    drawDim(ctx, {x: cx - Bft / 2, y: ty}, {x: cx + Bft / 2, y: ty}, `Bft=${d.bft}`, -off);
    drawDim(ctx, {x: cx - Bfb / 2, y: by}, {x: cx + Bfb / 2, y: by}, `Bfb=${d.bfb}`, off);
    drawDim(ctx, {x: wxL, y: cy}, {x: wxR, y: cy}, `${d.tw}`, 0);
}

// 2. Channel
function drawChannelSection(d) {
    const maxW = Math.max(d.bft, d.bfb);
    const {ctx, cx, cy, scale} = setupEngineeringCanvas(maxW, d.h);

    const H = d.h * scale;
    const Bft = d.bft * scale;
    const Bfb = d.bfb * scale;
    const tw = d.tw * scale;
    const tft = d.tft * scale;
    const tfb = d.tfb * scale;

    const maxR = Math.min((Bft - tw), (Bfb - tw), (H - tft - tfb) / 2);
    const r = Math.min(d.r * scale, maxR);

    const lx = cx - maxW / 2;
    const ty = cy - H / 2;
    const by = cy + H / 2;
    const innerX = lx + tw;

    ctx.beginPath();
    ctx.moveTo(lx, ty);
    ctx.lineTo(lx + Bft, ty);
    ctx.lineTo(lx + Bft, ty + tft);
    ctx.lineTo(innerX + r, ty + tft);
    ctx.arcTo(innerX, ty + tft, innerX, cy, r);
    ctx.lineTo(innerX, by - tfb - r);
    ctx.arcTo(innerX, by - tfb, innerX + r, by - tfb, r);
    ctx.lineTo(lx + Bfb, by - tfb);
    ctx.lineTo(lx + Bfb, by);
    ctx.lineTo(lx, by);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    const off = 25;
    drawDim(ctx, {x: lx - 40, y: ty}, {x: lx - 40, y: by}, `H=${d.h}`, 0);
    drawDim(ctx, {x: lx, y: ty}, {x: lx + Bft, y: ty}, `Bft=${d.bft}`, -off);
    drawDim(ctx, {x: lx, y: by}, {x: lx + Bfb, y: by}, `Bfb=${d.bfb}`, off);
}

// 3. L Angle
function drawLSection(d) {
    const {ctx, cx, cy, scale} = setupEngineeringCanvas(d.b, d.h);
    const H = d.h * scale;
    const B = d.b * scale;
    const th = d.th * scale;
    const tv = d.tv * scale;
    const r = Math.min(d.r * scale, (H - th), (B - tv));

    const lx = cx - B / 2;
    const ty = cy - H / 2;
    const by = cy + H / 2;
    const rx = cx + B / 2;
    const innerX = lx + tv;
    const innerY = by - th;

    ctx.beginPath();
    ctx.moveTo(lx, ty);
    ctx.lineTo(innerX, ty);
    ctx.lineTo(innerX, innerY - r);
    ctx.arcTo(innerX, innerY, innerX + r, innerY, r);
    ctx.lineTo(rx, innerY);
    ctx.lineTo(rx, by);
    ctx.lineTo(lx, by);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    const off = 25;
    drawDim(ctx, {x: lx - 40, y: ty}, {x: lx - 40, y: by}, `H=${d.h}`, 0);
    drawDim(ctx, {x: lx, y: by}, {x: rx, y: by}, `B=${d.b}`, off);
    drawDim(ctx, {x: lx, y: ty}, {x: innerX, y: ty}, `${d.tv}`, -10);
}

// 4. T Section
function drawTSection(d) {
    const {ctx, cx, cy, scale} = setupEngineeringCanvas(d.bf, d.h);
    const H = d.h * scale;
    const Bf = d.bf * scale;
    const tf = d.tf * scale;
    const tw = d.tw * scale;
    const r = Math.min(d.r * scale, (Bf - tw) / 2, H - tf);

    const ty = cy - H / 2;
    const by = cy + H / 2;
    const lx = cx - Bf / 2;
    const rx = cx + Bf / 2;
    const wxL = cx - tw / 2;
    const wxR = cx + tw / 2;
    const fy = ty + tf;

    ctx.beginPath();
    ctx.moveTo(lx, ty);
    ctx.lineTo(rx, ty);
    ctx.lineTo(rx, fy);
    ctx.lineTo(wxR + r, fy);
    ctx.arcTo(wxR, fy, wxR, by, r);
    ctx.lineTo(wxR, by);
    ctx.lineTo(wxL, by);
    ctx.lineTo(wxL, fy + r);
    ctx.arcTo(wxL, fy, wxL - r, fy, r);
    ctx.lineTo(lx, fy);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    const off = 25;
    drawDim(ctx, {x: lx, y: ty}, {x: rx, y: ty}, `Bf=${d.bf}`, -off);
    drawDim(ctx, {x: lx - 40, y: ty}, {x: lx - 40, y: by}, `H=${d.h}`, 0);
}

// 5. Box Section
function drawBoxSection(d) {
    const {ctx, cx, cy, scale} = setupEngineeringCanvas(d.b, d.h);
    const H = d.h * scale;
    const B = d.b * scale;
    const t = d.t * scale;

    const rIn = d.r * scale;
    const rOut = rIn + t;

    const lx = cx - B / 2;
    const ty = cy - H / 2;

    function roundRect(x, y, w, h, r) {
        ctx.moveTo(x + r, y);
        ctx.arcTo(x + w, y, x + w, y + h, r);
        ctx.arcTo(x + w, y + h, x, y + h, r);
        ctx.arcTo(x, y + h, x, y, r);
        ctx.arcTo(x, y, x + w, y, r);
    }

    ctx.beginPath();
    roundRect(lx, ty, B, H, rOut);

    ctx.moveTo(lx + t, ty + t + rIn);
    ctx.arcTo(lx + t, ty + H - t, lx + B - t, ty + H - t, rIn);
    ctx.arcTo(lx + B - t, ty + H - t, lx + B - t, ty + t, rIn);
    ctx.arcTo(lx + B - t, ty + t, lx + t, ty + t, rIn);
    ctx.arcTo(lx + t, ty + t, lx + t, ty + H - t, rIn);

    ctx.fill("evenodd");
    ctx.stroke();

    const off = 30;
    drawDim(ctx, {x: lx, y: ty}, {x: lx + B, y: ty}, `B=${d.b}`, -off);
    drawDim(ctx, {x: lx - 40, y: ty}, {x: lx - 40, y: ty + H}, `H=${d.h}`, 0);
    drawDim(ctx, {x: lx + B, y: cy}, {x: lx + B - t, y: cy}, `t=${d.t}`, -10);
}

// 6. C Section
function drawCSection(d) {
    const maxW = Math.max(d.bt, d.bb);
    const {ctx, cx, cy, scale} = setupEngineeringCanvas(maxW, d.h);
    const H = d.h * scale;
    const t = d.t * scale;
    const Bt = d.bt * scale;
    const Bb = d.bb * scale;
    const Ct = d.ct * scale;
    const Cb = d.cb * scale;
    const rIn = d.r * scale;
    const rOut = rIn + t;

    const lx = cx - maxW / 2;
    const ty = cy - H / 2;
    const by = cy + H / 2;

    ctx.beginPath();
    ctx.moveTo(lx + Bt, ty + Ct);
    ctx.lineTo(lx + Bt, ty + rOut);
    ctx.arcTo(lx + Bt, ty, lx, ty, rOut);
    ctx.arcTo(lx, ty, lx, by, rOut);
    ctx.arcTo(lx, by, lx + Bb, by, rOut);
    ctx.arcTo(lx + Bb, by, lx + Bb, by - rOut, rOut);
    ctx.lineTo(lx + Bb, by - Cb);
    ctx.lineTo(lx + Bb - t, by - Cb);

    ctx.lineTo(lx + Bb - t, by - rOut);
    ctx.arcTo(lx + Bb - t, by - t, lx + t, by - t, rIn);
    ctx.arcTo(lx + t, by - t, lx + t, ty + t, rIn);
    ctx.arcTo(lx + t, ty + t, lx + Bt - t, ty + t, rIn);
    ctx.arcTo(lx + Bt - t, ty + t, lx + Bt - t, ty + rOut, rIn);
    ctx.lineTo(lx + Bt - t, ty + Ct);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    const off = 25;
    drawDim(ctx, {x: lx - 40, y: ty}, {x: lx - 40, y: by}, `H=${d.h}`, 0);
    drawDim(ctx, {x: lx, y: ty}, {x: lx + Bt, y: ty}, `Bt=${d.bt}`, -off);
    drawDim(ctx, {x: lx, y: by}, {x: lx + Bb, y: by}, `Bb=${d.bb}`, off);
}

// 7. Z Section (重寫版 - 解決交叉)
function drawZSection(d) {
    const maxW = Math.max(d.bt, d.bb) * 1.6;
    const {ctx, cx, cy, scale} = setupEngineeringCanvas(maxW, d.h);

    const H = d.h * scale;
    const t = d.t * scale;
    const Bt = d.bt * scale;
    const Bb = d.bb * scale;
    const Ct = d.ct * scale;
    const Cb = d.cb * scale;
    const rIn = d.r * scale;
    const rOut = rIn + t;

    const ty = cy - H / 2;
    const by = cy + H / 2;

    const wxL = cx - t / 2;
    const wxR = cx + t / 2;
    const minX = wxR - Bb;

    ctx.beginPath();

    // --- 外輪廓 (Outer) ---
    ctx.moveTo(wxL + Bt, ty + Ct);
    ctx.lineTo(wxL + Bt, ty + rOut);
    ctx.arcTo(wxL + Bt, ty, wxL, ty, rOut);
    ctx.arcTo(wxL, ty, wxL, by, rOut);
    ctx.arcTo(wxL, by - t, wxL - rIn, by - t, rIn); // 腹板連下翼 (內角)
    ctx.arcTo(wxR - Bb + t, by - t, wxR - Bb + t, by - rOut, rIn); // 下翼連下唇 (內角)
    ctx.lineTo(wxR - Bb + t, by - Cb);

    // --- 厚度 ---
    ctx.lineTo(wxR - Bb, by - Cb);

    // --- 內輪廓 (Inner) ---
    ctx.lineTo(wxR - Bb, by - rOut);
    ctx.arcTo(wxR - Bb, by, wxR, by, rOut);
    ctx.arcTo(wxR, by, wxR, ty, rOut);
    ctx.arcTo(wxR, ty + t, wxR + rIn, ty + t, rIn); // 腹板連上翼 (內角)
    ctx.arcTo(wxL + Bt - t, ty + t, wxL + Bt - t, ty + Ct, rIn); // 上翼連上唇 (內角)
    ctx.lineTo(wxL + Bt - t, ty + Ct);

    // --- 閉合 ---
    ctx.lineTo(wxL + Bt, ty + Ct);

    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // 標註
    const off = 30;
    drawDim(ctx, {x: minX - 40, y: ty}, {x: minX - 40, y: by}, `H=${d.h}`, 0);
    drawDim(ctx, {x: wxL, y: ty}, {x: wxL + Bt, y: ty}, `Bt=${d.bt}`, -off);
    drawDim(ctx, {x: wxR, y: by}, {x: wxR - Bb, y: by}, `Bb=${d.bb}`, off);
    drawDim(ctx, {x: wxL + Bt, y: ty}, {x: wxL + Bt, y: ty + Ct}, `${d.ct}`, off);
    drawDim(ctx, {x: wxR - Bb, y: by}, {x: wxR - Bb, y: by - Cb}, `${d.cb}`, -off);
}

// 8. Pipe
function drawPipeSection(d) {
    const {ctx, cx, cy, scale} = setupEngineeringCanvas(d.d, d.d);
    const D = d.d * scale;
    const t = d.t * scale;

    ctx.beginPath();
    ctx.arc(cx, cy, D / 2, 0, Math.PI * 2);
    ctx.arc(cx, cy, D / 2 - t, 0, Math.PI * 2, true); // Hole
    ctx.fill("evenodd");
    ctx.stroke();

    const minX = cx - D / 2;
    drawDim(ctx, {x: minX - 40, y: cy - D / 2}, {x: minX - 40, y: cy + D / 2}, `D=${d.d}`, 0);
    drawDim(ctx, {x: cx - D / 2, y: cy - D / 2 - 10}, {x: cx + D / 2, y: cy - D / 2 - 10}, `D=${d.d}`, -10);
    drawDim(ctx, {x: cx + D / 2, y: cy}, {x: cx + D / 2 - t, y: cy}, `t=${d.t}`, -10);
}


// --- Backend Fetch ---
function fetchData(dataPayload) {
    const btn = document.getElementById('calculate-button');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="ri-loader-4-line ri-spin"></i> 計算中...';
    btn.disabled = true;

    const form = document.getElementById('sectionForm');
    const apiUrl = form.getAttribute('data-api-url');
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');

    fetch(apiUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfInput ? csrfInput.value : ''
        },
        body: JSON.stringify(dataPayload)
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                cachedData = data.data;
                renderResults();
            } else {
                alert('計算錯誤: ' + data.error);
            }
        })
        .catch(err => {
            console.error(err);
            alert('連線失敗');
        })
        .finally(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
        });
}

function renderResults() {
    if (!cachedData) return;
    const unit = document.querySelector('input[name="resultUnit"]:checked').value;
    const isCm = unit === 'cm';
    const f_len = isCm ? 10 : 1;
    const f_area = isCm ? 100 : 1;
    const f_mod = isCm ? 1000 : 1;
    const f_in = isCm ? 10000 : 1;
    const f_warp = isCm ? 1000000 : 1;

    const setVal = (id, val, div) => {
        const el = document.getElementById(id);
        if (el) el.innerText = (val / div).toLocaleString('en-US', {maximumFractionDigits: 2});
    };

    setVal('res-area', cachedData.area, f_area);
    setVal('res-cx', cachedData.cx, f_len);
    setVal('res-cy', cachedData.cy, f_len);
    setVal('res-pcx', cachedData.pcx, f_len);
    setVal('res-pcy', cachedData.pcy, f_len);
    setVal('res-ixx', cachedData.ixx, f_in);
    setVal('res-iyy', cachedData.iyy, f_in);
    setVal('res-ixy', cachedData.ixy, f_in);
    setVal('res-rx', cachedData.rx, f_len);
    setVal('res-ry', cachedData.ry, f_len);
    setVal('res-sx-top', cachedData.sx_top, f_mod);
    setVal('res-sx-bot', cachedData.sx_bot, f_mod);
    setVal('res-sy-right', cachedData.sy_right, f_mod);
    setVal('res-sy-left', cachedData.sy_left, f_mod);
    setVal('res-zx', cachedData.zx, f_mod);
    setVal('res-zy', cachedData.zy, f_mod);
    setVal('res-j', cachedData.j, f_in);
    setVal('res-cw', cachedData.cw, f_warp);

    const txt = isCm ? 'cm' : 'mm';
    document.querySelectorAll('.unit-area').forEach(e => e.innerText = `${txt}²`);
    document.querySelectorAll('.unit-len').forEach(e => e.innerText = `${txt}`);
    document.querySelectorAll('.unit-inertia').forEach(e => e.innerText = `${txt}⁴`);
    document.querySelectorAll('.unit-modulus').forEach(e => e.innerText = `${txt}³`);
    document.querySelectorAll('.unit-warp').forEach(e => e.innerText = `${txt}⁶`);
}