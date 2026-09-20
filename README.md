# 八喜桌宠

我以自己拍摄的猫咪照片为基础，结合 AI 制作动画，把八喜做成了 Windows 桌宠。项目使用 Python/PySide6 和透明 PNG 序列，包含投喂、舞蹈及托盘大小调整等交互。

本仓库提供完整源码、12 套动作和 210 张 PNG。源码 ZIP 不包含预编译 EXE；从源码运行或构建请按下面的步骤操作。

## Windows 源码运行
安装 Python 3.10 或以上，在解压目录执行：
```
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python tools/validate_baxi_assets.py
.venv\Scripts\python app/main.py
```
也可使用 run_baxi.bat。完整素材已包含，不需自行另找动画。

## Windows 构建
在 Windows 上安装 Python 3.10 或以上（包含 Python Launcher `py`），将源码完整解压后，双击 `build_windows.bat`；也可以在源码目录的 PowerShell 中执行：

```powershell
.\build_windows.bat
```

脚本会建立独立构建环境、联网安装依赖、校验素材并打包。生成的程序为 `dist\BaxiPet-v0.9-hotfix5-sourceprep2\BaxiPet-v0.9-hotfix5-sourceprep2.exe`。运行或分享时请保留整个输出目录，不要只复制 EXE；构建失败可查看 `build_error.log`。分发自行构建的程序时，第三方组件声明见 `THIRD_PARTY.md`。

## 使用范围

我的代码允许非商业修改和再发布；商业使用请通过本仓库 Issues 联系我取得许可。猫咪素材单独说明，第三方依赖保留各自许可。

完整代码许可见 LICENSE；素材、第三方依赖和参考来源分别见 ASSETS.md、THIRD_PARTY.md 和 REFERENCES.md。
