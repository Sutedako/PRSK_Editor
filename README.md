# PRSK_Editor

PRSK Editor 是为了规范化PJS字幕组内翻译流程而开发的工具。

## 使用

### 翻译文本导入

加载剧本 JSON 后，可通过原有的文本打开入口读取旧 TXT 或翻译 TXT v2。
v2 使用 `@version:2`、`@scenario:<ScenarioId>` 文件头，以及
`@dialog:001[说话人]`、`@banner:001`、`@marker:001` 条目标记。
编号对应原始 JSON 数组下标加一，条目可以调换顺序；支持多行正文、空说话人、
显式空正文、注释与行首转义。导入失败会提示具体原因，不应用部分翻译。
此处新增的是 v2 读取支持，保存仍使用现有的旧 TXT 格式。

请自行下载requirements.txt中的依赖库，使用

```bash
python main.pyw
```

运行程序。

你也可以使用PyInstaller将程序打包成exe文件：

```bash
pyinstaller --onefile main.pyw
```
