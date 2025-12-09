document.addEventListener('DOMContentLoaded', function () {
    const container = document.getElementById('svg-container');
    if (!container) return;

    // 監聽所有輸入框
    const inputs = document.querySelectorAll('input, select');
    const svgNS = "http://www.w3.org/2000/svg";

    function drawWall() {
        // 1. 讀取 DOM 數值 (Client-Side)
        const d = {
            H_stem: parseFloat(document.getElementById('H_stem')?.value) || 300,
            t_top: parseFloat(document.getElementById('t_stem_top')?.value) || 30,
            w_front: parseFloat(document.getElementById('w_stem_front')?.value) || 0,
            w_back: parseFloat(document.getElementById('w_stem_back')?.value) || 20,
            H_bp: parseFloat(document.getElementById('H_bp')?.value) || 50,
            L_front: parseFloat(document.getElementById('L_bp_front')?.value) || 100,
            L_back: parseFloat(document.getElementById('L_bp_back')?.value) || 200,
            H_sk: parseFloat(document.getElementById('H_sk')?.value) || 0,
            L_sk: parseFloat(document.getElementById('L_sk')?.value) || 0,
            x_1: parseFloat(document.getElementById('x_1')?.value) || 0,

            // name屬性選取
            H_fill: (document.querySelector('input[name="H_fill"]')?.value) ? parseFloat(document.querySelector('input[name="H_fill"]').value) : null,
            H_water: parseFloat(document.querySelector('input[name="H_water"]')?.value) || 0,
            alpha: parseFloat(document.querySelector('input[name="alpha_soil"]')?.value) || 0,
            H_soil_front: parseFloat(document.querySelector('input[name="H_soil_front"]')?.value) || 50
        };

        // 預設值處理
        if (d.H_fill === null) d.H_fill = d.H_stem;

        const t_bot = d.w_front + d.t_top + d.w_back;
        const B_total = d.L_front + t_bot + d.L_back;

        // 清空容器
        container.innerHTML = '';
        const svg = document.createElementNS(svgNS, "svg");
        svg.setAttribute("width", "100%");
        svg.setAttribute("height", "100%");

        // 3. 計算縮放
        let extraHeight = 0;
        if (d.alpha > 0) {
            let visibleSoilWidth = B_total * 0.8;
            extraHeight = visibleSoilWidth * Math.tan(d.alpha * Math.PI / 180);
        }

        const totalWidth = B_total * 1.6;
        const H_soil_total = d.H_bp + d.H_fill + extraHeight;
        const H_struct_total = d.H_bp + d.H_stem;
        const totalHeight = Math.max(H_soil_total, H_struct_total) + d.H_sk + 50;

        const availW = container.clientWidth || 500;
        const availH = container.clientHeight || 500;

        const scale = Math.min(availW / totalWidth, availH / totalHeight) * 0.8;
        const drawW = totalWidth * scale;
        const drawH = totalHeight * scale;
        const offsetX = (availW - drawW) / 2 + 50;
        const maxY = Math.max(d.H_bp + d.H_fill + extraHeight, d.H_bp + d.H_stem);
        const offsetY = (availH - drawH) / 2 + maxY * scale + 20;

        function toSVG(x, y) {
            return {x: offsetX + x * scale, y: offsetY - y * scale};
        }

        // 輔助函式
        function createPolygon(points, fill, stroke) {
            const pathData = "M " + points.map(p => `${p.x},${p.y}`).join(" L ") + " Z";
            const path = document.createElementNS(svgNS, "path");
            path.setAttribute("d", pathData);
            path.setAttribute("fill", fill);
            path.setAttribute("stroke", stroke);
            path.setAttribute("stroke-width", "2");
            svg.appendChild(path);
        }

        function createLine(p1, p2, color, width = 2, dash = null) {
            const line = document.createElementNS(svgNS, "line");
            line.setAttribute("x1", p1.x);
            line.setAttribute("y1", p1.y);
            line.setAttribute("x2", p2.x);
            line.setAttribute("y2", p2.y);
            line.setAttribute("stroke", color);
            line.setAttribute("stroke-width", width);
            if (dash) line.setAttribute("stroke-dasharray", dash);
            svg.appendChild(line);
        }

        function createText(x, y, content, color) {
            const text = document.createElementNS(svgNS, "text");
            text.setAttribute("x", x);
            text.setAttribute("y", y);
            text.setAttribute("fill", color);
            text.setAttribute("text-anchor", "middle");
            text.setAttribute("font-size", "12");
            text.textContent = content;
            svg.appendChild(text);
        }

        function drawDim(p1_cm, p2_cm, label, offset, orientation) {
            const c1 = toSVG(p1_cm.x, p1_cm.y);
            const c2 = toSVG(p2_cm.x, p2_cm.y);
            const color = "#0056b3";
            const gap = 5;

            if (orientation === 'H') {
                const y_line = c1.y - offset;
                createLine({x: c1.x, y: c1.y - (offset > 0 ? gap : -gap)}, {x: c1.x, y: y_line}, color, 1);
                createLine({x: c2.x, y: c2.y - (offset > 0 ? gap : -gap)}, {x: c2.x, y: y_line}, color, 1);
                createLine({x: c1.x, y: y_line}, {x: c2.x, y: y_line}, color, 1);
                createText((c1.x + c2.x) / 2, y_line - (offset > 0 ? 5 : -15), label, color);
            } else {
                const x_line = c1.x - offset;
                createLine({x: c1.x - (offset > 0 ? gap : -gap), y: c1.y}, {x: x_line, y: c1.y}, color, 1);
                createLine({x: c2.x - (offset > 0 ? gap : -gap), y: c2.y}, {x: x_line, y: c2.y}, color, 1);
                createLine({x: x_line, y: c1.y}, {x: x_line, y: c2.y}, color, 1);

                const t = document.createElementNS(svgNS, "text");
                t.setAttribute("x", x_line - (offset > 0 ? 5 : -15));
                t.setAttribute("y", (c1.y + c2.y) / 2);
                t.setAttribute("fill", color);
                t.setAttribute("text-anchor", "middle");
                t.setAttribute("font-size", "12");
                t.setAttribute("transform", `rotate(-90, ${x_line - (offset > 0 ? 5 : -15)}, ${(c1.y + c2.y) / 2})`);
                t.textContent = label;
                svg.appendChild(t);
            }
        }

        // --- 繪圖開始 ---

        // 1. 結構體
        const pt_toe_bot = toSVG(0, 0);
        const pt_toe_top = toSVG(0, d.H_bp);
        const pt_stem_front_base = toSVG(d.L_front, d.H_bp);
        const pt_stem_front_top = toSVG(d.L_front + d.w_front, d.H_bp + d.H_stem);
        const pt_stem_back_top = toSVG(d.L_front + d.w_front + d.t_top, d.H_bp + d.H_stem);
        const pt_stem_back_base = toSVG(B_total - d.L_back, d.H_bp);
        const pt_heel_top = toSVG(B_total, d.H_bp);

        let wallPoints = [
            pt_toe_bot, pt_toe_top, pt_stem_front_base, pt_stem_front_top,
            pt_stem_back_top, pt_stem_back_base, pt_heel_top
        ];

        if (d.H_sk > 0 && d.L_sk > 0) {
            const x_sk_r = B_total - d.x_1;
            const x_sk_l = x_sk_r - d.L_sk;
            wallPoints.push(toSVG(B_total, 0));
            wallPoints.push(toSVG(x_sk_r, 0));
            wallPoints.push(toSVG(x_sk_r, -d.H_sk));
            wallPoints.push(toSVG(x_sk_l, -d.H_sk));
            wallPoints.push(toSVG(x_sk_l, 0));
        } else {
            wallPoints.push(toSVG(B_total, 0));
        }
        createPolygon(wallPoints, "#d3d3d3", "#333");

        // 2. 牆後回填土 (Green)
        let x_soil_start = B_total - d.L_back;
        let soilY = d.H_bp + d.H_fill;
        let p_soil_start_cm_x = x_soil_start;

        if (d.H_fill <= d.H_stem) {
            let slope = d.w_back / d.H_stem;
            p_soil_start_cm_x = (B_total - d.L_back) - (d.H_fill * slope);
        } else {
            p_soil_start_cm_x = d.L_front + d.w_front + d.t_top;
        }

        let x_soil_end = totalWidth;
        let y_soil_end = soilY + (x_soil_end - p_soil_start_cm_x) * Math.tan(d.alpha * Math.PI / 180);
        createLine(toSVG(p_soil_start_cm_x, soilY), toSVG(x_soil_end, y_soil_end), "#4CAF50", 2, "5,5");
        createText(toSVG(x_soil_end, y_soil_end).x - 40, toSVG(x_soil_end, y_soil_end).y - 10, "Backfill", "#4CAF50");

        // 3. 牆前被動土 (Brown)
        let soilFrontY = d.H_bp + d.H_soil_front;
        createLine(toSVG(d.L_front, soilFrontY), toSVG(-50, soilFrontY), "#D2691E", 2, "5,5");
        createText(toSVG(-50, soilFrontY).x + 20, toSVG(-50, soilFrontY).y - 5, "Front", "#D2691E");

        // 4. 地下水位 (Blue)
        if (d.H_water > 0) {
            let p_water_start = {x: x_soil_start, y: d.H_water};
            let p_water_end = {x: totalWidth, y: d.H_water};
            createLine(toSVG(p_water_start.x, p_water_start.y), toSVG(p_water_end.x, p_water_end.y), "#2196F3", 2, "10,5");

            let tri_cx = (toSVG(p_water_start.x, 0).x + toSVG(p_water_end.x, 0).x) / 2;
            let tri_y = toSVG(0, d.H_water).y;
            const pathData = `M ${tri_cx} ${tri_y} L ${tri_cx - 6} ${tri_y - 10} L ${tri_cx + 6} ${tri_y - 10} Z`;
            const tri = document.createElementNS(svgNS, "path");
            tri.setAttribute("d", pathData);
            tri.setAttribute("fill", "#2196F3");
            svg.appendChild(tri);

            createText(toSVG(p_water_end.x, d.H_water).x - 50, toSVG(0, d.H_water).y - 10, "GWL", "#2196F3");
        }

        // 5. 尺寸標註
        drawDim({x: d.L_front, y: d.H_bp}, {x: d.L_front, y: d.H_bp + d.H_stem}, `H=${d.H_stem}`, 40, 'V');
        drawDim({x: 0, y: 0}, {x: 0, y: d.H_bp}, `t=${d.H_bp}`, 40, 'V');

        let dimY = d.H_bp;
        drawDim({x: 0, y: dimY}, {x: d.L_front, y: dimY}, `Lf=${d.L_front}`, 20, 'H');
        drawDim({x: B_total - d.L_back, y: dimY}, {x: B_total, y: dimY}, `Lb=${d.L_back}`, 20, 'H');

        if (d.H_sk > 0) {
            let x_r = B_total - d.x_1;
            let x_l = x_r - d.L_sk;
            drawDim({x: x_l, y: -d.H_sk}, {x: x_r, y: -d.H_sk}, `sk=${d.L_sk}`, -15, 'H');
            drawDim({x: B_total, y: -d.H_sk}, {x: B_total, y: 0}, `hk=${d.H_sk}`, -30, 'V');
        }

        let lowestY = (d.H_sk > 0) ? -d.H_sk : 0;
        drawDim({x: 0, y: lowestY}, {x: B_total, y: lowestY}, `B=${B_total}`, -45, 'H');

        container.appendChild(svg);
    }

    // Attach listeners
    inputs.forEach(input => input.addEventListener('input', drawWall));
    // Initial draw
    drawWall();
});