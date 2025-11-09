# Gemini Image API 测试指南

## 📋 测试目的

在正式开发图片生成功能之前，验证 Google Gemini 2.5 Flash Image API 是否可以正常调用。

## 🚀 快速开始

### 步骤 1: 安装新依赖

```bash
# 激活虚拟环境
source venv/bin/activate

# 安装新依赖
pip install google-genai Pillow
```

### 步骤 2: 确认环境变量

确保 `.env` 文件中有 `GOOGLE_API_KEY`：

```bash
# 查看 .env 文件
cat .env | grep GOOGLE_API_KEY
```

应该看到类似：
```
GOOGLE_API_KEY=your_api_key_here
```

### 步骤 3: 运行测试脚本

```bash
# 方式 1: 直接运行
python _test_image_api.py

# 方式 2: 作为可执行文件运行
./_test_image_api.py
```

## ✅ 预期输出

如果一切正常，你应该看到：

```
============================================================
🧪 Gemini Image API 测试脚本
============================================================

📌 步骤 1: 检查环境变量...
✅ API Key 已设置 (长度: 39)

📌 步骤 2: 导入依赖库...
✅ 所有依赖已成功导入

📌 步骤 3: 初始化 Gemini 客户端...
✅ 客户端初始化成功

📌 步骤 4: 调用 Image API 生成测试图片...
   Prompt: A friendly cartoon dolphin swimming in blue ocean
   模型: gemini-2.5-flash-image
   比例: 1:1 (1024x1024)

✅ API 调用成功 (耗时: 4.23秒)

📌 步骤 5: 提取图片数据并保存到文件...
✅ 图片已保存到: test_images/test_dolphin_20251107_143052.png
   尺寸: 1024x1024px
   大小: 234.56 KB

============================================================
🎉 测试完成！所有步骤均通过
============================================================

📊 测试摘要:
   ✅ API 连接: 正常
   ✅ 图片生成: 成功
   ✅ 文件保存: 成功
   ⏱️  生成耗时: 4.23秒

💡 下一步:
   1. 查看生成的图片: open test_images/
   2. 如果图片质量满意，可以开始集成到项目中
```

## 🖼️ 查看生成的图片

### macOS:
```bash
open test_images/
```

### Linux:
```bash
xdg-open test_images/
```

### 或直接用浏览器打开:
```bash
ls -lh test_images/
```

## ❌ 常见问题

### 问题 1: 导入失败 `ModuleNotFoundError: No module named 'google.genai'`

**解决方案**:
```bash
pip install google-genai
```

### 问题 2: API 调用失败 `401 Unauthorized`

**可能原因**:
- API Key 无效或已过期
- 未设置环境变量

**解决方案**:
```bash
# 检查 API Key
echo $GOOGLE_API_KEY

# 如果为空，重新加载 .env
source .env
export GOOGLE_API_KEY=your_actual_key
```

### 问题 3: API 调用失败 `403 Forbidden`

**可能原因**:
- 未启用 Imagen API
- API 配额已用完

**解决方案**:
1. 访问 [Google AI Studio](https://aistudio.google.com/)
2. 检查 API 状态和配额

### 问题 4: 网络超时

**解决方案**:
- 检查网络连接
- 确认可以访问 Google 服务
- 可能需要配置代理

## 📊 性能参考

根据测试，单张图片生成：
- **耗时**: 3-5 秒
- **尺寸**: 1024x1024px（1:1 比例）
- **文件大小**: 约 200-300 KB

## 🎯 测试成功后

如果测试通过，说明：
1. ✅ API Key 有效
2. ✅ Gemini Image API 可以正常访问
3. ✅ 图片生成和保存功能正常
4. ✅ 可以开始进行图片生成功能的集成开发

请告知测试结果，我们将继续进行**迭代 1: 基础图片生成功能**的开发。

## 📚 参考文档

- [Gemini Image API 官方文档](https://ai.google.dev/gemini-api/docs/image-generation)
- [图片生成功能需求与设计文档](./图片生成功能需求与设计文档.md)
