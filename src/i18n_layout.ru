# Pure Ru search-row layout policy. Measured native text widths are inputs.
# Inputs keep at least 80px; buttons wrap instead of covering other controls.
算 寻栏布局 宽 为 数, 按钮宽 为 阵:
    总 取 0.
    位 取 0.
    循 按钮宽 其 量 次
        总 取 总+按钮宽[位]+6.
        位 取 位+1.
    环
    输入宽 取 (宽-24)/2.
    单排 取 宽 >= 总+384.
    若 单排 则 输入宽 取 (宽-总-24)/2. 然
    输入宽 取 输入宽-输入宽%1.
    若 输入宽 < 80 则 输入宽 取 80. 然
    按们 取 [].
    横 取 8.
    纵 取 37.
    若 单排 则 横 取 24+输入宽*2. 纵 取 5. 然
    位 取 0.
    循 按钮宽 其 量 次
        按宽 取 按钮宽[位].
        若 横+按宽 > 宽-8 且 横 > 8 则 横 取 8. 纵 取 纵+32. 然
        按们 其 增 [横,纵,按宽,26].
        横 取 横+按宽+6.
        位 取 位+1.
    环
    得 {'height':(纵+33),'inputWidth':输入宽,'buttons':按们}.
法
