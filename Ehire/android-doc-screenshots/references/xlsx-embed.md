# xlsx 原图嵌入与校验

## 嵌入基本写法

```python
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.drawing.spreadsheet_drawing import OneCellAnchor, AnchorMarker
from openpyxl.utils.units import pixels_to_EMU

IMG_COL = 3          # D 列（0-based）
DISPLAY_W = 30       # 显示宽度 30px
OFFSET = pixels_to_EMU(1)

img = XLImage(path)                      # 原图，不压缩
ratio = img.height / img.width
img.width = DISPLAY_W
img.height = int(DISPLAY_W * ratio)

marker = AnchorMarker(
    col=IMG_COL,
    colOff=OFFSET + index * pixels_to_EMU(DISPLAY_W + 3),
    row=row_index,                        # 0-based
    rowOff=OFFSET,
)
img.anchor = OneCellAnchor(_from=marker, ext=None)
ws.add_image(img)
```

- `index` 是同一单元格内的第几张图，横向并排。
- 不要用 `ws.add_image(img, "D5")` 这种简写，它生成的锚点在不同软件里位置不一致。
- 图片对象要保留引用，避免被回收。

## 列宽

按该列最多张数计算，留出间隙：

```python
from openpyxl.utils import get_column_letter
max_count = 3
ws.column_dimensions[get_column_letter(IMG_COL + 1)].width = max_count * 4.2 + 1
```

具体换算按字体和截图比例微调，确保不压到相邻列。

## openpyxl 常见坑

- `range_boundaries()` 返回顺序是 `(min_col, min_row, max_col, max_row)`，参数写反会清空合并区域的数据。
- `insert_rows/delete_rows` 不会移动图片锚点、行高、合并区域，需要手工补偿。
- 修改合并区域前先记录原值，`unmerge` 会保留左上角值，但范围写错会丢数据。
- 保存前先备份；保存后重新打开逐项校验。

## 校验清单

1. **锚点行校验**：遍历 `ws._images`，读 `anchor._from.row + 1`，按行统计图片数量，与预期映射比对。
2. **内容校验**：逐行输出 A/B/C 列文本，与改动前快照比对，确认非截图列无变化。
3. **合并区域校验**：`ws.merged_cells.ranges` 与快照比对。
4. **图片本体校验**：把锚点行反查回 `rowNN_k.png`，比对文件 MD5，确认没有被旧图覆盖。
5. **列宽校验**：确认截图列宽度未挤压相邻列。

## 行结构变更后的重嵌

1. 先备份当前文件。
2. 记录每张图的锚点行与文件映射。
3. 按新结构重新生成「行号 → 图片文件」映射。
4. 清除截图列原有图片（只删 `_images` 中锚点在该列的对象），重新嵌入。
5. 跑一遍上面的校验清单。
