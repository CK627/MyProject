// 数据导入页面JavaScript代码

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 如果当前页面是数据导入页面，则初始化
    if (document.getElementById('importContent')) {
        initDataImportPage();
    }
});

/**
 * 初始化数据导入页面
 */
function initDataImportPage() {
    console.log('数据导入页面初始化');
    
    // 这里可以添加页面初始化逻辑
    // 例如：检查权限、加载配置等
}

/**
 * 处理文件选择
 * @param {Event} event - 文件选择事件
 */
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) {
        return;
    }
    
    // 验证文件类型
    const allowedTypes = ['.xlsx', '.xls'];
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!allowedTypes.includes(fileExtension)) {
        showImportError('请选择Excel文件（.xlsx 或 .xls 格式）');
        return;
    }
    
    // 文件大小验证已移除，支持任意大小的Excel文件
    
    console.log('选择的文件:', file.name, '大小:', (file.size / 1024 / 1024).toFixed(2) + 'MB');
    
    // 显示文件信息
    showFileInfo(file);
}

/**
 * 显示文件信息并解析Excel文件
 * @param {File} file - 选择的文件
 */
function showFileInfo(file) {
    console.log('显示文件信息:', file.name);
    
    // 显示文件信息
    updateImportProgress(10, '正在读取文件...');
    
    // 解析Excel文件
    parseExcelFile(file);
}

/**
 * 解析Excel文件
 * @param {File} file - Excel文件
 */
function parseExcelFile(file) {
    const reader = new FileReader();
    
    reader.onload = function(e) {
        try {
            updateImportProgress(30, '正在解析Excel文件...');
            
            const data = new Uint8Array(e.target.result);
            const workbook = XLSX.read(data, { type: 'array' });
            
            // 获取第一个工作表
            const firstSheetName = workbook.SheetNames[0];
            const worksheet = workbook.Sheets[firstSheetName];
            
            // 转换为JSON数据
            const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
            
            if (jsonData.length < 2) {
                throw new Error('Excel文件数据不足，至少需要包含表头和一行数据');
            }
            
            updateImportProgress(50, '正在验证数据格式...');
            
            // 处理解析的数据
            processExcelData(jsonData);
            
        } catch (error) {
            console.error('解析Excel文件失败:', error);
            showImportError('解析Excel文件失败: ' + error.message);
            updateImportProgress(0, '解析失败');
        }
    };
    
    reader.onerror = function() {
        showImportError('读取文件失败，请重试');
        updateImportProgress(0, '读取失败');
    };
    
    reader.readAsArrayBuffer(file);
}

/**
 * 处理Excel解析的数据
 * @param {Array} data - 解析的数据数组
 */
function processExcelData(data) {
    try {
        // 获取表头
        const headers = data[0];
        console.log('Excel表头:', headers);
        
        // 获取数据行
        const rows = data.slice(1);
        console.log('数据行数:', rows.length);
        
        // 转换为对象数组
        const importData = rows.map((row, index) => {
            const rowData = {};
            headers.forEach((header, colIndex) => {
                if (header && row[colIndex] !== undefined) {
                    rowData[header.trim()] = row[colIndex];
                }
            });
            rowData._rowIndex = index + 2; // Excel行号（从2开始，因为第1行是表头）
            return rowData;
        }).filter(row => {
            // 过滤空行
            const values = Object.values(row).filter(v => v !== undefined && v !== '' && v !== null);
            return values.length > 1; // 至少有一个有效字段（除了_rowIndex）
        });
        
        updateImportProgress(70, '正在验证数据...');
        
        // 验证数据
        const validationResult = validateImportData(importData);
        
        if (!validationResult.valid) {
            showImportError('数据验证失败: ' + validationResult.errors.join(', '));
            return;
        }
        
        // 显示验证警告
        if (validationResult.warnings.length > 0) {
            validationResult.warnings.forEach(warning => {
                showImportWarning(warning);
            });
        }
        
        updateImportProgress(80, '数据验证完成，准备导入...');
        
        // 存储解析的数据供导入使用
        window.parsedImportData = importData;
        
        showImportSuccess(`文件解析成功！共找到 ${importData.length} 条有效数据，点击"开始导入"按钮进行导入。`);
        
        // 启用导入按钮
        const importBtn = document.querySelector('.btn-import[onclick="DataImport.startImport()"]');
        if (importBtn) {
            importBtn.disabled = false;
        }
        
    } catch (error) {
        console.error('处理Excel数据失败:', error);
        showImportError('处理Excel数据失败: ' + error.message);
        updateImportProgress(0, '处理失败');
    }
}

/**
 * 开始导入数据
 */
function startImport() {
    console.log('开始导入数据');
    
    // 检查是否有解析的数据
    if (!window.parsedImportData || window.parsedImportData.length === 0) {
        showImportError('请先选择并解析Excel文件');
        return;
    }
    
    // 禁用导入按钮
    const importBtn = document.querySelector('.btn-import[onclick="DataImport.startImport()"]');
    if (importBtn) {
        importBtn.disabled = true;
        importBtn.innerHTML = '<span>⏳</span> 导入中...';
    }
    
    updateImportProgress(90, '正在导入数据到数据库...');
    
    // 准备导入数据
    const importData = window.parsedImportData.map(row => {
        // 移除内部字段
        const cleanRow = { ...row };
        delete cleanRow._rowIndex;
        return cleanRow;
    });
    
    // 调用后端API
    fetch('api/import.php', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            importData: importData
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP错误: ${response.status}`);
        }
        return response.json();
    })
    .then(result => {
        updateImportProgress(100, '导入完成');
        
        if (result.success) {
            const stats = result.stats;
            let message = `导入成功！共处理 ${stats.total} 条记录，成功导入 ${stats.success} 条`;
            
            if (stats.skip > 0) {
                message += `，跳过 ${stats.skip} 条`;
            }
            
            if (stats.error > 0) {
                message += `，失败 ${stats.error} 条`;
            }
            
            showImportSuccess(message);
            
            // 显示警告信息
            if (result.warnings && result.warnings.length > 0) {
                result.warnings.forEach(warning => {
                    showImportWarning(warning);
                });
            }
            
            // 显示错误信息
            if (result.errors && result.errors.length > 0) {
                result.errors.forEach(error => {
                    showImportError(error);
                });
            }
            
            // 清理数据
            window.parsedImportData = null;
            
        } else {
            showImportError(result.message || '导入失败');
        }
    })
    .catch(error => {
        console.error('导入请求失败:', error);
        showImportError('导入请求失败: ' + error.message);
        updateImportProgress(0, '导入失败');
    })
    .finally(() => {
        // 恢复导入按钮
        if (importBtn) {
            importBtn.disabled = false;
            importBtn.innerHTML = '<span>🚀</span> 开始导入';
        }
    });
}

/**
 * 显示导入成功消息
 * @param {string} message - 成功消息
 */
function showImportSuccess(message) {
    console.log('导入成功:', message);
    
    // 可以使用现有的toast通知系统
    if (typeof showSuccess === 'function') {
        showSuccess(message);
    }
}

/**
 * 显示导入错误消息
 * @param {string} message - 错误消息
 */
function showImportError(message) {
    console.log('导入错误:', message);
    
    // 可以使用现有的toast通知系统
    if (typeof showError === 'function') {
        showError(message);
    }
}

/**
 * 显示导入警告信息
 * @param {string} message - 警告信息
 */
function showImportWarning(message) {
    const resultDiv = document.getElementById('importResult');
    if (resultDiv) {
        const existingContent = resultDiv.innerHTML;
        resultDiv.innerHTML = existingContent + `
            <div class="import-warning">
                <span class="warning-icon">⚠️</span>
                <span class="warning-message">${message}</span>
            </div>
        `;
        resultDiv.style.display = 'block';
    }
}

/**
 * 显示导入警告消息
 * @param {string} message - 警告消息
 */
function showImportWarning(message) {
    console.log('导入警告:', message);
    
    // 可以使用现有的toast通知系统
    if (typeof showToast === 'function') {
        showToast(message, 'warning');
    }
}

/**
 * 重置导入状态
 */
function resetImportState() {
    console.log('重置导入状态');
    
    // 清除文件选择
    const fileInput = document.getElementById('importFileInput');
    if (fileInput) {
        fileInput.value = '';
    }
    
    // 隐藏结果显示
    const resultElements = document.querySelectorAll('.import-result');
    resultElements.forEach(element => {
        element.style.display = 'none';
    });
    
    // 隐藏进度条
    const progressContainer = document.querySelector('.progress-container');
    if (progressContainer) {
        progressContainer.style.display = 'none';
    }
}

/**
 * 更新导入进度
 * @param {number} percentage - 进度百分比（0-100）
 * @param {string} text - 进度文本
 */
function updateImportProgress(percentage, text) {
    const progressContainer = document.querySelector('.progress-container');
    const progressFill = document.querySelector('.progress-fill');
    const progressText = document.querySelector('.progress-text');
    
    if (progressContainer) {
        progressContainer.style.display = 'block';
    }
    
    if (progressFill) {
        progressFill.style.width = percentage + '%';
    }
    
    if (progressText) {
        progressText.textContent = text || `导入进度: ${percentage}%`;
    }
}

/**
 * 验证导入数据格式
 * @param {Array} data - 导入的数据
 * @returns {Object} 验证结果
 */
function validateImportData(data) {
    const result = {
        valid: true,
        errors: [],
        warnings: []
    };
    
    if (!data || !Array.isArray(data) || data.length === 0) {
        result.valid = false;
        result.errors.push('导入数据为空或格式不正确');
        return result;
    }
    
    // 定义字段映射（支持多种表头格式）
    const fieldMappings = {
        name: ['姓名', '名字', 'name', 'Name', '参会人员', '人员姓名'],
        phone: ['手机号', '电话', '手机', 'phone', 'Phone', '联系电话', '手机号码'],
        seat_number: ['座位号', '座位', 'seat', 'Seat', '座位编号', '席位号']
    };
    
    // 检查必填字段
    let nameFieldFound = false;
    const firstRow = data[0] || {};
    
    // 检查是否存在姓名字段
    for (const field in firstRow) {
        if (fieldMappings.name.includes(field)) {
            nameFieldFound = true;
            break;
        }
    }
    
    if (!nameFieldFound) {
        result.valid = false;
        result.errors.push('未找到姓名字段，请确保Excel文件包含姓名列（支持的表头：' + fieldMappings.name.join('、') + '）');
        return result;
    }
    
    // 验证每行数据
    let validRowCount = 0;
    let emptyNameCount = 0;
    let duplicateNames = new Set();
    let nameSet = new Set();
    
    data.forEach((row, index) => {
        const rowNumber = row._rowIndex || (index + 2);
        
        // 获取姓名字段值
        let nameValue = null;
        for (const field in row) {
            if (fieldMappings.name.includes(field)) {
                nameValue = row[field];
                break;
            }
        }
        
        // 检查姓名是否为空
        if (!nameValue || nameValue.toString().trim() === '') {
            emptyNameCount++;
            result.warnings.push(`第${rowNumber}行：姓名为空，将跳过此行`);
            return;
        }
        
        // 检查姓名重复
        const trimmedName = nameValue.toString().trim();
        if (nameSet.has(trimmedName)) {
            duplicateNames.add(trimmedName);
            result.warnings.push(`第${rowNumber}行：姓名"${trimmedName}"重复，将跳过此行`);
            return;
        }
        nameSet.add(trimmedName);
        
        // 验证手机号格式（如果存在）
        for (const field in row) {
            if (fieldMappings.phone.includes(field) && row[field]) {
                const phoneValue = row[field].toString().trim();
                if (phoneValue && !/^1[3-9]\d{9}$/.test(phoneValue)) {
                    result.warnings.push(`第${rowNumber}行：手机号"${phoneValue}"格式不正确`);
                }
            }
        }
        
        validRowCount++;
    });
    
    // 检查是否有有效数据
    if (validRowCount === 0) {
        result.valid = false;
        result.errors.push('没有找到有效的数据行，请检查Excel文件内容');
        return result;
    }
    
    // 添加统计信息
    result.stats = {
        totalRows: data.length,
        validRows: validRowCount,
        emptyNameRows: emptyNameCount,
        duplicateCount: duplicateNames.size
    };
    
    // 如果有重复姓名，添加警告
    if (duplicateNames.size > 0) {
        result.warnings.push(`发现${duplicateNames.size}个重复姓名，重复的行将被跳过`);
    }
    
    console.log('数据验证结果:', result);
    return result;
}

/**
 * 处理导入结果
 * @param {Object} result - 导入结果
 */
function handleImportResult(result) {
    if (result.success) {
        showImportSuccess(`导入成功！共处理 ${result.total} 条记录，成功 ${result.success} 条`);
        
        if (result.warnings && result.warnings.length > 0) {
            result.warnings.forEach(warning => {
                showImportWarning(warning);
            });
        }
    } else {
        showImportError(result.message || '导入失败');
        
        if (result.errors && result.errors.length > 0) {
            result.errors.forEach(error => {
                showImportError(error);
            });
        }
    }
}

// 导出函数供全局使用
window.DataImport = {
    handleFileSelect,
    startImport,
    resetImportState,
    updateImportProgress,
    validateImportData,
    handleImportResult
};