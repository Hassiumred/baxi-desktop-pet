# 第三方依赖与许可清单（源码范围）

本包只列安装需求，不附 wheel、DLL、Python 解释器、EXE 或第三方源码。没有准确历史安装锁文件，以下不是成品 EXE 的完整 SBOM，也不是许可证全文替代品。

|组件|本包声明/用途|许可线索与发布前工作|
|---|---|---|
|PySide6|>=6.6，窗口/计时/图像显示|Qt for Python 社区版 LGPLv3/GPLv3，另有商业版本。按实际模块/版本确认适用条款；不把所有 Qt 模块统一当 LGPL。|
|Pillow|>=10.0，素材校验工具导入 PIL|MIT-CMU；实际分发 Pillow 或其内含库时收集相应版本完整声明。|
|PyInstaller|>=6.0，构建工具|GPL 2.0 带打包例外，部分文件 Apache 2.0；打包例外不免除应用依赖义务。|
|Python|运行/构建环境，本包未附带|发布解释器或 EXE 时核对对应 Python 版本的 PSF 及第三方声明。|
|shiboken6、PySide6 Essentials/Addons、Qt 库及插件|PySide6 安装/构建时的间接组件|最终版本与实际捆绑范围尚未生成；发布 EXE 前列明并收集各自许可。|
|其他构建传递依赖/图像编解码库|由平台、wheel 和 PyInstaller 收集规则决定|不得把当前三个 requirements 条目当完整二进制许可清单。|

官方许可说明：
- https://doc.qt.io/qtforpython-6/commercial/index.html
- https://doc.qt.io/qtforpython-6/licenses.html
- https://pillow.readthedocs.io/en/stable/about.html
- https://pyinstaller.org/en/stable/license.html
- Python 后续核验入口：https://docs.python.org/3/license.html

分发 Windows 二进制时，需附带实际捆绑组件对应版本的许可和必要资料；本源码依赖清单不代替二进制发行包的完整声明。项目的非商业使用限制不覆盖第三方组件。
