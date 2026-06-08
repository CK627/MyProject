// 报名表单JavaScript功能

document.addEventListener('DOMContentLoaded', function() {
    // 首先检查页面状态
    checkPageStatus();
    
    // 获取表单元素
    const form = document.getElementById('registrationForm');
    const submitBtn = document.getElementById('submitBtn');
    const resetBtn = document.getElementById('resetBtn');
    
    // 获取输入字段
    const nameInput = document.getElementById('name');
    const phoneInput = document.getElementById('phone');
    const familyCountInputs = document.querySelectorAll('input[name="family_count"]');
    const paymentAmountInput = document.getElementById('paymentAmount');

    const talentSelect = document.getElementById('talentShow');
    const talentDetailsDiv = document.getElementById('talentDetails');
    const talentDetailsInput = document.getElementById('talentDescription');
    const costBreakdown = document.getElementById('costBreakdown');
    
    // 付款方式相关元素
    const paymentMethodInputs = document.querySelectorAll('input[name="payment_method"]');
    const paymentQrSection = document.getElementById('paymentQrSection');
    const otherPaymentSection = document.getElementById('otherPaymentSection');
    const paymentMethodName = document.getElementById('paymentMethodName');
    const defaultPaymentIcon = document.getElementById('defaultPaymentIcon');
    const qrCodePlaceholder = document.getElementById('qrCodePlaceholder');
    const qrCodeImage = document.getElementById('qrCodeImage');
    const totalAmountDisplay = document.getElementById('totalAmountDisplay');
    const otherPaymentAmount = document.getElementById('otherPaymentAmount');
    let paymentScreenshot = document.getElementById('paymentScreenshot');
    let uploadArea = document.getElementById('uploadArea');
    const uploadPreview = document.getElementById('uploadPreview');
    const removeScreenshot = document.getElementById('removeScreenshot');
    const sponsorshipInput = document.getElementById('materialSponsorship');
    const remarksInput = document.getElementById('remarks');

    // 表单验证规则
    const validationRules = {
        name: {
            required: true,
            minLength: 2,
            maxLength: 20,
            pattern: /^[\u4e00-\u9fa5a-zA-Z\s]+$/,
            message: '请输入2-20位中文或英文姓名'
        },
        phone: {
            required: true,
            pattern: /^1[3-9]\d{9}$/,
            message: '请输入正确的11位手机号码'
        },
        paymentAmount: {
            required: true,
            min: 0,
            max: 99999,
            message: '以自愿为原则，量力而行，遵从内心，上不封顶'
        },
        familyCount: {
            required: true,
            message: '请选择家属人数'
        }
    };

    // 实时验证函数
    function validateField(field, value) {
        const rules = validationRules[field];
        if (!rules) return { isValid: true };

        // 必填验证
        if (rules.required && (!value || value.trim() === '')) {
            return { isValid: false, message: `${getFieldName(field)}为必填项` };
        }

        // 如果不是必填且为空，则跳过其他验证
        if (!rules.required && (!value || value.trim() === '')) {
            return { isValid: true };
        }

        // 长度验证
        if (rules.minLength && value.length < rules.minLength) {
            return { isValid: false, message: `${getFieldName(field)}至少需要${rules.minLength}个字符` };
        }
        if (rules.maxLength && value.length > rules.maxLength) {
            return { isValid: false, message: `${getFieldName(field)}不能超过${rules.maxLength}个字符` };
        }

        // 数值范围验证
        if (rules.min !== undefined && parseFloat(value) < rules.min) {
            return { isValid: false, message: rules.message };
        }
        if (rules.max !== undefined && parseFloat(value) > rules.max) {
            return { isValid: false, message: rules.message };
        }

        // 正则表达式验证
        if (rules.pattern && !rules.pattern.test(value)) {
            return { isValid: false, message: rules.message };
        }

        return { isValid: true };
    }

    // 获取字段中文名称
    function getFieldName(field) {
        const fieldNames = {
            name: '姓名',
            phone: '手机号',
            paymentAmount: '缴费金额',
            familyCount: '家属人数'
        };
        return fieldNames[field] || field;
    }

    // 显示验证结果
    function showValidationResult(input, result) {
        const feedbackElement = input.parentNode.querySelector('.invalid-feedback') || 
                               input.parentNode.querySelector('.valid-feedback');
        
        // 移除现有的反馈元素
        if (feedbackElement) {
            feedbackElement.remove();
        }

        // 移除现有的验证类
        input.classList.remove('is-valid', 'is-invalid');

        if (result.isValid) {
            input.classList.add('is-valid');
            const validFeedback = document.createElement('div');
            validFeedback.className = 'valid-feedback';
            validFeedback.innerHTML = `<i class="fas fa-check-circle"></i> 输入正确`;
            input.parentNode.appendChild(validFeedback);
        } else {
            // 只添加红色边框，不显示错误信息文本
            input.classList.add('is-invalid');
            // 不再创建和显示 invalid-feedback 元素
        }
    }



    // 家属人数选择处理
    function handleFamilyCountSelection() {
        const familyCountCards = document.querySelectorAll('.family-count-card');
        familyCountCards.forEach(card => {
            card.classList.remove('selected');
        });
        
        const selectedFamilyCount = document.querySelector('input[name="family_count"]:checked');
        const overCapacityAlert = document.getElementById('overCapacityAlert');
        
        if (selectedFamilyCount) {
            selectedFamilyCount.closest('.family-count-card').classList.add('selected');
            
            // 检查是否选择了两个以上家属，显示超员提示
            const familyCount = parseInt(selectedFamilyCount.value);
            if (overCapacityAlert) {
                if (familyCount > 2) {
                    overCapacityAlert.style.display = 'block';
                } else {
                    overCapacityAlert.style.display = 'none';
                }
            }
        } else {
            // 如果没有选择，隐藏超员提示
            if (overCapacityAlert) {
                overCapacityAlert.style.display = 'none';
            }
        }
        
        updateTotalCost();
    }

    // 计算总费用
    function calculateTotalCost() {
        // 获取用户输入的缴费金额
        const paymentAmount = paymentAmountInput ? parseFloat(paymentAmountInput.value) || 0 : 0;
        return paymentAmount;
    }

    // 更新总费用显示
    function updateTotalCost() {
        const selectedFamilyCount = document.querySelector('input[name="family_count"]:checked');
        const is2025StudentCheckbox = document.getElementById('is2025Student');
        
        if (selectedFamilyCount) {
            const familyCount = parseInt(selectedFamilyCount.value);
            
            // 计算总费用
            const totalCost = calculateTotalCost();
            
            // 更新费用明细显示
            if (costBreakdown) {
                let breakdownHTML = '';
                
                // 显示缴费金额
                if (totalCost > 0) {
                    breakdownHTML += `
                        <div class="d-flex justify-content-between">
                            <span>缴费金额</span>
                            <span>¥${totalCost}</span>
                        </div>
                    `;
                }
                
                breakdownHTML += `
                    <hr>
                    <div class="d-flex justify-content-between fw-bold">
                        <span>总计</span>
                        <span class="text-primary">¥${totalCost}</span>
                    </div>
                `;
                
                costBreakdown.innerHTML = breakdownHTML;
            }
            
            // 更新付款区域的金额显示
            updateTotalAmountDisplay(totalCost);
            
            // 如果选择了其他付款方式，也更新其金额显示
            const selectedPaymentMethod = document.querySelector('input[name="payment_method"]:checked');
            if (selectedPaymentMethod && selectedPaymentMethod.value === 'other') {
                updateOtherPaymentAmount();
            }
        }
    }

    // 更新付款区域金额显示
    function updateTotalAmountDisplay(amount) {
        if (totalAmountDisplay) {
            totalAmountDisplay.textContent = `¥${amount || 0}`;
        }
    }

    // 才艺表演选择处理
    function handleTalentSelection() {
        if (talentSelect && talentDetailsDiv && talentDetailsInput) {
            // 如果选择了才艺表演（不是"不才艺表演"），则显示详情区域
            if (talentSelect.value && talentSelect.value !== '' && talentSelect.value !== '不才艺表演') {
                talentDetailsDiv.style.display = 'block';
                talentDetailsInput.required = true;
            } else {
                talentDetailsDiv.style.display = 'none';
                talentDetailsInput.required = false;
                talentDetailsInput.value = '';
            }
        }
    }

    // 手机号格式化
    function formatPhone(value) {
        const numbers = value.replace(/\D/g, '');
        if (numbers.length <= 3) return numbers;
        if (numbers.length <= 7) return `${numbers.slice(0, 3)} ${numbers.slice(3)}`;
        return `${numbers.slice(0, 3)} ${numbers.slice(3, 7)} ${numbers.slice(7, 11)}`;
    }

    // 金额格式化
    function formatAmount(value) {
        const numbers = value.replace(/[^\d.]/g, '');
        const parts = numbers.split('.');
        if (parts.length > 2) {
            return parts[0] + '.' + parts.slice(1).join('');
        }
        if (parts[1] && parts[1].length > 2) {
            parts[1] = parts[1].slice(0, 2);
        }
        return parts.join('.');
    }

    // 付款方式选择处理
    function handlePaymentMethodSelection() {
        const selectedMethod = document.querySelector('input[name="payment_method"]:checked');
        
        // 更新付款方式卡片选中状态
        document.querySelectorAll('.payment-method-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        if (selectedMethod) {
            selectedMethod.closest('.payment-method-card').classList.add('selected');
            
            const methodValue = selectedMethod.value;
            
            // 获取相关元素
            const paymentUploadSection = document.getElementById('paymentUploadSection');
            
            // 根据付款方式决定显示哪个区域
            if (methodValue === 'other') {
                // 选择其他付款方式时显示银行转账信息，隐藏二维码区域
                if (paymentQrSection) {
                    paymentQrSection.style.display = 'none';
                }
                if (otherPaymentSection) {
                    otherPaymentSection.style.display = 'block';
                }
                if (paymentUploadSection) {
                    paymentUploadSection.style.display = 'block';
                }
                // 隐藏收款码图片，显示占位符
                if (qrCodePlaceholder && qrCodeImage) {
                    qrCodeImage.style.display = 'none';
                    qrCodeImage.innerHTML = '';
                    qrCodePlaceholder.style.display = 'block';
                }
                // 更新其他付款方式的金额显示
                updateOtherPaymentAmount();
            } else {
                // 选择微信或支付宝时显示二维码区域，隐藏银行转账信息
                if (paymentQrSection) {
                    paymentQrSection.style.display = 'block';
                }
                if (otherPaymentSection) {
                    otherPaymentSection.style.display = 'none';
                }
                if (paymentUploadSection) {
                    paymentUploadSection.style.display = 'block';
                }
                
                // 更新付款方式名称和图标
                if (paymentMethodName && defaultPaymentIcon) {
                    if (methodValue === 'wechat') {
                        paymentMethodName.textContent = '微信支付';
                        defaultPaymentIcon.innerHTML = '<i class="fab fa-weixin text-success" style="font-size: 3rem;"></i>';
                    } else if (methodValue === 'alipay') {
                        paymentMethodName.textContent = '支付宝';
                        defaultPaymentIcon.innerHTML = '<i class="fab fa-alipay text-primary" style="font-size: 3rem;"></i>';
                    }
                }
                
                // 显示对应的收款码图片
                if (qrCodePlaceholder && qrCodeImage) {
                    if (methodValue === 'wechat') {
                        // 显示微信收款码
                        qrCodePlaceholder.style.display = 'none';
                        qrCodeImage.innerHTML = '<img src="../images/wx.jpg" alt="微信收款码" class="img-fluid">';
                        qrCodeImage.style.display = 'block';
                    } else if (methodValue === 'alipay') {
                        // 显示支付宝收款码
                        qrCodePlaceholder.style.display = 'none';
                        qrCodeImage.innerHTML = '<img src="../images/zbf.jpg" alt="支付宝收款码" class="img-fluid">';
                        qrCodeImage.style.display = 'block';
                    }
                }
                
                // 强制刷新DOM以确保图标更新
                if (defaultPaymentIcon) {
                    defaultPaymentIcon.style.display = 'none';
                    defaultPaymentIcon.offsetHeight; // 触发重排
                    defaultPaymentIcon.style.display = '';
                }
            }
        } else {
            // 隐藏所有付款区域
            if (paymentQrSection) {
                paymentQrSection.style.display = 'none';
            }
            if (otherPaymentSection) {
                otherPaymentSection.style.display = 'none';
            }
            // 隐藏收款码图片，显示占位符
            if (qrCodePlaceholder && qrCodeImage) {
                qrCodeImage.style.display = 'none';
                qrCodeImage.innerHTML = '';
                qrCodePlaceholder.style.display = 'block';
            }
            // 隐藏文件上传区域
            const paymentUploadSection = document.getElementById('paymentUploadSection');
            if (paymentUploadSection) {
                paymentUploadSection.style.display = 'none';
            }
        }
    }

    // 更新其他付款方式的金额显示
    function updateOtherPaymentAmount() {
        if (otherPaymentAmount) {
            const totalCost = calculateTotalCost();
            otherPaymentAmount.textContent = totalCost;
        }
    }

    // 处理2025级学生选项
    function handle2025StudentSelection() {
        const is2025StudentCheckbox = document.getElementById('is2025Student');
        const familyCountInputs = document.querySelectorAll('input[name="family_count"]');
        
        if (is2025StudentCheckbox && is2025StudentCheckbox.checked) {
            // 如果勾选了2025级学生
            
            // 1. 禁止选择携带家属，只能选择"不携带家属"
            familyCountInputs.forEach(input => {
                if (input.value === '0') {
                    // 自动选择"不携带家属"
                    input.checked = true;
                    input.disabled = false;
                } else {
                    // 禁用其他选项
                    input.checked = false;
                    input.disabled = true;
                }
            });
            
            // 2. 清空缴费金额输入框的值（但不禁用）
            if (paymentAmountInput) {
                paymentAmountInput.value = '';
                paymentAmountInput.classList.remove('is-valid', 'is-invalid');
            }
            
            // 更新家属选择卡片的视觉状态
            const familyCountCards = document.querySelectorAll('.family-count-card');
            familyCountCards.forEach((card, index) => {
                if (index === 0) { // "不携带家属"卡片
                    card.classList.add('selected');
                    card.style.opacity = '1';
                } else {
                    card.classList.remove('selected');
                    card.style.opacity = '0.5';
                    card.style.pointerEvents = 'none';
                }
            });
            
        } else {
            // 如果取消勾选2025级学生
            
            // 1. 恢复家属选择功能
            familyCountInputs.forEach(input => {
                input.disabled = false;
            });
            
            // 恢复家属选择卡片的视觉状态
            const familyCountCards = document.querySelectorAll('.family-count-card');
            familyCountCards.forEach(card => {
                card.style.opacity = '1';
                card.style.pointerEvents = 'auto';
            });
        }
        
        // 重新计算费用
        updateTotalCost();
        handleFamilyCountSelection();
    }

    // 文件上传处理
    function handleFileUpload() {
        if (!uploadArea || !paymentScreenshot) return;
        
        // 检查是否已经初始化过，避免重复绑定
        if (uploadArea.dataset.initialized === 'true') {
            return;
        }
        
        // 标记为已初始化
        uploadArea.dataset.initialized = 'true';
        
        // 重新获取uploadPreview引用
        const uploadPreview = document.getElementById('uploadPreview');

        // 点击上传区域触发文件选择（但要避免点击到input本身）
        uploadArea.addEventListener('click', function(e) {
            // 如果点击的是input元素本身，不要重复触发
            if (e.target === paymentScreenshot) {
                return;
            }
            e.preventDefault();
            e.stopPropagation();
            paymentScreenshot.click();
        });

        // 阻止input元素的点击事件冒泡
        paymentScreenshot.addEventListener('click', function(e) {
            e.stopPropagation();
        });

        // 拖拽上传功能
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });

        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
        });

        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            e.stopPropagation();
            uploadArea.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFileSelect(files[0], uploadPreview);
            }
        });

        // 文件选择处理
        paymentScreenshot.addEventListener('change', function(e) {
            e.stopPropagation();
            if (e.target.files.length > 0) {
                handleFileSelect(e.target.files[0], uploadPreview);
            }
        });
    }
    
    // 重新初始化文件上传（用于重置后）
    function reinitializeFileUpload() {
        // 清除初始化标记
        if (uploadArea) {
            uploadArea.dataset.initialized = 'false';
        }
        // 重新初始化
        handleFileUpload();
    }











    // 处理文件选择
    function handleFileSelect(file, uploadPreview) {
        // 验证文件类型
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
        if (!allowedTypes.includes(file.type)) {
            alert('请选择图片文件（JPG、PNG、GIF）');
            return;
        }
        
        // 验证文件大小（5MB）
        if (file.size > 5 * 1024 * 1024) {
            alert('文件大小不能超过5MB');
            return;
        }
        
        // 重命名文件
        const renamedFile = renameFile(file);
        
        // 显示预览
        displayFilePreview(renamedFile, uploadPreview);
    }

    // 重命名文件
    function renameFile(file) {
        const name = nameInput ? nameInput.value.trim() : '';
        const phone = phoneInput ? phoneInput.value.replace(/\s/g, '') : '';
        
        if (name && phone) {
            const extension = file.name.split('.').pop();
            const newName = `${name}_${phone}.${extension}`;
            
            // 创建新的File对象
            const renamedFile = new File([file], newName, { type: file.type });
            return renamedFile;
        }
        
        return file;
    }

    // 显示文件预览
    function displayFilePreview(file, uploadPreview) {
        if (!uploadPreview) {
            console.error('uploadPreview element not found');
            return;
        }
        
        // 创建新的DataTransfer对象来设置文件
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        paymentScreenshot.files = dataTransfer.files;
        
        const reader = new FileReader();
        reader.onload = function(e) {
            uploadPreview.innerHTML = `
                <div class="preview-container text-center">
                    <img src="${e.target.result}" alt="付款凭证" class="preview-image" style="max-width: 300px; max-height: 400px; width: auto; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <div class="mt-2">
                        <small class="text-muted d-block">${file.name}</small>
                        <small class="text-muted">${(file.size / 1024 / 1024).toFixed(2)} MB</small>
                    </div>
                    <button type="button" class="btn btn-sm btn-outline-danger mt-2" id="removeScreenshot">
                        <i class="fas fa-trash me-1"></i>删除
                    </button>
                </div>
            `;
            uploadPreview.style.display = 'block';
            
            // 隐藏上传区域的占位符，但保持input可用
            const uploadPlaceholder = uploadArea.querySelector('.upload-placeholder');
            if (uploadPlaceholder) {
                uploadPlaceholder.style.display = 'none';
            }
            
            // 绑定删除按钮事件
            const removeBtn = uploadPreview.querySelector('#removeScreenshot');
            if (removeBtn) {
                removeBtn.addEventListener('click', function() {
                    uploadPreview.style.display = 'none';
                    uploadPreview.innerHTML = '';
                    paymentScreenshot.value = '';
                    
                    // 显示上传区域的占位符
                    if (uploadPlaceholder) {
                        uploadPlaceholder.style.display = 'block';
                    }
                });
            }
            
            // 模拟保存到付款记录文件夹
            // 文件已上传
        };
        reader.readAsDataURL(file);
    }

    // 移除上传的文件
    function removeUploadedFile() {
        // 由于删除按钮是动态创建的，不需要特殊处理重复绑定
        // 每次创建预览时都会重新创建删除按钮
    }

    // 绑定事件监听器
    function bindEventListeners() {
        // 姓名输入事件
        if (nameInput) {
            nameInput.addEventListener('input', updateTotalCost);
            nameInput.addEventListener('blur', function() {
                const result = validateField('name', this.value);
                showValidationResult(this, result);
            });
        }

        // 手机号输入事件
        if (phoneInput) {
            phoneInput.addEventListener('input', function() {
                this.value = formatPhone(this.value);
                updateTotalCost();
            });
            
            phoneInput.addEventListener('blur', function() {
                const result = validateField('phone', this.value.replace(/\s/g, ''));
                showValidationResult(this, result);
            });
        }

        // 缴费金额输入事件
        if (paymentAmountInput) {
            paymentAmountInput.addEventListener('input', function() {
                this.value = formatAmount(this.value);
                updateTotalCost();
            });
            
            paymentAmountInput.addEventListener('blur', function() {
                const result = validateField('paymentAmount', this.value);
                showValidationResult(this, result);
            });
        }

        // 家属人数选择事件
        familyCountInputs.forEach(input => {
            input.addEventListener('change', handleFamilyCountSelection);
        });

        // 已移除额外捐赠功能相关事件监听

        // 才艺表演选择事件
        if (talentSelect) {
            talentSelect.addEventListener('change', handleTalentSelection);
        }

        // 付款方式选择事件
        paymentMethodInputs.forEach(input => {
            input.addEventListener('change', handlePaymentMethodSelection);
        });

        // 2025级学生选项事件
        const is2025StudentCheckbox = document.getElementById('is2025Student');
        if (is2025StudentCheckbox) {
            is2025StudentCheckbox.addEventListener('change', handle2025StudentSelection);
        }
    }

    // 表单提交处理
    // 表单验证函数
    function validateForm() {
        let isFormValid = true;
        
        // 验证姓名
        if (nameInput) {
            const nameResult = validateField('name', nameInput.value);
            showValidationResult(nameInput, nameResult);
            if (!nameResult.isValid) isFormValid = false;
        }
        
        // 验证手机号
        if (phoneInput) {
            const phoneResult = validateField('phone', phoneInput.value.replace(/\s/g, ''));
            showValidationResult(phoneInput, phoneResult);
            if (!phoneResult.isValid) isFormValid = false;
        }
        
        // 验证缴费金额（2025级学生免费，跳过验证）
        const is2025StudentCheckbox = document.getElementById('is2025Student');
        if (paymentAmountInput && !(is2025StudentCheckbox && is2025StudentCheckbox.checked)) {
            const paymentAmountResult = validateField('paymentAmount', paymentAmountInput.value);
            showValidationResult(paymentAmountInput, paymentAmountResult);
            if (!paymentAmountResult.isValid) isFormValid = false;
        }
        
        // 验证家属人数选择
        const selectedFamilyCount = document.querySelector('input[name="family_count"]:checked');
        if (!selectedFamilyCount) {
            showMessage('请选择家属人数', 'error');
            isFormValid = false;
        }
        
        // 移除额外捐赠功能，无需验证缴费金额

        
        // 验证付款方式选择（必填）
        const selectedPaymentMethod = document.querySelector('input[name="payment_method"]:checked');
        if (!selectedPaymentMethod) {
            showMessage('请选择付款方式', 'error');
            isFormValid = false;
        } else {
            // 验证付款凭证上传
            if (!paymentScreenshot || !paymentScreenshot.files[0]) {
                showMessage('请上传付款凭证', 'error');
                isFormValid = false;
            }
        }
        
        return isFormValid;
    }
    
    // 获取表单数据
     function getFormData() {
         const formData = new FormData();
         
         // 基本信息
         formData.append('name', nameInput ? nameInput.value.trim() : '');
         formData.append('phone', phoneInput ? phoneInput.value.replace(/\s/g, '') : '');
         
         // 2025级学生选项
         const is2025StudentCheckbox = document.getElementById('is2025Student');
         formData.append('is_2025_student', is2025StudentCheckbox && is2025StudentCheckbox.checked ? '1' : '0');
         
         // 缴费金额（2025级学生免费）
         const is2025Student = is2025StudentCheckbox && is2025StudentCheckbox.checked;
         const paymentAmount = is2025Student ? '0' : (paymentAmountInput ? paymentAmountInput.value : '0');
         formData.append('payment_amount', paymentAmount);
         
         // 家属信息
         const selectedFamilyCount = document.querySelector('input[name="family_count"]:checked');
         formData.append('family_count', selectedFamilyCount ? selectedFamilyCount.value : '0');
         
         // 移除额外捐赠功能
         
         // 才艺表演
         formData.append('talent_show', talentSelect ? talentSelect.value : '');
         if (talentDetailsInput && talentDetailsInput.value.trim()) {
             formData.append('talent_description', talentDetailsInput.value.trim());
         }
         
         // 付款方式
         const selectedPaymentMethod = document.querySelector('input[name="payment_method"]:checked');
         formData.append('payment_method', selectedPaymentMethod ? selectedPaymentMethod.value : '');
         
         // 付款截图
         if (paymentScreenshot && paymentScreenshot.files[0]) {
             formData.append('payment_screenshot', paymentScreenshot.files[0]);
         }
         
         // 物资赞助
         formData.append('material_sponsorship', sponsorshipInput ? sponsorshipInput.value.trim() : '');
         
         // 备注
         formData.append('remarks', remarksInput ? remarksInput.value.trim() : '');
         
         return formData;
     }
    
    // 重置表单
    function handleReset() {
        if (form) {
            form.reset();
        }
        

        
        // 重置家属人数选择状态
        document.querySelectorAll('.family-count-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        // 重置付款方式选择状态
        document.querySelectorAll('.payment-method-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        // 隐藏付款区域
        if (paymentQrSection) {
            paymentQrSection.style.display = 'none';
        }
        
        // 完全重置文件上传区域
        resetFileUploadArea();
        

        
        // 重置才艺表演
        if (talentDetailsDiv) {
            talentDetailsDiv.style.display = 'none';
        }
        if (talentDetailsInput) {
            talentDetailsInput.required = false;
            talentDetailsInput.value = '';
        }
        
        // 清除验证状态
        const validatedInputs = document.querySelectorAll('.is-valid, .is-invalid');
        validatedInputs.forEach(input => {
            input.classList.remove('is-valid', 'is-invalid');
        });
        
        const feedbacks = document.querySelectorAll('.valid-feedback, .invalid-feedback');
        feedbacks.forEach(feedback => feedback.remove());
        
        // 重置2025级学生选项
        const is2025StudentCheckbox = document.getElementById('is2025Student');
        if (is2025StudentCheckbox) {
            is2025StudentCheckbox.checked = false;
        }
        
        // 恢复家属选择和缴费金额的正常状态
        const familyCountInputs = document.querySelectorAll('input[name="family_count"]');
        familyCountInputs.forEach(input => {
            input.disabled = false;
        });
        
        // 重置缴费金额
        if (paymentAmountInput) {
            paymentAmountInput.value = '';
            paymentAmountInput.disabled = false;
        }
        

        
        // 恢复家属选择卡片的视觉状态
        const familyCountCards = document.querySelectorAll('.family-count-card');
        familyCountCards.forEach(card => {
            card.style.opacity = '1';
            card.style.pointerEvents = 'auto';
        });
        
        // 隐藏超员提示
        const overCapacityAlert = document.getElementById('overCapacityAlert');
        if (overCapacityAlert) {
            overCapacityAlert.style.display = 'none';
        }
        
        // 重置费用显示
        updateTotalCost();
        
        // 重新初始化文件上传功能
        setTimeout(() => {
            reinitializeFileUpload();
        }, 100);
    }
    
    // 完全重置文件上传区域
    function resetFileUploadArea() {
        // 清空文件输入
        if (paymentScreenshot) {
            paymentScreenshot.value = '';
            paymentScreenshot.files = null;
        }
        
        // 隐藏预览区域
        if (uploadPreview) {
            uploadPreview.style.display = 'none';
            uploadPreview.innerHTML = '';
        }
        
        // 显示上传区域
        if (uploadArea) {
            uploadArea.style.display = 'block';
            // 显示上传占位符
            const uploadPlaceholder = uploadArea.querySelector('.upload-placeholder');
            if (uploadPlaceholder) {
                uploadPlaceholder.style.display = 'block';
            }
            // 移除拖拽状态
            uploadArea.classList.remove('drag-over');
        }
    }

    // 重置按钮处理
    if (resetBtn) {
        resetBtn.addEventListener('click', handleReset);
    }

    // 工具函数
    function setButtonLoading(button, loading) {
        if (!button) return;
        
        if (loading) {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>提交中...';
        } else {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-paper-plane me-2"></i>提交报名';
        }
    }

    function generateRegistrationNumber() {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const random = Math.floor(Math.random() * 10000).toString().padStart(4, '0');
        return `REG${year}${month}${day}${random}`;
    }

    function showMessage(message, type) {
        // 只显示成功类型的消息，错误消息通过弹窗显示
        if (type === 'error') {
            return; // 不显示错误消息
        }
        
        // 创建消息提示（只用于成功消息）
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-success alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // 插入到表单顶部
        if (form) {
            form.insertBefore(alertDiv, form.firstChild);
        }
        
        // 自动消失
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }

    function showSuccessMessage(registrationNumber) {
        const message = `
            <strong>报名成功！</strong><br>
            您的报名编号是：<strong>${registrationNumber}</strong><br>
            请保存好此编号，以便后续查询。
        `;
        showMessage(message, 'success');
    }

    // 弹窗控制功能
    const modalElements = {
        registrationClosed: document.getElementById('registrationClosedModal'),
        registrationSuccess: document.getElementById('registrationSuccessModal'),
        registrationFailed: document.getElementById('registrationFailedModal'),
        failureReason: document.getElementById('failureReason')
    };

    // 显示报名未开启弹窗
    function showRegistrationClosedModal(reason = '报名暂未开放') {
        if (modalElements.registrationClosed) {
            // 更新弹窗中的错误信息
            const reasonElement = modalElements.registrationClosed.querySelector('.modal-body p');
            if (reasonElement) {
                reasonElement.textContent = reason;
            }
            
            const modal = new bootstrap.Modal(modalElements.registrationClosed);
            modal.show();
        }
    }

    // 显示报名成功弹窗
    function showRegistrationSuccessModal() {
        if (modalElements.registrationSuccess) {
            const modal = new bootstrap.Modal(modalElements.registrationSuccess);
            modal.show();
        }
    }

    // 显示报名失败弹窗
    function showRegistrationFailedModal(reason = '报名提交失败，请检查网络连接后重试。') {
        if (modalElements.registrationFailed && modalElements.failureReason) {
            // 处理多行文本显示
            const formattedReason = reason.replace(/\n/g, '<br>');
            modalElements.failureReason.innerHTML = formattedReason;
            
            // 如果是重复报名错误，调整模态框样式
            if (reason.includes('已经报名') || reason.includes('重复报名')) {
                // 更改图标颜色为橙色（警告色）
                const icon = modalElements.registrationFailed.querySelector('.modal-body i.fas');
                if (icon) {
                    icon.style.color = '#ffc107';
                    icon.className = 'fas fa-user-check mb-3';
                }
                
                // 更改标题
                const title = modalElements.registrationFailed.querySelector('.modal-title');
                if (title) {
                    title.innerHTML = '<i class="fas fa-user-check me-2"></i>重复报名提醒';
                }
                
                // 更改按钮文本
                const button = modalElements.registrationFailed.querySelector('.modal-footer .btn');
                if (button) {
                    button.innerHTML = '<i class="fas fa-check me-2"></i>我知道了';
                }
            } else {
                // 恢复默认样式
                const icon = modalElements.registrationFailed.querySelector('.modal-body i.fas');
                if (icon) {
                    icon.style.color = '#dc3545';
                    icon.className = 'fas fa-exclamation-circle mb-3';
                }
                
                const title = modalElements.registrationFailed.querySelector('.modal-title');
                if (title) {
                    title.innerHTML = '<i class="fas fa-times-circle me-2"></i>报名失败';
                }
                
                const button = modalElements.registrationFailed.querySelector('.modal-footer .btn');
                if (button) {
                    button.innerHTML = '<i class="fas fa-redo me-2"></i>重试';
                }
            }
            
            const modal = new bootstrap.Modal(modalElements.registrationFailed);
            modal.show();
        }
    }

    // 检查报名状态（调用API获取真实时间）
    async function checkRegistrationStatus() {
        try {
            const response = await fetch('../api/registrations.php?action=settings');
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const contentType = response.headers.get('content-type');
            
            // 检查是否返回的是JSON
            if (!contentType || !contentType.includes('application/json')) {
                // 如果不是JSON响应（比如静态服务器返回PHP源码），说明PHP环境不可用
            // PHP环境不可用，跳过报名状态检查
                return {
                    isOpen: true,
                    reason: '无法获取报名状态，默认允许报名'
                };
            }
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || '获取设置失败');
            }
            
            const settings = data.data;
            
            // 查找开始和结束时间设置
            const startTimeSetting = settings.find(s => s.setting_key === 'registration_start_time');
            const endTimeSetting = settings.find(s => s.setting_key === 'registration_end_time');
            
            if (!startTimeSetting || !endTimeSetting) {
                throw new Error('报名时间设置不完整');
            }
            
            const now = new Date();
            const startTime = new Date(startTimeSetting.setting_value);
            const endTime = new Date(endTimeSetting.setting_value);
            
            if (now < startTime) {
                return {
                    isOpen: false,
                    reason: `报名尚未开始，开始时间：${startTime.toLocaleString()}`
                };
            } else if (now > endTime) {
                return {
                    isOpen: false,
                    reason: `报名已结束，结束时间：${endTime.toLocaleString()}`
                };
            } else {
                return {
                    isOpen: true,
                    reason: '报名进行中'
                };
            }
        } catch (error) {
            console.error('检查报名状态失败:', error);
            // 如果检查失败，默认允许报名（避免因网络问题阻止正常报名）
            return {
                isOpen: true,
                reason: '无法获取报名状态，请稍后重试'
            };
        }
    }



    // 修改原有的表单提交处理函数
    function handleFormSubmit() {
        if (!form) return;
        
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // 先检查报名状态
            const registrationStatus = await checkRegistrationStatus();
            if (!registrationStatus.isOpen) {
                showRegistrationClosedModal(registrationStatus.reason);
                return;
            }
            
            // 验证表单
            if (!validateForm()) {
                showRegistrationFailedModal('请检查并修正表单中的错误');
                return;
            }
            
            // 显示加载状态
            setButtonLoading(submitBtn, true);
            
            // 准备表单数据
            const formData = new FormData();
            formData.append('name', nameInput.value.trim());
            formData.append('phone', phoneInput.value.replace(/\s/g, ''));
            
            // 2025级学生选项
            const is2025StudentCheckbox = document.getElementById('is2025Student');
            formData.append('is_2025_student', is2025StudentCheckbox && is2025StudentCheckbox.checked ? '1' : '0');
            
            // 学历信息（可选）
            const educationInfoInput = document.getElementById('educationInfo');
            if (educationInfoInput && educationInfoInput.value.trim()) {
                formData.append('education_info', educationInfoInput.value.trim());
            }
            
            // 家属人数
            const selectedFamilyCount = document.querySelector('input[name="family_count"]:checked');
            formData.append('family_count', selectedFamilyCount ? selectedFamilyCount.value : '0');
            
            // 缴费金额（使用用户输入的金额）
            const paymentAmount = paymentAmountInput ? paymentAmountInput.value : '0';
            formData.append('payment_amount', paymentAmount);
            
            // 移除额外捐赠功能，无需添加总费用
            
            // 才艺表演
            if (talentSelect && talentSelect.value) {
                formData.append('talent_show', talentSelect.value);
                if (talentDetailsInput && talentDetailsInput.value.trim()) {
                    formData.append('talent_description', talentDetailsInput.value.trim());
                }
            }
            
            // 物资赞助
            const materialSponsorshipInput = document.getElementById('materialSponsorship');
            if (materialSponsorshipInput && materialSponsorshipInput.value.trim()) {
                formData.append('material_sponsorship', materialSponsorshipInput.value.trim());
            }
            
            // 备注
            const remarksInput = document.getElementById('remarks');
            if (remarksInput && remarksInput.value.trim()) {
                formData.append('remarks', remarksInput.value.trim());
            }
            
            // 付款方式
            const selectedPaymentMethod = document.querySelector('input[name="payment_method"]:checked');
            if (selectedPaymentMethod) {
                formData.append('payment_method', selectedPaymentMethod.value);
                
                // 付款凭证
                if (paymentScreenshot && paymentScreenshot.files[0]) {
                    formData.append('payment_screenshot', paymentScreenshot.files[0]);
                }
            }
            
            // 发送请求到API
            fetch('../api/registrations.php', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                // 先检查HTTP状态码
                if (!response.ok) {
                    // 对于409状态码（手机号已存在），特殊处理
                    if (response.status === 409) {
                        return response.json().then(data => {
                            throw new Error(data.message || '该手机号已报名，请勿重复报名');
                        });
                    }
                    // 对于403状态码（报名时间限制），特殊处理
                    if (response.status === 403) {
                        return response.json().then(data => {
                            throw new Error(data.message || '当前不在报名时间范围内');
                        });
                    }
                    // 其他HTTP错误
                    throw new Error(`请求失败 (${response.status})`);
                }
                return response.json();
            })
            .then(data => {
                setButtonLoading(submitBtn, false);
                
                if (data.success) {
                    // 报名成功
                    showRegistrationSuccessModal();
                    
                    // 3秒后重置表单
                    setTimeout(() => {
                        handleReset();
                    }, 3000);
                } else {
                    // 报名失败
                    showRegistrationFailedModal(data.message || '报名提交失败，请稍后重试');
                }
            })
            .catch(error => {
                setButtonLoading(submitBtn, false);
                console.error('提交错误:', error);
                
                // 根据错误类型显示不同的提示
                let errorMessage = error.message;
                
                // 特殊处理常见错误
                if (errorMessage.includes('已报名') || errorMessage.includes('重复报名')) {
                    errorMessage = '该手机号已经报名过了！\n\n如有疑问，请联系工作人员：\n吴小琴 18928756699';
                } else if (errorMessage.includes('报名时间')) {
                    errorMessage = '当前不在报名时间范围内，请在规定时间内进行报名';
                } else if (errorMessage.includes('网络') || errorMessage.includes('连接')) {
                    errorMessage = '网络连接失败，请检查网络后重试';
                } else if (!errorMessage || errorMessage === 'Failed to fetch') {
                    errorMessage = '网络连接失败，请检查网络后重试';
                }
                
                showRegistrationFailedModal(errorMessage);
            });
        });
    }

    // 初始化
    async function init() {
        bindEventListeners();
        handleFormSubmit();
        handleFileUpload();
        
        // 初始化费用显示
        updateTotalCost();
        
        // 初始化才艺表演状态
        handleTalentSelection();
        
        // 检查报名状态
        await checkInitialRegistrationStatus();
    }
    

    
    // 检查初始报名状态
    async function checkInitialRegistrationStatus() {
        try {
            const registrationStatus = await checkRegistrationStatus();
            if (!registrationStatus.isOpen) {
                // 如果报名未开放，显示提示信息
                showRegistrationStatusMessage(registrationStatus.reason);
                // 可选：禁用提交按钮
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<i class="fas fa-clock me-2"></i>报名未开放';
                }
            }
        } catch (error) {
            console.error('检查初始报名状态失败:', error);
        }
    }
    
    // 显示报名状态消息
    function showRegistrationStatusMessage(message) {
        // 在表单顶部显示状态消息
        if (form) {
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-warning alert-dismissible fade show';
            alertDiv.innerHTML = `
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            form.insertBefore(alertDiv, form.firstChild);
        }
    }

    // 启动应用
    init();
});

// 检查页面状态函数
async function checkPageStatus() {
    try {
        const response = await fetch('../api/registrations.php?action=settings&key=registration_page_status');
        
        if (response.ok) {
            const contentType = response.headers.get('content-type');
            
            // 检查是否返回的是JSON
            if (contentType && contentType.includes('application/json')) {
                const data = await response.json();
                
                if (data.success && data.data && data.data.value === 'maintenance') {
                    // 页面处于维护状态，重定向到建设中页面
                    window.location.href = 'under-construction.html';
                    return;
                }
            } else {
                // 如果不是JSON响应（比如静态服务器返回PHP源码），说明PHP环境不可用
                // console.log('PHP环境不可用，跳过页面状态检查');
            }
        }
        
        // 如果获取状态失败或状态为active，继续正常加载页面
        // 页面状态检查完成，正常加载
        
    } catch (error) {
        console.error('检查页面状态失败:', error);
        // 如果检查失败，继续正常加载页面
    }
}