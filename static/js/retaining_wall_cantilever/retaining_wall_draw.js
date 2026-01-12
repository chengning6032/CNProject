document.addEventListener('DOMContentLoaded', function () {
    const canvas = document.getElementById('wallCanvas');
    // 如果找不到 canvas，嘗試等待一下或直接返回 (避免報錯)
    if (!canvas) {
        // console.warn("Canvas #wallCanvas not found.");
        return;
    }

    const ctx = canvas.getContext('2d');
    const inputs = document.querySelectorAll('input, select');

    function drawWall() {
        // 安全讀取數值函式
        const getVal = (id) => {
            const el = document.getElementById(id);
            return el ? (parseFloat(el.value) || 0) : 0;
        };

        // 針對 name 屬性的讀取
        const getNameVal = (name, defaultVal=0) => {
            const el = document.querySelector(`input[name="${name}"]`);
            if (!el) return defaultVal;
            if (el.value === "" || isNaN(parseFloat(el.value))) return defaultVal;
            return parseFloat(el.value);
        };

        // 1. 讀取數值
        const d = {
            H_stem: getVal('H_stem') || 300,
            t_top: getVal('t_stem_top') || 30,
            w_front: getVal('w_stem_front') || 0,
            w_back: getVal('w_stem_back') || 20,
            H_bp: getVal('H_bp') || 50,
            L_front: getVal('L_bp_front') || 100,
            L_back: getVal('L_bp_back') || 200,
            H_sk: getVal('H_sk') || 0,
            L_sk: getVal('L_sk') || 0,
            x_1: getVal('x_1') || 0,

            H_fill: getNameVal('H_fill', null),
            H_water: getNameVal('H_water', 0),
            alpha: getNameVal('alpha_soil', 0),
            H_soil_front: getNameVal('H_soil_front', 50)
        };

        if (d.H_fill === null) d.H_fill = d.H_stem;

        const t_bot = d.w_front + d.t_top + d.w_back;
        const B_total = d.L_front + t_bot + d.L_back;

        // 2. 設定 Canvas 解析度
        const container = canvas.parentElement;
        const rect = container.getBoundingClientRect();

        // 只有當容器可見時才調整大小與繪圖
        if (rect.width > 0) {
            canvas.width = rect.width;
            canvas.height = rect.height || 500;
        }

        // 清空畫面
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // 3. 計算縮放
        let extraHeight = 0;
        if (d.alpha > 0) {
            let visibleSoilWidth = B_total * 0.8;
            extraHeight = visibleSoilWidth * Math.tan(d.alpha * Math.PI / 180);
        }

        const totalWidth = B_total * 1.8;
        const H_soil_total = d.H_bp + d.H_fill + extraHeight;
        const H_struct_total = d.H_bp + d.H_stem;
        const totalHeight = Math.max(H_soil_total, H_struct_total) + d.H_sk + 50;

        const availW = canvas.width;
        const availH = canvas.height;

        const scale = Math.min(availW / totalWidth, availH / totalHeight) * 0.8;
        const drawW = totalWidth * scale;
        const drawH = totalHeight * scale;

        const offsetX = (availW - drawW) / 2 + 80;
        const maxY = Math.max(d.H_bp + d.H_fill + extraHeight, d.H_bp + d.H_stem);
        const offsetY = (availH - drawH) / 2 + maxY * scale + 30;

        function toCanvas(x, y) {
            return { x: offsetX + x * scale, y: offsetY - y * scale };
        }

        // --- [修正] 定義顏色變數 (解決 Uncaught ReferenceError) ---
        const dimColor = "#0056b3";
        const wallColor = "#333333";
        const wallFill = "#d3d3d3";

        // --- 繪圖輔助函式 ---
        function createLine(p1, p2, color, w=2, dash=[]) {
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = color;
            ctx.lineWidth = w;
            ctx.setLineDash(dash);
            ctx.stroke();
            ctx.setLineDash([]);
        }

        function createPolygon(points, fill, stroke) {
            ctx.beginPath();
            ctx.moveTo(points[0].x, points[0].y);
            for (let i = 1; i < points.length; i++) {
                ctx.lineTo(points[i].x, points[i].y);
            }
            ctx.closePath();
            ctx.fillStyle = fill;
            ctx.fill();
            ctx.strokeStyle = stroke;
            ctx.lineWidth = 2;
            ctx.stroke();
        }

        function createText(p, txt, color) {
            ctx.fillStyle = color;
            ctx.font = "14px Arial";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(txt, p.x, p.y);
        }

        function drawDim(p1_cm, p2_cm, txt, off, orient) {
            const c1 = toCanvas(p1_cm.x, p1_cm.y);
            const c2 = toCanvas(p2_cm.x, p2_cm.y);
            const gap = 5;

            ctx.beginPath();
            ctx.strokeStyle = dimColor;
            ctx.lineWidth = 1;

            if (orient === 'H') {
                const yl = c1.y - off;
                ctx.moveTo(c1.x, c1.y - (off > 0 ? gap : -gap)); ctx.lineTo(c1.x, yl);
                ctx.moveTo(c2.x, c2.y - (off > 0 ? gap : -gap)); ctx.lineTo(c2.x, yl);
                ctx.moveTo(c1.x, yl); ctx.lineTo(c2.x, yl);
                ctx.stroke();
                createText({x: (c1.x+c2.x)/2, y: yl - (off>0?10:-10)}, txt, dimColor);
            } else {
                const xl = c1.x - off;
                ctx.moveTo(c1.x - (off > 0 ? gap : -gap), c1.y); ctx.lineTo(xl, c1.y);
                ctx.moveTo(c2.x - (off > 0 ? gap : -gap), c2.y); ctx.lineTo(xl, c2.y);
                ctx.moveTo(xl, c1.y); ctx.lineTo(xl, c2.y);
                ctx.stroke();

                ctx.save();
                ctx.translate(xl - (off>0?10:-10), (c1.y+c2.y)/2);
                ctx.rotate(-Math.PI/2);
                ctx.fillText(txt, 0, 0);
                ctx.restore();
            }
        }

        // --- 繪製實體 ---

        // 1. 結構體
        let wallPts = [
            toCanvas(0, 0), toCanvas(0, d.H_bp),
            toCanvas(d.L_front, d.H_bp),
            toCanvas(d.L_front + d.w_front, d.H_bp + d.H_stem),
            toCanvas(d.L_front + d.w_front + d.t_top, d.H_bp + d.H_stem),
            toCanvas(B_total - d.L_back, d.H_bp),
            toCanvas(B_total, d.H_bp)
        ];

        if (d.H_sk > 0) {
            const x_sk_r = B_total - d.x_1;
            const x_sk_l = x_sk_r - d.L_sk;
            wallPts.push(toCanvas(B_total, 0));
            wallPts.push(toCanvas(x_sk_r, 0));
            wallPts.push(toCanvas(x_sk_r, -d.H_sk));
            wallPts.push(toCanvas(x_sk_l, -d.H_sk));
            wallPts.push(toCanvas(x_sk_l, 0));
        } else {
            wallPts.push(toCanvas(B_total, 0));
        }
        createPolygon(wallPts, wallFill, wallColor); // 這裡之前報錯

        // 2. 牆後土 (Green)
        let x_s_s = (d.H_fill <= d.H_stem) ? (B_total - d.L_back) - (d.H_fill * (d.w_back/d.H_stem || 0)) : (d.L_front + d.w_front + d.t_top);
        let y_s_s = d.H_bp + d.H_fill;
        let x_s_e = totalWidth;
        let y_s_e = y_s_s + (x_s_e - x_s_s) * Math.tan(d.alpha * Math.PI / 180);

        createLine(toCanvas(x_s_s, y_s_s), toCanvas(x_s_e, y_s_e), "#4CAF50", 2, [5, 5]);
        createText(toCanvas(x_s_e - 40, y_s_e + 15), `H_fill=${d.H_fill.toFixed(0)}`, "#4CAF50");

        // 3. 牆前土 (Brown)
        let y_f = d.H_bp + d.H_soil_front;
        createLine(toCanvas(d.L_front, y_f), toCanvas(-50, y_f), "#D2691E", 2, [5, 5]);
        createText(toCanvas(-30, y_f - 10), `Front`, "#D2691E");

        // 4. 水位 (Blue)
        if (d.H_water > 0) {
            let p_w_s = {x: B_total - d.L_back, y: d.H_water};
            let p_w_e = {x: totalWidth, y: d.H_water};
            createLine(toCanvas(p_w_s.x, p_w_s.y), toCanvas(p_w_e.x, p_w_e.y), "#2196F3", 2, [10, 5]);
            createText(toCanvas(p_w_e.x - 50, p_w_e.y - 10), `GWL=${d.H_water.toFixed(0)}`, "#2196F3");
        }

        // 5. 標註
        drawDim({x: d.L_front, y: d.H_bp}, {x: d.L_front, y: d.H_bp + d.H_stem}, `H=${d.H_stem}`, 40, 'V');
        drawDim({x: 0, y: 0}, {x: B_total, y: 0}, `B=${B_total}`, -45, 'H');

        if (d.H_sk > 0) {
            const x_sk_r = B_total - d.x_1;
            const x_sk_l = x_sk_r - d.L_sk;
            drawDim({x: x_sk_l, y: -d.H_sk}, {x: x_sk_r, y: -d.H_sk}, `sk=${d.L_sk}`, -15, 'H');
            drawDim({x: B_total, y: -d.H_sk}, {x: B_total, y: 0}, `hk=${d.H_sk}`, -30, 'V');
        }
    }

    // 綁定事件
    inputs.forEach(input => {
        input.addEventListener('input', drawWall);
        input.addEventListener('change', drawWall);
    });

    // 視窗改變大小時重繪
    window.addEventListener('resize', drawWall);

    // 初始執行 (延遲確保 CSS 載入)
    setTimeout(drawWall, 100);
});