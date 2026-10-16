# Pure-Ru native argument construction, shared by the GUI and portable tests.
# Parentheses delimit member calls before array commas. Without them a comma
# may become another member argument, even when the intent was another item.
算 菜单参数 状态, 菜单:
    得 [(状态 其 查 'window'),菜单].
法
算 窗口二参 状态, 第二:
    得 [(状态 其 查 'window'),第二].
法
算 控件二参 状态, 名, 第二:
    得 [(状态 其 查 名),第二].
法
算 注销类参数 状态:
    得 [(状态 其 查 'className'),(状态 其 查 'instance')].
法
