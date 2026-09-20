# 八喜桌宠

八喜是一款基于 Python/PySide6 的 Windows 桌宠，使用透明 PNG 序列播放动画，支持投喂、舞蹈和托盘大小调整。角色动画以实拍猫咪照片为基础，结合 AI 生成制作。

**本仓库提供完整源码及运行所需素材，包括 12 套动作、210 张 PNG。下载后需自行运行或打包，不包含预编译 EXE。**

## Windows 环境

- Python 3.10 或以上，安装时包含 Python Launcher（`py` 命令）。
- 将源码完整解压，保留目录结构及素材文件。
- 安装依赖和首次构建需要联网。

## 从源码运行

在解压后的项目目录执行：

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python tools/validate_baxi_assets.py
.venv\Scripts\python app/main.py
```

也可使用 `run_baxi.bat` 启动。运行所需动画已包含在仓库中。

## 打包 Windows EXE

在 Windows 上双击 `build_windows.bat`，或在项目目录的 PowerShell 中执行：

```powershell
.\build_windows.bat
```

脚本会建立独立构建环境、联网安装依赖、校验素材并打包。

输出目录及程序入口：

```text
dist\BaxiPet-v0.9-hotfix5-sourceprep2\
dist\BaxiPet-v0.9-hotfix5-sourceprep2\BaxiPet-v0.9-hotfix5-sourceprep2.exe
```

运行或分发时须保留**整个输出目录**，不要只复制 EXE。构建失败时查看 `build_error.log`。自行分发编译版本时，第三方组件声明见 `THIRD_PARTY.md`。

## 许可与反馈

- 代码：见 `LICENSE`，允许非商业修改和再发布；商用须另行取得许可。
- 猫咪素材：见 `ASSETS.md`，与代码许可分别处理。
- 第三方依赖：见 `THIRD_PARTY.md`，保留各自许可。
- 参考来源：见 `REFERENCES.md`。
- 问题反馈及商业许可联系：请在本仓库提交 Issue。
