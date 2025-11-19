import math
import base64


class SvgPlotter:
    def __init__(self, width=600, height=600, margin_percent=0.05):  # [修改6] 減少預設 margin
        self.width = width
        self.height = height
        self.elements = []
        self.legend_items = []
        self.colorbar = None  # [修改5] 新增 ColorBar 屬性
        self.defs = []

        # 自動邊界
        self.min_x = float('inf')
        self.max_x = float('-inf')
        self.min_y = float('inf')
        self.max_y = float('-inf')
        self.margin_percent = margin_percent

        # 定義箭頭標記
        self.add_def("""
            <marker id="arrowhead_red" markerWidth="10" markerHeight="7" 
            refX="9" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="red" />
            </marker>
            <marker id="arrowhead_blue" markerWidth="10" markerHeight="7" 
            refX="9" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="blue" />
            </marker>
            <marker id="arrowhead_black" markerWidth="10" markerHeight="7" 
            refX="9" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="black" />
            </marker>
        """)

    def update_bounds(self, x, y, r=0):
        self.min_x = min(self.min_x, x - r)
        self.max_x = max(self.max_x, x + r)
        self.min_y = min(self.min_y, y - r)
        self.max_y = max(self.max_y, y + r)

    def add_def(self, xml_str):
        self.defs.append(xml_str)

    # ... (保留 add_rect, add_circle, add_polygon, add_line, add_arrow, add_text, add_shapely_polygon, get_color_for_value 方法不變) ...
    # 為節省篇幅，這裡僅列出變更的部分，請保留原有的幾何繪圖方法

    def add_rect(self, x_center, y_center, width, height, fill="none", stroke="black", stroke_width=1, opacity=1.0,
                 stroke_dasharray=""):
        self.update_bounds(x_center - width / 2, y_center - height / 2)
        self.update_bounds(x_center + width / 2, y_center + height / 2)
        style = f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" fill-opacity="{opacity}"'
        if stroke_dasharray: style += f' stroke-dasharray="{stroke_dasharray}"'
        self.elements.append({'type': 'rect', 'cx': x_center, 'cy': y_center, 'w': width, 'h': height, 'style': style})

    def add_circle(self, x, y, r, fill="none", stroke="black", stroke_width=1, opacity=1.0, stroke_dasharray=""):
        self.update_bounds(x, y, r)
        style = f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" fill-opacity="{opacity}"'
        if stroke_dasharray: style += f' stroke-dasharray="{stroke_dasharray}"'
        self.elements.append({'type': 'circle', 'cx': x, 'cy': y, 'r': r, 'style': style})

    def add_polygon(self, points, fill="none", stroke="black", stroke_width=1, opacity=1.0, stroke_dasharray=""):
        if not points: return
        for px, py in points: self.update_bounds(px, py)
        style = f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" fill-opacity="{opacity}"'
        if stroke_dasharray: style += f' stroke-dasharray="{stroke_dasharray}"'
        self.elements.append({'type': 'polygon', 'points': points, 'style': style})

    def add_line(self, x1, y1, x2, y2, color="black", width=1, stroke_dasharray=""):
        self.update_bounds(x1, y1)
        self.update_bounds(x2, y2)
        style = f'stroke="{color}" stroke-width="{width}"'
        if stroke_dasharray: style += f' stroke-dasharray="{stroke_dasharray}"'
        self.elements.append({'type': 'line', 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'style': style})

    def add_arrow(self, x1, y1, x2, y2, color="red", width=2):
        self.update_bounds(x1, y1)
        self.update_bounds(x2, y2)
        marker = "url(#arrowhead_black)"
        if color == "red":
            marker = "url(#arrowhead_red)"
        elif color == "blue":
            marker = "url(#arrowhead_blue)"
        style = f'stroke="{color}" stroke-width="{width}" marker-end="{marker}"'
        self.elements.append({'type': 'line', 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'style': style})

    def add_text(self, x, y, text, color="black", size=12, anchor="middle", weight="normal", bg=None, rotation=0):
        self.update_bounds(x, y)
        self.elements.append({
            'type': 'text', 'x': x, 'y': y, 'text': text,
            'color': color, 'size': size, 'anchor': anchor,
            'weight': weight, 'bg': bg, 'rotation': rotation
        })

    def add_shapely_polygon(self, poly, fill="none", stroke="black", stroke_width=1, opacity=0.4, stroke_dasharray=""):
        if poly.is_empty: return
        if poly.geom_type == 'Polygon':
            exterior_coords = list(poly.exterior.coords)
            self.add_polygon(exterior_coords, fill, stroke, stroke_width, opacity, stroke_dasharray)
        elif poly.geom_type == 'MultiPolygon':
            for geom in poly.geoms:
                exterior_coords = list(geom.exterior.coords)
                self.add_polygon(exterior_coords, fill, stroke, stroke_width, opacity, stroke_dasharray)

    def get_color_for_value(self, value, max_value, min_value=0, base_color=(0, 123, 255)):
        if max_value == min_value: return "rgb(255, 255, 255)"
        ratio = (value - min_value) / (max_value - min_value)
        ratio = max(0.0, min(1.0, ratio))
        r = int(255 + (base_color[0] - 255) * ratio)
        g = int(255 + (base_color[1] - 255) * ratio)
        b = int(255 + (base_color[2] - 255) * ratio)
        return f"rgb({r}, {g}, {b})"

    # [修改5] 新增 ColorBar 方法
    def add_colorbar(self, min_val, max_val, unit_label, base_color=(0, 123, 255)):
        self.colorbar = {
            'min': min_val,
            'max': max_val,
            'unit': unit_label,
            'base_color': base_color
        }

    # [修改3] & [修改4] 增強圖例
    def add_legend_item(self, label, type, fill="none", stroke="black", stroke_width=1, stroke_dasharray=""):
        """
        type: 'rect' | 'circle' | 'line'
        """
        self.legend_items.append({
            'label': label,
            'type': type,
            'fill': fill,
            'stroke': stroke,
            'stroke_width': stroke_width,
            'stroke_dasharray': stroke_dasharray
        })

        # bpN_svg_utils.py 中的 render_to_base64 方法

    def render_to_base64(self):
        if self.min_x == float('inf'):
            return ""

        data_w = self.max_x - self.min_x
        data_h = self.max_y - self.min_y

        if data_w == 0: data_w = 10
        if data_h == 0: data_h = 10

        margin_x = data_w * self.margin_percent
        margin_y = data_h * self.margin_percent

        view_center_x = (self.min_x + self.max_x) / 2
        view_center_y = (self.min_y + self.max_y) / 2

        # [核心修正] 移除 max(...)，不再強制讓視野變成正方形
        # 這讓長方形的基礎版可以佔滿畫面，而不是被縮小
        final_data_w = data_w + 2 * margin_x
        final_data_h = data_h + 2 * margin_y

        # SVG ViewBox 左上角 (數學座標系中心點偏移)
        view_left = view_center_x - final_data_w / 2
        view_top = view_center_y + final_data_h / 2

        # 佈局計算
        legend_height = 60 if self.legend_items else 0
        colorbar_width = 80 if self.colorbar else 0

        # 主圖繪製區域寬度
        available_width = self.width - colorbar_width
        available_height = self.height - legend_height

        # 計算縮放比例 (Scale)，取最小比例以確保內容全部塞得進去
        scale = min(available_width / final_data_w, available_height / final_data_h)

        # 讓主圖在 available_width 中置中
        plot_offset_x = (available_width - (final_data_w * scale)) / 2
        # 讓主圖在 available_height 中置中 (垂直置中)
        plot_offset_y = (available_height - (final_data_h * scale)) / 2

        def tx(x):
            return plot_offset_x + (x - view_left) * scale

        def ty(y):
            return plot_offset_y + (view_top - y) * scale

        def ts(s):
            return s * scale

        svg_parts = []
        svg_parts.append(
            f'<svg width="100%" height="100%" viewBox="0 0 {self.width} {self.height}" xmlns="http://www.w3.org/2000/svg">')
        svg_parts.append('<defs>' + "".join(self.defs))

        if self.colorbar:
            bc = self.colorbar['base_color']
            svg_parts.append(f'''
                <linearGradient id="stressGradient" x1="0%" y1="100%" x2="0%" y2="0%">
                    <stop offset="0%" style="stop-color:rgb(255,255,255);stop-opacity:1" />
                    <stop offset="100%" style="stop-color:rgb({bc[0]},{bc[1]},{bc[2]});stop-opacity:1" />
                </linearGradient>
            ''')
        svg_parts.append('</defs>')

        # 白色背景
        svg_parts.append(f'<rect width="100%" height="100%" fill="white" />')

        # 繪製主元素
        for el in self.elements:
            if el['type'] == 'rect':
                rx = tx(el['cx'] - el['w'] / 2)
                ry = ty(el['cy'] + el['h'] / 2)
                rw = ts(el['w'])
                rh = ts(el['h'])
                svg_parts.append(f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" {el["style"]} />')
            elif el['type'] == 'circle':
                cx = tx(el['cx'])
                cy = ty(el['cy'])
                r = ts(el['r'])
                svg_parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" {el["style"]} />')
            elif el['type'] == 'polygon':
                points_str = " ".join([f"{tx(p[0])},{ty(p[1])}" for p in el['points']])
                svg_parts.append(f'<polygon points="{points_str}" {el["style"]} />')
            elif el['type'] == 'line':
                svg_parts.append(
                    f'<line x1="{tx(el["x1"])}" y1="{ty(el["y1"])}" x2="{tx(el["x2"])}" y2="{ty(el["y2"])}" {el["style"]} />')
            elif el['type'] == 'text':
                sx = tx(el['x'])
                sy = ty(el['y'])
                transform = f' transform="rotate({-el["rotation"]}, {sx}, {sy})"' if el['rotation'] else ""
                if el['bg']:
                    svg_parts.append(
                        f'<rect x="{sx - 2}" y="{sy - el["size"] * 0.6}" width="{len(str(el["text"])) * el["size"] * 0.6 + 4}" height="{el["size"] * 1.2}" fill="{el["bg"]}" fill-opacity="0.8" rx="2" {transform} />')
                svg_parts.append(
                    f'<text x="{sx}" y="{sy}" fill="{el["color"]}" font-family="Arial, sans-serif" font-size="{el["size"]}" text-anchor="{el["anchor"]}" font-weight="{el["weight"]}" dominant-baseline="middle" {transform}>{el["text"]}</text>')

        # 繪製 ColorBar
        if self.colorbar:
            bar_x = self.width - 60
            bar_y = 40
            bar_w = 15
            bar_h = available_height - 80
            svg_parts.append(
                f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" fill="url(#stressGradient)" stroke="#ccc" stroke-width="1" />')
            steps = 5
            for i in range(steps + 1):
                val = self.colorbar['min'] + (self.colorbar['max'] - self.colorbar['min']) * (i / steps)
                y_pos = bar_y + bar_h - (bar_h * (i / steps))
                svg_parts.append(
                    f'<line x1="{bar_x + bar_w}" y1="{y_pos}" x2="{bar_x + bar_w + 5}" y2="{y_pos}" stroke="black" stroke-width="1" />')
                svg_parts.append(
                    f'<text x="{bar_x + bar_w + 8}" y="{y_pos}" fill="#333" font-family="Arial" font-size="11" dominant-baseline="middle">{val:.1f}</text>')
            svg_parts.append(
                f'<text transform="translate({bar_x - 10}, {bar_y + bar_h / 2}) rotate(-90)" fill="#666" font-family="Arial" font-size="12" text-anchor="middle">{self.colorbar["unit"]}</text>')

        # 繪製圖例
        if self.legend_items:
            item_count = len(self.legend_items)
            item_width = available_width / item_count
            legend_y_start = self.height - legend_height + 25

            for i, item in enumerate(self.legend_items):
                cx = i * item_width + item_width / 2 + (plot_offset_x if self.colorbar else 0)
                icon_size = 24
                icon_x = cx - 45
                text_x = cx - 10
                style = f'fill="{item["fill"]}" stroke="{item["stroke"]}" stroke-width="{item["stroke_width"]}"'
                if item.get('stroke_dasharray'): style += f' stroke-dasharray="{item["stroke_dasharray"]}"'

                if item['type'] == 'rect':
                    svg_parts.append(
                        f'<rect x="{icon_x}" y="{legend_y_start - icon_size / 2}" width="{icon_size}" height="{icon_size}" {style} />')
                elif item['type'] == 'circle':
                    svg_parts.append(
                        f'<circle cx="{icon_x + icon_size / 2}" cy="{legend_y_start}" r="{icon_size / 2}" {style} />')
                elif item['type'] == 'line':
                    svg_parts.append(
                        f'<line x1="{icon_x}" y1="{legend_y_start}" x2="{icon_x + icon_size}" y2="{legend_y_start}" {style} />')

                svg_parts.append(
                    f'<text x="{text_x}" y="{legend_y_start + 5}" fill="#333" font-family="Arial, sans-serif" font-size="16" font-weight="bold" text-anchor="start">{item["label"]}</text>')

        svg_parts.append('</svg>')
        return base64.b64encode("".join(svg_parts).encode('utf-8')).decode('utf-8')