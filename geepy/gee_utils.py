import ee
import importlib
import geepy
from datetime import datetime
from IPython import get_ipython




def log_start_time(info=None):
    """
    记录代码单元执行的开始时间。
    """
    start_time = datetime.now()
    print(f"\n🔔 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

def register_pre_run_cell_hook():
    """
    注册 Jupyter Notebook 钩子，用于在代码单元运行前自动记录时间。
    """
    ipython = get_ipython()
    if ipython:
        ipython.events.register('pre_run_cell', log_start_time)
        print("✅ 已注册 pre_run_cell 钩子！")
    else:
        print("⚠️ 当前环境非 Jupyter Notebook，无法注册钩子！")


def print_image_collection_start_dates(imgcol):
    """
    打印影像集合中每个影像的开始时间，并转换为 'yyyy-MM-dd' 的日期格式。

    Args:
        imgcol (ee.ImageCollection): 输入的影像集合。

    Returns:
        list: 包含所有影像开始时间的字符串列表，格式为 'yyyy-MM-dd'。
    """
    def format_start_date(image):
        # 获取影像的开始时间属性并格式化为 'yyyy-MM-dd'
        start_date = ee.Date(image.get('system:time_start')).format('yyyy-MM-dd')
        return ee.Feature(None, {'date': start_date})  # 创建一个包含日期的 Feature

    # 将影像集合映射为日期集合
    date_features = imgcol.map(format_start_date)

    # 提取日期并打印
    dates = date_features.aggregate_array('date').getInfo()
    print("Start dates of images in the collection:")
    # for date in dates:
    #     print(date)

    return dates


def reload_geepy():
    """
    强制重新加载 geepy 包及其所有子模块，适用于开发者模式安装时更新后的动态加载。
    """
    for submodule in list(geepy.__dict__.values()):
        if hasattr(submodule, "__name__") and submodule.__name__.startswith("geepy."):
            importlib.reload(submodule)
    importlib.reload(geepy)


def create_rectangular_grid(study_area, grid_width=1.5, grid_height=1.5):
    """
    在给定的研究区内生成指定大小的矩形网格。

    Args:
        study_area (ee.FeatureCollection): 研究区。
        grid_width (float): 网格宽度（经度方向，单位：度）。
        grid_height (float): 网格高度（纬度方向，单位：度）。

    Returns:
        ee.FeatureCollection: 裁剪后的网格。
    """
    bounds = study_area.bounds()
    coords = bounds.coordinates().get(0)

    min_lon = ee.List(ee.List(coords).get(0)).get(0)
    max_lon = ee.List(ee.List(coords).get(1)).get(0)
    min_lat = ee.List(ee.List(coords).get(0)).get(1)
    max_lat = ee.List(ee.List(coords).get(2)).get(1)

    # 生成经度和纬度列表
    lon_list = ee.List.sequence(min_lon, max_lon, grid_width)
    lat_list = ee.List.sequence(min_lat, max_lat, grid_height)

    # 构建网格
    grid = lon_list.map(
        lambda lon: lat_list.map(
            lambda lat: ee.Feature(
                ee.Geometry.Rectangle(
                    [lon, lat, ee.Number(lon).add(grid_width), ee.Number(lat).add(grid_height)]
                )
            )
        )
    ).flatten()

    # 转换为 FeatureCollection 并裁剪到研究区
    grid_fc = ee.FeatureCollection(grid)
    return grid_fc.filterBounds(study_area)


def create_hexagonal_grid(study_area, radius=1.5):
    """
    在给定的研究区内生成指定大小的六边形网格。

    Args:
        study_area (ee.FeatureCollection): 研究区。
        radius (float): 六边形边到中心的距离（单位：度）。

    Returns:
        ee.FeatureCollection: 裁剪后的六边形网格。
    """
    bounds = study_area.bounds()
    coords = bounds.coordinates().get(0)

    xmin = ee.Number(ee.List(ee.List(coords).get(0)).get(0))
    ymin = ee.Number(ee.List(ee.List(coords).get(0)).get(1))
    xmax = ee.Number(ee.List(ee.List(coords).get(2)).get(0))
    ymax = ee.Number(ee.List(ee.List(coords).get(2)).get(1))

    # 将 Python float 转换为 ee.Number
    radius = ee.Number(radius)
    sqrt_3 = ee.Number(3).sqrt()
    r_half = radius.divide(2)
    r_half_sqrt_3 = r_half.multiply(sqrt_3)
    step_x = radius.multiply(3)
    step_y = radius.multiply(sqrt_3)

    xx1 = ee.List.sequence(xmin, xmax.add(radius), step_x)
    yy1 = ee.List.sequence(ymin, ymax.add(radius), step_y)

    xx2 = ee.List.sequence(xmin.subtract(radius.multiply(1.5)), xmax.add(radius), step_x)
    yy2 = ee.List.sequence(ymin.add(r_half_sqrt_3), ymax.add(radius), step_y)

    def hex(x, y):
        point1_x = ee.Number(x).subtract(radius)
        point2_x = ee.Number(x).subtract(r_half)
        point3_x = ee.Number(x).add(r_half)
        point4_x = ee.Number(x).add(radius)

        point1_y = ee.Number(y).add(r_half_sqrt_3)
        point2_y = ee.Number(y)
        point3_y = ee.Number(y).subtract(r_half_sqrt_3)

        polygon = ee.Geometry.Polygon(
            [[[point1_x, point2_y],
              [point2_x, point3_y],
              [point3_x, point3_y],
              [point4_x, point2_y],
              [point3_x, point1_y],
              [point2_x, point1_y]]]
        )
        return ee.Feature(polygon)

    cell1 = xx1.map(
        lambda x: yy1.map(lambda y: hex(x, y))
    ).flatten()

    cell2 = xx2.map(
        lambda x: yy2.map(lambda y: hex(x, y))
    ).flatten()

    # 将嵌套的列表扁平化并创建 FeatureCollection
    hex_grid = ee.FeatureCollection(cell1.cat(cell2))
    return hex_grid.filterBounds(study_area)


# 明确需要导出的函数
__all__ = ["register_pre_run_cell_hook", "print_image_collection_start_dates", "reload_geepy", "create_rectangular_grid", "create_hexagonal_grid"]
