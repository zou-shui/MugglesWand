# Muggles' Wand BLE 按键宏语法说明

为了让魔杖能够模拟任意键盘宏，本文档约定了一种**按键序列语法**，用一串字符表达键盘宏。

按键序列的语法设计思路只有一句话：

> **想模拟键盘打出什么，就写什么；打不出字符的键，用键盘上的键名。**

## 基本规则

1. **字符直接写**：想按下 `a`，就写 `a`。
2. **多个按键用逗号分隔**：程序会按顺序依次按下，如 `h,e,l,l,o, ,w,o,r,l,d,enter`。末尾无需结束符。
3. **控制键用键名**：Shift、Ctrl、Enter、方向键等打不出字符的键，用键盘上印的名字，如 `shift`、`ctrl`、`enter`、`left`、`f5`。键名不区分大小写。macOS 的 Command、Option 可分别写 `cmd`、`option`。
4. **快捷键用 `[]`**：如 `[ctrl+c]`、`[alt+f4]`、`[ctrl+shift+s]`。方括号内修饰键可以有多个。
5. **节奏用括号补充**：按键后加 `(按住毫秒,间隔毫秒)`，如 `a(500,200)` 表示保持按下a 500ms松开后等待200ms。如只需指定一个参数，则另一个参数留空：`a(,200)`或者`a(500,)`，省略项使用默认值 25ms，每项最大 10000ms。
6. 整条序列最长 127 个字符。

## 示例

| 序列                                                      | 效果                                                    |
| ------------------------------------------------------- | ----------------------------------------------------- |
| `H,e,l,l,o, ,W,o,r,l,d,enter`                           | 输入 Hello World后回车                                     |
| `up,down,left,right`                                    | 依次按下方向键的上、下、左、右                                       |
| `[ctrl+c]`                                              | Ctrl+C，复制的快捷键                                         |
| `[alt+f4]`                                              | Alt+F4，关闭程序的快捷键                                       |
| `a(,500),b(1000,)`                                      | 按完 a 之后等待500ms，然后按下 b 持续1秒                            |
| `playpause,next`                                        | 播放/暂停，然后下一首                                           |
| `[win+r](,500),c,m,d,enter(,500),i,p,c,o,n,f,i,g,enter` | 打开Windows运行窗口等待500ms后，输入cmd回车后等待500ms，然后输入ipconfig回车。 |
| `[cmd+c]`                                               | macOS：Command+C，复制快捷键                                 |
| `[cmd+space],t,e,r,m,i,n,a,l,enter`                     | macOS：Spotlight 搜索 Terminal 并回车                       |

## 字符与按键

- 字母直接写：`a`~`z`。大写会自动加 Shift，如 `A`。
- 数字直接写：`0`~`9`。
- 符号直接写。普通的：`.` `/` `;` `'` `-` `=` `\` `` ` ``；需要 Shift 的会自动处理：`!` `@` `#` `$` `%` `^` `&` `*` `_` `+` `{` `}` `|` `:` `"` `<` `>` `?` `~`。
- 支持空格和逗号，虽然逗号本身是分隔符，但程序会自动辨别分隔符逗号和按键逗号。
- `[` `]` `(` `)` 是语法符号，不能单独直接写，请使用键名 `leftbracket`、`rightbracket`、`leftparen`、`rightparen`。

## 键名表

### 编辑键、方向键与功能键

| 类别     | 键名                                                                                                                                                 |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| 编辑键    | `enter` / `return`、`esc` / `escape`、`tab`、`backspace`、`delete` / `del`、`insert` / `ins`、`home`、`end`、`pageup` / `pgup`、`pagedown` / `pgdn`、`space` |
| 方向键    | `left`、`right`、`up`、`down`                                                                                                                         |
| 锁定与系统键 | `capslock`、`numlock`、`scrolllock`、`printscreen`、`pause`、`menu`                                                                                     |
| 功能键    | `f1`~`f12`                                                                                                                                         |

> `pause` 是 Pause/Break 键；播放/暂停请用媒体键 `playpause`。

### 符号键别名

| 键名             | 符号  |
| -------------- | --- |
| `comma`        | `,` |
| `dot`          | `.` |
| `slash`        | `/` |
| `semicolon`    | `;` |
| `apostrophe`   | `'` |
| `grave`        | 反引号 |
| `minus`        | `-` |
| `equal`        | `=` |
| `leftbracket`  | `[` |
| `rightbracket` | `]` |
| `backslash`    | `\` |
| `plus`         | `+` |
| `leftparen`    | `(` |
| `rightparen`   | `)` |

### 修饰键

| 修饰键                 | 键名                                                                                      |
| ------------------- | --------------------------------------------------------------------------------------- |
| Ctrl                | `ctrl`、`control`、`lctrl`、`leftctrl`、`rctrl`、`rightctrl`                                 |
| Shift               | `shift`、`lshift`、`leftshift`、`rshift`、`rightshift`                                      |
| Alt / Option        | `alt`、`option`、`opt`、`lalt`、`leftalt`、`ralt`、`rightalt`、`altgr`                         |
| Win / Command / GUI | `win`、`windows`、`cmd`、`command`、`gui`、`super`、`meta`、`lwin`、`leftwin`、`rwin`、`rightwin` |

> Windows 上 `win` 是 Win 键，macOS 上等价于 Command（⌘），Linux 上等价于 Super。Mac 用户建议直接写 `cmd` / `option`。

### 媒体键

| 键名                  | 功能      |
| ------------------- | ------- |
| `playpause`         | 播放 / 暂停 |
| `next`              | 下一首     |
| `prev` / `previous` | 上一首     |

媒体键不能放进 `[]` 组合键；按住时间对它无效，只有间隔时间有效。

## 注意事项

- 单独字母区分大小写（大写自动加 Shift）；键名不区分大小写。
- 按键按 US 键盘布局发送，系统键盘布局不同时输出字符可能不同。
- 触发手势时魔杖 BLE 需已连接，否则不会发送按键。
- 序列最长 127 个字符，语法错误会保存失败并在控制台提示。
