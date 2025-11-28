from django.shortcuts import render
from django.http import JsonResponse
import json
import math
import numpy as np
import inspect
import sectionproperties.pre.library.steel_sections as steel_sections
from sectionproperties.analysis.section import Section
# 引入幾何建立所需的模組
from shapely.geometry import Polygon
from sectionproperties.pre.geometry import Geometry


def index(request):
    return render(request, 'section_properties/index.html')


def calculate_h_section(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            stype = data.get('type', 'H')

            # 1. 建立幾何
            geometry = create_geometry(stype, data)
            if geometry is None:
                return JsonResponse({'error': f'幾何建立失敗，請檢查尺寸是否合理'}, status=400)

            # 2. 建立網格
            min_dim = get_min_dimension(stype, data)
            # 網格設定
            mesh_size = max((min_dim ** 2) / 10.0, 0.5)
            mesh_size = min(mesh_size, 20.0)

            try:
                geometry.create_mesh(mesh_sizes=[mesh_size])
            except Exception as e:
                print(f"[ERROR] Meshing failed: {e}")
                return JsonResponse({'error': '網格劃分失敗，請檢查尺寸是否合理'}, status=400)

            # 3. 建立 Section 物件
            sec = Section(geometry)

            # 4. 執行計算
            sec.calculate_geometric_properties()
            sec.calculate_warping_properties()

            # 手動計算塑性性質
            zx, zy, pcx, pcy = calculate_plastic_manual(sec)

            # 5. 提取結果
            area = sec.get_area()
            ixx, iyy, ixy = sec.get_ic()
            rx, ry = sec.get_rc()
            cw = sec.get_gamma()
            j_val = sec.get_j()

            # 彈性形心
            cx, cy = sec.get_c()

            # 手動計算 S
            nodes = get_mesh_nodes(sec)
            x_coords = nodes[:, 0]
            y_coords = nodes[:, 1]
            xmin, xmax = np.min(x_coords), np.max(x_coords)
            ymin, ymax = np.min(y_coords), np.max(y_coords)

            dist_top = abs(ymax - cy)
            dist_bot = abs(cy - ymin)
            dist_right = abs(xmax - cx)
            dist_left = abs(cx - xmin)

            sx_top = ixx / dist_top if dist_top > 1e-6 else 0
            sx_bot = ixx / dist_bot if dist_bot > 1e-6 else 0
            sy_right = iyy / dist_right if dist_right > 1e-6 else 0
            sy_left = iyy / dist_left if dist_left > 1e-6 else 0

            # rts 計算
            rts = 0
            sx_min = min(sx_top, sx_bot)
            if sx_min > 0 and iyy > 0 and cw >= 0:
                try:
                    rts = math.sqrt(math.sqrt(iyy * cw) / sx_min)
                except:
                    rts = 0

            # 6. 回傳
            res = {
                'area': round(area, 2),
                'cx': round(cx, 2), 'cy': round(cy, 2),
                'pcx': round(pcx, 2), 'pcy': round(pcy, 2),
                'ixx': round(ixx, 2), 'iyy': round(iyy, 2), 'ixy': round(ixy, 2),
                'rx': round(rx, 2), 'ry': round(ry, 2),
                'sx_top': round(sx_top, 2), 'sx_bot': round(sx_bot, 2),
                'sy_right': round(sy_right, 2), 'sy_left': round(sy_left, 2),
                'zx': round(zx, 2), 'zy': round(zy, 2),
                'cw': round(cw, 2), 'j': round(j_val, 2), 'rts': round(rts, 2)
            }
            return JsonResponse({'success': True, 'data': res})

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid Method'}, status=405)


# --- [核心] 手動塑性分析函式 ---
def calculate_plastic_manual(sec):
    nodes = None
    elements = None
    if hasattr(sec.mesh, 'nodes'):
        nodes = np.array(sec.mesh.nodes)
    elif isinstance(sec.mesh, dict):
        if 'vertices' in sec.mesh:
            nodes = np.array(sec.mesh['vertices'])
        elif 'nodes' in sec.mesh:
            nodes = np.array(sec.mesh['nodes'])

    if hasattr(sec.mesh, 'elements'):
        elements = np.array(sec.mesh.elements)
    elif isinstance(sec.mesh, dict):
        if 'triangles' in sec.mesh:
            elements = np.array(sec.mesh['triangles'])
        elif 'elements' in sec.mesh:
            elements = np.array(sec.mesh['elements'])

    if nodes is None or elements is None: return 0, 0, 0, 0

    coords = nodes[elements]
    x = coords[:, :, 0]
    y = coords[:, :, 1]
    term1 = x[:, 0] * (y[:, 1] - y[:, 2])
    term2 = x[:, 1] * (y[:, 2] - y[:, 0])
    term3 = x[:, 2] * (y[:, 0] - y[:, 1])
    el_areas = 0.5 * np.abs(term1 + term2 + term3)
    el_cx = np.mean(x, axis=1)
    el_cy = np.mean(y, axis=1)

    total_area = np.sum(el_areas)
    half_area = total_area / 2.0

    # Zx
    sort_idx_y = np.argsort(el_cy)
    sorted_areas_y = el_areas[sort_idx_y]
    sorted_cy = el_cy[sort_idx_y]
    cum_area_y = np.cumsum(sorted_areas_y)
    pna_idx_y = np.searchsorted(cum_area_y, half_area)
    pna_y = sorted_cy[pna_idx_y] if pna_idx_y < len(sorted_cy) else sorted_cy[-1]
    zx = np.sum(el_areas * np.abs(el_cy - pna_y))

    # Zy
    sort_idx_x = np.argsort(el_cx)
    sorted_areas_x = el_areas[sort_idx_x]
    sorted_cx = el_cx[sort_idx_x]
    cum_area_x = np.cumsum(sorted_areas_x)
    pna_idx_x = np.searchsorted(cum_area_x, half_area)
    pna_x = sorted_cx[pna_idx_x] if pna_idx_x < len(sorted_cx) else sorted_cx[-1]
    zy = np.sum(el_areas * np.abs(el_cx - pna_x))

    return zx, zy, pna_x, pna_y


# --- 幾何建立函式 ---

def create_geometry(stype, d):
    try:
        # ==========================================
        # H 型鋼
        # ==========================================
        if stype == 'H':
            h = float(d['h']);
            tw = float(d['tw'])
            bft = float(d.get('bft', d.get('bf', 0)));
            tft = float(d.get('tft', d.get('tf', 0)))
            bfb = float(d.get('bfb', d.get('bf', 0)));
            tfb = float(d.get('tfb', d.get('tf', 0)))
            r_val = float(d.get('r', 0));
            n_r_val = 8 if r_val > 0 else 0

            sig = inspect.signature(steel_sections.mono_i_section)
            params = sig.parameters
            kwargs = {'d': h, 't_w': tw, 'b_t': bft, 'b_b': bfb, 'r': r_val, 'n_r': n_r_val}
            if 't_f_t' in params:
                kwargs['t_f_t'] = tft
            elif 't_t' in params:
                kwargs['t_t'] = tft
            elif 't_ft' in params:
                kwargs['t_ft'] = tft
            if 't_f_b' in params:
                kwargs['t_f_b'] = tfb
            elif 't_b' in params:
                kwargs['t_b'] = tfb
            elif 't_fb' in params:
                kwargs['t_fb'] = tfb
            return steel_sections.mono_i_section(**kwargs)

        # ==========================================
        # Z 型鋼 (修正版 - 修復變數名稱錯誤)
        # ==========================================
        elif stype == 'Z':
            h = float(d['h'])
            t = float(d['t'])
            b_def = float(d.get('b', 0))
            bt = float(d.get('bt', b_def)) if d.get('bt') else b_def
            bb = float(d.get('bb', b_def)) if d.get('bb') else b_def
            c_def = float(d.get('c', 0))
            ct = float(d.get('ct', c_def)) if d.get('ct') else c_def
            cb = float(d.get('cb', c_def)) if d.get('cb') else c_def
            r_in = float(d.get('r', 0))
            r_out = r_in + t
            n_r = 8 if r_in > 0 else 0

            limit_r = min(bt, bb, h / 2.0)
            if r_out > limit_r:
                r_out = limit_r - 0.1
                r_in = max(0, r_out - t)

            points = []
            xl, xr = -t / 2.0, t / 2.0
            yt, yb = h / 2.0, -h / 2.0

            # 1. 上唇尖 (外)
            x_tip_top_out = xl + bt
            y_tip_top_out = yt - ct
            points.append((x_tip_top_out, y_tip_top_out))

            # 2. 上唇外 -> 上翼板外
            if r_out > 0:
                cx, cy = x_tip_top_out - r_out, yt - r_out
                for i in range(n_r + 1):
                    ang = 0.0 + (i / n_r) * (0.5 * np.pi)
                    points.append((cx + r_out * np.cos(ang), cy + r_out * np.sin(ang)))
            else:
                points.append((x_tip_top_out, yt))

            # 3. 上翼板外 -> 腹板左
            if r_out > 0:
                cx, cy = xl + r_out, yt - r_out
                for i in range(n_r + 1):
                    ang = 0.5 * np.pi + (i / n_r) * (0.5 * np.pi)
                    points.append((cx + r_out * np.cos(ang), cy + r_out * np.sin(ang)))
            else:
                points.append((xl, yt))

            # 4. 腹板左 -> 下翼板上(內)
            if r_in > 0:
                cx, cy = xl - r_in, yb + t + r_in
                for i in range(n_r + 1):
                    ang = 0.0 - (i / n_r) * (0.5 * np.pi)
                    points.append((cx + r_in * np.cos(ang), cy + r_in * np.sin(ang)))
            else:
                points.append((xl, yb + t))

            # 5. 下翼板上(內) -> 下唇內
            x_tip_bot_in = xr - bb + t
            y_tip_bot_in = yb + cb

            if r_in > 0:
                cx, cy = xr - bb + t + r_in, yb + t + r_in
                for i in range(n_r + 1):
                    ang = 1.5 * np.pi - (i / n_r) * (0.5 * np.pi)
                    points.append((cx + r_in * np.cos(ang), cy + r_in * np.sin(ang)))
            else:
                points.append((x_tip_bot_in, yb + t))

            # 6. 下唇尖 (內)
            points.append((x_tip_bot_in, y_tip_bot_in))

            # 7. 下唇尖 (外)
            x_tip_bot_out = xr - bb
            y_tip_bot_out = yb + cb
            points.append((x_tip_bot_out, y_tip_bot_out))

            # 8. 下唇外 -> 下翼板下
            if r_out > 0:
                cx, cy = x_tip_bot_out + r_out, yb + r_out
                for i in range(n_r + 1):
                    ang = 1.0 * np.pi + (i / n_r) * (0.5 * np.pi)
                    points.append((cx + r_out * np.cos(ang), cy + r_out * np.sin(ang)))
            else:
                points.append((x_tip_bot_out, yb))

            # 9. 下翼板下 -> 腹板右
            if r_out > 0:
                cx, cy = xr - r_out, yb + r_out
                for i in range(n_r + 1):
                    ang = 1.5 * np.pi + (i / n_r) * (0.5 * np.pi)
                    points.append((cx + r_out * np.cos(ang), cy + r_out * np.sin(ang)))
            else:
                points.append((xr, yb))

            # 10. 腹板右 -> 上翼板下(內)
            if r_in > 0:
                cx, cy = xr + r_in, yt - t - r_in
                for i in range(n_r + 1):
                    ang = 1.0 * np.pi - (i / n_r) * (0.5 * np.pi)
                    points.append((cx + r_in * np.cos(ang), cy + r_in * np.sin(ang)))
            else:
                points.append((xr, yt - t))

            # 11. 上翼板下(內) -> 上唇內
            if r_in > 0:
                cx, cy = x_tip_top_out - t - r_in, yt - t - r_in
                for i in range(n_r + 1):
                    ang = 0.5 * np.pi - (i / n_r) * (0.5 * np.pi)
                    points.append((cx + r_in * np.cos(ang), cy + r_in * np.sin(ang)))
            else:
                points.append((x_tip_top_out - t, yt - t))

            # 12. 上唇尖 (內) -> [修正] 使用正確的變數名稱
            points.append((x_tip_top_out - t, y_tip_top_out))  # <--- 修正了這裡

            try:
                poly = Polygon(points).buffer(0)
                if poly.geom_type == 'MultiPolygon': poly = max(poly.geoms, key=lambda a: a.area)
                return Geometry(poly)
            except Exception as e:
                print(f"[ERROR] Z-Section Geometry Failed: {e}")
                return None

        # ==========================================
        # Channel
        # ==========================================
        elif stype == 'Channel':
            h = float(d['h']);
            tw = float(d['tw'])
            bf_default = float(d.get('bf', 0))
            bft = float(d.get('bft', bf_default));
            bfb = float(d.get('bfb', bf_default))
            t_default = float(d.get('tf', 0))
            tft = float(d.get('tft', t_default));
            tfb = float(d.get('tfb', t_default))
            r_val = float(d.get('r', 0));
            n_r_val = 8 if r_val > 0 else 0
            if bft == bfb and tft == tfb:
                sig = inspect.signature(steel_sections.channel_section)
                params = sig.parameters
                kwargs = {'d': h, 'b': bft, 't_f': tft, 't_w': tw, 'n_r': n_r_val}
                if 'r' in params:
                    kwargs['r'] = r_val
                elif 'r_r' in params:
                    kwargs['r_r'] = r_val
                return steel_sections.channel_section(**kwargs)
            else:
                points = []
                points.append((0, 0));
                points.append((bfb, 0));
                points.append((bfb, tfb))
                if r_val > 0:
                    cx = tw + r_val;
                    cy = tfb + r_val
                    for i in range(n_r_val + 1):
                        theta = 1.5 * np.pi - (i / n_r_val) * (0.5 * np.pi)
                        points.append((cx + r_val * np.cos(theta), cy + r_val * np.sin(theta)))
                else:
                    points.append((tw, tfb))
                if r_val > 0:
                    cx = tw + r_val;
                    cy = h - tft - r_val
                    for i in range(n_r_val + 1):
                        theta = 1.0 * np.pi - (i / n_r_val) * (0.5 * np.pi)
                        points.append((cx + r_val * np.cos(theta), cy + r_val * np.sin(theta)))
                else:
                    points.append((tw, h - tft))
                points.append((bft, h - tft));
                points.append((bft, h));
                points.append((0, h))
                return Geometry(Polygon(points).buffer(0))

        # ==========================================
        # C 型鋼
        # ==========================================
        elif stype == 'C':
            h = float(d['h']);
            t = float(d['t'])
            b_def = float(d.get('b', 0));
            bt = float(d.get('bt', b_def)) if d.get('bt') else b_def;
            bb = float(d.get('bb', b_def)) if d.get('bb') else b_def
            c_def = float(d.get('c', 0));
            ct = float(d.get('ct', c_def)) if d.get('ct') else c_def;
            cb = float(d.get('cb', c_def)) if d.get('cb') else c_def
            r_in = float(d.get('r', 0));
            r_out = r_in + t;
            n_r = 8 if r_in > 0 else 0
            limit_r = min(bt, bb, h / 2.0)
            if r_out > limit_r: r_out = limit_r - 0.1; r_in = max(0, r_out - t)
            points = []
            points.append((bb, cb))
            if r_out > 0:
                cx, cy = bb - r_out, r_out
                for i in range(n_r + 1):
                    ang = 0.0 - (i / n_r) * (0.5 * np.pi)
                    points.append((cx + r_out * np.cos(ang), cy + r_out * np.sin(ang)))
            else:
                points.append((bb, 0))
            if r_out > 0:
                cx, cy = r_out, r_out
                for i in range(n_r + 1):
                    ang = 1.5 * np.pi - (i / n_r) * (0.5 * np.pi)
                    points.append((cx + r_out * np.cos(ang), cy + r_out * np.sin(ang)))
            else:
                points.append((0, 0))
            if r_out > 0:
                cx, cy = r_out, h - r_out
                for i in range(n_r + 1):
                    ang = 1.0 * np.pi - (i / n_r) * (0.5 * np.pi)
                    points.append((cx + r_out * np.cos(ang), cy + r_out * np.sin(ang)))
            else:
                points.append((0, h))
            if r_out > 0:
                cx, cy = bt - r_out, h - r_out
                for i in range(n_r + 1):
                    ang = 0.5 * np.pi - (i / n_r) * (0.5 * np.pi)
                    points.append((cx + r_out * np.cos(ang), cy + r_out * np.sin(ang)))
            else:
                points.append((bt, h))
            points.append((bt, h - ct));
            points.append((bt - t, h - ct))
            if r_in > 0:
                cx, cy = bt - r_out, h - r_out
                for i in range(n_r + 1):
                    ang = 0.0 + (i / n_r) * (0.5 * np.pi)
                    points.append((cx + r_in * np.cos(ang), cy + r_in * np.sin(ang)))
            else:
                points.append((bt - t, h - t))
            if r_in > 0:
                cx, cy = r_out, h - r_out
                for i in range(n_r + 1):
                    ang = 0.5 * np.pi + (i / n_r) * (0.5 * np.pi)
                    points.append((cx + r_in * np.cos(ang), cy + r_in * np.sin(ang)))
            else:
                points.append((t, h - t))
            if r_in > 0:
                cx, cy = r_out, r_out
                for i in range(n_r + 1):
                    ang = 1.0 * np.pi + (i / n_r) * (0.5 * np.pi)
                    points.append((cx + r_in * np.cos(ang), cy + r_in * np.sin(ang)))
            else:
                points.append((t, t))
            if r_in > 0:
                cx, cy = bb - r_out, r_out
                for i in range(n_r + 1):
                    ang = 1.5 * np.pi + (i / n_r) * (0.5 * np.pi)
                    points.append((cx + r_in * np.cos(ang), cy + r_in * np.sin(ang)))
            else:
                points.append((bb - t, t))
            points.append((bb - t, cb))
            try:
                poly = Polygon(points).buffer(0)
                if poly.geom_type == 'MultiPolygon': poly = max(poly.geoms, key=lambda a: a.area)
                return Geometry(poly)
            except:
                return None

        # ==========================================
        # L 型鋼
        # ==========================================
        elif stype == 'L':
            h = float(d['h']);
            b = float(d['b'])
            t_default = float(d.get('t', 0));
            tv = float(d.get('tv', t_default));
            th = float(d.get('th', t_default))
            r_val = float(d.get('r', 0));
            n_r_val = 8 if r_val > 0 else 0
            if tv == th and tv > 0:
                sig = inspect.signature(steel_sections.angle_section)
                params = sig.parameters
                kwargs = {'d': h, 'b': b, 't': tv, 'n_r': n_r_val}
                if 'r' in params:
                    kwargs['r'] = r_val
                elif 'r_r' in params:
                    kwargs['r_r'] = r_val
                if 'r_t' in params: kwargs['r_t'] = 0
                return steel_sections.angle_section(**kwargs)
            else:
                points = []
                points.append((0, 0));
                points.append((b, 0));
                points.append((b, th))
                if r_val > 0:
                    cx = tv + r_val;
                    cy = th + r_val
                    for i in range(n_r_val + 1):
                        theta = 1.5 * np.pi - (i / n_r_val) * (0.5 * np.pi)
                        points.append((cx + r_val * np.cos(theta), cy + r_val * np.sin(theta)))
                else:
                    points.append((tv, th))
                points.append((tv, h));
                points.append((0, h))
                return Geometry(Polygon(points).buffer(0))

        # ==========================================
        # T, Pipe, Box
        # ==========================================
        elif stype == 'T':
            r_val = float(d.get('r', 0));
            n_r_val = 8 if r_val > 0 else 0
            return steel_sections.tee_section(d=float(d['h']), b=float(d['bf']), t_f=float(d['tf']), t_w=float(d['tw']),
                                              r=r_val, n_r=n_r_val)
        elif stype == 'Pipe':
            return steel_sections.circular_hollow_section(d=float(d['d']), t=float(d['t']), n=64)
        elif stype == 'Box':
            h = float(d['h'])
            b = float(d['b'])
            t = float(d['t'])

            r_in = float(d.get('r', 0))
            r_out = r_in + t
            n_r = 8 if r_in > 0 else 0

            # 物理限制檢查
            limit_r = min(b / 2.0, h / 2.0)
            if r_out > limit_r:
                r_out = limit_r - 0.01
                r_in = max(0, r_out - t)

            # 建立多邊形 Helper
            def create_rect_points(w, h, r, n):
                # 中心 (0,0)
                # 右上 (w/2, h/2)
                pts = []
                xr, yr = w / 2.0, h / 2.0

                if r <= 0:
                    # 直角矩形 (逆時針)
                    return [
                        (xr, yr),  # 右上
                        (-xr, yr),  # 左上
                        (-xr, -yr),  # 左下
                        (xr, -yr)  # 右下
                    ]

                # 圓角矩形 (逆時針)
                # 1. 右上圓角 (0 -> 90)
                # 圓心 (xr-r, yr-r)
                cx, cy = xr - r, yr - r
                for i in range(n + 1):
                    ang = 0.0 + (i / n) * (0.5 * np.pi)
                    pts.append((cx + r * np.cos(ang), cy + r * np.sin(ang)))

                # 2. 左上圓角 (90 -> 180)
                cx, cy = -xr + r, yr - r
                for i in range(n + 1):
                    ang = 0.5 * np.pi + (i / n) * (0.5 * np.pi)
                    pts.append((cx + r * np.cos(ang), cy + r * np.sin(ang)))

                # 3. 左下圓角 (180 -> 270)
                cx, cy = -xr + r, -yr + r
                for i in range(n + 1):
                    ang = 1.0 * np.pi + (i / n) * (0.5 * np.pi)
                    pts.append((cx + r * np.cos(ang), cy + r * np.sin(ang)))

                # 4. 右下圓角 (270 -> 360)
                cx, cy = xr - r, -yr + r
                for i in range(n + 1):
                    ang = 1.5 * np.pi + (i / n) * (0.5 * np.pi)
                    pts.append((cx + r * np.cos(ang), cy + r * np.sin(ang)))

                return pts

            # 產生外圈與內圈點
            outer_pts = create_rect_points(b, h, r_out, n_r)
            inner_pts = create_rect_points(b - 2 * t, h - 2 * t, r_in, n_r)

            try:
                # 建立帶孔的多邊形
                # shapely Polygon(shell, holes=[])
                poly = Polygon(shell=outer_pts, holes=[inner_pts]).buffer(0)
                return Geometry(poly)
            except Exception as e:
                print(f"[ERROR] Box Geometry Failed: {e}")
                return None

        return None

    except Exception as e:
        print(f"[ERROR in create_geometry] {e}")
        import traceback
        traceback.print_exc()
        return None


# --- 輔助函式 (保持不變) ---
def get_mesh_nodes(sec):
    if hasattr(sec, 'mesh') and hasattr(sec.mesh, 'nodes'): return np.array(sec.mesh.nodes)
    if hasattr(sec, 'mesh') and isinstance(sec.mesh, dict):
        if 'vertices' in sec.mesh: return np.array(sec.mesh['vertices'])
        if 'nodes' in sec.mesh: return np.array(sec.mesh['nodes'])
    if hasattr(sec, 'nodes'): return np.array(sec.nodes)
    raise ValueError(f"無法提取網格節點")


def get_min_dimension(stype, d):
    vals = []
    keys = ['tw', 'tf', 't', 'tft', 'tfb', 'tv', 'th']
    for key in keys:
        if key in d:
            val = float(d[key])
            if val > 0: vals.append(val)
    if not vals: return 10.0
    return min(vals)